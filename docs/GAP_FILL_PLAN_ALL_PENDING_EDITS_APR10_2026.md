# GAP Fill Plan - All Pending Edits - APR10_2026

Date: 2026-04-10  
Status: In Progress  
Scope: Cross-repo pending edits after Jetson -> MINDEX -> NatureOS/FUSARIUM integration rollout

## 1) Deployment/verification status from this run

- MINDEX commit `63c8879` pushed to `main` and deployed to VM `192.168.0.189`.
- MAS commit `9add3b526` pushed to `main` and deployed/restarted on VM `192.168.0.188`.
- MAS service on `8001` is active (`/live` returns 200).
- MINDEX `/api/mindex/internal/state/live` still returns 404 in production runtime and is a priority blocker.

## 2) All current pending edits snapshot (by repo)

### MAS (`C:/Users/admin2/Desktop/MYCOSOFT/CODE/MAS/mycosoft-mas`)

Tracked modified:
- `.cursor/rules/dev-server-3010.mdc`
- `mycosoft_mas/core/myca_main.py`
- `mycosoft_mas/core/routers/avani_router.py`
- `mycosoft_mas/core/routers/crep_command_api.py`
- `mycosoft_mas/core/routers/crep_stream.py`
- `mycosoft_mas/core/routers/device_registry_api.py`
- `mycosoft_mas/core/routers/fusarium_api.py`
- `mycosoft_mas/core/routers/platform_api.py`
- `mycosoft_mas/core/routers/search_orchestrator_api.py`
- `mycosoft_mas/core/routers/security_audit_api.py`
- `mycosoft_mas/core/routers/voice_command_api.py`
- `mycosoft_mas/core/routers/voice_orchestrator_api.py`

Untracked (non-cache):
- `.cursor/agents/maritime-nlm.md`
- `.cursor/agents/taco-integration.md`
- `.cursor/rules/taco-integration.mdc`
- `_jetson_mqtt.env`
- `_pve_tools_out.txt`
- `_qm101.txt`
- `docs/DEEP_AGENTS_V05_CROSS_SYSTEM_HOOKS_APR09_2026.md`
- `docs/DEEP_AGENTS_V05_FOUNDATION_IMPLEMENTATION_APR09_2026.md`
- `docs/DEEP_AGENTS_V05_INTEGRATION_PLAN.md`
- `docs/DEEP_AGENTS_V05_MULTI_REPO_SYSTEM_INTEGRATION_APR09_2026.md`
- `docs/FUSARIUM_ADDITIVE_MINDEX_DEFENSE_PLANE_COMPLETE_APR10_2026.md`
- `docs/FUSARIUM_FULLSCREEN_OPERATOR_APP_EXECUTION_PLAN_APR10_2026.md`
- `docs/FUSARIUM_FULL_ARCHITECTURE_IMPLEMENTATION_COMPLETE_APR09_2026.md`
- `docs/FUSARIUM_OPERATOR_APPLICATION_AND_CROSS_SYSTEM_INTEGRATION_COMPLETE_APR09_2026.md`
- `docs/FUSARIUM_PLANS_USED_SYSTEMS_GAPS_AND_INTEGRATIONS_APR10_2026.md`
- `docs/MQTT_LAN_WSS_DEPLOYMENT_AND_JETSON_HANDOFF_APR08_2026.md`
- `docs/TACO_CUI_HANDLING_APR08_2026.md`
- `docs/TACO_CURSOR_IMPLEMENTATION_PLAN.md`
- `docs/TACO_NIST_800_171_MAPPING_APR08_2026.md`
- `docs/zeetachec_mycosoft_taco_plan.md`
- `infra/csuite/paramiko_ssh_dual.py`
- `mycosoft_mas/agents/clusters/taco/`
- `mycosoft_mas/agents/compliance/`
- `mycosoft_mas/core/routers/agent_protocol_api.py`
- `mycosoft_mas/core/routers/fusarium_platform_api.py`
- `mycosoft_mas/deep_agents/`
- `mycosoft_mas/fusarium/`
- `mycosoft_mas/integrations/zeetachec_client.py`
- `mycosoft_mas/protocols/mdp_v2.py`
- `scripts/bootstrap_jetson_mqtt_env.py`
- `scripts/bootstrap_mqtt_broker_guest.sh`
- `scripts/deploy_mqtt_docker_via_pve_qga.py`
- `scripts/deploy_mqtt_status_page_sandbox_apr08_2026.py`
- `scripts/full_setup_mqtt_vm_from_windows.py`
- `scripts/install_ssh_pubkey_guest.py`
- `scripts/mqtt_jetson_e2e_roundtrip_apr08_2026.py`
- `scripts/mqtt_smoke_via_pve_qga.py`
- `scripts/mqtt_tunnel_cloudflare_apply.py`
- `scripts/provision_mqtt_broker_vm_pve90.py`
- `scripts/proxmox_disk_enable_ssh_and_qga.sh`
- `scripts/remote_setup_mqtt_vm.py`
- `scripts/validate_jetson_mqtt_connectivity_apr08_2026.py`

