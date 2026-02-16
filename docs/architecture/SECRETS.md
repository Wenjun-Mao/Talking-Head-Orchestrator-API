Secrets strategy (Docker + local dev)

Recommendation
- Use Docker secrets in production.
- Use a root .env for local development only.
- Keep real secrets out of git; commit only .env.example.

How it works with pydantic-settings
- Services read, in order:
  1) environment variables (`Sx_*`)
  2) `.env` file (local dev)
  3) Docker secrets mounted as files in `/run/secrets`
- With `secrets_dir="/run/secrets"`, secret files are unprefixed field names.

Prefix note
- Env vars use service prefixes (for example `S1_`, `S2_`, … `S8_`).
- Secret files are unprefixed (for example `/run/secrets/nocodb_api_key`).

Current shared secret files used by compose
- `/run/secrets/rabbitmq_url`
- `/run/secrets/nocodb_api_key`
- `/run/secrets/nocodb_base_url`
- `/run/secrets/video_parse_api_token`
- `/run/secrets/tts_api_token`
- `/run/secrets/chevereto_api_key`
- `/run/secrets/debug_log_payload`

Docker Compose example

services:
  s1-ingest-nocodb:
    build: ./services/s1-ingest-nocodb
    ports:
      - "7101:7101"
    environment:
      - S1_RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
    secrets:
      - nocodb_api_key
      - nocodb_base_url
    command: uvicorn ingest_nocodb.app:app --host 0.0.0.0 --port 7101

secrets:
  nocodb_api_key:
    file: ./secrets/nocodb_api_key
  nocodb_base_url:
    file: ./secrets/nocodb_base_url

Notes
- For RabbitMQ URL, env var is fine if it is not sensitive; otherwise put it in a secret file named rabbitmq_url.
- In Kubernetes, map secrets to `/run/secrets` or use env vars; `pydantic-settings` supports both.
- `s8-nocodb-updater` now primarily uses `table_id` from message payload; `S8_NOCODB_TABLE_ID` is optional fallback.
