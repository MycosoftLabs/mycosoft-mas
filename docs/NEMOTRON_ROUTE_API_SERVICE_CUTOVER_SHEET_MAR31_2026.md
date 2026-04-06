# Nemotron Route/API/Service Cutover Sheet — MAR31 2026

Date: 2026-03-31  
Status: Ready for staged cutover

## Cutover Summary

Corporate wave is active with Nemotron-first routing and Ollama fallback retained.

## Changed Artifacts

| Component | File | Owner | Cutover Action | Rollback Command |
|---|---|---|---|---|
| Backend mode routing | `mycosoft_mas/llm/backend_selection.py` | MAS backend | Use category-aware mode resolution for provider selection | `setx MYCA_BACKEND_MODE llama` (global) or `setx MYCA_BACKEND_MODE_CORPORATE llama` |
| Routing telemetry/fallback tags | `mycosoft_mas/llm/router.py` | MAS backend | Emit provider/model/category/mode/fallback telemetry per request | `setx MYCA_BACKEND_MODE llama` then restart MAS |
| Role mapping + provider defaults | `config/models.yaml` | MAS platform | Enable Nemotron category role aliases and primary role map | Revert role aliases to `ollama:*` and redeploy MAS |
| Rollout wave gates | `config/llm_migration_rollout.yaml` | MAS platform | Enforce category gates and promotion requirements | Set pending wave status and force `llama` mode |
| Website AVANI proxy (mock removal) | `WEBSITE/website/app/api/myca/route.ts` | Website API | Route to MAS live endpoints only, preserve response contract | Revert file to prior commit on website branch |
| Smoke matrix validation | `scripts/llm/run_nemotron_smoke_matrix.py` | MAS QA | Validate category selection and chat probe telemetry | Keep script; run with `MYCA_BACKEND_MODE=llama` to baseline |

## Environment Toggles

| Toggle | Purpose |
|---|---|
| `MYCA_BACKEND_MODE=hybrid` | default staged migration mode |
| `MYCA_BACKEND_MODE_CORPORATE=nemotron` | corporate wave activation |
| `MYCA_BACKEND_MODE_INFRA=nemotron` | infra wave activation |
| `MYCA_BACKEND_MODE_DEVICE=nemotron` | device wave activation |
| `MYCA_BACKEND_MODE_ROUTE=nemotron` | route wave activation |
| `MYCA_BACKEND_MODE_NLM=nemotron` | NLM wave activation |
| `MYCA_BACKEND_MODE_CONSCIOUSNESS=nemotron` | consciousness wave activation |

## Deployment Sequence

1. Deploy MAS changes (`backend_selection.py`, `router.py`, `models.yaml`, rollout config).
2. Run smoke matrix and confirm gates.
3. Deploy website route proxy update (`app/api/myca/route.ts`).
4. Validate AVANI contracts.
5. Promote next category by env toggle only.

