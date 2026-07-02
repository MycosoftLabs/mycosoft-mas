# ITAR / Export-Control Sensitive Code Inventory — Jun 25, 2026

**Date:** 2026-07-02  
**Status:** Draft for Morgan review  
**Purpose:** Inventory paths that may warrant export-control review or future private-repo treatment.  
**Classification:** None of the listed paths are marked ITAR-classified in-repo. All entries are **REVIEW** unless noted.

**Morgan action requested:** Review this table before any repo visibility change. **No repos were made private** as part of this sweep.

---

## Legend

| Flag | Meaning |
|------|---------|
| **REVIEW** | Potentially export-sensitive; legal/ops review recommended |
| **INFO** | Export-control awareness code (policy/compliance), not operational military tech |
| **LOW** | Public/open data pipelines; defense-adjacent naming only |

**Recommended action (default):** `Review → consider private repo or restricted submodule`

---

## Repository summary

| Repo | GitHub | Visibility (2026-07-02) | Priority |
|------|--------|-------------------------|----------|
| mycosoft-mas | MycosoftLabs/mycosoft-mas | PUBLIC | High |
| website | MycosoftLabs/website | PUBLIC | High |
| mindex | MycosoftLabs/mindex | PUBLIC | High |
| mycobrain | MycosoftLabs/mycobrain | PUBLIC | High |
| NatureOS | MycosoftLabs/NatureOS | PUBLIC | Medium |
| Mycorrhizae | MycosoftLabs/Mycorrhizae | PUBLIC | Medium |
| NLM | MycosoftLabs/NLM | PUBLIC | Low |
| sdk | MycosoftLabs/sdk | PUBLIC | Low |
| MYCODAO | MycosoftLabs/MYCODAO | PUBLIC | Low |
| platform-infra | (local / no remote match) | n/a | Medium |
| psathyrella-jetson | (local under `Devices/`) | n/a | **High** |
| Fusarium | MycosoftLabs/Fusarium | PRIVATE (org) | High |
| SINE artifacts | `.codex-artifacts/sine-repos/` (local cache) | n/a | **High** |

---

## Detailed inventory

### MAS — `mycosoft-mas`

| Path | Flag | Reason | Recommended action |
|------|------|--------|-------------------|
| `mycosoft_mas/fusarium/` | REVIEW | FUSARIUM defense operator plane, auth, mission workflows | Review → private or split defense submodule |
| `mycosoft_mas/integrations/defense_client.py` | REVIEW | Defense integration client | Review |
| `mycosoft_mas/agents/custom/create_a_defense.py` | REVIEW | Defense agent scaffolding | Review |
| `mycosoft_mas/agents/crep_security_agent.py` | REVIEW | CREP security agent | Review |
| `mycosoft_mas/agents/clusters/taco/` | REVIEW | Ocean/acoustic TACO agent cluster (signal classification, anomaly) | Review → private |
| `mycosoft_mas/earthlive/` | REVIEW | EarthLIVE packet assembly / collectors (operational sensor fusion) | Review |
| `mycosoft_mas/earthlive/collectors/` | REVIEW | Live environmental/maritime data collectors | Review |
| `mycosoft_mas/agents/security/export_control_agent.py` | INFO | Export-control compliance agent | Keep; policy surface |
| `mycosoft_mas/integrations/export_control_client.py` | INFO | Export-control client | Keep; policy surface |
| `config/ethics_checklists/defense_sector.yaml` | INFO | Defense sector ethics checklist | Keep |
| `docs/PSATHYRELLA_SINE_BUOY_INGEST_SCOPE_JUN26_2026.md` | REVIEW | Buoy/SINE ingest scope documentation | Review |
| `docs/NATUREOS_DEFENSE_V2_JUN15_2026.md` | REVIEW | Defense architecture documentation | Review |
| `docs/FUSARIUM_*` | REVIEW | FUSARIUM defense plane completion/plan docs | Review |

### Website — `website`

| Path | Flag | Reason | Recommended action |
|------|------|--------|-------------------|
| `app/defense/` | REVIEW | Defense portal UI | Review → private |
| `app/api/oei/` | REVIEW | Operational Environmental Intelligence API routes | Review → private |
| `app/api/crep/` | REVIEW | CREP unified / aviation / maritime / satellite / buoy APIs | Review |
| `app/api/defense/` | REVIEW | Defense briefing API | Review |
| `components/defense/` | REVIEW | Defense portal components (OEI/FUSARIUM UX) | Review |
| `components/oei/` | REVIEW | OEI monitoring components | Review |
| `components/psathyrella/` | REVIEW | Psathyrella maritime buoy device UI | Review → private |
| `lib/psathyrella/` | REVIEW | Psathyrella local operator / MQTT bridge logic | Review → private |
| `app/docs/devices/psathyrella/` | REVIEW | Psathyrella device documentation surface | Review |
| `services/crep-collectors/` | REVIEW | Aviation, maritime, satellite, rail, power-grid collectors | Review |
| `services/collectors/` | REVIEW | CREP collector Docker images (aviation, maritime, satellite) | Review |
| `services/crep-gateway/` | REVIEW | CREP gateway service | Review |
| `services/security/threat_intel_service.py` | REVIEW | Threat intelligence service | Review |
| `services/security/nmap_scanner.py` | REVIEW | Network scanning tooling | Review |
| `services/security/suricata_parser.py` | REVIEW | IDS log parsing | Review |
| `services/security/unifi_security_monitor.py` | REVIEW | Network security monitoring | Review |
| `lib/crep/military-enrichment.ts` | REVIEW | Military base enrichment (if present on main) | Review |
| `app/api/oei/military/` | REVIEW | Military facility OEI routes (if present on main) | Review |
| `scripts/import-military-bases.ts` | REVIEW | Military base import tooling | Review |

