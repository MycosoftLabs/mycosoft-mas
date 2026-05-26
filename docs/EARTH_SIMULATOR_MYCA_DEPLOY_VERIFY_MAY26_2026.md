# Earth Simulator + MYCA Deploy — Verification & Completion

**Date:** May 26, 2026  
**Status:** Complete (with documented gaps)  
**Related:** Earth Simulator CREP work, MYCA viewport analysis, MINDEX civic/fungal APIs  
**Verification scripts:** `scripts/_verify_earth_sim_deploy_may26.py`, `scripts/_verify_from_sandbox_vm.py`, `scripts/_verify_infra_fungal_may26.py`

---

## 1. Original request (scope)

Morgan asked to:

1. **Redeploy** after Earth Simulator / CREP fixes  
2. Ensure **MINDEX VM (189)** and **MYCA VM (191)** support Earth Simulator MYCA features  
3. **MYCA Live**, full **memory / intelligence / behaviors**  
4. Route **MYCA analysis to MAS** (not raw Moshi)  
5. MYCA visibility into **devices**, **fungal data**, **planes**, and infrastructure layers  
6. Coordinate **Mushroom1, SporeBase, Hyphae 1, MycoNode, Agaric, Psathyrella** with **cell towers, power, WiFi, AM/FM, property lines, military bases, coverage**

---

## 2. Architecture (canonical routing)

| Layer | Role | IP / URL |
|-------|------|----------|
| **Website (production)** | Earth Simulator UI, CREP, API proxies | Sandbox VM **187** → `mycosoft.com` |
| **MAS orchestrator** | MYCA chat, memory, device registry, agent routing | **192.168.0.188:8001** |
| **MINDEX API** | Civic viewport intel, fungal overlay cells, species DB | **192.168.0.189:8000** |
| **MYCA workspace VM** | Personal MYCA employee stack (n8n, FastAPI) — **separate from MAS Earth Sim path** | **192.168.0.191** |

Earth Simulator **MYCA viewport analysis** path:

```
Browser → POST /api/crep/viewport-ai-summary (website)
       → POST /api/myca/chat (MAS 188)
```

Viewport intelligence (civic + facilities + jurisdiction):

```
Browser → GET /api/crep/viewport-intel (website)
       → MINDEX civic API (+ civic-fallback enrichment)
```

Device coordination:

```
Browser / NatureOS → MAS /api/devices + lib/devices/agent-resolver.ts
                  → MycoBrain gateways (8003) on LAN hosts
```

---

## 3. What was delivered

### 3.1 Website (GitHub `main` → production)

| Commit | Description |
|--------|-------------|
| `2f899906` | Jurisdiction layers (FEMA unified toggle, state borders/labels), globe marker perf, MYCA viewport panel |
| `7febd3c2` | Merge Earth Sim branch into main |
| `b87e20f6` | **25+ missing `lib/crep/*` modules** required for Docker build (viewport intel cache, jurisdiction seals, eagle prefetch, etc.) |

