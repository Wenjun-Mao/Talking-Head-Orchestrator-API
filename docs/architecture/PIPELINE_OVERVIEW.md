Pipeline overview

1. Ingest webhook rows from NocoDB and enqueue jobs. (`s1-ingest-nocodb`)
2. Parse source URL and download background MP4. (`s2-download-mp4`)
3. Generate TTS audio from row content. (`s3-tts-voice`)
4. Run SoulX-FlashHead inference to generate avatar video. (`s4-inference-engine`)
5. Pass payload through (no B-roll selection yet). (`s5-broll-selector`)
6. Composite background + avatar and align duration with TTS audio/video timing. (`s6-video-compositor`)
7. Upload final MP4 to Chevereto and emit public URL. (`s7-storage-uploader`)
8. Update NocoDB `chengpinurl` for the row. (`s8-nocodb-updater`)

Queueing
- RabbitMQ broker with Dramatiq workers.
- `record_id` and webhook `table_id` are propagated through all stages.
- `s8` uses runtime `table_id` from message payload.

Implementation notes
- For full `s4` setup (vendor source, models, FlashAttention wheel, Ubuntu NVIDIA toolkit), see `services/s4-inference-engine/SOULX_FLASHHEAD_INTEGRATION.md`.

Message contract (stage by stage)

| Stage | Message in | Message out |
|---|---|---|
| `s1-ingest-nocodb` | NocoDB webhook payload (`data.table_id`, `data.rows[*]`) | `record_id, table_id, url, content` |
| `s2-download-mp4` | `record_id, table_id, url, content` | `record_id, table_id, content, douyin_video_path` |
| `s3-tts-voice` | `record_id, table_id, content, douyin_video_path` | `record_id, table_id, douyin_video_path, tts_audio_path` |
| `s4-inference-engine` | `record_id, table_id, douyin_video_path, tts_audio_path` | `record_id, table_id, douyin_video_path, tts_audio_path, inference_video_path` |
| `s5-broll-selector` | `record_id, table_id, douyin_video_path, tts_audio_path, inference_video_path` | unchanged pass-through payload |
| `s6-video-compositor` | `record_id, table_id, douyin_video_path, tts_audio_path, inference_video_path` | `record_id, table_id, composited_video_path` |
| `s7-storage-uploader` | `record_id, table_id, composited_video_path` | `record_id, table_id, public_mp4_url` |
| `s8-nocodb-updater` | `record_id, table_id, public_mp4_url` | NocoDB row patched (`chengpinurl`) |
