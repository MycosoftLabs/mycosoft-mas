# Execution Waves and Acceptance — Mar 19, 2026

**Date:** March 19, 2026  
**Status:** Sprint-shaped waves with acceptance criteria  
**Related:** [PLATFORM_GAP_AUDIT_AND_BACKLOG_MAR19_2026.md](PLATFORM_GAP_AUDIT_AND_BACKLOG_MAR19_2026.md), [INTEGRATION_COMPLETION_MATRIX_MAR19_2026.md](INTEGRATION_COMPLETION_MATRIX_MAR19_2026.md)

---

## Wave P0 — Security and correctness

**Scope:** Credentials, secret scan, mock-data removal per [GAPS_AND_SECURITY_AUDIT_MAR14_2026.md](GAPS_AND_SECURITY_AUDIT_MAR14_2026.md).

**Files/areas:**
- Scripts that touch VM/Proxmox credentials
- `tool_orchestrator.py`, `llm_brain.py` (base64 audit—already confirmed non-secret)
- Production data paths (no mock arrays)

**Tests/commands:**
- `grep -r "password\s*=\s*['\"]" scripts/` → no matches
- `grep -r "REDACTED_" .` → no matches in committed code
- Security audit skill or manual scan

**Evidence:** Grep output clean; completion note in GAPS_AND_SECURITY_AUDIT.

**Registry updates:** [API_CATALOG_FEB04_2026.md](API_CATALOG_FEB04_2026.md) when adding endpoints.

---

## Wave P1 — Integration contracts and API honesty

**Scope:** BFF normalization, MAS↔MINDEX alignment, CREP command path, 501 reconciliation.

**Files/areas:**
- `WEBSITE/website/app/api/**`
- MAS routers that call MINDEX
- [CREP_COMMAND_CONTRACT_MAR13_2026.md](CREP_COMMAND_CONTRACT_MAR13_2026.md) implementation

**Tests/commands:**
- `route-validator` or equivalent (find 501/not-implemented routes)
- `curl http://localhost:3010/api/health` → 200
- CREP command smoke (flyTo, showLayer)

**Evidence:** Route report; curl 200; CREP command received in dashboard.

**Registry updates:** [API_CATALOG_FEB04_2026.md](API_CATALOG_FEB04_2026.md), [SYSTEM_REGISTRY_FEB04_2026.md](SYSTEM_REGISTRY_FEB04_2026.md).

**P1 Evidence (Mar 19–20, 2026):**
- `curl http://localhost:3010/api/health` → 200, `{"status":"healthy",...}`
- Rules updated: 501 claim qualified in mycosoft-full-codebase-map.mdc, mycosoft-full-context-and-registries.mdc
- CREP row: smoke tests (flyTo, showLayer) added to definition of done in INTEGRATION_COMPLETION_MATRIX

---

## Wave P2 — Voice, duplex, and realtime strategy

**Scope:** Voice E2E, WebSocket/SSE spine choice, GPU placement docs.

**Files/areas:**
- [VOICE_TEST_QUICK_START_FEB18_2026.md](VOICE_TEST_QUICK_START_FEB18_2026.md)
- [SPEECH_DUPLEX_MIGRATION_MAR14_2026.md](SPEECH_DUPLEX_MIGRATION_MAR14_2026.md)
- CREP/device/AI Studio realtime surfaces

**Tests/commands:**
- E2E script or Playwright: speak → MAS → audio
- Document chosen WebSocket/SSE spine per surface in [INTEGRATION_COMPLETION_MATRIX_MAR19_2026.md](INTEGRATION_COMPLETION_MATRIX_MAR19_2026.md)

**Evidence:** Playwright or manual E2E log; GPU placement doc (190 vs local) per [python-process-registry.mdc](../.cursor/rules/python-process-registry.mdc).

**P2 Evidence (Mar 19–20, 2026):**
- Realtime spine documented in [INTEGRATION_COMPLETION_MATRIX_MAR19_2026.md](INTEGRATION_COMPLETION_MATRIX_MAR19_2026.md): WebSocket (voice, CREP), SignalR (NatureOS), HTTP heartbeat (devices)
- GPU placement: 190 in prod, local for dev; ref python-process-registry.mdc

---

## Wave P3 — Data plane and "looks complete but empty" UIs

