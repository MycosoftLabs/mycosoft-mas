# Mycosoft Infrastructure Bootstrap

Interactive bootstrap script for setting up Mycosoft's infrastructure integration with Proxmox, UniFi UDM, NAS, and HashiCorp Vault.

## Overview

This bootstrap script automates the setup of:
- **HashiCorp Vault** - Secret management with AppRole authentication
- **Proxmox** - VM management API integration (192.168.0.202, 192.168.0.131)
- **UniFi Dream Machine** - Network management API integration (192.168.0.1)
- **NAS** - Network storage mounting (NFS or SMB)

## Prerequisites

- Ubuntu/Debian Linux system (or compatible)
- Docker installed and running
- SSH access (optional, for Proxmox CLI token creation)
- Network access to:
  - Proxmox hosts (192.168.0.202:8006, 192.168.0.131:8006)
  - UniFi UDM (192.168.0.1:443)
  - NAS device (IP to be provided)

## Usage

### Dry Run (Validation Only)

```bash
./infra/bootstrap/bootstrap_mycosoft.sh --dry-run
```

This mode:
- Checks OS and required binaries
- Validates network connectivity
- Does NOT install or configure anything
- Does NOT prompt for secrets

### Apply Mode (Full Setup)

```bash
./infra/bootstrap/bootstrap_mycosoft.sh --apply
```

This mode:
- Performs all dry-run checks
- Installs and configures Vault
- Prompts for secrets interactively
- Creates Proxmox API tokens (CLI or UI guided)
- Creates UniFi API tokens (UI guided)
- Mounts NAS storage
- Generates configuration files

## What the Script Does

### 1. System Checks
- Verifies OS compatibility (Linux)
- Checks for required binaries (curl, jq, docker)
- Installs missing packages (with confirmation)

### 2. Network Validation
- Tests connectivity to Proxmox hosts
- Tests connectivity to UniFi UDM
- Reports reachability status

### 3. Vault Setup
- Downloads and installs HashiCorp Vault
- Creates systemd service for Vault
- Initializes Vault (interactive - you'll receive root token and unseal keys)
- Creates KV v2 mount at `mycosoft/`
- Creates `mycosoft` policy with least privilege
- Creates AppRole `myca` for MYCA authentication
- Saves role-id and secret-id to `~/.mycosoft-vault-role-id` and `~/.mycosoft-vault-secret-id`

### 4. Proxmox Token Setup
- Checks for existing token in Vault
- If missing, offers two paths:
  - **CLI Path**: Creates user, role, ACL, and token via SSH (if available)
  - **UI Path**: Provides step-by-step UI navigation instructions
- Validates token by calling Proxmox API
- Stores token securely in Vault

### 5. UniFi Token Setup
- Checks for existing token in Vault
- If missing, provides UI navigation steps
- Validates token via UniFi API
- Stores token securely in Vault

### 6. NAS Mounting
- Prompts for protocol (NFS or SMB)
- Prompts for NAS IP and share path
- Mounts to `/mnt/mycosoft-nas`
- Optionally adds to `/etc/fstab` for persistence
- Stores configuration in Vault

### 7. Configuration Generation
Creates files in `infra/bootstrap/out/`:
- `connections.json` - Non-secret connection information
- `vault_paths.md` - Documentation of secret locations
- `verify.sh` - Verification script
- `vault-agent.hcl` - Vault Agent configuration
- `templates/` - Vault Agent templates for secret injection

### 8. Docker Compose Template
Generates `docker-compose.sync.yml` in repo root:
- Vault Agent service for secret injection
- Proxmox sync service skeleton
- UniFi sync service skeleton
- Uses Vault Agent to fetch secrets at runtime

## Security Notes

- **Never commit secrets**: All secrets are stored in Vault, not in git
- **Role ID and Secret ID**: Saved to `~/.mycosoft-vault-role-id` and `~/.mycosoft-vault-secret-id` (excluded from git)
- **Vault Root Token**: Displayed once during initialization - save it securely!
- **Unseal Keys**: Displayed once during initialization - save them securely!
- **Silent Input**: Passwords are read with `read -sp` to avoid terminal echo

## Output Files

### `infra/bootstrap/out/connections.json`
Non-secret connection information (IPs, ports, mount paths).

### `infra/bootstrap/out/vault_paths.md`
Documentation of where secrets are stored in Vault and how to access them.

### `infra/bootstrap/out/verify.sh`
Script to verify all components are configured correctly.

### `docker-compose.sync.yml`
Docker Compose file for infrastructure sync services that read secrets from Vault.

## Verification

After running the bootstrap script, verify everything is working:

```bash
./infra/bootstrap/out/verify.sh
```

## Troubleshooting

### Vault is Sealed
If Vault becomes sealed, unseal it with 3 of the 5 unseal keys:
```bash
export VAULT_ADDR=http://127.0.0.1:8200
vault operator unseal <key1>
vault operator unseal <key2>
vault operator unseal <key3>
```

### Proxmox Token Invalid
- Verify the token ID format: `user@realm!token-name`
- Check token permissions in Proxmox UI
- Ensure token hasn't expired

### UniFi Token Invalid
- Verify API access is enabled in UniFi settings
- Check token hasn't been revoked
- Ensure you're using the correct admin account

### NAS Mount Failed
- Verify NAS IP is reachable: `ping <nas-ip>`
- Check NFS/SMB service is running on NAS
- Verify share path is correct
- Check firewall rules allow NFS/SMB traffic

## Next Steps

1. Review generated configuration files
2. Test Vault access:
   ```bash
   export VAULT_ADDR=http://127.0.0.1:8200
   export VAULT_ROLE_ID=$(cat ~/.mycosoft-vault-role-id)
   export VAULT_SECRET_ID=$(cat ~/.mycosoft-vault-secret-id)
   vault write auth/approle/login role_id=$VAULT_ROLE_ID secret_id=$VAULT_SECRET_ID
   vault kv get mycosoft/proxmox
   ```

3. Start infrastructure sync services:
   ```bash
   docker-compose -f docker-compose.sync.yml --profile infra-sync up -d
   ```

## Idempotency

The script is designed to be idempotent - safe to re-run:
- Checks for existing Vault initialization before initializing
- Checks for existing tokens before prompting for new ones
- Checks for existing NAS mount before mounting
- Skips installation if binaries already exist

## Support

For issues or questions, refer to:
- Vault documentation: https://www.vaultproject.io/docs
- Proxmox API documentation: https://pve.proxmox.com/pve-docs/api-viewer/
- UniFi API documentation: https://ubntwiki.com/products/software/unifi-controller/api
