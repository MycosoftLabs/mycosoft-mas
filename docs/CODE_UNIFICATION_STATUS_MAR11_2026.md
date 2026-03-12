# Code Unification Status — March 11, 2026

**Date**: March 11, 2026  
**Status**: Partial Complete  
**Related**: PR merge and multi-agent work consolidation

## Overview

Unified code across Mycosoft repos from multiple agents (Claude Code, Cursor agents, local work). Pushed all local commits and merged what could be merged. Several PRs remain blocked by conflicts.

---

## Completed

### MAS (mycosoft-mas)

| Action | Result |
|--------|--------|
| Local commit pushed | `docs: CREP species icons clickable fix + MASTER_DOCUMENT_INDEX + cursor rules updates` |
| **PR 78** (Unified Latents) | Merged into main — consolidates PR 72 (Claude Code UL framework) |
| PR 72 | Closed as superseded by PR 78 |
| PR 65 | Already merged (dependabot node 25-alpine) |

### Website

| Action | Result |
|--------|--------|
| Local commits pushed | CREP dashboard, deck-entity-layer, fungal-marker, aisstream-ships |
| **feature/mycobrain-website-integration** | Merged into main and pushed |
| **fix/dashboard-myca-proxies** | Merged into main and pushed |

### MINDEX

| Action | Result |
|--------|--------|
| Local commits pushed | Investigation router, migrations 0020/0021, GitHub labels workflow |

---

## Blocked (18 MAS PRs)

All fail with "Pull Request is not mergeable" or "merge commit cannot be cleanly created" due to conflicts with main.

### Feature PRs

| PR | Title | Branch |
|----|-------|--------|
| 45 | Event ingestion service | codex/enhance-integration-across-natureos-and-mas |
| 39 | INITIALIZED status, BaseAgent | codex/review-mas-code-for-bugs-and-upgrades |
| 36 | Monitoring tests for mean stats | codex/update-monitoring-tests-for-stats |

### Dependabot PRs

| PR | Title |
|----|-------|
| 64 | python-dotenv 1.0.0 → 1.2.1 |
| 63 | anchore/sbom-action 0.15.10 → 0.20.9 |
| 61 | pydantic 2.5.2 → 2.12.3 |
| 59 | python 3.11-slim → 3.14-slim |
| 58 | psycopg2-binary 2.9.9 → 2.9.11 |
| 57 | platformdirs 4.3.7 → 4.5.0 |
| 54 | pylint 3.3.6 → 3.3.9 |
| 52 | click 8.1.8 → 8.3.0 |
| 50 | actions/setup-python 2 → 6 |
| 46 | actions/checkout 2 → 5 |
| 41 | redis 5.0.1 → 5.3.1 |
| 40 | astroid 3.3.9 → 3.3.11 |
| 24 | fastapi 0.104.1 → 0.109.2 |
| 20 | uvicorn 0.24.0 → 0.27.1 |

### Root Causes

1. **CRLF vs LF on Windows** — Branches have CRLF; merges abort with "local changes would be overwritten".
2. **Dependabot branches** — Based on old main; pyproject.toml, Dockerfile, and Actions have moved on.
3. **Codex branches** — Larger code changes; conflict surface is high.

---

## Recommended Next Steps

1. **Line endings** — Add `.gitattributes` with `* text=auto eol=lf` and normalize the repo.
2. **Dependabot** — Close conflicted Dependabot PRs; let Dependabot open new ones from current main.
3. **Feature PRs (45, 39, 36)** — Use consolidation flow: branch from main, cherry-pick or apply changes, resolve conflicts, open new PR, merge.

---

## Repo Sync Status (as of Mar 11, 2026)

| Repo | Local main | Remote main |
|------|------------|-------------|
| MAS | Synced | Synced |
| Website | Synced | Synced |
| MINDEX | Synced | Synced |
| MycoBrain | Clean | — |
| NLM | Clean | — |
| SDK | Clean | — |

---

## Related Documents

- [AGENT_CENSUS_MAR02_2026.md](./AGENT_CENSUS_MAR02_2026.md)
- [DEV_TO_SANDBOX_PIPELINE_FEB06_2026.md](./DEV_TO_SANDBOX_PIPELINE_FEB06_2026.md)
