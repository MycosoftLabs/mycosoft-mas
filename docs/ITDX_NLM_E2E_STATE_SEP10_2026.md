# ITDX + NLM end-to-end state — 10 Sep 2026

Date: Thursday 10 Sep 2026  
Status: Implemented locally + NAS reference copied; live promote only after this doc’s test/deploy receipts  
Author: Cursor for Morgan Rockcoons (CEO/CTO/COO/SAO). RJ Ricasata is CFO.

## What’s live vs not promoted

| Item | State |
|---|---|
| Archived 25,728-param checkpoint on NAS `models/nlm/reference/` | Copied. SHA-256 `0c5fb815bf9b1e75a0e9aa27a3c373eb675d142a93e688b20d3f1084874091b2` |
| `incoming/` | Empty of this synthetic `weights.pt`. Forecast drop folder only |
| Fusarium `p` | Always `null` for this SHA. Stub `0.85` rejected |
| Forecast qualification | **Not promoted.** `training_origin=synthetic`, `qualification_status=candidate` |
| Ollama `:11434` | Not bound. NLM ≠ chat LLM |
| Official Army / FOUO injects | NOT_SUPPLIED. No FOUO ingest |
| New Mamba-shaped training | Not run. Packet oracles ≠ training receipt |

## START_HERE followed

Packet `START_HERE_CURSOR_MAS188.md` treated as normative. Archived checkpoint is SYNTHETIC_TEST (seed 11, 60 epochs). Loader still returns `model_loaded=false` for forecast schema. Replay runtime loads tensors for algorithm testing only.

Fresh numerical oracles: **21/21** — `docs/NLM_NUMERICAL_ORACLE_RESULTS_SEP10_2026.json`. Scope is specified arithmetic only.

## File → destination

| Packet file | Destination | Checksum |
|---|---|---|
| `reference/weights.pt` | NAS `\\192.168.0.105\mycosoft.com\models\nlm\reference\weights.pt` | OK `0c5fb815…` |
| `reference/reference_trained_weights.npz` | same `reference/` | copied |
| `reference/model.json` + inventory | same `reference/` | copied |
| Package docs | MAS `docs/*_SEP10_2026.md` | this file |
| Code | MAS `mycosoft_mas/nlm/formspace/*`, `nlm_api.py`; MINDEX GET on `nlm.nature_embeddings`; ITDX worktree Fusarium BFF |

188 root: fail-closed for blobs. Weights stay on NAS `/mnt/mycosoft-nas/models/nlm/reference`.

## How to test today

- MAS: `GET http://192.168.0.188:8001/api/nlm/health` — `forecast_qualified=false`, `bound_to_ollama=false`. Replay may set `model_loaded=true` if tensors are in-process.
- `POST /api/nlm/decision-path` — tasks include honest `NOT_SUPPLIED` for droids.
- `GET /api/itdx/situation-assessment` — 200, ecology UNQUALIFIED, `p=null`, `live_cop=false`.
- `GET /api/avani/status` — 200.
- Worktree 3010: ITDX popup **only** on `/fusarium/earth-simulator`, default collapsed. `/fusarium` and `/fusarium/soc` have no ITDX dock. No “ITDX backend is not configured” dump.
- Weka: `GET /api/nlm/weka-features` then owner-gated `/api/fusarium/itdx/weka-receipt`. Features are frozen synthetic parameters, not live COP rows.

## MINDEX retain

Existing table `nlm.nature_embeddings` via `POST/GET /api/mindex/internal/nlm/nmf` and `.../nmf/{embedding_id}`. No new tables. No `full_fungi_sync`. Proof IDs filled after live write.

## Memory

`/api/memory/remember` + `/recall` across ephemeral → session → working → semantic → episodic → system. NLM decisions also stored in MINDEX. Not bound to Ollama.

## Leftover NOT_SUPPLIED

- Official Army injects / FOUO
- Calibrated Fusarium ecology `p`
- Live droid / mission execution
- Password-grant owner login (stale; do not reset website main)
- New forecast-family training/serving qualification

## Related

- `docs/NLM_WEIGHTS_IMPLEMENTED_MAS188_SEP10_2026.md`
- Worktree `docs/ITDX_V14_CONFIG_ERROR_FIX_SEP10_2026.md`
