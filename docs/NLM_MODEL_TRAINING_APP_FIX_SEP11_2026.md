# NLM Model Training App Fix — Sep 11, 2026

**Date:** September 11, 2026  
**Status:** Complete  
**Related:** live page `/natureos/model-training`, MAS `/api/nlm/training/console`

## Outcome

The Nature Learning Model training app on mycosoft.com said **MAS degraded** and showed empty catalogs even though MAS `192.168.0.188:8001` was up. That copy came from skip-startup `/health` (`status: degraded` because collectors are skipped) being forwarded as a MAS outage. Empty owner-gated Supabase/Firebase model lists and unauthenticated MINDEX paths made the page look unplugged.

## Product locks held

- NLM is **not** Ollama. `bound_to_ollama: false`.
- Unqualified forecast `p` stays **null**. `forecast_qualified: false`.
- No calibrated-NLM or live-COP claim.
- Training jobs stay **fail-closed** on 188. No new model pulls.
- RJ is CFO. No CUI. No secrets.

## What was plugged

- MAS `GET /api/nlm/training/console` — honest MAS/NLM/MINDEX/checkpoint payload.
- MAS `GET /api/nlm/training/health` and disk checkpoint list.
- `POST /api/nlm/training/start` returns **503** under skip-startup / fail-closed.
- Website BFF `GET /api/natureos/nlm-training` is public and treats reachable MAS as **online**.
- Models and MINDEX panels read live MAS NLM + `/api/mindex/*` (auth headers). Empty from source is empty, not MAS down.
- UI chips: skip-startup note, not **MAS DEGRADED**.

## What still cannot train

188 remains FAIL-CLOSED / skip-startup. GPU training jobs are **not** started. The page must say that. Catalogs, loaded NLM, and last checkpoints (if any on disk) remain visible.

## Verify

- `http://192.168.0.188:8001/health` HTTP 200
- `http://192.168.0.188:8001/api/nlm/health` `model_loaded` from live runtime
- `https://mycosoft.com/natureos/model-training` HTTP 200
- Page does not say MAS degraded while 188:8001 is reachable
