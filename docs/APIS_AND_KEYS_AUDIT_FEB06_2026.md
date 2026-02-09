# APIs and Keys Audit – February 6, 2026

## Purpose

This document records where each of **MAS API**, **MINDEX API**, **Mycorrhizae API**, and **Key Service** lives, how to run them, and which keys they need and where those keys come from. It is the Phase 1 deliverable for the APIs and Keys system audit plan.

---

## 1. MAS API

| Item | Details |
|------|---------|
| **Status** | Running |
| **Location** | MAS VM **192.168.0.188**, port **8001** |
| **How run** | systemd service on MAS VM (orchestrator). Entrypoint: `mycosoft_mas/core/orchestrator_service.py` (FastAPI app, `uvicorn.run(app, host="0.0.0.0", port=8001)`). |
| **Keys** | No API key in use for internal calls. |
| **Used by** | Website `MAS_API_URL`, MAS agents, dashboard WebSocket/SSE. |

**References:** [website/lib/env.ts](https://github.com/MycosoftLabs/website/blob/main/lib/env.ts), [VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md](./VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md).

---

## 2. MINDEX API

| Item | Details |
|------|---------|
| **Status** | Not confirmed running in this workspace; documented as container on Sandbox 187. |
| **Expected URL** | **http://192.168.0.189:8000** (MINDEX VM) or **http://192.168.0.187:8000** (Sandbox). |
| **Location (server code)** | **Not found in MAS or website repo.** The HTTP server that exposes MINDEX (FastAPI on port 8000) is referenced in docs as container `mindex-api`. Website and MAS call it via `MINDEX_API_URL` and expect endpoints such as `/api/mindex/health`, `/api/mindex/stats`, `/api/mindex/taxa`, `/api/mindex/observations`, `/api/mindex/etl/status`. Implementation may live in an external repo or under paths excluded from search (e.g. `.cursorignore`). |
| **How run (documented)** | Docker Compose: `docker-compose.always-on.yml` (referenced in website docs; file not present in website workspace—may exist on Sandbox VM). Service name in docs: `mindex-api`. Alternative: deploy on MINDEX VM (189) as a container or systemd service. |
| **Keys** | `MINDEX_API_KEY` (default `local-dev-key` in website). Sent as header `X-API-Key`. MINDEX API must accept this key if it enforces auth. |
| **Used by** | Website (env `MINDEX_API_URL`, `MINDEX_API_BASE_URL`), MAS `mindex_client.py`, `memory_api.py`, `unified_memory_bridge.py`, agents (wifisense, drone), registry api_indexer, plugins, NatureOS. |

**References:** [website/docs/SYSTEM_INTEGRATION_COMPLETE_JAN25_2026.md](https://github.com/MycosoftLabs/website/blob/main/docs/SYSTEM_INTEGRATION_COMPLETE_JAN25_2026.md), [MINDEX_VM_DEPLOYMENT_STATUS_FEB04_2026.md](./MINDEX_VM_DEPLOYMENT_STATUS_FEB04_2026.md), [VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md](./VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md). MAS: `mycosoft_mas/integrations/mindex_client.py`, `core/routers/memory_api.py`, `registry/api_indexer.py`.

---

## 3. Mycorrhizae API

| Item | Details |
|------|---------|
| **Status** | Documented as running on Sandbox 187:8002. |
| **Location** | External repo: **https://github.com/MycosoftLabs/Mycorrhizae** (commit `59c9a6d` referenced in SYSTEM_INTEGRATION). Container name in docs: `mycorrhizae-api`, port **8002**. |
| **How run** | Docker container on Sandbox VM (192.168.0.187). Compose/deploy steps are repo-specific; ensure `mycorrhizae-api` is started and bound to 8002 so website and stream route can reach it. |
| **Keys** | **MYCORRHIZAE_PUBLISH_KEY** (publish to channels), **MYCORRHIZAE_ADMIN_KEY** (admin: keys, channels). API exposes key endpoints: `POST /api/keys`, `GET /api/keys`, `POST /api/keys/validate`, etc. Keys must be created/registered in the Mycorrhizae API (or via Key Service) and then set in website `.env.local` and in the Mycorrhizae API config so it accepts them. |
| **Used by** | Website `lib/env.ts`, `lib/mindex/mycorrhizae/client.ts`, `app/api/mycorrhizae/stream/route.ts`, MINDEX UI components (data-flow, agent-activity, mwave-dashboard, query-monitor, crypto-monitor) for publish/stream. |

**References:** [website/lib/env.ts](https://github.com/MycosoftLabs/website/blob/main/lib/env.ts), [website/app/api/mycorrhizae/stream/route.ts](https://github.com/MycosoftLabs/website/blob/main/app/api/mycorrhizae/stream/route.ts), [website/docs/SYSTEM_INTEGRATION_COMPLETE_JAN25_2026.md](https://github.com/MycosoftLabs/website/blob/main/docs/SYSTEM_INTEGRATION_COMPLETE_JAN25_2026.md).

---

## 4. Key Service (internal API key generation)

| Item | Details |
|------|---------|
| **Status** | **Not found in website or MAS workspace.** Documented only. |
| **Location (documented)** | Referenced as **`services/key_service.py`** in [website/docs/SYSTEM_INTEGRATION_COMPLETE_JAN25_2026.md](https://github.com/MycosoftLabs/website/blob/main/docs/SYSTEM_INTEGRATION_COMPLETE_JAN25_2026.md) under “Mycorrhizae Protocol Components → Services”. That path may be relative to the **Mycorrhizae** repo (GitHub MycosoftLabs/Mycorrhizae), not the website repo. Website repo has a `services/` folder but **no `key_service.py`** there. |
| **Documented behavior** | API key generation (SHA-256 hashed), validation with scope checking, rate limiting (per-minute, per-day), key rotation and revocation, audit logging. |
| **Gap** | No single internal service found in this workspace that issues MINDEX_API_KEY, MYCORRHIZAE_PUBLISH_KEY, or MYCORRHIZAE_ADMIN_KEY for dev/test/sandbox. Treat as **to be built** (Phase 2) unless confirmed in Mycorrhizae repo. |

**References:** [website/docs/SYSTEM_INTEGRATION_COMPLETE_JAN25_2026.md](https://github.com/MycosoftLabs/website/blob/main/docs/SYSTEM_INTEGRATION_COMPLETE_JAN25_2026.md).

---

## 5. Summary table

| API / Key | Where it lives | How to run | Keys needed / source |
|-----------|----------------|------------|------------------------|
| **MAS API** | MAS VM 188:8001, `mycosoft_mas/core/orchestrator_service.py` | systemd on MAS VM | None for internal |
| **MINDEX API** | Server code not in workspace; container `mindex-api` on 187 or 189:8000 | Docker (e.g. always-on compose on 187) or deploy on 189 | MINDEX_API_KEY (env); default `local-dev-key` |
| **Mycorrhizae API** | GitHub MycosoftLabs/Mycorrhizae | Docker on Sandbox 187:8002 | MYCORRHIZAE_PUBLISH_KEY, MYCORRHIZAE_ADMIN_KEY (create in API or Key Service) |
| **Key Service** | Not in workspace; doc ref `services/key_service.py` (likely Mycorrhizae repo) | Unknown; to be built or integrated if missing | N/A (issues keys) |

---

## 6. Internal keys API (Phase 2 – implemented)

A minimal **internal keys API** lives in the **website** repo and provides dev/test/sandbox keys without a separate Key Service:

| Item | Details |
|------|---------|
| **Location** | **Website**: `app/api/internal/keys/`, `lib/internal-keys/store.ts`. |
| **Endpoints** | `GET /api/internal/keys` – list envs and which have stored keys. `GET /api/internal/keys/dev` – get or create dev keys (returns `MINDEX_API_KEY`, `MYCORRHIZAE_PUBLISH_KEY`, `MYCORRHIZAE_ADMIN_KEY` and an `envSnippet` for `.env.local`). `POST /api/internal/keys/generate` – body `{ "env": "dev" \| "test" \| "sandbox" }` to generate and persist new keys. |
| **Auth** | Header `X-Internal-Keys-Secret` or `Authorization: Bearer <secret>`. Secret from env `INTERNAL_KEYS_ADMIN_SECRET`. If unset, only allowed in `NODE_ENV=development`. |
| **Storage** | JSON file `.internal-keys.json` in project root (or `INTERNAL_KEYS_STORE_DIR`). File is gitignored. |

Use these endpoints to obtain keys for local `.env.local` or for sandbox deploy scripts; then configure the Mycorrhizae API to accept the same `MYCORRHIZAE_PUBLISH_KEY` and `MYCORRHIZAE_ADMIN_KEY`.

---

## 7. Next steps (from plan)

- **Phase 3:** Dev/sandbox key flow: `.env.local.example`, script or doc to obtain and set keys; sandbox key setup for website container and Mycorrhizae API.
- **Phase 4:** Deploy MINDEX API (189 or 187) and Mycorrhizae API (187); update VM layout and pipeline docs.

---

*Document date: February 6, 2026*
