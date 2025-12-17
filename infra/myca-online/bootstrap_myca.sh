#!/usr/bin/env bash
set -euo pipefail

#=============================================================================
# MYCA Bootstrap - Bring MYCA MAS Fully Online
#=============================================================================
# Purpose: End-to-end bootstrap for MYCA infrastructure
# - Vault setup with AppRole
# - Proxmox API validation
# - UniFi API validation
# - NAS mounting
# - GPU runner deployment
# - UART ingest agent
# - MYCA core orchestrator with ops loops
# - n8n speech interface scaffolds
#
# Security: No passwords stored, interactive prompts only, Vault-based secrets
# Modes: dry-run, apply, verify
#=============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUT_DIR="$SCRIPT_DIR/out"
TEMPLATES_DIR="$SCRIPT_DIR/templates"
LOGS_DIR="$OUT_DIR/logs"

# Infrastructure endpoints
PROXMOX_BUILD="192.168.0.202:8006"
PROXMOX_DC1="192.168.0.2:8006"
PROXMOX_DC2="192.168.0.131:8006"
UNIFI_UDM="192.168.0.1"
VAULT_ADDR="http://127.0.0.1:8200"
MYCA_PORT="8001"
MYCA_UI_PORT="3001"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Mode
MODE="${1:-help}"

#=============================================================================
# Utility Functions
#=============================================================================

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*"
}

success() {
    echo -e "${GREEN}✓${NC} $*"
}

error() {
    echo -e "${RED}✗${NC} $*" >&2
}

warn() {
    echo -e "${YELLOW}!${NC} $*"
}

section() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $*${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
}

