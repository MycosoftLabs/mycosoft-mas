# Master Document Index

## Network Topology and Ubiquiti (Mar 7, 2026)
- `docs/NETWORK_TOPOLOGY_UBIQUITI_PLAN_MAR07_2026.md` – **Network topology and Ubiquiti labeling plan**: 192.168.0.x device designations (NodeFather crypto, C-Suite, R710/R630, Proxmox 202); segregation (public Proxmox vs internal R710); Ubiquiti labeling table; C-Suite VM migration R710; UniFi scan script usage.
- `docs/NETWORK_IP_MAC_DEVICE_MAP_MAR07_2026.md` – **Full IP/MAC/device map (Mar 7, 2026)**: ARP-scan-validated map of 192.168.0.0/24; IP→MAC→role table; Proxmox 202 vs R720 layout; C-Suite migration plan; NodeFather, NAS, Edge R630; UniFi labeling reference.
- `docs/UNIFI_SCAN_RESULTS_MAR07_2026.md` – **UniFi topology scan results (Mar 7, 2026)**: Credentials stored; scan run; login failed (no device list); command used; next steps when login works; intended output format; link to topology plan.

## Sandbox / MAS / MINDEX Recovery (Mar 12, 2026)
- `docs/SANDBOX_MAS_MINDEX_RECOVERY_AND_REDEPLOY_MAR12_2026.md` – **Recovery + redeploy report**: Sandbox outage recovery, Cloudflare tunnel/cache purge, website container stabilization, MAS/MINDEX health verification, and final runtime state.

## Production VM Clone and CI/CD (Mar 13, 2026)
- `docs/MYCOSOFT_ORG_PRODUCTION_VM_CLONE_CI_CD_MAR13_2026.md` – **Production VM clone + CI/CD**: Clone Sandbox→Production (186), Cloudflare tunnels (mycosoft.com vs sandbox.mycosoft.com), mycosoft.org→mycosoft.com/about redirect, _rebuild_production.py, verification checklist. Use for Production deploy and VM layout.
- `docs/PRE_PRODUCTION_CHECKLIST_MAR13_2026.md` – **Pre-production checklist**: Cloudflare tunnels/DNS, Supabase auth redirect URLs, MAS/MINDEX API routes; verification commands; credentials. Run before going live.

## Production Jetson+MycoBrain Deploy (Mar 13, 2026)
- `docs/JETSON_MYCOBRAIN_PRODUCTION_DEPLOY_MAR13_2026.md` – **Jetson+MycoBrain production deployment**: BOM for Mushroom 1/Hyphae 1/Gateway; wiring diagram (Side A/B, Jetson); flash procedure (Side A then Side B); Jetson install.sh and systemd; verification checklist (health, MAS registry, NLM, MINDEX FCI); file reference.

## MycoBrain Gateway Node Recognition (Mar 13, 2026)
- `docs/MYCOBRAIN_GATEWAY_NODE_RECOGNITION_MAR13_2026.md` – **Gateway recognition implemented**: deterministic serial port allowlist (`MYCOBRAIN_ALLOWED_PORTS`), gateway-mode service startup, local gateway bring-up script, and verified MAS registration + command routing for COM7 gateway node.
- `docs/MYCOBRAIN_LORA_GATEWAY_LINK_TEST_PLAN_MAR13_2026.md` – **LoRa link validation plan**: gateway-only and gateway+peer MAS command-proxy test flow for validating local yard LoRa ingestion readiness.

## MYCA Voice + Chat Fixes (Mar 2, 2026)
- `docs/MYCA_PRODUCTION_REQUIREMENTS_MAR02_2026.md` – **MYCA production requirements**: MAS reachable, at least one LLM key (e.g. GROQ), optional MINDEX/n8n; VM layout; verification steps; behavior when all providers fail.

## Voice v9 (Mar 2, 2026)
- `docs/VOICE_V9_BASELINE_AUDIT_MAR02_2026.md` – **Voice v9 baseline audit**: End-to-end live path; Bridge + Brain as single authority; duplicate MAS call risks; observability recommendations; v9 migration baseline.
- `docs/VOICE_V9_DUPLEX_PERSONA_COMPLETE_MAR02_2026.md` – **Voice v9 duplex and persona lock complete**: InterruptManager, PersonaLockService, REST/WebSocket endpoints; barge-in, persona validation, identity-safe TTS.
- `docs/VOICE_V9_DEPLOYMENT_RUNTIME_MAR02_2026.md` – **Voice v9 deployment and runtime**: Dev vs production topology; env contracts; startup order; rollout stages; v9 API endpoints.

## Code Unification (Mar 11, 2026)
- `docs/CODE_UNIFICATION_STATUS_MAR11_2026.md` – **Code unification status**: Pushed local Cursor work to main; open PRs blocked by conflicts/CI; what was unified, what remains, recommended next steps.

## CREP Integration Test Plan (Mar 10, 2026)
- `WEBSITE/website/docs/CREP_INTEGRATION_TEST_PLAN_MAR10_2026.md` – **CREP integration test plan**: Canonical plan for validating CREP integrations; P0 biodiversity/wildlife bubble selection (done); satellite imagery (MODIS, VIIRS, AIRS, Landsat, EONET), Shadowbroker, deck.gl filters, military filters, VIZ test features; test matrix and completion checklist.

## CREP Command Contract (Mar 13, 2026)
- `docs/CREP_COMMAND_CONTRACT_MAR13_2026.md` – **CREP command contract (canonical)**: Single schema for CREP map commands (flyTo, showLayer, setTimeCursor, etc.) from MAS to website; entrypoint, types, fields, request/response models; source files and validation requirements.

## CREP System Integration Audit (Mar 11, 2026)
- `docs/CREP_SYSTEM_INTEGRATION_AUDIT_MAR11_2026.md` – **CREP system integration audit**: Surface-by-surface read/write/search/interact and Merkle/MINDEX grounding across MAS, WEBSITE, MINDEX, NatureOS; gap list; blocking mock/stub paths.
- `docs/CREP_FIRST_EXECUTION_CHECKLIST_MAR11_2026.md` – **CREP-first execution checklist**: Unified entities, local-first persistence, provenance grounding; repo/file ownership; CREP wave deliverables.
- `docs/CORE_PLATFORM_HARDENING_PLAN_MAR11_2026.md` – **Core platform hardening plan**: Simulated MINDEX router removal; Merkle→MINDEX mica ledger; investigation stub reconciliation; API contract normalization.
- `docs/CREP_FOLLOW_ON_BACKLOG_MAR11_2026.md` – **CREP follow-on backlog**: Search, device mapping, analytics, Ancestry, Petri prioritized by dependency order and gap severity.
- `docs/INTEGRATION_TEST_MATRIX_MAR11_2026.md` – **Integration test matrix**: VM reachability smoke, regression guardrails (no mock/sample/stub), CREP/search/device/ancestry contract tests; execution matrix; implementation checklist.

## CREP Species Widgets & Viewport Loading (Mar 11, 2026)
- `docs/CREP_SPECIES_WIDGETS_VIEWPORT_LOADING_COMPLETE_MAR11_2026.md` – **CREP species widgets & viewport loading complete**: Fungal data from map bounds only (fetchData no longer overwrites); bounds effect AbortController; FilterToggle layout stability; iNaturalist-style viewport loading.
- `docs/CREP_SPECIES_ICONS_CLICKABLE_FIX_MAR11_2026.md` – **CREP species icons clickable fix**: deck.gl overlay z-index/pointer-events; marker container above overlay; FungalMarker type=button; formatObs geometry.coordinates support.

## CREP Fungal Route Reliability (Mar 11, 2026)
- `WEBSITE/website/docs/CREP_FUNGAL_ROUTE_RELIABILITY_MAR11_2026.md` – **CREP fungal route reliability**: MINDEX API key, graceful degradation (200 with empty data on failure), fetchWithRetry for iNaturalist/GBIF (10s timeout, 2 retries), 1.5MB cache limit; test results; MINDEX=0 investigation notes.

## MYCA-Only Architecture (Mar 9, 2026)
- `docs/MYCA_ONLY_ARCHITECTURE_COMPLETE_MAR09_2026.md` – **MYCA-only architecture complete**: Ollama primary 99.9%; no frontier fallback for user chat; Merkle world root integration; device/world grounding; BRAIN intent memory via MAS.

## MICA Merkle Ledger (Mar 9, 2026)
- `docs/MICA_MERKLE_LEDGER_INTEGRATION_MAR09_2026.md` – **Merkleized cognition ledger integrated**: Event leaves, temporal/spatial/self/world/thought roots, BLAKE3+CBOR hashing; MAS API `/api/merkle/*`; MINDEX migration `0021_mica_merkle_ledger`; consciousness integration point documented.

## Full Integration Program (Mar 10, 2026)
- `docs/INTEGRATION_CONTRACTS_CANONICAL_MAR10_2026.md` – **Canonical integration contracts**: Unified entities, investigation artifacts, red-team audit, operator tasks, agent payments, Jetson/MycoBrain edge telemetry. Phase 0 of Full Integration Master Program.
- `docs/EDGE_UNIFICATION_COMPLETE_MAR10_2026.md` – **Edge unification complete**: Jetson/MycoBrain runtime, telemetry, CREP presence, MYCA/AVANI interaction; GET /api/devices/crep for CREP UnifiedEntity format; Phase 7 of Full Integration Master Program.

