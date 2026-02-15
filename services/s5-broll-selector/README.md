Current mode: pass-through (no B-roll selection yet).

Original intended behavior (kept as trace):
<!--
Select a random guide video for tail content.

Inputs:
- local video directory
Outputs:
- video_guide_path
-->

Dependencies: managed with uv via pyproject.toml.

Inputs:
- record_id
- title
- url
- content
- original_text
- douyin_download_url
- douyin_video_path
- tts_audio_path
- inference_video_path

Behavior:
- consumes from queue `s5-broll-selector`
- forwards the payload unchanged to `s6-video-compositor`

Outputs:
- unchanged payload for downstream service
