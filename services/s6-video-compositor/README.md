Compose background video with avatar overlay, align lengths, then append guide video.

Dependencies: managed with uv via pyproject.toml.

Inputs:
- video_bg_path
- video_avatar_path
- video_guide_path
Outputs:
- video_final_path

Performance notes:
- s6 always uses fps-based retime for s2 and `libx264` encoding.