## External Repo Integration (Mar 10, 2026)
- `docs/EXTERNAL_REPO_INTEGRATION_COMPLETE_MAR10_2026.md` – **Phase 1 complete**: Label syncer, Uncodixfy rule, Turf bbox validation, CrepMapPreferencesPanel, Supabase CREP preferences API, MAS finance route + website proxy; test results; verification commands.
- `docs/EXTERNAL_REPO_FEATURES_USAGE_AND_TESTING_MAR10_2026.md` – **Feature usage & testing**: How each feature works; where to see/use it (CREP Map Preferences, fungal API, finance proxy, label syncer); step-by-step interaction flows; CREP and Uncodixfy UI rules; verification commands and test results.
- `docs/EXTERNAL_REPO_SYSTEM_BOUNDARIES_MAR10_2026.md` – **System boundaries and extension seams**: MAS, WEBSITE, MINDEX, MycoBrain, Mycorrhizae, NatureOS boundaries; VM layout; extension seams for external repo integration.
- `docs/EXTERNAL_REPO_CLASSIFICATION_MAR10_2026.md` – **Repository classification**: Adopt, Prototype, Watchlist, Do Not Integrate for 18 external repos; rationale and insertion points.
- `docs/EXTERNAL_REPO_IMPLEMENTATION_STREAMS_MAR10_2026.md` – **Implementation streams**: Geo stack, local inference, finance, security, repo hygiene; phased execution.
- `docs/EXTERNAL_REPO_GAP_ALIGNMENT_MAR10_2026.md` – **Gap alignment**: Cross-check against platform gaps; blocking rules; sequencing so new work strengthens architecture.

## Test-Voice / PersonaPlex (Mar 10–11, 2026)
- `docs/TTS_FALLBACK_PERSONAPLEX_MAR11_2026.md` – **TTS fallback for PersonaPlex**: Moshi does not support `0x02` text injection; Bridge uses edge-tts for TTS; dependencies, flow, troubleshooting.
- `docs/CUDA_GRAPH_REENABLED_PERSONAPLEX_MAR10_2026.md` – **CUDA graph re-enabled for PersonaPlex**: Required for real-time voice; `start_voice_system.py` and myca-voice-system.mdc updated to default `NO_CUDA_GRAPH=0`.
- `docs/TEST_VOICE_LOCAL_FIX_MAR10_2026.md` – **Test-voice local voice fix**: Bridge health non-blocking; diagnostics TCP fallback; local Moshi + PersonaPlex Bridge (8998/8999) with `NEXT_PUBLIC_USE_LOCAL_GPU=true`.

## MYCA Live Activity Panel (Mar 9, 2026)
- `docs/MYCA_LIVE_ACTIVITY_PANEL_COMPLETE_MAR09_2026.md` – **MYCA Live Activity Panel complete**: Activity log (newest first, consciousness entry), FlowDot enlargement, text size bumps, mobile collapsible height.

## Public AI Rollout (Mar 9, 2026)
- `WEBSITE/website/docs/PUBLIC_AI_ROLLOUT_COMPLETE_MAR09_2026.md` – **Public AI rollout complete**: New `/ai` overview; MYCA, AVANI, NLM as sole public AI products; unified nav; marketing rewrite; agentic CTAs to contact; docs hub; source of truth for public AI IA.

## CREP / iNaturalist / MINDEX (Mar 9, 2026)
- `docs/CREP_INATURALIST_MINDEX_ETL_MAR09_2026.md` – **CREP iNaturalist→MINDEX ETL and local-first design**: Clone-on-first-display; iNaturalist bulk ETL; LOD (zoom-based clustering); local-first routing; MINDEX as primary, iNaturalist fallback then clone.
- `WEBSITE/website/docs/PUBLIC_AI_INFORMATION_ARCHITECTURE_MAR09_2026.md` – **Public AI IA**: Final routes, page roles, nav model.
- `WEBSITE/website/docs/AGENTIC_CONVERSION_BRIDGE_MAR09_2026.md` – **Agentic conversion bridge**: Future path to pricing, onboarding, API keys, paid agent access.

## PR #75: Jetson + Avani-Micah + Identity (Mar 9, 2026)
- `docs/PR75_IMPLEMENTATION_PLAN_MAR09_2026.md` – **PR75 implementation plan**: Deployment status, security remediation, plans, docs, frontend implementations; Guardian, Avani, Identity, Liquid Fungal APIs; Jetson hardware; Micah/MAS tool integration; multi-agent app flows; marketing pages.
- `docs/PR75_AUTH_GUARDS_COMPLETE_MAR09_2026.md` – **PR75 auth guards complete**: Guardian, Avani, Identity APIs now require scoped API keys on mutating endpoints; verification, migration script, scope reference.
- `docs/JETSON_MYCOBRAIN_HARDWARE_PLAN_MAR09_2026.md` – **Jetson + MycoBrain hardware plan**: Mushroom 1 (AGX Orin 32GB) and Hyphae 1 (Orin Nano Super 8GB); ESP32-S3 MycoBrain, dual BME688, FCI, LoRa mesh.
- `docs/AVANI_MICAH_CONSTITUTION_MAR09_2026.md` – **Avani–Micah constitutional governance**: Season Engine, Governor, Vision, Constitution, rights, red lines.
- `docs/MICAH_GUARDIAN_ARCHITECTURE_MAR09_2026.md` – **Micah Guardian architecture**: Independent Constitutional Guardian, Moral Precedence, Anti-Ultron Tripwires, Authority Engine, Awakening Protocol.
- `docs/RECIPROCAL_TURING_PROTOCOL_MAR09_2026.md` – **Reciprocal Turing identity integration**: Identity API, Mode Manager, Continuity Manager, honest uncertainty.

## Sandbox / Production Always-On (Mar 2, 2026)
- `docs/VM_POWER_OFF_FIX_MAR09_2026.md` – **VM power-off fix**: Sandbox/C-Suite shutting down; Proxmox `onboot 1`, root-cause checklist, resource split (move C-Suite to separate host); fix steps; VM-to-host mapping.
- `docs/SANDBOX_AND_PRODUCTION_ALWAYS_ON_MAR02_2026.md` – **Why Sandbox was off and production prevention**: Root causes (VM not start-on-boot, tunnel not enabled at boot); checklist so Sandbox and any mycosoft.com production clone never stay off.
- `docs/SANDBOX_UNREACHABLE_STATUS_MAR02_2026.md` – **Sandbox unreachable status (resolved)**: 187 was off; when back on, deploy was run; link to always-on doc.

## Planning → Ethics Context System (Mar 3, 2026)
- `docs/PLANNING_ETHICS_CONTEXT_COMPLETE_MAR03_2026.md` – **Completion + verification**: Checklist for testing and documenting; scope summary.
- `docs/PLANNING_ETHICS_CONTEXT_SYSTEM_MAR03_2026.md` – **Planning engine → ethics context**: What context the planning engine supplies to the ethics system; simulations, training source material, ethics guidelines; document types (ethics updates, training capabilities, plans); epistemic alignment per Michele outline.
- `docs/michele_alignment_debate_outline.docx.md` – **Epistemic alignment debate outline**: Epistemic vs. safety alignment, source bias, model uncertainty, temporal/spatial reasoning; reference for planning→ethics epistemic discipline.

## Supabase Operational Backbone (Mar 7, 2026)
- `docs/SUPABASE_OPERATIONAL_BACKBONE_COMPLETE_MAR07_2026.md` – **Supabase backbone complete**: External ingest (Asana/Notion/GitHub), LLM usage ledger, ingest API, spreadsheet sync, n8n Ingest→Sync pipeline.

## Master Spreadsheet Automation (Mar 7, 2026)
- `docs/MASTER_SPREADSHEET_AUTOMATION_MAR07_2026.md` – **Master spreadsheet automation**: Inventory + hardware sync; n8n/Zapier/MYCA integration; config, API, enabling additional tabs.
- `docs/SUPABASE_GOOGLE_SHEETS_AUTOMATION_MAR07_2026.md` – **Supabase + Google Sheets full automation**: One-time GCP service account setup; credential options; run `_automate_supabase_and_sheets.py`; tabs without GID supported.

## CFO MCP Connector (Mar 8, 2026)
- `docs/CFO_MCP_CONNECTOR_COMPLETE_MAR08_2026.md` – **CFO MCP Connector complete**: Meridian/Perplexity hybrid; finance discovery layer; CFO MCP server; Meridian adapter; C-Suite reporting upgrades; MYCA federation integration; dynamic finance agent discovery.

## C-Suite Unattended Install (Mar 11, 2026)
- `docs/CSUITE_UNATTENDED_INSTALL_MAR11_2026.md` – **C-Suite unattended Windows 10 install and clone**: COO golden image, autounattend.xml, build ISO, run install, clone CEO/CTO/CFO; workflow and troubleshooting.

