Ingest NocoDB webhook rows and enqueue pipeline jobs.

Dependencies: managed with uv via pyproject.toml.

Endpoint
- POST /webhook (module path: ingest_nocodb.app:app)

Inputs:
- NocoDB webhook payload (`data.table_id`, `data.rows[*]`)
Outputs:
- Enqueue message to `s2_download_mp4.process`

Validation
- Requires non-empty `data.table_id`
- Requires per row: positive `Id` and non-empty `url`, `content`
- Only `Id`, `url`, `content` are modeled in `NocoDbRow`; all other row fields are accepted via `extra=allow` and ignored by the pipeline
- Logs payload validation errors server-side via the request validation handler
- Returns generic `Invalid webhook payload.` for invalid requests

Message out (to s2)
- `record_id`
- `table_id`
- `url`
- `content`
