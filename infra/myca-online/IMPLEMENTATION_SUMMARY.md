# MYCA Bootstrap Implementation Summary

## ✅ Implementation Complete

The complete MYCA infrastructure bootstrap system has been implemented and is ready for execution.

## What Was Created

### Core Bootstrap System

```
infra/myca-online/
├── bootstrap_myca.sh           # Main bootstrap script (3 modes: dry-run, apply, verify)
├── README.md                   # Comprehensive operational runbook (600+ lines)
├── IMPLEMENTATION_SUMMARY.md   # This file
├── .gitkeep                    # Directory marker
├── docker/                     # Custom Docker containers
│   ├── Dockerfile.uart         # UART ingest agent container
│   ├── uart_agent.py           # MycoBrain serial reader
│   ├── Dockerfile.gpu          # GPU runner container
│   └── gpu_runner.py           # GPU validation and job runner
├── templates/                  # Vault agent templates (generated at runtime)
└── out/                        # Generated outputs (gitignored)
    ├── .gitignore              # Ensures secrets never committed
    ├── connections.json        # Non-secret endpoints (generated)
    ├── vault_paths.md          # Vault secret documentation (generated)
    ├── audit_schema.json       # Audit log schema (generated)
    ├── verify.sh               # Verification script (generated)
    ├── logs/                   # Bootstrap logs (generated)
    ├── secrets/                # Runtime secrets (gitignored, generated)
    │   ├── .vault-role-id
    │   └── .vault-secret-id
    └── n8n/                    # Speech interface pack (generated)
        ├── myca_endpoints.md
        ├── myca_speech_workflow.json
        └── ui_plan.md
```

### MYCA Core Extensions

```
mycosoft_mas/
├── services/
│   └── infrastructure_ops.py   # Infrastructure operations service (500+ lines)
│       - Proxmox inventory, snapshot, rollback
│       - UniFi topology, client info
│       - GPU testing
│       - UART log tailing
│       - NAS status checking
│       - Audit logging to NAS
└── core/
    ├── routes_infrastructure.py # REST API endpoints (350+ lines)
    │   - /api/status
    │   - /api/proxmox/* (inventory, snapshot, rollback)
    │   - /api/unifi/* (topology, client info)
    │   - /api/gpu/run_test
    │   - /api/uart/tail
    │   - /api/nas/status
    │   - /api/command (generic command interface)
    │   - /api/speak (placeholder for n8n)
    └── myca_main.py            # Updated to include infrastructure router
```

### Docker Compose Files

```
docker-compose.myca.yml         # MYCA infrastructure services (generated at runtime)
├── myca-orchestrator           # Extends main orchestrator with Vault + NAS
├── vault-agent                 # Vault secret injection (profile: vault-agent)
├── uart-agent                  # MycoBrain UART reader (profile: hardware)
└── gpu-runner                  # GPU workload runner (profile: gpu)
```

### Configuration Updates

```
.gitignore                      # Updated with myca-online secret paths
```

## Architecture

### Security Model

1. **No passwords in files**: All secrets entered interactively at runtime
2. **Vault-based secret storage**: KV v2 at `mycosoft/`
3. **AppRole authentication**: Runtime services use AppRole, not root token
4. **Confirmation gates**: Write operations require explicit `confirm: true`
5. **Audit logging**: All actions logged to `/mnt/mycosoft-nas/logs/audit.jsonl`

### Infrastructure Integration

| Component | Integration | Status |
|-----------|-------------|--------|
| **Vault** | Install, init, configure KV v2 + AppRole | ✅ Implemented |
| **Proxmox** | 3 nodes, API token auth, inventory + snapshot ops | ✅ Implemented |
| **UniFi** | UDM API token, topology + client read-only | ✅ Implemented |
| **NAS** | Mount at /mnt/mycosoft-nas, logs + audit | ✅ Implemented |
| **GPU** | RTX 5090, nvidia-docker, CUDA validation | ✅ Implemented |
| **UART** | MycoBrain USB serial, JSON log ingest | ✅ Implemented |
| **MYCA Core** | FastAPI endpoints, ops loops, audit trail | ✅ Implemented |
| **n8n** | Speech interface scaffolds (phase 2) | ✅ Scaffolded |

## Operational Loops Implemented

### 1. Proxmox Operations

