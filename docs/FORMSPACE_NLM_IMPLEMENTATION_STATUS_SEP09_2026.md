# FormSpace NLM Implementation Status — 09 September 2026

**Date:** 09 September 2026  
**Status:** Stage A complete as discovery. Stage B started. Weights absent.  
**CMMC:** Mycosoft is **pursuing** CMMC L2 — not compliant. **RJ Ricasata is CFO.**

Handoff names this file `IMPLEMENTATION_STATUS.md`. Dated title is required by Mycosoft doc rules.

Statuses: `NOT_STARTED` | `IMPLEMENTED_UNTESTED` | `VERIFIED_LOCAL` | `VERIFIED_INTEGRATED` | `BLOCKED`.

---

## Modes

| Mode | Status | Notes |
|---|---|---|
| `legacy_reference` | `VERIFIED_LOCAL` (frozen kit) | ITDX v1.4 synthetic 25,728-param replay. SHA `1d3fe486…` preserved. Not production `/api/nlm`. |
| `nlm_forecast_only` | `NOT_STARTED` | Waiting for Morgan forecast artifacts on NAS. |
| `coupled_forecast` | `NOT_STARTED` | Requires registered dynamics + filter (Stage D). |

---

## Stages

| Stage | Status | Evidence |
|---|---|---|
| A Preserve + map | `VERIFIED_LOCAL` | `docs/FORMSPACE_NLM_REPOSITORY_MAP_SEP09_2026.md` |
| B Ledger + causal pipeline | `VERIFIED_LOCAL` | `mycosoft_mas/nlm/formspace/` + `tests/test_formspace_stage_b_sep09.py` |
| C Task 12 hazard head | `NOT_STARTED` | No forecast weights |
| D FormSpace coupling | `NOT_STARTED` | |
| E Links / VOI / maps | `NOT_STARTED` | |
| F Live parity | `BLOCKED` | 188 skip-startup ON; no artifacts; no 187 |
| G Transfer / behavior | `NOT_STARTED` | Must not delay C–F |

---

## Acceptance gates (handoff §14)

| ID | Status |
|---|---|
| Scalar oracle `acceptance_math.py` | `VERIFIED_LOCAL` — 19/19 |
| M06 duplicate evidence | `VERIFIED_LOCAL` — pipeline |
| M07 future `available_at` | `VERIFIED_LOCAL` — pipeline |
| I01 frozen hashes | `VERIFIED_LOCAL` — recorded, not overwritten |
| I03 ledger immutability | `VERIFIED_LOCAL` |
| I05 unsupported/failed/cancelled/stale export | `VERIFIED_LOCAL` — null probabilities |
| M01–M05, M08–M15 | `NOT_STARTED` in platform (oracle only) |
| I02 / I04 / I06 | `NOT_STARTED` |
| S01–S04 | `NOT_STARTED` — no trained forecast model |

---

## `/api/nlm`

| Check | Status |
|---|---|
| `model_loaded=false` until NAS forecast artifacts | Required. Loader refuses stubs and GGUF. |
| Never Ollama / `:11434` | Enforced in probe (`models/myca` + `*.gguf` ignored). |
| Never stub `0.85` as ecology `p` | Predict refuses unload; forecasts persist `null` hazards. |
| 188 VM disk blobs | Forbidden. Artifacts stay on NAS. |

---

## NAS ready-for-weights

| Item | Value |
|---|---|
| Shared mount | `/mnt/mycosoft-nas` |
| NLM only | `/mnt/mycosoft-nas/models/nlm/` |
| Expected drop | `incoming/weights.pt` + `incoming/model.json` |
| Empty except | README pointing at Stages A–F |
| Windows helper | `scripts/_nlm_nas_ready_folder_windows.py` |
| 188 helper | `scripts/_nlm_nas_mount_188.py` — mkdir NLM tree only; sibling owns `models/myca` |

---

## Blocked / honest gaps

- Downloads FormSpace zip has **no weights**. Do not wait for `.pth` there.
- Frozen v1.4 `weights.pt` is **SYNTHETIC_TEST**. Not the new forecast NLM.
- MINDEX forecast-ledger migration not started.
- Live 188 reload of this code is not done this pass (skip-startup ON).
- Hidden-onset end-to-end demo is Stage C+ and needs real artifacts.
