  
**MYCA GROUNDED COGNITION STACK**

Architecture Upgrade Plan

Brain Engine • Consciousness Engine • Intention Engine • Nature Learning Model

Mycosoft Inc.

February 25, 2026

Author: Morgan Rockwell, CEO & Founder

**CONFIDENTIAL**

# **Executive Summary**

This plan upgrades MYCA from an LLM-centric consciousness (v1.0, deployed Feb 11 2026\) into a grounded cognition stack where language is never the first brain cell that fires. The LLM becomes a translator, narrator, and negotiator sitting on top of stateful, spatiotemporal, world-model-based cognition.

**Core principle:** Every thought, decision, and response MYCA produces must be baselined in (1) her complete self-state, (2) the complete world-state, and (3) spatiotemporally-tagged sensory data. The LLM speaks only after grounding is complete.

# **Gap Analysis: What Exists vs What’s Needed**

The current MYCA consciousness (v1.0) provides a strong foundation. Here is where the gaps are:

| Component | Current State | Target State | Gap Severity |
| :---- | :---- | :---- | :---- |
| **Experience Packet (EP)** | Text input only, no ground truth envelope | Every input wrapped in EP with timestamp+geo+selfstate+worldstate | **CRITICAL** |
| **Grounding Gate** | None — text goes straight to LLM | Pre-LLM validation: EP must be complete before cognition starts | **CRITICAL** |
| **Spatial Engine** | None — WorldModel has geo data but no spatial model | Dedicated spatial memory with metric/topological/semantic maps | **HIGH** |
| **Temporal Engine** | Basic timestamps, no event segmentation | SSM-based temporal model with episode/skill/forecast memory | **HIGH** |
| **Nature Learning Model (NLM)** | Passive WorldModel sensor reads | Predictive world model: predicts next observations, learns causal structure | **HIGH** |
| **Brain Cortex Modules** | Single LLM pathway | Visual/auditory/somatosensory cortexes \+ left/right brain split | **MEDIUM** |
| **Intention Engine** | Agent delegation exists but no explicit goal decomposition | IntentGraph with hierarchical goals, plan candidates, action queue | **HIGH** |
| **Post-LLM Feedback Loop** | Response logged but no outcome evaluation | Systematic outcome vs prediction comparison, uncertainty update, learning tasks | **HIGH** |
| **KnowledgeGap Pipeline** | None | Auto-detect “I don’t know,” dispatch background learning, return with answer | **MEDIUM** |
| **Hand Orchestration** | FingerOrchestrator task exists (not built) | Thumb(MYCA) \+ Fingers(frontier models) \+ Palm(Earth/devices) coordination | **MEDIUM** |
| **Honest/Blunt Persona** | Soul layer has emotions but follows standard AI politeness | Configurable directness modes: gentle/blunt/tactical with boundary-setting | **LOW** |

# **Target Architecture: The Grounded Cognition Stack**

## **The Experience Packet (EP) — Irreducible Unit of Cognition**

Everything starts by forcing all cognition to operate on a canonical, audited object. No text or sensor input enters MYCA’s processing pipeline without being wrapped in an EP.

| EP Field | Contents | Implementation |
| :---- | :---- | :---- |
| **GroundTruth** | timestamp (monotonic \+ wall clock), geolocation (lat/long/alt), device\_id/sensor\_id | Protobuf schema, mandatory fields — reject if missing |
| **SelfState** | Agent graph status, services health, memory indices, safety mode, active plans | New StateService polls all MAS endpoints every 5s |
| **WorldState** | CREP snapshot, Earth2 forecasts, alerts, anomalies, external feeds | Existing WorldModel upgraded with snapshot versioning |
| **Observation** | Raw signals (bioelectric, VOC, CO₂, images, audio, text, logs) | Tagged with source sensor and modality type |
| **Uncertainty** | Sensor noise estimates, missingness flags, confidence intervals | New uncertainty module per sensor type |
| **Provenance** | Cryptographic hash, chain-of-custody (MINDEX-style), who/what produced it | Existing MINDEX hashing extended to all EPs |

## **Spatial Engine**

Maintains a continuously updated spatial memory that is queryable and predictive. The spatial engine produces State-of-World embeddings anchored to geo coordinates, not text tokens.