```bash
# Inventory
curl -X POST http://localhost:8001/api/proxmox/inventory

# Snapshot (dry-run)
curl -X POST http://localhost:8001/api/proxmox/snapshot \
  -H "Content-Type: application/json" \
  -d '{"node": "build", "vmid": 100, "snapshot_name": "pre-update", "confirm": false}'

# Snapshot (execute)
curl -X POST http://localhost:8001/api/proxmox/snapshot \
  -H "Content-Type: application/json" \
  -d '{"node": "build", "vmid": 100, "snapshot_name": "pre-update", "confirm": true}'
```

### 2. UniFi Operations

```bash
# Topology
curl -X POST http://localhost:8001/api/unifi/topology

# Client info
curl http://localhost:8001/api/unifi/client/aa:bb:cc:dd:ee:ff
```

### 3. GPU Operations

```bash
# Run test
curl -X POST http://localhost:8001/api/gpu/run_test
```

### 4. UART Operations

```bash
# Tail logs
curl http://localhost:8001/api/uart/tail?lines=100
```

### 5. NAS Operations

```bash
# Status
curl http://localhost:8001/api/nas/status
```

### 6. Overall Status

```bash
# Get status of all services
curl http://localhost:8001/api/status
```

## Running the Bootstrap

### Step 1: Dry Run (Check Prerequisites)

```bash
cd /mnt/c/Users/admin2/Desktop/MYCOSOFT/CODE/MAS/mycosoft-mas
bash infra/myca-online/bootstrap_myca.sh dry-run
```

**What it checks**:
- Required commands (curl, docker, jq, vault)
- Vault status
- Proxmox connectivity (3 nodes)
- UniFi connectivity
- NAS mount status
- GPU availability (nvidia-smi)
- UART devices (/dev/ttyUSB*, /dev/ttyACM*)

### Step 2: Apply (Interactive Setup)

```bash
bash infra/myca-online/bootstrap_myca.sh apply
```

**What it does**:
1. Installs Vault (if missing, with confirmation)
2. Initializes Vault (dev mode for now)
3. Configures KV v2 and AppRole
4. Prompts for Proxmox API token
   - Option A: SSH-assisted creation
   - Option B: Manual UI creation + paste
5. Validates Proxmox token across all nodes
6. Prompts for UniFi API key
7. Validates UniFi key
8. Prompts for NAS configuration
   - Protocol (NFS or SMB)
   - IP, share path, credentials
9. Mounts NAS and creates logs directory
10. Validates GPU (if available)
11. Detects UART devices
12. Generates docker-compose.myca.yml
13. Deploys MYCA core services
14. Generates output files
15. Creates verification script
16. Generates n8n integration pack

**Inputs you'll provide**:
- Proxmox API token (or SSH credentials to create)
- UniFi API key
- NAS IP, protocol, path
- NAS credentials (if SMB)
- Confirmation for package installs
- Confirmation for /etc/fstab (optional)

### Step 3: Verify (Check Everything)

```bash
bash infra/myca-online/bootstrap_myca.sh verify
# or
bash infra/myca-online/out/verify.sh
```

**What it verifies**:
- ✓ Vault running and unsealed
- ✓ Proxmox token in Vault and valid
- ✓ UniFi key in Vault and valid
- ✓ NAS mounted and writable
- ✓ GPU available (nvidia-smi)
- ✓ MYCA health endpoint responding
- ✓ MYCA UI endpoint responding

## Expected Endpoints After Bootstrap

Once `apply` completes successfully, you'll have:

| Endpoint | URL | Purpose |
|----------|-----|---------|
| MYCA API | http://localhost:8001 | Main orchestrator API |
| MYCA UI | http://localhost:3001 | Web interface |
| Health | http://localhost:8001/health | Health check |
| Status | http://localhost:8001/api/status | Infrastructure status |
| Proxmox Ops | http://localhost:8001/api/proxmox/* | VM operations |
| UniFi Ops | http://localhost:8001/api/unifi/* | Network operations |
| GPU | http://localhost:8001/api/gpu/run_test | GPU validation |
| UART | http://localhost:8001/api/uart/tail | MycoBrain logs |
| NAS | http://localhost:8001/api/nas/status | Storage status |
| Vault | http://127.0.0.1:8200 | Secret management |

## Confirmation Gates

The following operations require explicit `confirm: true`:

1. **Proxmox snapshot**: Set `confirm: true` in request body
2. **Proxmox rollback**: Set `confirm: true` in request body
3. **Package installation**: Interactive prompt during `apply`
4. **/etc/fstab modification**: Interactive prompt during `apply`

Without `confirm: true`, these operations return dry-run results showing what *would* happen.

## Audit Trail

All operations are logged to `/mnt/mycosoft-nas/logs/audit.jsonl`:

