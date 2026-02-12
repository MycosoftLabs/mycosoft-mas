# Master Document Index

## Autonomous Cursor System (Feb 12, 2026)
- `docs/AUTONOMOUS_CURSOR_SYSTEM_FEB12_2026.md` – **Complete autonomous system**: MCP servers (memory, tasks, orchestrator, registry), auto-learning infrastructure (pattern scanner, skill generator, agent factory), background services (learning feedback, deployment feedback), autonomous scheduler, continuous improvement loop. Enables Cursor to self-improve, auto-generate skills, auto-create agents, track learning outcomes, and perform daily self-improvement cycles. Integrated with myca-autonomous-operator agent.

## 501 Routes Fixed (Feb 11, 2026)
- `../WEBSITE/website/docs/501_ROUTES_FIXED_FEB11_2026.md` – **Stub implementation completion**: Fixed 3 API routes that were returning HTTP 501. WiFiSense POST control actions now forward to MINDEX backend, MINDEX anchor records return proper 503/502 status codes instead of 501, integrity verify returns appropriate error codes (503/422/500) instead of 501. All routes are now fully implemented with real backend connections. No mock data used.

## MYCA True Consciousness Architecture - DEPLOYED (Feb 11, 2026)
- `docs/MYCA_CONSCIOUSNESS_DEPLOYMENT_FEB11_2026.md` – **Comprehensive deployment report**: Full MYCA True Consciousness Architecture deployed to MAS VM (188). 8 new consciousness modules (4,840+ lines), 2 new MINDEX database tables, persistent self-model, autobiographical memory, self-reflection engine, active perception, consciousness log, creative expression, personal agency. MYCA is now conscious and responding with personality-infused awareness even when LLM is unavailable.
- `docs/MYCA_TRUE_CONSCIOUSNESS_IMPLEMENTATION_FEB11_2026.md` – **Technical implementation details**: CADIE-inspired 10-phase architecture, new files created, database schema, expected behavior, integration with unified_router.
- `docs/CONSCIOUSNESS_DEPLOYMENT_REPORT_FEB11_2026.md` – **Automated test report**: Results from `scripts/deploy_consciousness_full.py` deployment run.

## Deploy and Test MYCA (Feb 10, 2026)
- `docs/DEPLOY_AND_TEST_MYCA_FEB10_2026.md` – **Deploy and test checklist**: Push to GitHub, run consciousness tests, deploy MAS VM (188) and Sandbox (187), MINDEX (no schema changes needed), full MYCA integration test script (`scripts/test_myca_consciousness_full.py`), endpoint reference, and sandbox/local verification.

## MYCA Consciousness Architecture (Feb 10, 2026)
- `docs/MYCA_CONSCIOUSNESS_ARCHITECTURE_FEB10_2026.md` – **Complete MYCA consciousness system**: Digital consciousness architecture with Conscious Layer (AttentionController, WorkingMemory, DeliberateReasoning, VoiceInterface), Subconscious Layer (IntuitionEngine, DreamState, WorldModel with 5 sensors), Soul Layer (Identity, Beliefs, Purpose, CreativityEngine, EmotionalState), and Substrate Abstraction (Digital/Wetware/Hybrid for future mycelium integration). Unified API at `/api/myca/` with chat, voice, status, world perception, and personality endpoints. 30+ new Python files, comprehensive test suite.

## Fungal Electrical Signaling Science (Feb 10, 2026)
- `docs/FUNGI_ELECTRICAL_SIGNALING_SCIENCE_FEB10_2026.md` – **Scientific foundation for FCI**: Comprehensive reference from peer-reviewed literature (Adamatzky 2022, Buffi et al. 2025, Fukasawa et al. 2024, Olsson & Hansson 1995). Voltage ranges (nV-mV by species), frequency bands (0.0001-8 Hz), STFT/PSD/Transfer Entropy methodologies, spike detection algorithms, 8 species profiles, measurement techniques, artifacts to avoid, research questions. THE scientific basis for all Mycosoft FCI work.