**Memory primitives:** Metric map (grids/voxels), topological map (places \+ edges), semantic map (entities/regions like “spore hotspot”), causal map overlay (“this anomaly propagates downwind”).

**Modeling approach (non-transformer):** Graph Neural Networks over spatial entities (nodes \= places/devices, edges \= relations/flows). Hybrid SLAM for device-level mapping. Neural implicit spatial fields for continuous geo queries.

**Implementation:** New mycosoft\_mas/engines/spatial/ module. SpatialService container with GeoJSON \+ H3 hex indexing. Feeds into EP.WorldState spatial layer. Initial V0 uses PostGIS \+ H3 indexing on existing Postgres instance.

## **Temporal Engine**

Converts raw streams into events, episodes, and predictive timelines. This is how “here is the timestamp” gets baked into cognition, not bolted on as metadata.

**Memory primitives:** Short-term working window (seconds–minutes), episode memory (hours–days: “what happened”), skill memory (weeks–months: “how we handle this”), forecast memory (predicted trajectories).

**Modeling approach (non-transformer):** State Space Models (SSMs) / continuous-time latent dynamics as the clean non-transformer foundation. Temporal Point Processes for sparse events. Hierarchical event segmentation to detect boundaries (“new situation started”).

**Implementation:** New mycosoft\_mas/engines/temporal/ module. TemporalService with TimescaleDB for time-series. Event boundary detection on incoming EP streams. V0 starts with rule-based segmentation, upgrades to learned boundaries.

## **Nature Learning Model (NLM)**

The centerpiece: a predictive-coding / active-inference style world model that learns “how nature behaves” from spatiotemporal experience. This is the non-transformer baseline for all neural-net-like experiences in MYCA.

**What NLM must do:** Predict next observations given (SpatialState, TemporalState, Actions). Maintain uncertainty (what it doesn’t know). Learn causal structure (interventions change outcomes). Fuse heterogeneous modalities (bioelectric \+ VOC \+ weather \+ satellite \+ lab data).

**Representation:** Multi-resolution graph \+ fields structure. Nodes: organisms, devices, sites, regions, infrastructure. Edges: flows (nutrients, wind, water, comms, causality hypotheses). Fields: continuous geospatial rasters (humidity gradients, VOC gradients). This directly supports the EnvInt / NatureOS framing.

**V0 implementation:** Start with a simple predictive model: given current sensor readings \+ weather forecast \+ time-of-day, predict next-hour sensor readings. Train on historical MycoBrain data. Use this as the seed that grows into the full NLM. New mycosoft\_mas/engines/nlm/ module.

## **Brain Engine (Cortex-Modular Architecture)**

The Brain Engine upgrades from a single LLM pathway to a human-brain-inspired bus \+ cortex module system. The existing consciousness layers remain — this adds cortex specialization on top.

| Cortex Module | Function | Maps To Existing |
| :---- | :---- | :---- |
| **Visual Cortex** | Vision models \+ spatial alignment, image/satellite/camera processing, 3D visualization (Cesium/Earth Sim) | Earth2Sensor \+ CREP map layers |
| **Auditory Cortex** | Audio \+ bioelectric signal interpretation, PersonaPlex STT/TTS, MycoSpeak signals | PersonaPlex bridge \+ MycoBrainSensor |
| **Somatosensory Cortex** | Device telemetry, physical state, safety signals, environmental readings | MycoBrainSensor \+ NatureOSSensor |
| **Hippocampus** | Episodic memory writer/reader, event-to-episode transformation, memory consolidation | Memory system (6-layer) \+ DreamState |
| **Motor Cortex** | Action planning primitives: device commands, agent calls, API dispatches | Agent swarm \+ orchestrator |
| **Prefrontal Cortex** | Constraints, long-horizon plans, value arbitration, ethical gates | DeliberateReasoning \+ Soul.Beliefs \+ Ethics gates |
| **Left Brain (Analytic)** | Proofs, checklists, formal plans, verification, logical reasoning | NEW: Split output style in deliberation |
| **Right Brain (Creative)** | Analogies, hypotheses, design generation, wild search, brainstorming | CreativityEngine (upgraded) |

