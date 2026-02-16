Dependency layout

- Each service owns its own dependencies and should remain independently deployable.
- Modern services use uv with per-service pyproject.toml and uv.lock.
- `s4-inference-engine` also uses a service-local `pyproject.toml` (no root dependency coupling).
- Shared code lives in packages/* and is imported via editable installs or built artifacts in deployment.
- Do not install dependencies locally; only update dependency files.

Notes
- Keep root-level requirements.txt absent to avoid conflating service deps.
