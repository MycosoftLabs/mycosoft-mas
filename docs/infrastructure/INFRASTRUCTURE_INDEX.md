# MYCA Infrastructure Implementation Index

This document provides a comprehensive index of all infrastructure components created for the MYCA deployment plan.

## Quick Start

1. **Mount NAS Storage**: `.\scripts\mount_nas.ps1`
2. **Start Development**: `.\scripts\start_dev.ps1 -WithGPU`
3. **Deploy to Production**: `.\scripts\deploy_production.ps1`
4. **Verify Setup**: `.\scripts\verify_storage.ps1`

## Implementation Status

| Phase | Component | Status | Documentation |
|-------|-----------|--------|---------------|
| 1 | UDM Pro Storage | ✅ Complete | [UDM_STORAGE_SETUP.md](./UDM_STORAGE_SETUP.md) |
| 2 | mycocomp Development | ✅ Complete | [MYCOCOMP_DEV_SETUP.md](./MYCOCOMP_DEV_SETUP.md) |
| 3 | Proxmox HA Cluster | ✅ Complete | [PROXMOX_HA_CLUSTER.md](./PROXMOX_HA_CLUSTER.md) |
| 4 | MYCA Core VM | ✅ Complete | [PROXMOX_HA_CLUSTER.md](./PROXMOX_HA_CLUSTER.md) |
| 5 | Database Migration | ✅ Complete | [DATABASE_MIGRATION.md](./DATABASE_MIGRATION.md) |
| 6 | Cloudflare Tunnel | ✅ Complete | [CLOUDFLARE_TUNNEL.md](./CLOUDFLARE_TUNNEL.md) |
| 7 | Website Deployment | ✅ Complete | Scripts in `scripts/` |
| 8 | VLAN Security | ✅ Complete | [VLAN_SECURITY.md](./VLAN_SECURITY.md) |
| 9 | HashiCorp Vault | ✅ Complete | Scripts in `scripts/` |
| 10 | Monitoring Stack | ✅ Complete | [MONITORING_STACK.md](./MONITORING_STACK.md) |
| 11 | Dev-to-Prod Pipeline | ✅ Complete | Scripts in `scripts/` |
| 12 | Azure Failover | ✅ Complete | [AZURE_FAILOVER.md](./AZURE_FAILOVER.md) |

## Directory Structure

```
docs/infrastructure/
├── INFRASTRUCTURE_INDEX.md      # This file
├── UDM_STORAGE_SETUP.md         # NAS configuration
├── MYCOCOMP_DEV_SETUP.md        # Development environment
├── PROXMOX_HA_CLUSTER.md        # Proxmox HA setup
├── DATABASE_MIGRATION.md        # Database to NAS migration
├── CLOUDFLARE_TUNNEL.md         # External access via Cloudflare
├── VLAN_SECURITY.md             # Network segmentation
├── MONITORING_STACK.md          # Prometheus/Grafana/Loki
└── AZURE_FAILOVER.md            # Azure disaster recovery

config/
├── development.env              # Dev environment variables
├── production.env               # Prod environment variables
├── cloudflared/
│   └── config.yml               # Cloudflare Tunnel config
├── nginx/
│   └── mycosoft.conf            # Nginx reverse proxy
└── vault/
    └── vault-config.hcl         # HashiCorp Vault config

scripts/
├── mount_nas.ps1                # Mount UDM Pro storage
├── verify_storage.ps1           # Verify NAS configuration
├── start_dev.ps1                # Start dev environment
├── deploy_production.ps1        # Deploy to production
├── sync_dev_data.ps1            # Sync data between dev/NAS
├── deploy_website.sh            # Website deployment
├── setup_vault.sh               # Vault initialization
├── migrate_databases_to_nas.sh  # Database migration
├── azure_backup_sync.sh         # Azure backup sync
└── proxmox/
    ├── create_myca_core_vm.py   # Create MYCA Core VM
    └── create_agent_template.py # Create agent template
```

## Network Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Internet                                 │
│                             │                                    │
│                    ┌────────┴────────┐                          │
│                    │  Cloudflare     │                          │
│                    │  mycosoft.com   │                          │
│                    └────────┬────────┘                          │
│                             │                                    │
└─────────────────────────────┼────────────────────────────────────┘
                              │
