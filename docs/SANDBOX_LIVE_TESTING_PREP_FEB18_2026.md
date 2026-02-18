# Sandbox Live Testing Prep – February 18, 2026

**Purpose:** Prepare everything for testing in sandbox (live on all VMs, outside the development environment). **Deployment is executed by another agent**; this document is the single reference for what to deploy, where, and how to verify.

**Handoff for deploying agent:** See also `docs/DEPLOYMENT_HANDOFF_SANDBOX_FEB18_2026.md` for a short checklist and pointer to this doc. Code is prepared and pushed to GitHub; deployment runs on the VMs only.

---

## 1. VM and GPU Node Layout (Live)

| Host | IP | Role | Key Ports / Services |
|------|-----|------|------------------------|
| **Sandbox** | 192.168.0.187 | Website (Docker), optional services | **Website 3000**, n8n 5678, MINDEX API 8000?, Mycorrhizae 8002, Redis 6379, Postgres 5432 |
| **MAS** | 192.168.0.188 | Multi-Agent System, orchestrator | **Orchestrator 8001**, n8n 5678 |
| **MINDEX** | 192.168.0.189 | Database + vector store | Postgres 5432, Redis 6379, Qdrant 6333, **MINDEX API 8000** |
| **GPU Node** | 192.168.0.190 | PersonaPlex (NVIDIA), Linux | **Moshi** (internal, e.g. 19198), **Bridge 8999** |

- **Live site:** https://sandbox.mycosoft.com/
- **Credentials:** Load from `.credentials.local` (MAS or website repo); `VM_SSH_PASSWORD` / `VM_PASSWORD`; user `mycosoft` on all VMs.

---

## 2. What Must Be Running for Sandbox to Work

- **Sandbox (187):** Website container `mycosoft-website` on port 3000; NAS mount for media.
- **MAS (188):** Orchestrator on 8001 (systemd or Docker).
- **MINDEX (189):** MINDEX API on 8000 (and/or on 187 if that’s your topology).
- **GPU Node (190):** PersonaPlex Bridge on 8999; Moshi available (for test-voice).

---

## 3. Deployment Checklist (For the Deploying Agent)

Execute in order. Do not skip the NAS mount for the website container.

### 3.1 Prerequisites

- Website code **committed and pushed to GitHub `main`** (MycosoftLabs/website).
- SSH access to Sandbox: `mycosoft@192.168.0.187` (use credentials from `.credentials.local`).

### 3.2 On Sandbox VM (192.168.0.187)

1. **SSH**
   ```bash
   ssh mycosoft@192.168.0.187
   ```

2. **Pull latest website code**
   ```bash
   cd /opt/mycosoft/website
   git fetch origin
   git reset --hard origin/main
   ```

3. **Stop and remove existing website container**
   ```bash
   docker stop mycosoft-website 2>/dev/null || true
   docker rm mycosoft-website 2>/dev/null || true
   ```

4. **Rebuild Docker image**
   ```bash
   cd /opt/mycosoft/website
   docker build -t mycosoft-always-on-mycosoft-website:latest --no-cache .
   ```
   (Alternative image name used on some setups: `website-website:latest`; use the same name in the run command below.)

5. **Start container with NAS mount (required for media)**
   ```bash
   docker run -d --name mycosoft-website -p 3000:3000 \
     -v /opt/mycosoft/media/website/assets:/app/public/assets:ro \
     -e MAS_API_URL=http://192.168.0.188:8001 \
     --restart unless-stopped \
     mycosoft-always-on-mycosoft-website:latest
   ```

6. **Verify on VM**
   ```bash
   docker ps | grep mycosoft-website
   sleep 10
   curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
   ```
   Expect: container running, HTTP 200.

### 3.3 Cloudflare

- **Purge cache:** Cloudflare Dashboard → mycosoft.com → Caching → **Purge Everything** (or use Cloudflare API with zone ID and token from env).

### 3.4 Post-Deploy Verification

- **Homepage:** https://sandbox.mycosoft.com/ → 200, page loads.
- **Assets:** https://sandbox.mycosoft.com/assets/mushroom1/Main%20A.jpg → 200 (confirms NAS mount).
- **API (example):** https://sandbox.mycosoft.com/api/health or /api/mycobrain/health → appropriate status.

---

## 4. Paths and Image Names (Reference)

| Item | Value |
|------|--------|
| Website code on Sandbox | `/opt/mycosoft/website` |
| Website container name | `mycosoft-website` |
| Image name (primary) | `mycosoft-always-on-mycosoft-website:latest` |
| Image name (alternate) | `website-website:latest` |
| NAS mount (host) | `/opt/mycosoft/media/website/assets` |
| NAS mount (container) | `/app/public/assets:ro` |
| Website port | 3000 |

---

## 5. Test-Voice (Sandbox + GPU Node)

- **Test-voice page:** https://sandbox.mycosoft.com/test-voice (after website is deployed).
- **Bridge:** Must be reachable at `ws://192.168.0.190:8999` (or the URL configured in the website env). Bridge health: `http://192.168.0.190:8999/health`.
- **MAS:** Bridge uses `http://192.168.0.188:8001` for MYCA Brain.
- **Moshi:** Runs on GPU node; Bridge reports `moshi_available: true` when healthy.

---

## 6. Env Vars (Website Container / Sandbox)

Set in container or in compose/env file used to start the website:

- `MAS_API_URL=http://192.168.0.188:8001`
- `MINDEX_API_URL=http://192.168.0.189:8000` (or 187:8000 if MINDEX runs on Sandbox)
- For test-voice from browser: `NEXT_PUBLIC_PERSONAPLEX_BRIDGE_WS_URL=ws://192.168.0.190:8999` (if needed for sandbox.mycosoft.com)

---

## 7. Related Docs

- **VM layout and dev:** `docs/VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md`
- **Dev → Sandbox pipeline:** `docs/DEV_TO_SANDBOX_PIPELINE_FEB06_2026.md`
- **Sandbox runbook:** `docs/SANDBOX_DEPLOYMENT_RUNBOOK.md`
- **Voice quick start:** `docs/VOICE_TEST_QUICK_START_FEB18_2026.md`
- **Deploy skill:** `.cursor/skills/deploy-website-sandbox/SKILL.md`

---

## 8. GitHub Repos (Source of Truth)

- **Website:** https://github.com/MycosoftLabs/website (branch `main`)
- **MAS:** https://github.com/MycosoftLabs/mycosoft-mas (branch `main`)

Deployment agent should pull from GitHub after code is pushed; no deployment from local-only changes.
