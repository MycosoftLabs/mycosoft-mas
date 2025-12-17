# Quick Start Guide

## Commands to Run

### 1. Dry Run (Validation Only)
```bash
cd /path/to/mycosoft-mas
./infra/bootstrap/bootstrap_mycosoft.sh --dry-run
```

This validates:
- OS compatibility
- Required binaries
- Network connectivity to Proxmox and UniFi

**No secrets are prompted in dry-run mode.**

### 2. Apply Mode (Full Setup)
```bash
cd /path/to/mycosoft-mas
./infra/bootstrap/bootstrap_mycosoft.sh --apply
```

This will:
- Install Vault (if not present)
- Configure Vault as a system service
- Initialize Vault (you'll receive root token and unseal keys)
- Prompt for Proxmox API token (CLI or UI guided)
- Prompt for UniFi API token (UI guided)
- Mount NAS storage
- Generate all configuration files

### 3. Verify Setup
```bash
./infra/bootstrap/out/verify.sh
```

## What You'll Need

Before running `--apply`, prepare:

1. **Vault Credentials Storage**: Have a secure place to save:
   - Root token (displayed once)
   - 5 unseal keys (displayed once)

2. **Proxmox Access**: Either:
   - SSH access to Proxmox host (for CLI token creation), OR
   - Web UI access to create token manually

3. **UniFi Access**: 
   - Web UI access to UniFi UDM
   - Admin account credentials (myca@mycosoft.org)

4. **NAS Information**:
   - NAS IP address
   - Share path
   - Protocol (NFS or SMB)
   - Credentials (if SMB)

## Expected Output

After successful `--apply`, you'll see:

```
==========================================
  Mycosoft Infrastructure Bootstrap
  Final Status Report
==========================================

[✓] OS and binaries checked
[✓] Network connectivity verified
[✓] Vault installed
[✓] Vault configured
[✓] Vault initialized and AppRole created
[✓] Proxmox API token configured
[✓] UniFi API token configured
[✓] NAS mounted

==========================================

All critical components are configured!

Next steps:
1. Review configuration files in: infra/bootstrap/out/
2. Verify setup: infra/bootstrap/out/verify.sh
3. Start infrastructure sync services:
   docker-compose -f docker-compose.sync.yml --profile infra-sync up -d
```

## Troubleshooting

### Script Fails at Network Check
- Verify Proxmox hosts are reachable: `curl -k https://192.168.0.202:8006`
- Verify UniFi is reachable: `curl -k https://192.168.0.1`
- Check firewall rules

### Vault Installation Fails
- Ensure you have sudo/root access
- Check internet connectivity
- Verify architecture compatibility (amd64/arm64)

### Token Validation Fails
- Double-check token format
- Verify token hasn't expired
- Check API access is enabled (UniFi)

### NAS Mount Fails
- Verify NAS IP is pingable
- Check NFS/SMB service is running
- Verify share path is correct
- Check user permissions

## Next Steps After Bootstrap

1. **Test Vault Access**:
   ```bash
   export VAULT_ADDR=http://127.0.0.1:8200
   export VAULT_ROLE_ID=$(cat ~/.mycosoft-vault-role-id)
   export VAULT_SECRET_ID=$(cat ~/.mycosoft-vault-secret-id)
   vault write auth/approle/login role_id=$VAULT_ROLE_ID secret_id=$VAULT_SECRET_ID
   vault kv get mycosoft/proxmox
   ```

2. **Start Sync Services**:
   ```bash
   docker-compose -f docker-compose.sync.yml --profile infra-sync up -d
   ```

3. **Integrate with MYCA**: Use the generated `docker-compose.sync.yml` as a template for your MYCA services.
