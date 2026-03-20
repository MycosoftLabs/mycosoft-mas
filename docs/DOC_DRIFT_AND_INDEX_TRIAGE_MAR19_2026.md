# Doc Drift and Index Triage — Mar 19, 2026

**Date:** March 19, 2026  
**Status:** Triaged inbox  
**Related:** [PLATFORM_GAP_AUDIT_AND_BACKLOG_MAR19_2026.md](PLATFORM_GAP_AUDIT_AND_BACKLOG_MAR19_2026.md)

---

## Purpose

Single triage doc for unchecked lines from execution reports and `cursor_index_scan`. Each row: **Status** | **Owner repo** | **Proof link**.

**Columns:** Item | Source | Status | Owner | Proof

---

## Unchecked items from SYSTEM_EXECUTION_REPORT_FEB09_2026

| Item | Status | Owner | Proof |
|------|--------|-------|-------|
| MAS `.gitignore` cleaned, repo <100 MB | open | MAS | — | — |
| 187→188 connectivity verified from 187 | open | infra | — | SSH from 187, `curl 188:8001/health` |
| Cloudflare purged after website deploy | open | WEBSITE | Verify on next deploy |
| Sandbox CREP Earth2 status | open | WEBSITE | Browser check sandbox.mycosoft.com/crep |
| MASTER_DOCUMENT_INDEX reflects latest | open | docs | — | Updated Mar 19 |

---

## Unchecked items from WORK_SUMMARY_FEB15_18_2026

| Item | Status | Owner | Proof |
|------|--------|-------|-------|
| Deploy MAS to VM 188 | open | deploy | Rebuild container |
| Deploy MINDEX to VM 189 | open | deploy | Rebuild API container |
| Deploy Website to VM 187 | open | deploy | Verify |
| Purge Cloudflare cache | open | WEBSITE | After deploy |
| Verify all health endpoints | open | infra | — | curl 187:3000, 188:8001, 189:8000 |
| Test voice system end-to-end | open | MAS/WEBSITE | Playwright or manual |
| Test CREP dashboard | open | WEBSITE | Browser |
| Test search functionality | open | WEBSITE | — |

---

## cursor_index_scan (index_gaps)

Source: `.cursor/gap_report_latest.json` → `index_gaps.referenced_files_with_gaps`. ~180 items across 34 files. Full list below.

**Kinds:** `todo_fixme`, `stub`, `unchecked`, `501`

