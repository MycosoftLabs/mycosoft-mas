#!/bin/bash
# HashiCorp Vault Setup for MYCA
# Run this on the MYCA Core VM

set -e

NAS_MOUNT="/mnt/mycosoft"
VAULT_VERSION="1.16.0"

echo "=========================================="
echo "  HashiCorp Vault Setup for MYCA"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo"
    exit 1
fi

# ==============================================
# Install Vault
# ==============================================
echo "Installing HashiCorp Vault..."

# Add HashiCorp GPG key
curl -fsSL https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg

# Add repository
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" > /etc/apt/sources.list.d/hashicorp.list

# Install
apt-get update
apt-get install -y vault

echo "Vault version: $(vault --version)"

# ==============================================
# Create Directories
# ==============================================
echo ""
echo "Creating directories..."

mkdir -p /etc/vault.d
mkdir -p /var/log/vault
mkdir -p "$NAS_MOUNT/vault/data"
chown -R vault:vault "$NAS_MOUNT/vault"
chmod 700 "$NAS_MOUNT/vault/data"

# ==============================================
# Configure Vault
# ==============================================
echo ""
echo "Configuring Vault..."

# Copy configuration
cat > /etc/vault.d/vault.hcl << 'EOF'
# HashiCorp Vault Configuration for MYCA
storage "file" {
  path = "/mnt/mycosoft/vault/data"
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 1
}

api_addr = "http://127.0.0.1:8200"
cluster_addr = "http://127.0.0.1:8201"
ui = true
log_level = "info"

telemetry {
  prometheus_retention_time = "30s"
  disable_hostname = true
}
EOF

chown vault:vault /etc/vault.d/vault.hcl
chmod 640 /etc/vault.d/vault.hcl

# ==============================================
# Create Systemd Service
# ==============================================
echo ""
echo "Creating systemd service..."

cat > /etc/systemd/system/vault.service << 'EOF'
[Unit]
Description=HashiCorp Vault
Documentation=https://www.vaultproject.io/docs/
Requires=network-online.target
After=network-online.target
ConditionFileNotEmpty=/etc/vault.d/vault.hcl

[Service]
User=vault
Group=vault
ProtectSystem=full
ProtectHome=read-only
PrivateTmp=yes
PrivateDevices=yes
SecureBits=keep-caps
AmbientCapabilities=CAP_IPC_LOCK
CapabilityBoundingSet=CAP_SYSLOG CAP_IPC_LOCK
NoNewPrivileges=yes
ExecStart=/usr/bin/vault server -config=/etc/vault.d/vault.hcl
ExecReload=/bin/kill --signal HUP $MAINPID
KillMode=process
KillSignal=SIGINT
Restart=on-failure
RestartSec=5
TimeoutStopSec=30
LimitNOFILE=65536
LimitMEMLOCK=infinity

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

# ==============================================
# Start Vault
# ==============================================
echo ""
echo "Starting Vault..."

systemctl enable vault
systemctl start vault

# Wait for Vault to start
sleep 5

# Check status
export VAULT_ADDR='http://127.0.0.1:8200'

if vault status 2>&1 | grep -q "Sealed.*true"; then
    echo "Vault is running but sealed (expected for new installation)"
elif vault status 2>&1 | grep -q "connection refused"; then
    echo "ERROR: Vault not responding"
    journalctl -u vault --no-pager -n 20
    exit 1
else
    echo "Vault status:"
    vault status || true
fi

# ==============================================
# Initialize Vault (if not already initialized)
# ==============================================
echo ""
echo "Checking initialization status..."

if vault status 2>&1 | grep -q "Initialized.*false"; then
    echo "Initializing Vault..."
    
    # Initialize with 5 key shares and 3 key threshold
    vault operator init -key-shares=5 -key-threshold=3 > /root/vault-init-keys.txt
    
    echo ""
    echo "=========================================="
    echo "  IMPORTANT: SAVE THESE KEYS SECURELY!"
    echo "=========================================="
    cat /root/vault-init-keys.txt
    echo ""
    echo "Keys saved to /root/vault-init-keys.txt"
    echo "Move this file to secure offline storage!"
    
    # Also save to NAS backup
    cp /root/vault-init-keys.txt "$NAS_MOUNT/backups/vault-init-keys-$(date +%Y%m%d).txt"
    chmod 600 "$NAS_MOUNT/backups/vault-init-keys-$(date +%Y%m%d).txt"
    
    echo ""
    echo "Unsealing Vault..."
    
    # Extract first 3 unseal keys and root token
    KEY1=$(grep "Unseal Key 1:" /root/vault-init-keys.txt | awk '{print $NF}')
    KEY2=$(grep "Unseal Key 2:" /root/vault-init-keys.txt | awk '{print $NF}')
    KEY3=$(grep "Unseal Key 3:" /root/vault-init-keys.txt | awk '{print $NF}')
    ROOT_TOKEN=$(grep "Initial Root Token:" /root/vault-init-keys.txt | awk '{print $NF}')
    
    vault operator unseal "$KEY1"
    vault operator unseal "$KEY2"
    vault operator unseal "$KEY3"
    
    echo "Vault unsealed!"
    
    # Login with root token
    vault login "$ROOT_TOKEN"
    
    # ==============================================
    # Configure Secrets Engine
    # ==============================================
    echo ""
    echo "Configuring secrets engine..."
    
    # Enable KV v2 secrets engine
    vault secrets enable -path=mycosoft kv-v2
    
    # Create policy for MYCA
    cat > /tmp/myca-policy.hcl << 'POLICY'
# MYCA read-only access to secrets
path "mycosoft/*" {
  capabilities = ["read", "list"]
}

# Allow token renewal
path "auth/token/renew-self" {
  capabilities = ["update"]
}
POLICY
    
    vault policy write myca /tmp/myca-policy.hcl
    rm /tmp/myca-policy.hcl
    
    # Enable AppRole auth
    vault auth enable approle
    
    # Create AppRole for MYCA
    vault write auth/approle/role/myca \
        token_policies="myca" \
        token_ttl=1h \
        token_max_ttl=4h \
        secret_id_ttl=0
    
    # Get role ID and secret ID
    ROLE_ID=$(vault read -field=role_id auth/approle/role/myca/role-id)
    SECRET_ID=$(vault write -field=secret_id -f auth/approle/role/myca/secret-id)
    
    echo ""
    echo "AppRole configured:"
    echo "  Role ID: $ROLE_ID"
    echo "  Secret ID: $SECRET_ID"
    
    # Save AppRole credentials
    mkdir -p /etc/myca/vault
    echo "$ROLE_ID" > /etc/myca/vault/.role-id
    echo "$SECRET_ID" > /etc/myca/vault/.secret-id
    chmod 600 /etc/myca/vault/.role-id /etc/myca/vault/.secret-id
    
else
    echo "Vault already initialized"
fi

# ==============================================
# Summary
# ==============================================
echo ""
echo "=========================================="
echo "  Vault Setup Complete"
echo "=========================================="
echo ""
echo "Vault Address: http://127.0.0.1:8200"
echo "Vault UI:      http://127.0.0.1:8200/ui"
echo ""
echo "Next steps:"
echo "1. Store unseal keys in secure offline location"
echo "2. Add secrets: vault kv put mycosoft/proxmox token_id=... token_secret=..."
echo "3. Add secrets: vault kv put mycosoft/unifi api_key=..."
echo "4. Add secrets: vault kv put mycosoft/elevenlabs api_key=..."
echo ""
echo "MYCA can authenticate using AppRole credentials at:"
echo "  /etc/myca/vault/.role-id"
echo "  /etc/myca/vault/.secret-id"
