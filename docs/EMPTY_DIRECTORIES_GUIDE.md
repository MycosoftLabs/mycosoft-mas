# Empty Directories Guide

**Purpose**: This document explains why certain directories in `mycosoft-mas` are empty and where the actual code resides.

---

## Overview

The `mycosoft-mas` repository serves as an **integration layer** connecting multiple separate repositories. Many directories are intentionally empty because the actual code lives elsewhere.

---

## Directory Mapping

| Empty Directory | Actual Code Location | Purpose |
|-----------------|---------------------|---------|
| `agents/` | Python MAS orchestrator (various worktrees) | 42+ AI agent implementations |
| `services/` | `MINDEX/mindex`, `NATUREOS/NatureOS` | Backend services |
| `mycosoft_mas/` | MAS worktrees with Python package | Core Python package |
| `orchestrator-myca/` | Merged into components + n8n | MYCA orchestrator |
| `unifi-dashboard/` | `components/mas-dashboard.tsx` | UniFi-style dashboard |
| `docker/` | Root Dockerfiles + per-repo compose | Docker configurations |
| `n8n/` | n8n cloud + local instances | Workflow automation |
| `infra/` | `platform-infra/`, `NATUREOS/infrastructure/` | Infrastructure as code |
| `data/` | Runtime data (not committed) | Application data |
| `WEBSITE/` | `WEBSITE/website` | Production website |
| `docs/agents/` | Agent code in orchestrator | Agent documentation |

---

## agents/

**Purpose**: Contains agent definitions for the 42+ MAS agents.

**Why Empty**: Agent implementations are in the Python MAS orchestrator package.

**Actual Locations**:
- MAS worktrees containing `mycosoft_mas/` package
- Configuration: `config/mas_config.json`

**Agent Categories**:
- Core: MYCA Orchestrator, Project Manager, Dashboard
- Financial: Mercury Banking, Stripe Integration
- Mycology: Species Classifier, Research Agent
- DAO: MycoDAO, IP Tokenization
- Communication: Voice, Email, SMS
- Infrastructure: Device Manager, Network Monitor

---

## services/

**Purpose**: Backend service implementations.

**Why Empty**: Services are in their own repositories.

**Service Locations**:

| Service | Repository | Port |
|---------|------------|------|
| MINDEX API | `MINDEX/mindex` | 8000 |
| Website | `WEBSITE/website` | 3000 |
| NatureOS | `NATUREOS/NatureOS` | Azure |
| MycoBrain | `mycobrain/` | 8003 |

---

## mycosoft_mas/

**Purpose**: Core Python package for MAS orchestrator.

**Why Empty**: Package lives in separate Python project.

**Expected Structure**:
```
mycosoft_mas/
├── __init__.py
├── agents/           # Agent implementations
├── services/         # Background services
├── core/             # Orchestration
└── utils/            # Utilities
```

---

## orchestrator-myca/

**Purpose**: MYCA cognitive agent orchestrator.

**Why Empty**: Components merged into main app.

**Actual Locations**:
- `components/myca-dashboard-unifi.tsx`
- `components/myca-dashboard.tsx`
- n8n workflows for orchestration

---

## unifi-dashboard/

**Purpose**: UniFi-style network dashboard for MAS.

**Why Empty**: Dashboard merged into components.

**Component Files**:
- `components/mas-dashboard.tsx` - Main dashboard
- `components/mas-topology-view.tsx` - Topology
- `components/mas-sidebar.tsx` - Sidebar
- `components/mas-navigation.tsx` - Navigation
- `components/mas-search-bar.tsx` - Search
- `components/mas-entity-modal.tsx` - Entity details

---

## docker/

**Purpose**: Docker configurations.

**Why Empty**: Dockerfiles at root + per-repo compose.

**Docker Files**:
- `Dockerfile` - Main
- `Dockerfile.dev` - Development
- `Dockerfile.next` - Next.js
- `Dockerfile.orchestrator` - Orchestrator
- `Dockerfile.elevenlabs` - ElevenLabs

**Docker Compose**:
- `MINDEX/mindex/docker-compose.yml`
- `NATUREOS/NatureOS/docker-compose.yml`

---

## n8n/

**Purpose**: n8n workflow definitions.

**Why Empty**: Workflows in n8n cloud/local instances.

**n8n Instances**:
- Local: http://localhost:5678
- Cloud: https://mycosoft.app.n8n.cloud

**Import/Export**:
```bash
.\scripts\import_n8n_workflows.ps1
```

---

## infra/

**Purpose**: Infrastructure as code.

**Why Empty**: Infrastructure in dedicated repos.

**Actual Locations**:
- `platform-infra/` - General infrastructure
- `NATUREOS/NatureOS/infrastructure/` - Azure Bicep
- `scripts/proxmox/` - Proxmox scripts

---

## data/

**Purpose**: Runtime application data.

**Why Empty**: Data is runtime-generated, not committed.

**Data Locations**:
- PostgreSQL: Docker container
- NAS: UniFi NAS (27TB)
- Vector DB: Qdrant
- Cache: Redis

---

## WEBSITE/

**Purpose**: Pointer to production website.

**Why Empty**: Website is separate repository.

**Actual Location**:
```
C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website
```

---

## How to Contribute

1. **For agents**: Add to Python MAS orchestrator
2. **For services**: Create in appropriate service repo
3. **For UI**: Add to `components/` in this repo
4. **For infrastructure**: Add to `platform-infra/`
5. **For website**: Modify `WEBSITE/website`

---

## Related Documents

- [Master Architecture](./MASTER_ARCHITECTURE.md)
- [Port Assignments](../PORT_ASSIGNMENTS.md)
- [System Integration Guide](./SYSTEM_INTEGRATION_GUIDE.md)

---

*Last Updated: 2026-01-10*
