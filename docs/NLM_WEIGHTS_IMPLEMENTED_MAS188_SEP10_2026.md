# NLM weights implemented on MAS 188 — 10 Sep 2026

Date: Thursday 10 Sep 2026  
Status: Archived reference on NAS + honest replay API. **Not** a calibrated forecast promote.  
Related: `docs/ITDX_NLM_E2E_STATE_SEP10_2026.md`

## START_HERE

Followed `START_HERE_CURSOR_MAS188.md`. Synthetic archived checkpoint preserved. Do not claim six-spectrum foundation or Mamba-1 compatibility.

## Acceptance

- 21/21 numerical oracles: `docs/NLM_NUMERICAL_ORACLE_RESULTS_SEP10_2026.json`
- Targeted pytest: `tests/test_nlm_reference_runtime_sep10.py` + Stage B — 13 passed
- Health contract: `model_loaded` = tensors in-process; `forecast_qualified=false`; `p` never 0.85
- Weights SHA-256: `0c5fb815bf9b1e75a0e9aa27a3c373eb675d142a93e688b20d3f1084874091b2`

## Not promoted

Fresh training curriculum, measured calibration, live COP scoring, official injects.
