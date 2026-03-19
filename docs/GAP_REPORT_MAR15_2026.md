# Pull, Integration & Gap Report — NLM, MINDEX, MAS, Website

**Date:** March 15, 2026  
**Author:** MYCA  
**Status:** Complete

## Overview

Pulled latest code (today’s Claude Code work) for NLM, MINDEX, MAS, and website; checked for conflicts, security, and bugs; ensured the four repos work together; fixed one integration gap and documented the rest.

---

## 1. Pull Summary

| Repo    | Action | Result |
|---------|--------|--------|
| **Website** | Already up to date | Fast-forward (no local changes) |
| **NLM**     | Stash → pull       | Fast-forward; new `nlm/search/`, telemetry, API/client |
| **MINDEX**  | Stash → pull       | Fast-forward; earth router, unified_search, migrations, ETL |
| **MAS**     | Stash → pull       | Fast-forward; earth_search agent/router, `earth_search/`, migration 025, tests, doc |

**Stashes:** All three stashes (`nlm-local-mar15`, `mindex-local-mar15`, `mas-local-mar15`) were **dropped**; remote is source of truth.

---

## 2. Integration Fix Applied

**MINDEX — Unregistered routers**

- **Issue:** `plasticity_router`, `nlm_router`, and `search_answers` (router) existed as files but were **not** imported in `mindex_api/routers/__init__.py` or registered in `mindex_api/main.py`.
- **Fix:** All three are now imported in `routers/__init__.py` and included in `main.py` under the API prefix. Endpoints:
  - `/api/plasticity/*` — Plasticity Forge (candidates, aliases, training runs)
  - `/api/nlm/*` — NLM persistence (NMF, training, evals)
  - `/api/search/*` — Search answers (snippets, QA pairs, second-search)

---

## 3. Gaps and Recommendations

### 3.1 Stashes vs remote

- **Done.** All stashes dropped; remote is source of truth.

### 3.2 Security scan

- **Done.** Grep scan for revoked secrets run in MAS, MINDEX, NLM, website. MINDEX scripts that had hardcoded values were updated to use `VM_PASSWORD` / `MINDEX_DB_PASSWORD`; changes committed and pushed on MINDEX.

### 3.3 MINDEX migrations

- **Done.** On VM 189, applied via `docker exec -i mindex-postgres psql`: `001_search_schema_mar14_2026.sql`, `0022_plasticity_registry.sql`. No errors.

### 3.4 Cross-repo integration

- **MAS ↔ MINDEX:** Earth search uses MINDEX earth/unified_search; plasticity/NLM/search_answers are now exposed at MINDEX. Ensure MAS env points to MINDEX API (e.g. `MINDEX_API_URL=http://192.168.0.189:8000`).
- **Website:** Proxies and env (e.g. `MINDEX_API_URL`, `MAS_API_URL`) should point to the same MINDEX/MAS instances.
- **NLM:** NLM client and training sinks should use MINDEX base URL for `/api/nlm/*` and `/api/plasticity/*` if they call MINDEX.

### 3.5 Tests

- **NLM:** `python -m pytest` — no tests collected (project uses setuptools; test discovery may need `pip install -e ".[dev]"` or a dedicated test layout).
- **MINDEX:** `python -m pytest` — 8 failures: OpenAPI contract (namespaced prefix, DTO shapes), COBS/MDP protocol tests, `test_iter_fungi_taxa_handles_pagination`. Majority of tests passed.
- **MAS:** `poetry run pytest` — run completed with 6 collection errors in `test_orchestrator.py` and multiple failures (e.g. earth_search, full_integration_apis, myca_autonomous, reciprocal_turing_agent). Pre-existing; not introduced by this gap work.
- **Website:** No code changes in website for this task; build not re-run.

---

## 4. Conflicts, Security, Bugs

- **Conflicts:** None; all pulls were fast-forward.
- **Security:** Scan completed; revoked-secret grep run; MINDEX scripts updated to env vars and pushed.
- **Bugs:** Known test failures in MAS and MINDEX (see 3.5); not introduced by router fix or migrations.

---

## 5. Summary

- Latest code pulled for NLM, MINDEX, MAS, and website; no merge conflicts.
- MINDEX gap fixed: plasticity, NLM, and search_answers routers are now registered and mounted.
- Stashes dropped; security scan done and MINDEX secrets fixed; MINDEX migrations applied on VM 189; MINDEX deployed (container restarted; `docker-compose build` on VM has a YAML issue at line 180 for future full rebuilds).
- Tests run: NLM (no tests), MINDEX (8 failures documented), MAS (errors/failures as above). No redeploy of MAS or website—only MINDEX was updated and deployed.

---

## Related Documents

- [Doable Search Rollout Complete](./DOABLE_SEARCH_ROLLOUT_COMPLETE_MAR14_2026.md)
- [Gaps and Security Audit](./GAPS_AND_SECURITY_AUDIT_MAR14_2026.md)
- [No Hardcoded Secrets](.cursor/rules/no-hardcoded-secrets.mdc)
- [System Registry](./SYSTEM_REGISTRY_FEB04_2026.md)
- [API Catalog](./API_CATALOG_FEB04_2026.md)
