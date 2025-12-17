# MYCA Bootstrap - Operational Runbook

## Overview

This bootstrap system brings MYCA MAS fully online with complete infrastructure integration:

- **Vault**: Secure secret management with AppRole
- **Proxmox**: VM orchestration across 3 nodes
- **UniFi**: Network topology and device management
- **NAS**: Persistent storage for logs and data
- **GPU**: Local RTX 5090 for compute workloads
- **UART**: MycoBrain hardware interface
- **MYCA Core**: Orchestrator with operational loops
- **n8n**: Speech interface integration (scaffolds)

## Quick Start

```bash
# 1. Dry run to check prerequisites
bash infra/myca-online/bootstrap_myca.sh dry-run

# 2. Apply (interactive setup)
bash infra/myca-online/bootstrap_myca.sh apply

# 3. Verify everything is working
bash infra/myca-online/bootstrap_myca.sh verify
```

## Infrastructure Endpoints

| Component | Endpoint | Purpose |
|-----------|----------|---------|
| Proxmox Build | https://192.168.0.202:8006 | Primary build node |
| Proxmox DC1 | https://192.168.0.2:8006 | Datacenter node 1 |
| Proxmox DC2 | https://192.168.0.131:8006 | Datacenter node 2 |
| UniFi UDM | https://192.168.0.1 | Network controller |
| Vault | http://127.0.0.1:8200 | Secret management |
| MYCA API | http://localhost:8001 | MAS orchestrator |
| MYCA UI | http://localhost:3001 | Web interface |
| n8n | http://localhost:5678 | Workflow automation |

## Security Model

### No Passwords Stored

- **All secrets entered at runtime** via interactive prompts
- **Secrets stored ONLY in Vault** (encrypted at rest)
- **No credentials in git** (enforced by .gitignore)
- **AppRole for runtime auth** (no root token in containers)

### Token-Based Access

- **Proxmox**: API token (user: myca@pve, token: mas)
- **UniFi**: API key (non-expiring)
- **Vault**: AppRole with 1h TTL, 4h max

### Confirmation Gates

- Package installation requires confirmation
- /etc/fstab modifications require confirmation
- Proxmox write operations (snapshot/rollback) require explicit confirm flag
- UniFi write operations are read-only by default

## Inputs Required During Apply

When you run `apply`, you will be prompted for:

1. **Proxmox API Token**
   - Option A: SSH access to create automatically
   - Option B: Manual creation in UI, paste token

2. **UniFi API Key**
   - Manual creation in UI
   - Paste key when prompted

3. **NAS Configuration**
   - Protocol (NFS or SMB)
   - IP address
   - Share path
   - Credentials (SMB only)

4. **Optional Confirmations**
   - Install packages (Vault, etc.)
   - Add NAS to /etc/fstab
   - Deploy GPU containers

## What Gets Created

### Directory Structure

```
infra/myca-online/
├── bootstrap_myca.sh          # Main bootstrap script
├── README.md                  # This file
├── templates/                 # Vault agent templates
├── out/                       # Generated outputs (gitignored)
│   ├── connections.json       # Non-secret endpoints
│   ├── vault_paths.md         # Vault secret documentation
│   ├── audit_schema.json      # Audit log schema
│   ├── verify.sh              # Verification script
│   ├── logs/                  # Bootstrap logs
│   ├── secrets/               # Runtime secrets (gitignored)
│   │   ├── .vault-role-id
│   │   └── .vault-secret-id
│   └── n8n/                   # Speech interface pack
│       ├── myca_endpoints.md
│       ├── myca_speech_workflow.json
│       └── ui_plan.md
```

### Docker Compose Files

- `docker-compose.myca.yml` - MYCA infrastructure services
- Extends existing `docker-compose.yml` with:
  - vault-agent (profile: vault-agent)
  - uart-agent (profile: hardware)
  - gpu-runner (profile: gpu)

### Vault Configuration

**KV v2 Mount**: `mycosoft/`