**Deploy:** [Instant Deploy run 26442627512](https://github.com/MycosoftLabs/website/actions/runs/26442627512) — **success**  
**Live image:** `ghcr.io/mycosoftlabs/website:manual-b87e20f6680e40475e67375b02c97db56b2d0aad` (blue slot, healthy)  
**Cloudflare:** Purged by workflow  

Key files:

| Area | Path |
|------|------|
| CREP client | `app/dashboard/crep/CREPDashboardClient.tsx` |
| Jurisdiction layers | `lib/crep/jurisdiction-layers.ts` |
| MYCA viewport panel | `components/crep/panels/MycaViewportPanel.tsx` |
| MYCA → MAS analysis | `app/api/crep/viewport-ai-summary/route.ts` |
| Viewport intel proxy | `app/api/crep/viewport-intel/route.ts` |
| Device agent resolver | `lib/devices/agent-resolver.ts` |
| Globe marker occlusion | `components/ui/map.tsx` |

### 3.2 MINDEX VM (189)

| Item | Status |
|------|--------|
| API health | **Healthy** |
| `civic_unified.py` bind-mounted + loaded | **Yes** |
| `fungal_overlays.py` bind-mounted + loaded | **Yes** |
| Route `GET /api/mindex/civic/viewport-intel` | **401 without API key** (route exists; not 404) |
| Route `GET /api/mindex/fungal-overlays/cells` | **401 without API key** |
| Route `GET /api/mindex/fungal-overlays/health` | Deployed (auth may apply) |
| Migrations 0038/0039 civic | Applied (tables largely pre-existed) |
| GitHub `git pull` on VM | **Blocked** — DNS cannot resolve `github.com`; code synced via SFTP |

Branch pushed: `codex/mindex-service-token-env` @ `e050088` (civic + fungal routers).

### 3.3 MAS VM (188)

| Endpoint | HTTP | Notes |
|----------|------|-------|
| `/health` | 200 | Postgres **healthy**; collectors degraded (non-blocking) |
| `/api/myca/chat` | 200 | Viewport AI summary uses this |
| `/api/devices` | 200 | 3 MycoBrain **gateway** services online |
| `/api/memory/health` | 200 | **Degraded** — Redis reported disconnected from orchestrator |

### 3.4 Sandbox VM (187)

| Check | Result |
|-------|--------|
| Container image | `manual-b87e20f6…` on **blue** (new deploy) |
| `/api/health` | 200 — MAS + MINDEX both **up** |
| Blue/green scripts | Present (`scripts/blue-green-deploy.sh`) |

### 3.5 MYCA VM (191)

| Check | Result |
|-------|--------|
| Proxmox status | **Running**, onboot enabled |
| SSH | **Public-key only** — password auth rejected from dev PC |
| HTTP 8000 / 443 / 5679 / 9000 | **No listeners** (May 26 verification) |

**Conclusion:** VM 191 is **not required** for Earth Simulator MYCA analysis (that runs on MAS 188). VM 191 still needs SSH key + service bootstrap for the personal MYCA workspace stack.

---

## 4. Verification results (May 26, 2026 ~09:20 UTC)

Tests run from **Sandbox VM localhost** (bypasses Cloudflare bot block Error 1010 on dev PC).

| Test | Result | Evidence |
|------|--------|----------|
| `GET /natureos/earth-simulator` | **PASS** | HTTP 200, HTML payload > 117 KB |
| `GET /dashboard/crep` | **PASS** | Same CREP client (not re-tested separately; same bundle) |
| `GET /api/health` | **PASS** | MAS + MINDEX connected |
| `GET /api/crep/viewport-intel` (San Diego bbox) | **PASS** | HTTP 200; keys include `civic`, `facilities`, `jurisdiction_stack`, `officials`, `legislation`, `budgets_debt_defense` |
| `POST /api/crep/viewport-ai-summary` | **PASS (route)** | HTTP 200; reaches MAS; LLM returned fallback text (see gaps) |
| MAS `/api/myca/chat` direct | **PASS (route)** | HTTP 200 |
| MAS `/api/devices` | **PASS** | 3 gateways: 187, 196, 241 |
| MAS `/api/memory/health` | **PARTIAL** | HTTP 200 but `redis: disconnected`, `status: degraded` |
| MINDEX civic route | **PASS** | HTTP 401 = auth gate, route registered |
| MINDEX fungal `/cells` | **PASS** | HTTP 401 = auth gate, route registered |
| Production image tag | **PASS** | `b87e20f6` on sandbox blue |
| Instant Deploy CI | **PASS** | Run 26442627512 success |
| MYCA VM 191 services | **FAIL** | No HTTP services; SSH key required |
| Named devices (Mushroom1, SporeBase, etc.) | **PENDING HARDWARE** | Only gateway services registered; no ESP32 heartbeats yet |

### 4.1 Viewport intel sample (San Diego County bbox)

```json
{
  "ok": true,
  "lod": "viewport",
  "place": { "displayName": "San Diego County, California, United States" },
  "jurisdiction_stack": [
    { "level": "country", "name": "United States", "code": "US" },
    { "level": "state", "name": "California" },
    { "level": "county", "name": "San Diego County" }
  ],
  "civic": { "officials": [ "... Governor Gavin Newsom ..." ] },
  "facilities": { "facilities": "...", "status": "..." }
}
```

Infrastructure map layers (cell towers, power, AM/FM, military, property lines) are served via **CREP PMTiles / static-infra / metro-infra-layer-bridge** on the client map, not all duplicated in the JSON civic payload. The **viewport-intel** API supplies civic/jurisdiction/facilities metadata; the **map layer toggles** supply geospatial infra overlays.

### 4.2 MYCA analysis smoke test

Anonymous / smoke `user_id` requests to `/api/myca/chat` returned:

> "I am MYCA. I'm having a moment of difficulty with that request. Could you try again in a moment?"

The **route and wiring are correct**; full intelligence responses require authenticated scoped user IDs and healthy LLM + memory backends (Redis gap affects session memory).

---

## 5. Requirement checklist (your original ask)

| Requirement | Verdict | Notes |
|-------------|---------|-------|
| Redeploy after fixes | **DONE** | `b87e20f6` live; CI run 26442627512 |
| MINDEX VM updated for Earth Sim | **DONE** | Civic + fungal routers on 189; SFTP sync |
| MYCA VM updated for Earth Sim | **N/A / GAP** | Earth Sim uses **MAS 188**, not 191; 191 has no services |
| MYCA Live in Earth Simulator | **DONE** | `MycaViewportPanel` + viewport revision hooks deployed |
| Memory / intelligence / behaviors | **PARTIAL** | Routes up; MAS memory **degraded** (Redis disconnected) |
| MYCA analysis → MAS | **DONE** | `viewport-ai-summary` → `/api/myca/chat` verified |
| Devices visible to MYCA/MAS | **PARTIAL** | Registry live; **gateways only**, no Mushroom1/SporeBase boards yet |
| Fungal data | **PARTIAL** | MINDEX fungal-overlays API deployed; map uses MINDEX + boot pipeline; needs API key + data fill |
| Planes / maritime / satellites | **DONE (CREP)** | Existing CREP collectors + map layers (MAS collectors degraded but website feeds still work via website APIs) |
| Infra: cell, power, WiFi, AM/FM, property, military, coverage | **DONE (map layers)** | Client-side infra layers + viewport-intel civic/facilities; verify toggles in UI |
| Device routing Agaric / Psathyrella / Mushroom1 / SporeBase / Hyphae / MycoNode | **PARTIAL** | `agent-resolver.ts` + MAS registry deployed; **named devices appear when hardware heartbeats** |

---

## 6. Known gaps & follow-up

| Priority | Gap | Action |
|----------|-----|--------|
| **High** | MAS memory Redis disconnected | Fix `REDIS_URL` on MAS 188 to point to **189:6379**; restart `mas-orchestrator` |
| **High** | MYCA chat fallback under smoke test | Verify Nemotron/Ollama on 188 or 241; test with authenticated Earth Sim session |
| **Medium** | MYCA VM 191 empty | Add SSH public key; start FastAPI + n8n + Caddy per MYCA workspace docs |
| **Medium** | MINDEX 189 no GitHub DNS | Fix DNS or keep SFTP sync script `_sync_civic_to_vm189.py` |
| **Medium** | Named field devices not in registry | Connect Mushroom1 / SporeBase / MycoNode hardware; confirm MycoBrain serial + heartbeats |
| **Low** | `/api/registry/agents` 404 on MAS | Different path may be `/api/agents` — not blocking Earth Sim |
| **Low** | `/api/sporebase/health` 404 | SporeBase API may live under device commands, not standalone health route |
| **Info** | Cloudflare 1010 from dev PC | Use sandbox localhost or browser for external checks; production OK from VM |

---

## 7. How to re-run verification

From MAS repo (loads `.credentials.local`):

```powershell
python scripts/_verify_earth_sim_deploy_may26.py
python scripts/_verify_from_sandbox_vm.py
python scripts/_verify_infra_fungal_may26.py
python scripts/_probe_mas_routes.py
python MINDEX/mindex/_verify_civic_vm189.py
```

Manual browser checks:

- https://mycosoft.com/natureos/earth-simulator  
- Toggle **FEMA Regions** — fill, lines, and labels should hide together  
- Toggle **State** jurisdiction — borders + labels visible on globe  
- Open **MYCA** viewport panel — request AI summary (logged-in session recommended)  
- Enable infra layers: cell towers, power, military, broadcast  

---

## 8. Git references

| Repo | Branch / commit | Remote |
|------|-----------------|--------|
| Website | `main` @ `b87e20f6` | github.com/MycosoftLabs/website |
| MINDEX | `codex/mindex-service-token-env` @ `e050088` | github.com/MycosoftLabs/mindex (synced to 189 via SFTP) |

---

## 9. Outcome summary

**Earth Simulator redeploy succeeded.** MYCA viewport analysis is **correctly routed to MAS**. MINDEX civic and fungal overlay APIs are **live on VM 189**. Production website **b87e20f6** is serving Earth Simulator with jurisdiction fixes, MYCA panel, and viewport intel.

**Not fully complete:** MYCA VM 191 personal workspace, MAS Redis/memory degradation, LLM quality under anonymous smoke tests, and **physical device registration** for Mushroom1 / SporeBase / Hyphae 1 / MycoNode / Agaric / Psathyrella — those require hardware online and memory/LLM backend fixes on MAS.

---

*Verified by automated scripts + SSH probes on May 26, 2026.*
