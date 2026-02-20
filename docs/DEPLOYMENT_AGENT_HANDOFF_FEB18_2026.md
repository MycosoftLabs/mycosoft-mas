# Deployment Agent Handoff – February 18, 2026

**Purpose:** Instructions for the **deployment agent** to deploy the Mycosoft website to Sandbox VM. All code is committed and pushed to GitHub. Execute in another Cursor session; use this document as the single reference.

---

## 1. What You Are Deploying

| Repo | Branch | Latest commits (at handoff) |
|------|--------|-----------------------------|
| **Website** | main | d16dbb0 security purge, ce84cec mobile+team, cce488c HierarchicalTaxonomyTree fix, 7bcc182 About overhaul, d2c9786 Search genetics UI, 022b7bf Defense neuromorphic |

**Key changes in this deploy:**
- Defense neuromorphic (Defense 2, Fusarium, OEI Capabilities)
- Search UI (genetics sequence box contrast)
- About page overhaul (video, particles, neural network, team bios)
- Mobile + team changes
- HierarchicalTaxonomyTree build fix
- Security: hardcoded secrets purged

---

## 2. Prerequisites

- **Credentials:** Load from `.credentials.local` in MAS or website repo root. Variables: `VM_SSH_PASSWORD` or `VM_PASSWORD`, `VM_SSH_USER=mycosoft`. **NEVER ask the user for password.**
- **Cloudflare (optional):** For cache purge, set in `.env.local` or env: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ZONE_ID`.
- **SSH access:** `mycosoft@192.168.0.187` (Sandbox VM).

---

## 3. VM Layout (Reference)

| VM | IP | Role |
|----|-----|------|
| **Sandbox** | 192.168.0.187 | Website container (port 3000) |
| MAS | 192.168.0.188 | Orchestrator (8001) |
| MINDEX | 192.168.0.189 | API (8000) |
| GPU Node | 192.168.0.190 | PersonaPlex Bridge (8999) |

---

## 4. Commands – Two Options

### Option A: Automated (Recommended)

From the **website repo root** (e.g. `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website`):

```powershell
# Load credentials (run first)
Get-Content ".credentials.local" | ForEach-Object {
    if ($_ -match "^([^#=]+)=(.*)$") {
        [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
    }
}

# Run deploy script (handles git pull, build, container restart, NAS mount, Cloudflare purge)
python _rebuild_sandbox.py
```

The script:
1. Syncs repo to `origin/main`
2. Rebuilds Docker image (`--no-cache`)
3. Stops/removes old container
4. Starts new container **with NAS mount** and env vars
5. Waits for health
6. Purges Cloudflare (if configured)

### Option B: Manual (SSH step-by-step)

```bash
# 1. SSH to Sandbox
ssh mycosoft@192.168.0.187

# 2. Pull latest code
cd /opt/mycosoft/website
git fetch origin
git reset --hard origin/main

# 3. Rebuild image
docker build -t mycosoft-always-on-mycosoft-website:latest --no-cache .

# 4. Stop and remove old container
docker stop mycosoft-website 2>/dev/null || true
docker rm mycosoft-website 2>/dev/null || true

# 5. Start new container (CRITICAL: include NAS mount)
docker run -d --name mycosoft-website -p 3000:3000 \
  -v /opt/mycosoft/media/website/assets:/app/public/assets:ro \
  -e MAS_API_URL=http://192.168.0.188:8001 \
  -e MYCOBRAIN_SERVICE_URL=http://192.168.0.187:8003 \
  -e MYCOBRAIN_API_URL=http://192.168.0.187:8003 \
  --restart unless-stopped mycosoft-always-on-mycosoft-website:latest

# 6. Verify
sleep 10
docker ps | grep mycosoft-website
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
```

**7. Cloudflare:** Purge Everything (Dashboard → Caching → Purge Everything, or use API).

---

## 5. Verification Checklist

| Check | Command/URL | Expected |
|-------|-------------|----------|
| Container running | `docker ps \| grep mycosoft-website` | Container listed, status Up |
| HTTP 200 | `curl -s -o /dev/null -w "%{http_code}" http://localhost:3000` | 200 |
| Live site | https://sandbox.mycosoft.com/ | Page loads |
| NAS media | https://sandbox.mycosoft.com/assets/mushroom1/ | Assets load (confirms mount) |
| Defense page | https://sandbox.mycosoft.com/defense | Neuromorphic UI |

---

## 6. Critical Rules

- **NAS mount:** Container MUST include `-v /opt/mycosoft/media/website/assets:/app/public/assets:ro` or device videos/images will not load.
- **Credentials:** Load from `.credentials.local`; never prompt user for password.
- **Build order:** Build BEFORE stopping the old container; do not replace a working site with a failed build.
- **Image name:** Use `mycosoft-always-on-mycosoft-website:latest` consistently in build and run.

---

## 7. Troubleshooting

| Issue | Action |
|-------|--------|
| Docker build timeout (Docker Hub TLS) | Script tries legacy builder first; if still failing, check VM network/DNS to auth.docker.io |
| HTTP 500 / container crash | Check `docker logs mycosoft-website` |
| No media (videos/images) | Verify NAS mount in `docker inspect mycosoft-website` |
| Cloudflare purge skipped | Set `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ZONE_ID` in env or `.env.local` |

---

## 8. Related Docs

- `docs/SANDBOX_LIVE_TESTING_PREP_FEB18_2026.md` – VM layout, health checks
- `docs/DEPLOYMENT_HANDOFF_SANDBOX_FEB18_2026.md` – Short checklist
- `.cursor/agents/deploy-pipeline.md` – Deploy agent protocol

---

## 9. GitHub Repos

- **Website:** https://github.com/MycosoftLabs/website (main)
- **MAS:** https://github.com/MycosoftLabs/mycosoft-mas (main)