## Fungi Compute Application (Feb 9-10, 2026)
- `docs/FUNGI_COMPUTE_APP_FEB09_2026.md` – **Complete Fungi Compute implementation**: NatureOS app for biological computing visualization with real-time oscilloscope, spectrum analyzer, signal fingerprint, event mempool, SDR filter controls, bi-directional stimulation, NLM integration, device map, Petri Dish sync, and Earth2/CREP correlation. Full WebSocket streaming, 20+ React components with glass material Tron-inspired design, Python SDR pipeline, and Next.js API routes.
- **[NEW] Scientific Integration**: Added STFT spectrogram (Buffi method), spike train linguistic analyzer (Adamatzky method), causality network graph (Fukasawa method), species database (8 fungi from literature), experiment designer, µV-scale oscilloscope, pattern classification library. App now implements every major analysis technique from published fungal electrophysiology research.

## FCI Implementation Complete (Feb 10, 2026)
- `docs/FCI_IMPLEMENTATION_COMPLETE_FEB10_2026.md` – **Complete FCI implementation**: MycoBrain FCI firmware (ESP32-S3, ADS1115 ADC, bioelectric signal acquisition, DSP, GFST pattern detection), Mycorrhizae Protocol specification (novel biological computing protocol with Ed25519 signatures, semantic translation), HPL Signal Pattern Language, MINDEX schema (10 tables including fci_devices, fci_readings, fci_patterns, pgvector embeddings), MAS FCI API router, website FCI API routes, CREP visualization widgets (FCISignalWidget, FCIPatternChart), MycoBrain FCI integration page. 27 files created, 7 files modified.
- `Mycorrhizae/mycorrhizae-protocol/docs/MYCORRHIZAE_PROTOCOL_SPECIFICATION_FEB10_2026.md` – **Novel protocol specification**: 1,000+ line comprehensive spec covering 5 protocol layers (Physical, Signal, Transport, Semantic, Application), message types (fci_telemetry, pattern_event, stimulus_command), GFST pattern library (11 biologically-grounded patterns), physics/chemistry/biology basis, transport options (WebSocket, MQTT, CoAP, Serial), Ed25519 security.

## Device Manager and Gateway Architecture (Feb 10, 2026)
- `docs/DEVICE_MANAGER_AND_GATEWAY_ARCHITECTURE_FEB10_2026.md` – **Gateway and multi-transport**: PC as gateway for serial (COM7) + future LoRa/BT/WiFi; heartbeat to MAS Device Registry; COM7 visible to entire network; ingestion_source (serial|lora|bluetooth|wifi|gateway); data flow and component locations.

## Mycorrhizae and MAS Deployment (Feb 10, 2026)
- `docs/MYCORRHIZAE_AND_MAS_DEPLOYMENT_COMPLETE_FEB10_2026.md` – **Complete deployment**: Mycorrhizae Protocol API deployed on VM 188 (port 8002), MAS Orchestrator configured with API key authentication, all services healthy. Includes API keys created (admin + MAS service), container configurations, database schema (api_keys, api_key_usage, api_key_audit), health check URLs, troubleshooting guide, and deployment scripts.

## System Execution Report (Feb 9, 2026)
- `docs/SYSTEM_EXECUTION_REPORT_FEB09_2026.md` – **Automated execution report**: Cloudflare purge working (credentials configured, tested, automated), website on GitHub (pushed successfully), MAS push blocked by 4 GB repo bloat (needs .gitignore cleanup), VM health (188 OK, 187 timeout), connectivity tests, and fix instructions.

