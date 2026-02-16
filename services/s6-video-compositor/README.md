Compose background video with avatar overlay and align durations.

Dependencies: managed with uv via pyproject.toml.

Message in
- `record_id`
- `table_id`
- `douyin_video_path`
- `tts_audio_path`
- `inference_video_path`

Message out
- `record_id`
- `table_id`
- `composited_video_path`

Performance notes:
- s6 always uses fps-based retime for s2 and `libx264` encoding.