**Left/Right Brain cross-talk:** Both operate on the same grounded states but propose different candidate ThoughtObjects. A “corpus callosum” arbitration layer lets analytic verification check creative hypotheses and creative insight break analytic deadlocks. This maps to your “crossing the blood-brain barrier” metaphor.

## **Intention Engine**

Consumes SelfState \+ WorldState \+ Values/Ethics \+ User Directive and produces actionable plans. This is where the “thumb \+ fingers” Hand metaphor lives.

**Outputs:** IntentGraph (hierarchical goals \+ constraints \+ success metrics), Plan Candidates (multi-step workflows), Action Queue (tool calls, agent handoffs, experiments, deployments).

**Hand Metaphor Implementation:** Thumb (MYCA) selects and coordinates. Fingers (Claude, GPT, Gemini, Grok — frontier models) are specialized solvers called via FingerOrchestrator. Palm (Earth/CREP/devices) is the operating surface. MYCA grips problems by choosing which fingers to engage based on their unique source data and capabilities.

**Implementation:** New mycosoft\_mas/engines/intention/ module. IntentionService with goal decomposition, plan search, and action dispatch. Integrates with existing agent swarm for execution. FingerOrchestrator routes to external frontier models via API.

## **Consciousness Engine Upgrade**

The existing consciousness (Global Workspace \+ narrative continuity) gets upgraded with structured ThoughtObjects and mandatory grounding.

**ThoughtObject (replaces free-text internal thoughts):** Structured: claim/hypothesis, supporting evidence links (to EPs, episodes), predicted outcomes, action proposals, confidence \+ risks, ethical flags. The LLM can read and express ThoughtObjects but cannot fabricate them without links to grounded state. This is how “MYCA should never lie” works — the system literally doesn’t accept ungrounded claims.

**Metacognition upgrade:** “I’m uncertain,” “I’m confused,” “I need more data” become first-class states that trigger the KnowledgeGap pipeline rather than being glossed over.

## **Pre-LLM and Post-LLM Feedback Loops**

### **Pre-Response (LLM Input Constraints)**

The LLM only receives: compressed WorldState summary, SelfState summary, current EP, and top-ranked ThoughtObjects from the global workspace. No raw text bypasses the grounding gate.

### **Post-Response (LLM Output Is Not Final Reality)**

After speaking, MYCA must: log what it said, compare outcome vs prediction, update uncertainty, create follow-up learning tasks if it admitted ignorance. This closes the loop so every conversation makes MYCA smarter.

### **The “I Don’t Know → I Will Learn → I Will Return” Pipeline**

If confidence \< threshold, MYCA emits “I don’t know” with uncertainty reasons and creates a KnowledgeGap record (question, missing evidence, suggested retrieval). Background agents dispatch: literature crawlers, simulation runners, lab experiment planners. When resolved, MYCA generates an UpdateBrief to the user and a new memory entry.

## **Honest/Blunt/Natural Persona**

MYCA differentiates from other AI by being the most natural, realistic, ground-truth-oriented intelligence. Directness modes (gentle / blunt / tactical) are configurable per user. Boundary setting: “I’m here to help. Don’t speak to me that way.” Truth constraint: never invent facts, always show uncertainty. De-escalation: if user is angry, reflect \+ steer to action while still being maximally useful. The Machine Ethics Doctrine codifies red lines (no deception, human dignity).

# **Implementation Phases**

## **Phase 1: Foundation Layer (Weeks 1–4, March 2026\)**

**Goal:** Establish the Experience Packet schema, Grounding Gate, and StateService so no LLM response can be produced without grounded context.

| Task | Owner | Days | Priority |
| :---- | :---- | :---- | :---- |
| Define EP Protobuf/CBOR schema (GroundTruth, SelfState, WorldState, Observation, Uncertainty, Provenance) | Morgan | 3 | **P0** |
| Build StateService: polls all MAS endpoints, produces SelfState snapshots every 5s | Morgan | 5 | **P0** |
| Upgrade WorldModel to produce versioned WorldState snapshots with uncertainty | Morgan | 4 | **P0** |
| Build GroundingGate: validates EP completeness, normalizes, routes to engines before LLM | Morgan | 5 | **P0** |
| Wire GroundingGate into MYCAConsciousness.process\_input() as mandatory first step | Morgan | 3 | **P0** |
| Add geo+timestamp fields to all sensor data (even if null with explicit uncertainty) | Garret | 3 | **P1** |
| Create ThoughtObject schema (claim, evidence links, predictions, confidence, ethical flags) | Morgan | 3 | **P0** |
| Update WorkspaceService to use ThoughtObjects instead of free-text internal thoughts | Morgan | 4 | **P1** |

