# Nemotron MYCA/AVANI Deployment Topology

**Date:** March 14, 2026  
**Status:** Reference (service placement for Nemotron integration)  
**Related:** `nemotron_myca_rollout_8469ab79.plan.md` §6, VM layout, SPEECH_DUPLEX_MIGRATION_MAR14_2026.md, MINDEX_NEMOTRON_RAG_PLAN_MAR14_2026.md

---

## 1. VM and NAS Roles (Canonical)

| Host | IP | Role | Key services / ports |
|------|-----|------|----------------------|
| **Sandbox** | 192.168.0.187 | Website (Docker), MycoBrain host, optional edge | Website 3000, MycoBrain 8003, Mycorrhizae 8002? |
| **MAS** | 192.168.0.188 | Multi-Agent System, orchestrator, AVANI backend | Orchestrator **8001**, n8n 5678, Ollama 11434, AVANI evaluate |
| **MINDEX** | 192.168.0.189 | Database, vector store, RAG API, embeddings, rerank | Postgres 5432, Redis 6379, Qdrant 6333, **MINDEX API 8000**, RAG/retrieve |
| **GPU node** | 192.168.0.190 | Low-latency voice, Nemotron speech, full-duplex inference | PersonaPlex/Moshi 8998, Bridge 8999, Nemotron ASR/TTS (Phase 2), Nemotron core (optional colocation) |
| **NAS** | e.g. 192.168.0.105 | Shared storage | Model weights, datasets (mounted on VMs as needed) |

---

## 2. Nemotron-Related Service Placement

### 2.1 Nemotron core (LLM)

- **Preferred:** **MAS VM (188)** for orchestration-coupled inference (Brain API, chat, tool use). Model weights can be loaded from **NAS** (e.g. mount at `/opt/mycosoft/models` or similar) so 188 does not need to store large binaries on local disk.
- **Alternative:** **GPU node (190)** if the chosen Nemotron model requires GPU and 188 has no GPU. In that case, MAS orchestrator (188) calls 190 for inference (HTTP or gRPC). Latency trade-off: one extra hop (188 → 190) for each brain request.
- **Roles:** `nemotron-super` (MYCA core), `nemotron-nano` (edge/device), `nemotron-ultra` (future high-depth). Config in `config/models.yaml`; unified routing via LLMRouter / FrontierLLMRouter / LLMBrain.

### 2.2 Nemotron speech (ASR / TTS)

- **Preferred:** **GPU node (190)** for low-latency, interruptible ASR/TTS (see SPEECH_DUPLEX_MIGRATION_MAR14_2026.md). PersonaPlex Bridge and Moshi already target 190; Nemotron speech services can run alongside or replace Moshi.
- **Ports:** Allocate dedicated ports for Nemotron ASR and TTS (e.g. 8990/8991 or as documented in the speech migration). Bridge (8999) connects to these when Phase 2 is enabled.
- **Model storage:** Weights on NAS or 190 local SSD; avoid pulling large models over the network on every cold start.

### 2.3 Nemotron safety (content / AVANI)

- **Preferred:** **MAS VM (188)**. AVANI evaluation is already an authoritative backend service (POST `/api/avani/evaluate-message`). Safety checks (e.g. Nemotron Safety or guardrails) can run in the same process or as a sidecar on 188 so every MYCA ingress (chat, voice, search/chat) passes through one governance path.
- **No separate VM** required for safety unless scale demands it.

### 2.4 RAG, embeddings, rerank (MINDEX)

- **Preferred:** **MINDEX VM (189)**. RAG retrieval (embedding + optional rerank), vector search, and provenance-rich retrieval run in MINDEX API (8000) or dedicated RAG service on 189. Embedding model can run on 189 (CPU or GPU if available) or on 190 with 189 calling 190 for embeddings only.
- **NAS:** If embedding/rerank model weights are large, store on NAS and mount on 189 (or 190) so the process that runs the model can load them.
- **Data:** Postgres, Qdrant, and any RAG collections stay on 189. No duplication of vector data on 190 unless a dedicated “voice RAG” cache is added later.

### 2.5 Edge / Nano (devices, Jetson, etc.)

- **Jetson / on-device:** `nemotron-nano` or smaller models for edge tasks (e.g. device commands, local intent). These are **not** required to run on 187/188/189/190; they run on the device. MAS (188) may still route some requests to “edge” by returning instructions or by the device calling 188 for heavier work.
- **Sandbox (187):** Can run optional edge-facing proxies or caches (e.g. for website or MycoBrain); no mandatory Nemotron service on 187 for the core MYCA/AVANI integration.

---

## 3. NAS Model Storage

- **Purpose:** Single place for large model weights (Nemotron core, speech, embedding, rerank) so VMs do not each store hundreds of GB.
- **Mount points (examples):**
  - **188 (MAS):** `/opt/mycosoft/models` or `C:\path\to\models` (Windows dev) for Nemotron core if inference runs on 188.
  - **189 (MINDEX):** Same path or `/opt/mycosoft/models` for embedding/rerank models if run on 189.
  - **190 (GPU node):** `/opt/mycosoft/models` for Nemotron speech and/or core when inference runs on 190.
- **Convention:** Document actual NAS path and mount in ops runbooks (e.g. `\\192.168.0.105\mycosoft.com\...` or NFS). No hardcoded secrets; use env vars for paths and credentials.

---

## 4. Network and Dependencies

- **Website (187)** → MAS (188) for chat, voice proxy, AVANI; → MINDEX (189) for search/RAG when applicable.
- **MAS (188)** → MINDEX (189) for RAG, memory, worldstate; → 190 for voice/speech when PersonaPlex or Nemotron speech is used.
- **Bridge (190 or local)** → MAS (188) Brain API; → Moshi/Nemotron speech on 190.
- **All VMs** can reach NAS (192.168.0.105 or configured host) for model weights if mounted.

---

## 5. Summary Table (Nemotron roles)

| Role | Primary host | Fallback / notes |
|------|-------------|------------------|
| Nemotron core (super/nano/ultra) | 188 (MAS) | 190 if GPU required and 188 has no GPU |
| Nemotron speech (ASR/TTS) | 190 (GPU node) | — |
| Nemotron safety / AVANI | 188 (MAS) | — |
| RAG / embeddings / rerank | 189 (MINDEX) | Embedding inference on 190 if 189 has no GPU |
| Edge / Nano (on-device) | Device (e.g. Jetson) | — |
| Model weights (shared) | NAS | Mounted on 188, 189, 190 as needed |

---

**Next:** Keep this doc aligned with actual deployment (systemd, Docker, or compose on each VM). Update SYSTEM_REGISTRY and ops runbooks when services are deployed.
