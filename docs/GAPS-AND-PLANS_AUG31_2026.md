# Gaps and Plans — August 31, 2026

Inventory of incomplete work in `mycosoft-mas`: open issues, draft PRs,
Dependabot backlog, and README/infra gaps. Each item has a status
(**fixed**, **planned**, or **needs-decision**) and a recommended next step.

---

## 1. Open Issues

### 1.1 #103 — Enable async consciousness tests in CI

| Field | Value |
|-------|-------|
| Status | **Fixed in this PR** |
| Author | nodefather (Mar 28 2026) |
| Root cause | `pytest.ini` lacked `asyncio_mode = auto`, so every `@pytest.mark.asyncio` test was silently skipped when pytest-asyncio defaulted to `strict` mode. |
| Fix | Added `asyncio_mode = auto` to both `pytest.ini` (root) and `tests/pytest.ini`. All 153 consciousness tests now execute and pass. |
| Residual risk | None — the existing CI pytest invocation (`poetry run pytest tests/ ...`) picks up the root `pytest.ini` automatically. |

### 1.2 #104 — Update world-state consumers for freshness-wrapped payloads

| Field | Value |
|-------|-------|
| Status | **Planned** (not safe to auto-fix) |
| Author | nodefather (Mar 28 2026) |
| Problem | `/api/myca/world` now wraps `predictions`, `ecosystem`, `nlm`, `earthlive`, `presence` inside `{ data, freshness }` objects. Downstream consumers expecting bare dicts will break. |

**Plan:**

1. **Audit consumers.** Grep the website repo, MAS internal callers, and any
   n8n workflows that hit `/api/myca/world`. Produce a list of call sites and
   whether they read `.data` or the bare dict.
2. **Add a compatibility shim** (optional): if the API detects
   `?compat=v1` or an `Accept-Version: v1` header, unwrap the freshness
   envelope and return bare dicts. This buys time for consumer migration.
3. **Update each consumer** to read `.data` and optionally use `.freshness`
   for staleness indicators.
4. **Update integration docs** (`docs/API_CATALOG_FEB04_2026.md`, OpenAPI
   schema) to document the new shape.
5. **Remove the compat shim** once all consumers are migrated.

**Owner:** Whoever touches the world-state API next; suggest tagging the
website-dev and backend-dev agents.

---

## 2. Draft Pull Requests

### 2.1 #116 — TurboQuant codec + Nemotron migration design

| Field | Value |
|-------|-------|
| Status | **Planned** — research-first, draft PR with design doc + reference impl |
| Branch | `claude/turboquant-research-integration-t4vtI` |
| What exists | `mycosoft_mas/memory/turboquant.py` (numpy-only codec, 8 passing tests), design doc at `docs/TURBOQUANT_NEMOTRON_INTEGRATION_JUN06_2026.md`. |

**Plan to merge:**

1. **Review the design doc** with the team — especially the Nemotron base-URL
   decision (`resolve_nemotron_base_url()` currently defaults to Ollama
   11434; production target is the GPU VM via NIM).
2. **Validate codec against real embeddings** — run TurboQuant on a sample of
   actual MINDEX/Qdrant vectors and measure recall vs. the synthetic tests.
3. **Stage follow-up PRs** per the phased rollout in the design doc:
   NemotronRetrieverEmbedder, TurboQuant sidecar in semantic memory, omni/ultra
   roles, KV-cache serving profile, Ollama decommission.
4. **Merge only the design doc + codec** once review is done; the codec is
   self-contained and low-risk.

### 2.2 #114 — CVE-2026-31431 (Copy Fail) mitigation bundle

| Field | Value |
|-------|-------|
| Status | **Planned** — security bundle, needs staging validation |
| Branch | `claude/patch-cve-2026-31431-VgbgI` |
| What exists | Host mitigation/detection scripts, Ansible playbook, Kyverno policy, Falco rules, runner pre-check, findings report. |