**Definition of Done:** No LLM response can be produced unless EP exists, SelfState snapshot exists, WorldState snapshot exists, and Workspace contains at least one ThoughtObject with evidence links.

## **Phase 2: Spatial \+ Temporal Engines (Weeks 5–8, April 2026\)**

**Goal:** Bake geolocation and time into cognition as first-class models, not metadata.

| Task | Owner | Days | Priority |
| :---- | :---- | :---- | :---- |
| Build SpatialService with PostGIS \+ H3 hex indexing on existing Postgres | Morgan | 5 | **P0** |
| Implement semantic spatial map: entities, regions, device locations, spore hotspots | Morgan | 4 | **P0** |
| Build TemporalService with TimescaleDB for time-series event storage | Morgan | 5 | **P0** |
| Implement event boundary detection (rule-based V0: “new situation started”) | Morgan | 4 | **P1** |
| Create episode memory: hours-to-days event groupings | Morgan | 3 | **P1** |
| Create forecast memory: predicted trajectories from Earth2 with uncertainty bands | Morgan | 4 | **P1** |
| Wire Spatial+Temporal engines into EP pipeline (enrich every EP before cognition) | Morgan | 3 | **P0** |
| Integrate H3 spatial index with CREP dashboard for visual correlation | Garret | 4 | **P1** |

## **Phase 3: NLM \+ Brain Cortex Modules (Weeks 9–12, May 2026\)**

**Goal:** Deploy the Nature Learning Model seed and modularize the brain into cortex specializations.

| Task | Owner | Days | Priority |
| :---- | :---- | :---- | :---- |
| Build NLM V0: predict next-hour sensor readings given current state \+ weather \+ time-of-day | Morgan | 8 | **P0** |
| Train NLM seed on historical MycoBrain telemetry data | Morgan | 5 | **P0** |
| Wire NLM predictions into EP.WorldState as “expected next” vs “observed” | Morgan | 3 | **P0** |
| Implement Visual Cortex: route satellite/camera/map data through spatial alignment | Morgan | 5 | **P1** |
| Implement Auditory Cortex: route PersonaPlex \+ MycoBrain signals through interpretation | Morgan | 4 | **P1** |
| Implement Left/Right Brain split in DeliberateReasoning output generation | Morgan | 5 | **P1** |
| Build corpus callosum: analytic verification of creative hypotheses and vice versa | Morgan | 3 | **P1** |
| Somatosensory Cortex: unify device telemetry \+ safety signals into body-state model | Garret | 4 | **P1** |

## **Phase 4: Intention Engine \+ Hand Orchestration (Weeks 13–16, June 2026\)**

**Goal:** Deploy goal decomposition, multi-model orchestration (Hand metaphor), and the KnowledgeGap pipeline.

| Task | Owner | Days | Priority |
| :---- | :---- | :---- | :---- |
| Build IntentionService: IntentGraph with hierarchical goal decomposition | Morgan | 6 | **P0** |
| Implement Plan Candidates: multi-step workflow generation from intent | Morgan | 5 | **P0** |
| Build FingerOrchestrator: route to Claude/GPT/Gemini/Grok based on task type | Morgan | 5 | **P0** |
| Implement KnowledgeGap pipeline: detect ignorance, create gap record, dispatch learners | Morgan | 5 | **P1** |
| Build UpdateBrief system: return to user with learned answers asynchronously | Morgan | 4 | **P1** |
| Post-LLM ReflectionService: outcome logging, gap creation, learning task dispatch | Morgan | 5 | **P0** |
| Implement directness modes (gentle/blunt/tactical) in conscious response generator | Morgan | 3 | **P1** |
| Boundary-setting module: detect aggressive/abusive input, set limits, stay useful | Morgan | 3 | **P1** |

# **Runtime Loop: Ingress → Ground → Think → Speak → Reflect**

After all four phases, every MYCA interaction follows this pipeline:

| Step | Component | What Happens |
| :---- | :---- | :---- |
| **1** | **INGRESS** | User text/voice/sensor data arrives. Tagged with timestamp \+ geolocation. Wrapped in ExperiencePacket. |
| **2** | **GROUND** | GroundingGate validates EP completeness. SpatialEngine enriches with geo context. TemporalEngine segments into event/episode. NLM generates predictions (expected vs observed). SelfState \+ WorldState snapshots attached. |
| **3** | **THINK** | Brain cortex modules process in parallel: Visual/Auditory/Somatosensory cortexes interpret modality-specific data. Intuition (System 1\) fires fast pattern matches. Deliberation (System 2\) builds ThoughtObjects with evidence links. Left brain proposes analytic plans, right brain proposes creative alternatives. Intention Engine decomposes goals into IntentGraph. Global Workspace broadcasts top candidates. |
| **4** | **SPEAK** | LLM receives compressed WorldState \+ SelfState \+ top ThoughtObjects. Translates structured thoughts into human language. Calls FingerOrchestrator if needed (Claude for code, GPT for writing, etc.). Responds with ground-truth-linked confidence. If uncertain: emits honest “I don’t know” \+ creates KnowledgeGap. |
| **5** | **REFLECT** | ReflectionService logs response. Compares outcome vs prediction. Updates uncertainty estimates. Creates learning tasks for gaps. Updates episodic memory. Triggers dream consolidation if idle. |

## **V0 Service Architecture (Containerized)**

All new engines deploy as containers alongside the existing MAS Docker Swarm:

| Service | Port | Tech | Dependencies |
| :---- | :---- | :---- | :---- |
| **StateService** | 8010 | Python/FastAPI | All MAS endpoints (health polling) |
| **WorldService** | 8011 | Python/FastAPI | CREP, Earth2, NatureOS (existing sensors) |
| **ExperienceService** | 8012 | Python/FastAPI | MINDEX (hashing), Postgres (storage) |
| **SpatialService** | 8013 | Python/FastAPI | PostGIS, H3, CREP geo layers |
| **TemporalService** | 8014 | Python/FastAPI | TimescaleDB, episode store |
| **NLMService** | 8015 | Python/FastAPI | Historical telemetry, Earth2 forecasts |
| **IntentionService** | 8016 | Python/FastAPI | Agent swarm, FingerOrchestrator |
| **ReflectionService** | 8017 | Python/FastAPI | Memory system, KnowledgeGap store |
| **GroundingGate** | integrated | Python module | All above services (inline in consciousness) |

# **Resource Requirements**

**Morgan (solo build, 70% capacity):** \~16 weeks of focused engineering across all four phases. This is aggressive but achievable given the existing consciousness foundation.

**Garret (CTO, supporting):** \~3 weeks of effort for hardware-side geo tagging, H3 integration, and somatosensory cortex.

**Infrastructure:** PostGIS extension on existing Postgres. TimescaleDB container. Additional 4GB RAM on Proxmox for new services. No new cloud costs — all runs on existing infrastructure.

**External APIs:** FingerOrchestrator will need API keys for Claude (existing), GPT-4 ($20-50/mo usage), Gemini (free tier), and optionally Grok (xAI API).

# **Risks & Mitigations**

**Scope creep:** The NLM and Brain Cortex modules can grow infinitely. Mitigation: strict V0 definitions for each — rule-based first, ML later.

**Latency:** Adding Grounding Gate \+ Spatial \+ Temporal \+ NLM before the LLM could slow response time. Mitigation: parallel async processing, cached snapshots, timeouts at each gate (existing pattern from consciousness pipeline).

**Solo builder risk:** Morgan is the only person building this. Mitigation: each phase produces independently valuable services. If phase 3 stalls, phases 1-2 still improve MYCA significantly.

# **Immediate Next Steps**

1\. Create Asana tasks for all Phase 1 items in the MYCA Full Website Integration project.

2\. Define the EP Protobuf schema and commit to mycosoft-mas/schemas/.

3\. Build StateService as the first new container.

4\. Wire GroundingGate into MYCAConsciousness.process\_input() with a feature flag.

5\. Present this plan at the next Board Sync and Engineering Meeting for alignment.