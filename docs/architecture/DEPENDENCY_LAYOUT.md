Dependency layout

- Each service owns its own dependencies and should remain independently deployable.
- Modern services use uv with per-service pyproject.toml and uv.lock.
- `s4-inference-engine` also uses a service-local `pyproject.toml` (no root dependency coupling).
- Shared code lives in packages/* and is imported via editable installs or built artifacts in deployment.
- Do not install dependencies locally; only update dependency files.

Current shared-runtime wiring
- `packages/core` is installed into `s1` and `s3` to `s8` container images.
- `s4` to `s8` Docker builds now use repo-root build context (`infra/docker-compose/docker-compose.yml`) so `packages/core` can be copied during image build.
- Root `.dockerignore` limits context transfer to `services/**` and `packages/**` (while excluding large runtime data and model artifact directories).

Notes
- Keep root-level requirements.txt absent to avoid conflating service deps.
- Detailed migration blueprint: `docs/architecture/SHARED_UTILS_PHASE2_PLAN.md`.
- Centralized logging rollout blueprint: `docs/architecture/CENTRALIZED_LOGGING_PHASE2_PLAN.md`.
