# MINDEX SINE Acoustic — MAS Integration Note (June 4, 2026)

**Date:** June 4, 2026  
**Status:** Complete (documentation only — no MAS code changes in this pass)  
**MINDEX completion:** `MINDEX/mindex/docs/MINDEX_SINE_ACOUSTIC_VM_DEPLOY_COMPLETE_JUN04_2026.md`  
**MINDEX commit:** `a0e391a` on `https://github.com/MycosoftLabs/mindex`  
**VM:** MINDEX **192.168.0.189:8000**

---

## Purpose

Record how the **MAS** platform relates to the June 2026 **MINDEX Library + SINE acoustic** deployment so agents do not confuse this work with MycoBrain, MQTT, or chemistry tracks.

**Out of scope for this document:** MycoBrain firmware/service (separate agent), website UI commits (Codex).

---

## Architecture (unchanged for MAS)

| System | VM / host | Role |
|--------|-----------|------|
| **MAS orchestrator** | 192.168.0.188:8001 | Agents, device registry, MYCA routing |
| **MINDEX API** | 192.168.0.189:8000 | Library blobs, SINE analyze/classify, Postgres/Qdrant |
| **Website dev** | localhost:3010 | BFF proxies to 188/189 via `.env.local` |

The website dev BFF calls **MINDEX directly** for Library/SINE routes (`/api/natureos/mindex/library`, `/api/mindex/sine/*`). MAS is not in the hot path for acoustic playback unless a future agent orchestrates ingest or device-tied analysis.

---

## Env contract (website dev — reference for MAS agents)

Set on the **website** machine (Codex maintains `WEBSITE/website/.env.local`):

```env
MINDEX_API_URL=http://192.168.0.189:8000
MINDEX_API_BASE_URL=http://192.168.0.189:8000
MINDEX_INTERNAL_TOKEN=<first token from VM MINDEX_INTERNAL_TOKENS>
MAS_API_URL=http://192.168.0.188:8001
```

Do **not** point acoustic inference at localhost GPU; see `docs/GPU_TOPOLOGY_CONSOLIDATED_MAY24_2026.md`.

---

## Surfaces (for testers)

| Surface | URL (dev) | Backend |
|---------|-----------|---------|
| MINDEX console Library | `http://localhost:3010/natureos/mindex` → Acoustic tab | BFF → 189 library + classify |
| SINE player | `http://localhost:3010/sensing/sine/player` | BFF → 189 sine + library catalog |

Production website deploy is **Codex** scope (Sandbox 187 + Cloudflare).

---

## MINDEX endpoints MAS may call later

If MAS agents need acoustic classification without the website:

```http
GET  http://192.168.0.189:8000/api/mindex/health
GET  http://192.168.0.189:8000/api/mindex/library/blobs?category=acoustic&limit=50
POST http://192.168.0.189:8000/api/mindex/library/blobs/{uuid}/classify
POST http://192.168.0.189:8000/api/mindex/sine/blobs/{uuid}/analyze
```

Header: `X-Internal-Token: <MINDEX_INTERNAL_TOKENS first value>` (never commit token; use env).

---

## What was *not* changed in MAS repo (this pass)

- No updates to `mycosoft_mas/agents/*` for SINE.
- No MycoBrain service or MQTT bridge edits.
- No new MAS API routes required for Library tab smoke tests.

Existing cross-links remain valid:

- `docs/MINDEX_APP_CONSOLE_MAY27_2026.md` — console tabs context
- `docs/LIVE_NETWORK_STACK_STATUS_MAY27_2026.md` — MAS/MINDEX/Redis health (separate from acoustic classifier)
- `docs/EARTH_SIMULATOR_FIELD_MYCOBRAIN_BACKEND_HANDOFF_MAY27_2026.md` — field devices (not acoustic library)

---

## Verification checklist (MAS operator)

From a machine on `192.168.0.0/24` with valid `MINDEX_INTERNAL_TOKEN`:

1. `curl -sf -H "X-Internal-Token: $TOK" http://192.168.0.189:8000/api/mindex/health` → `"db":"ok"`
2. `curl -sf -H "X-Internal-Token: $TOK" "http://192.168.0.189:8000/api/mindex/sine/status"` → `acoustic_blobs` ≥ 2000
3. MAS orchestrator: `curl -sf http://192.168.0.188:8001/health` → healthy (independent)

---

## Handoff split

| Repo | Owner | Action |
|------|-------|--------|
| **mindex** | Done | `a0e391a` pushed; VM 189 deployed |
| **mycosoft-mas** | This doc only | No code deploy required for acoustic |
| **website** | Codex | Frontend + BFF commit/push |
| **mycobrain** | Other agent | Do not modify in acoustic threads |
