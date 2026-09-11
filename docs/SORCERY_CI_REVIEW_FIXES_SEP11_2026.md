# Sorcery / CI / Review Fixes — Sep 11, 2026

**Date:** Sep 11, 2026  
**Status:** Complete (fixes pushed; Instant Deploy on website main not raced)  
**Related:** website PRs #317/#318/#319, MAS PRs #152/#153, `GITHUB_CI_TRIAGE_SEP10_2026.md`, `SORCERY_AI_GITHUB_TRIAGE_SEP10_2026.md`

## Inventory

| Source | Finding | Disposition |
|---|---|---|
| Sourcery (`sourcery-ai[bot]`) on website #317/#318/#319 and MAS #152/#153 | Rate-limited Reviewer's Guide only; no inline comments | No code change. Older Sourcery work already merged as website #305 / MAS #150 (Sep 10). |
| Bugbot website #317 | Approved, no findings | None |
| Bugbot website #318 | 4 NLM honesty / URL issues | Fixed on `fix/sorcery-ci-review-sep11` |
| Bugbot website #319 | ERA5 timer stall, invented weight row, preferBound, wind governor | Fixed on `fix/sorcery-ci-review-sep11` |
| Bugbot + Cursor security MAS #152/#153 | Path leak, rglob DoS, duplicate scans, `str(exc)`, compound_count page size, /load catalog | Fixed on `fix/sorcery-ci-review-sep11` |
| `myca-ci` / `myca-validate` on MAS main `5561e893` and #153 `9a8e41625` | `scripts/check_myca_workflow_drift.py` missing (`Errno 2`) | Script restored; policy updated so MAS vs MYCA n8n trees are not required mirrors |
| Website Instant Deploy on `2a46b851` | In flight at inventory | Not raced; 187 primary left up |
| Website CI cancelled on `952d8da5` | Superseded by #319 merge | Infra/supersede, not a code defect |
| Bot PRs #182 / #115 | `action_required` approval | Not this cut |
| Scheduled MAS Dependencies on `fc450a80` | Older SHA, not today's NLM PRs | Out of scope |

NLM locks held: not Ollama, no `p=0.85`, `forecast_p` null if unqualified. RJ remains CFO. No secrets / CUI. No device marketing media edits.

## Website comment → fix

| Comment | File | Fix |
|---|---|---|
| #318 `engineState` is available whenever health/runtime/weights succeed | `app/api/fusarium/nlm/status/route.ts` | `unavailable` if MAS down; `available` only if `model_loaded`; else `unloaded`. MAS URL via `resolveMasServerBaseUrl()`. |
| #318 panel `live` on MAS OR; “loaded” when weightCount=0 | `components/fungi-compute/nlm-panel.tsx` | Live only if `model_loaded` or weight count > 0; honest degraded copy |
| #318 metrics `NLM_BASE_URL` raw env | `app/api/myca/nlm/metrics/route.ts` | `NLM_BASE_URL = resolveMasServerBaseUrl()` |
| #318 `engineOnline` requires `status === 'healthy'` | same | `engineOnline = healthResult.ok` |
| #319 High: `startAnimation` restarts interval every 400ms gate | `components/crep/layers/field-raster-layer.tsx` | Already no-ops when `timerRef.current` is set; left as-is |
| #319 invents `runtime-sha` weight row | `lib/fusarium/scenario-sim/nlm-from-status.ts` | Removed synthetic append |
| #319 `preferBound` returns MAS `NOT_SUPPLIED` over local `UNQUALIFIED` | `lib/itdx/local-situation-bind.mjs` | Local `UNQUALIFIED` preferred |
| #319 wind layer never registers with governor | `components/crep/earth2/wind-vector-layer.tsx` | `registerAnimatedLayer("earth2-wind", "wind", …)` + cleanup |

## MAS comment / CI → fix

| Comment / run | File | Fix |
|---|---|---|
| `myca-ci` missing drift script | `scripts/check_myca_workflow_drift.py` | Restored. Does not fail on expected MAS (`n8n/workflows`) vs MYCA (`workflows/n8n`) split. Fails only on invalid JSON or same-filename checksum mismatch. |
| #152/#153 rglob + hash on every request | `mycosoft_mas/nlm/formspace/scientific_loader.py` | 60s cache, unique roots, walk/depth/artifact caps, hash cache |
| Absolute paths + SHA on `/weights` `/runtime` | `scientific_loader.py`, `nlm_api.py` | Relative/basename/`nlm-home`; SHA kept for loaded-weight match |
| Duplicate overlapping scan | `_disk_checkpoints` in `nlm_training_api.py` | Unique roots + `seen` + 200 walk / 50 row cap + 60s cache |
| `str(exc)` at live status | `nlm_training_api.py` | `"error": "nlm_status_unavailable"` |
| `compound_count` = `len(compounds)` after `limit=25` | `nlm_training_api.py` | `stats.compound_count` or `total_compounds` or null |
| `/load` only searched in-memory | `nlm_training_api.py` | `_checkpoint_catalog()` (memory + disk); unique disk ids |

Protected files not edited: `orchestrator.py`, `orchestrator_service.py`, guardian, `security/`, constitution, soul yaml, `identity.py`.

## SHAs

Recorded after push. See PR comments for the live SHAs.

| Repo | Branch | Base |
|---|---|---|
| MycosoftLabs/mycosoft-mas | `fix/sorcery-ci-review-sep11` | `5561e893` |
| MycosoftLabs/website | `fix/sorcery-ci-review-sep11` | `2a46b851` |

## Verify

- `python scripts/check_myca_workflow_drift.py` → `ok: true` (99 MAS + 13 MYCA JSON files; no filename collisions)
- Website scenario-sim `node --test` needs the repo TS runner (bare `node --test` cannot resolve `./packet` from `.ts`); the invented-weight assertion remains in `lib/fusarium/scenario-sim/__tests__/scenario-sim.test.mjs`
- Instant Deploy: do not stop 187 primary; merge website only after that run finishes or if CI on the next SHA is required without cutover
