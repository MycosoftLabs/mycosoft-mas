# Dev to Sandbox Pipeline – February 6, 2026

## Summary

- **Local dev**: Run the **Next.js dev server only** (no Docker). Instant hot reload from Cursor. Port **3010**.
- **Local Docker**: Optional; only for testing a full production-like stack. **Not required** for day-to-day website dev.
- **Sandbox deploy**: Code in **GitHub** → VM pulls, **builds Docker image**, runs container → **Cloudflare** cache purge. CI/CD can automate this.

---

## 1. Local development (instant updates, hot reload)

**Goal:** Edit code in Cursor and see changes immediately. No Docker.

| What | Where | Command |
|------|--------|--------|
| Website code | `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website` | — |
| Dev server | Local machine, port **3010** | `npm run dev:next-only` (or `npm run dev` if you need GPU/voice) |
| URL | http://localhost:3010 | — |

**Steps:**

1. Open terminal, go to website repo:
   ```powershell
   cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website
   ```
2. Start dev server (no Docker, no GPU services):
   ```powershell
   npm run dev:next-only
   ```
3. In Cursor, edit files under `website`. Next.js hot-reloads; refresh browser if needed.

**If port 3010 is in use:** Stop the process using it, or run:
```powershell
# In website repo: scripts/start-dev.ps1
# Or manually:
Get-NetTCPConnection -LocalPort 3010 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website
npm run dev:next-only
```

**Backends (APIs, MINDEX, MAS):** Use the VMs so you don’t run DB/agents locally. In `.env.local` set:
- **MAS:** `MAS_API_URL=http://192.168.0.188:8001` (MAS VM)
- **MINDEX:** `MINDEX_API_URL=http://192.168.0.189:8000` (MINDEX VM; or 187/188 if API runs there)
See **docs/VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md** for full VM layout and VM-to-local.

---

## 2. Local Docker (optional)

**When to use:** Testing production-like stack (website + Postgres + Redis + services) on your machine. **Not required** for normal website dev.

| What | Purpose |
|------|--------|
| `WEBSITE/website/docker-compose.yml` | Full stack: website, postgres, redis, mycobrain, collectors, n8n, monitoring. Heavy. |
| `WEBSITE/website/docker-compose.services.yml` | Extra services. |
| `WEBSITE/website/docker-compose.crep.yml` | CREP-related. |

**Reality:** The live website code in Cursor has grown past what these compose files target. For daily work, **ignore local Docker** and use the dev server (section 1). Use local Docker only when you explicitly need to test the full stack.

**If you do run local Docker:** Use a separate terminal; keep the dev server on 3010 for editing. Don’t expect “dev site” to mean “Docker on my machine” – it means “Next.js dev server on 3010.”

---

## 3. Sandbox VM deployment (proper deploy with GitHub, Docker, Cloudflare)

**Goal:** Run the built website in Docker on the Sandbox VM and serve it via Cloudflare.

| Step | Where | Action |
|------|--------|--------|
| 1. Code in GitHub | Website repo (and/or MAS repo if that’s where deploy runs from) | Commit and push from Cursor. |
| 2. VM has code | Sandbox 192.168.0.187 | SSH, pull (e.g. `git pull` or sync from GitHub). |
| 3. Build image | VM: `/opt/mycosoft/website` (or path where website code lives) | `docker build -t mycosoft-always-on-mycosoft-website:latest --no-cache .` |
| 4. Run container | VM | Restart/recreate website container (e.g. `docker run ...` with NAS mount or `docker compose -p mycosoft-production up -d mycosoft-website`). |
| 5. Cloudflare | Dashboard | **Purge Everything** (or purge relevant zones) so users see new content. |

**VM website paths (as of this doc):**

- Website code on VM: `/opt/mycosoft/website`
- Image name used: `mycosoft-always-on-mycosoft-website:latest`
- Container name: `mycosoft-website`, port 3000
- NAS mount (required for media): `-v /opt/mycosoft/media/website/assets:/app/public/assets:ro`

