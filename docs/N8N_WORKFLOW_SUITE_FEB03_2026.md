# n8n Workflow Suite - February 3, 2026

## Executive Summary

Comprehensive n8n workflow suite for MYCA, PersonaPlex, science, Earth 2 CREP simulator, agents, NLM models, security, and dashboards.

---

## New Workflows Created

### 40. PersonaPlex Voice Gateway
**Path**: `/personaplex/voice`
**Purpose**: Route voice/text from PersonaPlex to MYCA orchestrator

Features:
- Parse voice input (transcript, audio, session)
- Route to MAS VM orchestrator
- Track latency metrics
- Return formatted response with actions taken

```json
POST /webhook/personaplex/voice
{
  "transcript": "What is your name?",
  "session_id": "voice_123",
  "voice_id": "NATURAL_F2",
  "modality": "voice"
}
```

---

### 41. Memory Manager
**Path**: `/myca/memory`
**Purpose**: CRUD operations for MYCA memory system

Operations:
- `write`: Store data in memory scope
- `read`: Retrieve data from memory
- `search`: Semantic search across memory
- `delete`: Remove data from memory

Scopes:
- conversation, session, user, system, agent, workflow, semantic, vector

```json
POST /webhook/myca/memory
{
  "operation": "write",
  "scope": "conversation",
  "namespace": "session_123",
  "key": "user_preference",
  "value": {"theme": "dark"}
}
```

---

### 42. Science Research Hub
**Path**: `/science/research`
**Purpose**: Coordinate scientific computing modules

Modules:
| Module | Actions |
|--------|---------|
| mycology | species_lookup, genome_analysis, cultivation_protocol, network_topology |
| protein | structure_predict, folding_simulate, docking_analyze, alphafold_query |
| chemistry | compound_search, reaction_predict, synthesis_plan, toxicity_check |
| bioinformatics | sequence_align, blast_search, phylogenetic_tree, gene_expression |
| simulation | mycelium_grow, network_propagate, signal_flow, optimization |
| mindex | species_search, taxonomy_lookup, property_query, image_search |

```json
POST /webhook/science/research
{
  "module": "protein",
  "action": "structure_predict",
  "params": {"sequence": "MKFLILLFNILCLFPVLAADNHGVGPQGAS..."}
}
```

---

### 43. Earth 2 CREP Simulator
**Path**: `/earth2/crep`
**Purpose**: Cellular Resilient Earth Protocol simulations

Simulation Types:
- **mycelium_network**: Simulate mycelium growth and signal propagation
- **soil_ecology**: Model soil ecosystem with fungi, bacteria, roots
- **climate_impact**: Climate effects on fungal distribution
- **network_topology**: Analyze network optimization
- **decomposition**: Organic matter decomposition modeling
- **symbiosis**: Plant-fungi symbiotic relationships
- **spore_dispersal**: Spore dispersal patterns

Topologies:
- mesh, tree, hub_spoke, random, small_world, scale_free

Actions:
- `run`: Execute simulation
- `status`: Get running simulations
- `analyze`: Analyze results
- `visualize`: Generate visualizations

```json
POST /webhook/earth2/crep
{
  "simulation": "mycelium_network",
  "action": "run",
  "params": {
    "substrate": "wood_chips",
    "temperature": 22,
    "humidity": 85,
    "time_steps": 1000
  }
}
```

---

### 44. Agent Orchestrator
**Path**: `/agents/orchestrate`
**Purpose**: Manage 227+ specialized AI agents

Categories (14):
| Category | Count | Examples |
|----------|-------|----------|
| Core | 12 | myca_orchestrator, task_router, memory_manager |
| Financial | 18 | treasury_manager, crypto_portfolio, dao_treasury |
| Mycology | 24 | species_identifier, genome_analyzer, cultivation_planner |
| Scientific | 20 | hypothesis_generator, experiment_designer, data_collector |
| DAO | 15 | proposal_drafter, voting_coordinator, governance_analyzer |
| Communications | 16 | email_composer, discord_moderator, community_manager |
| Data | 18 | data_ingester, etl_pipeline_manager, backup_manager |
| Infrastructure | 22 | proxmox_manager, docker_orchestrator, network_monitor |
| Simulation | 16 | mycelium_simulator, protein_folder, monte_carlo_sampler |
| Security | 18 | authentication_manager, anomaly_detector, encryption_manager |
| Integrations | 20 | api_gateway, webhook_manager, database_connector |
| Devices | 14 | mushroom1_controller, petraeus_interface, mycobrain_processor |
| Chemistry | 12 | compound_searcher, reaction_predictor, synthesis_planner |
| NLM | 12 | text_embedder, semantic_searcher, generation_coordinator |

Actions:
- `list`: List agents (by category or all)
- `invoke`: Call specific agent
- `status`: Get agent status
- `delegate`: Delegate task to multiple agents

```json
POST /webhook/agents/orchestrate
{
  "action": "invoke",
  "agent_id": "species_identifier",
  "task": "identify_species",
  "params": {"image_url": "https://..."}
}
```

---

### 45. NLM Model Hub
**Path**: `/nlm/models`
**Purpose**: Neural Language Model coordination