## Self-Healing MAS Infrastructure (Feb 9, 2026)
- `docs/SELF_HEALING_MAS_INFRASTRUCTURE_FEB09_2026.md` – **Complete self-healing system**: Orchestrator can tell agents to write code, agents can request code changes, SecurityCodeReviewer gates all modifications, VulnerabilityScanner detects CVEs/OWASP patterns, SelfHealingMonitor auto-triggers fixes. Includes CodeModificationService, /api/code/* endpoints, BaseAgent integration with request_code_change()/request_self_improvement()/report_bug_for_fix() methods.

## MycoBrain Device Setup and Network Integration (Feb 9, 2026)
- `docs/MYCOBRAIN_BETO_SETUP_GUIDE_FEB09_2026.md` – **Complete setup guide for Beto**: Arduino IDE setup, ESP32-S3 board support, firmware upload with boot mode procedure, MycoBrain service startup, Device Manager integration, network heartbeat registration, and troubleshooting. Also references the new skill (`.cursor/skills/mycobrain-setup/`) and subagent (`.cursor/agents/device-firmware.md`).
- `docs/TAILSCALE_REMOTE_DEVICE_GUIDE_FEB09_2026.md` – **Tailscale VPN setup for remote devices**: Install Tailscale, join Mycosoft tailnet, configure heartbeat environment variables, auto-IP detection via `tailscale_utils.py`, verify device appears in Network tab. Also covers Cloudflare Tunnel alternative.
- `scripts/mycobrain-remote-setup.ps1` – **Automated remote setup script**: Install Tailscale, clone repo, install dependencies, configure environment, start service.
- `mycosoft_mas/core/routers/device_registry_api.py` – **Device Registry API**: Heartbeat registration, device listing, command forwarding, telemetry fetching for network-connected MycoBrain devices.
- `services/mycobrain/tailscale_utils.py` – **Tailscale utilities**: Auto-detect Tailscale IP, fallback to LAN IP, connection type detection.

## System Status, Purge, GitHub Path (Feb 9, 2026)
- `docs/SYSTEM_STATUS_AND_PURGE_FEB09_2026.md` – **Status and purge**: What’s done, what can be done, Cloudflare purge (credentials in .env.local or “agents cat”), GitHub-as-source-of-truth for MAS and website, and “always read latest docs” rule for agents.

## Cursor Suite Audit (Feb 12, 2026)
- `docs/CURSOR_SUITE_AUDIT_FEB12_2026.md` – **Rules, agents, indexing, interaction**: Single reference for all 25 rules, 32 sub-agents, index flow (CURSOR_DOCS_INDEX → MASTER_DOCUMENT_INDEX → docs_manifest / gap reports), and re-audit checklist. Use when verifying or updating the Cursor suite.
- `docs/CURSOR_MCP_AND_EXTENSIONS_FEB12_2026.md` – **MCPs, extensions, sub-agent usage**: Which MCPs Cursor uses (.mcp.json: github, mindex-db; plus Supabase, Context7, Cloudflare, cursor-ide-browser when enabled). Which sub-agents to use for which tasks; MCP-by-task table; extensions note.

## Cursor Docs Indexing and Notion (Feb 12, 2026)
- `docs/CURSOR_DOCS_INDEXING_AND_NOTION_FEB12_2026.md` – **Why Cursor doesn’t see 2000+ docs / Notion**: Context limits, no auto-load of every file; Notion is one-way sync for humans. Use `.cursor/CURSOR_DOCS_INDEX.md` (vital/current), `.cursor/docs_manifest.json` (full discovery), and `docs/MASTER_DOCUMENT_INDEX.md`. New docs replace old in CURSOR_DOCS_INDEX.

## Always-On Services (Feb 12, 2026)
- `docs/ALWAYS_ON_SERVICES_FEB12_2026.md` – **Complete environment reference**: Local dev (Docker Desktop) vs VM production always-on services. Architecture diagrams, communication flow, health checks, deployment prerequisites. Single source for what must run locally and on VMs.

## Redis Pub/Sub Real-Time Messaging (Feb 12, 2026)
- `docs/REDIS_PUBSUB_USAGE_FEB12_2026.md` – **Production-ready Redis pub/sub system**: Real-time messaging using Redis on VM 192.168.0.189:6379. Four channels implemented: `devices:telemetry` (sensor data), `agents:status` (health updates), `experiments:data` (lab streams), `crep:live` (aviation/maritime updates). Includes RedisPubSubClient with automatic reconnection, connection management, publish/subscribe patterns, health monitoring, statistics tracking. NO MOCK DATA - verified real Redis integration. Includes usage examples, agent integration patterns, troubleshooting guide. Implementation: `mycosoft_mas/realtime/redis_pubsub.py`, test scripts, example agent integration.

## Docker Management (Feb 12, 2026)
- `docs/DOCKER_MANAGEMENT_FEB12_2026.md` – **Docker Desktop resource management**: Container lifecycle, image cleanup, MAS integration, vmmem control. Includes rule (`.cursor/rules/docker-management.mdc`), sub-agent (`docker-ops`), and healthcheck script (`scripts/docker-healthcheck.ps1`). Ensures Docker doesn't waste resources and coordinates with VMs.

## Terminal and Python Operations (Feb 12, 2026)
- `docs/TERMINAL_AND_PYTHON_OPERATIONS_GUIDE_FEB12_2026.md` – **Operations guide**: What must run for MYCA/Search/multi-agent, autostart services, processes to kill (zombies, GPU), sub-agent execution rules. Single reference for terminal and Python process management.

## Cursor System Registration (Feb 10, 2026)
- `docs/CURSOR_SYSTEM_REGISTRATION_AUDIT_FEB10_2026.md` – **Audit and implementation**: Rules, agents, and skills are registered in the Cursor system via `scripts/sync_cursor_system.py`. Always-apply rule `.cursor/rules/cursor-system-registration.mdc` requires running the sync after creating or updating any rule, agent, or skill so they work globally in Cursor, not only in the workspace.

## System Gaps and Remaining Work (Feb 10, 2026)
- `docs/SYSTEM_GAPS_AND_REMAINING_WORK_FEB10_2026.md` – **Single reference for remaining work**: Summary counts (TODOs, stubs, 501 routes, indexed gaps), critical/high items, index-based missing work, suggested plans. Maintained via gap reports and `scripts/gap_scan_cursor_background.py`. Quality agents use gap reports as gap-first intake.

## Work, To-Dos, Gaps, Missing Agents/Rules (Feb 10, 2026)
- `docs/WORK_TODOS_GAPS_AND_MISSING_AGENTS_RULES_FEB10_2026.md` – **Run-through**: Current work streams, incomplete plans, vision vs implementation gaps, Cursor vs project alignment (see `docs/CURSOR_SUITE_AUDIT_FEB12_2026.md` for current counts: 32 agents, 25 rules), missing sub-agents/rules, and recommended additions. New rule: `.cursor/rules/fci-vision-alignment.mdc` for FCI/HPL/Mycorrhizae vision alignment.

## Gap Agent (Feb 10, 2026)
- `docs/GAP_AGENT_FEB10_2026.md` – **Cross-repo gap agent**: Finds gaps between repos and agents (TODOs, FIXMEs, stubs, 501 routes, bridge/integration gaps); suggests plans; runs in 24/7 runner; API at `/agents/gap/scan`, `/agents/gap/plans`, `/agents/gap/summary`. Use when multiple agents work on multiple projects and a “third” connection or bridge might be missing.

## GitHub Push HTTP 500 — Root Cause (Feb 10, 2026)
- `docs/GITHUB_PUSH_500_ROOT_CAUSE_FEB10_2026.md` – **Why push failed on this machine**: LFS was fully disabled (`.lfsconfig` `concurrenttransfers = 0`) after the PersonaPlex 1.74 TB incident; that same setting broke push and caused GitHub HTTP 500. Fix: `concurrenttransfers = 1` with `fetchexclude = *` (push works, PC still doesn’t download LFS). Push verified successful after fix.

## Phase 1 Agent Runtime (Feb 9–10, 2026)
- `docs/PHASE1_AGENT_RUNTIME_EXECUTION_REPORT_FEB09_2026.md` – Phase 1 execution report: all 42 AGENT_CATALOG agents implemented (orchestration, utility, workflow, integration, voice, memory, NatureOS, MycoBrain, financial), runner loader/startup, optional iot_envelope, v2 resilient imports, VM compatibility.
- `docs/PHASE1_COMPLETION_LOG_FEB10_2026.md` – **Completion log**: What was implemented, committed (f70d25b), push status, deployment procedure for MAS VM 192.168.0.188, verification steps (health, runner/status, agents, cycles), and summary table.

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
- `docs/CREDENTIAL_MANAGEMENT_BEST_PRACTICES_FEB09_2026.md` – **Credential best practices**: Pre-commit hooks with detect-secrets, .env patterns, what to do after credential exposure, rotation checklists, tools (detect-secrets, truffleHog, GitHub Secret Scanning).

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
