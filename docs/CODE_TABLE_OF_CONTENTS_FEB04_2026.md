# Code Table of Contents - Mycosoft Full Spectrum Registry
## Created: February 4, 2026

## Overview

This document provides a complete index of all source code files across the Mycosoft ecosystem, organized by repository and function.

---

## Repository Structure

| Repository | Purpose | Language | File Count |
|------------|---------|----------|------------|
| `mycosoft-mas` | Multi-Agent System | Python | ~400 files |
| `website` | Dashboard & Website | TypeScript/React | ~180 files |
| `NatureOS` | Nature Operating System | C# | ~100 files |
| `MycoBrain` | IoT Firmware | C++/Arduino | ~200 files |
| `NLM` | Nature Learning Models | Python | ~60 files |
| `MINDEX` | Memory & Knowledge | Python | ~50 files |

---

## mycosoft-mas (Multi-Agent System)

### Core Components

```
mycosoft_mas/
â”œâ”€â”€ core/
â”‚   â”œâ”€â”€ __init__.py
â”‚   â”œâ”€â”€ myca_main.py           # FastAPI main application
â”‚   â”œâ”€â”€ orchestrator.py        # Agent orchestration
â”‚   â”œâ”€â”€ routers/
â”‚   â”‚   â”œâ”€â”€ memory_api.py      # Unified memory endpoints
â”‚   â”‚   â”œâ”€â”€ security_audit_api.py  # Security & audit
â”‚   â”‚   â”œâ”€â”€ registry_api.py    # System registry
â”‚   â”‚   â”œâ”€â”€ graph_api.py       # Knowledge graph
â”‚   â”‚   â”œâ”€â”€ voice_api.py       # Voice integration
â”‚   â”‚   â””â”€â”€ mindex_query.py    # MINDEX queries
â”‚   â””â”€â”€ config.py              # Configuration
â”œâ”€â”€ agents/
â”‚   â”œâ”€â”€ v2/
â”‚   â”‚   â”œâ”€â”€ base_agent.py
â”‚   â”‚   â”œâ”€â”€ myca_agent.py      # Main MYCA agent
â”‚   â”‚   â”œâ”€â”€ scientific_agents.py
â”‚   â”‚   â”œâ”€â”€ lab_agents.py
â”‚   â”‚   â””â”€â”€ simulation_agents.py
â”‚   â””â”€â”€ enums/
â”‚       â”œâ”€â”€ agent_status.py
â”‚       â””â”€â”€ task_status.py
```

### Memory & Ledger

```
mycosoft_mas/
â”œâ”€â”€ memory/
â”‚   â”œâ”€â”€ __init__.py
â”‚   â”œâ”€â”€ memory_manager.py      # Core memory management
â”‚   â”œâ”€â”€ persistent_graph.py    # Knowledge graph
â”‚   â”œâ”€â”€ graph_indexer.py       # Auto graph builder
â”‚   â””â”€â”€ vector_store.py        # Qdrant integration
â”œâ”€â”€ ledger/
â”‚   â”œâ”€â”€ __init__.py
â”‚   â”œâ”€â”€ chain.py               # In-memory blockchain
â”‚   â”œâ”€â”€ persistent_chain.py    # PostgreSQL blockchain
â”‚   â””â”€â”€ file_ledger.py         # JSONL backup
```

### Security & Registry

```
mycosoft_mas/
â”œâ”€â”€ security/
â”‚   â”œâ”€â”€ __init__.py
â”‚   â””â”€â”€ integrity_service.py   # Cryptographic integrity
â”œâ”€â”€ registry/
â”‚   â”œâ”€â”€ __init__.py
â”‚   â”œâ”€â”€ system_registry.py     # System/API registry
â”‚   â”œâ”€â”€ api_indexer.py         # API discovery
â”‚   â”œâ”€â”€ code_indexer.py        # Code file indexing
â”‚   â””â”€â”€ device_registry.py     # Device management
```

### Integrations