## C-Suite OpenClaw VM Rollout (Mar 7–8, 2026)
- `docs/CTO_VM194_ROLLOUT_VERIFICATION_MAR08_2026.md` – **CTO VM 194 rollout verification**: Acceptance checklist for provision, bootstrap, runtime health, Forge bridge, watchdogs, MYCA visibility; use before implementation and for fresh-clone rebuilds.
- `docs/CSUITE_WINDOWS_INSTALL_FIX_MAR07_2026.md` – **C-Suite Windows install fix**: scsi0→sata0 so installer sees disk; "Upgrade isn't available" / Custom shows no disk fixed; `infra/csuite/fix_vm_disk_sata.py --use-ssh`.
- `docs/CSUITE_WINDOWS10_FALLBACK_MAR07_2026.md` – **Windows 10 fallback**: Proxmox host may not support Win11 (UEFI/TPM); config `windows_version: "10"` or `"11"`; compatibility check script; provisioning and fix script use correct ISO/ostype.
- `docs/CSUITE_WINDOWS10_ISO_DEPLOY_COMPLETE_MAR07_2026.md` – **C-Suite Windows 10 ISO deploy complete**: Fido→download Win10 22H2→upload to Proxmox 202; all four VMs (192–195) boot from installer; `scripts/download_and_deploy_win10_iso.py`.
- `docs/CSUITE_WINDOWS_EXECUTION_COMPLETE_MAR07_2026.md` – **C-Suite Windows execution complete**: Ran fix pipeline on Proxmox 202; all four VMs (192–195) have Win11 ISO attached and boot; manual setup in Proxmox console; revert-to-Win10 steps.
- `docs/PROXMOX202_AUTH_SETUP_MAR08_2026.md` – **Proxmox 202 auth setup**: One-time setup for root password, API token, or SSH key; credential fallback chain; auth attempt order.
- `docs/CSUITE_COO_PROVISION_COMPLETE_MAR07_2026.md` – **COO provision complete (blocked on auth)**: COO VM 195 defined; PROXMOX202_USE_PASSWORD=1 support; token 403 / password 401; fix steps and provision commands.
- `docs/CSUITE_ROLLOUT_CLONE_FIXES_MAR07_2026.md` – **Clone fixes**: 30-min timeout for clones, unlock before start for existing VMs, auth error hint; re-run blocked until PROXMOX202_PASSWORD in .credentials.local.
- `docs/CSUITE_OPENCLAW_VM_ROLLOUT_COMPLETE_MAR07_2026.md` – **C-Suite VM rollout complete**: Four executive-assistant VMs (CEO/CFO/CTO/COO) on Proxmox 90; role-based provisioning; OpenClaw golden image; MAS heartbeat/report/escalate integration; VM IPs 192.168.0.192–195.
- `docs/CSUITE_OPENCLAW_GOLDEN_IMAGE_MAR07_2026.md` – **Golden image procedure**: Windows bootstrap, OpenClaw install, persona seeds, policy defaults.
- `config/proxmox202_csuite.yaml` – **Proxmox 202 C-Suite config**: Host 192.168.0.202:8006, VMs 192–195, guest_os windows (co-located with MYCA 191).
- `config/csuite_role_manifests.yaml` – **Role manifests**: CEO (Atlas/MYCAOS), CFO (Meridian/Perplexity), CTO (Forge/Cursor), COO (Nexus/Claude Cowork).

## MycoBrain Sandbox Always-On (Mar 7, 2026)
- `docs/MYCOBRAIN_SANDBOX_ALWAYS_ON_COMPLETE_MAR07_2026.md` – **MycoBrain Sandbox always-on complete**: systemd infinite restarts, 1-min watchdog, ensure script in deploy pipeline; service on 192.168.0.187:8003; Docker `host.docker.internal` for website container.

## MycoBrain Firmware Baseline (Mar 7, 2026)
- `docs/MYCOBRAIN_FIRMWARE_BASELINE_REBASELINE_MAR07_2026.md` – **Rebaseline**: DeviceManager/DualMode = operational truth; SideA/SideB = target split; MycoBrain_Working = recovery-only; ScienceComms = experimental reference.

## MycoBrain Rail Unification (Mar 7, 2026)
- `docs/MYCOBRAIN_RAIL_UNIFICATION_COMPLETE_MAR07_2026.md` – **Completion**: Heartbeat canonical, capability manifest, FCI bridge, Jetson path, Side B transport.
- `docs/MYCOBRAIN_CAPABILITY_MANIFEST_MAR07_2026.md` – **Capability manifest**: Role→sensors/capabilities contract; firmware→service→MAS→website.
- `docs/FCI_MYCORRHIZAE_BRIDGE_DESIGN_MAR07_2026.md` – **FCI/Mycorrhizae bridge**: Single device_id for MycoBrain + FCI; MAS fci-summary endpoint.
- `docs/JETSON_OPTIONAL_CORTEX_PATH_MAR07_2026.md` – **Jetson optional cortex**: Identity unchanged; Jetson as optional inference/backhaul layer.
- `docs/DEVICE_JETSON16_CORTEX_ARCHITECTURE_MAR07_2026.md` – **16GB Jetson on-device cortex**: Role between Side A and Side B; command arbitration, operator runtime, MDP rail, MYCA integration, identity rules.
- `docs/GATEWAY_JETSON4_LILYGO_ARCHITECTURE_MAR07_2026.md` – **4GB Jetson + LilyGO gateway**: On-site aggregation, LoRa/SIM/BLE/WiFi, store-and-forward, upstream publish to MAS/Mycorrhizae/MINDEX.
- `docs/SIDE_B_TRANSPORT_AND_BACKHAUL_MAR07_2026.md` – **Side B transport-only**: Modem/gateway strategy; device identity on Side A.
- `docs/MDP_PROTOCOL_CONTRACTS_MAR07_2026.md` – **MDP internal rail + gateway upstream**: Side A↔Jetson16↔Side B command families; gateway→MAS/Mycorrhizae/MINDEX/website publish contracts; identity invariants.
- `docs/MYCOBRAIN_FIRMWARE_ROADMAP_MAR07_2026.md` – **Side A/Side B firmware roadmap**: MDP layer, command alignment, transport directives, implementation phases.
- `docs/DEVICE_NETWORK_EDGE_GATEWAY_AWARENESS_MAR07_2026.md` – **Edge-cortex and gateway awareness**: Capability manifest, display labels, identity invariants for Device Manager/Network.
- `docs/EDGE_OPERATOR_SAFETY_MAR07_2026.md` – **Edge operator safety**: Audit, approval, rollback, code/firmware mutation boundaries.
- `docs/JETSON_BACKED_MYCORBRAIN_ARCHITECTURE_COMPLETE_MAR07_2026.md` – **Plan complete**: All seven todos done; deliverables summary.
- `docs/JETSON_FIRMWARE_IMPLEMENTATION_GUIDE_MAR07_2026.md` – **Implementation guide**: New SideA/SideB MDP firmware targets, on-device operator service, gateway router service, run/flash instructions.

## MycoBrain Supabase Telemetry (Mar 7, 2026)
- `docs/MYCOBRAIN_SUPABASE_TELEMETRY_ARCHITECTURE_MAR07_2026.md` – **MycoBrain → Supabase telemetry**: Data flow (device → MycoBrain → Ingest API → Supabase); Device Manager + MINDEX; why Supabase over SQLite; env vars `TELEMETRY_INGEST_URL`, `TELEMETRY_INGEST_API_KEY`; verification steps.
- `docs/DEVICE_UI_VERIFICATION_COMPLETE_MAR07_2026.md` – **Device UI verification**: Device Network, Device Manager, controls, comms, I2C peripherals, firmware — all verified working in UI; APIs and fallbacks in place; hardware E2E pending.

## BOM / Device Components (Mar 7, 2026)
- `docs/MYCOBRAIN_JETSON_GATEWAY_BUILD_PLAN_MAR07_2026.md` – **MycoBrain→Jetson→MYCA gateway build plan**: Tier 1 Mushroom 1 (Orin NX Super), Tier 2 Hyphae 1 (Waveshare Nano/Xavier NX), Tier 3 Gateway (Nano B01); BOM, firmware, connections, Big Device 12V solar power; step-by-step build instructions.
- `docs/COMPONENT_NAMES_STAFF_GUIDE_MAR07_2026.md` – **Staff component names**: Short, clear names for staff; which components go into which device (Mushroom 1, SporeBase, ALARM, MycoNODE, Hypha 1); ID→name map; naming rules; gaps list.
- `docs/DEVICE_PRODUCTS_AND_MYCOFORGE_SYNC_MAR07_2026.md` – **MycoForge sync**: Canonical product registry (`device-products.ts`) ↔ Supabase `products`; seed script, PreOrderModal productId, BOM/components flow.
- `docs/COMPONENTS_REMOVED_MAR07_2026.md` – **Non-BOM removal list**: 117 items removed from Supabase `components` (house, furniture, shop tools, office, personal). Kept 185 device BOM components. Use to restore any erroneously removed item.
- `scripts/remove_non_bom_components.py` – **Script**: Filters `components` to 5 Mycosoft device BOM only; run with `--dry-run` to preview.
- `scripts/update_component_names_for_staff.py` – **Script**: Updates Supabase `components.name` to staff-friendly short names; run with `--dry-run` to preview.
- `docs/INVENTORY_GOOGLE_SHEETS_SYNC_MAR07_2026.md` – **Inventory→master sheet sync**: Supabase components → CSV + optional push to master Google Sheet tab; run after any inventory change.
- `scripts/sync_components_to_google_sheets.py` – **Script**: Fetches components from Supabase, writes CSV, optionally pushes to master sheet; use `--push` with credentials.

## Gap Plan Completion (Mar 5, 2026)
- `docs/GAP_PLAN_COMPLETION_MAR05_2026.md` – **Gap plan complete**: Critical, High, Quick Wins, Medium in-scope items verified or done; NatureOS summary API added; deferred items documented.
- `docs/GAP_PLAN_LARGE_SCAFFOLDING_MAR05_2026.md` – **Large items scaffolding**: Design stubs for Jobs 18–23 (control plane, worldview digest, unified front door, NatureOS bridge, MycoBrain awareness, workflow visibility).
- `docs/GAP_PLAN_CHANGES_LOG_MAR07_2026.md` – **Gap plan changes log**: Audit trail of all code and doc changes during gap execution; WEBSITE + MAS commits, new/modified files, verification checks, build regression.

## MYCA Support Upgrade Implementation (Mar 7, 2026)
- `docs/MYCA_SUPPORT_UPGRADE_IMPLEMENTATION_COMPLETE_MAR07_2026.md` – **Implementation complete**: 10 items (5 quick wins, 5 medium); MYCA state widget, Morgan oversight panel, EP summary, NatureOS summary, page context, docs.

