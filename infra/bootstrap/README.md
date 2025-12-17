# Mycosoft Infrastructure Bootstrap

Interactive bootstrap for setting up Mycosoft's infrastructure: **Proxmox**, **UniFi UDM**, **NAS**, and **HashiCorp Vault**.

---

## ⚠️ SECURITY NOTICE - PASSWORD ROTATION REQUIRED

**If passwords were ever shared in chat, logs, or exposed in any way:**

### Immediate Actions Required

1. **Rotate Proxmox root passwords** on each node:
   ```bash
   # SSH to each Proxmox node and run:
   passwd
   ```
   - Build Node: `192.168.0.202`
   - DC1: `192.168.0.2`
   - DC2: `192.168.0.131`

2. **Rotate WiFi password** for SSID `Myca` in UniFi:
   - Open: https://192.168.0.1
   - Navigate to: Settings → WiFi → Myca → Edit
   - Generate a new strong password

3. **Rotate any exposed service account passwords**

4. **After API tokens are configured**, disable SSH password auth:
   ```bash
   # On each Proxmox node:
   sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
   systemctl restart sshd
   ```

---

## Overview

This bootstrap automates secure setup of:

| Component | IPs | Purpose |
|-----------|-----|---------|
| **Proxmox Build** | 192.168.0.202:8006 | Primary VM build node |
| **Proxmox DC1** | 192.168.0.2:8006 | Datacenter node 1 |
| **Proxmox DC2** | 192.168.0.131:8006 | Datacenter node 2 |
| **UniFi UDM** | 192.168.0.1:443 | Network management |
| **NAS** | (user-provided) | Shared storage |
| **Vault** | 127.0.0.1:8200 | Secret management |

## Security Model

- **No passwords stored in files or git** - Ever
- **All secrets entered at runtime** - Interactive prompts
- **Secrets stored ONLY in Vault** - Encrypted at rest
- **AppRole for MYCA** - No root token in configs
- **Token-based API auth** - No password auth for services

## Prerequisites

- Ubuntu/Debian Linux (or compatible)
- Docker installed and running
- Network access to infrastructure IPs
- SSH access (optional, for automated Proxmox setup)

## Usage

### Dry Run (Check Only)

```bash
./infra/bootstrap/bootstrap_mycosoft.sh --dry-run
```

Validates connectivity and prerequisites without making changes.

### Apply (Full Setup)

```bash
./infra/bootstrap/bootstrap_mycosoft.sh --apply
```

Interactive setup that:
1. Installs Vault
2. Initializes/unseals Vault
3. Creates AppRole for MYCA
4. Guides you through Proxmox token creation
5. Guides you through UniFi API key creation
6. Mounts NAS storage
7. Generates configuration files

### Verify (Re-check)

```bash
./infra/bootstrap/bootstrap_mycosoft.sh --verify
# or directly:
./infra/bootstrap/out/verify.sh
```

## What Gets Created

### Vault Configuration

| Item | Description |
|------|-------------|
| KV v2 mount | `mycosoft/` |
| Policy | `mycosoft` (read-only for MYCA) |
| AppRole | `myca` with 1h TTL tokens |
| Role ID | `~/.mycosoft-vault-role-id` |
| Secret ID | `~/.mycosoft-vault-secret-id` |

### Vault Secret Paths

| Path | Contents |
|------|----------|
| `mycosoft/proxmox` | token_id, token_secret, hosts |
| `mycosoft/unifi` | api_key, host |
| `mycosoft/nas` | protocol, ip, share, mount_point |
| `mycosoft/nas_credentials` | username, password (SMB only) |

### Generated Files

```
infra/bootstrap/out/
├── connections.json      # Non-secret connection info
├── vault_paths.md        # Secret documentation
├── verify.sh             # Verification script
├── vault-agent.hcl       # Vault Agent config
├── templates/            # Vault Agent templates
│   ├── proxmox.tpl
│   └── unifi.tpl
└── secrets/              # Runtime secrets (gitignored)
```

### Docker Compose

```
docker-compose.sync.yml   # Infrastructure services
```

Services:
- `vault-agent` - Fetches secrets for containers
- `orchestrator` - MYCA orchestration
- `agent-runner` - MAS agent execution
- `uart-agent` - Hardware UART interface (profile: hardware)
- `gpu-runner` - GPU workloads (profile: gpu)
- `redis` - Message broker

## Starting Services

