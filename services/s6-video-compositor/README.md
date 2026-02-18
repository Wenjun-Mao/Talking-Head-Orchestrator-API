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

Output-size safety knobs:
- `S6_TARGET_TOTAL_BITRATE_MBPS` (default `0.6`): fallback total bitrate (video + audio) used after an oversized first encode.
- `S6_MIN_TOTAL_BITRATE_MBPS` (default `0.35`): lowest total bitrate allowed before failing.
- `S6_BITRATE_STEP_KBPS` (default `50`): bitrate reduction step between retries.
- `S6_AUDIO_BITRATE_KBPS` (default `96`): AAC audio bitrate.
- `S6_MAX_OUTPUT_SIZE_MB` (default `30`): hard output size guardrail.

Adaptive behavior:
- First encode uses the original `s2` source total bitrate.
- If output is larger than `S6_MAX_OUTPUT_SIZE_MB`, `s6` re-encodes at fallback bitrate, then steps down until within limit or minimum bitrate is reached.
