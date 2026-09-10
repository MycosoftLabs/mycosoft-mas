# GitHub CI Triage — SEP10 2026

**Date:** 10 September 2026  
**Status:** Fixes pushed; bake/publish rules documented  
**Owner:** devops-engineer (gate hub = GitHub)  
**Related:** `docs/MASTER_DOCUMENT_INDEX.md`, `.cursor/CURSOR_DOCS_INDEX.md`

Morgan asked for a full red-check inventory across MAS, MINDEX, platform-infra, and the website shipping branch. Live `mycosoft-website` on 187 was not stopped. No second blue-green cutover.

## Inventory (now)

| Repo | Workflow | Was | Root cause | Fix | Now |
|------|----------|-----|------------|-----|-----|
| `MycosoftLabs/mycosoft-mas` | `mas-ci` | failure (test-build, test 3.11) | PR #142/#143 imported `formspace.contracts` / `forecast_ledger` / `observation_pipeline` on main but those three modules were never in the GitHub tree | Ship the three modules (`fix/formspace-contracts-ci-sep10`) | Watch `mas-ci` on the merge SHA |
| `MycosoftLabs/mycosoft-mas` | `Dependencies` | failure (tox on 3.13); 3.11/3.12 cancelled | Scheduled tox ran live VM integration (`No VMs reachable; run with SKIP_INTEGRATION=1`) | Job + tox `SKIP_INTEGRATION=1`; ignore the same integration files as `mas-ci` | Watch next `Dependencies` run |
| `MycosoftLabs/mindex` | `platform-one-build` | failure (`Run unit tests`) | Workflow called `pytest --suppress-no-test-exit-code` without `pytest-custom-exit-code` | Treat pytest exit 5 (no tests collected) as success | Watch `platform-one-build` on the merge SHA |
| `MycosoftLabs/mindex` | `Deploy MINDEX to VM 189` | success | n/a | none | green |
| `MycosoftLabs/website` | `Mycosoft CI/CD`, `CI`, `Website CI` on `main` / ITDX PR #301 | success | n/a | none | green (ITDX `cursor/itdx-codex-v13-connect-20260909` merged) |
| `MycosoftLabs/website` | `Arraylake field bake` | failure (8+ scheduled runs) | Bake succeeded; `setup-ssh` timed out (`UNKNOWN:65535` / Cloudflare Access). Same tunnel path as blue/green. | NAS publish now opt-in via `ARRAYLAKE_PUBLISH_SSH=true`. Bake + artifact remain the gate. | Bake should go green; publish **blocked** until tunnel/Access is fixed |
| platform-infra (local `CODE/platform-infra`) | none | n/a | **No GitHub remote, no `.github/workflows`.** Morgan’s “platform-infra” red check is MINDEX `platform-one-build`. Folder lives in the CODE monorepo without an origin. | Documented; no GitHub CI to repair | no GitHub workflow |

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

1. **Arraylake NAS publish:** Cloudflare Tunnel SSH from GitHub Actions fails (`Connection to UNKNOWN port 65535`). Fix `PRODUCTION_HOST` / Access service token (repo or `production` environment), then set Actions variable `ARRAYLAKE_PUBLISH_SSH=true`. Do not restart the live website container for this.
2. **platform-infra:** If it needs GitHub CI, add a remote and workflows later. It is not a MycosoftLabs repo today.
3. **Website bot PRs** (`bot/inat-nyc-dc-hourly`, `bot/eagle-cameras-nightly`) sit at `action_required` (environment approval). Not test failures.
