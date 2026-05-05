# Security real systems rebuild — Deploy handoff — May 04, 2026

**Audience:** Deploy agent (`@deploy-pipeline`, `infrastructure-ops`, or scripted SSH).  
**Purpose:** Ship the **SOC Postgres + MAS APIs + `/security` UI** work already merged to GitHub. **Do not edit** `.cursor/plans/security_real_systems_rebuild_*.plan.md`.

**Spec / completion:** `docs/SECURITY_REAL_SYSTEMS_REBUILD_MAY03_2026.md` · `docs/SECURITY_REAL_SYSTEMS_REBUILD_COMPLETE_MAY03_2026.md`

---

## 0. Preconditions

- **LAN** to `192.168.0.0/24`.
- **Git:** `main` (or your release branch) **pushed** for **MINDEX**, **MAS**, **Website** before VM pulls.
- **Secrets:** Load `VM_PASSWORD` / `VM_SSH_PASSWORD` from MAS repo `.credentials.local` (never commit). MAS on 188 needs **`MINDEX_DATABASE_URL`** (or equivalent) pointing at **189** Postgres so `/api/incidents/health` reports DB configured.

---

## 1. Order (required)

1. **MINDEX (189)** — DB schema + API (SOC tables must exist before MAS relies on them).  
2. **MAS (188)** — orchestrator restart so routers + pollers + L2/L3 load.  
3. **Website (187)** — Docker rebuild + **NAS mount** + Cloudflare purge.

---

## 2. MINDEX — `192.168.0.189`

- **Goal:** Postgres has `soc_ops` objects (`device_inventory`, `security_incidents`, `incident_chain`, `redteam_runs`, `redteam_findings`, `compliance_controls`, `compliance_docs` per spec). Apply **any pending migrations** from the MINDEX repo that introduced this schema, then restart API.

- **Runbook:** `.cursor/skills/deploy-mindex/SKILL.md` (from MAS repo Cursor merge) or local `MINDEX/mindex` `_deploy_mindex.py` after loading `.credentials.local`.

- **Quick SSH pattern:** `ssh mycosoft@192.168.0.189` → `cd /home/mycosoft/mindex` → `git fetch && git reset --hard origin/main` → run your migration command (compose job, `alembic`, or SQL bundle per repo) → `docker compose` rebuild/restart **api** only (leave Postgres/Redis/Qdrant up).

- **Verify:** `curl -s http://192.168.0.189:8000/health`

---

## 3. MAS — `192.168.0.188`

- **Includes:** `incidents_api`, `redteam_api` (`/api/redteam/soc-runs`, `/api/redteam/soc-findings`), `security_events_stream`, `incident_source_poller`, `redteam/layer2_scoped.py`, `layer3_ai.py`, `myca_main` startup wiring.

- **Runbook:** `.cursor/skills/deploy-mas-service/SKILL.md` — typically `cd /home/mycosoft/mycosoft/mas` → pull → **`sudo systemctl restart mas-orchestrator`** **or** Docker rebuild per your production layout (match whatever 188 already uses; do not invent a second orchestrator).

- **Verify:**

```text
GET http://192.168.0.188:8001/api/incidents/health
GET http://192.168.0.188:8001/api/redteam/health
GET http://192.168.0.188:8001/api/redteam/soc-runs?limit=5
GET http://192.168.0.188:8001/api/redteam/soc-findings?limit=10
```

---

## 4. Website — Sandbox `192.168.0.187`

- **User-visible:** `/security/redteam` (SOC tab + `soc-runs` / `soc-findings` via BFF), `/security/compliance` (MAS bundle / regenerate), plus any prior `/security/network` and `/security/incidents` wiring from the same initiative.

- **Runbook:** `.cursor/skills/deploy-website-sandbox/SKILL.md`

- **Non-negotiable:** Container **must** mount NAS read-only:

```bash
docker run -d --name mycosoft-website -p 3000:3000 \
  -v /opt/mycosoft/media/website/assets:/app/public/assets:ro \
  --restart unless-stopped mycosoft-always-on-mycosoft-website:latest
```

- **Cloudflare:** **Purge Everything** (or at minimum `/security/*` and `/api/security/*`) after container is healthy.

- **Verify:** Compare `http://localhost:3010/security/redteam` (admin) vs `https://sandbox.mycosoft.com/security/redteam` after purge.

---

## 5. Rollback

- Revert VM git SHAs and restart prior containers / `systemctl` units; DB rollback only if migrations were backward-compatible (prefer forward-only migrations).

---

## 6. Known gap (post-deploy, optional)

- **`/api/redteam/authorize`:** Website BFF uses **`requireAdmin()`**; MAS may still issue short-lived session tokens. Hardening = forward Supabase JWT to MAS — not required for initial SOC UI deploy.
