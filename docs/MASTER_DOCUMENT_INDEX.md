# Master Document Index

## Self-Healing MAS Infrastructure (Feb 9, 2026)
- `docs/SELF_HEALING_MAS_INFRASTRUCTURE_FEB09_2026.md` – **Complete self-healing system**: Orchestrator can tell agents to write code, agents can request code changes, SecurityCodeReviewer gates all modifications, VulnerabilityScanner detects CVEs/OWASP patterns, SelfHealingMonitor auto-triggers fixes. Includes CodeModificationService, /api/code/* endpoints, BaseAgent integration with request_code_change()/request_self_improvement()/report_bug_for_fix() methods.

## MycoBrain Device Setup (Feb 9, 2026)
- `docs/MYCOBRAIN_BETO_SETUP_GUIDE_FEB09_2026.md` – **Complete setup guide for Beto**: Arduino IDE setup, ESP32-S3 board support, firmware upload with boot mode procedure, MycoBrain service startup, Device Manager integration, and troubleshooting. Also references the new skill (`.cursor/skills/mycobrain-setup/`) and subagent (`.cursor/agents/device-firmware.md`).

## System Status, Purge, GitHub Path (Feb 9, 2026)
- `docs/SYSTEM_STATUS_AND_PURGE_FEB09_2026.md` – **Status and purge**: What’s done, what can be done, Cloudflare purge (credentials in .env.local or “agents cat”), GitHub-as-source-of-truth for MAS and website, and “always read latest docs” rule for agents.

## Phase 1 Agent Runtime (Feb 9, 2026)
- `docs/PHASE1_AGENT_RUNTIME_EXECUTION_REPORT_FEB09_2026.md` – Phase 1 execution report: core 42 runtime, runner loader/startup, optional iot_envelope, Batch 1 (orchestration + utility) real agents, v2 package resilient imports, VM compatibility.

## PhysicsNeMo Integration (Feb 9, 2026)
- `docs/PHYSICSNEMO_INTEGRATION_FEB09_2026.md` - PhysicsNeMo container/runtime integration across MAS + Earth2 + CREP, including new `/api/physics/*` proxy endpoints and GPU service lifecycle scripts.

## Claude Code Local Autonomous System (Feb 9, 2026)
- `docs/CLAUDE_CODE_SETUP_GUIDE_FEB09_2026.md` – **Quick setup guide**: 5-minute setup for Claude Code on local dev machine with autonomous background service, API bridge, and parallel execution with VMs.
- `docs/CLAUDE_CODE_LOCAL_AUTONOMOUS_FEB09_2026.md` – **Full architecture**: Local autonomous coding system with API bridge (port 8350), background service, task queue, VM integration, parallel execution, safety rules, and monitoring.

## Implementation and Testing (Feb 9, 2026)
- `docs/IMPLEMENTATION_AND_TESTING_GUIDE_FEB09_2026.md` – **Implementation and testing runbook**: Per-workstream implementation steps, test commands (curl, npm test, Playwright), and verification checklist for prioritization deliverables (architecture, security, visualization, memory, integrations, CI/CD).
- `docs/FULL_PLATFORM_AUTOMATION_EXECUTION_REPORT_FEB09_2026.md` – **Automation execution report**: End-to-end preflight, validation matrix across all repos, fixes/retests, VM redeploy results (MAS/Website/MINDEX), cache-purge status, health verification, and residual blockers.

## Architecture and Operations (Feb 9, 2026)
- `docs/MASTER_ARCHITECTURE_FEB09_2026.md` – **Master architecture document**: Full ecosystem Mermaid diagrams (Website, MAS, MINDEX, MycoBrain, NatureOS, Platform-Infra, Dev Machine, n8n), data flow sequences (REST, telemetry, voice, Earth2 GPU), network topology for 3 VMs (187/188/189) with full port map (25 ports), repository map (9 repos, 4 languages), 6-layer memory architecture (Ephemeral/Session/Working/Semantic/Episodic/System), security boundaries and access matrix, deployment pipeline (local dev -> GitHub -> Docker -> Cloudflare purge), agent architecture (14 categories, 100+ agents), rollback procedures.
- `docs/PRODUCTION_MIGRATION_RUNBOOK_FEB09_2026.md` – **Production migration runbook**: VM deployment plans (187/188/189), Docker container management, rollback procedures (Proxmox snapshots, image tagging, git reset), secrets rotation schedule (quarterly), data backups (PostgreSQL pg_dump, Redis RDB, Qdrant snapshots, NAS sync), health check commands, emergency recovery procedures.
- `docs/IOT_ENVELOPE_LOCAL_FIRST_INTEGRATION_FEB09_2026.md` – Local-first unified IoT envelope ingest: MAS `/api/iot/*` forwarding, Mycorrhizae verification/dedupe/ACK, MINDEX `/api/telemetry/*` canonical storage (verified + replay + health), NatureOS envelope consumer, and NLM verified ingest.
- `docs/IOT_API_KEY_BOOTSTRAP_FEB09_2026.md` – Bootstrap and wiring for `MYCORRHIZAE_API_KEY` and `MINDEX_API_KEY` (no secrets in git), including first-admin-key bootstrap, migrations, and `.env.example` templates.
- `docs/MYCORRHIZAE_VM188_CONTAINER_DEPLOYMENT_FEB09_2026.md` – Run Mycorrhizae as an always-on Docker container on MAS VM 188 (port 8002) using Postgres+Redis on VM 189; includes compose file and bootstrap steps.

## Security Hardening (Feb 9, 2026)
- `docs/SECRET_MANAGEMENT_POLICY_FEB09_2026.md` – **Secret management policy**: No secrets in code, .env.example pattern for all repos, quarterly rotation schedule, CI/CD secrets via GitHub Actions, audit procedures, git-filter-repo for history remediation, current findings (30+ hardcoded secrets in scripts/, 12 credential-containing defaults in library code), remediation priority and pre-commit hook setup.

## Status, MYCA coding, and VM layout (Feb 9, 2026)
- `docs/AGENT_REGISTRY_FULL_FEB09_2026.md` – **Full agent registry**: why counts differ (223+ vs 42+), canonical numbers, full list of agents, core vs Cursor vs runtime; recommendations so one registry and “all running” are possible.
- `docs/STATUS_AND_NEXT_STEPS_FEB09_2026.md` – Memory/LFS status, today's docs, MYCA coding plan status, checklist to test Claude Code on VMs 187 and 188.
- `docs/MYCA_CODING_SYSTEM_FEB09_2026.md` – MYCA autonomous coding system: CodingAgent, coding API, CLAUDE.md, VM setup.
- `docs/MINDEX_VM_189_AVX_BUN_ASSESSMENT_FEB09_2026.md` – Why VM 189 shows “bun has crashed” / AVX segfault (Claude Code, not MINDEX). 189 is data-only; do not run Claude Code on 189. MINDEX stack verified healthy.
- `docs/SECURITY_BUGFIXES_FEB09_2026.md` - **CRITICAL**: Fixed 7 bugs including 2 critical security issues (hardcoded credentials in git, shell injection vulnerability) and 5 stability issues. All fixed before MYCA coding system deployment.

## Notion Documentation Sync System (Feb 8, 2026)
- `docs/NOTION_DOCS_SYNC_SYSTEM_FEB08_2026.md` – Comprehensive multi-repo docs-to-Notion sync: 1,271 docs across 8 repos, auto-categorization, versioning, file watcher for real-time auto-sync.

## Data loss and drive full (Feb 6, 2026)
- `docs/PERSONAPLEX_LFS_INCIDENT_AND_PREVENTION_FEB06_2026.md` – **CRITICAL**: PersonaPlex Git LFS caused 1.74 TB garbage, filled 8TB drive, destroyed all Cursor chats. Full root cause, cascade analysis, permanent fixes, and prevention rules for all future development.
- `docs/DATA_LOSS_AND_DRIVE_FULL_RECOVERY_FEB06_2026.md` – Initial recovery doc written during the incident.
