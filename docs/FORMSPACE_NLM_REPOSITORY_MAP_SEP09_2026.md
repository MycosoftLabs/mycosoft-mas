# FormSpace NLM Repository Map — 09 September 2026

**Date:** 09 September 2026  
**Status:** Stage A discovery. No new forecast weights in the Downloads handoff (~81 KB, 6 files).  
**CMMC:** Mycosoft is **pursuing** CMMC L2 — not compliant. **RJ Ricasata is CFO.**  
**CUI:** This surface is outside the CUI boundary. No FOUO.

Handoff names this file `REPOSITORY_MAP.md`. Dated title is required by Mycosoft doc rules.

---

## Compartments (do not mix)

| Stack | Path | Role |
|---|---|---|
| **FormSpace / scientific NLM** | `/mnt/mycosoft-nas/models/nlm/` | Forecast artifacts only. 188 must not store blobs on VM disk. |
| **Llama + Nemotron (MYCA chat)** | `/mnt/mycosoft-nas/models/myca/` (sibling mount) | Ollama GGUF. Never called NLM. Never loaded by `/api/nlm`. |
| Shared mount root | `/mnt/mycosoft-nas` → `//192.168.0.105/mycosoft.com` | One CIFS mount. Two subtrees. |

---

## MAS (this repo)

| Component | Actual path | Notes |
|---|---|---|
| `/api/nlm` router | `mycosoft_mas/core/routers/nlm_api.py` | Health, load, Stage B `observations` / `forecasts`. |
| ITDX ecology status | `mycosoft_mas/core/routers/itdx_api.py` | Must stay UNQUALIFIED `p=null` until a real forecast head scores. |
| Legacy LLM-style wrapper | `mycosoft_mas/nlm/models/base_model.py` | `load()` no longer stubs `is_loaded=True`. |
| Inference service | `mycosoft_mas/nlm/inference/service.py` | Ready only after scientific probe. Never Ollama. |
| FormSpace Stage B | `mycosoft_mas/nlm/formspace/` | Contracts, ledger, causal pipeline, NAS probe. |
| Loader default | `NLM_HOME=/mnt/mycosoft-nas/models/nlm` | Ignores `models/myca` and `*.gguf`. |

There is **no** FormSpace atlas/filter/hazard-head module in MAS yet (Stages C–D).

---

## Scientific NLM package (`CODE/MAS/NLM`)

| Component | Actual path |
|---|---|
| NatureLearningModel | `nlm/model/nlm_model.py` |
| SSM / graph / heads | `nlm/model/ssm_blocks.py`, `graph_encoders.py`, `heads.py` |
| Checkpoints | `nlm/training/` (expects `model_state_dict` `.pt` / safetensors) |

This is **not** Llama. No production forecast checkpoint is in that repo today.

---

## Frozen ITDX v1.4 FormSpace lab (Downloads kit — do not overwrite)

**Root:** `C:\Users\Owner1\Downloads\Mycosoft_ITDX26_v1.4.0_Standalone_Lab\Mycosoft_ITDX26_v1.4.0`

| Item | Path / value |
|---|---|
| FormSpace code | `formspace/nlm_formspace/` (`atlas`, `behavior`, `calibration`, `data`, `engine`, `model`, `server`) |
| Lab worker | `formspace/lab_worker.py` |
| Frozen replay weights | `local_data/cli_runs/*/model/weights.pt` (~117,846 bytes) |
| `weights_sha256` | `0c5fb815bf9b1e75a0e9aa27a3c373eb675d142a93e688b20d3f1084874091b2` |
| `model_sha256` (legacy hint) | `1d3fe486d94507600f5c82e2be527ac9be42ff9a8a59586e7f158397a1a3b792` |
| Schema | `formspace-environmental-reference/0.1.0` |
| Parameters | 25728 |
| Origin | `SYNTHETIC_TEST` |

Mode: **legacy_reference** only. Do not copy these bytes into `/mnt/mycosoft-nas/models/nlm/`. Do not set `model_loaded=true` from them.

Handoff also recorded source commit `8716d02` and numerical reference `bd919a4`. Current NLM snapshot in the v1.4 kit: `formspace/source_inventory.json`.

---

## Cursor handoff kit (spec, not weights)

`C:\Users\Owner1\Downloads\FormSpace_NLM_Cursor_Handoff\FormSpace_NLM_Cursor_Handoff`

| File | Role |
|---|---|
| `START_HERE_CURSOR.md` | Immediate stages |
| `FormSpace_NLM_Cursor_Implementation_Handoff.md` | Canonical spec |
| `acceptance_math.py` | Scalar oracle (19/19) |
| `numerical_fixtures.json` | Port fixtures |
| `PACKAGE_MANIFEST.json` | SHA-256 of packaged files |
| `VALIDATION_REPORT.json` | LaTeX + numerical tests only |

No `.pth` / `.pt` in that zip.

---

## Service bindings

| Service | Binding |
|---|---|
| MAS orchestrator | `192.168.0.188:8001` — skip-startup **ON** |
| `/api/nlm/health` | `model_loaded=false` until NAS forecast artifacts |
| Ollama `:11434` | MYCA chat only. Not NLM. |
| MINDEX | `192.168.0.189:8000` — forecast ledger persistence not migrated yet |
| Website 187 | Out of scope this pass |

Proposed handoff URLs mapped onto **existing** `/api/nlm` (not new production hosts):

- `POST /api/nlm/observations`
- `POST /api/nlm/forecasts`
- `GET /api/nlm/forecasts/{id}`
- `POST /api/nlm/forecasts/{id}/patch` — always refuse overwrite (I03)
