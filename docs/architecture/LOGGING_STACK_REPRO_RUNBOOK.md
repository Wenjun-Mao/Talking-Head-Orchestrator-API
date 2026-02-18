Logging stack reproducibility runbook (project pilot)

Purpose
- Capture the exact working setup for this repo so future implementations avoid prior trial-and-error.
- Document not only steps, but the key decisions and why they were made.

Final topology (working)
- App services emit JSON logs to stdout (Loguru).
- One host-level `vector-agent` tails Docker logs for all services.
- Vector sends logs to SigNoz OTLP HTTP receiver at `http://signoz-otel-collector:4318/v1/logs`.
- SigNoz stack runs from local bundled files in `infra/observability/signoz/*`.

Noise exclusion policy (current)
- Vector excludes infrastructure noise before shipping to SigNoz.
- Excluded sources:
  - RabbitMQ logs (`rabbitmq`).
  - Vector self-logs (`vector-agent`).
  - SigNoz stack logs (compose project `signoz`, including `signoz`, `otel-collector`, `clickhouse`, `zookeeper`, schema migrators).
- Intent: keep dashboards/search focused on pipeline services (`s1..s8`) and reduce ingestion noise.

Why these choices
- Single Vector agent (not one per service): lower operational overhead and simpler rollout.
- Separate infra location (`infra/observability`): clean boundary from business services.
- Local bundled SigNoz deploy files (not full cloned repo): smaller footprint, stable/pinned config, fewer Windows path issues.
- Vector on `signoz-net` only: avoids intermittent DNS resolution issues seen with dual-network attachment.
- SigNoz collector started with static config command only: avoids unstable behavior encountered with manager/opamp startup mode in this local setup.

Prerequisites
- Docker Desktop running.
- `signoz-net` external network is created by SigNoz compose startup.

Step 1: Start SigNoz
- From `infra/observability`:
  - `./bootstrap-signoz.ps1`
- Equivalent manual command:
  - `docker compose -p signoz -f ./signoz/docker/compose.yaml up -d --remove-orphans`
- UI:
  - `http://localhost:8080`

Step 2: Start app + Vector
- From `infra/docker-compose`:
  - `docker compose up -d --build`
- `vector-agent` is part of this compose and sends to SigNoz collector over `signoz-net`.

Step 3: Validate health quickly
- SigNoz containers:
  - `docker ps --format "table {{.Names}}\t{{.Status}}" | Select-String "signoz|NAMES"`
- Vector ingestion errors (should be empty):
  - `docker compose logs --since=2m vector-agent | Select-String "Bad Request|HTTP error|Events dropped|Not retriable|ERROR|error"`
- Recent logs ingested in ClickHouse:
  - `docker exec signoz-clickhouse clickhouse-client --query "SELECT count() FROM signoz_logs.distributed_logs_v2 WHERE timestamp > now() - INTERVAL 1 MINUTE"`

Command quick reference
- Copy/paste operational commands are in:
  - `docs/architecture/LOGGING_STACK_COMMANDS.md`

Known-good expected behavior
- `signoz-init-clickhouse`, `schema-migrator-sync`, and `schema-migrator-async` are one-shot jobs and should exit with code 0.
- `signoz`, `signoz-otel-collector`, `signoz-clickhouse`, `signoz-zookeeper-1` should stay running.

Troubleshooting shortcuts
- If Vector shows DNS lookup failures for `signoz-otel-collector`:
  - ensure `vector-agent` is attached to `signoz-net`.
- If collector errors mention connection/receiver issues:
  - restart SigNoz via `./bootstrap-signoz.ps1`.
  - check collector startup logs contain both:
    - `Starting GRPC server ... [::]:4317`
    - `Starting HTTP server ... [::]:4318`

What was intentionally removed
- Temporary `otel-gateway` bridge service used during debugging.
- Full cloned SigNoz repository under `infra/observability/vendor/signoz`.
