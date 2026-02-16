Upload final video to storage and return URL.

Dependencies: managed with uv via pyproject.toml.

Message in
- `record_id`
- `table_id`
- `composited_video_path`

Message out (to s8)
- `record_id`
- `table_id`
- `public_mp4_url`

Chevereto API (v1.1):
- Upload endpoint: `/api/1/upload`
- Auth: `X-API-Key` header
- Upload params used:
	- `source` (multipart file)
	- `format=json`
	- `expiration` (default `P3D`)
	- `album_id` (optional but recommended)

Configuration notes:
- `S7_CHEVERETO_BASE_URL` defaults to `https://imagor.wanyouwan.cn`.
- `S7_CHEVERETO_API_KEY` is read from docker secret `chevereto_api_key`.
- Upload title is generated internally as `record-<record_id>`.
- To force uploads into album "talking head", set `S7_CHEVERETO_ALBUM_ID` to that album id.
- `S7_CHEVERETO_ALBUM_NAME` is only informational; API upload assignment uses `album_id`.
- s7 enqueues `(record_id, table_id, public_mp4_url)` to s8.
