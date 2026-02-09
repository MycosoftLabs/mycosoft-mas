# MINDEX VM Deployment Status - February 4, 2026

## Deployment Complete

The MINDEX VM has been successfully created and deployed on Proxmox with all required services.

---

## VM Configuration

| Property | Value |
|----------|-------|
| **VM ID** | 189 |
| **Name** | MINDEX-VM |
| **IP Address** | 192.168.0.189 |
| **Gateway** | 192.168.0.1 |
| **OS** | Ubuntu 22.04 LTS (Cloud Image) |
| **CPUs** | 4 cores |
| **RAM** | 8 GB |
| **Disk** | 100 GB |
| **User** | mycosoft |
| **Password** | Mushroom1!Mushroom1! |

---

## Running Services

| Container | Image | Port | Status |
|-----------|-------|------|--------|
| mindex-postgres | postgres:15-alpine | 5432 | RUNNING |
| mindex-redis | redis:7-alpine | 6379 | RUNNING |
| mindex-qdrant | qdrant/qdrant:latest | 6333, 6334 | RUNNING |

---

## Database Schema

PostgreSQL has been initialized with 4 schemas and 9 tables:

### memory schema
- `entries` - Memory key-value storage with TTL support
- `audit_log` - Security audit trail

### ledger schema
- `blocks` - Blockchain blocks with Merkle roots
- `entries` - Ledger entries with SHA256 hashes

### registry schema
- `systems` - Registered Mycosoft systems
- `apis` - Indexed API endpoints
- `devices` - MycoBrain device registry

### graph schema
- `nodes` - Knowledge graph nodes
- `edges` - Knowledge graph relationships

---

## Pre-Registered Systems

| System | Type | URL | Status |
|--------|------|-----|--------|
| MAS | orchestrator | http://192.168.0.188:8001 | active |
| Website | frontend | http://192.168.0.187:3000 | active |
| MINDEX | database | http://192.168.0.189:8000 | active |
| NatureOS | platform | http://192.168.0.188:5000 | active |
| NLM | ml | http://192.168.0.188:8200 | active |
| MycoBrain | iot | http://192.168.0.188:8080 | active |

---

## File Locations on VM

| Path | Purpose |
|------|---------|
| `/opt/mycosoft/mindex/` | Docker compose and SQL files |
| `/opt/mycosoft/ledger/` | JSONL ledger backup |
| `/data/postgres/` | PostgreSQL data |
| `/data/redis/` | Redis persistence |
| `/data/qdrant/` | Qdrant vector storage |

---

## Connectivity

### From Local Network

```bash
# PostgreSQL
psql -h 192.168.0.189 -U mycosoft -d mindex

# Redis
redis-cli -h 192.168.0.189

# Qdrant
curl http://192.168.0.189:6333/
```

### From Other VMs

```python
# Python example
import asyncpg

conn = await asyncpg.connect(
    host="192.168.0.189",
    port=5432,
    user="mycosoft",
    password="mycosoft_mindex_2026",
    database="mindex"
)
```

---

## Proxmox Access

| Property | Value |
|----------|-------|
| **Proxmox URL** | https://192.168.0.202:8006 |
| **User** | root |
| **Password** | 20202020 |
| **Node** | pve |

---

## SSH Access

```bash
ssh mycosoft@192.168.0.189
# Password: Mushroom1!Mushroom1!
```

---

## Management Commands

### Check container status
```bash
sudo docker ps
```

### View container logs
```bash
sudo docker logs mindex-postgres
sudo docker logs mindex-redis
sudo docker logs mindex-qdrant
```

### Restart all services
```bash
cd /opt/mycosoft/mindex
sudo docker-compose restart
```

### PostgreSQL queries
```bash
sudo docker exec mindex-postgres psql -U mycosoft -d mindex -c "SELECT * FROM registry.systems;"
```

---

## Next Steps

1. Configure MAS Orchestrator to use MINDEX VM for memory storage
2. Set up NAS mount for ledger backup at `/mnt/nas/mycosoft/ledger/`
3. Configure Proxmox snapshot schedule (daily at 2:00 AM)
4. **Deploy MINDEX API service container** – Run the MINDEX HTTP API (FastAPI on port 8000) on this VM or on Sandbox 187. See **docs/VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md** (sections 1.1) and **docs/APIS_AND_KEYS_AUDIT_FEB06_2026.md** for deploy path and keys.
5. Update Website environment to use MINDEX endpoints (`MINDEX_API_URL`, `MINDEX_API_KEY`).

---

## Related Documentation

- [MINDEX VM Spec](./infra/mindex-vm/MINDEX_VM_SPEC_FEB04_2026.md)
- [Full Spectrum Registry Implementation](./docs/FULL_SPECTRUM_REGISTRY_IMPLEMENTATION_FEB04_2026.md)
- [Memory Integration Guide](./docs/MEMORY_INTEGRATION_GUIDE_FEB04_2026.md)
