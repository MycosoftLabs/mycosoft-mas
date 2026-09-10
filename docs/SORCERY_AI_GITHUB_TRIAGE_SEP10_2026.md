# Sourcery AI GitHub triage — Sep 10, 2026

**Date:** Thursday 10 Sep 2026  
**Status:** Complete (triage + targeted fixes on clean worktrees)  
**Bot:** GitHub App `sourcery-ai` / login `sourcery-ai[bot]` (Morgan: “Sorcery AI bought”)  
**Related:** existing `mas-ci`, website `CI` / `Website CI`, MINDEX `platform-one-build`

## What was searched

| Query | Result |
|---|---|
| `reviewed-by:sourcery-ai[bot] org:MycosoftLabs` | 374 PRs (org-wide, all time in search window) |
| `commenter:sourcery-ai[bot] org:MycosoftLabs` | 405 issues/PRs |
| Inline review comments since 2026-07-12 on mas / website / mindex / Fusarium / NatureOS / mycalab | **63** |
| Issue comments (same window) | **68** — all `review_guide` summaries, not findings |
| Review objects sampled on recent/open PRs | **31** (several Sep 10 reviews are **RATE_LIMIT**: 250,000 diff characters / 7 days) |
| `.github/workflows` for a Sourcery job | None. Marketplace action `sourcery-ai/action@v1` exists but needs secret **`SOURCERY_TOKEN`**. `gh secret list` on mas / website / mindex: **not present**. Not invented. |
| `platform-infra` | Local tree, **no git remotes**, not MycosoftLabs |

MINDEX remote discovered as `MycosoftLabs/mindex`.

Extract cache (not committed): `.cursor/sourcery_triage_sep10.json`.

## Bot quality

Sourcery **does flag real issues** (range checks, 422 vs 500, exception leaks, silent pytest pass, typed path params, workflow artifact paths). It also **misfires**:

- Treats the intentional **0.85 stub-confidence reject** as a bug (accepted policy; Fusarium/NLM must never ship placeholder `p`).
- Claims `SCANNED_SCOPE` is a string; it is a **1-tuple**.
- Claims Next.js 15 `params` is not a Promise (it is).
- Floods Reviewer's Guides and social share footers.
- Hits **rate limit** on large Sep 10 diffs, so recent PRs often get no inline review.

## Counts

| Bucket | Count |
|---|---|
| Inline findings triaged | 63 |
| **Valid and fixed this batch** | 7 |
| Valid, skipped (protected path, billing/OSINT design, or needs own PR) | 16 |
| False positive | 2 |
| Accepted policy (0.85 reject) | 2 |
| Stale / nit / already merged | 36 |
| Issue-comment Reviewer's Guides | 68 (not findings) |

Valid = `valid-fixed` + `valid-skipped` + `accepted-policy` treated as real-or-intentional.  
**Actionable valid defects fixed now:** 7.

## Fixes (clean worktrees only)

Primary checkouts were dirty. **Never reset.** Fixes landed on:

