# OpenViking Memory Integration Plan for MAS + OpenClaw/NemoClaw

**Date:** March 19, 2026
**Status:** Planning
**Author:** MYCA Coding Agent
**Scope:** MAS Memory System + Edge Device Memory (Jetson Orin / Mushroom1 / Hyphae1)

---

## Executive Summary

[OpenViking](https://github.com/volcengine/OpenViking) is ByteDance's open-source "Context Database" for AI agents. It replaces flat vector storage with a **hierarchical file-system paradigm** and **L0/L1/L2 tiered context loading**, dramatically reducing token costs and improving retrieval accuracy.

This plan integrates OpenViking into the Mycosoft ecosystem in two ways:

1. **On-Device (Jetson):** OpenViking runs locally on Jetson Orin devices inside Mushroom1 and Hyphae1 as the memory manager for OpenClaw/NemoClaw agents
2. **MAS Bridge:** A bidirectional sync bridge connects OpenViking's context database to MAS's 6-layer memory system on MINDEX

This hybrid approach gives edge devices fast local memory while MAS maintains centralized knowledge.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    MAS (VM 188)                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  MemoryCoordinator (singleton)                        │   │
│  │  ├── MYCAMemory (6-layer)                             │   │
│  │  ├── A2AMemory (Redis pub/sub)                        │   │
│  │  ├── GraphMemory                                      │   │
│  │  └── OpenVikingBridge  ◄── NEW                        │   │
│  │       ├── sync_from_device(device_id)                 │   │
│  │       ├── push_to_device(device_id, context)          │   │
│  │       └── query_device_memory(device_id, query)       │   │
│  └──────────────────────────────────────────────────────┘   │
│                          │                                   │
│                     REST/gRPC                                │
│                          │                                   │
└──────────────────────────┼───────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│  Mushroom1       │ │  Hyphae1         │ │  Future Devices  │
│  (Jetson Orin)   │ │  (Jetson Orin)   │ │                  │
│  192.168.0.123   │ │  192.168.0.???   │ │                  │
│                  │ │                  │ │                  │
│  ┌────────────┐  │ │  ┌────────────┐  │ │                  │
│  │ OpenViking │  │ │  │ OpenViking │  │ │                  │
│  │ Server     │  │ │  │ Server     │  │ │                  │
│  │ :1933      │  │ │  │ :1933      │  │ │                  │
│  └─────┬──────┘  │ │  └─────┬──────┘  │ │                  │
│        │         │ │        │         │ │                  │
│  ┌─────┴──────┐  │ │  ┌─────┴──────┐  │ │                  │
│  │ OpenClaw/  │  │ │  │ NemoClaw   │  │ │                  │
│  │ NemoClaw   │  │ │  │            │  │ │                  │
│  │ :18789     │  │ │  │ :18789     │  │ │                  │
│  └────────────┘  │ │  └────────────┘  │ │                  │
│  ┌────────────┐  │ │  ┌────────────┐  │ │                  │
│  │ MycoBrain  │  │ │  │ MycoBrain  │  │ │                  │
│  │ Board      │  │ │  │ Board      │  │ │                  │
│  └────────────┘  │ │  └────────────┘  │ │                  │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

---

## Why Hybrid (Both Local + Bridge)

| Concern | Local Only | Bridge Only | Hybrid (Recommended) |
|---------|-----------|-------------|---------------------|
| Latency for on-device agents | Fast (local) | Slow (network) | Fast (local) |
| Token costs | Saved via L0/L1/L2 | No savings | Saved via L0/L1/L2 |
| MAS visibility | None | Full | Full (via sync) |
| Offline resilience | Works offline | Fails offline | Works offline, syncs when online |
| Cross-device knowledge | Siloed | Shared | Shared via MAS bridge |
| Sensor data context | Local only | Central only | Both |

**Recommendation: Hybrid.** OpenClaw/NemoClaw get fast local memory with OpenViking's efficient tiered loading. MAS gets visibility and can share knowledge across all devices via the bridge.

---

## Phase 1: OpenViking on Jetson Devices

### 1.1 Installation on Jetson Orin

OpenViking requires Python 3.10+ (Jetson Orin supports this). It can use **Ollama** as its LLM backend via LiteLLM, which is already relevant since MAS Ollama runs on VM 188.

```bash
# On each Jetson device
pip install openviking --upgrade

# Configure (~/.openviking/ov.conf)
{
  "storage": {
    "workspace": "/home/jetson/openviking_workspace"
  },
  "log": {
    "level": "INFO",
    "output": "/home/jetson/.local/state/openviking.log"
  },
  "embedding": {
    "dense": {
      "provider": "jina",
      "model": "jina-embeddings-v3",
      "api_key": "${JINA_API_KEY}",
      "dimension": 1024
    },
    "max_concurrent": 3
  },
  "vlm": {
    "provider": "litellm",
    "model": "ollama/llama3.2",
    "api_base": "http://192.168.0.188:11434",
    "max_concurrent": 5
  }
}
```

**Key decisions:**
- **Embeddings:** Jina (lightweight, good quality) or local embedding model on Jetson
- **VLM:** Ollama on MAS VM 188 via LiteLLM (Jetson can also run small models locally for offline mode)
- **Storage:** Local filesystem on Jetson SSD

### 1.2 OpenViking Directory Structure for OpenClaw

```
viking://
├── memories/
│   ├── sensor-observations/     # BME688/690 patterns, environmental data
│   ├── task-completions/        # What OpenClaw has done successfully
│   ├── errors-learned/          # Failures and how to avoid them
│   └── device-preferences/      # Calibration, thresholds, behaviors
├── resources/
│   ├── mushroom-cultivation/    # Domain knowledge for the grow environment
│   ├── sensor-calibration/      # BME688 gas resistance baselines
│   ├── mycobrain-protocols/     # How to talk to MycoBrain boards
│   └── mas-agent-context/       # Synced context from MAS agents
├── skills/
│   ├── environmental-monitoring/ # How to read and interpret sensors
│   ├── anomaly-detection/       # Learned anomaly patterns
│   ├── actuator-control/        # GPIO, relay, fan control procedures
│   └── reporting/               # How to report to MAS
└── sessions/
    └── current/                  # Active session context
```

### 1.3 OpenClaw/NemoClaw Integration

OpenClaw already runs on port 18789. Add OpenViking as its memory backend:

```python
# In OpenClaw agent configuration
OPENVIKING_URL = "http://localhost:1933"

# Agent uses viking:// paths to navigate memory
# L0 summaries for quick context loading
# L2 full documents only when deep detail needed
```

### 1.4 Systemd Service

```ini
# /etc/systemd/user/openviking.service
[Unit]
Description=OpenViking Context Database
After=network-online.target
Before=openclaw-gateway.service

[Service]
Type=simple
ExecStart=/home/jetson/.local/bin/openviking-server
Restart=always
RestartSec=5
Environment=OPENVIKING_CONFIG_FILE=/home/jetson/.openviking/ov.conf

[Install]
WantedBy=default.target
```

---

## Phase 2: MAS OpenViking Bridge

### 2.1 New Files

| File | Purpose |
|------|---------|
| `mycosoft_mas/memory/openviking_bridge.py` | Bridge client connecting MAS to device OpenViking instances |
| `mycosoft_mas/memory/openviking_sync.py` | Bidirectional sync logic (scheduled + event-driven) |
| `mycosoft_mas/core/routers/openviking_api.py` | REST API for managing OpenViking device connections |
| `mycosoft_mas/edge/openviking_client.py` | Low-level HTTP client for OpenViking server API |
| `tests/test_openviking_bridge.py` | Tests |

### 2.2 OpenVikingBridge (Core Integration)

```python
# mycosoft_mas/memory/openviking_bridge.py

class OpenVikingBridge:
    """
    Bidirectional bridge between MAS 6-layer memory and
    OpenViking context databases running on edge devices.

    Sync strategy:
    - Device → MAS: Sensor observations, task completions, learned patterns
      are promoted to MAS semantic/episodic layers
    - MAS → Device: Agent knowledge, cultivation protocols, updated models
      are pushed to device viking://resources/
    """

    def __init__(self, coordinator: MemoryCoordinator):
        self.coordinator = coordinator
        self._devices: Dict[str, OpenVikingDeviceConnection] = {}

    async def register_device(self, device_id: str, openviking_url: str):
        """Register an edge device's OpenViking instance."""

    async def sync_from_device(self, device_id: str):
        """Pull new memories/observations from device → MAS semantic layer."""

    async def push_to_device(self, device_id: str, content: Dict, viking_path: str):
        """Push MAS knowledge to device's OpenViking filesystem."""

    async def query_device_memory(self, device_id: str, query: str, tier: str = "L0"):
        """Query a device's OpenViking memory with tiered loading."""

    async def sync_all_devices(self):
        """Periodic sync of all registered devices."""
```

### 2.3 Memory Layer Mapping

| OpenViking Path | MAS Layer | Sync Direction | Notes |
|-----------------|-----------|----------------|-------|
| `viking://memories/sensor-observations/` | Episodic | Device → MAS | Environmental events |
| `viking://memories/task-completions/` | Episodic | Device → MAS | What OpenClaw did |
| `viking://memories/errors-learned/` | Semantic | Device → MAS | Patterns to share across devices |
| `viking://resources/mas-agent-context/` | Semantic | MAS → Device | Knowledge from MAS agents |
| `viking://resources/mushroom-cultivation/` | Semantic | MAS → Device | Domain knowledge updates |
| `viking://skills/` | Procedural | MAS → Device | New procedures/playbooks |
| `viking://sessions/` | Session | No sync | Local only, ephemeral |

### 2.4 Sync Strategy

```
Periodic Sync (every 5 minutes):
  ├── For each registered device:
  │   ├── GET device OpenViking /memories/ (changed since last sync)
  │   ├── Promote important observations → MAS episodic layer
  │   ├── Promote learned patterns → MAS semantic layer
  │   ├── Check MAS for new knowledge relevant to device
  │   └── Push updated resources → device viking://resources/
  │
  └── Cross-device knowledge sharing:
      ├── If Mushroom1 learns something useful
      ├── MAS promotes it to semantic layer
      └── Next sync pushes it to Hyphae1's viking://resources/

Event-Driven Sync:
  ├── Device detects anomaly → immediate push to MAS
  ├── MAS agent learns new protocol → push to relevant devices
  └── Device goes offline → MAS marks device memory as stale
```

### 2.5 REST API Endpoints

```
POST   /api/openviking/devices/register     - Register device OpenViking instance
DELETE /api/openviking/devices/{device_id}   - Unregister device
GET    /api/openviking/devices               - List all registered devices
POST   /api/openviking/sync/{device_id}      - Trigger manual sync
POST   /api/openviking/sync/all              - Sync all devices
POST   /api/openviking/query/{device_id}     - Query device memory (with tier)
POST   /api/openviking/push/{device_id}      - Push content to device
GET    /api/openviking/health                - Bridge health + device status
```

---

## Phase 3: Agent Integration

### 3.1 OpenVikingAgent (New MAS Agent)

A dedicated agent that manages all OpenViking device connections:

```python
class OpenVikingAgent(BaseAgent):
    """Manages OpenViking context databases on edge devices."""

    capabilities = [
        "openviking_device_management",
        "edge_memory_sync",
        "cross_device_knowledge_sharing",
        "context_tier_optimization"
    ]

    async def process_task(self, task):
        match task["type"]:
            case "sync_device": ...
            case "push_knowledge": ...
            case "query_device": ...
            case "optimize_tiers": ...  # Re-tier L0/L1/L2 based on access patterns
```

### 3.2 Existing Agent Updates

- **MycoBrainCoordinator:** Add OpenViking URL to EdgeNode metadata, auto-register on device connect
- **DeviceMemorySync:** Add OpenViking sync alongside existing Postgres device state sync
- **OnDeviceOperator:** Use OpenViking for local context instead of raw file-based state

---

## Phase 4: Advanced Features (Future)

### 4.1 Federated Memory Across Devices

```
Mushroom1 learns: "BME688 gas resistance spike = contamination risk"
  → OpenViking stores in viking://memories/errors-learned/
  → MAS bridge syncs to semantic layer
  → MAS pushes to ALL devices' viking://resources/mas-agent-context/
  → Hyphae1 now knows this pattern without experiencing it
```

### 4.2 L0/L1/L2 Optimization for MAS

Apply OpenViking's tiered loading concept to MAS itself:
- L0: Agent gets 100-token summary of a memory
- L1: 2k-token structural overview
- L2: Full document only when needed

This would reduce MAS LLM token consumption for memory recall operations.

### 4.3 Observable Retrieval Trajectories

Use OpenViking's retrieval trajectory visualization to debug MAS memory issues. When an agent recalls the wrong context, trace the exact path through the viking:// filesystem.

---

## Implementation Order

| Step | Work | Effort | Dependencies |
|------|------|--------|-------------|
| 1 | Install OpenViking on Mushroom1 Jetson | 1-2 hours | SSH access to 192.168.0.123 |
| 2 | Configure OpenViking + create directory structure | 1 hour | Step 1 |
| 3 | Create `openviking_client.py` (low-level HTTP client) | 2 hours | OpenViking API docs |
| 4 | Create `openviking_bridge.py` (MAS memory integration) | 3-4 hours | Step 3 |
| 5 | Create `openviking_sync.py` (bidirectional sync) | 3-4 hours | Step 4 |
| 6 | Create `openviking_api.py` router | 2 hours | Step 4 |
| 7 | Create `OpenVikingAgent` | 2-3 hours | Steps 4-6 |
| 8 | Update MycoBrainCoordinator + DeviceMemorySync | 1-2 hours | Step 4 |
| 9 | Wire into MemoryCoordinator | 1 hour | Step 4 |
| 10 | Tests | 2-3 hours | All above |
| 11 | Deploy to Hyphae1 | 1-2 hours | Step 1 pattern |

**Total estimated effort: ~20-25 hours across phases**

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Jetson resource constraints (RAM/CPU) | OpenViking is lightweight; L0/L1/L2 tiers reduce load |
| Network latency for Ollama VLM calls | Cache embeddings locally; use offline-capable small model as fallback |
| OpenViking API instability (new project) | Pin version; wrap client with retry/fallback to existing MAS memory |
| Data consistency during sync | Use timestamp-based conflict resolution; MAS is source of truth for shared knowledge |
| OpenViking project abandonment | Bridge is thin adapter; can swap backend without changing MAS interfaces |

---

## Decision Points for CEO

1. **Embedding provider for Jetson:** Jina API (fast, costs money) vs. local model on Jetson (free, slower) vs. share MAS Qdrant embeddings?
2. **VLM for OpenViking on Jetson:** Use MAS Ollama (188:11434) vs. run small model locally on Jetson?
3. **Sync frequency:** 5 minutes default, or more/less aggressive?
4. **Which device first:** Mushroom1 (192.168.0.123) or Hyphae1?
5. **Start implementation now or wait for OpenViking to stabilize further?**