**Sandbox env (keys for MINDEX and Mycorrhizae):** The website container on 187 must have `MINDEX_API_URL`, `MINDEX_API_KEY`, `MYCORRHIZAE_API_URL`, `MYCORRHIZAE_PUBLISH_KEY`, and `MYCORRHIZAE_ADMIN_KEY` set (e.g. in the compose env or a `.env` used by the stack). Obtain dev/sandbox keys from the internal keys API (see **website/docs/DEV_SANDBOX_KEYS_FLOW_FEB06_2026.md**) or use fixed dev keys and configure the Mycorrhizae API on 187 to accept the same keys.

**Example full deploy (from your machine, after push to GitHub):**

```powershell
# 1. Commit and push (website repo and/or MAS repo as you use)
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website
git add -A
git commit -m "Your message"
git push origin main

# 2. Rebuild and run on VM (from MAS repo script that SSHs to VM)
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
python scripts/_rebuild_sandbox.py
# Or: SSH to VM, then on VM:
#   cd /opt/mycosoft/website && git pull && docker build -t mycosoft-always-on-mycosoft-website:latest --no-cache . && docker compose -p mycosoft-production up -d mycosoft-website

# 3. Cloudflare: Purge Everything
```

---

## 4. CI / CD (GitHub Actions, Cloudflare)

**Website repo** (`.github/workflows/ci-cd.yml`):

- Lint, typecheck, tests, Docker build, push to registry.
- Deploy to staging (e.g. `develop`) or production (e.g. `main`) via SSH to a host (e.g. `PROXMOX_HOST` / `STAGING_HOST`).

**MAS repo** (`.github/workflows/docker-deploy.yml`):

- Builds and deploys MAS containers (different from the website container).

**To have “push to main → sandbox website updated”:**

- In the **website** repo workflow (or a dedicated deploy workflow), add a job that:
  - SSHs to Sandbox VM (192.168.0.187),
  - Runs: `cd /opt/mycosoft/website && git pull && docker build ... && docker compose ... up -d mycosoft-website`.
- Store VM host, user, and SSH key in GitHub secrets (e.g. `SANDBOX_HOST`, `SANDBOX_USER`, `SANDBOX_SSH_KEY`).
- After deploy, trigger Cloudflare cache purge (API or manual “Purge Everything” until automated).

**Cloudflare:**

- Cache purge is **required** after deploy so browsers and edge see new assets/pages.
- Either: manual **Purge Everything**, or automate via Cloudflare API in the same workflow.

---

## 5. One-page reference

| Phase | What runs | Where | Port / URL |
|-------|------------|------|------------|
| **Dev** | Next.js dev server | Your PC | http://localhost:3010 |
| **Local Docker** (optional) | Full stack | Your PC | Depends on compose (e.g. 3000 for website) |
| **Sandbox** | Website container | VM 192.168.0.187 | 3000 → sandbox.mycosoft.com (via Cloudflare) |
| **Production** | Same idea as sandbox, different host/domain | Proxmox/production VM | As configured |

**Golden rules:**

1. **Dev = instant updates:** Use only the dev server (npm run dev:next-only) on port 3010; no Docker required.
2. **Deploy = GitHub + VM + Docker + Cloudflare:** Push code → VM pulls and builds Docker → restart website container → purge Cloudflare.
3. **Local Docker** is optional and for full-stack testing only; the “dev site” you work on daily is the Next.js server on 3010.

---

## 6. Scripts and docs

| Script / Doc | Purpose |
|--------------|--------|
| `WEBSITE/website/scripts/start-dev.ps1` | Kill process on 3010 if needed, start `npm run dev:next-only`. |
| `WEBSITE/website/_rebuild_sandbox.py` | Rebuild website image on VM and start container (with NAS mount). |
| `WEBSITE/website/_deploy_sandbox.py` | Restart website container on VM (no rebuild). |
| `MAS/scripts/fix_and_deploy.py` | Fix permissions, pull MAS code, Docker prune, start n8n, check endpoints on VM. |
| `docs/VM_RECOVERY_FEB06_2026.md` | VM recovery and website container run command. |
| `.cursor/rules/mycodao-agent.mdc` | Dev server port 3010 and VM website container + NAS mount. |

---

*Document date: February 6, 2026*
