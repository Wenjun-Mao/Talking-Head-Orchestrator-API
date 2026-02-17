Core shared models and job contracts.

Responsibilities:
- Job IDs and status enums
- Shared config loading
- Structured logging conventions

Current shared runtime modules
- `core.logging`
	- `configure_service_logger(service_name: str, debug: bool = False)`
	- `get_logger(service_name: str | None = None)`

Usage pattern
- Configure once at service startup/lifespan.
- Use `get_logger("<service-name>")` in modules to emit structured JSON logs with common `service` field.