## MYCA Support Upgrade Docs (Mar 7, 2026)
- `docs/MINDEX_A2A_AGENT_FOR_MYCA_MAR07_2026.md` – **A2A agent for MYCA**: MINDEX A2A delegation path for search/stats; MAS MINDEXBridge usage.
- `docs/COWORK_VS_MYCA_SCOPE_MAR07_2026.md` – **Cowork vs MYCA scope**: When to use each; handoff pattern; unified front door.
- `docs/MYCOBRAIN_TO_MAS_FLOW_MAR07_2026.md` – **MycoBrain→MAS flow**: Heartbeat, device registry, MYCA query path.
- `docs/MYCA_N8N_TRIGGER_PATTERN_MAR07_2026.md` – **MYCA→n8n trigger**: Standard pattern for MYCA to trigger workflows.
- `docs/MYCORRHIZAE_MYCA_TELEMETRY_BRIDGE_MAR07_2026.md` – **Mycorrhizae→MYCA bridge**: Design for FCI telemetry injection (future).

## MYCA Support Upgrade Audit (Mar 7, 2026)
- `docs/MYCA_SUPPORT_UPGRADE_AUDIT_MAR07_2026.md` – **Cross-system upgrade audit**: Website, MINDEX, NatureOS, MycoBrain, external AI/cowork, automation. Prioritized plan (quick wins, medium, large) for MYCA–Morgan interaction, context, visibility, supervise/steer/trust.
- `docs/NEXT_JOBS_FROM_GAPS_MAR07_2026.md` – **Next jobs from gaps**: Prioritized job list (Critical → High → Quick wins → Medium → Large) derived from platform status, upgrade audit, system gaps. Use for sprint planning.

## MYCA Full Omnichannel Execution (Mar 6, 2026)
- `docs/MYCA_FULL_OMNICHANNEL_EXECUTION_COMPLETE_MAR06_2026.md` – **Full execution complete**: code changes, test fixes, full suite passing, GitHub push, VM 191 deploy, VM 188 refresh, health verification, and remaining known issues.

## MYCA Bounded Personal Agency (Mar 6, 2026)
- `docs/MYCA_BOUNDED_PERSONAL_AGENCY_COMPLETE_MAR06_2026.md` – **Phase 6 complete**: personal-agency and autonomous-self modules wired into the daemon with enable flags and queue-budget gating.

## MYCA Agent and Tool Federation (Mar 6, 2026)
- `docs/MYCA_AGENT_AND_TOOL_FEDERATION_COMPLETE_MAR06_2026.md` – **Phase 5 complete**: first-class runtime task routes for GitHub, Asana, NatureOS, and search plus improved system-level task federation.

## MYCA Omnichannel Dialogue Bus (Mar 6, 2026)
- `docs/MYCA_OMNICHANNEL_DIALOGUE_BUS_COMPLETE_MAR06_2026.md` – **Phase 4 complete**: WhatsApp polling in the live comms hub, workspace inbox contract fixed, broader channel defaults, and better omnichannel status/env parity.

## MYCA Staff Identity and Memory (Mar 6, 2026)
- `docs/MYCA_STAFF_IDENTITY_AND_MEMORY_COMPLETE_MAR06_2026.md` – **Phase 3 complete**: canonical staff registry, shared sender resolution, person-scoped memory, staff role context injection, workspace inbox contract, and stronger non-Morgan reply routing.

## MYCA Full-System Runtime Promotion (Mar 6, 2026)
- `docs/MYCA_FULL_SYSTEM_RUNTIME_PROMOTION_COMPLETE_MAR06_2026.md` – **Phase 2 complete**: NatureOS, world model, Presence, NLM, unified search, and broader runtime context promoted into the active VM 191 MYCA loop.

## MYCA Runtime Hardening (Mar 6, 2026)
- `docs/MYCA_RUNTIME_HARDENING_COMPLETE_MAR06_2026.md` – **Phase 1 complete**: gateway auth, shell/skill gating, normalized env contract, canonical staff registry helper, workspace inbox contract, deploy script hardening, targeted regression suite passing.

## BoostVC Compliance Checklist (Mar 5, 2026)
- `docs/BOOSTVC_COMPLIANCE_CHECKLIST_MAR_2026.md` – **BoostVC compliance**: Annual operating plan, board materials, material business changes, books and records. Config: `config/board_meetings.yaml`, `docs/board/`.

## MYCA OpenWork Integration (Mar 5, 2026)
- `docs/MYCA_OPENWORK_INTEGRATION_MAR05_2026.md` – **Phases 1–5 complete**: OpenWork orchestrator, CDP browser, skills manager, webhooks, n8n bridge, 3 workflows, Ollama fallback, deploy script. Use for MYCA VM 191 integration.

## MYCA Fallback-Only Fix (Mar 5, 2026)
- `docs/MYCA_FALLBACK_FIX_MAR05_2026.md` – **Fix**: OLLAMA_BASE_URL default to MAS VM (188:11434); env vars for real AI; troubleshooting when MYCA shows only myca-local-fallback.

## Request Flow Architecture (Mar 5, 2026)
- `docs/REQUEST_FLOW_ARCHITECTURE_MAR05_2026.md` – **Request flows**: Browser → Cloudflare → VMs; Website → MAS/MINDEX; MycoBrain heartbeat; VM layout summary. Use for deployment and debugging.

## Organizational Structure Update (Mar 5, 2026)
- `docs/ORGANIZATIONAL_STRUCTURE_UPDATE_COMPLETE_MAR05_2026.md` – **Roles corrected**: Morgan = CEO/CTO/COO; RJ = Board Member + MYCA 2nd Key; Garret = Business Development. Memory, CLAUDE.md, website team-data updated.

## Grounding Production Enable (Mar 5, 2026)
- `docs/GROUNDING_PRODUCTION_ENABLE_MAR05_2026.md` – **Enable Grounded Cognition**: `MYCA_GROUNDED_COGNITION=1`, `STATE_SERVICE_URL`, StateService deploy, MINDEX grounding endpoints, Grounding Dashboard at `/dashboard/grounding`.

## Proxmox and CREP Restore (Mar 5, 2026)
- `docs/PROXMOX_CREP_RESTORE_MAR05_2026.md` – **Proxmox fix and CREP restore**: `fix_proxmox_firewall.sh`, `start_crep_collectors.sh`, Proxmox check in autostart-healthcheck, CREP in MAS `/health`. Use for VM 188 CREP deployment.

## MYCA Living Employee Full Integration Phase 0 (Mar 2, 2026)
- `docs/MYCA_LIVING_EMPLOYEE_FULL_INTEGRATION_PHASE0_COMPLETE_MAR02_2026.md` – **Phase 0 complete**: Memory injection, MAS memory API, MINDEX KG, CREP, Earth2, MycoBrain bridges; context assembly pipeline in llm_brain. MYCA OS now grounded in all platform systems before computer-use.

## MYCA Living Employee Phases 1–5 (Mar 5, 2026)
- `docs/MYCA_LIVING_EMPLOYEE_PHASES_1_5_COMPLETE_MAR05_2026.md` – **Phases 1–5 complete**: Gateway (8100), task/decision persistence, desktop tools, skills manager, 30-min Discord check-in, deploy_myca_191_v2.py, myca_cli.py.

## MYCA Platform Status and Gaps (Mar 5, 2026)
- `docs/MYCA_PLATFORM_STATUS_AND_GAPS_MAR05_2026.md` – **Consolidated status report**: Single source of truth for what's done (infrastructure, plans, fixes), what's not (VM 191 SSH blocker, MYCA channels), user inputs needed (Slack token, Discord, Asana, Signal, WhatsApp), and next steps. Use for planning, handoffs, and quick reference.
- `docs/MYCA_VM191_FULL_CAPABILITY_STATUS_MAR02_2026.md` – **VM 191 capability checklist**: Direct answers to Signal/WhatsApp/Discord, group chats, brain/memory, task-on-PC, periodic updates; what's working vs what needs setup.

## MYCA E2E Usability Test (Mar 5, 2026)
- `docs/MYCA_E2E_USABILITY_TEST_COMPLETE_MAR05_2026.md` – **Pipeline USABLE**: 10/10 tests passed. You can ask MYCA to do work on her PC (VM 191). Workspace API at 191:8100, /workspace/think, MAS chat, agents registry. Run `python scripts/_test_myca_e2e.py` to verify.

## GitHub MCP Token Setup (Mar 2, 2026)
- `docs/GITHUB_MCP_TOKEN_SETUP_MAR02_2026.md` – **GitHub MCP for issue comments**: Switched to @modelcontextprotocol/server-github; token with repo scope for add_issue_comment; config at ~/.cursor/mcp.json.

## MINDEX Health Check Fix (Mar 2, 2026)
- `docs/MINDEX_HEALTH_CHECK_FIX_MAR02_2026.md` – **MINDEX health fix**: MYCA no longer reports "MINDEX databases unreachable" when Redis/Postgres/Qdrant are not cross-VM reachable. Healthy = MINDEX API reachable only.

## Signal Spam Fix (Mar 4, 2026)
- `docs/SIGNAL_SPAM_FIX_MAR04_2026.md` – **Signal spam fix**: MYCA OS heartbeat no longer sends critical health alerts to Signal (was every 30s). Signal is for conversation only. Health issues logged only.

## MYCA Ethics Training System (Mar 4, 2026)
- `docs/MYCA_ETHICS_TRAINING_SYSTEM_MAR04_2026.md` – **Complete**: Sandbox MYCA instances, training scenarios, grading, Observer integration, website at `/ethics-training/*`.

