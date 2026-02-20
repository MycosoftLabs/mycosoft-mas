# Deploy All Three VMs – February 19, 2026

**Purpose:** Single checklist for deploying Website (187), MAS (188), and MINDEX (189) in one pass. For the deployment agent.

---

## Prerequisites

- **Credentials:** `.credentials.local` in **website** or **MAS** repo root must contain:
  - `VM_PASSWORD=Loserology1!` (or `VM_SSH_PASSWORD=Loserology1!`)
  - `VM_SSH_USER=mycosoft`
- **Never ask the user for the password.** Load from file.
- **Cloudflare:** For cache purge after website deploy, set `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ZONE_ID` (e.g. in website `.env.local` or env).

---

## 1. Website → Sandbox (192.168.0.187)

**Option A – Automated (recommended)**  
From **website repo** root (`C:\...\WEBSITE\website`):

```powershell
Get-Content ".credentials.local" | ForEach-Object { if ($_ -match "^([^#=]+)=(.*)$") { [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process") } }
python _rebuild_sandbox.py
```

Script: SSH → pull `origin/main` → `docker build --no-cache` → stop/rm container → run with **NAS mount** → health check → Cloudflare purge.

**Option B – Manual SSH**

```bash
ssh mycosoft@192.168.0.187
cd /opt/mycosoft/website && git fetch origin && git reset --hard origin/main
docker stop mycosoft-website 2>/dev/null || true; docker rm mycosoft-website 2>/dev/null || true
docker build -t mycosoft-always-on-mycosoft-website:latest --no-cache .
docker run -d --name mycosoft-website -p 3000:3000 \
  -v /opt/mycosoft/media/website/assets:/app/public/assets:ro \
  -e MAS_API_URL=http://192.168.0.188:8001 \
  -e MYCOBRAIN_SERVICE_URL=http://192.168.0.187:8003 \
  -e MYCOBRAIN_API_URL=http://192.168.0.187:8003 \
  --restart unless-stopped mycosoft-always-on-mycosoft-website:latest
```

Then **purge Cloudflare** (Purge Everything). Verify: https://sandbox.mycosoft.com/

---

## 2. MAS → VM 188

```bash
ssh mycosoft@192.168.0.188
cd /home/mycosoft/mycosoft/mas && git fetch origin && git reset --hard origin/main
docker build -t mycosoft/mas-agent:latest --no-cache .
docker stop myca-orchestrator-new 2>/dev/null || true
docker rm myca-orchestrator-new 2>/dev/null || true
docker run -d --name myca-orchestrator-new --restart unless-stopped -p 8001:8000 mycosoft/mas-agent:latest
```

Verify: `curl -s http://192.168.0.188:8001/health`

---

## 3. MINDEX → VM 189

```bash
ssh mycosoft@192.168.0.189
cd /home/mycosoft/mindex && git fetch origin && git reset --hard origin/main
docker compose stop mindex-api
docker compose build --no-cache mindex-api
docker compose up -d mindex-api
```

Verify: `curl -s http://192.168.0.189:8000/api/mindex/health`

---

## 4. Post-Deploy Verification

| VM   | URL | Expect |
|------|-----|--------|
| 187  | http://192.168.0.187:3000 | HTTP 200 |
| 187  | https://sandbox.mycosoft.com/ | 200, fresh after purge |
| 188  | http://192.168.0.188:8001/health | JSON, `"service": "mas"` |
| 189  | http://192.168.0.189:8000/api/mindex/health | JSON, `"status": "ok"` |

---

## 5. Related Docs

- `docs/DEPLOYMENT_AGENT_HANDOFF_FEB18_2026.md` – Full handoff (website focus)
- `docs/DEPLOYMENT_READINESS_CHECK_FEB19_2026.md` – Git status, build, credentials
- `docs/SANDBOX_LIVE_TESTING_PREP_FEB18_2026.md` – Full VM layout and checklist
- `docs/COMPOUNDS_BUG_FIX_AND_DEPLOY_FEB19_2026.md` – Compounds fix and deploy steps
- `docs/DEPLOYMENT_COMMANDS_FEB18_2026.md` – Copy-paste commands
