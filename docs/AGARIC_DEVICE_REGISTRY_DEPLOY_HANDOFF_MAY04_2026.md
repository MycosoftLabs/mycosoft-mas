# Agaric + Device Registry — Deploy Handoff — May 04, 2026

**Audience:** Deploy agent (`@deploy-pipeline` or equivalent)  
**Scope:** Ship to production the **Agaric device page**, **device catalog / Earth Simulator API**, **NatureOS registry strip**, **MAS heartbeat role documentation**, and **Cursor `device-tracker` agent** — already implemented locally; this doc is **what to merge and how to deploy**.

**Implementation record:** `docs/AGARIC_DEVICE_AND_DEVICE_TRACKER_MAY03_2026.md`  
**Device roster (human):** `docs/DEVICES_REGISTRY_MAY03_2026.md`

## Deployment hold — CREP Earth Simulator (May 4, 2026)

**Do not run Sandbox (187) / production website deploy** until the in-flight **CREP Earth Simulator** agent work is complete and Morgan clears this hold. That work touches the same surface area (Earth Sim / CREP); shipping the website now would race or overwrite incomplete changes. MAS-only restarts may still be acceptable if they do not include conflicting Earth Sim routes—when in doubt, wait for the same clear signal.

---

## 1. Repositories and branches

| Repo | Path on dev machine | What changed |
|------|---------------------|--------------|
| **Website** | `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website` | New route `/devices/agaric`, `agaric-details.tsx`, portal + `header` + `mobile-nav`, `lib/devices/catalog.ts`, `app/api/earth-simulator/devices/route.ts`, `app/natureos/devices/registry/page.tsx`, `.cursor/agents/device-tracker.md` |
| **MAS** | `C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas` | `mycosoft_mas/core/routers/device_registry_api.py` (`device_role` Field description), docs + indexes + `.cursor/agents/device-tracker.md` |

**Before deploy:** Ensure both repos are **committed and pushed** to the branch you deploy from (typically `main`). If work sits on a feature branch, merge to `main` first (or document the branch name for Sandbox pull).

---

## 2. Website — Sandbox VM **192.168.0.187**

This is the **user-visible** change (mycosoft.com / sandbox).

### Preconditions

- GitHub has the website commits.
- Deploy agent has `VM_PASSWORD` / SSH from `.credentials.local` (MAS repo) per `vm-credentials.mdc`.

### Steps (canonical)

Follow `.cursor/skills/deploy-website-sandbox/SKILL.md` — summary:

1. `ssh mycosoft@192.168.0.187`
2. `cd /opt/mycosoft/website` (or the canonical website path on 187 if different)
3. `git fetch origin && git reset --hard origin/main` (or your deploy branch)
4. Stop/remove old container: `docker stop mycosoft-website` / `docker rm mycosoft-website` (adjust name if production uses another name)
5. **Rebuild:** `docker build -t mycosoft-always-on-mycosoft-website:latest --no-cache .`
6. **Run with NAS mount (required for device videos/images):**
   ```bash
   docker run -d --name mycosoft-website -p 3000:3000 \
     -v /opt/mycosoft/media/website/assets:/app/public/assets:ro \
     --restart unless-stopped mycosoft-always-on-mycosoft-website:latest
   ```
7. **Cloudflare:** Purge **Everything** for the zone (or at minimum purge `/*` for HTML and `/devices/*`, `/api/earth-simulator/*`).
8. **Verify:**
   - `https://sandbox.mycosoft.com/devices/agaric` (or prod host) returns 200 and renders.
   - `https://…/api/earth-simulator/devices` returns JSON with `agaric-mini`, `agaric-standard`, `agaric-heavy` and `source: "catalog"` when no live units overlay.
   - `/devices` shows Agaric card; header + mobile nav include Agaric.

### NAS assets (Morgan / ops — not blocking HTML deploy)

Agaric media paths are under `public/assets/agaric/` in repo **placeholders**; real files go on NAS: `\\192.168.0.105\mycosoft.com\website\assets\agaric\` (mounted into the container as above). Missing files still render (video fallbacks); upload when ready.

### Optional: repo deploy script

If your pipeline uses `WEBSITE/website/_rebuild_sandbox.py` or `_deploy_sandbox.py`, run those **after** loading credentials — they must still apply the **same NAS `-v` mount** on `docker run`.

---

## 3. MAS — VM **192.168.0.188**

**Change:** `device_registry_api.py` only extends the **Pydantic `Field` description** for `device_role` (documentation for integrators). **No DB migration.**

### Deploy

- Pull MAS repo on 188 to the commit containing this change.
- Restart orchestrator per your standard (e.g. `sudo systemctl restart mas-orchestrator` or Docker restart for the MAS container — match whatever VM 188 uses today).

### Verify

- `GET http://192.168.0.188:8001/health` OK.
- OpenAPI or code review: heartbeat model still accepts string `device_role`; description lists `agaric_mini`, `agaric_standard`, `agaric_heavy`, etc.

---

## 4. Cursor — `device-tracker` agent file

New files:

- `MAS/mycosoft-mas/.cursor/agents/device-tracker.md`
- `WEBSITE/website/.cursor/agents/device-tracker.md`

**No VM deploy.** After git push, either rely on **`python scripts/sync_cursor_system.py --watch`** on the dev machine or run **one-shot** `python scripts/sync_cursor_system.py` from the MAS repo root so `~/.cursor/agents/` picks up the new agent.

---

## 5. Quick verification matrix (post-deploy)

| Check | URL / command |
|-------|----------------|
| Agaric page | `GET /devices/agaric` → 200 |
| Catalog API | `GET /api/earth-simulator/devices` → `success: true`, devices include catalog ids |
| NatureOS registry | `GET /natureos/devices/registry` → “Known device types” section visible |
| MAS health | `GET http://192.168.0.188:8001/health` |

---

## 6. Rollback

- **Website:** Redeploy previous image tag or `git reset` to prior commit on 187, rebuild, re-run container **with NAS mount**, purge Cloudflare.
- **MAS:** Revert `device_registry_api.py` and restart orchestrator (low risk; doc-only change).

---

**End of handoff.** For full file list and local verification notes, see `docs/AGARIC_DEVICE_AND_DEVICE_TRACKER_MAY03_2026.md`.