prompt_confirm() {
    local message="$1"
    read -p "$message [y/N]: " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

check_command() {
    if command -v "$1" &>/dev/null; then
        success "$1 is installed"
        return 0
    else
        error "$1 is not installed"
        return 1
    fi
}

test_url() {
    local url="$1"
    local name="$2"
    if curl -fsSL -k --connect-timeout 5 "$url" &>/dev/null; then
        success "$name is reachable ($url)"
        return 0
    else
        error "$name is NOT reachable ($url)"
        return 1
    fi
}

#=============================================================================
# Initialization
#=============================================================================

init_dirs() {
    mkdir -p "$OUT_DIR"/{logs,secrets,vault,docker}
    mkdir -p "$TEMPLATES_DIR"
    chmod 700 "$OUT_DIR/secrets"
}

#=============================================================================
# Vault Setup
#=============================================================================

vault_check() {
    log "Checking Vault status..."
    
    if ! check_command vault; then
        return 1
    fi
    
    export VAULT_ADDR="$VAULT_ADDR"
    
    if vault status &>/dev/null; then
        local sealed=$(vault status -format=json | jq -r '.sealed')
        if [ "$sealed" = "true" ]; then
            warn "Vault is sealed"
            return 1
        else
            success "Vault is running and unsealed"
            return 0
        fi
    else
        error "Vault is not running"
        return 1
    fi
}

vault_install() {
    log "Installing Vault..."
    
    if [ "$MODE" = "dry-run" ]; then
        log "[DRY-RUN] Would install Vault"
        return 0
    fi
    
    if check_command vault; then
        log "Vault already installed"
        return 0
    fi
    
    # Install Vault
    if [ "$(uname)" = "Linux" ]; then
        if command -v apt-get &>/dev/null; then
            warn "Installing Vault via apt..."
            if prompt_confirm "Install Vault?"; then
                wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
                echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
                sudo apt-get update && sudo apt-get install -y vault
                success "Vault installed"
            fi
        fi
    fi
}

vault_init() {
    log "Initializing Vault..."
    
    export VAULT_ADDR="$VAULT_ADDR"
    
    if [ "$MODE" = "dry-run" ]; then
        log "[DRY-RUN] Would initialize Vault"
        return 0
    fi
    
    # Check if already initialized
    if vault status &>/dev/null; then
        log "Vault already initialized"
        return 0
    fi
    
    # Start Vault server in dev mode for now (production: use proper config)
    log "Starting Vault server..."
    vault server -dev -dev-root-token-id="mycosoft-root-token" -dev-listen-address="127.0.0.1:8200" &>/dev/null &
    local vault_pid=$!
    echo "$vault_pid" > "$OUT_DIR/vault.pid"
    
    sleep 3
    
    # Export token
    export VAULT_TOKEN="mycosoft-root-token"
    
    success "Vault initialized (dev mode)"
}

vault_configure() {
    log "Configuring Vault..."
    
    export VAULT_ADDR="$VAULT_ADDR"
    export VAULT_TOKEN="${VAULT_TOKEN:-mycosoft-root-token}"
    
    if [ "$MODE" = "dry-run" ]; then
        log "[DRY-RUN] Would configure Vault KV and AppRole"
        return 0
    fi
    
    # Enable KV v2 secrets engine
    if ! vault secrets list | grep -q "mycosoft/"; then
        vault secrets enable -path=mycosoft kv-v2
        success "KV v2 enabled at mycosoft/"
    else
        log "KV v2 already enabled"
    fi
    
    # Create policy
    cat > "$OUT_DIR/vault/mycosoft-policy.hcl" <<'EOF'
path "mycosoft/data/*" {
  capabilities = ["read", "list"]
}
EOF
    
    vault policy write mycosoft "$OUT_DIR/vault/mycosoft-policy.hcl"
    success "Policy 'mycosoft' created"
    
    # Enable AppRole auth
    if ! vault auth list | grep -q "approle/"; then
        vault auth enable approle
        success "AppRole auth enabled"
    else
        log "AppRole already enabled"
    fi
    
    # Create AppRole
    vault write auth/approle/role/myca \
        token_policies="mycosoft" \
        token_ttl=1h \
        token_max_ttl=4h
    
    # Get Role ID
    vault read -field=role_id auth/approle/role/myca/role-id > "$OUT_DIR/secrets/.vault-role-id"
    chmod 600 "$OUT_DIR/secrets/.vault-role-id"
    
    # Generate Secret ID
    vault write -field=secret_id auth/approle/role/myca/secret-id > "$OUT_DIR/secrets/.vault-secret-id"
    chmod 600 "$OUT_DIR/secrets/.vault-secret-id"
    
    success "AppRole 'myca' configured"
}

#=============================================================================
# Proxmox Integration
#=============================================================================

proxmox_check() {
    log "Checking Proxmox connectivity..."
    
    local all_ok=true
    
    test_url "https://$PROXMOX_BUILD/api2/json/version" "Proxmox Build" || all_ok=false
    test_url "https://$PROXMOX_DC1/api2/json/version" "Proxmox DC1" || all_ok=false
    test_url "https://$PROXMOX_DC2/api2/json/version" "Proxmox DC2" || all_ok=false
    
    if [ "$all_ok" = true ]; then
        return 0
    else
        return 1
    fi
}

proxmox_setup() {
    log "Setting up Proxmox integration..."
    
    if [ "$MODE" = "dry-run" ]; then
        log "[DRY-RUN] Would configure Proxmox API tokens"
        return 0
    fi
    
    export VAULT_ADDR="$VAULT_ADDR"
    export VAULT_TOKEN="${VAULT_TOKEN:-mycosoft-root-token}"
    
    # Check if already configured
    if vault kv get mycosoft/proxmox &>/dev/null; then
        log "Proxmox credentials already in Vault"
        
        # Validate token
        local token_id=$(vault kv get -field=token_id mycosoft/proxmox)
        local token_secret=$(vault kv get -field=token_secret mycosoft/proxmox)
        
        if curl -fsSL -k -H "Authorization: PVEAPIToken=$token_id=$token_secret" \
            "https://$PROXMOX_BUILD/api2/json/nodes" &>/dev/null; then
            success "Proxmox token is valid"
            return 0
        else
            warn "Proxmox token invalid, needs reconfiguration"
        fi
    fi
    
    # Guide user through token creation
    cat <<EOF

${YELLOW}════════════════════════════════════════════════════════════════
Proxmox API Token Setup Required
════════════════════════════════════════════════════════════════${NC}

You need to create an API token in Proxmox. Choose one method:

${GREEN}Option A: SSH-Assisted (Automated)${NC}
  - Script will SSH to Proxmox and create user + token
  - Requires: SSH access to Proxmox root

${GREEN}Option B: UI-Assisted (Manual)${NC}
  - Open: https://$PROXMOX_BUILD
  - Datacenter → Permissions → Users → Add
    - User: myca@pve
  - Datacenter → Permissions → Roles → Create
    - Name: MYCA_ROLE
    - Privileges: Datastore.*, Pool.Allocate, Sys.*, VM.*
  - Datacenter → Permissions → Add → Path: /, User: myca@pve, Role: MYCA_ROLE
  - Datacenter → Permissions → API Tokens → Add
    - User: myca@pve
    - Token ID: mas
    - Privilege Separation: OFF
  - Copy the token immediately!

EOF
    
    if prompt_confirm "Do you have SSH access to create token automatically (Option A)?"; then
        read -p "Proxmox SSH user (default: root): " ssh_user
        ssh_user="${ssh_user:-root}"
        
        local proxmox_host="${PROXMOX_BUILD/:*/}"
        
        log "Creating user and token on Proxmox..."
        
        ssh "$ssh_user@$proxmox_host" bash <<'REMOTE_EOF'
pveum user add myca@pve --comment "MYCA MAS Service Account" 2>/dev/null || true
pveum role add MYCA_ROLE --privs "Datastore.AllocateSpace,Datastore.Audit,Pool.Allocate,Sys.Audit,Sys.Modify,VM.Allocate,VM.Audit,VM.Clone,VM.Config.CDROM,VM.Config.CPU,VM.Config.Cloudinit,VM.Config.Disk,VM.Config.HWType,VM.Config.Memory,VM.Config.Network,VM.Config.Options,VM.Monitor,VM.PowerMgmt" 2>/dev/null || true
pveum aclmod / --users myca@pve --roles MYCA_ROLE
pveum token add myca@pve mas --privsep 0 --output-format json
REMOTE_EOF
        
        success "Token created on Proxmox"
    fi
    
    # Manual token entry
    echo ""
    read -p "Enter Proxmox API Token ID (e.g., myca@pve!mas): " token_id
    read -sp "Enter Proxmox API Token Secret: " token_secret
    echo ""
    
    # Validate token
    log "Validating token..."
    if curl -fsSL -k -H "Authorization: PVEAPIToken=$token_id=$token_secret" \
        "https://$PROXMOX_BUILD/api2/json/nodes" | jq -e '.data' &>/dev/null; then
        success "Token validated successfully"
    else
        error "Token validation failed"
        return 1
    fi
    
    # Store in Vault
    vault kv put mycosoft/proxmox \
        token_id="$token_id" \
        token_secret="$token_secret" \
        hosts="$PROXMOX_BUILD,$PROXMOX_DC1,$PROXMOX_DC2"
    
    success "Proxmox credentials stored in Vault"
}

#=============================================================================
# UniFi Integration
#=============================================================================

unifi_check() {
    log "Checking UniFi connectivity..."
    
    test_url "https://$UNIFI_UDM/" "UniFi UDM"
}

unifi_setup() {
    log "Setting up UniFi integration..."
    
    if [ "$MODE" = "dry-run" ]; then
        log "[DRY-RUN] Would configure UniFi API key"
        return 0
    fi
    
    export VAULT_ADDR="$VAULT_ADDR"
    export VAULT_TOKEN="${VAULT_TOKEN:-mycosoft-root-token}"
    
    # Check if already configured
    if vault kv get mycosoft/unifi &>/dev/null; then
        log "UniFi credentials already in Vault"
        
        # Validate token
        local api_key=$(vault kv get -field=api_key mycosoft/unifi)
        
        if curl -fsSL -k -H "X-API-Key: $api_key" \
            "https://$UNIFI_UDM/proxy/network/api/self" &>/dev/null; then
            success "UniFi API key is valid"
            return 0
        else
            warn "UniFi API key invalid, needs reconfiguration"
        fi
    fi
    
    # Guide user
    cat <<EOF

${YELLOW}════════════════════════════════════════════════════════════════
UniFi API Key Setup Required
════════════════════════════════════════════════════════════════${NC}

1. Open: https://$UNIFI_UDM
2. Login to UniFi Network
3. Settings → System → Advanced
4. Enable "API Access"
5. Create API Key → Name: "MYCA-MAS"
6. Copy the key immediately!

EOF
    
    read -sp "Enter UniFi API Key: " api_key
    echo ""
    
    # Validate key
    log "Validating API key..."
    if curl -fsSL -k -H "X-API-Key: $api_key" \
        "https://$UNIFI_UDM/proxy/network/api/self" | jq -e '.data' &>/dev/null; then
        success "API key validated successfully"
    else
        error "API key validation failed"
        return 1
    fi
    
    # Store in Vault
    vault kv put mycosoft/unifi \
        api_key="$api_key" \
        host="$UNIFI_UDM"
    
    success "UniFi credentials stored in Vault"
}

#=============================================================================
# NAS Setup
#=============================================================================

nas_check() {
    log "Checking NAS mount..."
    
    if mountpoint -q /mnt/mycosoft-nas; then
        success "NAS is mounted at /mnt/mycosoft-nas"
        return 0
    else
        error "NAS is NOT mounted"
        return 1
    fi
}

nas_setup() {
    log "Setting up NAS mount..."
    
    if [ "$MODE" = "dry-run" ]; then
        log "[DRY-RUN] Would mount NAS"
        return 0
    fi
    
    export VAULT_ADDR="$VAULT_ADDR"
    export VAULT_TOKEN="${VAULT_TOKEN:-mycosoft-root-token}"
    
    # Check if already mounted
    if mountpoint -q /mnt/mycosoft-nas; then
        success "NAS already mounted"
        return 0
    fi
    
    # Prompt for NAS details
    cat <<EOF

${YELLOW}════════════════════════════════════════════════════════════════
NAS Mount Configuration
════════════════════════════════════════════════════════════════${NC}

EOF
    
    read -p "NAS IP address: " nas_ip
    read -p "Protocol (nfs/smb): " nas_protocol
    nas_protocol=$(echo "$nas_protocol" | tr '[:upper:]' '[:lower:]')
    
    if [ "$nas_protocol" = "nfs" ]; then
        read -p "NFS export path (e.g., /volume1/mycosoft): " nas_path
        
        # Test NFS
        log "Testing NFS connectivity..."
        if ! showmount -e "$nas_ip" &>/dev/null; then
            error "Cannot reach NFS server at $nas_ip"
            return 1
        fi
        
        # Mount NFS
        sudo mkdir -p /mnt/mycosoft-nas
        sudo mount -t nfs "$nas_ip:$nas_path" /mnt/mycosoft-nas
        
    elif [ "$nas_protocol" = "smb" ]; then
        read -p "SMB share name: " nas_share
        read -p "SMB username: " nas_user
        read -sp "SMB password: " nas_password
        echo ""
        
        # Mount SMB
        sudo mkdir -p /mnt/mycosoft-nas
        sudo mount -t cifs "//$nas_ip/$nas_share" /mnt/mycosoft-nas \
            -o username="$nas_user",password="$nas_password"
        
        # Store credentials in Vault
        vault kv put mycosoft/nas_credentials \
            username="$nas_user" \
            password="$nas_password"
    else
        error "Invalid protocol: $nas_protocol"
        return 1
    fi
    
    # Verify mount
    if mountpoint -q /mnt/mycosoft-nas; then
        success "NAS mounted successfully"
    else
        error "NAS mount failed"
        return 1
    fi
    
    # Test write
    if sudo touch /mnt/mycosoft-nas/.test_write && sudo rm /mnt/mycosoft-nas/.test_write; then
        success "NAS is writable"
    else
        error "NAS is not writable"
        return 1
    fi
    
    # Create logs directory
    sudo mkdir -p /mnt/mycosoft-nas/logs
    success "Created /mnt/mycosoft-nas/logs"
    
    # Store NAS config in Vault
    vault kv put mycosoft/nas \
        protocol="$nas_protocol" \
        ip="$nas_ip" \
        share="$nas_path" \
        mount_point="/mnt/mycosoft-nas"
    
    # Offer fstab persistence
    if prompt_confirm "Add to /etc/fstab for automatic mounting on boot?"; then
        if [ "$nas_protocol" = "nfs" ]; then
            echo "$nas_ip:$nas_path /mnt/mycosoft-nas nfs defaults 0 0" | sudo tee -a /etc/fstab
        else
            echo "//$nas_ip/$nas_share /mnt/mycosoft-nas cifs credentials=/root/.smbcredentials 0 0" | sudo tee -a /etc/fstab
        fi
        success "Added to /etc/fstab"
    fi
}

#=============================================================================
# GPU Setup
#=============================================================================

gpu_check() {
    log "Checking GPU availability..."
    
    if check_command nvidia-smi && nvidia-smi &>/dev/null; then
        success "NVIDIA GPU detected"
        nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | while read line; do
            log "  GPU: $line"
        done
        return 0
    else
        error "NVIDIA GPU not detected"
        return 1
    fi
}

gpu_setup() {
    log "Setting up GPU runner..."
    
    if [ "$MODE" = "dry-run" ]; then
        log "[DRY-RUN] Would deploy GPU runner"
        return 0
    fi
    
    # Deploy GPU test job
    log "Running GPU validation test..."
    
    docker run --rm --gpus all nvidia/cuda:12.3.0-base-ubuntu22.04 nvidia-smi > "$OUT_DIR/logs/gpu_test.log" 2>&1
    
    if [ $? -eq 0 ]; then
        success "GPU test passed"
        return 0
    else
        error "GPU test failed"
        return 1
    fi
}

#=============================================================================
# UART Setup
#=============================================================================

uart_check() {
    log "Checking UART devices..."
    
    if ls /dev/ttyUSB* /dev/ttyACM* &>/dev/null; then
        success "UART devices detected:"
        ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null | awk '{print "  " $NF}'
        return 0
    else
        warn "No UART devices detected"
        return 1
    fi
}

uart_setup() {
    log "Setting up UART ingest agent..."
    
    if [ "$MODE" = "dry-run" ]; then
        log "[DRY-RUN] Would deploy UART agent"
        return 0
    fi
    
    # Will be deployed via docker-compose
    log "UART agent will be deployed with docker-compose"
}

#=============================================================================
# MYCA Core Deployment
#=============================================================================

myca_deploy() {
    log "Deploying MYCA core services..."
    
    if [ "$MODE" = "dry-run" ]; then
        log "[DRY-RUN] Would deploy MYCA stack"
        return 0
    fi
    
    cd "$REPO_ROOT"
    
    # Deploy MYCA stack
    docker-compose -f docker-compose.yml up -d
    
    # Wait for health check
    log "Waiting for MYCA to be healthy..."
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -fsSL "http://localhost:$MYCA_PORT/health" &>/dev/null; then
            success "MYCA is healthy"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 2
    done
    
    error "MYCA failed to become healthy"
    return 1
}

myca_check() {
    log "Checking MYCA services..."
    
    local all_ok=true
    
    if curl -fsSL "http://localhost:$MYCA_PORT/health" | jq -e '.status == "healthy"' &>/dev/null; then
        success "MYCA health endpoint OK"
    else
        error "MYCA health endpoint failed"
        all_ok=false
    fi
    
    if curl -fsSL "http://localhost:$MYCA_UI_PORT" &>/dev/null; then
        success "MYCA UI endpoint OK"
    else
        error "MYCA UI endpoint failed"
        all_ok=false
    fi
    
    if [ "$all_ok" = true ]; then
        return 0
    else
        return 1
    fi
}

#=============================================================================
# Generate Output Files
#=============================================================================

generate_outputs() {
    log "Generating output files..."
    
    # connections.json
    cat > "$OUT_DIR/connections.json" <<EOF
{
  "proxmox": {
    "build": "https://$PROXMOX_BUILD",
    "dc1": "https://$PROXMOX_DC1",
    "dc2": "https://$PROXMOX_DC2"
  },
  "unifi": {
    "udm": "https://$UNIFI_UDM"
  },
  "nas": {
    "mount": "/mnt/mycosoft-nas",
    "logs": "/mnt/mycosoft-nas/logs"
  },
  "myca": {
    "api": "http://localhost:$MYCA_PORT",
    "ui": "http://localhost:$MYCA_UI_PORT",
    "health": "http://localhost:$MYCA_PORT/health"
  },
  "vault": {
    "addr": "$VAULT_ADDR"
  }
}
EOF
    
    success "Generated connections.json"
    
    # vault_paths.md
    cat > "$OUT_DIR/vault_paths.md" <<'EOF'
# Vault Secret Paths

## KV v2 Mount
- Path: `mycosoft/`

## Secrets
| Path | Keys | Description |
|------|------|-------------|
| `mycosoft/proxmox` | token_id, token_secret, hosts | Proxmox API credentials |
| `mycosoft/unifi` | api_key, host | UniFi API credentials |
| `mycosoft/nas` | protocol, ip, share, mount_point | NAS configuration |
| `mycosoft/nas_credentials` | username, password | NAS credentials (SMB only) |

## AppRole
- Role: `myca`
- Policy: `mycosoft` (read-only)
- Token TTL: 1h
- Max TTL: 4h

## Access

### Admin (root token)
```bash
export VAULT_ADDR=http://127.0.0.1:8200
vault login <root_token>
vault kv get mycosoft/proxmox
```

### AppRole (MYCA runtime)
```bash
export VAULT_ADDR=http://127.0.0.1:8200
ROLE_ID=$(cat out/secrets/.vault-role-id)
SECRET_ID=$(cat out/secrets/.vault-secret-id)
VAULT_TOKEN=$(vault write -field=token auth/approle/login role_id=$ROLE_ID secret_id=$SECRET_ID)
VAULT_TOKEN=$VAULT_TOKEN vault kv get mycosoft/proxmox
```
EOF
    
    success "Generated vault_paths.md"
    
    # audit_schema.json
    cat > "$OUT_DIR/audit_schema.json" <<'EOF'
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["timestamp", "action", "actor", "status"],
  "properties": {
    "timestamp": {
      "type": "string",
      "format": "date-time"
    },
    "action": {
      "type": "string",
      "enum": ["proxmox.inventory", "proxmox.snapshot", "proxmox.rollback", "unifi.topology", "gpu.run", "uart.ingest"]
    },
    "actor": {
      "type": "string"
    },
    "status": {
      "type": "string",
      "enum": ["success", "failure", "pending"]
    },
    "details": {
      "type": "object"
    }
  }
}
EOF
    
    success "Generated audit_schema.json"
}

