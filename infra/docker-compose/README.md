Local development compose files live here.

Current services
- RabbitMQ (broker)
- s1-ingest-nocodb
- s2-download-mp4
- s3-tts-voice
- s4-inference-engine
- s5-broll-selector
- s6-video-compositor
- s7-storage-uploader
- s8-nocodb-updater
- vector-agent (ships container logs to SigNoz OTLP endpoint)

Quick start
0) Start SigNoz first (from `infra/observability`):
	- `docker compose -p signoz -f ./signoz/docker/compose.yaml up -d --remove-orphans`
1) Create secret files under infra/docker-compose/secrets:
	- nocodb_api_key
	- nocodb_base_url
 	- rabbitmq_url
	- video_parse_api_token
	- tts_api_token
	- chevereto_api_key
	- debug_log_payload
2) Run from this folder:
	docker compose up -d --build

Run a single service (example)
- `docker compose up -d --build s7-storage-uploader`
- `docker compose logs --tail=100 s7-storage-uploader`

How Docker secrets work (Compose)
- Secrets are files mounted at /run/secrets/<name> inside the container.
- This repo reads secrets via pydantic-settings with secrets_dir=/run/secrets.
- Each secret file should contain only the value (no quotes, no key names).
- Secret files are unprefixed (e.g., nocodb_api_key), while env vars use service prefixes (S1_...S8_).

Example
- /run/secrets/nocodb_api_key contains: abcd1234
- /run/secrets/nocodb_base_url contains: https://nocodb.example.com

Notes
- Environment variables still work and can override secrets if set.
- `s8` table selection comes from message `table_id`.
- `vector-agent` forwards logs to `http://signoz-otel-collector:4318/v1/logs` over shared Docker network `signoz-net`.
- `vector-agent` is a single host-level collector for this compose project (no per-service Vector sidecars).
- Services log to stdout/stderr; they do not share an application log directory in this setup.