┌─────────────────────────────┼────────────────────────────────────┐
│                    ┌────────┴────────┐                          │
│                    │  UDM Pro        │                          │
│                    │  192.168.0.1    │                          │
│                    │  + 26TB Storage │                          │
│                    └────────┬────────┘                          │
│                             │                                    │
│  ┌──────────────────────────┼──────────────────────────────┐    │
│  │                          │                               │    │
│  │  ┌───────────┐  ┌───────┴───────┐  ┌───────────┐       │    │
│  │  │ mycocomp  │  │ Proxmox       │  │ MycoBrain │       │    │
│  │  │ (Dev)     │  │ HA Cluster    │  │ (IoT)     │       │    │
│  │  │ RTX 5090  │  │               │  │           │       │    │
│  │  └───────────┘  │ ┌───────────┐ │  └───────────┘       │    │
│  │                 │ │ Build     │ │                       │    │
│  │  VLAN 1         │ │ DC1       │ │  VLAN 40             │    │
│  │  192.168.0.x    │ │ DC2       │ │  192.168.40.x        │    │
│  │                 │ └───────────┘ │                       │    │
│  │                 │               │                       │    │
│  │                 │ VLAN 20 (Prod)│                       │    │
│  │                 │ 192.168.20.x  │                       │    │
│  │                 │               │                       │    │
│  │                 │ VLAN 30 (Agent│                       │    │
│  │                 │ 192.168.30.x  │                       │    │
│  └─────────────────┴───────────────┴───────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Service Ports

### Production (VLAN 20)

| Service | IP | Port | Description |
|---------|-----|------|-------------|
| MYCA Core | 192.168.20.10 | 8001 | Main orchestrator API |
| Website | 192.168.20.11 | 3000 | Next.js frontend |
| PostgreSQL | 192.168.20.12 | 5432 | Primary database |
| Redis | 192.168.20.12 | 6379 | Cache |
| Qdrant | 192.168.20.12 | 6333 | Vector database |
| N8N | 192.168.20.10 | 5678 | Workflow automation |
| Vault | 192.168.20.10 | 8200 | Secret management |
| Prometheus | 192.168.20.10 | 9090 | Metrics |
| Grafana | 192.168.20.10 | 3001 | Dashboards |

### Development (mycocomp)

| Service | Port | Description |
|---------|------|-------------|
| MAS Orchestrator | 8001 | Development API |
| PostgreSQL | 5433 | Dev database |
| Redis | 6390 | Dev cache |
| Qdrant | 6345 | Dev vector DB |
| Ollama | 11434 | Local LLM (GPU) |
| Whisper | 8765 | STT (GPU) |
| N8N | 5678 | Workflow dev |
| Dashboard | 3100 | Dev UI |

## Key Files Modified

| File | Changes |
|------|---------|
| `config.yaml` | Added NAS storage paths and environment variables |

## Execution Order

For a clean deployment, execute in this order:

1. **Phase 1: Storage**
   ```powershell
   .\scripts\mount_nas.ps1
   .\scripts\verify_storage.ps1
   ```

2. **Phase 2: Development Environment**
   ```powershell
   .\scripts\start_dev.ps1 -WithGPU
   ```

3. **Phase 3-4: Proxmox Cluster**
   ```bash
   # On Proxmox nodes
   python scripts/proxmox/create_myca_core_vm.py --dry-run
   python scripts/proxmox/create_agent_template.py create --dry-run
   ```

4. **Phase 5: Database Migration**
   ```bash
   # On MYCA Core VM
   sudo ./scripts/migrate_databases_to_nas.sh
   ```

5. **Phase 6-7: Website & Tunnel**
   ```bash
   # On Website VM
   sudo ./scripts/deploy_website.sh
   # Configure Cloudflare Tunnel in dashboard
   ```

6. **Phase 8: Security**
   - Configure VLANs in UniFi dashboard
   - Follow [VLAN_SECURITY.md](./VLAN_SECURITY.md)

7. **Phase 9: Vault**
   ```bash
   sudo ./scripts/setup_vault.sh
   ```

8. **Phase 10: Monitoring**
   ```bash
   docker compose up -d prometheus grafana loki
   ```

9. **Phase 11: Deployment Pipeline**
   ```powershell
   .\scripts\deploy_production.ps1 -DryRun
   ```

10. **Phase 12: Azure Prep**
    ```bash
    az login
    ./scripts/azure_backup_sync.sh
    ```

## Support

For issues with infrastructure setup:

1. Check relevant documentation in `docs/infrastructure/`
2. Review logs in `/mnt/mycosoft/audit/logs/`
3. Contact Morgan via MYCA voice interface