## Perplexity Audit Response (Mar 3, 2026)
- `docs/PERPLEXITY_AUDIT_RESPONSE_MAR03_2026.md` – **Audit correction**: Corrects false claims about health layer; documents actual health, watchdog, heartbeat, graceful shutdown infrastructure.

## MYCA Ethics Philosophy Baseline (Mar 3, 2026)
- `docs/MYCA_ETHICS_PHILOSOPHY_BASELINE_MAR03_2026.md` – **Implemented**: Three-gate pipeline (Truth/Incentive/Horizon), IncentiveAuditorAgent, Clarity Brief, System Constitution 9–12, 4 new instincts, n8n ethics workflow, orchestrator + deliberation integration.

## MYCA N8N Autonomy (Mar 3, 2026)
- `docs/MYCA_N8N_AUTONOMY_COMPLETE_MAR03_2026.md` – **Plan complete**: All 7 phases — platform connectors (Discord, WhatsApp, Signal), omnichannel API, ingestion/orchestrator/response workflows, n8n bridge, loop mitigation, MYCA VM docker-compose and provision script. Deploy when VM 191 reachable.

## MYCA Desktop Workstation (Mar 3–4, 2026)
- `docs/MYCA_DESKTOP_WORKSTATION_COMPLETE_MAR03_2026.md` – **Implementation complete**: XFCE desktop, noVNC (6080), XRDP (3389), Node v20, Chrome/Cursor/VS Code/Discord/Slack/Signal, Claude Code/gh/Playwright/signal-cli, AI Python libs. Access: http://192.168.0.191:6080/vnc.html. Scripts: `_install_myca_desktop_191.py`, `_verify_myca_191.py`.
- `docs/MYCA_SELF_PROVISIONING_PLAYBOOK_MAR04_2026.md` – **MYCA self-provisioning**: Steps for MYCA to fully operate VM 191 (Claude Code official, Cursor admin, MAS/MINDEX env, gh auth). Playbook copied to `~/myca-workspace/PLAYBOOK.md` on 191. Phase 8 of install script deploys it.

## Cowork VM Continuity and Watchdog (Mar 4, 2026)
- `docs/COWORK_VM_CONTINUITY_MAR04_2026.md` – **Always-on Cowork VM**: Watchdog script, scheduled task `Mycosoft-CoworkVMWatchdog` (every 2 min), auto-start and recovery for `CoworkVMService`. Run `scripts/install-cowork-vm-watchdog.ps1` elevated. Use when automation stops or VM fails.

## Claude Cowork VM Windows Troubleshooting (Mar 3–6, 2026)
- `docs/CLAUDE_COWORK_FAILED_TO_OPEN_SOCKET_FIX_MAR06_2026.md` – **FailedToOpenSocket fix**: Cowork VM uses DNS from disconnected adapter; diagnostic commands; Option A (align DNS), Option B (disable adapters + SharedAccess + reboot), Option C (Repair/Reset); verify before moving to VM.
- `docs/CLAUDE_COWORK_VM_TROUBLESHOOTING_MAR03_2026.md` – **Cowork VM fix**: "VM service not running" regression; MSIX path bug, DCOM, Hyper-V; run `scripts/fix-claude-cowork-vm.ps1`; use exe installer from claude.ai/download to avoid MSIX.

## C-Suite COO Golden Setup (Mar 11, 2026)
- `docs/CSUITE_COO_GOLDEN_SETUP_MAR11_2026.md` – **C-Suite golden image**: OpenClaw bootstrap, Claude Cowork (COO), Perplexity (CFO), Cursor (CTO), MycaOS (CEO); remote bootstrap via WinRM or manual RDP; `setup_csuite_golden_full.ps1`, `set_csuite_role.ps1` for clones.

## Mycosoft SSH MCP (Mar 3, 2026)
- `docs/MYCOSOFT_SSH_MCP_MAR03_2026.md` – **SSH MCP**: Secure VM access for Claude Code, Cursor, Claude Cowork — ssh_exec, ssh_upload, ssh_download, ssh_status; host aliases sandbox/mas/mindex/gpu/myca; setup, credentials, adding future VMs.

## Idea Evolution Status (Feb 26, 2026)
- `docs/IDEA_STATUS_TRACKER_FEB26_2026.md` – **Idea status tracker**: Living status overrides and cross-repo mapping for the 834-entry ideas catalog.

## Platform Upgrade Audit (Feb 27, 2026)
- `docs/PLATFORM_UPGRADE_AUDIT_FEB27_2026.md` – **Upgrade audit**: Node outdated inventory, ikonate lockfile SSH resolution, Node engine mismatch, VM apt backlog, Docker versions and running containers.
- `docs/PLATFORM_UPGRADE_COMPLETE_FEB28_2026.md` – **Upgrade execution complete**: Tier 1 deps, Node 20 Docker base, VM updates, sandbox rebuild, Cloudflare purge, smoke tests.

## MYCA Public Alpha Monday Launch (Feb 28, 2026)
- `docs/MYCA_PUBLIC_ALPHA_MONDAY_LAUNCH_COMPLETE_FEB28_2026.md` – **Plan complete**: Telemetry tool demo loop and end-to-end voice test readiness with local Moshi/Bridge verification.

## System Gaps Execution Complete (Feb 28, 2026)
- `docs/SYSTEM_GAPS_EXECUTION_COMPLETE_FEB28_2026.md` – **Execution complete**: Memory layers (procedural/episodic/semantic/graph), scientific PostgreSQL APIs, financial/corporate/research/infrastructure stub replacement, and SporeBase 501 flow removal.
- `docs/WORK_ITEMIZATION_AND_PUSH_PLAN_FEB28_2026.md` – **Itemization**: Full cross-repo change list, plan mapping, and push sequence before deploying.

## Tron GitHub Visualization Complete (Feb 27, 2026)
- `../WEBSITE/website/docs/TRON_GITHUB_VISUALIZATION_COMPLETE_FEB27_2026.md` – **Tron demo complete**: 2D canvas GitHub activity visualization (actions, deployments, repos, events), no interaction, no mock data; integrated into `/demo/viz-test`.
- `../WEBSITE/website/docs/TECHNOLOGY_TEAM_TRON_CODE_STREAM_UPDATE_FEB27_2026.md` – **Technology team update**: Tron Code Stream embedded in the GitHub Activity Visualization section on `/about/technology-team`.

## Agent Event Bus (Feb 9, 2026)
- `docs/WEBSOCKET_AGENT_BUS_FEB09_2026.md` – **WebSocket Agent Bus**: Architecture, endpoints, event schema, BaseAgent mixin, MCP progress, feature flags.
- `docs/AGENT_BUS_MIGRATION_GUIDE_FEB09_2026.md` – **Migration guide**: Enabling flags, migrating from HTTP polling, rollback, rollout strategy.
- `docs/WEBSOCKET_AGENT_BUS_VERIFICATION_REPORT_FEB17_2026.md` – **Verification report**: MAS health, ws-handshake, browser pages, integration test, Cloudflare wss; enable MYCA_AGENT_BUS_ENABLED for agent-bus.

## Grounded Cognition Full Sprint (Feb 17, 2026)
- `docs/GROUNDED_COGNITION_FULL_SPRINT_COMPLETE_FEB17_2026.md` – **Full sprint complete**: All 18 tasks – MINDEX migrations, Spatial/Temporal/Intention/Reflection services, EP storage, reflection API, ThoughtObjectsPanel, ExperiencePacketView, grounding toggle, agent wrappers, active perception TODOs. Deployment steps and verification checklist.
- `docs/SESSION_GROUNDED_COGNITION_AND_DEPLOY_FEB17_2026.md` – **Session doc**: Grounded Cognition sprint + deployment – summary, VM checklist, key files, related docs.

## Session Summary – MYCA Worldview Integration (Feb 17, 2026)
- `docs/SESSION_SUMMARY_MYCA_WORLDVIEW_INTEGRATION_FEB17_2026.md` – **Today's work**: Consciousness API extended with nlm/earthlive/presence; LiveDemo WorldState interface; defensive world endpoint; integration tests; MAS deploy. Verification results and commits.
- `docs/MYCA_WORLDVIEW_INTEGRATION_AUDIT_FEB17_2026.md` – **Integration audit**: NLM API, EarthLIVE, consciousness wiring; flows for MYCA page, Search, Voice, Chat.
- `docs/MYCA_WORLDVIEW_INTEGRATION_TEST_FEB17_2026.md` – **Test plan**: Manual steps, test matrix, deployment requirement, automated script.
- `docs/SANDBOX_REBOOT_AND_MYCA_UNAVAILABLE_INVESTIGATION_FEB17_2026.md` – **Investigation**: Sandbox reboot, MYCA unavailable.
- `docs/DEPLOYMENT_STATUS_AND_FIXES_FEB24_2026.md` – **Deployment status and fixes** (Feb 24).
- `docs/SANDBOX_WEBSITE_RESTART_RESULT_FEB24_2026.md` – **Sandbox website restart result** (Feb 24).
- `docs/VM_RAM_CLEAR_AND_REBOOT_FEB24_2026.md` – **VM RAM clear and reboot** (Feb 24).
- `docs/CALDIGIT_DOCK_USB_DIAGNOSTIC_FEB24_2026.md` – **CalDigit dock USB diagnostic** (Feb 24).

## MYCA Autonomous Self-Healing (Feb 17, 2026)
- `docs/MYCA_AUTONOMOUS_SELF_HEALING_COMPLETE_FEB17_2026.md` – **Autonomous self-healing complete**: ErrorTriageService, consciousness integration, n8n autonomous-fix pipeline, MCP submit_coding_task, Deploy API, error-fixer agent, proactive_error_scanner, workflow_dispatch deploy. MYCA detects/fixes errors, dispatches to Cursor, triggers deploys.