Untracked cache/artifacts:
- `.poetry-cache/cache/repositories/PyPI/**`

### WEBSITE (`C:/Users/admin2/Desktop/MYCOSOFT/CODE/WEBSITE/website`)

Tracked modified:
- `.env.example`
- `app/about/page.tsx`
- `app/api/devices/network/route.ts`
- `app/api/health/media/route.ts`
- `app/api/myca/activity/route.ts`
- `app/api/myca/query/route.ts`
- `app/api/natureos/activity/route.ts`
- `app/api/natureos/status/route.ts`
- `app/api/search/suggestions/route.ts`
- `app/api/search/unified-v2/route.ts`
- `app/api/security/agents/route.ts`
- `app/api/security/redteam/route.ts`
- `app/defense/fusarium/page.tsx`
- `app/layout.tsx`
- `app/natureos/fusarium/page.tsx`
- `app/search/page.tsx`
- `components/defense/challenge-canvas.tsx`
- `components/defense/cta-snake-canvas.tsx`
- `components/defense/defense-particles.tsx`
- `components/defense/defense-portal-v2.tsx`
- `components/defense/intelligence-waves.tsx`
- `components/devices/hyphae1-details.tsx`
- `components/devices/myconode-details.tsx`
- `components/devices/sporebase-details.tsx`
- `components/effects/connected-dots.tsx`
- `components/effects/particle-gravity.tsx`
- `components/enhanced-search.tsx`
- `components/header.tsx`
- `components/home/hero-search.tsx`
- `components/home/parallax-search.tsx`
- `components/mobile-nav.tsx`
- `components/providers/AppShellProviders.tsx`
- `components/search-section.tsx`
- `components/search/fluid/FluidSearchCanvas.tsx`
- `components/search/mobile/MobileSearchChat.tsx`
- `components/search/use-search.ts`
- `components/ui/alert-dialog.tsx`
- `components/ui/dialog.tsx`
- `components/ui/neuromorphic/NeuSelect.tsx`
- `docs/CLOUDFLARE_ASSETS_VIDEO_CACHE_APR06_2026.md`
- `hooks/use-unified-search.ts`
- `lib/access/routes.ts`
- `lib/asset-video-sources.ts`
- `lib/devices.ts`
- `middleware.ts`
- `next.config.js`
- `package.json`
- `tsconfig.tsbuildinfo`

Untracked:
- `_check_sandbox_docker_status_apr08_2026.py`
- `_check_sandbox_mqtt_status_deploy_apr08_2026.py`
- `_deploy_mqtt_status_sandbox.py`
- `_kill_sandbox_stale_website_builds_apr08_2026.py`
- `_sandbox_reset_builds_and_rebuild_mqtt_status_apr08_2026.py`
- `_start_sandbox_mqtt_status_deploy_apr08_2026.py`
- `app/api/crep/maritime/`
- `app/api/fusarium/catalog/`
- `app/api/fusarium/maritime/`
- `app/api/fusarium/platform/`
- `app/api/fusarium/stream/`
- `app/api/mas/agent-protocol/`
- `app/api/mqtt/`
- `app/api/security/taco-compliance/`
- `app/dashboard/fusarium-maritime/`
- `app/dashboard/fusarium/`
- `app/fusarium/`
- `app/mqtt-status/`
- `components/chunk-load-recovery.tsx`
- `components/fusarium/`
- `hooks/fusarium/`
- `hooks/use-deferred-outside-dismiss.ts`
- `lib/design-system/`
- `lib/fusarium/`
- `lib/mas/deep-agent-events.ts`
- `nul`
- `scripts/restart-dev-external.ps1`
- `tests/search/`

### MINDEX (`C:/Users/admin2/Desktop/MYCOSOFT/CODE/MINDEX/mindex`)

Tracked modified:
- `mindex_api/routers/etl.py`
- `mindex_api/routers/nlm_router.py`
- `mindex_api/routers/observations.py`
- `mindex_api/routers/research.py`
- `mindex_api/routers/unified_search.py`
- `mindex_api/routers/worldview/__init__.py`
- `mindex_api/storage.py`

