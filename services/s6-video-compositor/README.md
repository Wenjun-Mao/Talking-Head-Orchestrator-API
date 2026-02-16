Compose background video with avatar overlay and align durations.

Dependencies: managed with uv via pyproject.toml.

Message in
- `record_id`
- `table_id`
- `title`
- `url`
- `content`
- `original_text`
- `douyin_download_url`
- `douyin_video_path`
- `tts_audio_path`
- `inference_video_path`

Message out
- all input fields above
- `composited_video_path`

Performance notes:
- s6 always uses fps-based retime for s2 and `libx264` encoding.
