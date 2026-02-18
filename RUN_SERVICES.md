Quick service launch guide

Start everything (top 2 commands)
- Full service stack:
  - `docker compose -f infra/docker-compose/compose.yaml up -d --build`
- Full SigNoz stack:
  - `docker compose -p signoz -f infra/observability/signoz/docker/compose.yaml up -d --remove-orphans`

Recommended startup order
- Start SigNoz first, then start the service stack.

Daily operations
- Tail all service logs:
  - `docker compose -f infra/docker-compose/compose.yaml logs -f --tail=100`
- Show service status:
  - `docker compose -f infra/docker-compose/compose.yaml ps`
- Restart one service with rebuild (example `s7-storage-uploader`):
  - `docker compose -f infra/docker-compose/compose.yaml up -d --build s7-storage-uploader`

Stop operations
- Stop service stack:
  - `docker compose -f infra/docker-compose/compose.yaml down`
- Stop SigNoz stack:
  - `docker compose -p signoz -f infra/observability/signoz/docker/compose.yaml down`

Smoke check (webhook + observability)
- Send webhook using Bruno payload:
  - `docs/bruno/talking-head-api-local-test/local webhook real data.yml`
- Verify log freshness in SigNoz (ClickHouse):
  - `docker exec signoz-clickhouse clickhouse-client -q "SELECT fromUnixTimestamp64Nano(toInt64(max(timestamp))) FROM signoz_logs.logs_v2"`
- Verify service coverage in recent logs:
  - `docker exec signoz-clickhouse clickhouse-client -q "SELECT resources_string['service.name'], count() FROM signoz_logs.logs_v2 WHERE timestamp > toUInt64(toUnixTimestamp(now() - INTERVAL 10 MINUTE) * 1000000000) GROUP BY resources_string['service.name'] ORDER BY resources_string['service.name']"`

Current pipeline
- `s1-ingest-nocodb` → `s2-download-mp4` → `s3-tts-voice` → `s4-inference-engine` → `s5-broll-selector` → `s6-video-compositor` → `s7-storage-uploader` → `s8-nocodb-updater`

Contract note
- `table_id` from the webhook is propagated end-to-end and used by `s8` at runtime to choose the NocoDB table.