#=============================================================================
# Verification
#=============================================================================

generate_verify_script() {
    log "Generating verification script..."
    
    cat > "$OUT_DIR/verify.sh" <<'VERIFY_EOF'
#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

VAULT_ADDR="http://127.0.0.1:8200"
MYCA_PORT="8001"
MYCA_UI_PORT="3001"

check() {
    local name="$1"
    local command="$2"
    
    if eval "$command" &>/dev/null; then
        echo -e "${GREEN}✓${NC} $name"
        return 0
    else
        echo -e "${RED}✗${NC} $name"
        return 1
    fi
}

echo "MYCA Bootstrap Verification"
echo "============================"
echo ""

check "Vault running" "vault status"
check "Vault unsealed" "vault status -format=json | jq -e '.sealed == false'"
check "Proxmox token in Vault" "vault kv get mycosoft/proxmox"
check "UniFi key in Vault" "vault kv get mycosoft/unifi"
check "NAS config in Vault" "vault kv get mycosoft/nas"
check "NAS mounted" "mountpoint -q /mnt/mycosoft-nas"
check "GPU available" "nvidia-smi"
check "MYCA health endpoint" "curl -fsSL http://localhost:$MYCA_PORT/health"
check "MYCA UI endpoint" "curl -fsSL http://localhost:$MYCA_UI_PORT"

echo ""
echo "Verification complete!"
VERIFY_EOF
    
    chmod +x "$OUT_DIR/verify.sh"
    success "Generated verify.sh"
}

