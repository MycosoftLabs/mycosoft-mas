# Master Document Index

## Architecture and Operations (Feb 9, 2026)
- `docs/MASTER_ARCHITECTURE_FEB09_2026.md` – **Master architecture document**: Full ecosystem Mermaid diagrams (Website, MAS, MINDEX, MycoBrain, NatureOS, Platform-Infra, Dev Machine, n8n), data flow sequences (REST, telemetry, voice, Earth2 GPU), network topology for 3 VMs (187/188/189) with full port map (25 ports), repository map (9 repos, 4 languages), 6-layer memory architecture (Ephemeral/Session/Working/Semantic/Episodic/System), security boundaries and access matrix, deployment pipeline (local dev -> GitHub -> Docker -> Cloudflare purge), agent architecture (14 categories, 100+ agents), rollback procedures.
- `docs/PRODUCTION_MIGRATION_RUNBOOK_FEB09_2026.md` – **Production migration runbook**: VM deployment plans (187/188/189), Docker container management, rollback procedures (Proxmox snapshots, image tagging, git reset), secrets rotation schedule (quarterly), data backups (PostgreSQL pg_dump, Redis RDB, Qdrant snapshots, NAS sync), health check commands, emergency recovery procedures.

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
