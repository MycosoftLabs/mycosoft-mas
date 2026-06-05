# Codex Handoff — MAS NLM ↔ MINDEX Library (June 4, 2026)

**Date:** June 4, 2026  
**Repo:** `MAS/mycosoft-mas` only (MAS VM deploy)  
**Completion doc:** `docs/MAS_NLM_MINDEX_LIBRARY_INTEGRATION_COMPLETE_JUN04_2026.md`

---

## What changed (MAS)

1. **`MindexLibraryClient`** — talks to `MINDEX_API_URL` + `/api/mindex/library/*` and `/api/mindex/sine/*`
2. **NLM training** — `acoustic_library` category pulls blobs + human-tags from MINDEX into JSONL
3. **MAS proxy** — `GET/POST /api/mas/mindex/library/...` on orchestrator **188:8001**
4. **NMF persist** — `POST /api/nlm/nmf/persist` forwards to MINDEX `POST /api/mindex/nlm/nmf`
5. **NLM package** — `waveform_refs` from `library_blob_id`; `NLM/client.py` default port fixed to **8000**

---

## What Codex should NOT change

| Area | Reason |
|------|--------|
| **Website** `WEBSITE/website/app/**`, `components/**`, BFF routes | UI hot path already calls **189** directly; Morgan/Codex owns website |
| **MINDEX** schema/migrations on 189 | Already deployed (`MINDEX_WAVE_ANNOTATIONS_BACKEND_COMPLETE_JUN04_2026.md`) |
| **MycoBrain** service/firmware | Separate track |
| **Mock training data** in MAS | Removed — real MINDEX only |

---

## Env on MAS VM (188) — set before restart

```env
MINDEX_API_URL=http://192.168.0.189:8000
MINDEX_INTERNAL_TOKEN=<first value from VM MINDEX_INTERNAL_TOKENS>
MAS_API_URL=http://192.168.0.188:8001
```

Optional: `MINDEX_API_KEY` if internal token unavailable.

---

## Deploy (MAS only)

```bash
ssh mycosoft@192.168.0.188
cd /home/mycosoft/mycosoft/mas   # or canonical MAS path on VM
git pull origin main
sudo systemctl restart mas-orchestrator
curl -sf http://127.0.0.1:8001/health
```

No website rebuild. No Cloudflare purge for this change.

---

## Verification curls (from LAN)

```bash
export TOK="<MINDEX_INTERNAL_TOKEN>"

# Proxy health
curl -sf http://192.168.0.188:8001/api/mas/mindex/library/health \
  -H "X-Internal-Token: $TOK"

# List acoustic blobs
curl -sf "http://192.168.0.188:8001/api/mas/mindex/library/blobs?limit=5" \
  -H "X-Internal-Token: $TOK"

# Human tags for training
curl -sf "http://192.168.0.188:8001/api/mas/mindex/library/sine/human-tags?limit=10" \
  -H "X-Internal-Token: $TOK"

# NMF persist (replace blob uuid)
curl -sf -X POST http://192.168.0.188:8001/api/nlm/nmf/persist \
  -H "Content-Type: application/json" -H "X-Internal-Token: $TOK" \
  -d '{"packet":{"frame_type":"nmf","observation":{}},"library_blob_id":"a742bbd6-383d-4a7f-8945-e3c7d55c1982"}'

# Start acoustic_library training prep (async)
curl -sf -X POST http://192.168.0.188:8001/api/nlm/training/start \
  -H "Content-Type: application/json" \
  -d '{"categories":["acoustic_library"],"epochs":1}'
```

---

## Codex follow-ups (optional, website)

- No change required for SINE player if BFF already proxies wave-annotation / human-identification to 189
- Model-training page may use **188** `/api/nlm/training/*` (unchanged contract; now includes `acoustic_library`)

---

## Git state

MAS changes are local until committed/pushed. After push, deploy 188 only.
