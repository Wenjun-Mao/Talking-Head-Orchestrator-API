# Vector Configuration Guide

This directory contains the configuration for **Vector**, the high-performance log aggregator and processor used in the Talking-Head-Orchestrator pipeline.

## Overview

Vector is responsible for the "ETL" (Extract, Transform, Load) of system logs. It bridges the gap between raw Docker container output and the **SigNoz** observability platform.

### 🚀 Log Pipeline Flow

```text
  [ 📦 DOCKER SERVICES ]
  │   (s1-s8 pipeline workers)
  │   (Loguru Logs: JSON or Text)
  │
  ▼  (stdout/stderr stream)
  
  [ 🔌 DOCKER SOCKET ]
  │   (/var/run/docker.sock)
  │
  ▼  (Vector Source: docker_logs)
  
  [ 🛰️ VECTOR AGENT ]
  │
  ├─ 🧹 1. FILTER: Drop infra noise (RabbitMQ, DBs, etc.)
  │
  ├─ 🧠 2. REMAP: Parse Loguru & extract record_id/table_id
  │
  └─ 💾 3. BUFFER: Persist to disk for reliability
  │
  ▼  (OTLP / JSON over HTTP)
  
  [ 📊 SIGNOZ STACK ]
  │
  ├─ 📥 1. COLLECTOR: Receive structured OTLP data
  │
  ├─ 🗄️ 2. STORAGE: High-speed save to ClickHouse
  │
  └─ 📈 3. DASHBOARD: Real-time trace & log analysis
```

## Configuration Breakdown (`vector.yaml`)

### 1. Data Source (`sources`)
*   **`docker_logs`**: Vector monitors the Docker daemon socket to automatically discover and ingest logs from all running containers. It captures metadata such as container names, image IDs, and Docker Compose labels.

### 2. Filtering (`transforms.drop_rabbitmq_logs`)
To keep the SigNoz dashboard clean and cost-effective, we filter out "infrastructure noise."
*   **Excluded**: Logs from RabbitMQ, ClickHouse, SigNoz components, and Vector itself are dropped.
*   **Included**: Only logs from the core application services (`s1-ingest-nocodb` through `s8-nocodb-updater`) are passed through.

#### **VRL Variables in Filter**
The filter uses the following shorthand variables defined in Vector Remap Language (VRL):
*   **`svc`**: Short for **Service**. Extracted from the Docker Compose label `com.docker.compose.service`. This identifies the specific service name defined in your `docker-compose.yml`.
*   **`proj`**: Short for **Project**. Extracted from the Docker Compose label `com.docker.compose.project`. This identifies the stack or project name (e.g., `signoz`).
*   **`cname`**: Short for **Container Name**. Extracted from the raw `.container_name` field. This is used as a fallback or for more specific matching if labels are missing.

### 3. Normalization & Parsing (`transforms.normalize_docker_log`)
This transformation logic is optimized for the **Loguru** logging library used across our Python services.

#### **A. Format Handling**
The configuration supports two log formats:
1.  **JSON (Structured)**: If Loguru is configured to emit JSON, Vector parses it directly. This is the most reliable method for preserving field types.
2.  **Plain Text (Fallback)**: If the log is text-based, a Regex parser extracts the level, service name, and message.

#### **B. Business Context Extraction**
Vector uses specialized regex patterns to scan the log message for pipeline-specific identifiers:
*   `record_id`: The unique NocoDB record ID.
*   `table_id`: The NocoDB table context.
*   `event`: The specific lifecycle event (e.g., `DOWNLOAD_START`, `INFERENCE_COMPLETE`).

Extracting these into top-level fields allows for powerful filtering and "trace-like" log correlation in SigNoz.

#### **C. OpenTelemetry (OTLP) Mapping**
SigNoz requires logs in the OTLP format. Vector dynamically constructs a JSON envelope that maps our internal fields to standard OTLP attributes:
*   `.service` → `service.name`
*   `.level` → `severityText`
*   `.log_message` → `body`

### 4. Shipping (`sinks`)
*   **`signoz_otlp_logs`**: Forwards the OTLP-wrapped logs to the SigNoz collector via HTTP.
*   **Reliability**: A **disk-based buffer** (512MB) is used. If the network is interrupted or SigNoz is down, Vector persists logs to disk and retries automatically when connectivity is restored.
*   **Latency**: Configured with `max_events: 1` to ensure logs appear in the UI with near-zero delay during development.

## Technical Glossary: Flags & Components

Below are explanations for the specific "knobs" used in `vector.yaml`:

### 1. Component Types
*   **`type: docker_logs`**: A built-in source that connects to the Docker engine via its Unix socket or named pipe. It handles the complexity of discovering new containers and streaming their stdout/stderr.
*   **`type: filter`**: A transformation component that evaluates a boolean condition for each log event. If the condition is `true`, the log is passed to the next stage; if `false`, it is dropped.
*   **`type: remap`**: Vector's most powerful transform. It uses the **VRL (Vector Remap Language)** to modify fields, parse strings, and restructure the log event's schema.

### 2. Configuration Flags
*   **`auto_partial_merge: true`**: In Docker, very long log lines are often split into multiple chunks (e.g., if they exceed 16KB). Setting this to `true` tells Vector to automatically reassemble these split messages into a single coherent log entry before processing.
*   **`codec: raw_message`**: Used in the SigNoz sink to tell Vector *not* to add its own wrapping (like its default JSON structure) when sending data. We use this because we manually built the required OTLP JSON envelope in the `remap` stage.
*   **`uri: ${VARIABLE:-default}`**: This syntax allows the configuration to be dynamic. It will use the environment variable `VECTOR_SIGNOZ_OTLP_HTTP_URI` if it exists; otherwise, it falls back to the local Docker networking address (`http://host.docker.internal:4318/v1/logs`).

## Operations

### Reloading Configuration
If you modify `vector.yaml`, you must restart the container to apply changes:

```bash
docker-compose -f infra/observability/docker-compose.yml restart vector-agent
```

### Debugging Vector
To see if Vector is having trouble parsing logs or reaching SigNoz:

```bash
docker logs -f vector-agent
```