```
mycosoft_mas/
â”œâ”€â”€ integrations/
â”‚   â”œâ”€â”€ __init__.py
â”‚   â””â”€â”€ unified_memory_bridge.py  # Cross-system memory
â”œâ”€â”€ bio/
â”‚   â”œâ”€â”€ __init__.py
â”‚   â””â”€â”€ biosensor_interface.py
â”œâ”€â”€ natureos/
â”‚   â”œâ”€â”€ __init__.py
â”‚   â””â”€â”€ natureos_client.py
```

### Database Migrations

```
migrations/
â”œâ”€â”€ 001_initial_schema.sql
â”œâ”€â”€ 010_provenance_ledger.sql
â”œâ”€â”€ 013_unified_memory.sql
â”œâ”€â”€ 014_knowledge_graph.sql
â””â”€â”€ 015_system_registry.sql
```

---

## website (Dashboard & Website)

### App Structure (Next.js App Router)

```
website/
â”œâ”€â”€ app/
â”‚   â”œâ”€â”€ layout.tsx
â”‚   â”œâ”€â”€ page.tsx
â”‚   â”œâ”€â”€ natureos/
â”‚   â”‚   â”œâ”€â”€ page.tsx
â”‚   â”‚   â”œâ”€â”€ mas/
â”‚   â”‚   â”‚   â””â”€â”€ topology/
â”‚   â”‚   â”‚       â””â”€â”€ page.tsx   # 3D Agent Topology
â”‚   â”‚   â””â”€â”€ ai-studio/
â”‚   â”‚       â””â”€â”€ page.tsx       # AI Studio Command Center
â”‚   â”œâ”€â”€ api/
â”‚   â”‚   â”œâ”€â”€ agents/
â”‚   â”‚   â”œâ”€â”€ memory/
â”‚   â”‚   â”œâ”€â”€ voice/
â”‚   â”‚   â””â”€â”€ natureos/
```

### Components

```
website/
â”œâ”€â”€ components/
â”‚   â”œâ”€â”€ ui/                    # shadcn/ui components
â”‚   â”œâ”€â”€ mas/
â”‚   â”‚   â”œâ”€â”€ topology/
â”‚   â”‚   â”‚   â”œâ”€â”€ agent-topology-3d.tsx
â”‚   â”‚   â”‚   â”œâ”€â”€ memory-monitor.tsx
â”‚   â”‚   â”‚   â”œâ”€â”€ memory-dashboard.tsx
â”‚   â”‚   â”‚   â””â”€â”€ layout-manager.tsx
â”‚   â”‚   â””â”€â”€ agent-card.tsx
â”‚   â”œâ”€â”€ voice/
â”‚   â”‚   â””â”€â”€ voice-interface.tsx
â”‚   â””â”€â”€ natureos/
â”‚       â”œâ”€â”€ device-grid.tsx
â”‚       â””â”€â”€ telemetry-chart.tsx
```

### Lib/Utils

```
website/
â”œâ”€â”€ lib/
â”‚   â”œâ”€â”€ memory/
â”‚   â”‚   â””â”€â”€ client.ts          # Memory API client
â”‚   â”œâ”€â”€ api/
â”‚   â”‚   â””â”€â”€ mas-client.ts
â”‚   â””â”€â”€ utils.ts
```

---

## NatureOS (C# Backend)

### Core API

```
NatureOS/
â”œâ”€â”€ src/
â”‚   â”œâ”€â”€ core-api/
â”‚   â”‚   â”œâ”€â”€ Controllers/
â”‚   â”‚   â”‚   â”œâ”€â”€ DevicesController.cs
â”‚   â”‚   â”‚   â”œâ”€â”€ TelemetryController.cs
â”‚   â”‚   â”‚   â””â”€â”€ CommandsController.cs
â”‚   â”‚   â”œâ”€â”€ Services/
â”‚   â”‚   â”‚   â”œâ”€â”€ DeviceService.cs
â”‚   â”‚   â”‚   â”œâ”€â”€ TelemetryService.cs
â”‚   â”‚   â”‚   â””â”€â”€ MemoryBridgeService.cs
â”‚   â”‚   â””â”€â”€ Models/
â”‚   â”‚       â”œâ”€â”€ Device.cs
â”‚   â”‚       â””â”€â”€ TelemetryData.cs
â”‚   â”œâ”€â”€ protocol/
â”‚   â”‚   â”œâ”€â”€ MycorrhizaeProtocol.cs
â”‚   â”‚   â””â”€â”€ MessageTypes.cs
```

