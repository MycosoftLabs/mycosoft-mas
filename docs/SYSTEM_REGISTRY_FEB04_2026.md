# System Registry Documentation
## Created: February 4, 2026

## Overview

The System Registry is a PostgreSQL-backed service that tracks all components of the Mycosoft ecosystem:
- **Systems**: Core platforms (MAS, Website, NatureOS, MINDEX, NLM, MycoBrain)
- **APIs**: All 200+ API endpoints across systems
- **Agents**: AI agents and their capabilities
- **Services**: Background services and workers
- **Devices**: MycoBrain IoT devices
- **Code Files**: Source code index across repositories

## Architecture

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                       System Registry                            â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚                                                                  â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”             â”‚
â”‚  â”‚   Systems   â”‚  â”‚    APIs     â”‚  â”‚   Agents    â”‚             â”‚
â”‚  â”‚   (6+)      â”‚  â”‚   (200+)    â”‚  â”‚   (50+)     â”‚             â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜             â”‚
â”‚                                                                  â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”             â”‚
â”‚  â”‚  Services   â”‚  â”‚   Devices   â”‚  â”‚ Code Files  â”‚             â”‚
â”‚  â”‚   (20+)     â”‚  â”‚   (8+)      â”‚  â”‚  (1000+)    â”‚             â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜             â”‚
â”‚                                                                  â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                              â”‚
                              â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                      PostgreSQL Database                         â”‚
â”‚  Schema: registry                                                â”‚
â”‚  Tables: systems, apis, agents, services, devices, code_files   â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

## API Endpoints

### Systems

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/registry/systems` | GET | List all systems |
| `/api/registry/systems/{name}` | GET | Get system by name |
| `/api/registry/systems` | POST | Register/update system |

### APIs

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/registry/apis` | GET | List APIs (filterable) |
| `/api/registry/apis/count` | GET | Get total API count |
| `/api/registry/apis/index` | POST | Trigger API indexing |
| `/api/registry/apis/index/sync` | POST | Synchronous indexing |

### Agents

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/registry/agents` | GET | List agents |
| `/api/registry/agents` | POST | Register agent |

### Services

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/registry/services` | GET | List services |
| `/api/registry/services` | POST | Register service |
| `/api/registry/services/{name}/health` | POST | Update health |

### Devices

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/registry/devices` | GET | List devices |
| `/api/registry/devices` | POST | Register device |
| `/api/registry/devices/health` | GET | Health summary |
| `/api/registry/devices/firmware` | GET | Firmware report |
| `/api/registry/devices/initialize` | POST | Init known devices |
| `/api/registry/devices/{id}/status` | POST | Update status |

**IoT signing key note (FEB09 2026):**
- Device Ed25519 public keys are expected to be stored as base64 in a registry-accessible location.
- Current contract key: `publicKeyB64` (32-byte Ed25519 public key, base64) in `telemetry.device.metadata` (MINDEX) and/or `registry.devices.metadata`.

### Network Device Registry (Feb 9, 2026)

This new API provides heartbeat-based registration for remote MycoBrain devices.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/devices/register` | POST | Register device via heartbeat |
| `/api/devices` | GET | List all network-registered devices |
| `/api/devices/{device_id}` | GET | Get specific device info |
| `/api/devices/{device_id}` | DELETE | Unregister device |
| `/api/devices/{device_id}/command` | POST | Forward command to remote device |
| `/api/devices/{device_id}/telemetry` | GET | Fetch telemetry from remote device |
| `/api/devices/health` | GET | Device registry health check |

**Router**: `mycosoft_mas/core/routers/device_registry_api.py`
**Registered in**: `mycosoft_mas/core/myca_main.py`

### Network Device Service

| Service | Host | Port | Description |
|---------|------|------|-------------|
| MycoBrain Remote Service | Remote machines | 8003 | Local device manager with heartbeat |

