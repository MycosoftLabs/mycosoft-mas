# MINDEX ETL and Integration Test Report - February 4, 2026

## Executive Summary

The MINDEX VM has been successfully deployed, configured, and tested with full ETL pipeline functionality and integration with the Mycosoft ecosystem.

## Infrastructure Status

### MINDEX VM (192.168.0.189)
| Component | Status | Details |
|-----------|--------|---------|
| **VM** | Running | Proxmox Host: 192.168.0.202, VM ID: 189 |
| **OS** | Ubuntu 22.04 | 4 CPU, 8GB RAM, 100GB Disk |
| **Docker** | Active | 3 containers running |
| **PostgreSQL** | Healthy | Port 5432, User: mycosoft, DB: mindex |
| **Redis** | Healthy | Port 6379, Appendonly enabled |
| **Qdrant** | Healthy | Ports 6333-6334, Vector DB |

### Storage Configuration
| Storage | Type | Capacity | Purpose |
|---------|------|----------|---------|
| **NAS (192.168.0.105)** | CIFS/SMB | 2x 8TB | Ledger backup, Snapshots |
| **Local SSD** | ext4 | 100GB (97GB free) | Primary data |
| **Dream Machine (192.168.0.1)** | Network Device | N/A | Router/Gateway (not storage) |

### NAS Mount Status
- **Mount Path on MINDEX**: Via rsync sync (hourly cron)
- **NAS Path**: `//192.168.0.105/mycosoft.com/mindex/`
- **Sync Script**: `/opt/mycosoft/sync_to_nas.sh`
- **Cron Schedule**: Hourly (0 * * * *)

## Database Status

### Schemas
| Schema | Tables | Purpose |
|--------|--------|---------|
| memory | 2 | Memory entries, Audit log |
| ledger | 2+ | Blockchain ledger, Entries |
| registry | 6+ | System registry |
| graph | 3+ | Knowledge graph |

### Pre-Registered Systems
| ID | Name | Type | URL | Status |
|----|------|------|-----|--------|
| 1 | MAS | orchestrator | http://192.168.0.188:8001 | active |
| 2 | Website | frontend | http://192.168.0.187:3000 | active |
| 3 | MINDEX | database | http://192.168.0.189:8000 | active |
| 4 | NatureOS | platform | http://192.168.0.188:5000 | active |
| 5 | NLM | ml | http://192.168.0.188:8200 | active |
| 6 | MycoBrain | iot | http://192.168.0.188:8080 | active |

### Data Counts (Post-ETL Test)
| Schema | Count |
|--------|-------|
| Memory Entries | 3 |
| Ledger Entries | 1 |
| Registry Systems | 6 |
| Graph Nodes | 0 (pending) |

## ETL Pipeline Test Results

### Phase 1: Memory Insert
- **Status**: PASS
- **Entries Created**: 3
- **Scopes Tested**: system, agent

### Phase 2: Qdrant Vector Store
- **Status**: PASS
- **Collection Created**: mycosoft_knowledge
- **Vector Size**: 384 dimensions
- **Distance Metric**: Cosine

### Phase 3: Ledger Entry
- **Status**: PASS
- **Entry Type**: system_init
- **Hash Recorded**: Yes

### Phase 4: NAS Sync
- **Status**: PASS
- **Sync Time**: ~1 second
- **Data Synced**: ledger/etl_test.log

## Connectivity Test Results

| Source | Target | Status |
|--------|--------|--------|
| MINDEX -> MAS | http://192.168.0.188:8001/health | OK |
| MINDEX -> Website | http://192.168.0.187:3000 | OK |
| MINDEX -> NAS | 192.168.0.105 (via Sandbox) | OK |
| MAS -> MINDEX | PostgreSQL direct | OK |

## Data Paths

### Local Paths (MINDEX VM)
```
/opt/mycosoft/
├── mindex/
│   ├── docker-compose.yml
│   └── init-postgres.sql
├── data/
│   ├── ledger/
│   ├── backups/
│   └── snapshots/
└── sync_to_nas.sh
```

### NAS Paths
```
//192.168.0.105/mycosoft.com/
├── mindex/
│   ├── ledger/       <- Synced from MINDEX
│   ├── backups/      <- Synced from MINDEX
│   ├── snapshots/    <- Synced from MINDEX
│   └── data/         <- Synced from MINDEX
└── website/          <- Existing website assets
```

## Docker Containers

```bash
$ docker ps
CONTAINER ID   IMAGE                  STATUS          PORTS
ae297bbb1bb4   postgres:15-alpine     Up 47 minutes   0.0.0.0:5432->5432/tcp
4e66b668d37d   qdrant/qdrant:latest   Up 47 minutes   0.0.0.0:6333-6334->6333-6334/tcp
77617e9d6755   redis:7-alpine         Up 47 minutes   0.0.0.0:6379->6379/tcp
```

## Access Commands

### SSH Access
```bash
ssh mycosoft@192.168.0.189
# Password: REDACTED_VM_SSH_PASSWORD
```

### PostgreSQL Access
```bash
docker exec -it mindex-postgres psql -U mycosoft -d mindex
```

### Redis CLI
```bash
docker exec -it mindex-redis redis-cli
```

### Manual NAS Sync
```bash
/opt/mycosoft/sync_to_nas.sh
```

## Notes on Dream Machine

The Dream Machine at 192.168.0.1 is a **UniFi Dream Machine** network device (router/gateway), not a storage server. The "26TB" mentioned may refer to:
1. Aggregate storage across all connected devices
2. Total NAS capacity managed through the UniFi ecosystem
3. A separate storage device managed via the Dream Machine

The 26TB is not directly accessible for MINDEX storage. All data storage is handled by:
- Local SSD on MINDEX VM (100GB)
- NAS at 192.168.0.105 (2x 8TB)

## Next Steps

1. [ ] Deploy MINDEX API service for external access
2. [ ] Configure MAS Orchestrator to use MINDEX for persistent memory
3. [ ] Set up Proxmox snapshot schedule (daily at 2:00 AM)
4. [ ] Integrate Knowledge Graph with system topology
5. [ ] Connect Website memory dashboard to MINDEX endpoints

## Conclusion

The MINDEX VM is fully operational with:
- PostgreSQL database with all schemas initialized
- Redis cache for high-speed access
- Qdrant vector database for semantic search
- Hourly sync to NAS for backup
- Full connectivity to MAS, Website, and NAS

All ETL tests passed successfully.
