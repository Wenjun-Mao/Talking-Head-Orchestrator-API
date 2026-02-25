Observability infrastructure

Layout
- `signoz/`  — Shared SigNoz stack (planned for extraction to its own repo).
- Vector config has moved to `infra/vector/`.

SigNoz (shared, standalone)
- Compose: `signoz/docker/compose.yaml`
- Start: `docker compose -p signoz -f signoz/docker/compose.yaml up -d --remove-orphans`
- UI: `http://localhost:8080`
- Published OTLP ports: 4317 (gRPC), 4318 (HTTP), 13133 (health)
- Onboarding guide: `signoz/docs/ONBOARDING.md`
- Repo-level readme: `signoz/README.md`

Vector (per-project, lives in app stack)
- Config: `infra/vector/vector.yaml`
- Documentation: `infra/vector/README.md`
- Runs inside each project's app compose, not here.

Multi-project model
- SigNoz is shared infrastructure — accepts telemetry from any project on localhost, LAN, or via nginx + SSL.
- Each project runs its own `vector-agent` and points to SigNoz OTLP endpoint.

Reference
- Architecture: `docs/architecture/CENTRALIZED_LOGGING_PHASE2_PLAN.md`
- Commands: `docs/architecture/LOGGING_STACK_COMMANDS.md`
- Runbook: `docs/architecture/LOGGING_STACK_REPRO_RUNBOOK.md`

