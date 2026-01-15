## Mycosoft MAS (Multi-Agent System)

Mycosoft MAS is a **distributed multi-agent system** (Python/FastAPI) plus a **web UI (Next.js "MYCA")** and an optional **observability stack** (PostgreSQL, Redis, Qdrant, Prometheus, Grafana).

This repository is the **top-level MAS repo**. The previous root README content describing "ENVINT Platform" belongs in subsystem-specific docs and **is not the MAS README**.

> **Latest Update (January 2026):** Major CREP Dashboard enhancements with full data pipelines for aviation, maritime, satellite, and environmental data. New geocoding services, containerized data collectors, and comprehensive documentation. See the [Website Repository](https://github.com/MycosoftLabs/website) for CREP dashboard details.

---

## Table of contents

- [What MAS is (in this repo)](#what-mas-is-in-this-repo)
- [Architecture at a glance](#architecture-at-a-glance)
- [Quick start (Docker Compose)](#quick-start-docker-compose)
- [Local development (backend + UI)](#local-development-backend--ui)
- [Configuration](#configuration)
- [Authentication (Auth0/JWT)](#authentication-auth0jwt)
- [Ports and endpoints](#ports-and-endpoints)
- [Integrations](#integrations)
- [Monitoring & dashboards](#monitoring--dashboards)
- [Testing](#testing)
- [Common operations](#common-operations)
- [Troubleshooting](#troubleshooting)
- [Repo layout](#repo-layout)

---

## What MAS is (in this repo)

- **MAS API (FastAPI)**: a web API that initializes and runs the MAS runtime and exposes health/metrics endpoints.
  - Code: `mycosoft_mas/core/myca_main.py` (exports `app`)
- **MAS Orchestrator**: central coordinator for agents, services, MCP servers, dependencies, security, integrations.
  - Code: `mycosoft_mas/orchestrator.py`
- **Agents**: domain agents (mycology, finance, corporate ops, marketing, project management, DAO/IP, dashboard, opportunity scout, desktop automation).
  - Code: `mycosoft_mas/agents/*`
- **Integrations**: clients + unified manager for MINDEX, NatureOS, website, Notion, n8n, Azure.
  - Code: `mycosoft_mas/integrations/*`
- **Web UI (Next.js)**: the “MYCA” dashboard frontend.
  - Code: root `app/`, `components/`, `lib/`
- **Observability stack (optional)**: Prometheus + Grafana + dashboards, plus Redis/Qdrant/Postgres used by the runtime.
  - Code/config: `docker-compose.yml`, `prometheus.yml`, `grafana/`

---

## Architecture at a glance

- **Core architecture doc**: `mycosoft_mas/docs/architecture.md`
- **Integration architecture doc**: `docs/SYSTEM_INTEGRATIONS.md`

High-level: Orchestrator coordinates agents and managers (task/dependency/integration), backed by Redis/Postgres/Qdrant, and emits metrics to Prometheus/Grafana.

---

## Quick start (Docker Compose)

### Prerequisites

- **Docker Desktop** (Windows/macOS) or Docker Engine (Linux)

### Start everything

From repo root:

```bash
docker compose up -d
```

On Windows you can also use the included helper:

```powershell
.\start_mas.ps1
```

### Verify

```bash
docker compose ps
```

Then check:

- **Grafana**: `http://localhost:3000`
- **Prometheus**: `http://localhost:9090`
- **Qdrant**: `http://localhost:6333`
- **MYCA UI (Next.js)**: `http://localhost:3001`
- **MAS container port mapping**: `http://localhost:8001` (see note below about running the FastAPI app)

### Important note about the MAS API container

The MAS API is implemented as a FastAPI app exported by:

- `mycosoft_mas.core.myca_main:app`

If you want the **`mas-orchestrator`** container to serve the API, its command should run Uvicorn for that app.

- **If your Compose stack is not responding on the mapped API port**, run the API locally (see [Local development](#local-development-backend--ui)) or update the Compose command to something like:

```yaml
command: >
  sh -c "wait-for-it redis:6379 -t 60 &&
         wait-for-it postgres:5432 -t 60 &&
         uvicorn mycosoft_mas.core.myca_main:app --host 0.0.0.0 --port 8000"
```

---

## Local development (backend + UI)

### Prerequisites

- **Python 3.11**
- **Poetry** (dependency manager)
- **Node.js 20+** (matches `Dockerfile.next`)
- **Docker** (for Redis/Postgres/Qdrant/Grafana/Prometheus)

### 1) Start infrastructure services

```bash
docker compose up -d redis postgres qdrant prometheus grafana
```

### 2) Install Python deps

```bash
poetry install --with dev
```

### 3) Configure environment variables

The FastAPI MAS app loads `config/config.yaml` and expects runtime values via environment variables:

- `DATABASE_URL` (Postgres)
- `REDIS_URL`
- `OPENAI_API_KEY` (optional, if using OpenAI provider)
- `ANTHROPIC_API_KEY` (optional, if using Anthropic provider)
- `MESSAGE_BROKER_URL` (if using external broker)

Integrations (optional, but supported):

- `MINDEX_DATABASE_URL`, `MINDEX_API_URL`, `MINDEX_API_KEY`
- `NATUREOS_API_URL`, `NATUREOS_API_KEY`, `NATUREOS_TENANT_ID`
- `WEBSITE_API_URL`, `WEBSITE_API_KEY`
- `NOTION_API_KEY`, `NOTION_DATABASE_ID`
- `N8N_WEBHOOK_URL`, `N8N_API_URL`, `N8N_API_KEY`

### 4) Run the MAS API

```bash
poetry run uvicorn mycosoft_mas.core.myca_main:app --reload --host 0.0.0.0 --port 8000
```

Now you should have:

- `GET http://localhost:8000/health`
- `GET http://localhost:8000/metrics`

### 5) Run the MYCA web UI

```bash
npm ci
npm run dev
```

By default Next.js serves on `http://localhost:3000` (Compose maps it to `3001`).

---

## Configuration

There are **two** top-level configuration styles in this repo:

- **Runtime API config**: `config/config.yaml`
  - Used by: `mycosoft_mas/core/myca_main.py` (the FastAPI app)
  - Uses environment-variable substitution like `${DATABASE_URL}`

- **System/agent config**: root `config.yaml`
  - Used by: `python -m mycosoft_mas.run_mas` and `python -m mycosoft_mas` (`mycosoft_mas/__main__.py`)
  - Contains detailed per-agent settings (mycology/financial/corporate/etc.) and integration defaults

Container defaults are provided in `docker-compose.yml` for common URLs and local ports.

---

## Authentication (Auth0/JWT)

Several API routers require a valid JWT via `Authorization: Bearer <token>`.

- Implemented in: `mycosoft_mas/core/security.py`
- Required env vars:
  - `AUTH0_DOMAIN`
  - `AUTH0_API_AUDIENCE`

Endpoints that use auth dependency include:

- `/agents/*`
- `/tasks/*`
- `/dashboard/*` (API router)

If these env vars are not set (or token is invalid), those endpoints will return **401**.

---

## Ports and endpoints

### Docker Compose (default)

- **MAS API / Orchestrator container**: `8001 -> 8000` (`mas-orchestrator`)
- **MYCA UI (Next.js)**: `3001 -> 3000` (`myca-app`)
- **Grafana**: `3000 -> 3000`
- **Prometheus**: `9090 -> 9090`
- **Qdrant**: `6333 -> 6333`
- **Redis**: `6379 -> 6379`
- **Postgres**: `5433 -> 5432` (external `5433` to avoid local conflicts)

### MAS API (FastAPI)

- App: `mycosoft_mas.core.myca_main:app`
- Key endpoints:
  - `GET /` — basic status
  - `GET /health` — MAS health (agents + services)
  - `GET /metrics` — Prometheus metrics
  - `/dashboard` — a mounted dashboard app plus an API router (see note below)

**Note:** `mycosoft_mas/core/myca_main.py` both mounts a dashboard ASGI app at `/dashboard` and also includes an API router with prefix `/dashboard`. If you see unexpected routing behavior, check:

- Mounted app: `mycosoft_mas/monitoring/dashboard.py` (mounted at `/dashboard`)
- API router: `mycosoft_mas/core/routers/dashboard.py` (prefix `/dashboard`, requires auth)

---

## Integrations

The MAS integration clients live under `mycosoft_mas/integrations/`.

- **Primary integration README**: `mycosoft_mas/integrations/README.md`
- **System-level integration doc**: `docs/SYSTEM_INTEGRATIONS.md`

The recommended entrypoint for cross-system work is the unified manager:

- `mycosoft_mas.integrations.unified_integration_manager.UnifiedIntegrationManager`

---

## Monitoring & dashboards

- **Prometheus scraping**: `prometheus.yml`
- **Grafana provisioning/dashboards**: `grafana/`
- **MAS metrics endpoint**: `GET /metrics` on the FastAPI app

If you’re using Docker Compose, Grafana is exposed at `http://localhost:3000`.

- **Default Grafana login (Compose default)**: username `admin`, password `admin` (see `docker-compose.yml`).

---

## Testing

### Python tests

```bash
poetry run pytest
```

Or use the repo helper (Windows-oriented):

```bash
python run_tests.py
```

### CI

See GitHub workflows under `.github/workflows/`.

---

## Common operations

- **Start/stop stack**:

```bash
docker compose up -d
docker compose down
```

- **Follow logs**:

```bash
docker compose logs -f --tail=200
```

- **Verify the stack**:

```bash
python scripts/verify_mas.py
```

- **Restart & rebuild containers (PowerShell)**:

```powershell
.\scripts\restart_mas.ps1
```

---

## Troubleshooting

- **Port conflicts**: Postgres uses `5433` externally; if you still have conflicts see `PORT_CONFLICT_RESOLUTION.md`.
- **Auth endpoints return 401**: set `AUTH0_DOMAIN` + `AUTH0_API_AUDIENCE` and send a valid Bearer token.
- **Compose starts but API healthcheck fails**: ensure the `mas-orchestrator` service is actually running Uvicorn for `mycosoft_mas.core.myca_main:app` (see [Quick start](#quick-start-docker-compose)).
- **Windows venv path differences**:
  - Some scripts assume `.venv` (bash) and some assume `venv` (PowerShell). Adjust activation paths to match your environment.

---

## Repo layout

- `mycosoft_mas/` — Python package (MAS runtime, API, agents, services, integrations)
- `config/` — runtime config for the FastAPI app (`config/config.yaml`)
- `config.yaml` — system/agent configuration used by `run_mas`
- `docker-compose.yml`, `Dockerfile`, `Dockerfile.next` — containerized stack
- `grafana/`, `prometheus/`, `prometheus.yml` — observability configuration
- `app/`, `components/`, `lib/` — Next.js UI
- `docs/` — repo documentation
- `scripts/` — operational scripts and helpers

---

## Related Repositories & Systems

Mycosoft MAS integrates with several companion systems:

| System | Description | Repository |
|--------|-------------|------------|
| **MINDEX** | Fungal Intelligence Database with 1.2M+ observations | [MycosoftLabs/mindex](https://github.com/MycosoftLabs/mindex) |
| **Website** | Main Mycosoft website with CREP dashboard | [MycosoftLabs/website](https://github.com/MycosoftLabs/website) |
| **CREP** | Common Relevant Environmental Picture dashboard | Part of Website repo |
| **NatureOS** | Biomimetic operating system layer | Part of Website repo |
| **MycoBrain** | IoT sensor platform for environmental monitoring | Part of MAS repo |

### CREP Dashboard Features (Latest)

The CREP dashboard provides real-time global situational awareness:
- **Aviation Tracking**: FlightRadar24 integration with animated trajectories
- **Maritime Tracking**: AIS vessel data with port-to-port routes
- **Satellite Tracking**: CelesTrak TLE data with orbit visualization
- **Environmental Events**: Earthquakes, wildfires, storms, lightning
- **Fungal Observations**: MINDEX integration with 1.2M+ fungal data points
- **Space Weather**: NOAA SWPC solar/geomagnetic monitoring

For detailed CREP documentation, see `docs/CREP_SYSTEM.md` in the Website repository.

---

## Version History

See [CHANGELOG.md](./CHANGELOG.md) for detailed version history.