```json
{
  "timestamp": "2025-12-17T10:30:00Z",
  "action": "proxmox.snapshot",
  "actor": "myca-orchestrator",
  "status": "success",
  "details": {
    "node": "build",
    "vmid": 100,
    "snapshot_name": "pre-update"
  }
}
```

## n8n Speech Interface (Phase 2)

The bootstrap generates scaffolds for speech integration in `out/n8n/`:

- **myca_endpoints.md**: API specifications
- **myca_speech_workflow.json**: n8n workflow template
- **ui_plan.md**: Browser UI implementation plan

To activate (manual):
1. Import workflow into n8n
2. Test with curl (no microphone needed)
3. Deploy voice services: `docker-compose --profile voice-premium up -d`
4. Build browser UI per ui_plan.md

## Next Steps After Bootstrap

1. **Test operational loops**:
   ```bash
   curl http://localhost:8001/api/status
   curl -X POST http://localhost:8001/api/proxmox/inventory
   curl -X POST http://localhost:8001/api/unifi/topology
   ```

2. **Review audit logs**:
   ```bash
   tail -f /mnt/mycosoft-nas/logs/audit.jsonl
   ```

3. **Deploy n8n workflow** (when ready for speech):
   - Import `out/n8n/myca_speech_workflow.json`
   - Configure endpoints
   - Test with curl

4. **Set up monitoring**:
   ```bash
   docker-compose --profile observability up -d
   # Grafana: http://localhost:3000
   # Prometheus: http://localhost:9090
   ```

5. **Schedule backups**:
   - Proxmox: snapshot VMs before updates
   - Vault: backup unseal keys securely
   - NAS: verify retention policy

## Production Considerations

### Before Production Use

1. **Vault production mode**:
   - Configure proper storage backend (Consul/etcd/filesystem)
   - Enable TLS
   - Use proper unseal mechanism (Shamir or auto-unseal)
   - Backup unseal keys securely offline

2. **Rotate from dev credentials**:
   - Proxmox: create proper least-privilege user
   - UniFi: rotate API key every 90 days
   - Vault: use production policies

3. **Network security**:
   - Vault: localhost only or internal network
   - Proxmox: internal network + VPN
   - UniFi: internal network + VPN
   - MYCA API: add authentication

4. **Monitoring**:
   - Enable Prometheus/Grafana
   - Set up alerts for failed auth
   - Forward audit logs to SIEM

## Rollback

To undo bootstrap:

```bash
# Stop containers
docker-compose -f docker-compose.yml -f docker-compose.myca.yml down

# Unmount NAS
sudo umount /mnt/mycosoft-nas

# Stop Vault
kill $(cat infra/myca-online/out/vault.pid)

# Remove Proxmox token (optional)
ssh root@192.168.0.202 "pveum token remove myca@pve mas"

# Revoke UniFi key (optional)
# Via UI: Settings → System → Advanced → API Keys → Revoke
```

## Support

See `infra/myca-online/README.md` for:
- Detailed troubleshooting
- Proxmox token creation guides
- UniFi API key creation guides
- Vault operations
- Security best practices

## Status

- ✅ Bootstrap script implemented (1000+ lines)
- ✅ README documentation (600+ lines)
- ✅ Infrastructure operations service (500+ lines)
- ✅ REST API endpoints (350+ lines)
- ✅ Docker containers (UART, GPU)
- ✅ Vault integration
- ✅ Proxmox client (existing, integrated)
- ✅ UniFi client (existing, integrated)
- ✅ NAS mounting
- ✅ GPU validation
- ✅ UART ingest
- ✅ Audit logging
- ✅ Confirmation gates
- ✅ n8n scaffolds
- ✅ Security model (no passwords stored)
- ✅ Gitignore protection

**Ready for execution!**

## Quick Start Commands

```bash
# Navigate to repo
cd /mnt/c/Users/admin2/Desktop/MYCOSOFT/CODE/MAS/mycosoft-mas

# Run dry-run to check prerequisites
bash infra/myca-online/bootstrap_myca.sh dry-run

# If all checks pass, run apply
bash infra/myca-online/bootstrap_myca.sh apply

# After completion, verify
bash infra/myca-online/bootstrap_myca.sh verify

# Test MYCA
curl http://localhost:8001/api/status
curl http://localhost:8001/health
curl -X POST http://localhost:8001/api/proxmox/inventory
```

---

**Implementation completed**: December 17, 2025  
**Total lines of code**: ~3000+  
**Ready for deployment**: Yes ✅
