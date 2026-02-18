Quick service launch guide

Daily ops (quick links)
- Logging stack reproducibility runbook:
  - `docs/architecture/LOGGING_STACK_REPRO_RUNBOOK.md`
- Logging stack command cheatsheet (copy/paste up/down/wipe commands):
  - `docs/architecture/LOGGING_STACK_COMMANDS.md`

General
- Every service in `services/` is active and part of the current pipeline.
- Python services use `uv` with per-service `pyproject.toml`.
- Prefer Docker Compose for end-to-end runs; use local `uv run` only for targeted debugging.

Run full stack (recommended)
- From repo root:
  - `docker compose -f infra/docker-compose/docker-compose.yml up -d --build`
- Check logs:
  - `docker compose -f infra/docker-compose/docker-compose.yml logs -f --tail=100`

Run one service with rebuild
- Example (`s7-storage-uploader`):
  - `docker compose -f infra/docker-compose/docker-compose.yml up -d --build s7-storage-uploader`
  - `docker compose -f infra/docker-compose/docker-compose.yml logs --tail=100 s7-storage-uploader`

Run services locally with uv (per service)
- `s1-ingest-nocodb` (FastAPI):
  - `cd services/s1-ingest-nocodb`
  - `uv sync`
  - `uv run uvicorn ingest_nocodb.app:app --host 0.0.0.0 --port 7101`
- Workers (`s2` to `s8`):
  - `cd services/<service-name>`
  - `uv sync`
  - `uv run dramatiq <module>.worker`

Current pipeline
- `s1-ingest-nocodb` → `s2-download-mp4` → `s3-tts-voice` → `s4-inference-engine` → `s5-broll-selector` → `s6-video-compositor` → `s7-storage-uploader` → `s8-nocodb-updater`

Contract note
- `table_id` from the webhook is propagated end-to-end and used by `s8` at runtime to choose the NocoDB table.

Phase 2 verification checklist
- Rebuild and restart observability + workers (`s4` to `s8`) after logger/filter changes:
  - `docker compose -f infra/docker-compose/docker-compose.yml up -d --build s4-inference-engine s5-broll-selector s6-video-compositor s7-storage-uploader s8-nocodb-updater`
  - `docker compose -f infra/docker-compose/docker-compose.yml up -d --force-recreate vector-agent`
- Run one smoke webhook using Bruno payload (`docs/bruno/talking-head-api-local-test/local webhook real data.yml`) or equivalent JSON to `POST http://localhost:7101/webhook`.
- Verify local container flow by `record_id` across `s1` to `s8` with `docker logs`.
- Verify SigNoz ingestion freshness with ClickHouse:
  - `docker exec signoz-clickhouse clickhouse-client -q "SELECT fromUnixTimestamp64Nano(toInt64(max(timestamp))) FROM signoz_logs.logs_v2"`
  - `docker exec signoz-clickhouse clickhouse-client -q "SELECT resources_string['service.name'], count() FROM signoz_logs.logs_v2 WHERE timestamp > toUInt64(toUnixTimestamp(now() - INTERVAL 10 MINUTE) * 1000000000) GROUP BY resources_string['service.name'] ORDER BY resources_string['service.name']"`
