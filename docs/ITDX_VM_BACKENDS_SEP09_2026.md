# ITDX VM backends — 09 September 2026

**Date:** 09 September 2026  
**Status:** 188/189 are the live source of truth for Fusarium/ITDX. No 187 website cutover.  
**Related:** `docs/ITDX_EXTERNAL_SOURCES_INTEGRATION_SEP09_2026.md`, `docs/MAS_MYCA_AVANI_FUSARIUM_ITDX_INTEGRATION_PLAN_SEP09_2026.md`  
**CMMC:** Mycosoft is **pursuing** CMMC L2 — not compliant. **RJ Ricasata is CFO.**  
**CUI:** This surface is outside the CUI boundary. No FOUO. Official injects stay NOT_SUPPLIED.

Ship doc: [ITDX_FUSARIUM_LIVE_SHIP_SEP09_2026.md](ITDX_FUSARIUM_LIVE_SHIP_SEP09_2026.md). This file is the VM health section only.

---

## Health-prove (09 Sep 2026 ~18:47–18:54 UTC)

| Check | Result |
|---|---|
| `http://192.168.0.188:8001/health` | HTTP **200** `degraded` — postgres/redis/crep **healthy**; collectors skipped |
| `http://192.168.0.188:8001/api/itdx/health` | HTTP **200** `healthy`; `in_process` situation-assessment; `self_http_assessment=false` |
| `http://192.168.0.189:8000/health` | HTTP **200** `{"status":"healthy"}` (`/docs` 404 — health path is enough) |
| `http://192.168.0.188:8001/api/nlm/health` | HTTP **200** `model_loaded=true` — Fusarium p stays honest (`qualification=BOUND`, stub `0.85` rejected) |
| `http://192.168.0.188:8001/api/avani/status` | HTTP **200** `healthy`, `is_operational=true` |
| `POST/GET /api/itdx/situation-assessment` | HTTP **200** `in_process=true` `self_http=false` `origin=SYNTHETIC_EXERCISE` |
| n8n `http://192.168.0.188:5678/healthz` | HTTP **200** `ok` — MAS instance on 188. **Not** merged with MYCA 191. |
| Sandbox `http://192.168.0.187:3000` | HTTP **200** — website left running (deploy-pipeline owns blue-green) |
| MycoBrain `http://192.168.0.187:8003/health` | HTTP **200** `ok` (0 devices connected) |
| Earth-2 `192.168.0.249:8220` | Unreachable / timeout. **Not started** (weather already SUPPLIED via Open-Meteo). |

---

## MAS 192.168.0.188

- `mas-orchestrator` **active**, `NRestarts=0`, ~390 MB service RSS. Listen `:8001`.
- **Skip-startup left ON** (`MAS_SKIP_BACKGROUND_STARTUP=1` in `mas-orchestrator.service.d/override.conf`).
  - RAM can take collectors: 64 GB total, **~58 GB available**. No recent OOM in dmesg.
  - Skip stays because collectors **wedge the API**, not because of RAM. Live demo needs 8001/ITDX unwedged. `health.agents` stays `[]` by design.
- Agent **registry** `GET /agents/registry/` HTTP **200**, **48** named agents (Manager, Guardian, ITDXTask8, mycology, finance, simulators, Search, etc.). Not claimed as process-running under skip-startup.
- ITDX mapped roles (listed, not invented as running): grounding, intention, planner, reflection, avani-governor, secretary.
- Protected files **not edited**: orchestrator.py, orchestrator_service.py, guardian, security/, constitution/, soul, identity.py.
- Disk was **98%** (2.7 GB free). Vacuumed journals to 400 MB → **94% / 6.5 GB free**. Docker volumes ~51 GB active (Wazuh/n8n) — not pruned.
- Local `:5432` is not listening on 188; MAS health uses reachable postgres (MINDEX/shared) — healthy from LAN (~111 ms).
- Redis + n8n listening on 188.

**Later data/math:** change NLM / ITDX / MINDEX clients on 188/189. Do **not** rebuild the website for backend numbers.

---

## MINDEX 192.168.0.189

| Service | State |
|---|---|
| `mindex-api` Docker | Up, healthy, `:8000` |
| `mindex-postgres` | Up, healthy, `:5432` TCP open |
| Redis (`77617e9d6755_mindex-redis`) | Up, healthy, `:6379` TCP open |
| `mindex-qdrant` | Up; `GET :6333/readyz` **200** all shards ready. Collections: `mycosoft_knowledge`, `myca_semantic_memory` |
| `mindex-earth-sync` | Up, healthy |
| systemd `mindex-api` | inactive (Docker is the owner — expected) |

No `full_fungi_sync` / alphabetical GBIF. `/taxa` and `/observations` still **404**; situation-assessment uses live GBIF/iNat for biology.

---

## Sandbox 192.168.0.187 (do not cut over)

- `mycosoft-website-green` Up 5 days **healthy**; proxy healthy.
- `mycosoft-website-blue` Up 5 days **unhealthy** — **not stopped / not swapped** (sibling deploy-pipeline).
- Local website origin HTTP **200**. MycoBrain 8003 present.
- RAM tight on the guest (~1.6 GB available of 6.4 GB). Website left alone.

---

## Voice 241 / Earth-2 249 / MYCA 191

- Earth-2 8220 still down. Not started this pass (Open-Meteo weather already SUPPLIED).
- Voice 241 not required for this Fusarium/ITDX backend prove.
- MYCA 191 n8n **not** merged with MAS 188.

---

## Situation-assessment honesty (live curl)

| Channel | Status |
|---|---|
| weather | SUPPLIED (Open-Meteo) |
| biology | SUPPLIED (GBIF / iNat) |
| information / equipment_weapons_assets (public roads only) | SUPPLIED |
| chemistry / physics / decision_authority | UNQUALIFIED (no invented p; NLM BOUND) |
| traffic / pathways / navigation | NOT_SUPPLIED (`REQUEST_DENIED` on Maps Directions/Matrix) |
| Earth-2 | `available=false` |

NLM `model_loaded=true` so Fusarium probability is **not** the old stub 0.85. If NLM later unloads, keep **UNQUALIFIED** (`p=null`).

---

## SSH note (operators)

Password auth is **publickey-only** on 187/188/189. Automation key: Owner1 `mycosoft_vm_automation_ed25519` (187/188). MINDEX 189: Owner1 `id_ed25519`. Never print secrets.
