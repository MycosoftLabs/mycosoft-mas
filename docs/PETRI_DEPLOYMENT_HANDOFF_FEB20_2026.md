# Petri Full Integration Deployment Handoff

**Date:** Feb 20, 2026  
**Status:** Ready for deploy agent  
**Related:** petri-full-integration plan, PETRI_INTEGRATION_DEMO_WALKTHROUGH_FEB20_2026.md

---

## Scope

Deploy the completed Petri integration to production:
- Website (VM 187)
- MAS (VM 188)
- MINDEX migration (VM 189) – optional, when ready

---

## Pre-Deployment Checklist

- [ ] All code committed and pushed to GitHub (MAS, website, MINDEX, petridishsim)
- [ ] Credentials loaded from `.credentials.local` (VM_PASSWORD / VM_SSH_PASSWORD)
- [ ] No uncommitted secrets

---

## 1. Website (Sandbox VM 192.168.0.187)

### Steps

1. SSH: `ssh mycosoft@192.168.0.187` (use password from `.credentials.local`)
2. Navigate: `cd /opt/mycosoft/website` (or configured website path)
3. Pull: `git fetch origin && git reset --hard origin/main`
4. Rebuild: `docker build -t mycosoft-always-on-mycosoft-website:latest --no-cache .`
5. Stop old container: `docker stop mycosoft-website 2>/dev/null; docker rm mycosoft-website 2>/dev/null`
6. Run new container (**must include NAS mount**):
   ```bash
   docker run -d --name mycosoft-website -p 3000:3000 \
     -v /opt/mycosoft/media/website/assets:/app/public/assets:ro \
     --restart unless-stopped mycosoft-always-on-mycosoft-website:latest
   ```
7. Purge Cloudflare cache (Purge Everything for mycosoft.com)
8. Verify: `curl -s -o /dev/null -w "%{http_code}" http://localhost:3000` → 200

---

## 2. MAS (VM 192.168.0.188)

### Steps

1. SSH: `ssh mycosoft@192.168.0.188`
2. Navigate to MAS repo path (e.g. `/home/mycosoft/mycosoft/mas` or equivalent)
3. Pull: `git fetch origin && git reset --hard origin/main`
4. Restart orchestrator: `sudo systemctl restart mas-orchestrator`
5. Verify: `curl -s http://localhost:8001/health` → `{"status":"healthy"}` or similar
6. Petri status: `curl -s http://localhost:8001/api/simulation/petri/status`

### Environment

Ensure `PETRIDISHSIM_URL` is set if petridishsim runs elsewhere (e.g. `http://192.168.0.187:8004` or local).

---

## 3. MINDEX Migration (VM 192.168.0.189) – Optional

Apply petri simulation tables when MINDEX persistence is desired:

1. SSH: `ssh mycosoft@192.168.0.189`
2. Run migration: `psql -U mindex -d mindex -f /path/to/migrations/0015_petri_simulation.sql`
   - Or use your migration runner (e.g. `alembic upgrade head` if wired)

Migration file: `MINDEX/mindex/migrations/0015_petri_simulation.sql`

---

## 4. PetriDishSim (if deployed separately)

If petridishsim runs as a separate service:

- **Location:** `Petri Dish Sim/petridishsim`
- **Run:** `uvicorn` or equivalent; expose port (e.g. 8004)
- **MAS:** Set `PETRIDISHSIM_URL` to that service URL

---

## 5. Post-Deploy Verification

| Check | Command / Action |
|-------|------------------|
| Website | Open https://sandbox.mycosoft.com/apps/petri-dish-sim |
| MAS health | `curl http://192.168.0.188:8001/health` |
| Petri status | `curl http://192.168.0.188:8001/api/simulation/petri/status` |
| Agent control | `curl -X POST http://192.168.0.188:8001/api/simulation/petri/agent/control -H "Content-Type: application/json" -d '{"action":"monitor","source":"deploy"}'` |

---

## 6. Rollback

### Website

```bash
docker stop mycosoft-website
docker rm mycosoft-website
# Run previous image if tagged
docker run -d --name mycosoft-website -p 3000:3000 \
  -v /opt/mycosoft/media/website/assets:/app/public/assets:ro \
  --restart unless-stopped <previous-image>:latest
```

### MAS

```bash
sudo systemctl restart mas-orchestrator
# Or revert git and restart
```

---

## 7. References

- Plan: `c:\Users\admin2\.cursor\plans\petri-full-integration_d6c1497d.plan.md`
- Demo walkthrough: `docs/PETRI_INTEGRATION_DEMO_WALKTHROUGH_FEB20_2026.md`
- VM layout: `docs/VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md`
- Credentials: `.credentials.local` (gitignored)
