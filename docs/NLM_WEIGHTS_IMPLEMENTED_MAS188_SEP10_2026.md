# NLM weights implemented on MAS 188 — 10 Sep 2026

Date: Thursday 10 Sep 2026  
Status: **Live tensors loaded.** Replay-qualified only. **Not** a calibrated Fusarium forecast promote.  
Related: `docs/ITDX_NLM_E2E_STATE_SEP10_2026.md`

## P0 health (live, proven)

`GET http://192.168.0.188:8001/api/nlm/health`

```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_name": "nlm",
  "model_version": "0.1.0",
  "forecast_qualified": false,
  "qualification_status": "candidate",
  "training_origin": "synthetic",
  "architecture_family": "native_tied_A_rank1",
  "weights_sha256": "0c5fb815bf9b1e75a0e9aa27a3c373eb675d142a93e688b20d3f1084874091b2",
  "bound_to_ollama": false,
  "model_dir": "/mnt/mycosoft-nas/models/nlm/reference",
  "load_reason": "Archived synthetic reference loaded for algorithm replay. Not a calibrated Fusarium forecast. p stays null."
}
```

`model_loaded` is true only because 47 finite tensors / 25,728 params are in-process from the NAS npz + matching `weights.pt` SHA. Forecast `p` stays null. NLM is not bound to `:11434`.

## START_HERE

Followed `START_HERE_CURSOR_MAS188.md`. Archived checkpoint is SYNTHETIC_TEST (seed 11, 60 epochs). Not a six-spectrum foundation model. Not Mamba-1 compatible.

## What was placed on NAS

Path: `/mnt/mycosoft-nas/models/nlm/reference/` (Windows `\\192.168.0.105\mycosoft.com\models\nlm\reference\`)

| File | Role |
|---|---|
| `weights.pt` | Archived 25,728-param checkpoint. SHA-256 `0c5fb815bf9b1e75a0e9aa27a3c373eb675d142a93e688b20d3f1084874091b2` |
| `reference_trained_weights.npz` | Same tensors, NumPy, `allow_pickle=False` (this is what the process loads) |
| `model.json`, `AUDIT.json`, `WEIGHT_INVENTORY.csv`, `SOURCE_LOCATIONS.md` | Inventory / audit |

`incoming/` has no synthetic `weights.pt`. 188 root stay fail-closed for blobs (89% / 11G). `NLM_HOME` / `NLM_MODEL_DIR` point at the NAS reference dir. Skip-startup ON (`MAS_SKIP_BACKGROUND_STARTUP=1`).

## Acceptance

- 21/21 numerical oracles: `docs/NLM_NUMERICAL_ORACLE_RESULTS_SEP10_2026.json`
- Targeted pytest `tests/test_nlm_reference_runtime_sep10.py`: 7 passed
- Live `/api/nlm/runtime` 200, `model_loaded=true`
- Live `/api/nlm/weka-features` 200, `p=null`
- Live `/api/avani/status` 200
- Live `/api/itdx/situation-assessment` 200, `live=false`
- Live `/api/nlm/decision-path` 200, droids `NOT_SUPPLIED`, `p=null`

## Data families

| Family | Wired vs NOT_SUPPLIED |
|---|---|
| Archived FormSpace replay (npz/pt) | **Wired** — live `model_loaded=true` |
| Inverse-variance fusion + native SSM state | **Wired** — replay / Weka features |
| MINDEX `nlm.nature_embeddings` retain | **Wired** (table exists on 189; POST via `/api/mindex/internal/nlm/nmf`) |
| MYCA 6-layer remember/recall | **Wired** (`/api/memory/remember` + `/recall` proven) |
| AVANI governance `/status` | **Wired** — advisory only |
| ITDX situation-assessment | **Wired** — ecology UNQUALIFIED, not live COP |
| Earth Sim / fungal atlas / AM·ECM display scores | **NOT_SUPPLIED** as NLM training labels (display ≠ measured) |
| Official Army / FOUO injects | **NOT_SUPPLIED** — no FOUO ingest |
| Calibrated Fusarium ecology `p` | **NOT_SUPPLIED** — `forecast_qualified=false` |
| Live droid / mission execution | **NOT_SUPPLIED** |
| New Mamba-shaped training / serving qualification | **NOT_SUPPLIED** — packet did not train |
| Ollama / Nemotron `:11434` | **Not bound** — NLM ≠ chat LLM |

## Not promoted

Fresh measured curriculum, calibration population, live COP scoring, official injects. Do not treat `model_loaded=true` as forecast qualification.
