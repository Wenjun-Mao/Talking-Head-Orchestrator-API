from __future__ import annotations

import os
import subprocess
import sys
import time
from collections import deque
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import imageio
import librosa
import numpy as np
import torch
from loguru import logger


@contextmanager
def _pushd(path: Path):
	old_cwd = Path.cwd()
	os.chdir(path)
	try:
		yield
	finally:
		os.chdir(old_cwd)


class SoulXRuntime:
	def __init__(self, *, flashhead_ckpt_dir: str, wav2vec_dir: str, model_type: str) -> None:
		self.vendor_root = Path(__file__).resolve().parents[2] / "vendor" / "SoulX-FlashHead"
		self.flashhead_ckpt_dir = str(Path(flashhead_ckpt_dir).resolve())
		self.wav2vec_dir = str(Path(wav2vec_dir).resolve())
		self.model_type = model_type

		if self.model_type not in {"pro", "lite"}:
			raise ValueError(f"Invalid S4_MODEL_TYPE={self.model_type!r}; expected 'pro' or 'lite'")

		if not self.vendor_root.exists():
			raise FileNotFoundError(f"SoulX vendor repo not found at: {self.vendor_root}")
		if not Path(self.flashhead_ckpt_dir).exists():
			raise FileNotFoundError(f"FlashHead checkpoint dir not found: {self.flashhead_ckpt_dir}")
		if not Path(self.wav2vec_dir).exists():
			raise FileNotFoundError(f"wav2vec checkpoint dir not found: {self.wav2vec_dir}")

		if str(self.vendor_root) not in sys.path:
			sys.path.insert(0, str(self.vendor_root))

		with _pushd(self.vendor_root):
			import flash_head.inference as flash_inference

		self.flash_inference = flash_inference
		logger.info(
			"Loading SoulX pipeline at startup (model_type={}, ckpt_dir={}, wav2vec_dir={})",
			self.model_type,
			self.flashhead_ckpt_dir,
			self.wav2vec_dir,
		)
		self.pipeline = self.flash_inference.get_pipeline(
			world_size=1,
			ckpt_dir=self.flashhead_ckpt_dir,
			wav2vec_dir=self.wav2vec_dir,
			model_type=self.model_type,
		)
		self.infer_params = self.flash_inference.get_infer_params()
		self._is_prewarmed = False
		logger.info("SoulX pipeline preloaded successfully")

	def prewarm(
		self,
		*,
		cond_image_path: str,
		base_seed: int,
		use_face_crop: bool,
		duration_sec: int,
	) -> bool:
		if self._is_prewarmed:
			logger.info("SoulX startup prewarm skipped: already prewarmed")
			return True

		cond_image = Path(cond_image_path)
		if not cond_image.exists():
			logger.warning("SoulX startup prewarm skipped: cond image not found at {}", cond_image)
			return False

		sample_rate = int(self.infer_params["sample_rate"])
		tgt_fps = int(self.infer_params["tgt_fps"])
		cached_audio_duration = int(self.infer_params["cached_audio_duration"])
		frame_num = int(self.infer_params["frame_num"])

		audio_start_idx = cached_audio_duration * tgt_fps - frame_num
		audio_end_idx = cached_audio_duration * tgt_fps

		warmup_sec = max(cached_audio_duration, int(duration_sec))
		warmup_audio = np.zeros(sample_rate * warmup_sec, dtype=np.float32)

		logger.info(
			"Starting SoulX startup prewarm (duration_sec={}, cond_image={}, model_type={})",
			warmup_sec,
			cond_image,
			self.model_type,
		)

		with _pushd(self.vendor_root):
			self.flash_inference.get_base_data(
				self.pipeline,
				cond_image_path_or_dir=str(cond_image),
				base_seed=base_seed,
				use_face_crop=use_face_crop,
			)

			audio_embedding = self.flash_inference.get_audio_embedding(
				self.pipeline,
				warmup_audio,
				audio_start_idx,
				audio_end_idx,
			)

			if torch.cuda.is_available():
				torch.cuda.synchronize()
			start_ts = time.time()
			self._run_pipeline(audio_embedding, chunk_idx=-1)
			if torch.cuda.is_available():
				torch.cuda.synchronize()
			elapsed = time.time() - start_ts

		self._is_prewarmed = True
		logger.info("SoulX startup prewarm completed in {:.2f}s", elapsed)
		return True

	def generate(
		self,
		*,
		record_id: int,
		cond_image_path: str,
		audio_path: str,
		output_dir: str,
		base_seed: int,
		use_face_crop: bool,
		audio_encode_mode: str,
	) -> str:
		cond_image = Path(cond_image_path)
		source_audio = Path(audio_path)
		if not cond_image.exists():
			raise FileNotFoundError(f"Condition image not found: {cond_image}")
		if not source_audio.exists():
			raise FileNotFoundError(f"TTS audio not found: {source_audio}")

		if audio_encode_mode not in {"stream", "once"}:
			raise ValueError(
				f"Invalid S4_AUDIO_ENCODE_MODE={audio_encode_mode!r}; expected 'stream' or 'once'"
			)

		output_root = Path(output_dir)
		output_root.mkdir(parents=True, exist_ok=True)

		with _pushd(self.vendor_root):
			self.flash_inference.get_base_data(
				self.pipeline,
				cond_image_path_or_dir=str(cond_image),
				base_seed=base_seed,
				use_face_crop=use_face_crop,
			)

		generated_frames = self._run_inference(source_audio, audio_encode_mode)
		if not generated_frames:
			raise RuntimeError("SoulX produced no video chunks from the provided audio")

		out_path = output_root / f"record_{record_id}_{uuid4().hex}_soulx.mp4"
		self._save_video(
			frames_list=generated_frames,
			video_path=out_path,
			audio_path=source_audio,
			fps=int(self.infer_params["tgt_fps"]),
		)
		return str(out_path)

	def _run_inference(self, audio_path: Path, audio_encode_mode: str) -> list[torch.Tensor]:
		sample_rate = int(self.infer_params["sample_rate"])
		tgt_fps = int(self.infer_params["tgt_fps"])
		cached_audio_duration = int(self.infer_params["cached_audio_duration"])
		frame_num = int(self.infer_params["frame_num"])
		motion_frames_num = int(self.infer_params["motion_frames_num"])
		slice_len = frame_num - motion_frames_num

		audio_array_all, _ = librosa.load(str(audio_path), sr=sample_rate, mono=True)
		if audio_array_all.size == 0:
			raise RuntimeError("Input TTS audio is empty")

		generated_list: list[torch.Tensor] = []
		if audio_encode_mode == "once":
			audio_embedding_all = self.flash_inference.get_audio_embedding(self.pipeline, audio_array_all)
			total_frames = int(audio_embedding_all.shape[1])
			if total_frames < frame_num:
				return generated_list
			chunk_count = 1 + (total_frames - frame_num) // slice_len
			for chunk_idx in range(chunk_count):
				start = chunk_idx * slice_len
				end = start + frame_num
				audio_embedding_chunk = audio_embedding_all[:, start:end].contiguous()
				generated_list.append(self._run_pipeline(audio_embedding_chunk, chunk_idx))
			return generated_list

		cached_audio_length_sum = sample_rate * cached_audio_duration
		audio_end_idx = cached_audio_duration * tgt_fps
		audio_start_idx = audio_end_idx - frame_num
		audio_dq = deque([0.0] * cached_audio_length_sum, maxlen=cached_audio_length_sum)

		human_speech_array_slice_len = max(1, slice_len * sample_rate // tgt_fps)
		clipped = audio_array_all[
			: (len(audio_array_all) // human_speech_array_slice_len) * human_speech_array_slice_len
		]
		if clipped.size == 0:
			clipped = np.pad(audio_array_all, (0, human_speech_array_slice_len - len(audio_array_all)))
		speech_slices = clipped.reshape(-1, human_speech_array_slice_len)

		for chunk_idx, speech_slice in enumerate(speech_slices):
			audio_dq.extend(speech_slice.tolist())
			audio_array = np.array(audio_dq)
			audio_embedding = self.flash_inference.get_audio_embedding(
				self.pipeline,
				audio_array,
				audio_start_idx,
				audio_end_idx,
			)
			generated_list.append(self._run_pipeline(audio_embedding, chunk_idx))
		return generated_list

	def _run_pipeline(self, audio_embedding: torch.Tensor, chunk_idx: int) -> torch.Tensor:
		if torch.cuda.is_available():
			torch.cuda.synchronize()
		video = self.flash_inference.run_pipeline(self.pipeline, audio_embedding)
		if torch.cuda.is_available():
			torch.cuda.synchronize()
		logger.debug("SoulX generated chunk {}", chunk_idx)
		return video.cpu()

	@staticmethod
	def _save_video(frames_list: list[torch.Tensor], video_path: Path, audio_path: Path, fps: int) -> None:
		temp_video_path = video_path.with_name(video_path.stem + "_tmp.mp4")
		with imageio.get_writer(
			str(temp_video_path),
			format="mp4",
			mode="I",
			fps=fps,
			codec="h264",
			ffmpeg_params=["-bf", "0"],
		) as writer:
			for frames in frames_list:
				np_frames = frames.numpy().astype(np.uint8)
				for idx in range(np_frames.shape[0]):
					writer.append_data(np_frames[idx])

		cmd = [
			"ffmpeg",
			"-i",
			str(temp_video_path),
			"-i",
			str(audio_path),
			"-c:v",
			"copy",
			"-c:a",
			"aac",
			"-shortest",
			str(video_path),
			"-y",
		]
		result = subprocess.run(cmd, capture_output=True, text=True)
		if result.returncode != 0:
			raise RuntimeError(f"ffmpeg merge failed: {result.stderr}")
		temp_video_path.unlink(missing_ok=True)
