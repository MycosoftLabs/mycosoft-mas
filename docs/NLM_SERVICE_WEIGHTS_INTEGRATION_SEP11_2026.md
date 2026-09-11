# NLM Service Weights Integration — Sep 11, 2026

**Date:** September 11, 2026  
**Status:** Complete (MAS service live; website SHA for ba065cf1 Instant Deploy)  
**Related:** `docs/NLM_MODEL_TRAINING_APP_FIX_SEP11_2026.md`, `docs/NLM_WEIGHTS_IMPLEMENTED_MAS188_SEP10_2026.md`

## Service URL

NLM is the MAS orchestrator router, not a second process and not Ollama.

| Surface | URL |
|---------|-----|
| Service | `http://192.168.0.188:8001/api/nlm` |
| Health | `GET /api/nlm/health` |
| Weights | `GET /api/nlm/weights` |
| Runtime | `GET /api/nlm/runtime` |
| Training console | `GET /api/nlm/training/console` |
| Training jobs | `GET /api/nlm/training/health` — `jobs_available: false` on 188 fail-closed |

`bound_to_ollama: false`. Unqualified forecast `p` is `null`. `forecast_qualified: false`.

## Weight inventory (on disk, no new pulls)

Local `MAS/NLM` is protocol/code only — no `.pt` / `.safetensors` blobs.

188 NAS `/mnt/mycosoft-nas/models/nlm/`:

| Path | Role |
|------|------|
| `reference/weights.pt` | Frozen ITDX v1.4 synthetic (`0c5fb815bf9b1e75a0e9aa27a3c373eb675d142a93e688b20d3f1084874091b2`, 117846 bytes) |
| `reference/reference_trained_weights.npz` | Reference tensors (25,728 params) |
| `reference/model.json` | Metadata |
| `incoming/` | Empty — waiting for Morgan forecast weights |
| `data/` | Present; scanned, not invented |

`GET /api/nlm/weights` lists every on-disk artifact. GGUF / `models/myca` / Ollama paths are ignored.

## MAS / MINDEX routes

| Consumer | Route |
|----------|--------|
| Website BFF | `MAS_API_URL=http://192.168.0.188:8001` → `/api/nlm/*` |
| MINDEX catalogs | `http://192.168.0.189:8000/api/mindex` (`/stats`, `/taxa`, `/compounds`) |
| Training page | `/api/natureos/nlm-training` → MAS console + weights |
| NatureOS panel | `components/fungi-compute/nlm-panel.tsx` → same BFF |
| Fusarium | `/api/fusarium/nlm/status` → `/api/nlm/health`, `/runtime`, `/weights`, `/training/status` |

## Locks honored

- No HuggingFace / Ollama model pulls (188 root ~89% fail-closed).
- No stub `p = 0.85`.
- Training start remains **503** while skip-startup / no GPU job capacity.
- RJ is CFO. No CUI. No mock training rows.
- Instant Deploy on 187 left to agent `ba065cf1`.

## Verify

```bash
curl -sS http://192.168.0.188:8001/api/nlm/health
curl -sS http://192.168.0.188:8001/api/nlm/weights
curl -sS http://192.168.0.188:8001/api/nlm/training/console
```
