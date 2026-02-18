# s4-inference-engine (SoulX-FlashHead)

This service runs SoulX-FlashHead inference as a Dramatiq worker.

Detailed setup
- See `SOULX_FLASHHEAD_INTEGRATION.md` for full vendor/model/flash-attn setup and Ubuntu NVIDIA container runtime requirements.

## What it does
- Preloads SoulX pipeline once at worker startup.
- Uses a fixed condition image from `data/imgs/girl.png` (configurable).
- Uses TTS audio from s3 message payload for per-job generation.
- Enqueues generated mp4 to s5 while preserving upstream metadata (`record_id`, `table_id`, source fields).

## Local assets (not tracked by git)
Place model folders under:
- `services/s4-inference-engine/vendor/SoulX-FlashHead/models/SoulX-FlashHead-1_3B`
- `services/s4-inference-engine/vendor/SoulX-FlashHead/models/wav2vec2-base-960h`

Place condition image:
- `data/imgs/girl.png`

## Compose env (s4)
Defaults in compose:
- `S4_FLASHHEAD_CKPT_DIR=/models/SoulX-FlashHead-1_3B`
- `S4_WAV2VEC_DIR=/models/wav2vec2-base-960h`
- `S4_MODEL_TYPE=lite`
- `S4_COND_IMAGE_PATH=/data/imgs/girl.png`
- `S4_AUDIO_ENCODE_MODE=stream`

## Run
```bash
docker compose -f infra/docker-compose/compose.yaml up -d --build s4-inference-engine
```

## Notes
- Upstream SoulX repo is vendored at `services/s4-inference-engine/vendor/SoulX-FlashHead`.
- We do not modify upstream SoulX files; integration lives in `src/inference_engine/soulx_runtime.py`.
- Optional SageAttention is intentionally not installed.
- `flash_attn` install is attempted in Docker build; on slim/non-devel images without `nvcc`, build continues without it.
