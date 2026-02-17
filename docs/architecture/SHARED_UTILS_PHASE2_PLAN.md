Shared utilities Phase 2 plan

Goal
- Enable true shared runtime helpers (for example debug payload truncation helpers) in `packages/core`.
- Keep service images reproducible and avoid ad-hoc cross-service imports.

Current blocker
- Every service Dockerfile currently builds from a service-local context (`services/<service>`).
- That context cannot see repo-level `packages/*` during image build.
- So importing from `packages/core` at runtime is brittle unless build context/dependency wiring is changed.

Recommended architecture decision
- Keep `packages/` and make it real (recommended), rather than deleting it.
- Treat `packages/core` as an installable Python package used by services.

Option A (recommended): root build context + service Dockerfile paths
- In compose, for each service:
  - set `build.context` to repo root (`../..` from `infra/docker-compose`)
  - set `build.dockerfile` to the service Dockerfile path (e.g. `services/s1-ingest-nocodb/Dockerfile`)
- Update service Dockerfiles to copy both:
  - service source (`services/<name>/src`, `services/<name>/pyproject.toml`)
  - shared package (`packages/core`)
- Install `packages/core` into the venv during image build (`uv pip install` editable or wheel).

Option B (alternate): publish internal package artifact
- Build/package `packages/core` in CI and install by version in each service.
- Cleaner release boundaries, but more CI/release overhead right now.

Implementation details (Option A)

1) Package `core` properly
- Ensure `packages/core` has:
  - `pyproject.toml` with package metadata
  - importable module path under `packages/core/`
- Add utility module, for example:
  - `packages/core/core/logging_payload.py`
  - functions such as:
    - `truncate_text(value: str, max_chars: int = 30) -> str`
    - `truncate_payload_text_fields(payload: Any, fields: set[str], max_chars: int = 30) -> Any`

2) Update each service pyproject dependency
- Add a dependency on `core` in service `pyproject.toml` (local path style if using root context build) OR install via `uv pip install /app/packages/core` in Dockerfile.

3) Update Dockerfiles (service template)
- Before `uv sync`, copy:
  - service `pyproject.toml`
  - service `src`
  - `packages/core`
- Install sequence example:
  - `uv sync --no-dev`
  - `uv pip install --python /app/.venv/bin/python /app/packages/core`
- Keep cache-friendly copy order (metadata first, source later where possible).

4) Update compose build definitions
- Example for one service:
  - `context: ../..`
  - `dockerfile: services/s1-ingest-nocodb/Dockerfile`
- Roll this through all services that import shared utilities.

5) Migrate duplicated helpers
- Replace local `_truncate_text` and `_truncate_payload_text_fields` in:
  - `services/s1-ingest-nocodb/src/ingest_nocodb/app.py`
  - `services/s2-download-mp4/src/download_mp4/worker.py`
  - `services/s3-tts-voice/src/tts_voice/worker.py`
- Import from `core.logging_payload` instead.

6) Validation checklist
- Build + run each touched service container.
- Verify imports resolve inside containers.
- Smoke test webhook path (`s1`) and first jobs through `s2/s3`.
- Confirm log output truncation behavior unchanged.

7) Rollout strategy
- Phase 2a: wire one pilot service (`s1`) to `packages/core`.
- Phase 2b: wire `s2` and `s3`.
- Phase 2c: migrate remaining services only if shared helpers are needed.

8) Rollback plan
- If build/import issues appear, revert service to local helper implementation and previous compose build context.
- No data/schema migration required; rollback is code/config only.

Do we still need `packages/`?
- Yes, if we adopt Option A or B.
- If we decide never to share runtime code, `packages/` can be removed later; today that would trade maintainability for short-term simplicity.

Decision recommendation
- Approve Option A and execute Phase 2a (pilot on `s1`) first.
- This gives a low-risk proof before touching all services.

Pilot status update (implemented)
- `s1-ingest-nocodb` now builds with root Docker context and explicit Dockerfile path from compose.
- `packages/core` is installed into `s1` image during build.
- `s1` imports shared logger bootstrap from `core.logging`.

Relationship to centralized logging Phase 2
- This plan is a prerequisite/enabler for `docs/architecture/CENTRALIZED_LOGGING_PHASE2_PLAN.md`.
- Shared utilities provide the mechanism to keep one logging configuration in `packages/core` and import it from all services.
- Recommended order:
  1) complete shared-utils pilot (`s1`) and confirm Docker build wiring,
  2) add shared logging helper in `packages/core`,
  3) migrate service logging setup incrementally.