**Plan to merge:**

1. **Test on a staging MAS node** — run `bash scripts/security/cve-2026-31431-mitigate.sh`,
   reboot, verify the detect script exits 0.
2. **Ansible dry-run** — `ansible-playbook --check ops/ansible/cve-2026-31431.yml`.
3. **Kyverno dry-run** on staging cluster (if applicable).
4. **Falco rule test** — trigger a deliberate `socket(AF_ALG)` and confirm alert.
5. Merge after all four checks pass. The PR's own test plan documents these steps.

**Note:** This is infrastructure-only (no application code changes). The adjacent-issue
audit found 0 hits for AF_ALG/splice/privileged usage in MAS code.

### 2.3 #113 — Harden MYCA deploy boundary and local n8n

| Field | Value |
|-------|-------|
| Status | **Planned** — draft PR with identity security, n8n bootstrap |
| Branch | `codex/myca-live-deploy-boundary` |
| What exists | MYCA identity model, internal service-token guard, n8n bootstrap script, workflow drift checks, 8 passing tests. |

**Plan to merge:**

1. **Review identity boundary changes** — the PR touches chat, voice, memory,
   search, gateway, and router paths. This is invasive; review each changed
   file for regressions.
2. **Test the n8n bootstrap** — confirm `n8n_bootstrap_local.py` works with
   a fresh local n8n instance and that workflow drift detection is accurate.
3. **Verify lazy-loading** — the PR refactors router exports to lazy-load
   optional routers; confirm no imports break in the minimal (no-GPU) config.
4. **Credential follow-ups** — Slack auth, Signal, WhatsApp/Evolution remain
   deployment-policy decisions per the PR notes.
5. Merge after review and staging validation.

---

## 3. Open Dependabot PRs

18 Dependabot PRs are open. They fall into three risk tiers.

### 3.1 Safe to merge (minor/patch bumps, no breaking changes expected)

| PR | Bump | Notes |
|----|------|-------|
| #64 | python-dotenv 1.0.0 → 1.2.1 | Patch; changelog is bugfixes only |
| #58 | psycopg2-binary 2.9.9 → 2.9.11 | Patch |
| #57 | platformdirs 4.3.7 → 4.5.0 | Minor; dev-only dependency |
| #54 | pylint 3.3.6 → 3.3.9 | Patch; dev-only |
| #40 | astroid 3.3.9 → 3.3.11 | Patch; dev-only (pylint transitive) |

**Recommendation:** Merge these one at a time, let CI pass after each. They
are low-risk and keep the dependency tree current.

### 3.2 Merge with minor validation

| PR | Bump | Notes |
|----|------|-------|
| #52 | click 8.1.8 → 8.3.0 | Minor; but `pyproject.toml` pins `click >=8.1.0,<8.2` for Typer compat — **this PR will conflict with the pin**. Validate Typer works with click 8.3 before merging. |
| #41 | redis 5.0.1 → 5.3.1 | Minor; but `pyproject.toml` already has `redis ^7.1.0` which is *newer* — this Dependabot PR may be stale or targeting an old lockfile. Verify. |
| #24 | fastapi 0.104.1 → 0.109.2 | Minor; but `pyproject.toml` already has `fastapi ^0.124.0` — likely stale. Verify and close if lockfile is already past this. |
| #20 | uvicorn 0.24.0 → 0.27.1 | Same — `pyproject.toml` has `uvicorn ^0.38.0`. Likely stale. |
| #61 | pydantic 2.5.2 → 2.12.3 | `pyproject.toml` has `pydantic ^2.12.0` — may be stale. |

**Recommendation:** Check if these are already superseded by current
`pyproject.toml` constraints. Close stale ones; merge any that are still
relevant after CI validation.

### 3.3 Needs a plan (major version bumps)