**Heartbeat System**:
- Devices send heartbeats every 30 seconds (configurable)
- Heartbeats include: device_id, host, port, status, connection_type
- Connection types: `tailscale`, `cloudflare`, `lan`
- Devices auto-detected via Tailscale IP or manual configuration

### n8n Workflows API (Feb 18, 2026)

MYCA has full view and full access to n8n workflows. Source of truth: repo `n8n/workflows/*.json`. Sync-both pushes to local (N8N_LOCAL_URL) and cloud (N8N_URL) so production and local dev stay in sync.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/workflows/registry` | GET | Full workflow registry for MYCA (id, name, active, category, webhook_base, source_url, count) |
| `/api/workflows/sync-both` | POST | Sync repo workflows to both local and cloud n8n (body: `{"activate_core": true}` optional) |
| `/api/workflows/list` | GET | List workflows |
| `/api/workflows/health` | GET | n8n health |
| `/api/workflows/stats` | GET | Workflow stats |
| `/api/workflows/{id}` | GET/PUT/DELETE | Get, update, delete workflow |
| `/api/workflows/{id}/activate` | POST | Activate workflow |
| `/api/workflows/{id}/deactivate` | POST | Deactivate workflow |
| `/api/workflows/create` | POST | Create workflow |
| `/api/workflows/sync` | POST | Sync to primary n8n |
| `/api/workflows/export-all` | POST | Export all to repo |

**Router**: `mycosoft_mas/core/routers/n8n_workflows_api.py`  
**Rule**: `.cursor/rules/n8n-management.mdc`  
**Agents**: n8n-workflow, n8n-ops, n8n-workflow-sync

### Code Files

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/registry/code/stats` | GET | Code statistics |
| `/api/registry/code/index` | POST | Trigger indexing |
| `/api/registry/code/index/sync` | POST | Synchronous indexing |

### Statistics & Health

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/registry/stats` | GET | Overall stats |
| `/api/registry/health` | GET | Health check |

## Data Models

### SystemInfo

```python
class SystemInfo(BaseModel):
    id: UUID
    name: str                    # e.g., "MAS", "Website"
    type: SystemType             # mas, website, natureos, mindex, nlm, mycobrain
    url: str                     # e.g., "http://192.168.0.188:8001"
    description: str
    status: str                  # active, inactive, maintenance
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
```

### APIInfo

```python
class APIInfo(BaseModel):
    id: UUID
    system_id: UUID
    path: str                    # e.g., "/api/memory/write"
    method: str                  # GET, POST, PUT, DELETE
    description: str
    tags: List[str]
    request_schema: Dict
    response_schema: Dict
    auth_required: bool
    deprecated: bool
    metadata: Dict[str, Any]
```

### DeviceInfo

```python
class DeviceInfo(BaseModel):
    id: UUID
    device_id: str               # e.g., "sporebase-001"
    name: str                    # e.g., "SporeBase Alpha"
    type: DeviceType             # sporebase, mushroom1, nfc, sensor, gateway
    firmware_version: str
    hardware_version: str
    status: str
    last_seen: datetime
    config: Dict
    telemetry: Dict
    metadata: Dict
```

## Usage Examples

### Python

```python
from mycosoft_mas.registry.system_registry import get_registry

async def example():
    registry = get_registry()
    
    # List all systems
    systems = await registry.list_systems()
    
    # Get specific system
    mas = await registry.get_system("MAS")
    
    # List APIs for a system
    apis = await registry.list_apis(system_name="MAS")
    
    # Get registry statistics
    stats = await registry.get_registry_stats()
    print(f"Total APIs: {stats['apis']}")
    print(f"Total Devices: {stats['devices']}")
```

### HTTP

```bash
# List all systems
curl http://192.168.0.189:8000/api/registry/systems

# Get API count
curl http://192.168.0.189:8000/api/registry/apis/count

