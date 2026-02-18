Logging stack command cheatsheet (copy/paste)

Purpose
- Fast, low-error startup/shutdown commands for app stack + SigNoz stack.
- Includes both safe restart (keep history) and full reset (wipe previous logs/data).

Conventions
- Run from repository root unless noted.
- SigNoz compose file: `infra/observability/signoz/docker/docker-compose.yaml`
- App compose file: `infra/docker-compose/docker-compose.yml`
- SigNoz compose project name is fixed as `signoz`.

Start (keep existing logs/data)
1) Start SigNoz first:
- `docker compose -p signoz -f infra/observability/signoz/docker/docker-compose.yaml up -d --remove-orphans`

2) Start app stack:
- `docker compose -f infra/docker-compose/docker-compose.yml up -d --build`

Stop (keep existing logs/data)
1) Stop app stack:
- `docker compose -f infra/docker-compose/docker-compose.yml down`

2) Stop SigNoz stack (volumes preserved):
- `docker compose -p signoz -f infra/observability/signoz/docker/docker-compose.yaml down`

RabbitMQ-only restart note
- If you recreate only RabbitMQ, some workers may reconnect before their queues are re-declared and emit temporary `queue not_found` churn.
- Prefer restarting app workers together after RabbitMQ recreation:
  - `docker compose -f infra/docker-compose/docker-compose.yml up -d --force-recreate rabbitmq s1-ingest-nocodb s2-download-mp4 s3-tts-voice s4-inference-engine s5-broll-selector s6-video-compositor s7-storage-uploader s8-nocodb-updater`

Full reset (wipe previous logs/data)
Warning
- This permanently removes existing SigNoz history.
- Use only when you intentionally want a clean observability state.

1) Stop app stack:
- `docker compose -f infra/docker-compose/docker-compose.yml down`

2) Stop SigNoz and delete its volumes:
- `docker compose -p signoz -f infra/observability/signoz/docker/docker-compose.yaml down -v`

3) (Optional) remove Vector local disk buffer volume:
- `docker compose -f infra/docker-compose/docker-compose.yml down -v`

4) Start fresh:
- `docker compose -p signoz -f infra/observability/signoz/docker/docker-compose.yaml up -d --remove-orphans`
- `docker compose -f infra/docker-compose/docker-compose.yml up -d --build`

Health checks
- SigNoz UI: `http://localhost:8080`
- SigNoz containers:
  - `docker ps --format "table {{.Names}}\t{{.Status}}" | Select-String "signoz|NAMES"`
- App containers:
  - `docker compose -f infra/docker-compose/docker-compose.yml ps`
- Vector recent errors:
  - `docker compose -f infra/docker-compose/docker-compose.yml logs --since=2m vector-agent | Select-String "Bad Request|HTTP error|Events dropped|Not retriable|ERROR|error"`

Where SigNoz data is stored
- `signoz-clickhouse` (log/trace/metric data)
- `signoz-sqlite` (SigNoz app metadata)
- `signoz-zookeeper-1` (zookeeper state)

Inspect volume mountpoints
- `docker volume inspect signoz-clickhouse signoz-sqlite signoz-zookeeper-1`