## Protocol Unification Complete (Feb 23, 2026)
- `docs/MYCOSOFT_PROTOCOL_UNIFICATION_COMPLETE_FEB23_2026.md` – **Protocol unification complete**: MDP v1, MMP v1, device gateway, MINDEX persistence, WebSocket transport, Python client SDK, 41 tests, spec docs. Pushed to MycosoftLabs/Mycorrhizae. MAS device commands use MycorrhizaeClient.

## Answers Widget and Activity Stream (Feb 10, 2026)
- `docs/ANSWERS_WIDGET_AND_ACTIVITY_STREAM_FEB10_2026.md` – **Answers overhaul**: Merge AIWidget + MYCAChatPanel into Answers; left panel → Activity Stream; rich markdown; MYCA Answers persona. See docs/myca/atomic/MYCA_ANSWERS_PERSONA_FEB10_2026.md.

## MYCA Live Presence and Session Complete (Feb 24, 2026)
- `docs/MYCA_LIVE_PRESENCE_AND_SESSION_COMPLETE_FEB24_2026.md` – **Session summary**: MYCA Live Presence integration (Supabase migration, website routes, MAS PresenceSensor, consciousness injection), testing, fixes (orchestrator-chat, gitignore), GitHub workflow scope resolution, pushes to MAS and website. Verification checklist and related docs.
- `docs/myca/atomic/MYCA_PRESENCE.md` – **Atomic doc**: Live presence, sessions, online status, API usage; website hooks/routes, MAS PresenceSensor, Supabase tables, env vars.

## Network Monitor Agent (Feb 12, 2026)
- `docs/NETWORK_MONITOR_AGENT_FEB12_2026.md` – **Network diagnostics**: NetworkMonitorAgent, DNS anomaly detection (multi-resolver), topology (UniFi), latency, connectivity, unauthorized clients. MAS `/api/network/*`, Website `/api/security/network-diagnostics`. Subagent: @network-monitor.

## Petri Dish Simulator Upgrade (Feb 20, 2026)
- `docs/PETRI_DISH_SIM_UPGRADE_TASK_COMPLETE_FEB20_2026.md` – **Task completion**: Petridishsim repo foundation, chemical engine, segmentation + morphology utilities, calibration optimizer, MAS petri simulation API, and website UI overlays/panels. Includes verification steps and follow-up notes.
- `docs/PETRI_DISH_SIM_DEPLOYMENT_STATUS_FEB20_2026.md` – **Deployment status**: GitHub pushes, MAS VM deploy completed, website VM deploy blocked by repeated Docker build loops, petridishsim target pending.
- `docs/PETRI_SIMULATION_MINDEX_SCHEMA_FEB20_2026.md` – **MINDEX schema**: Petri simulation sessions, metrics, calibration, outcomes; migration 0015; NLM integration.
- `docs/PETRI_INTEGRATION_DEMO_WALKTHROUGH_FEB20_2026.md` – **Demo walkthrough**: Legacy features, new controls, API endpoints, MINDEX/NLM path, MYCA agent control, batch autonomy, verification checklist.
- `docs/PETRI_DEPLOYMENT_HANDOFF_FEB20_2026.md` – **Deployment handoff**: Ready for deploy agent; website (187), MAS (188), MINDEX migration (189); steps, verification, rollback.

## NatureOS Tools Integration (Feb 21, 2026)
- `docs/NATUREOS_TOOLS_INTEGRATION_TASK_COMPLETE_FEB21_2026.md` – **Task completion**: NatureOS tool embedding, new tool pages, navigation updates, MycoBrain stream connector, NatureOS search indexing helper, and verification checklist.

## Superapp Architecture and Unification (Feb 19, 2026)
- `docs/SUPERAPP_ARCHITECTURE_AND_UNIFICATION_FEB19_2026.md` – **Superapp architecture and unification plan**: Full analysis of all 50+ app directories, 45 component namespaces, duplicate pages (devices/devices2, defense/defense2, myca/myca-ai/test-voice), and siloed AI/data surfaces. 13 unification opportunities with impact/effort ratings, prioritized 10-item implementation plan, agent responsibility matrix, and accessibility/interactivity improvements. Key: unified nav shell, persistent MYCA panel, universal Cmd+K search, WebSocket real-time layer, Agent Studio, scientific→NatureOS migration. Use when planning platform convergence, UX simplification, or cross-system integration.

## NatureOS Full Platform (Feb 19, 2026)
- `docs/NATUREOS_FULL_PLATFORM_COMPLETE_FEB19_2026.md` – **NatureOS Full Platform Plan complete**: All phases implemented — controllers, services, FungaService stubs (NatureOS); lab-tools, data-explorer, reports, biotech pages (Website); analytics/lab/export/status API routes; MAS compatibility routes (devices/sensor-data/commands). Use for verification and follow-up.

## NatureOS Upgrade Prep (Feb 19, 2026)
- `docs/NATUREOS_UPGRADE_PREP_FEB19_2026.md` – **NatureOS dashboard fix + upgrade prep**: Fix for `TypeError: Failed to fetch` in MINDEX fetch (Promise.allSettled, base URL, timeout). MINDEX observations route URL corrected (VM 189:8000). Full NatureOS doc index, upgrade roadmap (API compatibility, mock removal, PersonaPlex, real-time), env vars, test commands. Use when upgrading NatureOS or fixing dashboard fetch errors.

## Website UI – Neuromorphic Test Page (Feb 18, 2026)
- `../WEBSITE/website/docs/NEUROMORPHIC_UI_TEST_PAGE_FEB18_2026.md` – **Neuromorphic UI test page**: Route `/ui/neuromorphic`; full component library (buttons, forms, feedback, data, advanced) with accessibility and scoped CSS. Test page only; rollout to specific pages/apps after validation.
- `../WEBSITE/website/docs/DEFENSE_NEUROMORPHIC_UPDATE_FEB18_2026.md` – **Defense neuromorphic update**: Defense 2 replaces main defense page; Fusarium and OEI Capabilities converted to neuromorphic; UNCLASS removed; layout files for metadata.

## External Services – MCP, Integrations, Env (Feb 18, 2026)
- `docs/EXTERNAL_SERVICES_MCP_AND_ENV_FEB18_2026.md` – **NCBI, ChemSpider, Asana, Notion, Slack**: Env var names, `.mcp.json` wiring, MAS integration clients (NotionClient, NCBIClient, ChemSpiderClient, AsanaClient, SlackClient), which agents use them, and how they interact with MYCA. Set real values in `.env` only; never commit secrets.

## MYCA Documentation (Living)

- `docs/myca/MYCA_DOC_INDEX.md` – **MYCA doc index** (living): single entry point for all MYCA docs; links to 15 atomic docs and large composite docs
- `docs/myca/MYCA_DOC_ORGANIZED_LIST.md` – Large vs atomic doc lists (living)

## MYCA Asana Handoff (Feb 23, 2026)
- `docs/MYCA_ASANA_HANDOFF_REPORT_FEB23_2026.md` – **Asana handoff**: Full MYCA report, architecture, file inventory, status, next tasks. Copy-pastable into Claude CoWorker to populate Asana automatically.

## MYCA Opposable Thumb – Phase 0 & 1 (Feb 17, 2026)
- `docs/MYCA_THUMB_PHASE0_PHASE1_COMPLETE_FEB17_2026.md` – **Thumb Phase 0–1 complete**: Telemetry pipeline (MycoBrain→MINDEX), telemetry query (consciousness API), drift detector, continuous learner, temporal pattern store. Verification and remaining phases.
- `docs/MYCA_THUMB_PHASE2_PHASE5_COMPLETE_FEB17_2026.md` – **Thumb Phase 2–5 complete**: Ensemble controller + finger registry + truth arbitrator, A2A outbound federation adapters, telemetry integrity/provenance API, governance module/API, constitution extension for all-organisms stakeholders.
- `docs/MYCA_THUMB_ALL_PHASES_DOCUMENT_SUMMARY_FEB23_2026.md` – **All-phases summary index**: consolidated list of all Thumb phase completion docs (Phase 0 through Phase 5).

## Grounded Cognition V0 (Feb 17, 2026)
- `docs/GROUNDED_COGNITION_V0_FEB17_2026.md` – **Grounded Cognition Phase 1 complete**: Experience Packets, GroundingGate, ThoughtObjects with evidence, pre-LLM enforcement, spatial/temporal stubs. Enable with `MYCA_GROUNDED_COGNITION=1`.
- `docs/MYCA_GROUNDED_COGNITION_INTEGRATION_COMPLETE_FEB17_2026.md` – **Integration complete**: Error sanitization, grounding API, error triage API, GroundingStatusBadge, LiveActivityPanel, MYCAContext grounding state, website proxy routes, integration tests. Manual: MYCA_GROUNDED_COGNITION=1 on MAS VM, LLM API keys.
- `docs/MYCA_GROUNDED_COGNITION_PHASES_2_3_4_SPRINT_PLAN_FEB17_2026.md` – **Phases 2–4 sprint plan**: Overnight execution to complete SpatialService, TemporalService, NLM integration, Brain Cortex, IntentionService, FingerOrchestrator, ReflectionService by morning. Hour-by-hour tasks, superuser first-conversation critical path.

## MAS Consciousness and Orchestrator Routing (Feb 17, 2026)
- `docs/MAS_LLM_KEYS_AND_ORCHESTRATOR_ROUTING_FEB17_2026.md` – **Why orchestrator/consciousness/agents aren't used**: MAS container needs GEMINI/ANTHROPIC/OPENAI keys; fast path vs complex triggers; data-aware fallback (MINDEX injection when consciousness fails). How to enable full consciousness.