**Scope:** Scientific dashboards real data; NatureOS/superapp wiring; MYCA2 verification.

**Files/areas:**
- Scientific dashboard components (wire MINDEX/MAS)
- [SUPERAPP_ARCHITECTURE_AND_UNIFICATION_FEB19_2026.md](SUPERAPP_ARCHITECTURE_AND_UNIFICATION_FEB19_2026.md) items in order
- MYCA2 PSILO: verification, operator UX, production isolation proof

**Tests/commands:**
- Scientific dashboard shows real series (not placeholder)
- Superapp nav/shell per UNI-01
- MYCA2 sandbox smoke (myca2_vm_rollout.py, pytest MYCA2_VM_SMOKE=1)

**Evidence:** Screenshot or test output; completion rows in DOC_DRIFT.

**P3 Evidence (Mar 19–20, 2026):**
- **Scientific dashboards:** `useFCI` (hooks/scientific/use-fci.ts) fetches from `/api/bio/fci`; `useFCIDevices` (lib/fungi-compute/hooks.ts) fetches from `/api/fci/devices`. Mock `DEMO_DEVICES` fallback removed; empty state on API failure per no-mock-data policy.
- **FCI monitor, bio page, electrode-map:** Use real API via useFCI; no placeholder series in production paths.
- **SUPERAPP / NatureOS:** Doc-level stubs (cursor_index_scan) in SUPERAPP_ARCHITECTURE, NATUREOS_*; implementation tracked in SUPERAPP plan (UNI-01..UNI-05+). INTEGRATION_COMPLETION_MATRIX NatureOS row: SignalR spine documented; live-map/AI Studio use real hub.
- **DOC_DRIFT:** SUPERAPP and NatureOS rows updated with P3 proof link.

---

## Cross-cutting: Backlog cadence

### Weekly gap refresh (explicit checklist)

1. **Refresh gap artifact:**
   ```bash
   python scripts/gap_scan_cursor_background.py
   ```
   Or via MAS API: `GET http://192.168.0.188:8001/agents/gap/scan`
2. **Merge into triage:** Open [DOC_DRIFT_AND_INDEX_TRIAGE_MAR19_2026.md](DOC_DRIFT_AND_INDEX_TRIAGE_MAR19_2026.md); append new `referenced_files_with_gaps` from `gap_report_latest.json` → `cursor_index_scan` section.
3. **Close rows:** For each resolved item, set Status → `done`, Proof → commit SHA or PR link.
4. **Update indexes:** If new vital docs added, update [MASTER_DOCUMENT_INDEX.md](MASTER_DOCUMENT_INDEX.md) and [CURSOR_DOCS_INDEX.md](../.cursor/CURSOR_DOCS_INDEX.md).

### Per-deploy checklist

| System | Steps | Commands / verification |
|--------|-------|-------------------------|
| **Website** | 1. Test localhost:3010<br>2. Commit + push to main<br>3. SSH to Sandbox 187<br>4. Pull, rebuild image, restart container<br>5. Purge Cloudflare | `ssh mycosoft@192.168.0.187`<br>`cd /opt/mycosoft/website && git reset --hard origin/main`<br>`docker build -t mycosoft-always-on-mycosoft-website:latest --no-cache .`<br>`docker run -d ... -v /opt/mycosoft/media/website/assets:/app/public/assets:ro ...`<br>Cloudflare Dashboard → Purge Everything |
| **MAS** | 1. Push to main<br>2. SSH to MAS 188<br>3. Pull, restart orchestrator | `ssh mycosoft@192.168.0.188`<br>`sudo systemctl restart mas-orchestrator` |
| **MINDEX** | 1. Push to main<br>2. SSH to MINDEX 189<br>3. Pull, rebuild API container, restart | `docker compose stop mindex-api && docker compose build --no-cache mindex-api && docker compose up -d mindex-api` |
| **Verify** | Health checks | `curl http://192.168.0.187:3000`<br>`curl http://192.168.0.188:8001/health`<br>`curl http://192.168.0.189:8000/health` |

---

## Definition of done (global)

- Code merged with tests or documented manual proof
- Registries/catalog updated when behavior or URLs change
- Dated doc updated (DOC_DRIFT row closed) or completion doc per [plan-and-task-completion-docs.mdc](../.cursor/rules/plan-and-task-completion-docs.mdc)
