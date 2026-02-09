# VM Layout and Dev Using Remote MAS/MINDEX – February 6, 2026

## Summary

- **MAS VM (192.168.0.188)** and **MINDEX VM (192.168.0.189)** host the orchestrator and database/API. Your **local dev website** (localhost:3010) can use them so you **don’t run database or agents locally**.
- **Sandbox VM (192.168.0.187)** runs the deployed website and can run other services. All three VMs can talk to each other on the server LAN.
- **VMs can call back to your local dev site** (e.g. webhooks, callbacks) if your PC is reachable at a LAN IP (e.g. `http://192.168.0.x:3010`) and the dev server is bound to all interfaces (Next.js dev default).

---

## 1. VM layout (what runs where)

| VM | IP | Role | Main services / ports |
|----|-----|------|------------------------|
| **Sandbox** | 192.168.0.187 | Website (Docker), optional services | Website 3000, Redis 6379?, Mycorrhizae 8002?, n8n 5678? (see compose on VM) |
| **MAS** | 192.168.0.188 | Multi-Agent System, orchestrator | Orchestrator **8001**, n8n 5678, NatureOS 5000?, NLM 8200? |
| **MINDEX** | 192.168.0.189 | Database + vector store | Postgres 5432, Redis 6379, Qdrant 6333/6334, **MINDEX API 8000** (if deployed) |

**MAS Orchestrator** is a systemd service on the MAS VM; it stays on and is the main entry for agents/voice/scientific APIs.

**MINDEX VM** currently runs Postgres, Redis, and Qdrant. The **MINDEX API** (HTTP on 8000) may be:
- On MINDEX VM (192.168.0.189:8000) if the API container has been deployed there, or
- On Sandbox (187) or MAS (188) as a container; in that case use the appropriate host:8000 (or the URL your team uses).

Use the table below for **local dev**. If 189:8000 doesn’t respond, point `MINDEX_API_URL` to wherever the MINDEX API actually runs (187 or 188) until 189 has the API.

### 1.1 MINDEX API deploy path

| Item | Details |
|------|---------|
| **Preferred host** | MINDEX VM **192.168.0.189** on port **8000** (or Sandbox 187 if 189 is not ready). |
| **Container name** | `mindex-api` (documented in website docs; compose may be `docker-compose.always-on.yml` on Sandbox). |
| **How to start** | On **Sandbox (187):** from the directory that has the MINDEX API compose/build, run the service that exposes port 8000 (e.g. `docker compose up -d mindex-api`). On **MINDEX VM (189):** deploy the same MINDEX API container or binary so it listens on 0.0.0.0:8000; use systemd or Docker. |
| **Keys** | Set `MINDEX_API_KEY` in the website (and optionally in the MINDEX API if it validates keys). Use the internal keys API (website `GET /api/internal/keys/dev` or `POST /api/internal/keys/generate`) or a fixed dev key (`local-dev-key`) for dev/sandbox. |
| **Health** | `GET http://<host>:8000/health` or `GET http://<host>:8000/api/mindex/health`. |

### 1.2 Mycorrhizae API deploy path

| Item | Details |
|------|---------|
| **Host** | Sandbox **192.168.0.187**, port **8002**. |
| **Container name** | `mycorrhizae-api`. |
| **Codebase** | **GitHub MycosoftLabs/Mycorrhizae** (external repo). |
| **How to start** | Clone the Mycorrhizae repo on 187 (or use a pre-built image), run via Docker Compose so the API is bound to 8002. Ensure Redis (e.g. 6380) is available if the protocol requires it. |
| **Keys** | Configure **MYCORRHIZAE_PUBLISH_KEY** and **MYCORRHIZAE_ADMIN_KEY** in both the **website** container env and the **Mycorrhizae API** config. Obtain keys from the website internal keys API (`GET /api/internal/keys/dev` or `POST /api/internal/keys/generate` with env `sandbox`) or create them in the Mycorrhizae API (e.g. `POST /api/keys`) and copy into website `.env.local` / sandbox env. |
| **Health** | `GET http://192.168.0.187:8002/health`. |

See **docs/APIS_AND_KEYS_AUDIT_FEB06_2026.md** and **website/docs/DEV_SANDBOX_KEYS_FLOW_FEB06_2026.md** for key flow and env vars.

---

## 2. Local dev website using VMs (no local DB/agents)

Goal: run only the **Next.js dev server** on your PC (port 3010) and have it call **MAS** and **MINDEX** on the VMs.

### 2.1 Env for “dev with remote MAS + MINDEX”

In the **website** repo create or update `.env.local` with at least:

```bash
# MAS VM – orchestrator, agents, scientific APIs
MAS_API_URL=http://192.168.0.188:8001
NEXT_PUBLIC_MAS_API_URL=http://192.168.0.188:8001
NEXT_PUBLIC_MAS_WS_URL=ws://192.168.0.188:8001/api/dashboard/ws
N8N_URL=http://192.168.0.188:5678

# MINDEX VM – database API (use 189 if MINDEX API is deployed there; else 187 or 188)
MINDEX_API_URL=http://192.168.0.189:8000
MINDEX_API_BASE_URL=http://192.168.0.189:8000
NEXT_PUBLIC_MINDEX_URL=http://192.168.0.189:8000
MINDEX_API_KEY=local-dev-key

# Optional: Mycorrhizae (often on Sandbox). Get keys from website internal keys API (see DEV_SANDBOX_KEYS_FLOW_FEB06_2026.md).
MYCORRHIZAE_API_URL=http://192.168.0.187:8002
MYCORRHIZAE_PUBLISH_KEY=<from internal keys API or Mycorrhizae API>
MYCORRHIZAE_ADMIN_KEY=<from internal keys API or Mycorrhizae API>

# Optional: Redis (if used by website server-side and Redis is on Sandbox)
REDIS_URL=redis://192.168.0.187:6379

# Local dev URL (for server-side redirects / callbacks)
NEXT_PUBLIC_BASE_URL=http://localhost:3010
```