| PR | Bump | Risk |
|----|------|------|
| #117 | nvidia/cuda 12.1-runtime → 13.3.0-runtime | **High** — CUDA major version; affects all GPU workloads, torch compatibility, driver requirements. |
| #112 | node 25-alpine → 26-alpine | **Medium** — Node major version; may break Next.js build or npm scripts. |
| #59 | python 3.11-slim → 3.14-slim | **High** — Python major version jump (3.11→3.14); the Dockerfile already uses 3.13; 3.14 has removal of deprecated stdlib modules. |

**Recommendation:** Do **not** merge these without:
1. A compatibility matrix (which torch/CUDA versions are supported, which
   Node version Next.js requires, which Python version the test matrix covers).
2. A staging test with the bumped base image.
3. A rollback plan.

### 3.4 GitHub Actions bumps

| PR | Bump | Notes |
|----|------|-------|
| #82 | github/codeql-action 3 → 4 | Major; review migration guide |
| #81 | docker/login-action 3 → 4 | Major; review migration guide |
| #63 | anchore/sbom-action 0.15.10 → 0.20.9 | Minor; likely safe |
| #50 | actions/setup-python 2 → 6 | Major jump; CI already uses `@v5` — stale? |
| #46 | actions/checkout 2 → 5 | Major jump; CI already uses `@v4` — stale? |

**Recommendation:** Close #50 and #46 if CI already uses the pinned versions.
Merge #63 after checking SBOM output format. Review migration guides for #82
and #81 before merging.

---

## 4. Other Open PRs

### 4.1 #79 — security: remove all hardcoded secrets from codebase

| Field | Value |
|-------|-------|
| Status | **Needs review and merge** |
| Branch | `security/rotate-secrets-mar14` |
| What exists | Removed hardcoded secrets from ~300+ files, added pre-commit hook, `.env.example` with 450+ vars. |

**Plan:** This is critical security work. Review the diff, confirm no
functional regressions (all secrets replaced with `os.environ.get()`), merge,
then do a `git filter-repo` purge of the old secrets from history and force-push.

---

## 5. README / Infrastructure Gaps (fixed or documented)

### 5.1 Compose command accuracy

| Field | Value |
|-------|-------|
| Status | **Fixed in this PR** |
| Problem | README warned that `mas-orchestrator` might not run uvicorn, and suggested a fix command identical to what was already in `docker-compose.yml`. |
| Fix | Updated README to state the command is already correct and point to `docker compose logs` for debugging. |

### 5.2 Dual `/dashboard` mount

| Field | Value |
|-------|-------|
| Status | **Fixed in this PR** (documentation clarified) |
| Problem | README warned about overlapping `/dashboard` mounts (ASGI app + API router). |
| Fix | Clarified that neither is currently mounted in `myca_main.py` — the warning was about a historical/potential issue, not a current bug. |

### 5.3 `wait-for-it` script missing

| Field | Value |
|-------|-------|
| Status | **Documented** |
| Problem | `Dockerfile` line 74 copies `docker/wait-for-it.sh` but the `docker/` directory does not exist in the repo. |
| Impact | The Compose command no longer uses `wait-for-it` (it was removed from the command), and the Dockerfile `COPY` will fail at build time if the file is missing. However, the `CMD` doesn't use it either — it goes straight to uvicorn. The `COPY` is dead code. |
| Recommendation | Either add `docker/wait-for-it.sh` to the repo or remove the `COPY` line from the Dockerfile. Low priority since the current build may work if Docker ignores the missing file during the runtime stage (the COPY is in the runtime stage, after the build stage). |

### 5.4 Empty/dead files

| Field | Value |
|-------|-------|
| Status | **Fixed in this PR** |
| Problem | Four files existed as empty stubs with no content: `PORT_CONFLICT_RESOLUTION.md` (0 bytes, linked from README), `PREPARE_FOR_TEST.ps1` (0 bytes), `TEST_EXECUTION_PLAN.md` (0 bytes), `docker-compose.essential.yml` (2 bytes). |
| Fix | Populated `PORT_CONFLICT_RESOLUTION.md` with real port-map and conflict-resolution content (README links to it). Deleted the other three — no code references them. |

