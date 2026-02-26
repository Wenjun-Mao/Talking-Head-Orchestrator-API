Logging stack reproducibility runbook (project pilot)

Purpose
- Capture the exact working setup for this repo so future implementations avoid prior trial-and-error.
- Document not only steps, but the key decisions and why they were made.

Final topology (working)
- App services emit JSON logs to stdout (Loguru).
- One host-level `vector-agent` tails Docker logs for all services.
- Vector sends logs to SigNoz OTLP HTTP receiver (endpoint configured via `secrets/signoz_otlp_http_url`).
- SigNoz stack lives in a separate repo: https://github.com/Wenjun-Mao/signoz-stack

Noise exclusion policy (current)
- Vector excludes infrastructure noise before shipping to SigNoz.
- Excluded sources:
  - RabbitMQ logs (`rabbitmq`).
  - Vector self-logs (`vector-agent`).
  - SigNoz stack logs (compose project `signoz`, including `signoz`, `otel-collector`, `clickhouse`, `zookeeper`, schema migrators).
- Intent: keep dashboards/search focused on pipeline services (`s1..s8`) and reduce ingestion noise.

Why these choices
- Single Vector agent (not one per service): lower operational overhead and simpler rollout.
- SigNoz extracted to its own repo: clean ownership, shared across projects.
- Per-project Vector points to SigNoz via configurable OTLP endpoint (`secrets/signoz_otlp_http_url`).
- SigNoz collector started with static config command only: avoids unstable behavior encountered with manager/opamp startup mode in this local setup.

Prerequisites
- Docker Desktop running.

Step 1: Start SigNoz
- From the signoz-stack repo (https://github.com/Wenjun-Mao/signoz-stack):
  - `docker compose -p signoz -f docker/compose.yaml up -d --remove-orphans`
- UI:
  - `http://localhost:8080`

Step 2: Start app stack
- From `infra/docker-compose`:
  - `docker compose up -d --build`
- `vector-agent` is part of this compose and sends to SigNoz collector over the published OTLP endpoint.

Step 3: Validate health quickly
- SigNoz containers:
  - `docker ps --format "table {{.Names}}\t{{.Status}}" | Select-String "signoz|NAMES"`
- Vector ingestion errors (should be empty):
  - `docker compose -f infra/docker-compose/compose.yaml logs --since=2m vector-agent | Select-String "Bad Request|HTTP error|Events dropped|Not retriable|ERROR|error"`
- Recent logs ingested in ClickHouse:
  - `docker exec signoz-clickhouse clickhouse-client --query "SELECT count() FROM signoz_logs.distributed_logs_v2 WHERE timestamp > now() - INTERVAL 1 MINUTE"`

Command quick reference
- Copy/paste operational commands are in:
  - `docs/architecture/LOGGING_STACK_COMMANDS.md`

Known-good expected behavior
- `signoz-init-clickhouse`, `schema-migrator-sync`, and `schema-migrator-async` are one-shot jobs and should exit with code 0.
- `signoz`, `signoz-otel-collector`, `signoz-clickhouse`, `signoz-zookeeper-1` should stay running.

Troubleshooting shortcuts
- If Vector shows connection failures to collector:
  - ensure SigNoz is up and collector HTTP receiver is published on `4318`.
- If collector errors mention connection/receiver issues:
  - restart SigNoz from signoz-stack repo: `docker compose -p signoz -f docker/compose.yaml up -d --remove-orphans`.
  - check collector startup logs contain both:
    - `Starting GRPC server ... [::]:4317`
    - `Starting HTTP server ... [::]:4318`

What was intentionally removed
- Temporary `otel-gateway` bridge service used during debugging.
- Full cloned SigNoz repository under `infra/observability/vendor/signoz`.
