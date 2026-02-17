Observability stack (local/internal)

Purpose
- Host centralized logging infrastructure separately from application services.
- Current approved pilot stack: SigNoz backend + Vector shipper integration from app services.

Why this location
- Keep `services/` for business pipeline workers only.
- Keep infra/platform tooling under `infra/` for clean ownership and lifecycle.

Recommended compose layout
- Application pipeline compose: `infra/docker-compose/docker-compose.yml`
- Observability compose: `infra/observability/docker-compose.yml`

Operational model
- Bring up observability stack first.
- Bring up application stack second.
- Vector forwards logs to SigNoz OTLP endpoint over Docker networking.

Next implementation step
- Add `infra/observability/docker-compose.yml` for SigNoz and document exact startup commands.
- Then wire Vector endpoint/env in app compose/services.

Reference
- Architecture decision and rollout: `docs/architecture/CENTRALIZED_LOGGING_PHASE2_PLAN.md`