#=============================================================================
# n8n Integration Pack
#=============================================================================

generate_n8n_pack() {
    log "Generating n8n speech interface integration pack..."
    
    # Endpoint spec
    cat > "$OUT_DIR/n8n/myca_endpoints.md" <<'EOF'
# MYCA Speech Interface Endpoints

## Core Endpoints

### Health Check
```
GET /health
Response: {"status": "healthy"}
```

### Status
```
GET /api/status
Response: {
  "services": {...},
  "vault": "connected",
  "proxmox": "ok",
  "unifi": "ok",
  "nas": "mounted"
}
```

### Speech Command
```
POST /api/speak
Body: {"text": "Hello from MYCA"}
Response: {"audio_url": "/audio/12345.mp3"}
```

### Execute Command
```
POST /api/command
Body: {"command": "proxmox.inventory", "confirm": false}
Response: {"status": "success", "data": {...}}
```

### UART Tail
```
GET /api/uart/tail?lines=100
Response: {"lines": [...]}
```

## Speech Integration Flow

1. User speaks → Browser captures audio
2. Browser sends to n8n webhook
3. n8n → Whisper STT
4. n8n → MYCA /api/command with text
5. MYCA processes command
6. MYCA response → n8n
7. n8n → ElevenLabs/TTS
8. n8n → Browser with audio response
EOF
    
    # n8n workflow scaffold
    cat > "$OUT_DIR/n8n/myca_speech_workflow.json" <<'EOF'
{
  "name": "MYCA Speech Interface",
  "nodes": [
    {
      "parameters": {
        "path": "myca-speak",
        "method": "POST"
      },
      "name": "Webhook: Receive Audio",
      "type": "n8n-nodes-base.webhook",
      "position": [250, 300]
    },
    {
      "parameters": {
        "url": "http://whisper:8000/v1/audio/transcriptions",
        "method": "POST"
      },
      "name": "Whisper STT",
      "type": "n8n-nodes-base.httpRequest",
      "position": [450, 300]
    },
    {
      "parameters": {
        "url": "http://mas-orchestrator:8000/api/command",
        "method": "POST",
        "body": {
          "command": "={{ $json.text }}"
        }
      },
      "name": "MYCA Execute",
      "type": "n8n-nodes-base.httpRequest",
      "position": [650, 300]
    },
    {
      "parameters": {
        "url": "http://elevenlabs-proxy:8000/v1/audio/speech",
        "method": "POST",
        "body": {
          "text": "={{ $json.response }}"
        }
      },
      "name": "TTS",
      "type": "n8n-nodes-base.httpRequest",
      "position": [850, 300]
    },
    {
      "parameters": {},
      "name": "Return Audio",
      "type": "n8n-nodes-base.respondToWebhook",
      "position": [1050, 300]
    }
  ],
  "connections": {
    "Webhook: Receive Audio": {
      "main": [[{"node": "Whisper STT", "type": "main", "index": 0}]]
    },
    "Whisper STT": {
      "main": [[{"node": "MYCA Execute", "type": "main", "index": 0}]]
    },
    "MYCA Execute": {
      "main": [[{"node": "TTS", "type": "main", "index": 0}]]
    },
    "TTS": {
      "main": [[{"node": "Return Audio", "type": "main", "index": 0}]]
    }
  }
}
EOF
    
    # UI plan
    cat > "$OUT_DIR/n8n/ui_plan.md" <<'EOF'
# MYCA Speech UI Plan (Phase 2)

## Components Needed

1. **Push-to-Talk Button**
   - HTML5 MediaRecorder API
   - Capture audio from microphone
   - Send to n8n webhook

2. **Audio Playback**
   - Play TTS response
   - Visual feedback during playback

3. **Status Display**
   - Show current command
   - Display MYCA status

## Implementation Checklist

- [ ] Create HTML UI with microphone button
- [ ] Implement MediaRecorder for audio capture
- [ ] Send audio to n8n webhook
- [ ] Receive and play TTS response
- [ ] Add visual feedback (recording, processing, speaking)
- [ ] Error handling

## Security Considerations

- HTTPS required for getUserMedia()
- CORS configuration for n8n webhooks
- Rate limiting on speech endpoints

## Testing Without Microphone

Use curl to test endpoints:

```bash
# Test speech endpoint
curl -X POST http://localhost:5678/webhook/myca-speak \
  -H "Content-Type: application/json" \
  -d '{"text": "get proxmox inventory"}'
```
EOF
    
    success "Generated n8n integration pack"
}

