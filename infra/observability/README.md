Observability stack (local/internal)

Purpose
- Host centralized logging infrastructure separately from application services.
- Current approved pilot stack: SigNoz backend + Vector shipper integration from app services.

Why this location
- Keep `services/` for business pipeline workers only.
- Keep infra/platform tooling under `infra/` for clean ownership and lifecycle.

Recommended compose layout
- Application pipeline compose: `infra/docker-compose/compose.yaml`
- SigNoz compose: `infra/observability/signoz/docker/compose.yaml`

SigNoz bootstrap (official upstream)
1) Start stack:
  - `docker compose -p signoz -f ./signoz/docker/compose.yaml up -d --remove-orphans`
2) Open UI:
	- `http://localhost:8080`

Bundled SigNoz files in this repo
- Minimal pinned deploy bundle lives under:
  - `infra/observability/signoz/docker`
  - `infra/observability/signoz/common`
- This avoids keeping a full cloned SigNoz source repository in `vendor/`.

Vector wiring in this repo
- `vector-agent` is wired in this project's app stack (`infra/docker-compose/compose.yaml`).
- It tails Docker logs and forwards OTLP logs to:
  - `http://signoz-otel-collector:4318/v1/logs`
- Config file:
  - `infra/observability/vector/vector.yaml`

Multi-project model
- SigNoz is shared infrastructure.
- Each project runs its own `vector-agent` in its own stack and points to this SigNoz collector.

Operational model
- Bring up observability stack first.
- Bring up application stack second.
- Vector forwards logs to SigNoz OTLP endpoint over Docker networking.

Next implementation step
- Add shared logging bootstrap in `packages/core` and migrate `s1` to it first.
- Validate that `record_id`/`table_id` queries work end-to-end in SigNoz.

Reference
- Architecture decision and rollout: `docs/architecture/CENTRALIZED_LOGGING_PHASE2_PLAN.md`
