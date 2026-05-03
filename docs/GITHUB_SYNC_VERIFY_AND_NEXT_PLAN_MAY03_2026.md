# GitHub sync, verification, credential hygiene, and next plan (May 3, 2026)

**Date:** May 3, 2026  
**Status:** Operational summary for merge-to-main readiness (no key rotation per directive).

## Scope

- Confirm **live secrets are not committed** via `.gitignore` (`.credentials.local`, `.env` patterns).
- **Redact** one deployment doc line that contained a literal VM password placeholder pattern (use env-only wording).
- Record **verification** runs executed before push (MAS pytest subset, website lint, LAN probes).
- List **remaining credential-debt** (historical literals in older docs/scripts — tracked separately from today’s deliverables).
- Outline **next implementation / test / verify** steps after `main` is green.

## Credential hygiene (pre-push)

| Item | Result |
|------|--------|
| `.credentials.local` | Listed in MAS (and website) `.gitignore`; must never be staged. |
| `DEPLOY_ALL_THREE_VMS_FEB19_2026.md` | Updated to reference `<from .credentials.local only>` — no literal passwords in that instruction line. |
| Legacy literals (`Mushroom1!`, old API keys, etc.) | Some **revoked/example** strings remain in **historical** docs and scripts per existing `ROTATION_RUNBOOK` / policy docs; **full scrub** is backlog work — see Next plan. |

**Policy:** Do **not** paste secrets into chat, commits, or new docs; use `$env:VM_PASSWORD` / `os.environ.get("VM_PASSWORD")` only.

## Verification (May 3, 2026)

| Check | Command / URL | Outcome |
|-------|----------------|---------|
| Prometheus (MAS VM) | `http://192.168.0.188:9090/-/healthy` | HTTP 200 (when LAN reachable) |
| MAS orchestrator | `http://192.168.0.188:8001/health` | HTTP 200 (when LAN reachable) |
| MAS unit tests | `poetry run pytest tests/ -q --ignore=tests/test_cli.py` | **1310 passed**, 22 skipped, 1 warning (~302s) |
| Website ESLint | `npm run lint` (website repo) | **Exit 0** (warnings only: anonymous default exports in various `lib/*` files) |
| Gap scan artifact | `python scripts/gap_scan_cursor_background.py` | Writes `.cursor/gap_report_latest.json` when run |

### Known test gap

- `tests/test_cli.py` imports **`typer`**; collection fails if `typer` is not installed in the Poetry env. Add as dev dependency or install in CI so the full suite includes CLI tests.

## Deliverables tied to today’s thread (reference)

- Prometheus remediate/diagnose scripts on MAS repo (`scripts/remediate_prometheus_mas188.py`, `scripts/diagnose_prometheus_mas188.py`).
- MCP SSH server credential fallback improvements (`mycosoft_mas/mcp/ssh_server.py`).
- Platform audit / Prometheus runbook updates (`docs/MYCOSOFT_PLATFORM_AUDIT_INVENTORY_AND_GAPS_MAY02_2026.md`, `docs/PROMETHEUS_MAS_VM188_RUNBOOK_MAY03_2026.md`).
- MINDEX `.gitignore`: ignore `pytest_out*.txt` dumps.

## Next plan (implement → test → verify)

1. **MAS:** Add `typer` to dev dependencies (or document optional extra); restore default pytest collection including `test_cli.py`.
2. **Credential scrub sprint:** Replace remaining historical literals in scripts with env reads only; redact docs per `no-hardcoded-secrets.mdc`; run `security-audit` / pre-commit secret scan before releases.
3. **Website:** Schedule CI job for `npm run lint` + `npm run build` on PRs to `main`; treat ESLint warnings as backlog unless blocking.
4. **MINDEX:** Run pytest with project venv/poetry; confirm migrations applied on VM **189** per deploy docs after merge.
5. **Deploy matrix:** After merges, follow `docs/NATUREOS_DEPLOY_PUSH_MATRIX_MAY02_2026.md` (187 / 188 / 189 / Legions as applicable); purge Cloudflare when website image changes.

## How to verify after GitHub merge

- **MAS:** `curl -sS http://192.168.0.188:8001/health` and Prometheus health URL above.
- **Website:** Compare `localhost:3010` vs sandbox after container rebuild + Cloudflare purge (see deployment checklist rules).

## Post-push log (May 3, 2026)

| Repository | Remote / branch | Notes |
|------------|-----------------|--------|
| `mycosoft-mas` | `origin` `main` | Pushed `f13ae7bd5` (Prometheus + MCP + docs + May03 completion set). |
| `website` | `origin` `main` | Rebased on remote; pushed `a748aeaf` (May03 NatureOS BFF/UI). |
| `mindex` | `origin` `main` | Pushed `3b0ddfc` (all-life ETL, migrations, supabase pack). |
| `mycobrain` | `origin` `main` | Pushed `5211757` then **security follow-up** `ac4f806` — removed `MQTT/**/config/passwd`, ~19MB jetson backup tarball, and nested `workspace` gitlink from the tree. **History note:** those blobs may still exist in earlier commits — schedule `git filter-repo` if GitHub history must be scrubbed (distinct from key rotation). |
| `NatureOS` | `origin` `main` | Pushed `73b10f8`. |
| `Mycorrhizae` | `origin` `main` | Remote repo name `Mycorrhizae`; pushed `02cabfb`. |
| `NLM` | `origin` `main` | Rebased; pushed `83d74de`. |
| `sdk` | `origin` `main` | Pushed `4404709`. |
| `MYCODAO` | `nodefather` + `mycosoftlabs` `main` | No `origin` remote configured locally; pushed `88eba0b` (restored `.gitignore`, ignore nested `MYCO-App`). |

## Incident — nested repos / artifacts (corrective actions)

1. **MYCODAO:** Avoid `git add app/natureapp/` when `MYCO-App` contains its own `.git`; path is now gitignored. Prefer a declared submodule when the app should ship with the monorepo.
2. **mycobrain:** MQTT `passwd` and jetson backup tarball must never land in VCS; patterns added to `.gitignore`. Regenerate Mosquitto passwords on the deployment host only.

---

**Related:** `docs/PROMETHEUS_MAS_VM188_RUNBOOK_MAY03_2026.md`, `docs/MYCOSOFT_PLATFORM_AUDIT_INVENTORY_AND_GAPS_MAY02_2026.md`, `.cursor/rules/no-hardcoded-secrets.mdc`.