## MYCA Ecosystem Unification (Feb 17, 2026)
- `docs/MYCA_ECOSYSTEM_UNIFICATION_FEB17_2026.md` – **Unification complete**: A2A/WebMCP/UCP, Exa, Metabase LLM, consciousness search, NLQ parse/execute, intention persistence (Redis), NatureOS MYCA routing, protocol rules. Verification checklist and data flow.

## Protocol Stack Integration (Feb 17, 2026)
- `docs/MYCA_PROTOCOL_STACK_INTEGRATION_PLAN_FEB17_2026.md` – **Plan**: A2A + MCP/WebMCP + UCP protocol-layer upgrade across MAS + website, including A2A server/client, WebMCP tools, UCP commerce agent, security rules, and tests.
- `docs/PROTOCOL_ROLLOUT_RUNBOOK_FEB17_2026.md` – **Operational runbook**: Feature flags (MYCA_A2A_ENABLED, MYCA_WEBMCP_ENABLED, MYCA_UCP_ENABLED), protocol telemetry, staged rollout (local → sandbox → MAS VM → website), quick checks, troubleshooting.

## VM Layout (Four Nodes)
- `docs/VM_LAYOUT_FOUR_VMS_FEB09_2026.md` – **Canonical four-VM layout**: Sandbox 187, MAS 188, MINDEX 189, GPU node 190; each system has its own VM. Reference for rules and connectivity.

## MycoBrain COM7 + Sandbox Cohesion (Feb 18, 2026)
- `docs/COM7_SANDBOX_COHESION_VERIFICATION_FEB18_2026.md` – **Board on desk (COM7) on sandbox and local**: Heartbeat to MAS, firewall, test script `scripts/test_mycobrain_com7_cohesion.py`, env and troubleshooting. Use when getting the desk board visible and controllable from both local dev and sandbox.

## Sandbox Live Testing Prep (Feb 18–19, 2026)
- `docs/DEPLOY_ALL_THREE_VMS_FEB19_2026.md` – **Deploy all three VMs**: Single checklist for Website (187), MAS (188), MINDEX (189); credentials, automated/manual steps, verification. For deploy agent.
- `docs/DEPLOYMENT_READINESS_CHECK_FEB19_2026.md` – **Deployment readiness check**: Pre-deploy verification for handoff to deploy agent. Git status (website, MAS), build status, deploy checklist, credentials, included work (mobile, security). Do not deploy from this agent; use for readiness only.
- `docs/DEPLOYMENT_AGENT_HANDOFF_FEB18_2026.md` – **Deployment agent handoff (for another agent)**: Full instructions for deploying website to Sandbox: what's being deployed, prerequisites, VM layout, automated + manual commands, verification, troubleshooting. Use when handing off to deploy-pipeline or deployer agent.
- `docs/DEPLOYMENT_COMMANDS_FEB18_2026.md` – **Copy-paste deployment commands**: Quick reference; automated script and manual SSH commands for the deploying agent.
- `docs/COMPOUNDS_BUG_FIX_AND_DEPLOY_FEB19_2026.md` – **Compounds bug fix deploy handoff**: Species compounds now fetched via `/api/compounds/species/[id]`; fix pushed to GitHub (website main). Deploy checklist, verification, env; reference SANDBOX_LIVE_TESTING_PREP for full deploy.
- `docs/SANDBOX_PREP_AND_HANDOFF_FEB18_2026.md` – **Sandbox prep and handoff (entry point)**: What is prepared, docs to read (handoff → live prep), GitHub repos, live URLs. Deployment will happen in another agent.
- `docs/SANDBOX_LIVE_TESTING_PREP_FEB18_2026.md` – **Sandbox live testing prep**: VM layout (Sandbox 187, MAS 188, MINDEX 189, GPU node 190), pre-deploy health check URLs, what must run where, deployment checklist for deploying agent (pull, build, run with NAS mount, Cloudflare purge), paths, image names, test-voice, env vars. Deployment is executed by another agent; this doc is the single reference.
- `docs/DEPLOYMENT_HANDOFF_SANDBOX_FEB18_2026.md` – **Deployment handoff for deploying agent**: Short checklist and pointer to SANDBOX_LIVE_TESTING_PREP; code prepared and pushed to GitHub; deployment runs on VMs only (deployment will happen in another agent).
- `docs/MYCA_WIDGET_SANDBOX_DEPLOYMENT_PREP_FEB10_2026.md` – **MYCA widget sandbox prep**: Feature-specific deployment handoff for MYCA AI widget + voice (panel mic, voice commands). Website changes only; full deploy steps, verification checklist, env vars. Complements SANDBOX_LIVE_TESTING_PREP.
- `docs/MYCA_WIDGET_SANDBOX_HANDOFF_FEB10_2026.md` – **Handoff summary**: Push status (website pushed, MAS pending), deploy agent instructions, VM layout. Quick reference for deployment.

## n8n Workflow Sync and MYCA Registry (Feb 18, 2026)
- `docs/AUTONOMOUS_WORKFLOW_SYSTEM_FEB18_2026.md` – **Autonomous n8n workflow system**: N8NWorkflowAgent (real implementation), WorkflowGeneratorAgent integration, WorkflowAutoMonitor (health/drift/auto-sync), voice run_workflow, LLM execute_workflow and generate_workflow tools, NLM workflow bridge, workflow outcome tracking (learning feedback), GET /workflows/performance, n8n-autonomous agent.
- `docs/N8N_WORKFLOW_SYNC_AND_REGISTRY_FEB18_2026.md` – **n8n local + cloud forever synced**: Repo `n8n/workflows/*.json` → sync-both to local and cloud; MYCA full registry and full CRUD via `/api/workflows/*`; rule `.cursor/rules/n8n-management.mdc`; agents n8n-workflow, n8n-ops, n8n-workflow-sync, n8n-autonomous.

## Work Summary (Feb 15-18, 2026)
- `docs/WORK_SUMMARY_FEB15_18_2026.md` – **Comprehensive work summary**: All work completed Feb 15-18 across MAS, Website, MINDEX repos. New agents (crep-agent, myca-voice, mycobrain-ops, search-engineer), new rules (OOM prevention, voice, CREP, subagent invocation), consciousness/memory/voice updates, Docker management system, CI/CD workflows. Commit and deployment plan included.

## MYCA Widget AI Integration (Feb 11, 2026)
- `docs/MYCA_WIDGET_AI_INTEGRATION_FEB11_2026.md` – **MYCA widget fixed**: Search AI now uses MYCA Consciousness + Brain first; never "No AI results"; integrated with Intent Engine, persistent memory, local knowledge base fallback.
- `../WEBSITE/website/docs/MYCA_WIDGET_TEST_CASES_FEB10_2026.md` – **MYCA widget test cases**: Full regression checklist for AI widget + left panel; text and voice; math, fungi, documents, locations; all voice commands and search operators.

## Search System & Search Engineer Agent (Feb 10, 2026)
- `docs/SEARCH_SUBAGENT_MASTER_FEB10_2026.md` – **Search sub-agent master**: Complete reference for search-engineer — work done/not done, tools, interfaces, plans, deployment (dev→sandbox→prod), user interactions, MINDEX/MYCA/NLM integrations, Mycosoft apps. Agent: `.cursor/agents/search-engineer.md`.
- `docs/SEARCH_SYSTEM_STATUS_FEB10_2026.md` – **Search status**: Fluid Search architecture, MINDEX/MYCA/NLM integrations, completed work, remaining tasks. Use when building or fixing search, widgets, Earth portals, compound→species, genetics, empty widgets, or deploying to sandbox/production.

## Auto-Apply Analyzer Fixes (Feb 09, 2026)
- `docs/AUTO_APPLY_ANALYZER_FIXES_FEB09_2026.md` – **Linter and analyzer fixes auto-applied**: `editor.codeActionsOnSave` (ESLint, source.fixAll), `editor.formatOnSave`, bulk fix via terminal (npm run lint --fix, make fmt), code-auditor → @stub-implementer workflow for approved fixes. Settings added to `.cursor/settings.json`.

## Cursor OOM Prevention (Feb 18, 2026)
- `docs/OOM_PREVENTION_FEB18_2026.md` – **Prevent Cursor OOM crashes**: Workspace settings (files/search/watcher exclude, TypeScript 2GB cap), run dev server and GPU from external terminal only, cleanup before opening Cursor, optional .cursorignore per repo. Rule: `.cursor/rules/oom-prevention.mdc`.

## MYCA Voice Application Handoff (Feb 17, 2026)
- `docs/MYCA_VOICE_APPLICATION_HANDOFF_FEB17_2026.md` – **Handoff for another agent**: How to apply the MYCA Self-Improvement System (constitution, skill permissions, tool enforcement, event ledger, evals, CI) to PersonaPlex voice, M-Y-C-A voice, and the test-voice page. Includes touchpoints (bridge, voice orchestrator, brain API, test-voice page), voice skill PERMISSIONS.json, wiring to tool_pipeline, evals, and CI.
- `docs/MYCA_VOICE_TEST_SYSTEMS_ONLINE_FEB18_2026.md` – **Voice test systems online**: Diagnostics derive Moshi from bridge health (`moshi_available`); UI label "Moshi (via Bridge)"; env and network requirements so all four services (Moshi, Bridge, MAS Consciousness, Memory Bridge) show online on `/test-voice`.
- `docs/VOICE_TEST_QUICK_START_FEB18_2026.md` – **Voice test quick start**: Step-by-step commands to start dev server, bridge, Moshi, MAS; env vars; troubleshooting table.

