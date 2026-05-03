# Petri Dish v2 — Deploy Runbook (May 02, 2026)

**Status:** Operational reference  
**Related:** `docs/PETRI_DISH_V2_ARCHITECTURE_MAY02_2026.md`, `services/petri_engine/README.md`

## Components

| Service | Host | Port | Image / command |
|---------|------|------|-----------------|
| `petri_engine_service` (Rust) | Sandbox **187** | **8050** | `mycosoft/petri-engine:v2` (`services/petri_engine/Dockerfile`) |
| MyceliumSeg API | Sandbox **187** | **8051** | `mycosoft/myceliumseg-api:v1` (`scripts/myceliumseg/Dockerfile`) |
| MAS proxy | MAS **188** | 8001 | `/api/simulation/petri/v2/*` reads `PETRI_ENGINE_V2_URL` |
| Website BFF | 187 / local | — | `/api/simulation/petri/v2`, `/api/simulation/petri-seg` |

## One-shot deploy on Sandbox (187)

From a machine with LAN access and VM credentials:

```powershell
cd C:\...\mycosoft-mas
python scripts/deploy_petri_v2_stack_vm187.py
```

This `git reset --hard origin/main` in `~/mycosoft/mas`, builds both images on **187**, starts:

- `petri-engine-v2` → `8050`
- `myceliumseg-api` → `8051` (loads `MINDEX_DATABASE_URL` from `/opt/mycosoft/.env` if present)

**Manual build (on 187):**

```bash
cd ~/mycosoft/mas && git pull
cd services/petri_engine && docker build -t mycosoft/petri-engine:v2 .
docker rm -f petri-engine-v2; docker run -d --name petri-engine-v2 --restart unless-stopped -p 8050:8050 -e PETRI_ENGINE_PORT=8050 mycosoft/petri-engine:v2

cd ~/mycosoft/mas
docker build -f scripts/myceliumseg/Dockerfile -t mycosoft/myceliumseg-api:v1 .
docker rm -f myceliumseg-api
docker run -d --name myceliumseg-api --restart unless-stopped -p 8051:8051 \
  -e PORT=8051 -e MINDEX_DATABASE_URL="<postgres url>" mycosoft/myceliumseg-api:v1
```

## MAS VM (188) environment

Set on the **mas-orchestrator** service (systemd `Environment=` or `EnvironmentFile=`):

```bash
PETRI_ENGINE_V2_URL=http://192.168.0.187:8050
```

Restart: `sudo systemctl restart mas-orchestrator`

Verify:

- `curl -s http://192.168.0.188:8001/api/simulation/petri/v2/health`
- Expect JSON from Rust `/health` when URL is set; `degraded` when unset.

## Website `.env`

- `PETRI_SEG_SERVICE_URL=http://192.168.0.187:8051` (server-side BFF)
- Optional `NEXT_PUBLIC_PETRI_SEG_SERVICE_URL` only if a client must call seg directly (avoid exposing DB-backed URL publicly without auth).

## WASM build (browser)

See `services/petri_engine/README.md` — `wasm-pack` output to `website/public/wasm/petri_engine` or project `lib` path.

## Cloudflare

After website container rebuild for Petri UI/assets: **Purge Everything** (`scripts/cloudflare_purge_zone_from_mas_env.py`).
