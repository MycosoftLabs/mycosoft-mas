# System Gaps and Remaining Work (Feb 10, 2026)

**Purpose:** Single reference for what is still needed across the entire Mycosoft system. Sourced from gap reports, sub-agent rules, and known backlogs. Kept in sync by the **gap-agent** and **gap_scan_cursor_background.py** full-workspace scan.

---

## How This Is Maintained

1. **Refresh reports:** From MAS repo run `python scripts/gap_scan_cursor_background.py`.
2. **Read:** `.cursor/gap_report_latest.json` (workspace-wide) and `.cursor/gap_report_index.json` (indexed/canonical files).
3. **Quality agents** (code-auditor, route-validator, plan-tracker, stub-implementer, regression-guard, test-engineer) use these reports as **gap-first intake** before manual scans.
4. **gap-agent** runs in the background of every chat and surfaces missing connections, TODOs, stubs, 501 routes, and bridge gaps.

---

## Summary Counts (from gap reports)

| Category | Count | Priority |
|----------|-------|----------|
| TODOs/FIXMEs in code | 80+ | Medium–High |
| Placeholder/stub implementations | 29–50+ | Medium–High |
| Indexed files with gaps | 13 | High |
| Index gaps (in indexed files) | 100 | High |
| Broken API routes (501) | 7–23 | High |
| Bridge/integration gaps (docs) | 3+ | High |
| Missing website pages | 15 | High |
| Incomplete plans/roadmaps | 17 | Track |
| Security flaw (base64 encryption) | 1 | Critical |
| Voice system completion | ~40% | High |
| WebSocket infrastructure | Not built | Medium |

---

## Critical / High Priority

- **Security:** Replace base64 with AES-GCM in `mycosoft_mas/security/security_integration.py` (and any similar usage).
- **501 routes:** Implement real logic for `/api/mindex/wifisense`, `/api/mindex/agents/anomalies`, `/api/docker/containers` (clone/backup), and any other routes returning 501.
- **Missing pages:** Add or redirect `/contact`, `/support`, `/careers`, `/myca`, `/auth/reset-password`, `/dashboard/devices`, and device routes referenced in nav/defense portal.
- **Stub implementations:** Financial agents (Mercury, QuickBooks, Pulley), Research agent task handlers, Task Manager (orchestrator client, monitoring), Memory vector search (mem0_adapter), real WiFiSense and anomalies backends.

---

## Index-Based Missing Work (canonical files)

These files are referenced in `docs/MASTER_DOCUMENT_INDEX.md` (and related indexes) and still contain TODO/FIXME/501/unchecked items:

- `.cursor/agents/device-firmware.md` — 14 unchecked checklist items (COM port, USB, boot mode, service 8003, BME688, baud).
- `docs/AGENT_REGISTRY_FULL_FEB09_2026.md` — Stub/catalog mentions (dynamic stubs, Cursor agents).
- `docs/SECURITY_BUGFIXES_FEB09_2026.md` — 20 unchecked items (rotate passwords, audit git, secret scanning, pre-commit, Vault, quarterly audits, agent security review, alerting, credential docs, threat model).
- `docs/STATUS_AND_NEXT_STEPS_FEB09_2026.md` — 7 unchecked (187 git/claude, 188 SSH key, 189 MINDEX-only, integration test).
- `docs/SYSTEM_EXECUTION_REPORT_FEB09_2026.md` — 8 unchecked (MAS gitignore/push, website container, 187↔188 connectivity, MAS deploy, Cloudflare, CREP status, MASTER_DOCUMENT_INDEX).
- `docs/FCI_IMPLEMENTATION_COMPLETE_FEB10_2026.md` — HPL program execution (stub).
- `docs/SECRET_MANAGEMENT_POLICY_FEB09_2026.md` — TODO for `.env.example` in MINDEX, NatureOS, Mycorrhizae, Platform-Infra.
- Plus: DATA_LOSS_AND_DRIVE_FULL_RECOVERY, GAP_AGENT_FEB10_2026, PHASE1_*, PHYSICSNEMO_*, WORK_TODOS_GAPS_AND_MISSING_AGENTS_RULES_FEB10_2026.

---

## Suggested Plans (from gap scan)

1. **Complete indexed work** — 13 indexed files have TODO/FIXME/501/pending; prioritize docs and code referenced in MASTER_DOCUMENT_INDEX.
2. **Address TODOs/FIXMEs** — Resolve or triage 80+ items across repos.
3. **Replace stubs with implementations** — Replace or document 29+ stub/placeholder usages.
4. **Implement 501 routes** — Implement API routes currently returning 501.
5. **Add missing bridges** — Implement integration layer or agent where docs indicate a bridge is missing.

---

## Agent and Rule Updates (Done Feb 10, 2026)

- **gap-agent:** Now includes "Continuous Full-System Monitoring" and routes findings to code-auditor, route-validator, stub-implementer, plan-tracker, regression-guard, test-engineer.
- **code-auditor, route-validator, plan-tracker, stub-implementer, regression-guard, test-engineer:** Each has a "Gap-First Intake (Required)" section: refresh and read gap reports before manual scans.
- **gap-agent-background.mdc:** Updated to describe full-workspace scan and that quality agents must use gap reports first.
- **gap_scan_cursor_background.py:** Scans all known repos (MAS, WEBSITE, MINDEX, MycoBrain, NatureOS, Mycorrhizae, NLM, SDK, platform-infra), writes `by_repo` counts, stubs, routes_501, bridge_gaps; merges with MAS gap API and index scan when available.

---

## References

- `scripts/gap_scan_cursor_background.py` — Full workspace gap scan; run periodically or at session start.
- `scripts/gap_scan_cursor_index.py` — Index-based scan only (MASTER_DOCUMENT_INDEX + related).
- `.cursor/gap_report_latest.json` — Latest workspace + index merged report.
- `.cursor/gap_report_index.json` — Indexed files with gaps.
- `docs/GAP_AGENT_FEB10_2026.md` — Gap agent behavior and API.
- `docs/WORK_TODOS_GAPS_AND_MISSING_AGENTS_RULES_FEB10_2026.md` — Work streams and alignment.
- `docs/VISION_VS_IMPLEMENTATION_GAP_ANALYSIS_FEB10_2026.md` — Vision vs implementation gaps.