```bash
# Basic MYCA services:
docker-compose -f docker-compose.sync.yml --profile myca up -d

# With hardware support:
docker-compose -f docker-compose.sync.yml --profile myca --profile hardware up -d

# With GPU support:
docker-compose -f docker-compose.sync.yml --profile myca --profile gpu up -d
```

## Proxmox Token Setup

### Option A: SSH-Assisted (Automated)

The script can SSH to Proxmox and run:
```bash
pveum user add myca@pve --comment "MYCA MAS Service Account"
pveum role add MYCA_ROLE --privs "..."
pveum aclmod / --users myca@pve --roles MYCA_ROLE
pveum token add myca@pve mas --privsep 0
```

### Option B: UI-Assisted (Manual)

1. Open Proxmox UI (e.g., https://192.168.0.202:8006)
2. Create user: `myca@pve`
3. Create role: `MYCA_ROLE` with privileges:
   - Datastore.AllocateSpace, Datastore.Audit
   - Pool.Allocate
   - Sys.Audit, Sys.Modify
   - VM.Allocate, VM.Audit, VM.Clone
   - VM.Config.* (all)
   - VM.Monitor, VM.PowerMgmt
4. Add ACL: Path `/`, User `myca@pve`, Role `MYCA_ROLE`
5. Create API token: User `myca@pve`, Token ID `mas`, Privilege Separation: OFF
6. Copy the token secret immediately!

## UniFi API Key Setup

1. Open https://192.168.0.1
2. Navigate to: Settings → System → Advanced
3. Enable "API Access"
4. Create new API key named "MYCA-MAS"
5. Copy the key immediately!

## Vault Operations

### Unseal Vault (after reboot)

```bash
export VAULT_ADDR=http://127.0.0.1:8200
vault operator unseal <key1>
vault operator unseal <key2>
vault operator unseal <key3>
```

### Generate New Secret ID

```bash
vault write -f -field=secret_id auth/approle/role/myca/secret-id > ~/.mycosoft-vault-secret-id
chmod 600 ~/.mycosoft-vault-secret-id
```

### Access Secrets (Admin)

```bash
export VAULT_ADDR=http://127.0.0.1:8200
vault login <root_token>
vault kv get mycosoft/proxmox
vault kv get mycosoft/unifi
```

### Access Secrets (AppRole)

   ```bash
   export VAULT_ADDR=http://127.0.0.1:8200
ROLE_ID=$(cat ~/.mycosoft-vault-role-id)
SECRET_ID=$(vault write -f -field=secret_id auth/approle/role/myca/secret-id)
VAULT_TOKEN=$(vault write -field=token auth/approle/login role_id=$ROLE_ID secret_id=$SECRET_ID)
VAULT_TOKEN=$VAULT_TOKEN vault kv get mycosoft/proxmox
   ```

## Troubleshooting

### Vault is Sealed

```bash
vault operator unseal <key1>
vault operator unseal <key2>
vault operator unseal <key3>
```

### Proxmox Token Invalid

- Verify format: `myca@pve!mas`
- Check token exists: Datacenter → Permissions → API Tokens
- Verify ACL: Datacenter → Permissions → Permissions
- Test manually:
  ```bash
  curl -k -H "Authorization: PVEAPIToken=myca@pve!mas=<secret>" \
    https://192.168.0.202:8006/api2/json/nodes
  ```

### UniFi API Key Invalid

- Verify API Access is enabled in UniFi settings
- Check key wasn't revoked
- Test manually:
  ```bash
  curl -k -H "X-API-Key: <key>" \
    https://192.168.0.1/proxy/network/api/self
  ```

### NAS Mount Failed

- Ping the NAS: `ping <nas-ip>`
- Check NFS exports: `showmount -e <nas-ip>`
- Verify firewall allows NFS (2049) or SMB (445)
- Check mount manually:
   ```bash
  sudo mount -t nfs <nas-ip>:/path /mnt/test
  # or
  sudo mount -t cifs //<nas-ip>/share /mnt/test -o username=user
   ```

## Idempotency

The script is safe to re-run:
- Checks existing Vault initialization
- Validates existing tokens before prompting
- Checks existing NAS mount
- Skips installation if already present

## Files That Should NEVER Be Committed

```
# Already in .gitignore:
infra/bootstrap/out/
infra/bootstrap/network_config.json
*.mycosoft-vault-role-id
*.mycosoft-vault-secret-id
.vault/
*credentials*
*password*
```

## Support

- Vault docs: https://www.vaultproject.io/docs
- Proxmox API: https://pve.proxmox.com/pve-docs/api-viewer/
- UniFi API: https://ubntwiki.com/products/software/unifi-controller/api
