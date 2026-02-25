# SigNoz Shared Observability Stack

Standalone SigNoz deployment for centralized logging, tracing, and metrics across multiple projects.

## Quick start

```bash
docker compose -p signoz -f docker/compose.yaml up -d --remove-orphans
```

Open UI at **http://localhost:8080**

## Published ports

| Port  | Protocol   | Purpose                          |
|-------|------------|----------------------------------|
| 8080  | HTTP       | SigNoz web dashboard             |
| 4317  | gRPC       | OTLP receiver (traces/metrics/logs) |
| 4318  | HTTP       | OTLP receiver (traces/metrics/logs) |
| 13133 | HTTP       | Collector health check (`/`)     |

All ports bind to `0.0.0.0` — reachable from localhost, LAN, and nginx reverse proxy.

## Access patterns

| Client location                 | OTLP endpoint                              |
|---------------------------------|--------------------------------------------|
| Same-host Docker container      | `http://host.docker.internal:4318/v1/logs` |
| Same-host non-Docker process    | `http://localhost:4318/v1/logs`            |
| LAN peer                        | `http://<signoz-host-ip>:4318/v1/logs`    |
| Remote / VPS (nginx + SSL)      | `https://<domain>/v1/logs`                |

## Nginx reverse proxy (example snippet)

```nginx
# OTLP HTTP ingestion
upstream signoz_otlp {
    server 127.0.0.1:4318;
}

server {
    listen 443 ssl;
    server_name  signoz-otlp.example.com;

    # ... ssl_certificate directives ...

    location /v1/ {
        proxy_pass  http://signoz_otlp;
        proxy_set_header  Host $host;
        proxy_set_header  X-Real-IP $remote_addr;
    }
}

# SigNoz UI
upstream signoz_ui {
    server 127.0.0.1:8080;
}

server {
    listen 443 ssl;
    server_name  signoz.example.com;

    # ... ssl_certificate directives ...

    location / {
        proxy_pass       http://signoz_ui;
        proxy_set_header Host $host;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## Directory layout

```
signoz/
├── README.md              ← you are here
├── docs/
│   └── ONBOARDING.md      ← per-project onboarding guide
├── common/                ← shared config mounted into containers
│   ├── clickhouse/
│   ├── dashboards/
│   └── signoz/
└── docker/
    ├── compose.yaml
    └── otel-collector-config.yaml
```

## Onboarding new projects

See [docs/ONBOARDING.md](docs/ONBOARDING.md) for:
- endpoint selection by client location
- required OTLP resource/log attributes
- copy-paste Vector agent compose snippet
- verification queries

## Lifecycle

This stack is **shared infrastructure** — independent of any single project.
- Start it once; leave it running.
- Project stacks start/stop without affecting SigNoz.
- Plan and communicate SigNoz upgrades since all projects share it.

## Stop / reset

```bash
# Stop (keep data)
docker compose -p signoz -f docker/compose.yaml down

# Full reset (wipe ClickHouse, SQLite, ZooKeeper volumes)
docker compose -p signoz -f docker/compose.yaml down -v
```