| File | Gap count | Kind | Status | Owner | Proof |
|------|-----------|------|--------|-------|-------|
| .cursor/CURSOR_DOCS_INDEX.md | 2 | todo_fixme | open | MAS | — |
| .cursor/agents/search-engineer.md | 1 | todo_fixme | open | MINDEX | — |
| .cursor/docs_manifest.json | 9 | todo_fixme | noise | — | — |
| docs/AUTONOMOUS_CURSOR_SYSTEM_FEB12_2026.md | 2 | todo_fixme | open | MAS | — |
| docs/AUTONOMOUS_WORKFLOW_SYSTEM_FEB18_2026.md | 1 | stub | open | MAS | — |
| docs/AUTO_APPLY_ANALYZER_FIXES_FEB09_2026.md | 6 | todo_fixme | open | MAS | — |
| docs/CONSCIOUSNESS_PIPELINE_OPTIMIZATION_FEB11_2026.md | 5 | unchecked | open | MAS | — |
| docs/CREDENTIAL_MANAGEMENT_BEST_PRACTICES_FEB09_2026.md | 7 | todo_fixme | open | MAS | — |
| docs/CURSOR_MCP_AND_EXTENSIONS_FEB12_2026.md | 1 | stub | open | MAS | — |
| docs/CURSOR_SUITE_AUDIT_FEB12_2026.md | 6 | todo_fixme | open | MAS | — |
| docs/CURSOR_TEAM_AUDIT_FEB12_2026.md | 3 | todo_fixme | open | MAS | — |
| docs/DATA_LOSS_AND_DRIVE_FULL_RECOVERY_FEB06_2026.md | 3 | unchecked | open | infra | — |
| docs/GROUNDED_COGNITION_FULL_SPRINT_COMPLETE_FEB17_2026.md | 7 | unchecked | open | MAS | — |
| docs/GROUNDED_COGNITION_V0_FEB17_2026.md | 6 | todo_fixme | open | MAS | — |
| docs/MASTER_DOCUMENT_INDEX.md | 4 | todo_fixme | open | docs | — |
| docs/MYCA_ECOSYSTEM_UNIFICATION_FEB17_2026.md | 1 | unchecked | open | MAS | — |
| docs/MYCA_GROUNDED_COGNITION_INTEGRATION_COMPLETE_FEB17_2026.md | 1 | stub | open | MAS | — |
| docs/MYCA_GROUNDED_COGNITION_PHASES_2_3_4_SPRINT_PLAN_FEB17_2026.md | 18 | unchecked | open | MAS | — |
| docs/MYCA_WORLDVIEW_INTEGRATION_AUDIT_FEB17_2026.md | 10 | unchecked | open | MAS | — |
| docs/NATUREOS_FULL_PLATFORM_COMPLETE_FEB19_2026.md | 3 | stub | in progress | NatureOS | [EXECUTION_WAVES P3 Evidence](EXECUTION_WAVES_AND_ACCEPTANCE_MAR19_2026.md#wave-p3--data-plane-and-looks-complete-but-empty-uis) |
| docs/NATUREOS_TOOLS_INTEGRATION_TASK_COMPLETE_FEB21_2026.md | 1 | stub | in progress | NatureOS | P3 audit; SignalR spine in INTEGRATION_COMPLETION_MATRIX |
| docs/NATUREOS_UPGRADE_PREP_FEB19_2026.md | 17 | unchecked | open | NatureOS | — | — |
| docs/PETRI_DEPLOYMENT_HANDOFF_FEB20_2026.md | 3 | unchecked | open | WEBSITE | — |
| docs/PETRI_DISH_SIM_DEPLOYMENT_STATUS_FEB20_2026.md | 3 | unchecked | open | WEBSITE | — |
| docs/PETRI_INTEGRATION_DEMO_WALKTHROUGH_FEB20_2026.md | 10 | unchecked | open | WEBSITE | — |
| docs/SEARCH_SUBAGENT_MASTER_FEB10_2026.md | 2 | todo_fixme | open | MINDEX | — |
| docs/SECURITY_BUGFIXES_FEB09_2026.md | 8 | unchecked | open | MAS | — |
| docs/SESSION_GROUNDED_COGNITION_AND_DEPLOY_FEB17_2026.md | 1 | unchecked | open | MAS | — |
| docs/STATUS_AND_NEXT_STEPS_FEB09_2026.md | 6 | unchecked | open | MAS | — |
| docs/STUB_IMPLEMENTATIONS_FEB12_2026.md | 16 | todo_fixme | open | MAS | — |
| docs/SUBAGENT_ROLES_AND_COMMANDS_FEB12_2026.md | 1 | stub | open | MAS | — |
| docs/SUPERAPP_ARCHITECTURE_AND_UNIFICATION_FEB19_2026.md | 3 | stub | in progress | WEBSITE | [EXECUTION_WAVES P3 Evidence](EXECUTION_WAVES_AND_ACCEPTANCE_MAR19_2026.md#wave-p3--data-plane-and-looks-complete-but-empty-uis); UNI-01..UNI-05+ tracked in plan |
| docs/SYSTEM_EXECUTION_REPORT_FEB09_2026.md | 5 | unchecked | open | infra | — | — |
| docs/WORK_SUMMARY_FEB15_18_2026.md | 8 | unchecked | open | infra | — | — |

**Refresh:** Run `python scripts/gap_scan_cursor_background.py` or `GET /agents/gap/scan`; merge new `referenced_files_with_gaps` here.

---

## Doc drift fixes (reconcile)

| Item | Status | Action / proof |
|------|--------|----------------|
| MYCA2 plan: "registry not live hot-path" | **done** | Updated `.cursor/plans/myca2_psilo_stack_50e28949.plan.md` line 45: registry **is** the live hot-path for MYCA2 roles; `backend_selection.py` lines 99–113 call `resolve_alias_to_backend_spec(role)` first. |
| Workspace rules: "7 API routes returning 501" | **done** | Mar 19: Rules updated. Website BFF has no routes that directly return 501; some MAS/MINDEX proxy routes may. `mycosoft-full-codebase-map.mdc` and `mycosoft-full-context-and-registries.mdc` now qualify the claim; see DOC_DRIFT + route-validator for current list. |
| docs_manifest.json todo/stub hits | **noise** | Many are doc titles containing "TODO"/"stub"; filter or ignore in gap scan. |
| force_restart_container.py hardcoded Proxmox token | **done** | Mar 19: Refactored to load from env or `.credentials.local`; no literal secrets. |
