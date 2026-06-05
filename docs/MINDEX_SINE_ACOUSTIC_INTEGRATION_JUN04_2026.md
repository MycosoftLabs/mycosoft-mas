# MINDEX SINE Acoustic — MAS Integration (June 4, 2026)

**Date:** June 4, 2026  
**Status:** Complete (MAS code + MINDEX backend)  
**MAS completion:** `docs/MAS_NLM_MINDEX_LIBRARY_INTEGRATION_COMPLETE_JUN04_2026.md`  
**MINDEX completion:** `MINDEX/mindex/docs/MINDEX_SINE_ACOUSTIC_VM_DEPLOY_COMPLETE_JUN04_2026.md`  
**Codex handoff:** `docs/codex-handoffs/MAS_NLM_LIBRARY_CODEX_HANDOFF_JUN04_2026.md`  
**VM:** MINDEX **192.168.0.189:8000** · MAS **192.168.0.188:8001**

---

## Architecture

| System | VM / host | Role |
|--------|-----------|------|
| **MAS orchestrator** | 192.168.0.188:8001 | Agents, NLM training, **library proxy** `/api/mas/mindex/library/*` |
| **MINDEX API** | 192.168.0.189:8000 | Library blobs, SINE analyze/classify, wave/human annotations |
| **Website dev** | localhost:3010 | BFF proxies to **189 directly** (not via MAS) |

Website UI hot path: **3010 → 189**. MAS proxy is for **agents, n8n, NLM training**, not browser playback.

---

## MAS routes (new — June 4, 2026)

| Method | MAS (188) | Proxies to MINDEX |
|--------|-----------|-------------------|
| GET | `/api/mas/mindex/library/health` | `/library/catalog` |
| GET | `/api/mas/mindex/library/catalog` | `/library/catalog` |
| GET | `/api/mas/mindex/library/blobs` | `/library/blobs` |
| GET | `/api/mas/mindex/library/blobs/{id}` | `/library/blobs/{id}` |
| POST | `/api/mas/mindex/library/blobs/{id}/classify` | `/library/blobs/{id}/classify` |
| POST | `/api/mas/mindex/library/blobs/{id}/analyze` | `/sine/blobs/{id}/analyze` |
| GET | `/api/mas/mindex/library/sine/human-tags` | `/sine/training/human-tags` |
| POST | `/api/mas/mindex/library/blobs/{id}/wave-annotation` | `/library/blobs/{id}/wave-annotation` |
| POST | `/api/mas/mindex/library/blobs/{id}/human-identification` | `/library/blobs/{id}/human-identification` |
| POST | `/api/nlm/nmf/persist` | `/nlm/nmf` (source_id = `library_blob_id` when set) |

Client: `mycosoft_mas.integrations.mindex_library_client.MindexLibraryClient`

---

## Env contract

**MAS VM (188):**

```env
MINDEX_API_URL=http://192.168.0.189:8000
MINDEX_INTERNAL_TOKEN=<from VM — never commit>
MAS_API_URL=http://192.168.0.188:8001
```

**Website dev (Codex — unchanged):**

```env
MINDEX_API_URL=http://192.168.0.189:8000
MINDEX_INTERNAL_TOKEN=<same token family>
MAS_API_URL=http://192.168.0.188:8001
```

---

## NLM training

- Category: **`acoustic_library`** (first in default list)
- Data: MINDEX acoustic blobs + `sine/training/human-tags` + wave annotations on blob detail
- Control plane: `POST /api/nlm/training/start` with `"categories": ["acoustic_library"]`

---

## Direct MINDEX endpoints (still valid)

```http
GET  http://192.168.0.189:8000/api/mindex/library/blobs?category=acoustic&limit=50
POST http://192.168.0.189:8000/api/mindex/library/blobs/{uuid}/classify
POST http://192.168.0.189:8000/api/mindex/sine/blobs/{uuid}/analyze
GET  http://192.168.0.189:8000/api/mindex/sine/training/human-tags
POST http://192.168.0.189:8000/api/mindex/library/blobs/{uuid}/wave-annotation
POST http://192.168.0.189:8000/api/mindex/nlm/nmf
```

Header: `X-Internal-Token` or `X-API-Key` (env only).

---

## Verification checklist

1. MINDEX: `curl -sf -H "X-Internal-Token: $TOK" http://192.168.0.189:8000/api/mindex/sine/status`
2. MAS proxy: `curl -sf -H "X-Internal-Token: $TOK" http://192.168.0.188:8001/api/mas/mindex/library/health`
3. MAS orchestrator: `curl -sf http://192.168.0.188:8001/health`
4. Smoke script: `python scripts/smoke_mindex_library_client.py` (skips if down or no token)

---

## Handoff split

| Repo | Owner | Action |
|------|-------|--------|
| **mindex** | Done | Library + SINE on 189 |
| **mycosoft-mas** | Done | Client, trainer, proxy, NMF persist — deploy 188 |
| **website** | Codex | BFF/UI only; do not route Library tab through MAS |
| **NLM** | Minimal | `waveform_refs` + client default URL |
| **mycobrain** | Other agent | Out of scope |