#=============================================================================
# Main Execution
#=============================================================================

run_dry_run() {
    section "DRY RUN MODE - Checking Prerequisites"
    
    local all_ok=true
    
    log "Checking commands..."
    check_command curl || all_ok=false
    check_command docker || all_ok=false
    check_command jq || all_ok=false
    
    echo ""
    vault_check || warn "Vault needs setup"
    proxmox_check || warn "Proxmox connectivity issues"
    unifi_check || warn "UniFi connectivity issues"
    nas_check || warn "NAS needs mounting"
    gpu_check || warn "GPU not detected (optional)"
    uart_check || warn "UART not detected (optional)"
    
    echo ""
    log "Dry run complete. Run with 'apply' to execute setup."
}

run_apply() {
    section "APPLY MODE - Setting Up MYCA Infrastructure"
    
    init_dirs
    
    section "1/10 Vault Setup"
    vault_install
    vault_init
    vault_configure
    
    section "2/10 Proxmox Integration"
    proxmox_setup
    
    section "3/10 UniFi Integration"
    unifi_setup
    
    section "4/10 NAS Setup"
    nas_setup
    
    section "5/10 GPU Setup"
    gpu_check && gpu_setup || warn "GPU setup skipped"
    
    section "6/10 UART Setup"
    uart_check && uart_setup || warn "UART setup skipped"
    
    section "7/10 Generate Docker Compose Files"
    generate_docker_compose
    
    section "8/10 Deploy MYCA Core"
    myca_deploy
    
    section "9/10 Generate Output Files"
    generate_outputs
    generate_verify_script
    
    section "10/10 Generate n8n Integration Pack"
    generate_n8n_pack
    
    section "BOOTSTRAP COMPLETE!"
    
    cat <<EOF

${GREEN}════════════════════════════════════════════════════════════════
MYCA is now online!
════════════════════════════════════════════════════════════════${NC}

Endpoints:
  - API:    http://localhost:$MYCA_PORT
  - UI:     http://localhost:$MYCA_UI_PORT
  - Health: http://localhost:$MYCA_PORT/health
  - Vault:  $VAULT_ADDR

Run verification:
  bash $OUT_DIR/verify.sh

Vault access:
  export VAULT_ADDR=$VAULT_ADDR
  vault login <root_token>

Next steps:
  1. Review n8n integration pack in $OUT_DIR/n8n/
  2. Test endpoints with curl
  3. Deploy n8n workflow (when ready)

EOF
}

