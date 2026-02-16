Ingest NocoDB webhook rows and enqueue pipeline jobs.

Dependencies: managed with uv via pyproject.toml.

Endpoint
- POST /webhook (module path: ingest_nocodb.app:app)

Inputs:
- NocoDB webhook payload (`data.table_id`, `data.rows[*]`)
Outputs:
- Enqueue message to `s2_download_mp4.process`

Validation
- Requires per row: `Title`, `url`, `content`, `originaltext`
- Returns 400 when rows are empty or mandatory fields are missing

Message out (to s2)
- `record_id`
- `table_id`
- `title`
- `url`
- `content`
- `original_text`
