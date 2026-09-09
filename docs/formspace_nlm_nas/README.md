# FormSpace NLM — waiting for Morgan weights

**Date:** 09 September 2026  
**Path on the shared NAS mount:** `/mnt/mycosoft-nas/models/nlm/`  
**Sibling MYCA chat GGUF:** `/mnt/mycosoft-nas/models/myca/` — do not put those files here.

This directory is the drop point for **scientific FormSpace / Nature Learning Model** artifacts only.

## Do not put here

- Llama or Nemotron GGUF
- Ollama blobs
- PersonaPlex / Moshi / Whisper
- The frozen ITDX v1.4 synthetic `weights.pt` (legacy reference stays in the v1.4 lab kit)

## When Morgan sends weights, drop

```
incoming/weights.pt
incoming/model.json
```

Optional: chart + calibration artifacts next to those files.

`model.json` should include `weights_sha256`, `model_sha256`, chart id, and calibration id.

Then set `NLM_MODEL_DIR=/mnt/mycosoft-nas/models/nlm/incoming` (or `NLM_HOME=/mnt/mycosoft-nas/models/nlm`).  
188 must **not** copy blobs onto VM root disk.

## Handoff stages (Downloads kit has no weights)

1. Stage A — repository map + implementation status (done locally in MAS docs).
2. Stage B — forecast ledger + causal observation pipeline (started; no fake p).
3. Stages C–G — hazard head, coupling, maps, parity — after real forecast artifacts exist.

`GET /api/nlm/health` stays `model_loaded=false` until those artifacts load. Never Ollama.