### MINDEX — `mindex`

| Path | Flag | Reason | Recommended action |
|------|------|--------|-------------------|
| `sine-acoustic-classifier/` | REVIEW | SINE marine acoustic classification (export-sensitive adjacency) | Review → private split |
| `mindex_etl/sources/osm_military_polygons.py` | REVIEW | OSM military polygon ingestion | Review |
| `mindex_etl/jobs/sync_osm_military_polygons.py` | REVIEW | Military polygon sync job | Review |
| `docs/ACOUSTIC_CLASSIFIER_SCOPE_MAY27_2026.md` | REVIEW | Acoustic classifier scope | Review |
| `tests/test_sine_classifier_visualisation_contract.py` | REVIEW | SINE classifier tests | Review with classifier |

### MycoBrain — `mycobrain`

| Path | Flag | Reason | Recommended action |
|------|------|--------|-------------------|
| `firmware/MycoBrain_FCI/include/fci_defense_profile.h` | REVIEW | FCI defense profile firmware header | Review |
| `firmware/MycoBrain_FCI/include/mdp_v2_fusarium.h` | REVIEW | FUSARIUM MDP v2 firmware protocol | Review |
| `firmware/MycoBrain_ScienceComms/include/modem_audio.h` | REVIEW | Modem/audio comms (marine adjacency) | Review |
| `deploy/jetson/taco_inference.py` | REVIEW | Jetson TACO inference deploy | Review |
| `firmware/gateway/` | REVIEW | Sensor gateway firmware (field device) | Review |

### NatureOS — `NatureOS`

| Path | Flag | Reason | Recommended action |
|------|------|--------|-------------------|
| `src/core-api/Services/MycoBrainService.cs` | LOW | Device ingestion (field sensors) | Review if defense-tagged |
| `src/ingestion/MycoBrainIngestionFunction.cs` | LOW | Telemetry ingestion | Review if defense-tagged |
| `src/mycorrhizae/MDPv1Protocol.cs` | LOW | Device protocol | Review with firmware |

### Mycorrhizae — `Mycorrhizae`

| Path | Flag | Reason | Recommended action |
|------|------|--------|-------------------|
| `mycorrhizae-protocol/mycorrhizae/fci/signal_classification.py` | REVIEW | FCI signal classification | Review |
| `mycorrhizae-protocol/mycorrhizae/fci/signal_processing.py` | REVIEW | FCI signal processing | Review |
| `mycorrhizae-protocol/mycorrhizae/mwave/` | LOW | Earthquake/USGS analyzer (public data) | LOW unless fused with defense |

### Local / non-GitHub paths

| Path | Flag | Reason | Recommended action |
|------|------|--------|-------------------|
| `Devices/psathyrella-jetson/` | REVIEW | Jetson buoy edge agent (bringup, MQTT, install) | Review → dedicated private repo |
| `CODE/docs/PSATHYRELLA_*` | REVIEW | Psathyrella buoy/GCS integration handoffs | Review |
| `CODE/FUSARIUM/` | REVIEW | FUSARIUM architecture plan artifacts (not production code) | Archive or move to private planning repo |
| `CODE/.codex-artifacts/sine-repos/` | REVIEW | Cached SINE/audio classification repos | Do not publish; delete or private |
| `CODE/.codex-temp/sine-audio-repo-audit/` | REVIEW | SINE audit temp artifacts | Delete after review |

### MAS NLM / SDK

| Path | Flag | Reason | Recommended action |
|------|------|--------|-------------------|
| `MAS/NLM/` (whole repo) | LOW | Nature learning models; review if trained on defense-tagged datasets | Review data provenance |
| `MAS/sdk/` (whole repo) | LOW | NatureOS SDK; review if defense APIs exposed | Review API surface |

### Platform infra

| Path | Flag | Reason | Recommended action |
|------|------|--------|-------------------|
| `platform-infra/` (whole repo) | REVIEW | Deployment manifests may reference defense endpoints/VMs | Review env templates only |

---

## Third-party forks — NOTICE only (do not overwrite LICENSE)

Per Morgan directive and `CURSOR_HANDOFF.md`, these forks retain upstream OSS licenses:

| Fork repo | Action taken |
|-----------|--------------|
| AgaricFlight | No proprietary LICENSE overwrite |
| MycaControl | No proprietary LICENSE overwrite |
| Mycowallet-android | No proprietary LICENSE overwrite |
| mycelium-library | No proprietary LICENSE overwrite |
| intersection_observer | No proprietary LICENSE overwrite |
| Agaric | No proprietary LICENSE overwrite |

Optional follow-up: separate PR adding **NOTICE** only (ownership / export-awareness).

---

## What was NOT done

- No `gh repo edit --visibility private` on any repository
- No CI/CD workflow changes
- No deployment, NAS, buoy runtime, SINE, or Psathyrella code changes (docs/LICENSE/NOTICE/README only)
- No secrets collected or listed in this document

---

## Morgan review checklist

1. Confirm which **REVIEW** paths are false positives vs. require private split.
2. Decide fate of **local-only** paths (`Devices/psathyrella-jetson`, `FUSARIUM/`, `.codex-artifacts/sine-repos/`).
3. Approve optional **NOTICE-only** PRs for six third-party forks.
4. If private flip is approved later, start with: `website` (defense/OEI/CREP), `mindex` (sine-acoustic-classifier), `mycosoft-mas` (fusarium/taco), `mycobrain` (FCI defense firmware).

**Contact:** legal@mycosoft.org