Model Categories:

**Local Models** (RTX 5090):
- moshi_7b (voice)
- llama3_8b (text)
- whisper_large (STT)
- coqui_tts (TTS)

**Cloud Models**:
- gemini_pro, gemini_flash (Google)
- gpt4_turbo (OpenAI)
- claude_opus (Anthropic)
- elevenlabs (TTS)

**Specialized Models**:
- alphafold, esm2, colabfold, rosettafold (Protein)
- fungal_bert (Mycology)
- species_vit (Vision)

Protocols:
- text_generation: greedy, beam_search, sampling, nucleus, contrastive
- embedding: mean_pooling, cls_token, weighted
- voice: streaming, batch, real_time, duplex
- protein: monomer, complex, multimer, template_free

Tools:
- prompt_engineering: template_builder, few_shot_manager, chain_of_thought
- evaluation: perplexity, bleu, rouge, bert_score
- optimization: quantization, pruning, distillation, lora
- deployment: onnx_export, tensorrt, vllm, triton

```json
POST /webhook/nlm/models
{
  "action": "generate",
  "model": "llama3_8b",
  "prompt": "Explain fungal network topology",
  "params": {"temperature": 0.7, "max_tokens": 500}
}
```

---

### 46. Genetic Crypto Security Hub
**Path**: `/security/genetic-crypto`
**Purpose**: DNA-based cryptography and biosecurity

Modules:

**Genetic Crypto**:
- dna_encryption/decryption
- dna_key_generation
- dna_signature
- dna_steganography
- mutation_resistant_encoding
- Algorithms: DNAC-256, BioRSA, SequenceAES, MutationProof-128

**Biosecurity**:
- sample_chain_of_custody
- contamination_detection
- bsl_compliance
- pathogen_screening
- dual_use_monitoring
- Compliance: BSL-1/2/3, IBC, DURC, SELECT-AGENT

**CREP Topology Security**:
- network_encryption
- topology_integrity
- node_authentication
- signal_integrity
- sybil_resistance
- partition_detection
- Protocols: CREPAuth, TopoSign, NodeTrust, SignalSeal

**RBAC**:
- role_management
- permission_assignment
- access_audit
- Roles: admin, researcher, operator, viewer, auditor, guardian

**Encryption**:
- at_rest_encryption, in_transit_encryption
- key_management, key_rotation
- hardware_security_module
- quantum_resistant
- Algorithms: AES-256-GCM, ChaCha20-Poly1305, KYBER-1024, DILITHIUM-3

**Audit**:
- activity_logging
- anomaly_detection
- compliance_reporting
- forensic_analysis
- Standards: SOC2, ISO27001, HIPAA, GDPR, NIST

```json
POST /webhook/security/genetic-crypto
{
  "module": "genetic_crypto",
  "action": "encrypt",
  "params": {"data": "secret message", "algorithm": "DNAC-256"}
}
```

---

### 47. Dashboard Integrations Hub
**Path**: `/dashboard/data`
**Purpose**: Aggregate data for all dashboards

Dashboards:
| Dashboard | Widgets |
|-----------|---------|
| overview | system_health, agent_status, recent_activity, alerts |
| myca | conversations, voice_metrics, memory_usage, agent_invocations |
| scientific | experiments, simulations, publications, datasets |
| infrastructure | vms, containers, network, storage |
| crep | network_graph, node_status, signal_flow, resilience |
| mindex | species_count, recent_additions, search_stats, data_quality |
| devices | device_status, telemetry, alerts, maintenance |
| security | access_log, threats, compliance, encryption |

```json
GET /webhook/dashboard/data?dashboard=myca&range=24h
```

---

## Workflow Summary

| # | Workflow | Webhook Path | Purpose |
|---|----------|--------------|---------|
| 40 | PersonaPlex Voice Gateway | /personaplex/voice | Voice/text routing |
| 41 | Memory Manager | /myca/memory | Memory CRUD |
| 42 | Science Research Hub | /science/research | Scientific computing |
| 43 | Earth 2 CREP Simulator | /earth2/crep | CREP simulations |
| 44 | Agent Orchestrator | /agents/orchestrate | Agent management |
| 45 | NLM Model Hub | /nlm/models | LLM coordination |
| 46 | Genetic Crypto Security | /security/genetic-crypto | Security operations |
| 47 | Dashboard Integrations | /dashboard/data | Dashboard data |

---

## Total Workflow Count

- **Existing workflows**: 46
- **New workflows added**: 8
- **Total workflows**: 54

---

## Deployment

To import all workflows:

1. Go to http://192.168.0.188:5678
2. Login: morgan@mycosoft.org / REDACTED_VM_SSH_PASSWORD
3. Import each JSON file from `n8n/workflows/`
4. Activate each workflow

Or use the n8n API:

```bash
curl -X POST http://192.168.0.188:5678/api/v1/workflows \
  -H "Content-Type: application/json" \
  -H "X-N8N-API-KEY: your-api-key" \
  -d @n8n/workflows/40_personaplex_voice_gateway.json
```

---

*Document created: February 3, 2026*