| Repo | Worktree | Branch | Base HEAD when branched |
|---|---|---|---|
| `MycosoftLabs/mycosoft-mas` | `CODE/_ci_wt/mas-sourcery-sep10` | `fix/sourcery-ai-triage-sep10` | `a1dd0efd3` (merge PR #148) |
| `MycosoftLabs/mindex` | `CODE/_ci_wt/mindex-sourcery-sep10` | `fix/sourcery-ai-triage-sep10` | `9d657a4` (merge PR #14) |
| `MycosoftLabs/website` | `CODE/_ci_wt/website-sourcery-sep10` | `fix/sourcery-arraylake-artifact-sep10` | `a077848b` (merge PR #304) |

Did **not** edit dirty website main or the ITDX website worktree. Did **not** blue-green 187. Did **not** touch orchestrator / soul / `mycosoft_mas/security/` / constitution / identity.

### MAS

- `is_usable_nlm_confidence`: restore `0.0 < value <= 1.0`; reject `confidence_usable is False`; **keep** rejecting exactly `0.85`.
- `POST /api/nlm/observations` cutoff: `ValueError` → HTTP **422** `"Invalid cutoff timestamp"`.
- Incidents `"reported"` timeline: add `"at"` UTC ISO-8601.
- NLM environmental handler: 500 detail is `"Environmental process failed"` (no `str(e)`).
- Packet reference test: `pytest.skip` when the archived Windows packet is absent.

### MINDEX

- `GET /nlm/nmf/{embedding_id}`: `embedding_id: int` (FastAPI 422 on junk); drop `CAST`.
- Persist/get 500s: generic `persist_failed` / `get_failed`; re-raise `HTTPException`.

### Website

- Arraylake bake artifact upload path: `${{ env.ARRAYLAKE_FIELD_OUT }}/**/manifest.json`.

## What now runs on every merge

**No new Sourcery Actions job.** The org App already reviews PRs. Adding `sourcery-ai/action@v1` would require secret **`SOURCERY_TOKEN`** (document the name only; do not invent a key).

| Repo | Workflow | Triggers | What it runs |
|---|---|---|---|
| MAS | `mas-ci` (`.github/workflows/ci.yml`) | `pull_request` + `push` to `main` + dispatch | pytest (skipped heavy integrations), flake8 syntax, isort `|| true`, bandit `|| true`, docs presence. Docker publish/deploy only on push main when secrets exist. |
| Website | `CI` + `Website CI` | PR + push main (`CI`); PR (`Website CI`) | `npm run lint` + `npm run build`. Heavy `Mycosoft CI/CD` stays push-to-main deploy — **not duplicated**. |
| MINDEX | `platform-one-build` | **`pull_request` + `push` to `main`** (PR trigger added this batch) | pytest (exit 5 = no tests = success), optional Iron Bank image when secrets exist. |

CI YAML comments now state: do not add the marketplace Action without `SOURCERY_TOKEN`.

## Inline comment table

| # | PR | File:line | Claim | Disposition | Note |
|---|---|---|---|---|---|
| 1 | `MycosoftLabs/mycosoft-mas#119` | `docs/API_CATALOG_FEB04_2026.md:48` | **nitpick (typo):** Consider adding 'is' for smoother grammar in the phrase 'when prod ordering enabled'. | stale | Grammar nit on catalog row. Not a runtime defect. |
| 2 | `MycosoftLabs/mycosoft-mas#120` | `scripts/setup_mas_vm_auto.py:180` | **issue (bug_risk):** New logic never creates a .env file on a fresh MAS VM, which can leave the system unusable. | stale | Bootstrap .env design. Ops scripts already assume credentials files exist. |
| 3 | `MycosoftLabs/mycosoft-mas#120` | `scripts/_ops_migration031_patchv2_jul21_2026.py:94` | **suggestion:** Unused psql_cmd and duplicated execution path make the migration logic harder to follow. | stale | Dead psql_cmd in one-shot Jul 21 migration. Not merge-blocking. |
| 4 | `MycosoftLabs/mycosoft-mas#120` | `tests/test_evidence_emitter.py:34` | **suggestion (testing):** Add coverage for `primary_evidence_uri` when PreVeil is absent and when no artifacts are present. | stale | Extra test coverage suggestion. Not a production bug. |
| 5 | `MycosoftLabs/mycosoft-mas#121` | `mycosoft_mas/core/routers/security_evidence_api.py:77` | **🚨 issue (security):** Avoid returning raw exception strings in HTTP error responses to prevent leaking internal details. | valid-skipped | Generic 500 leak is real; left for a dedicated security-evidence PR. Same class of fix applied on nlm_api environmental handler. |
| 6 | `MycosoftLabs/mycosoft-mas#121` | `mycosoft_mas/compliance/evidence_register.py:107` | **issue (bug_risk):** Artifact-path extraction may incorrectly treat URLs as internal paths. | stale | URL-vs-path backtick edge case. Low risk after merge. |
| 7 | `MycosoftLabs/mycosoft-mas#122` | `mycosoft_mas/security/posture_integrity_monitor.py:66` | **issue (bug_risk):** Controls iterable is consumed twice, which will break when a non-reusable iterator/generator is passed in. | valid-skipped | Iterator consume-twice is real if a generator is passed. File is under mycosoft_mas/security/ — not edited. |
| 8 | `MycosoftLabs/mycosoft-mas#122` | `mycosoft_mas/core/myca_main.py:1963` | **question (bug_risk):** Integrity monitor is started even when MAS_SKIP_BACKGROUND_STARTUP is set to skip background tasks. | stale | Sourcery marked addressed in 73613a096d. |
| 9 | `MycosoftLabs/mycosoft-mas#123` | `mycosoft_mas/core/routers/incidents_api.py:89` | **suggestion (bug_risk):** Incident 'reported' timeline event lacks a timestamp, which may reduce auditability. | valid-fixed | Reported timeline now includes at=UTC ISO-8601. |
| 10 | `MycosoftLabs/mycosoft-mas#124` | `mycosoft_mas/security/posture_integrity_monitor.py:66` | **issue (bug_risk):** Avoid consuming a generic Iterable twice when building the snapshot. | valid-skipped | Same as #122. Protected security/ path. |
| 11 | `MycosoftLabs/mycosoft-mas#125` | `mycosoft_mas/integrations/mindex_client.py:117` | **issue:** Switching to `dsn` drops the previous fallback behavior for incomplete/invalid URLs. | stale | DSN requirement is intentional. Incomplete URLs should fail closed. |
| 12 | `MycosoftLabs/mycosoft-mas#125` | `tests/integrations/test_mindex_client.py:18` | **suggestion (testing):** Assert that `_get_db_pool` does not recreate the pool on subsequent calls (caching behavior). | stale | Optional cache assertion. Not a defect. |
| 13 | `MycosoftLabs/mycosoft-mas#126` | `mycosoft_mas/security/posture_integrity_monitor.py:82` | **issue:** Error message is misleading because it also covers 'compliant' controls. | valid-skipped | Error-message wording. Protected security/ path. |
| 14 | `MycosoftLabs/mycosoft-mas#127` | `mycosoft_mas/soc/gws_boundary_scan.py:119` | **issue (bug_risk):** SCANNED_SCOPE is a string, so `list(SCANNED_SCOPE)` produces a list of characters instead of a list of scope descriptions. | false-positive | SCANNED_SCOPE is a one-element tuple; list() is correct. |
| 15 | `MycosoftLabs/mycosoft-mas#127` | `mycosoft_mas/soc/repository.py:1004` | **issue (bug_risk):** Run and hit inserts are not wrapped in a transaction, so a partial write is possible if hit insertion fails. | valid-skipped | Partial write if hit insert fails. Needs a transaction redesign; not in this batch. |
| 16 | `MycosoftLabs/mycosoft-mas#128` | `scripts/cmmc/_wave1_promote_after_sign_jul22.py:124` | **security (python.lang.security.audit.dangerous-subprocess-use-audit):** Detected subprocess function 'run' without a static string. If this data can be contro | stale | Static-analysis subprocess warning on an internal CMMC script. No user input. |
| 17 | `MycosoftLabs/mycosoft-mas#134` | `docs/ITDX_FUSARIUM_LIVE_SHIP_SEP09_2026.md:4` | **issue (broader_impact):** The new status lines declare the website LIVE on blue, but the linked VM backends note still contains the old "do not cut over" sect | stale | Ops-doc contradiction from Sep 09 ship notes. Not code. |
| 18 | `MycosoftLabs/mycosoft-mas#135` | `mycosoft_mas/core/routers/fusarium_api.py:177` | **issue (bug_risk):** The species, risk-zones, and threats endpoints changed their successful response shape from a bare list to an object containing the list u | stale | Envelope vs list and pathogenic_only semantics were an intentional API change after merge. |
| 19 | `MycosoftLabs/mycosoft-mas#135` | `mycosoft_mas/core/routers/fusarium_api.py:190` | **issue (bug_risk):** `pathogenic_only=True` only adds `lineage_contains=Fusarium`, which restricts results to the Fusarium lineage but does not require pathoge | stale | pathogenic_only=lineage_contains Fusarium is the current filter contract. |
| 20 | `MycosoftLabs/mycosoft-mas#136` | `mycosoft_mas/nlm/inference/service.py:23` | **issue (bug_risk):** is_usable_nlm_confidence rejects every confidence value exactly equal to 0.85, including a legitimate model prediction of 0.85, because it | accepted-policy | Rejecting exactly 0.85 is Fusarium/NLM policy so stub p never ships as ecology. |
| 21 | `MycosoftLabs/mycosoft-mas#137` | `mycosoft_mas/core/routers/itdx_public_sources.py:1025` | **issue (broader_impact):** `fetch_nws_forecast` is removed from the first-wave jobs and `nws` is now hard-coded as deferred, so NWS is never queried. When Open | stale | NWS deferred is an intentional first-wave timeout design. |
| 22 | `MycosoftLabs/mycosoft-mas#137` | `mycosoft_mas/nlm/inference/service.py:57` | **issue (bug_risk):** Every confidence numerically equal to `0.85` is rejected, even when it comes from a ready real model with no stub metadata or placeholder  | accepted-policy | Same 0.85 hard reject as #136. |
| 23 | `MycosoftLabs/mycosoft-mas#138` | `mycosoft_mas/core/routers/itdx_public_sources.py:1109` | **issue (bug_risk):** When `gather_public_osint` is cancelled while `_await_named` is awaiting `asyncio.wait`, the function exits without cancelling or awaiting | valid-skipped | Cancel-without-await is theoretically real. High-risk OSINT path; not patched here. |
| 24 | `MycosoftLabs/mycosoft-mas#139` | `docs/ITDX_FUSARIUM_LIVE_SHIP_SEP09_2026.md:206` | **issue (broader_impact):** The new live-proof table reports chemistry as SUPPLIED, contradicting the document's earlier live-channel table and prior prove reco | stale | Chemistry SUPPLIED vs UNQUALIFIED doc drift. Not code. |
| 25 | `MycosoftLabs/mycosoft-mas#140` | `mycosoft_mas/core/routers/itdx_api.py:511` | **issue (bug_risk):** `asyncio.wait_for` cancels the wrapper around `asyncio.to_thread(_devices_inprocess)`, but it cannot stop the underlying worker thread. Wh | valid-skipped | to_thread cannot cancel the worker. Known asyncio limit; needs a dedicated timeout design. |
| 26 | `MycosoftLabs/mycosoft-mas#141` | `mycosoft_mas/core/routers/itdx_api.py:45` | **issue (bug_risk):** The broad `except ImportError` treats every import failure from `mycosoft_mas.nlm.inference.service` as the old-helper compatibility case. | valid-skipped | Broad ImportError swallow. Compatibility fallback is intentional; skip. |
| 27 | `MycosoftLabs/mycosoft-mas#141` | `tests/test_itdx_task8_api.py:240` | **issue (testing):** The new test imports the helpers from the router under the normal current service module, so the fallback branch is never selected. It pass | stale | Test does not exercise the fallback import branch. Coverage gap, not a prod bug. |
| 28 | `MycosoftLabs/mycosoft-mas#142` | `mycosoft_mas/nlm/inference/service.py:55` | **issue (bug_risk):** is_usable_nlm_confidence returns True for confidence values greater than 1 because the upper-bound check was removed, so callers can emit  | valid-fixed | Restored 0.0 < value <= 1.0 and reject confidence_usable is False. Still reject exactly 0.85 (policy). |
| 29 | `MycosoftLabs/mycosoft-mas#142` | `mycosoft_mas/nlm/inference/service.py:60` | **issue (broader_impact):** is_usable_nlm_confidence ignores metadata confidence_usable=false and accepts the confidence whenever it is positive and the text is | valid-fixed | Now rejects metadata confidence_usable is False. |
| 30 | `MycosoftLabs/mycosoft-mas#142` | `mycosoft_mas/core/routers/nlm_api.py:894` | **issue (bug_risk):** accept_observation calls datetime.fromisoformat without handling parsing errors, so a malformed cutoff query causes an uncaught ValueError | valid-fixed | Malformed cutoff now HTTP 422 Invalid cutoff timestamp. |
| 31 | `MycosoftLabs/mycosoft-mas#142` | `mycosoft_mas/nlm/formspace/reference_runtime.py:173` | **issue (bug_risk):** replay starts each default replay from self.state and then overwrites self.state, so repeated prediction, decision-path, or Weka requests  | valid-skipped | Stateful replay is used for sequential FormSpace scans. Changing default would break packet replay. |
| 32 | `MycosoftLabs/mycosoft-mas#142` | `mycosoft_mas/nlm/formspace/persist.py:114` | **issue (bug_risk):** remember_layers writes memory layers sequentially without rollback or per-layer exception handling, so a failure on a later layer leaves e | valid-skipped | Per-layer memory writes are not a single DB transaction. Needs memory-coordinator work. |
| 33 | `MycosoftLabs/mycosoft-mas#142` | `scripts/_persist_nlm_env_mas188_sep10.py:54` | **issue (bug_risk):** The deployment script prints FAIL_CLOSED_NO_ROOT_BLOBS when root usage is at least 80 percent but continues writing the environment file a | valid-skipped | Fail-closed print-then-continue is real. One-shot 188 script; not merge CI. |
| 34 | `MycosoftLabs/mycosoft-mas#142` | `tests/test_nlm_reference_runtime_sep10.py:56` | **issue (testing):** test_reference_runtime_from_packet returns without making any assertion when the hard-coded Windows packet path is absent, so CI and normal | valid-fixed | Missing Windows packet path now pytest.skip instead of silent pass. |
| 35 | `MycosoftLabs/website#245` | `docs/cmmc_l2/verification/soc_ops-updates.sql:10` | **🚨 suggestion (security):** Avoid committing host-specific absolute paths in the generated SQL comments. | stale | Host path in SQL comments. Merged; do not edit dirty website main. |
| 36 | `MycosoftLabs/website#247` | `lib/reports/llm.ts:154` | **question (bug_risk):** generateNarrative can now throw for CUI/secrets, which is a behavioral change from the previous "never throws" contract. | stale | CUI throw is intentional fail-closed. Merged. |
| 37 | `MycosoftLabs/website#247` | `lib/security/cui/cui-guard.ts:83` | **issue (bug_risk):** walk() does not guard against circular references, which can cause unbounded recursion on cyclic payloads. | valid-skipped | walk() cycle guard would be nice. Merged Jul 15 path; not in this batch. |
| 38 | `MycosoftLabs/website#247` | `AI_AGENT_CUI_RULES_OF_BEHAVIOR_JUL15_2026.md:42` | **issue:** Clarify this "MUST NOT" item so it reads as a prohibition rather than an instruction. | stale | Wording nit. Canonical RoB lives in CODE/docs. |
| 39 | `MycosoftLabs/website#252` | `components/security/HitlTabletopConsole.tsx:436` | **issue (bug_risk):** Guard against multiple rapid submissions to avoid duplicate writes to the backend. | stale | Double-submit guard. Merged Jul work. |
| 40 | `MycosoftLabs/website#253` | `_rebuild_sandbox.py:101` | **suggestion:** Clarify interaction between --local-build and --image to avoid surprising behavior. | stale | Deploy-script nits. Do not start a second 187 cutover. |
| 41 | `MycosoftLabs/website#253` | `_rebuild_sandbox.py:238` | **suggestion:** Make preflight failures more targeted to distinguish missing Docker vs. resource contention. | stale | Preflight timeout conflation. Deploy script; no 187 work. |
| 42 | `MycosoftLabs/website#253` | `_rebuild_sandbox.py:257` | **issue (bug_risk):** Avoid potential interactivity or failure from using sudo in diagnostics. | stale | sudo dmesg interactivity. Deploy script; no 187 work. |
| 43 | `MycosoftLabs/website#253` | `docs/SANDBOX_BUILD_TIMEOUT_ROOT_CAUSE_FIX_JUL22_2026.md:11` | **issue (typo):** Clarify the phrasing around "no no-progress detection" to avoid a potentially confusing double "no". | stale | Docs typo. |
| 44 | `MycosoftLabs/website#255` | `lib/security/supply-chain/amazon-reconciliation.ts:67` | **🚨 question (security):** Consider whether embedding live spreadsheet IDs and order IDs in the client bundle is acceptable from a privacy/compliance standpoint | stale | Spreadsheet IDs in client bundle is a compliance question, not a CI defect. |
| 45 | `MycosoftLabs/website#255` | `lib/security/supply-chain/amazon-reconciliation.ts:117` | **suggestion (bug_risk):** Derive device/non-device counts from classification instead of `pmRef` to avoid coupling to BOM linkage. | stale | pmRef vs classification count. Merged. |
| 46 | `MycosoftLabs/website#257` | `app/api/security/network-diagnostics/route.ts:20` | **suggestion (performance):** Hoist the hostname validation regex to module scope to avoid recreating it on each request. | stale | Regex hoist micro-optimization. |
| 47 | `MycosoftLabs/website#263` | `app/api/fusarium/launchpad/billing/session/[id]/route.ts:20` | **suggestion:** The `context.params` type as a Promise is unusual and adds unnecessary complexity. | false-positive | Next.js 15 App Router params are a Promise. await is correct. |
| 48 | `MycosoftLabs/website#266` | `docs/launchpad/CURSOR_TO_CLAUDE_NAV_FIX_LIVE_AUG13_2026.md:23` | **suggestion (typo):** Consider adding a verb in the parenthetical for clearer grammar. | stale | Docs grammar. |
| 49 | `MycosoftLabs/website#266` | `docs/launchpad/CURSOR_TO_CLAUDE_NAV_FIX_LIVE_AUG13_2026.md:64` | **suggestion (typo):** The second sentence is a fragment; you may want to add a verb for completeness. | stale | Sentence fragment. Docs only. |
| 50 | `MycosoftLabs/website#267` | `lib/launchpad/billing/provision.ts:26` | **issue:** User lookup via `listUsers` is limited to the first 200 results, which can miss matches in larger deployments. | stale | 200-user page limit. Merged Aug Launchpad path. |
| 51 | `MycosoftLabs/website#267` | `app/api/fusarium/launchpad/onboarding/accept-terms/route.ts:42` | **suggestion:** IP hashing for terms acceptance relies solely on `x-forwarded-for` and doesn’t normalize multiple IPs. | stale | x-forwarded-for normalize. Merged. |
| 52 | `MycosoftLabs/website#268` | `app/api/fusarium/launchpad/billing/activate/route.ts:117` | **issue (bug_risk):** Handle failures from signInWithOtp instead of always returning success for existing accounts | stale | OTP error handling. Merged Aug path. |
| 53 | `MycosoftLabs/website#268` | `app/api/fusarium/launchpad/onboarding/accept-terms/route.ts:48` | **issue (bug_risk):** Avoid race between pre-check and insert when combined with the new unique index | stale | Unique-index race. Merged. |
| 54 | `MycosoftLabs/website#286` | `components/launchpad/TenantGate.tsx:236` | **issue (bug_risk):** When the tenant API returns a 409, TenantGate discards the response's `memberships` and renders only a message saying to choose a workspac | stale | 409 memberships UX. Merged. |
| 55 | `MycosoftLabs/website#286` | `scripts/launchpad/audit-launchpad-mobile.mjs:127` | **issue (testing):** The audit skips every anchor whose computed display starts with `inline`, including standalone or icon links that are not inside a sentence | stale | Inline tap-target exemption. Audit script only. |
| 56 | `MycosoftLabs/website#287` | `app/api/fusarium/launchpad/signatures/route.ts:164` | **issue (bug_risk):** The hosted envelope credit is marked `redeemed` before `createAndSendEnvelope` runs, so a DocuSign API failure consumes the customer's pre | valid-skipped | Credit redeemed before DocuSign send is a real billing race. Needs a dedicated Launchpad billing PR. |
| 57 | `MycosoftLabs/website#287` | `app/api/fusarium/launchpad/radar/opportunities/route.ts:41` | **issue:** The Radar UI hardcodes SBIR.gov and Grants.gov as `configured: true`/`connected` and the empty states say both collectors are not built, even though  | stale | Radar configured:true copy vs collector status. Merged. |
| 58 | `MycosoftLabs/website#290` | `scripts/arraylake/validate_bake_output.py:65` | **issue (bug_risk):** Wind-grid validation checks only that `u` and `v` are lists of the expected length; it never checks that their elements are finite numbers | valid-skipped | Wind-grid / PNG completeness checks are real bake-gate gaps. Separate Arraylake validation PR. |
| 59 | `MycosoftLabs/website#290` | `scripts/arraylake/validate_bake_output.py:52` | **issue (broader_impact):** PNG validation accepts any file containing a valid 24-byte signature/IHDR header and positive dimensions, without checking that the  | valid-skipped | PNG header-only validation. Separate bake-gate PR. |
| 60 | `MycosoftLabs/website#291` | `lib/fusarium-operator-login.test.mjs:43` | **issue (testing):** The test claims authentication runs before telemetry fetching, but it compares the position of `requireFusariumOwner` with the first occurr | stale | String-position auth test is weak. Merged. |
| 61 | `MycosoftLabs/website#296` | `app/api/fusarium/internal/health/route.ts:18` | **🚨 issue (security):** The loopback restriction trusts caller-supplied `x-forwarded-for` and `host` headers instead of the actual peer address, so a request re | valid-skipped | Header-spoof loopback is a real concern if that route is public. Needs network-bind review, not this batch. |
| 62 | `MycosoftLabs/website#303` | `.github/workflows/arraylake-field-bake.yml:64` | **issue (broader_impact):** When the repository variable `ARRAYLAKE_FIELD_OUT` is set to a non-default directory, the bake writes manifests there but the later  | valid-fixed | Artifact path now uses ${{ env.ARRAYLAKE_FIELD_OUT }}/**/manifest.json. |
| 63 | `MycosoftLabs/mindex#12` | `mindex_api/routers/nlm_router.py:69` | **issue (bug_risk):** A non-numeric `embedding_id` reaches `CAST(:embedding_id AS bigint)`, causing a database conversion error that is caught and returned as H | valid-fixed | embedding_id is int; CAST dropped; 500 details no longer leak exc. |

## Constraints honored

- RJ Ricasata is **CFO** (not COO).
- No secrets committed. `SOURCERY_TOKEN` named only.
- No CUI in this commercial surface.
- Agent `d0d48a45` owns blue-green 187 — this work did not touch Sandbox containers.

## How to verify

```powershell
# MAS worktree
python -m pytest tests/test_nlm_reference_runtime_sep10.py -q
# After PRs merge: Actions tabs on mas-ci, website CI, platform-one-build
```
