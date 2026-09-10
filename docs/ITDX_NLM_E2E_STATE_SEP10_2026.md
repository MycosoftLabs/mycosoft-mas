# ITDX + NLM end-to-end state — 10 Sep 2026

Date: Thursday 10 Sep 2026  
Status: **NLM tensors live on 188.** Website cutover is owned by a sibling (this agent did not touch 187).  
Author: Cursor for Morgan Rockcoons (CEO/CTO/COO/SAO). RJ Ricasata is CFO.

## Live P0

`GET http://192.168.0.188:8001/api/nlm/health` → `model_loaded=true`, SHA `0c5fb815bf9b1e75a0e9aa27a3c373eb675d142a93e688b20d3f1084874091b2`, path `/mnt/mycosoft-nas/models/nlm/reference`, `forecast_qualified=false`, `bound_to_ollama=false`.

## What’s live vs not promoted

| Item | State |
|---|---|
| Archived 25,728-param checkpoint on NAS `models/nlm/reference/` | **Loaded by MAS** |
| Fusarium `p` | Always `null` for this SHA. Stub `0.85` rejected |
| Forecast qualification | **Not promoted** |
| Ollama `:11434` | Not bound |
| Official Army / FOUO | NOT_SUPPLIED |
| 187 website blue-green | **Not this agent** |

## 188

- Skip-startup ON (`MAS_SKIP_BACKGROUND_STARTUP=1`)
- Root 89% — fail-closed for model blobs
- `NLM_HOME` / `NLM_MODEL_DIR` → NAS reference dir
- Loader: `mycosoft_mas/nlm/formspace/reference_runtime.py` (npz + SHA check)

## MINDEX + memory proof

- MINDEX `embedding_id=3` (`nlm-decision_trace-76b44ef6eb5d`) via `GET /api/mindex/internal/nlm/nmf/3`
- Memory layers: ephemeral `abfe51d2-…`, session `4ad871d1-…`, working `e1ecbe80-…`, semantic `feede3bb-…`, episodic `ea8d5b42-…`, system `73a9a8f2-…`
- Episode `ac84f103-5ace-46aa-ba03-3dae556dc0f0`

## Leftover NOT_SUPPLIED

- Official Army injects / FOUO
- Calibrated Fusarium ecology `p`
- Live droid / mission execution
- Password-grant owner login (stale; do not reset website main)
- New forecast-family training/serving qualification
- Earth Sim / AM·ECM rasters as measured NLM labels

## Related

- `docs/NLM_WEIGHTS_IMPLEMENTED_MAS188_SEP10_2026.md`
