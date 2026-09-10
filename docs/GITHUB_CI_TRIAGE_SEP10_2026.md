# GitHub CI Triage — SEP10 2026

**Date:** 10 September 2026  
**Status:** Code fixes merged; MINDEX and Arraylake bake green; `mas-ci` watching newest main  
**Owner:** devops-engineer (gate hub = GitHub)  
**Related:** `docs/MASTER_DOCUMENT_INDEX.md`, `.cursor/CURSOR_DOCS_INDEX.md`

Morgan asked for a full red-check inventory across MAS, MINDEX, platform-infra, and the website shipping branch. Live `mycosoft-website` on 187 was not stopped. No second blue-green cutover. Instant Deploy `34510868160` (ITDX, not this lane) was left running.

## Inventory (now)

| Repo | Workflow | Was | Root cause | Fix SHA / PR | Now |
|------|----------|-----|------------|--------------|-----|
| `MycosoftLabs/mycosoft-mas` | `mas-ci` | failure on `acf425f62` (collection error in `tests/test_nlm_reference_runtime_sep10.py`) | PR #142 imported `formspace.contracts` / `forecast_ledger` / `observation_pipeline` without those files on GitHub `main` | [#145](https://github.com/MycosoftLabs/mycosoft-mas/pull/145) merge `c3f06f9fd` (rebase commit `d41fd01fc`) | FormSpace files are on `main`. Later Fusarium docs merges cancelled earlier `mas-ci` via concurrency. Newest run [`34510948289`](https://github.com/MycosoftLabs/mycosoft-mas/actions/runs/34510948289) on `a1dd0efd3` (#148) is the gate. |
| `MycosoftLabs/mycosoft-mas` | `Dependencies` | failure (tox 3.13 hit live VM integration: `SKIP_INTEGRATION=1`) | Scheduled/push tox did not set `SKIP_INTEGRATION` or ignore the same integration files as `mas-ci` | Same #145 (`dependencies.yml` + `tox.ini`) | In progress on #145 head `d41fd01fc` (run `34510514070`). Next `main` schedule/push should inherit the env. |
| `MycosoftLabs/mindex` | `platform-one-build` | failure `34505403818` (`--suppress-no-test-exit-code` unknown) then exit 1 after #13 | (1) flag needs `pytest-custom-exit-code`; (2) once pytest ran: OpenAPI included `/api/biobank/*`; SINE test still expected `{uuid}` literals | [#13](https://github.com/MycosoftLabs/mindex/pull/13) `87364ee07` (exit 5); [#14](https://github.com/MycosoftLabs/mindex/pull/14) `9d657a4f1` (prefix + uuid[] lists) | **Green** [`34510905929`](https://github.com/MycosoftLabs/mindex/actions/runs/34510905929) |
| `MycosoftLabs/mindex` | `Deploy MINDEX to VM 189` | success | n/a | none (deployed #14 API prefix change) | **Green** `34510905884` |
| `MycosoftLabs/website` | `Mycosoft CI/CD` / `CI` / `Website CI` | ITDX PR #301/#302 green; later main pending | n/a for the original red | ITDX already merged; dirty local website main not reset | Latest `main` CI/CD `34510781821` on `a077848b` pending (runner queue). Not the original failure. |
| `MycosoftLabs/website` | `Arraylake field bake` | failure (8+ scheduled; SSH `UNKNOWN:65535` / Access) | Bake OK; Cloudflare Tunnel SSH failed and failed the job. Same tunnel as blue/green. | [#303](https://github.com/MycosoftLabs/website/pull/303) merge `e58cea4d7` — NAS publish only if `ARRAYLAKE_PUBLISH_SSH=true` | **Green** [`34510927475`](https://github.com/MycosoftLabs/website/actions/runs/34510927475). SSH skipped. Publish **blocked** until tunnel/Access + variable. |
| `MycosoftLabs/website` | `CREP — weekly SD+TJ coverage bake` | failure `34357895934` (9 Sep) | `peter-evans/create-pull-request` dirty tree (`lib/crep/fly-to-panels.ts`) after harvest | none this pass (weekly; not red-now) | **Blocked** next weekly; harvest itself wrote GeoJSON | 
| platform-infra (`CODE/platform-infra`) | none | n/a | **No GitHub remote, no `.github/workflows`.** The “platform-infra” red check is MINDEX `platform-one-build`. | Documented | no GitHub workflow |

## Rules honored

- Site stays up. Did not stop `mycosoft-website` on 187. Did not start a second cutover.
- Dirty local MAS (`cursor/field-operator-live-observations-sep01`) and website (`fix/launchpad-ingest-bearer-alias`) were not reset. Fixes used clean worktrees from `origin/main`.
- No edits to `orchestrator.py`, `orchestrator_service.py`, guardian, `security/`, constitution, soul, or `identity.py`.
- No secrets committed. RJ remains CFO. No CUI.

## How to verify

```powershell
gh run list --repo MycosoftLabs/mycosoft-mas --workflow mas-ci --limit 3
gh run list --repo MycosoftLabs/mindex --workflow platform-one-build --limit 3
gh run list --repo MycosoftLabs/website --workflow "Arraylake field bake" --limit 3
```

## Follow-up (blocked, not a code skip)

1. **`mas-ci` on newest `main`:** watch run `34510948289` until green. Earlier #145/#146/#147 runs were cancelled by concurrency, not by a new collection error.
2. **Arraylake NAS publish:** Cloudflare Tunnel SSH from GitHub Actions fails (`UNKNOWN` port 65535). Fix `PRODUCTION_HOST` / Access service token, then set `ARRAYLAKE_PUBLISH_SSH=true`. Do not restart the live website container for this.
3. **CREP weekly SD+TJ bake:** next weekly needs a clean `create-pull-request` (add only `public/data/crep/sdtj-*`).
4. **platform-infra:** add a remote and workflows only if Morgan wants GitHub CI there. Not a MycosoftLabs repo today.
5. **Website bot PRs** (`bot/inat-nyc-dc-hourly`, `bot/eagle-cameras-nightly`) sit at `action_required` (environment approval). Not test failures.