---

## 6. DAO Agent — JSON→MINDEX Migration

| Field | Value |
|-------|-------|
| Status | **Planned** (do not rewrite the agent in this PR) |
| File | `mycosoft_mas/agents/myco_dao_agent.py` |
| Problem | `_execute_proposal_action` is a self-documented placeholder. All persistence (members, proposals, treasury, governance) writes to local JSON files under `data/myco_dao/`. MINDEX already has a `mycodao_zone` schema that should be the real backend. |

**Plan:**

1. **Audit the MINDEX `mycodao_zone` schema** — determine which tables/columns
   exist and what the DAO agent currently writes to JSON that has no MINDEX
   equivalent.
2. **Create a `MINDEXDAOClient`** (or extend `mindex_client.py`) that wraps
   the DAO-specific CRUD operations:
   - `upsert_member(member_data)` → MINDEX `mycodao_zone.members`
   - `upsert_proposal(proposal_data)` → MINDEX `mycodao_zone.proposals`
   - `update_treasury(amount)` → MINDEX `mycodao_zone.treasury`
   - `log_vote(vote_data)` → MINDEX `mycodao_zone.votes`
3. **Swap JSON persistence calls** in `myco_dao_agent.py` with MINDEX client
   calls. Keep JSON writes as a **local fallback** behind a feature flag
   (`DAO_PERSIST_MODE=mindex|json`, default `mindex`) for offline development.
4. **Implement `_execute_proposal_action`** properly — the funding branch
   already works but the parameter branch is a no-op; wire it to a real
   config update or agent-config patch via the MAS orchestrator API.
5. **Add tests** — at minimum, test that proposals round-trip through MINDEX
   and that the JSON fallback still works.

**Risk:** Low — the DAO agent is not on a critical path. The migration can
happen incrementally.

---

## 7. Embodiment Package

| Field | Value |
|-------|-------|
| Status | **Tracked elsewhere** — `mycosoft-embodiment` extracted to its own repo (PR [#2](https://github.com/MycosoftLabs/mycosoft-embodiment/pull/2)) |
| In this repo | `mycosoft-embodiment/` directory remains as a copy. This is intentional — the MAS repo keeps its copy for now. |
| Action | None in this PR. When the embodiment repo stabilizes, consider replacing this directory with a git submodule or a pyproject dependency. |

---

## 8. Larger Incomplete Systems (context only)

These are tracked elsewhere but listed here for completeness:

| System | Status | Tracking |
|--------|--------|----------|
| PersonaPlex / MYCA Voice | ~40% complete per README/docs | Voice docs, myca-voice agent |
| WebSocket infrastructure | Not built; needed by 5+ systems | docs/SYSTEM_REGISTRY |
| Scientific dashboard | UI exists, no real backend data | code-auditor findings |
| 80+ TODOs/FIXMEs in MAS code | Ongoing | code-auditor |
| 50+ placeholder/stub implementations | Ongoing | stub-implementer |
| 15 missing website pages | Website repo | route-validator |

---

## Summary of Actions in This PR

| Action | Files | Closes |
|--------|-------|--------|
| Enable `asyncio_mode = auto` in pytest config | `pytest.ini`, `tests/pytest.ini` | #103 |
| Fix misleading README Compose note | `README.md` | — |
| Clarify README dashboard mount note | `README.md` | — |
| Populate `PORT_CONFLICT_RESOLUTION.md` | `PORT_CONFLICT_RESOLUTION.md` | — |
| Delete empty dead files | `PREPARE_FOR_TEST.ps1`, `TEST_EXECUTION_PLAN.md`, `docker-compose.essential.yml` | — |
| Create this gaps/plans document | `docs/GAPS-AND-PLANS_AUG31_2026.md` | — |
