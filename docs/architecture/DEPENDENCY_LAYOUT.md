Dependency layout

- Each service owns its own dependencies and should remain independently deployable.
- Modern services use uv with per-service pyproject.toml and uv.lock.
- The inference-engine (s4) currently maintains its own legacy requirements.
- Shared code lives in packages/* and is imported via editable installs or built artifacts in deployment.
- Do not install dependencies locally; only update dependency files.

Notes
- Keep root-level requirements.txt absent to avoid conflating service deps.