If the MINDEX API is not on 189 yet, set `MINDEX_API_URL` / `MINDEX_API_BASE_URL` to the host:port where it does run (e.g. `http://192.168.0.187:8000` or `http://192.168.0.188:8000`).

### 2.2 Start dev

```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website
npm run dev:next-only
```

Open http://localhost:3010. The app will use MAS and MINDEX on the VMs; you do **not** need to run Postgres, Redis, or the MAS stack locally.

### 2.3 Check VMs are reachable from your PC

From your dev machine:

```powershell
# MAS health
curl http://192.168.0.188:8001/health

# MINDEX (if API is on 189)
curl http://192.168.0.189:8000/health
# or whatever health/root path the MINDEX API exposes
```

If these fail, fix network/firewall or start the services on the VMs (see MAS_ORCHESTRATOR_SERVICE and MINDEX_VM_DEPLOYMENT_STATUS docs).

---

## 3. VM-to-VM and VM-to-local

### 3.1 VMs talking to each other

All three VMs are on the same LAN (192.168.0.x). They can call each other by IP:

- **Sandbox (187)** → MAS: `http://192.168.0.188:8001`, MINDEX: `http://192.168.0.189:8000` (or 187/188 if API is there).
- **MAS (188)** → MINDEX: `http://192.168.0.189:8000`, Sandbox website: `http://192.168.0.187:3000`.
- **MINDEX (189)** → MAS: `http://192.168.0.188:8001`, Sandbox: `http://192.168.0.187:3000`.

Use these URLs in env vars or config on each VM (containers or systemd services) so they talk to the right host.

### 3.2 VMs talking to your local dev website

When you want MAS or MINDEX (or anything on a VM) to call **your local dev site** (e.g. webhooks, redirects):

1. **Your PC must be reachable** from the VMs. That usually means your PC has a **LAN IP** (e.g. 192.168.0.172 or 192.168.0.x) on the same network as the VMs.
2. **Next.js dev server** must listen on that IP. By default `next dev` binds to `0.0.0.0`, so it’s reachable on the LAN. If you started it with `npm run dev:next-only`, it should already be.
3. **Point callbacks to your PC.** Set the base URL for webhooks/redirects to your PC’s LAN IP and port 3010, e.g. `http://192.168.0.172:3010` (replace with your PC’s IP). Options:
   - In **website** `.env.local`: `NEXT_PUBLIC_BASE_URL=http://192.168.0.YOUR_PC_IP:3010` when testing callbacks from VMs.
   - Or configure the **MAS/MINDEX** (or other) service on the VM with a webhook URL like `http://192.168.0.YOUR_PC_IP:3010/api/webhooks/...`.
4. **Firewall:** On your PC, allow inbound TCP **3010** from 192.168.0.0/24 (or at least 187, 188, 189) so the VMs can reach you.

To find your PC’s LAN IP (PowerShell):

```powershell
(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback' }).IPAddress
```

Use that IP in the URLs above.

---

## 4. When you deploy or test on Sandbox

- **Deploy website to Sandbox:** Push code, then on 187: pull, build image, run container (see DEV_TO_SANDBOX_PIPELINE). The **website container on 187** should have env vars pointing to MAS (188:8001) and MINDEX (189:8000 or wherever the API runs), not localhost.
- **Update MAS or MINDEX:** SSH to 188 or 189, pull code, restart the orchestrator or MINDEX API (e.g. systemd or Docker). No need to run them locally; your **local dev site** keeps using the VMs via the same .env.local.
- **Verify from local dev:** With `.env.local` pointing at 188 and 189 (or 187 for MINDEX if applicable), use the dev site at http://localhost:3010 to confirm agents, search, and database features work against the live VMs.

---

## 5. One-page reference

| Purpose | URL or value |
|--------|----------------|
| Local dev site | http://localhost:3010 |
| MAS Orchestrator | http://192.168.0.188:8001 |
| MAS health | http://192.168.0.188:8001/health |
| MINDEX API (if on MINDEX VM) | http://192.168.0.189:8000 |
| Sandbox website | http://192.168.0.187:3000 / sandbox.mycosoft.com |
| VMs → local dev | http://YOUR_PC_LAN_IP:3010 (allow port 3010 from 192.168.0.0/24) |

---

## 6. Related docs

- **MAS_ORCHESTRATOR_SERVICE_FEB06_2026.md** – MAS VM service management
- **MINDEX_VM_DEPLOYMENT_STATUS_FEB04_2026.md** – MINDEX VM services and next steps (e.g. deploy MINDEX API on 189)
- **DEV_TO_SANDBOX_PIPELINE_FEB06_2026.md** – Dev server vs Docker, deploy to Sandbox, CI/CD
- **APIS_AND_KEYS_AUDIT_FEB06_2026.md** – Where MAS, MINDEX, Mycorrhizae, and Key Service live; internal keys API
- **Website repo: docs/DEV_SANDBOX_KEYS_FLOW_FEB06_2026.md** – How to obtain and set dev/sandbox keys

---

*Document date: February 6, 2026*
