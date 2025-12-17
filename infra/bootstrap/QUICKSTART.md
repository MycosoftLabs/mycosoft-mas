# Mycosoft Bootstrap - Quick Start

## ⚠️ First: Rotate Any Exposed Passwords

If passwords were shared in chat, logs, or exposed anywhere:

```bash
# 1. SSH to each Proxmox node and change root password
ssh root@192.168.0.202  # then: passwd
ssh root@192.168.0.2    # then: passwd
ssh root@192.168.0.131  # then: passwd

# 2. Change WiFi password for SSID "Myca" in UniFi UI
#    https://192.168.0.1 → Settings → WiFi → Myca → Edit
```

---

## Quick Setup (5 minutes)

### 1. Dry Run (Check Connectivity)

```bash
cd /path/to/mycosoft-mas
./infra/bootstrap/bootstrap_mycosoft.sh --dry-run
```

This checks:
- ✓ OS and prerequisites (curl, jq, docker, ssh)
- ✓ Proxmox nodes reachable (192.168.0.202, 192.168.0.2, 192.168.0.131)
- ✓ UniFi UDM reachable (192.168.0.1)

### 2. Full Setup

```bash
./infra/bootstrap/bootstrap_mycosoft.sh --apply
```

Interactive prompts will guide you through:
1. Installing Vault
2. Creating Vault secrets engine and AppRole
3. Creating Proxmox API token (SSH or UI guided)
4. Creating UniFi API key
5. Mounting NAS storage

### 3. Verify

```bash
./infra/bootstrap/out/verify.sh
```

### 4. Start Services

```bash
docker-compose -f docker-compose.sync.yml --profile myca up -d
```

---

## Infrastructure IPs

| Service | IP | Port | URL |
|---------|-----|------|-----|
| Proxmox Build | 192.168.0.202 | 8006 | https://192.168.0.202:8006 |
| Proxmox DC1 | 192.168.0.2 | 8006 | https://192.168.0.2:8006 |
| Proxmox DC2 | 192.168.0.131 | 8006 | https://192.168.0.131:8006 |
| UniFi UDM | 192.168.0.1 | 443 | https://192.168.0.1 |
| Vault | 127.0.0.1 | 8200 | http://127.0.0.1:8200 |

---

## Key Files

```
~/.mycosoft-vault-role-id    # Vault AppRole ID (safe to store)
~/.mycosoft-vault-secret-id  # Vault Secret ID (regenerate as needed)

infra/bootstrap/out/
├── connections.json         # Non-secret connection info
├── vault_paths.md           # Where secrets are stored
├── verify.sh                # Verification script
└── vault-agent.hcl          # Vault Agent config
```

---

## Using Python Clients

```python
# With Vault integration
from proxmox_client import ProxmoxClient
from unifi_client import UniFiClient

# Load credentials from Vault
proxmox = ProxmoxClient.from_vault("192.168.0.202")
unifi = UniFiClient.from_vault()

# List VMs
for vm in proxmox.get_vms():
    print(f"{vm['name']}: {vm['status']}")

# List network clients
for client in unifi.get_clients():
    print(f"{client['hostname']}: {client['ip']}")
```

---

## Common Commands

   ```bash
# Unseal Vault after reboot
   export VAULT_ADDR=http://127.0.0.1:8200
vault operator unseal <key1>
vault operator unseal <key2>
vault operator unseal <key3>

# Generate new Secret ID
vault write -f -field=secret_id auth/approle/role/myca/secret-id

# Read Proxmox token from Vault
   vault kv get mycosoft/proxmox

# Test Proxmox API
curl -k -H "Authorization: PVEAPIToken=myca@pve!mas=<secret>" \
  https://192.168.0.202:8006/api2/json/nodes

# Test UniFi API
curl -k -H "X-API-Key: <key>" \
  https://192.168.0.1/proxy/network/api/self
```