# Update device status
curl -X POST "http://192.168.0.189:8000/api/registry/devices/sporebase-001/status?status=online"
```

## Database Schema

```sql
-- Systems table
CREATE TABLE registry.systems (
    id UUID PRIMARY KEY,
    name VARCHAR(100) UNIQUE,
    description TEXT,
    type VARCHAR(50),
    url VARCHAR(512),
    status VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);

-- APIs table
CREATE TABLE registry.apis (
    id UUID PRIMARY KEY,
    system_id UUID REFERENCES registry.systems(id),
    path VARCHAR(512),
    method VARCHAR(10),
    description TEXT,
    tags VARCHAR(255)[],
    auth_required BOOLEAN,
    deprecated BOOLEAN,
    UNIQUE(system_id, path, method)
);

-- Devices table
CREATE TABLE registry.devices (
    id UUID PRIMARY KEY,
    device_id VARCHAR(100) UNIQUE,
    name VARCHAR(100),
    type VARCHAR(50),
    firmware_version VARCHAR(50),
    status VARCHAR(50),
    last_seen TIMESTAMPTZ
);
```

## Indexing

### API Indexing

The API Indexer automatically discovers endpoints from:
1. **OpenAPI specifications** (`/openapi.json`)
2. **Swagger specifications** (`/swagger/v1/swagger.json`)
3. **Known routes** (fallback for systems without OpenAPI)

```python
from mycosoft_mas.registry.api_indexer import index_all_apis

result = await index_all_apis()
# Returns: {"total_apis": 234, "systems": {...}}
```

### Code Indexing

The Code Indexer scans all repositories:
- `mas`: Python files
- `website`: TypeScript/TSX files
- `natureos`: C# files
- `mycobrain`: C++/Arduino files

```python
from mycosoft_mas.registry.code_indexer import index_all_code

result = await index_all_code()
# Returns: {"total_files": 1500, "total_lines": 250000}
```

## Integration with Knowledge Graph

The registry data is automatically synced to the Knowledge Graph:

```
System (MAS) â”€â”€containsâ”€â”€> API (/api/memory/write)
System (MAS) â”€â”€containsâ”€â”€> Agent (MYCA)
System (MycoBrain) â”€â”€managesâ”€â”€> Device (SporeBase)
```

## Files

| File | Purpose |
|------|---------|
| `mycosoft_mas/registry/system_registry.py` | Core registry service |
| `mycosoft_mas/registry/api_indexer.py` | API discovery |
| `mycosoft_mas/registry/code_indexer.py` | Code file indexing |
| `mycosoft_mas/registry/device_registry.py` | Device management |
| `mycosoft_mas/core/routers/registry_api.py` | REST API endpoints |
| `migrations/015_system_registry.sql` | Database schema |

## Related Documentation

- [API Catalog](./API_CATALOG_FEB04_2026.md)
- [Memory Integration Guide](./MEMORY_INTEGRATION_GUIDE_FEB04_2026.md)
- [Cryptographic Integrity](./CRYPTOGRAPHIC_INTEGRITY_FEB04_2026.md)

---

## PhysicsNeMo Integration (Feb 9, 2026)

### Registered Service

| Service | Host | Port | Type | Notes |
|---------|------|------|------|-------|
| PhysicsNeMo Local Service | Dev Machine | 8400 | GPU physics inference | On-demand container: `nvcr.io/nvidia/physicsnemo/physicsnemo:25.06` |

### Registered Agent

| Agent ID | Class | Category | Capabilities |
|----------|-------|----------|--------------|
| `physicsnemo-agent` | `PhysicsNeMoAgent` | scientific | `physics_simulation`, `neural_operator`, `pinn_solver`, `cfd_surrogate`, `gpu_status` |

### Router

| Router File | Prefix | Purpose |
|-------------|--------|---------|
| `mycosoft_mas/core/routers/physicsnemo_api.py` | `/api/physics` | MAS proxy for PhysicsNeMo simulation endpoints |