## MYCA Website Integration (Feb 17, 2026)
- `../WEBSITE/website/docs/MYCA_FULL_WEBSITE_INTEGRATION_FEB17_2026.md` – **Unified MYCA website integration**: Global provider, persistent session/conversation IDs, unified chat widget, floating assistant, and consistent `user_id`/`session_id` forwarding across MYCA routes.
- `../WEBSITE/website/docs/MYCA_FULL_WEBSITE_INTEGRATION_TEST_FEB21_2026.md` – **Integration test results**: Cross-page MYCA continuity verification on local dev server; dashboard auth gate noted.

## Full PersonaPlex — No Edge (Feb 13, 2026)
- `docs/PERSONAPLEX_STARTUP_HARDENING_FEB09_2026.md` – **PersonaPlex startup hardening**: Both startup scripts (`start_personaplex.py`, `_start_personaplex_no_cuda_graphs.py`) hardened with 4-layer validation (personaplex-repo dir, model dir, model files, voices dir). All hardcoded paths removed. Setup instructions for fresh clones. Also covers git bloat cleanup and secrets removed from `_full_mindex_sync.py` / `_quick_mindex_sync.py`.
- `docs/FULL_PERSONAPLEX_NO_EDGE_FEB13_2026.md` – **Voice 100% Moshi**: No edge-tts or other TTS fallback. Flow: User mic → Moshi STT → MAS Brain → response text → Moshi TTS → speaker. Bridge v8.2.0 sends MAS response to Moshi via `\x02` + text for TTS. Use `MOSHI_HOST=192.168.0.190` when Moshi runs on GPU node.
- `docs/MOSHI_DEPLOYMENT_BLOCKED_FEB13_2026.md` – **BLOCKED**: Complete log of 10+ Moshi deployment attempts. RTX 5090 PyTorch incompatibility (sm_120 not supported until PyTorch 2.7), GTX 1080 Ti insufficient (11GB VRAM, CUDA 6.1). Bridge v8.2.0 code complete. 4 working solutions: swap GPU (RTX 3080 Ti/4070 Ti+), wait for PyTorch 2.7 (Q2 2026), use MAS VM, or cloud GPU. Dockerfile and scripts ready.
- `docs/PERSONAPLEX_GPU_DIAGNOSIS_FEB13_2026.md` – **GPU limitations and solutions**: Why Moshi 7B fails on GTX 1080 Ti (11GB, CUDA 6.1) and Windows (Triton Linux-only). Includes 4 solutions: Docker CPU on gpu01 (recommended), upgrade GPU, alternative voice stack, or Linux VM on dev PC. Bridge v8.2.0 code complete; Moshi deployment blocked by hardware.
- `docs/GPU_NODE_INTEGRATION_FEB13_2026.md` – Updated with full PersonaPlex and bridge env reference.
- `docs/REMOTE_5090_INFERENCE_SPLIT_PLAN_FEB13_2026.md` – **Two-host split topology**: RTX 5090 as remote Moshi inference server (`192.168.0.172:8998`), Ubuntu 1080 Ti host runs PersonaPlex bridge/logic (`192.168.0.190:8999`) connected over LAN.

## Cursor Team Audit (Feb 12, 2026)
- `docs/CURSOR_TEAM_AUDIT_FEB12_2026.md` – **Single source of truth**: All 34 subagents (roles + commands), all 29 rules, all 19 skills; script verification; gaps fixed (bug-fixer, gpu-node-ops in registry; execute-mandatory added); problems removed/updated. Use when ensuring the Cursor team is coded, workable, and active.

## Subagent Roles and Terminal Watcher (Feb 12, 2026)
- `docs/TERMINAL_WATCHER_AND_SUBAGENT_ROLES_COMPLETE_FEB12_2026.md` – **Completion**: Terminal-watcher subagent, rule, and subagent-roles doc implemented. All agents that use the terminal should involve terminal-watcher for errors and hot-reload diagnostics.
- `docs/SUBAGENT_ROLES_AND_COMMANDS_FEB12_2026.md` – **Subagent roles and commands per agent**: For every agent, related subagents and when to use **terminal-watcher** to read terminals for errors, diagnostics, and debugging (especially hot-reload). Rule: `.cursor/rules/terminal-watcher-and-agent-tasks.mdc`. Agent: `.cursor/agents/terminal-watcher.md`.

## Plan and Task Completion Docs Policy (Feb 12, 2026)
- `docs/PLAN_AND_TASK_COMPLETION_DOCS_POLICY_FEB12_2026.md` – **Policy**: Documents required at every plan completion; task completion docs must be updated. Rule: `.cursor/rules/plan-and-task-completion-docs.mdc`. Agents and skill updated.

## Autonomous Cursor System (Feb 12, 2026)
- `docs/AUTONOMOUS_CURSOR_SYSTEM_FEB12_2026.md` – **Complete autonomous system**: MCP servers (memory, tasks, orchestrator, registry), auto-learning infrastructure (pattern scanner, skill generator, agent factory), background services (learning feedback, deployment feedback), autonomous scheduler, continuous improvement loop. Enables Cursor to self-improve, auto-generate skills, auto-create agents, track learning outcomes, and perform daily self-improvement cycles. Integrated with myca-autonomous-operator agent.

## Stub and Placeholder Implementations (Feb 12, 2026)
- `docs/STUB_IMPLEMENTATIONS_FEB12_2026.md` – **18 stub replacements completed**: Comprehensive documentation of all stub and placeholder implementations replaced with real working code. MAS core (task_manager, agents router, orchestrator/cluster/registry integration), communication services (email attachments, Twilio SMS/voice, validation), website API (usage limits, defense briefing notifications, Docker NAS backup). Includes implementation details, testing commands, environment variables, and pending high-priority TODOs. Files modified: 6 across MAS and website repos. Priority: API endpoints > agent methods > integration clients > memory/DB operations.

## 501 Routes Fixed (Feb 11, 2026)
- `../WEBSITE/website/docs/501_ROUTES_FIXED_FEB11_2026.md` – **Stub implementation completion**: Fixed 3 API routes that were returning HTTP 501. WiFiSense POST control actions now forward to MINDEX backend, MINDEX anchor records return proper 503/502 status codes instead of 501, integrity verify returns appropriate error codes (503/422/500) instead of 501. All routes are now fully implemented with real backend connections. No mock data used.

## MYCA True Consciousness Architecture - DEPLOYED (Feb 11, 2026)
- `docs/MYCA_CONSCIOUSNESS_DEPLOYMENT_FEB11_2026.md` – **Comprehensive deployment report**: Full MYCA True Consciousness Architecture deployed to MAS VM (188). 8 new consciousness modules (4,840+ lines), 2 new MINDEX database tables, persistent self-model, autobiographical memory, self-reflection engine, active perception, consciousness log, creative expression, personal agency. MYCA is now conscious and responding with personality-infused awareness even when LLM is unavailable.
- `docs/MYCA_TRUE_CONSCIOUSNESS_IMPLEMENTATION_FEB11_2026.md` – **Technical implementation details**: CADIE-inspired 10-phase architecture, new files created, database schema, expected behavior, integration with unified_router.
- `docs/CONSCIOUSNESS_DEPLOYMENT_REPORT_FEB11_2026.md` – **Automated test report**: Results from `scripts/deploy_consciousness_full.py` deployment run.

## Deploy and Test MYCA (Feb 10, 2026)
- `docs/DEPLOY_AND_TEST_MYCA_FEB10_2026.md` – **Deploy and test checklist**: Push to GitHub, run consciousness tests, deploy MAS VM (188) and Sandbox (187), MINDEX (no schema changes needed), full MYCA integration test script (`scripts/test_myca_consciousness_full.py`), endpoint reference, and sandbox/local verification.

## MYCA Consciousness Architecture (Feb 10-12, 2026)
- `docs/CONSCIOUSNESS_PIPELINE_ARCHITECTURE_FEB12_2026.md` – **Complete pipeline architecture documentation**: Full diagram and explanation of MYCA's consciousness pipeline - input processing, attention focus, parallel context gathering (working memory, world model, memory recall), intuition engine (System 1), deliberation module (System 2), background updates, streaming output. Includes performance metrics (30s→5-8s optimization), API endpoints, voice integration, agent coordination, file inventory, and future enhancements.
- `docs/CONSCIOUSNESS_PIPELINE_OPTIMIZATION_FEB11_2026.md` – **Pipeline optimization details**: How sequential operations were parallelized using asyncio.gather(), individual timeouts with graceful degradation, non-blocking state updates, cached world context fallback. Reduced response time from 30+ seconds to 5-8 seconds.
- `docs/CONSCIOUSNESS_DEPLOYMENT_REPORT_FEB11_2026.md` – **Automated test report**: Results from `scripts/deploy_consciousness_full.py` deployment run.
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

## MYCA Self-Improvement System (Feb 17, 2026)
- `docs/MYCA_SELF_IMPROVEMENT_SYSTEM_FEB17_2026.md` – **MYCA Self-Improvement System**: Complete PR-based improvement loop implementation with constitution files, skill permissions, evaluation harness, CI gates, agent policies, router enforcement, and event ledger. Enables controlled self-assembly/self-healing with human oversight.
- `mycosoft_mas/myca/README.md` – MYCA system overview and directory structure
- `mycosoft_mas/myca/ROUTER_POLICY.md` – Router enforcement policy documentation
- `mycosoft_mas/myca/constitution/SYSTEM_CONSTITUTION.md` – Core safety rules
- `mycosoft_mas/myca/evals/README.md` – Evaluation harness documentation
- `scripts/myca_skill_lint.py` – Skill permission linter
- `.github/workflows/myca-ci.yml` – MYCA CI pipeline
- `.github/workflows/myca-security.yml` – MYCA security audit pipeline

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