run_verify() {
    if [ -f "$OUT_DIR/verify.sh" ]; then
        bash "$OUT_DIR/verify.sh"
    else
        error "verify.sh not found. Run 'apply' first."
        exit 1
    fi
}

generate_docker_compose() {
    log "Generating docker-compose.myca.yml..."
    
    cat > "$REPO_ROOT/docker-compose.myca.yml" <<'EOF'
version: "3.9"

services:
  myca-orchestrator:
    extends:
      file: docker-compose.yml
      service: mas-orchestrator
    environment:
      - VAULT_ADDR=http://host.docker.internal:8200
    volumes:
      - /mnt/mycosoft-nas/logs:/app/nas-logs
    extra_hosts:
      - "host.docker.internal:host-gateway"
  
  vault-agent:
    image: hashicorp/vault:latest
    command: agent -config=/vault/config/agent.hcl
    volumes:
      - ./infra/myca-online/templates:/vault/templates
      - ./infra/myca-online/out/vault:/vault/config
    environment:
      - VAULT_ADDR=http://host.docker.internal:8200
    extra_hosts:
      - "host.docker.internal:host-gateway"
    profiles: ["vault-agent"]

  uart-agent:
    build:
      context: ./infra/myca-online/docker
      dockerfile: Dockerfile.uart
    devices:
      - /dev/ttyUSB0:/dev/ttyUSB0
    volumes:
      - /mnt/mycosoft-nas/logs:/logs
    profiles: ["hardware"]

  gpu-runner:
    image: nvidia/cuda:12.3.0-runtime-ubuntu22.04
    command: sleep infinity
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    volumes:
      - /mnt/mycosoft-nas/logs:/logs
    profiles: ["gpu"]

networks:
  default:
    name: mas-network
    external: true
EOF
    
    success "Generated docker-compose.myca.yml"
}

show_help() {
    cat <<EOF
MYCA Bootstrap - Bring MYCA MAS Fully Online

Usage:
  $0 <mode>

Modes:
  dry-run    Check prerequisites without making changes
  apply      Full setup (interactive)
  verify     Re-run verification checks
  help       Show this message

Examples:
  $0 dry-run
  $0 apply
  $0 verify

EOF
}

#=============================================================================
# Entry Point
#=============================================================================

case "$MODE" in
    dry-run)
        run_dry_run
        ;;
    apply)
        run_apply
        ;;
    verify)
        run_verify
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        error "Unknown mode: $MODE"
        show_help
        exit 1
        ;;
esac