**Secrets**:
| Path | Keys | Description |
|------|------|-------------|
| `mycosoft/proxmox` | token_id, token_secret, hosts | Proxmox API credentials |
| `mycosoft/unifi` | api_key, host | UniFi API credentials |
| `mycosoft/nas` | protocol, ip, share, mount_point | NAS configuration |
| `mycosoft/nas_credentials` | username, password | NAS credentials (SMB only) |

**AppRole**: `myca`
- Policy: `mycosoft` (read-only access to mycosoft/*)
- Token TTL: 1h
- Token Max TTL: 4h

## MYCA Operational Loops

Once MYCA is online, the following ops loops are available via API:

### Status and Inventory

```bash
# Overall status
curl http://localhost:8001/api/status

# Proxmox inventory
curl -X POST http://localhost:8001/api/proxmox/inventory

# UniFi topology
curl -X POST http://localhost:8001/api/unifi/topology
```

### VM Operations (with confirmation gates)

```bash
# Dry-run snapshot (safe)
curl -X POST http://localhost:8001/api/proxmox/snapshot \
  -H "Content-Type: application/json" \
  -d '{"vmid": 100, "node": "build", "confirm": false}'

# Execute snapshot (requires confirm: true)
curl -X POST http://localhost:8001/api/proxmox/snapshot \
  -H "Content-Type: application/json" \
  -d '{"vmid": 100, "node": "build", "snapshot_name": "pre-update", "confirm": true}'
```

### GPU and Hardware

```bash
# Run GPU test
curl -X POST http://localhost:8001/api/gpu/run_test

# Tail UART logs
curl http://localhost:8001/api/uart/tail?lines=100
```

### Audit Trail

All actions are logged to `/mnt/mycosoft-nas/logs/audit.jsonl`:

```json
{
  "timestamp": "2025-12-17T10:30:00Z",
  "action": "proxmox.snapshot",
  "actor": "myca-orchestrator",
  "status": "success",
  "details": {
    "vmid": 100,
    "node": "build",
    "snapshot_name": "pre-update"
  }
}
```

## Verification

### Manual Health Checks

```bash
# Vault
export VAULT_ADDR=http://127.0.0.1:8200
vault status

# Proxmox (via Vault)
vault kv get mycosoft/proxmox

# MYCA Health
curl http://localhost:8001/health

# MYCA UI
curl http://localhost:3001/
```

### Automated Verification

```bash
bash infra/myca-online/out/verify.sh
```

Output:
```
MYCA Bootstrap Verification
============================

✓ Vault running
✓ Vault unsealed
✓ Proxmox token in Vault
✓ UniFi key in Vault
✓ NAS config in Vault
✓ NAS mounted
✓ GPU available
✓ MYCA health endpoint
✓ MYCA UI endpoint

Verification complete!
```

## Starting and Stopping Services

### Start MYCA Core

```bash
cd $REPO_ROOT
docker-compose -f docker-compose.yml up -d
```

### Start with Infrastructure Services

```bash
# With vault-agent
docker-compose -f docker-compose.yml -f docker-compose.myca.yml \
  --profile vault-agent up -d

# With hardware (UART)
docker-compose -f docker-compose.yml -f docker-compose.myca.yml \
  --profile hardware up -d

# With GPU
docker-compose -f docker-compose.yml -f docker-compose.myca.yml \
  --profile gpu up -d

# All profiles
docker-compose -f docker-compose.yml -f docker-compose.myca.yml \
  --profile vault-agent --profile hardware --profile gpu up -d
```

### Stop Services

```bash
docker-compose -f docker-compose.yml -f docker-compose.myca.yml down
```

## n8n Speech Interface (Phase 2)

The bootstrap generates scaffolds for speech integration but does **NOT** execute browser/microphone automation.

### Generated Files

- `out/n8n/myca_endpoints.md` - API endpoint specifications
- `out/n8n/myca_speech_workflow.json` - n8n workflow template
- `out/n8n/ui_plan.md` - UI implementation plan

### Manual Activation Steps

1. **Import n8n workflow**:
   - Open http://localhost:5678
   - Import `out/n8n/myca_speech_workflow.json`

2. **Test without microphone**:
   ```bash
   curl -X POST http://localhost:5678/webhook/myca-speak \
     -H "Content-Type: application/json" \
     -d '{"text": "get proxmox inventory"}'
   ```

3. **Enable voice services**:
   ```bash
   docker-compose -f docker-compose.yml \
     --profile voice-premium up -d elevenlabs-proxy
   ```

4. **Build UI** (see `out/n8n/ui_plan.md` for details)

## Proxmox Token Creation

### Option A: SSH-Assisted (Automated)

The bootstrap script can SSH to Proxmox and run:

```bash
pveum user add myca@pve --comment "MYCA MAS Service Account"
pveum role add MYCA_ROLE --privs "Datastore.AllocateSpace,Datastore.Audit,Pool.Allocate,Sys.Audit,Sys.Modify,VM.Allocate,VM.Audit,VM.Clone,VM.Config.CDROM,VM.Config.CPU,VM.Config.Cloudinit,VM.Config.Disk,VM.Config.HWType,VM.Config.Memory,VM.Config.Network,VM.Config.Options,VM.Monitor,VM.PowerMgmt"
pveum aclmod / --users myca@pve --roles MYCA_ROLE
pveum token add myca@pve mas --privsep 0 --output-format json
```

### Option B: UI-Assisted (Manual)

1. Open https://192.168.0.202:8006
2. Login as root
3. **Create User**:
   - Datacenter → Permissions → Users → Add
   - User: `myca@pve`
   - Comment: `MYCA MAS Service Account`

4. **Create Role**:
   - Datacenter → Permissions → Roles → Create
   - Name: `MYCA_ROLE`
   - Privileges:
     - Datastore: AllocateSpace, Audit
     - Pool: Allocate
     - Sys: Audit, Modify
     - VM: Allocate, Audit, Clone, Config.*, Monitor, PowerMgmt

5. **Assign Permissions**:
   - Datacenter → Permissions → Add
   - Path: `/`
   - User: `myca@pve`
   - Role: `MYCA_ROLE`

6. **Create API Token**:
   - Datacenter → Permissions → API Tokens → Add
   - User: `myca@pve`
   - Token ID: `mas`
   - Privilege Separation: **OFF** (important!)
   - Copy token immediately: `PVE:myca@pve!mas=<secret>`

## UniFi API Key Creation

1. Open https://192.168.0.1
2. Login to UniFi Network
3. **Enable API Access**:
   - Settings → System → Advanced
   - Enable "API Access"

4. **Create API Key**:
   - Settings → System → Advanced → API Keys
   - Create Key
   - Name: `MYCA-MAS`
   - Copy key immediately (non-recoverable)

## Troubleshooting

### Vault is Sealed

After reboot, Vault needs to be unsealed:

```bash
export VAULT_ADDR=http://127.0.0.1:8200
vault operator unseal <key1>
vault operator unseal <key2>
vault operator unseal <key3>
```

**Note**: In dev mode, Vault runs in-memory and doesn't persist. For production, configure proper storage backend.

### Proxmox Token Invalid

Test token manually:

```bash
curl -k -H "Authorization: PVEAPIToken=myca@pve!mas=<secret>" \
  https://192.168.0.202:8006/api2/json/nodes
```

Common issues:
- Token format incorrect (should be `user@realm!tokenid`)
- Privilege separation enabled (should be OFF)
- ACL not applied to root path
- Token expired or revoked

### UniFi API Key Invalid

Test key manually:

```bash
curl -k -H "X-API-Key: <key>" \
  https://192.168.0.1/proxy/network/api/self
```

Common issues:
- API Access not enabled in UniFi settings
- Key revoked
- Network connectivity issues

### NAS Mount Failed

Check connectivity:

```bash
# Ping NAS
ping <nas-ip>

# Check NFS exports
showmount -e <nas-ip>

# Check SMB shares
smbclient -L //<nas-ip> -N
```

Manual mount test:

```bash
# NFS
sudo mount -t nfs <nas-ip>:/path /mnt/test

# SMB
sudo mount -t cifs //<nas-ip>/share /mnt/test -o username=user,password=pass
```

### GPU Not Detected

Check NVIDIA drivers:

```bash
nvidia-smi
docker run --rm --gpus all nvidia/cuda:12.3.0-base-ubuntu22.04 nvidia-smi
```

Install NVIDIA Container Toolkit:

```bash
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### UART Device Not Found

List serial devices:

```bash
ls -l /dev/ttyUSB* /dev/ttyACM*
```

Add user to dialout group:

```bash
sudo usermod -a -G dialout $USER
# Log out and back in
```

### MYCA Not Healthy

Check logs:

```bash
docker-compose -f docker-compose.yml logs mas-orchestrator
```

Check dependencies:

```bash
docker-compose -f docker-compose.yml ps
```

Restart services:

```bash
docker-compose -f docker-compose.yml restart
```

## Rollback

To undo changes:

1. **Stop containers**:
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.myca.yml down
   ```

2. **Unmount NAS**:
   ```bash
   sudo umount /mnt/mycosoft-nas
   # Remove from /etc/fstab if added
   ```

3. **Stop Vault**:
   ```bash
   kill $(cat infra/myca-online/out/vault.pid)
   ```

4. **Remove Proxmox token** (optional):
   ```bash
   ssh root@192.168.0.202 "pveum token remove myca@pve mas"
   ```

5. **Revoke UniFi key** (optional):
   - UniFi UI → Settings → System → Advanced → API Keys → Revoke

## Files That Should NEVER Be Committed

Already in `.gitignore`:

```
infra/myca-online/out/
infra/myca-online/out/secrets/
*.vault-role-id
*.vault-secret-id
*credentials*
*password*
```

## Next Steps

After bootstrap is complete:

1. **Test operational loops**:
   ```bash
   curl http://localhost:8001/api/status
   curl -X POST http://localhost:8001/api/proxmox/inventory
   ```

2. **Review audit logs**:
   ```bash
   tail -f /mnt/mycosoft-nas/logs/audit.jsonl
   ```

3. **Deploy n8n workflow** (when ready for speech interface):
   - Import workflow from `out/n8n/myca_speech_workflow.json`
   - Test with curl before enabling microphone

4. **Set up monitoring**:
   ```bash
   docker-compose -f docker-compose.yml --profile observability up -d
   # Grafana: http://localhost:3000
   # Prometheus: http://localhost:9090
   ```

5. **Schedule backups** (manual for now):
   - Proxmox: snapshot VMs before updates
   - NAS: verify backup retention policy
   - Vault: backup unseal keys securely

## Support and Documentation

- Vault docs: https://www.vaultproject.io/docs
- Proxmox API: https://pve.proxmox.com/pve-docs/api-viewer/
- UniFi API: https://ubntwiki.com/products/software/unifi-controller/api
- Docker Compose: https://docs.docker.com/compose/

## Security Best Practices

1. **Rotate secrets regularly**:
   - Proxmox tokens: every 90 days
   - UniFi keys: every 90 days
   - Vault AppRole secret IDs: on-demand

2. **Use production Vault** (not dev mode):
   - Configure proper storage backend (Consul, etcd, or filesystem)
   - Enable TLS
   - Use proper unseal keys (Shamir or auto-unseal)

3. **Restrict network access**:
   - Vault: localhost only
   - Proxmox: internal network only
   - UniFi: internal network only

4. **Monitor audit logs**:
   - Set up alerts for failed auth attempts
   - Review audit.jsonl regularly
   - Forward logs to SIEM if available

5. **Backup unseal keys**:
   - Store Vault unseal keys in secure offline location
   - Test recovery procedure
   - Document key holders

## License

Copyright © 2025 Mycosoft. All rights reserved.
