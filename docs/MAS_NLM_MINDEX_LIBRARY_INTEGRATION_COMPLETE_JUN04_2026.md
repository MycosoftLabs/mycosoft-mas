# MAS ↔ MINDEX Library ↔ NLM Integration — Complete (June 4, 2026)

**Date:** June 4, 2026  
**Status:** Complete  
**Related:** `docs/MINDEX_SINE_ACOUSTIC_INTEGRATION_JUN04_2026.md`, `docs/codex-handoffs/MAS_NLM_LIBRARY_CODEX_HANDOFF_JUN04_2026.md`

---

## Scope delivered (P0–P4)

| Phase | Deliverable |
|-------|-------------|
| **P0** | `mycosoft_mas/integrations/mindex_library_client.py` — async httpx client for library + SINE |
| **P1** | `acoustic_library` category in `nlm/trainer.py`; real MINDEX fetch; `nlm_training_api.py` prepares data before GPU train |
| **P2** | `nlm/library_frames.py`, harness `library_blob_id`, `fusarium/nlm_bridge.classify_library_blob`, NLM `waveform_refs` |
| **P3** | `core/routers/mindex_library_proxy_api.py` — `/api/mas/mindex/library/*` passthrough |
| **P4** | `POST /api/nlm/nmf/persist` → MINDEX `/api/mindex/nlm/nmf` |

---

## New / modified files

**Created**

- `mycosoft_mas/integrations/mindex_library_client.py`
- `mycosoft_mas/nlm/library_frames.py`
- `mycosoft_mas/core/routers/mindex_library_proxy_api.py`
- `scripts/smoke_mindex_library_client.py`
- `tests/test_mindex_library_client.py`
- `docs/MAS_NLM_MINDEX_LIBRARY_INTEGRATION_COMPLETE_JUN04_2026.md`
- `docs/codex-handoffs/MAS_NLM_LIBRARY_CODEX_HANDOFF_JUN04_2026.md`

**Modified (MAS)**

- `mycosoft_mas/nlm/trainer.py`
- `mycosoft_mas/core/routers/nlm_training_api.py`
- `mycosoft_mas/core/routers/nlm_api.py`
- `mycosoft_mas/core/myca_main.py`
- `mycosoft_mas/fusarium/nlm_bridge.py`
- `mycosoft_mas/harness/nlm_interface.py`
- `mycosoft_mas/integrations/__init__.py`

**Modified (NLM package — minimal)**

- `NLM/nlm/client.py` — default `MINDEX_API_URL` → `http://192.168.0.189:8000`
- `NLM/nlm/data/rooted_frame_builder.py` — `waveform_refs` param + `library_blob_id` in readings

---

## MAS VM env (192.168.0.188)

```env
MINDEX_API_URL=http://192.168.0.189:8000
MINDEX_INTERNAL_TOKEN=<from VM — never commit>
# or MINDEX_API_KEY=<key>
MAS_API_URL=http://192.168.0.188:8001
NLM_INFERENCE_URL=http://192.168.0.188:8001
```

---

## Verification

| Check | Command | Result (dev PC, Jun 4) |
|-------|---------|------------------------|
| Unit tests | `py -3 -m pytest tests/test_mindex_library_client.py -v` | **5 passed** |
| Import | `from mycosoft_mas.integrations.mindex_library_client import MindexLibraryClient` | **ok** |
| Smoke (LAN) | `python scripts/smoke_mindex_library_client.py` | **189 reachable**; 401 without token (expected) |
| Deploy MAS | SSH 188 → pull → `sudo systemctl restart mas-orchestrator` | **Pending** (code not pushed in this session) |

Post-deploy curls (with token):

```bash
curl -sf http://192.168.0.188:8001/api/mas/mindex/library/health -H "X-Internal-Token: $TOK"
curl -sf "http://192.168.0.188:8001/api/mas/mindex/library/blobs?limit=3" -H "X-Internal-Token: $TOK"
curl -sf -X POST http://192.168.0.188:8001/api/nlm/nmf/persist -H "Content-Type: application/json" \
  -d '{"packet":{"type":"nmf"},"library_blob_id":"<uuid>"}'
```

---

## Out of scope (unchanged)

- Website BFF / SINE player UI (Codex)
- MycoBrain / MQTT
- MINDEX schema (already on 189)

---

## Post-deploy token fix (June 5, 2026)

Production **188:8001** returned **401** on `/api/mas/mindex/library/health` until `MINDEX_INTERNAL_TOKEN` in `/home/mycosoft/mycosoft/mas/.env` was synced from **189** and `mas-orchestrator` was restarted.

**Details:** `docs/MAS_NLM_LIBRARY_TOKEN_FIX_COMPLETE_JUN05_2026.md`  
**Automation:** `scripts/ensure_mas_mindex_env_188.py`  
**Verified:** library health, blobs, sine human-tags → **200**; MINDEX **189** health → **db ok**.

---

## Lessons learned

- Website hot path stays on 189; MAS proxy is for **agents and n8n**, not UI.
- Removed placeholder mock rows from `NLMTrainer._fetch_category_data`; non-wired categories return empty JSONL.
- `NLM_API_URL` default now prefers MAS self (`188:8001`) via `_nlm_upstream_url()`.
- After deploy, confirm **systemd vs Docker** on 188 and sync `MINDEX_INTERNAL_TOKEN` to the active listener (see Jun 5 token fix doc).
