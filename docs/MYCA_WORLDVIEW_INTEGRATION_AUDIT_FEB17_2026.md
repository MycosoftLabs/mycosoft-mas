# MYCA Worldview Integration Audit – February 17, 2026

## Purpose

Verify the MYCA Worldview plan is complete and that all integrations between **MYCA AI, MAS, Search, Memory, Consciousness, Brain, MINDEX, MycoBrain, Services, Protocols, Apps, NatureOS, NLM, Data, and Training** modules work together with their respective APIs and routes.

**Use this audit** when sub-agents work on anything that touches these systems. Ensure integration points remain functional.

---

## 1. Plan Completion Status

| Phase | Component | Status | Location |
|-------|-----------|--------|----------|
| **1** | Telemetry Envelopes (ETA, ESI, BAR, RER, EEW) | ✅ Done | `mycosoft_mas/nlm/telemetry_envelopes.py` |
| **2** | Bio-Token Vocabulary | ✅ Done | `mycosoft_mas/nlm/bio_tokens.py` |
| **2** | Nature Message Frame (NMF) | ✅ Done | `mycosoft_mas/nlm/nmf.py` |
| **2** | Translation Layer | ✅ Done | `mycosoft_mas/nlm/translation_layer.py` |
| **3** | EarthLIVE Framework | ✅ Done | `mycosoft_mas/earthlive/` (collectors, packet_assembler) |
| **3** | EarthLIVESensor | ✅ Done | `consciousness/sensors/earthlive_sensor.py` |
| **4** | NLM API (full endpoints) | ✅ Done | NLM repo `nlm/api/main.py` + MAS `routers/nlm_api.py` |
| **4** | EarthLIVE Router | ✅ Done | `routers/earthlive_api.py` |
| **5** | NLMAgent | ⚠️ **GAP** | Not created |
| **5** | EarthLIVEAgent | ⚠️ **GAP** | Not created |
| **5** | FungiComputeAgent | ⚠️ **GAP** | Not created |
| **6** | World Model (EarthLIVE wired) | ✅ Done | EarthLIVESensor wired; earthlive_packet, earthlive_freshness in WorldState; to_summary extended. nlm_frame, fci_telemetry still optional future fields |
| **7** | Spec docs | ⚠️ **GAP** | NLM_TELEMETRY, EARTHLIVE_FRAMEWORK, NLM_TRANSLATION, WORLDVIEW_ARCH |
| **8** | API Catalog, System Registry | ⚠️ **GAP** | NLM routes not fully documented |

---

## 2. Cross-System Integration Map

### APIs and Routes

| System | Base URL | Key Routes | Used By |
|--------|----------|------------|---------|
| **MAS** | 192.168.0.188:8001 | `/api/nlm/*`, `/api/memory/*`, `/mindex/*`, `/api/agents/*` | Website, Consciousness, NLMSensor |
| **MINDEX** | 192.168.0.189:8000 | `/api/search/unified`, `/api/species/*`, `/api/compounds/*` | NLM client, MAS mindex router, Search |
| **NLM** | localhost:8200 (optional) | `/api/translate`, `/api/nmf/create`, `/api/tokens/vocabulary`, `/api/predict/fruiting`, `/api/query/knowledge`, `/api/environmental/process` | MAS nlm_api (proxy), NLMSensor |
| **MycoBrain** | localhost:8003 | `/health`, `/devices` | MycoBrainSensor, device_telemetry |
| **NatureOS** | 192.168.0.187:8002 | Channels, keys, stream | NatureOSSensor, ecosystem_status |
| **EarthLIVE** | N/A (internal) | Via packet_assembler | EarthLIVESensor → WorldState |

### Consciousness → World Model Data Flow

```
CREPSensor       → crep_data, crep_freshness
Earth2Sensor     → predictions, predictions_freshness
NatureOSSensor   → ecosystem_status, ecosystem_freshness
MINDEXSensor     → knowledge_stats
MycoBrainSensor  → device_telemetry, device_freshness
NLMSensor        → nlm_insights, nlm_freshness
PresenceSensor   → presence_data, online_users, etc.
EarthLIVESensor  → earthlive_packet, earthlive_freshness
```

### NLM → MINDEX Integration

- **NLM client** `query_knowledge_graph()` calls `MINDEX_API_URL/api/search/unified`
- MAS nlm_api `/api/nlm/query/knowledge` proxies to NLM or uses NLM client

### Memory Integration

- **memory_api** router: `/api/memory/*`
- **memory_integration_api**: bridges memory with other MAS components
- Consciousness can inject memory context; NLM/agents can store/recall via memory modules

### Search Integration

- Website Fluid Search → MINDEX unified search
- NLM knowledge query → MINDEX unified search
- MAS mindex_router proxies to MINDEX API

### Training Modules

- `mycosoft_mas/nlm/training/` – NLMTrainer
- `mycosoft_mas/nlm/inference/` – NLM inference service
- NLM API `/api/telemetry/ingest-verified` for learning pipelines

---

## 3. Critical Gaps to Fix

### High Priority (FIXED Feb 17 2026)

1. ~~**Wire EarthLIVESensor into World Model**~~ ✅ Done
2. ~~**Create earthlive_api Router**~~ ✅ Done

### Medium Priority

3. **Create NLMAgent, EarthLIVEAgent, FungiComputeAgent**
   - Register in `agents/__init__.py` and agent registry
   - Wire to NLM API, EarthLIVE, FCI/HPL

4. **WorldState: nlm_frame, fci_telemetry_envelope**
   - Add optional `nlm_frame: Optional[Dict]` (NMF serialized)
   - Add optional `fci_telemetry_envelope: Optional[Dict]`
   - Extend `to_summary()` for EarthLIVE, NMF, FCI

### Lower Priority

5. **Documentation** – Create spec docs per plan Phase 7
6. **API Catalog / System Registry** – Document all NLM and EarthLIVE routes

---

## 4. Integration Checklist for Sub-Agents

When working on code that touches any of these systems:

- [ ] **NLM** – Check `nlm_api` router, `nlm/client.py`, `mycosoft_mas.nlm` modules
- [ ] **Consciousness** – Check `world_model.py`, sensors, `to_summary()`
- [ ] **MINDEX** – Check `mindex_router`, NLM client `MINDEX_API_URL`
- [ ] **Memory** – Check `memory_api`, `memory_integration_api`, memory modules
- [ ] **Search** – Check website Fluid Search, MINDEX unified search, NLM knowledge query
- [ ] **MycoBrain** – Check `MycoBrainSensor`, device_telemetry, port 8003
- [ ] **NatureOS** – Check `NatureOSSensor`, Mycorrhizae protocol
- [ ] **EarthLIVE** – Check `earthlive` module, `EarthLIVESensor`, packet_assembler
- [ ] **Protocols** – Check MDP, MMP, HPL, FCI in Mycorrhizae repo
- [ ] **Training** – Check `nlm/training`, `nlm/inference`, telemetry ingest

---

## 5. File Reference

| Purpose | Path |
|---------|------|
| Plan | `~/.cursor/plans/myca_worldview_complete_build_939bcf99.plan.md` |
| This Audit | `docs/MYCA_WORLDVIEW_INTEGRATION_AUDIT_FEB17_2026.md` |
| Cursor Rule | `.cursor/rules/myca-worldview-integration.mdc` |
| World Model | `mycosoft_mas/consciousness/world_model.py` |
| NLM Router | `mycosoft_mas/core/routers/nlm_api.py` |
| EarthLIVE | `mycosoft_mas/earthlive/` |
| Sensors | `mycosoft_mas/consciousness/sensors/` |
