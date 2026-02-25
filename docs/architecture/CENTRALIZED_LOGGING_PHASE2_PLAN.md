Centralized logging Phase 2 plan (approved)

Status
- Approved direction for this project pilot.
- Client side: Loguru + Vector.
- Server side: SigNoz.
- Reproducibility runbook: `docs/architecture/LOGGING_STACK_REPRO_RUNBOOK.md`.

Goals
- Standardize structured logs across all services with one shared logging setup.
- Ship logs reliably to a central backend for search, dashboards, and alerting.
- Keep rollout low-risk and incremental for the current project first.

Scope decisions (confirmed)
- Retention target: 7 days hot, 30-90 days warm, optional archive later.
- PII/security/cost guardrails are out of scope for this internal local phase.
- Alerting: implement a standard baseline set for worker pipelines.

Where SigNoz should live
- Do NOT place SigNoz under `services/`.
- Place observability infrastructure under `infra/observability/`.
- Keep it as a separate compose stack from the app pipeline compose:
  - app pipeline: `infra/docker-compose/compose.yaml`
  - observability stack: `infra/observability/signoz/docker/compose.yaml`

Why separate stack (recommended)
- Clear ownership boundary: app services vs platform tooling.
- Easier lifecycle management (start/stop/rebuild observability independently).
- Safer experiments without coupling changes to core service compose.

Can SigNoz run as "another container"?
- Yes. For this pilot, run SigNoz as additional containers in the same host using a dedicated compose project under `infra/observability`.
- Each project-local Vector can export to SigNoz OTLP endpoint over the published collector port (`4318`).

Phase relationship with shared utilities
- This plan complements `docs/architecture/SHARED_UTILS_PHASE2_PLAN.md`; it does not replace it.
- Shared-utils Phase 2 solves package/runtime sharing (`packages/core`) via Docker build-context wiring.
- Logging centralization should use that same path once available:
  - create shared module in `packages/core` (for example `core/logging.py`),
  - all services import one `configure_logging(...)` helper,
  - remove duplicated local logging setup.
- Recommended execution order:
  1) Shared-utils Phase 2a pilot (`s1`) to prove import/build model.
  2) Introduce shared logging helper in `packages/core`.
  3) Roll out to `s2..s8`.

Target architecture for this repo
- Service process emits structured JSON logs with Loguru.
- Log format includes: `timestamp`, `level`, `service`, `stage`, `record_id`, `table_id`, `queue`, `event`, `message`, `exception`.
- Vector agent tails container logs and forwards via OTLP to SigNoz.
- SigNoz handles storage, querying, dashboards, and alert rules.

Standard logging contract (minimum)
- Required fields for job logs: `service`, `record_id`, `table_id`, `event`.
- Required fields for failures: `error_type`, `error_message`, `stage`.
- Keep payload bodies out of info logs; continue truncation policy for debug-only text fields.

Rollout plan

Phase 2.1 — Infra + plumbing (pilot)
- Add `infra/observability/` with SigNoz compose and runbook.
- Add Vector service in app compose OR sidecar compose (one Vector per host for this project).
- Route Vector -> SigNoz OTLP.

Phase 2.2 — Shared logging config
- Add shared logger setup in `packages/core`.
- Migrate `s1` to shared setup first.
- Validate field consistency and queryability in SigNoz.

Phase 2.3 — Service rollout
- Migrate `s2..s8` to shared logging setup.
- Remove duplicated per-service logging bootstraps.
- Verify end-to-end traceability by `record_id` across all stages.

Phase 2.4 — Alerting baseline
- Configure these default alerts in SigNoz:
  1) Error spike: `ERROR` count above threshold per service over 5m.
  2) Stalled pipeline: no `s8` success events for N minutes.
  3) Queue lag proxy: sustained high queue depth or delayed processing signal.
  4) Worker crash loop: repeated service restarts in a short window.

Suggested initial thresholds (tune after 1 week)
- Error spike: > 20 errors / 5m per service.
- Stalled pipeline: no successful `s8` updates for 15m during active window.
- Worker crash loop: >= 3 restarts / 10m.

Retention implementation notes
- Hot retention: 7 days in SigNoz primary store.
- Warm retention: 30-90 days with reduced-cost tier/config per SigNoz storage backend.
- Archive: optional future export (object storage) if needed.

Success criteria
- All services emit standardized structured logs.
- A single query by `record_id` shows full `s1 -> s8` path.
- Baseline alerts are active and produce actionable notifications.
- No service keeps bespoke logging config after migration completion.

Out-of-scope for this phase
- Multi-tenant access control, strict PII governance, and cost optimization automation.
- Cross-project/global observability platform hardening.