Untracked:
- `docs/NLM_TRAINING_DATA_SOURCES.md`
- `migrations/0030_maritime_acoustic_schemas.sql`
- `migrations/0031_fusarium_analytics.sql`
- `migrations/0032_fusarium_catalog_training_env.sql`
- `mindex_api/routers/fusarium_analytics.py`
- `mindex_api/routers/fusarium_catalog.py`
- `mindex_api/routers/maritime.py`
- `mindex_api/routers/rag_retrieve.py`
- `mindex_api/routers/taco.py`
- `mindex_api/routers/worldview/maritime.py`
- `mindex_api/utils/deep_agent_events.py`
- `mindex_api/utils/fusarium_training_doc_parser.py`
- `mindex_etl/jobs/bootstrap_fusarium_p0_manifests.py`
- `mindex_etl/jobs/bootstrap_fusarium_training_registry.py`
- `mindex_etl/jobs/sync_maritime_data.py`
- `mindex_etl/sources/navy_oceanographic.py`
- `mindex_etl/sources/noaa_hydrophone.py`
- `mindex_etl/sources/noaa_ocean.py`
- `mindex_etl/sources/zeetachec_ingest.py`
- `pytest_out.txt`
- `pytest_out_cmd.txt`
- `pytest_out_cmd2.txt`

### MycoBrain (`C:/Users/admin2/Desktop/MYCOSOFT/CODE/mycobrain`)

Tracked modified:
- `firmware/MycoBrain_FCI/include/fci_config.h`
- `firmware/MycoBrain_FCI/src/fci_signal.cpp`
- `firmware/MycoBrain_ScienceComms/include/modem_audio.h`

Untracked:
- `MQTT/`
- `deploy/jetson/taco_inference.py`
- `firmware/MycoBrain_FCI/include/fci_defense_profile.h`
- `firmware/MycoBrain_FCI/include/mdp_v2_fusarium.h`
- `firmware/side_a/pio_out.txt`

### NatureOS (`C:/Users/admin2/Desktop/MYCOSOFT/CODE/NATUREOS/NatureOS`)

Tracked modified:
- `src/core-api/Controllers/MasDevicesController.cs`
- `src/core-api/Controllers/MonitoringController.cs`
- `src/core-api/Controllers/MycoBrainController.cs`
- `src/core-api/Controllers/MycosoftController.cs`
- `src/core-api/Controllers/SecurityController.cs`
- `src/core-api/Controllers/WorkflowController.cs`
- `src/core-api/Program.cs`

Untracked:
- `src/core-api/Services/DeepAgentEventService.cs`

### NLM (`C:/Users/admin2/Desktop/MYCOSOFT/CODE/MAS/NLM`)

Tracked modified:
- `nlm/core/fingerprints.py`
- `nlm/data/preconditioner.py`
- `nlm/guardian/avani.py`
- `nlm/model/config.py`
- `nlm/model/encoders.py`
- `nlm/model/heads.py`
- `nlm/model/nlm_model.py`
- `nlm/training/dataset.py`
- `nlm/training/losses.py`

Untracked:
- `tests/test_maritime.py`

### SDK (`C:/Users/admin2/Desktop/MYCOSOFT/CODE/MAS/sdk`)

Tracked modified:
- `natureos_sdk/client.py`

## 3) Gap-fill execution plan

### Phase A - Stabilize deployed integration (Priority 0)

- [ ] MINDEX: resolve missing `/api/mindex/internal/state/live` route in production runtime.
- [ ] Verify `live_state_router` is present in runtime OpenAPI and returns 200 with telemetry/nlm/experience/merkle keys.
- [ ] MAS: validate `/api/myca/world/summary` includes `mindex_live` object after MINDEX route is live.
- [ ] End-to-end smoke: Jetson publish -> MINDEX ingest -> NatureOS fanout attempt -> Fusarium mirror row creation.

### Phase B - Clean and classify pending edits (Priority 1)

- [ ] Split workspace changes into shippable feature groups: `taco`, `fusarium`, `maritime`, `mqtt`, `search`, `docs`, `cache/artifacts`.
- [ ] Remove non-source artifacts from git consideration (`.poetry-cache/**`, `pytest_out*.txt`, temp files like `nul`).
- [ ] Create per-repo commit batches with explicit scope and verification evidence.

### Phase C - Finish planned integrations (Priority 2)

- [ ] Add human-readable subscriber/operator JSON inspection workflow for MQTT -> MINDEX pipeline.
- [ ] Extend Jetson publisher from one-sensor payload to multi-sensor bundle schema.
- [ ] Confirm NatureOS auth contract (`X-Webhook-Secret` / `X-API-Key`) against active endpoint.
- [ ] Validate MYCA reads live NLM + self/world/fingerprint + Merkle provenance from runtime state endpoints.

### Phase D - Verification and release hygiene (Priority 3)

- [ ] Run MINDEX targeted tests for telemetry/mycobrain/live-state paths.
- [ ] Run MAS targeted tests for mindex bridge and worldstate route composition.
- [ ] Deploy updated website integration routes if dependent UI surfaces are required.
- [ ] Update completion docs and registries for each finalized batch.

## 4) Definition of done for this gap plan

- [ ] Production MINDEX endpoint `/api/mindex/internal/state/live` returns 200 and expected schema.
- [ ] MAS world summary includes `mindex_live` field with non-empty payload.
- [ ] All pending edits are either committed in scoped batches or explicitly dropped as artifacts.
- [ ] Remaining backlog is documented with owner, repo, and acceptance criteria.