---

## MycoBrain (IoT Firmware)

### Arduino/ESP32

```
MycoBrain/
â”œâ”€â”€ firmware/
â”‚   â”œâ”€â”€ sporebase/
â”‚   â”‚   â”œâ”€â”€ sporebase.ino      # Main firmware
â”‚   â”‚   â”œâ”€â”€ sensors.h
â”‚   â”‚   â”œâ”€â”€ wifi_manager.h
â”‚   â”‚   â””â”€â”€ api_client.h
â”‚   â”œâ”€â”€ mushroom1/
â”‚   â”‚   â”œâ”€â”€ mushroom1.ino
â”‚   â”‚   â””â”€â”€ display.h
â”‚   â””â”€â”€ shared/
â”‚       â”œâ”€â”€ config.h
â”‚       â””â”€â”€ telemetry.h
```

---

## NLM (Nature Learning Models)

### Model Training

```
NLM/
â”œâ”€â”€ models/
â”‚   â”œâ”€â”€ nature_base.py
â”‚   â”œâ”€â”€ smell_classifier.py
â”‚   â””â”€â”€ growth_predictor.py
â”œâ”€â”€ training/
â”‚   â”œâ”€â”€ trainer.py
â”‚   â”œâ”€â”€ dataset_loader.py
â”‚   â””â”€â”€ evaluation.py
â”œâ”€â”€ inference/
â”‚   â”œâ”€â”€ server.py
â”‚   â””â”€â”€ client.py
```

---

## Infrastructure

### Docker

```
mycosoft-mas/
â”œâ”€â”€ docker/
â”‚   â”œâ”€â”€ agents/
â”‚   â”‚   â””â”€â”€ docker-compose.all-agents.yml
â”‚   â”œâ”€â”€ grafana/
â”‚   â”œâ”€â”€ postgres/
â”‚   â””â”€â”€ redis/
â”œâ”€â”€ infra/
â”‚   â””â”€â”€ mindex-vm/
â”‚       â”œâ”€â”€ docker-compose.yml
â”‚       â”œâ”€â”€ init-postgres.sql
â”‚       â”œâ”€â”€ prometheus.yml
â”‚       â””â”€â”€ MINDEX_VM_SPEC_FEB04_2026.md
```

### Configuration

```
mycosoft-mas/
â”œâ”€â”€ config/
â”‚   â”œâ”€â”€ default.yaml
â”‚   â”œâ”€â”€ production.yaml
â”‚   â””â”€â”€ agents.yaml
â”œâ”€â”€ prometheus/
â”‚   â””â”€â”€ prometheus.yml
â”œâ”€â”€ grafana/
â”‚   â”œâ”€â”€ dashboards/
â”‚   â””â”€â”€ provisioning/
```

---

## Key Files Quick Reference

### Memory System

| File | Purpose |
|------|---------|
| `mycosoft_mas/core/routers/memory_api.py` | Main memory API |
| `mycosoft_mas/memory/persistent_graph.py` | Knowledge graph |
| `mycosoft_mas/ledger/persistent_chain.py` | Blockchain ledger |
| `mycosoft_mas/security/integrity_service.py` | Crypto integrity |

### Registry System

| File | Purpose |
|------|---------|
| `mycosoft_mas/registry/system_registry.py` | Core registry |
| `mycosoft_mas/registry/api_indexer.py` | API discovery |
| `mycosoft_mas/registry/device_registry.py` | Device tracking |

### Frontend

| File | Purpose |
|------|---------|
| `website/components/mas/topology/memory-dashboard.tsx` | Memory UI |
| `website/app/natureos/ai-studio/page.tsx` | AI Studio |
| `website/lib/memory/client.ts` | Memory client |

---

## Related Documentation

- [System Registry](./SYSTEM_REGISTRY_FEB04_2026.md)
- [API Catalog](./API_CATALOG_FEB04_2026.md)
- [Memory Integration Guide](./MEMORY_INTEGRATION_GUIDE_FEB04_2026.md)
- [Cryptographic Integrity](./CRYPTOGRAPHIC_INTEGRITY_FEB04_2026.md)
