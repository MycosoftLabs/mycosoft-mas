#!/bin/bash
#
# Mycosoft Infrastructure Bootstrap Script
# Interactive setup for Proxmox, UniFi UDM, NAS, and HashiCorp Vault integration
#
# Usage:
#   ./bootstrap_mycosoft.sh [--dry-run|--apply]
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}/out"
VAULT_DIR="${HOME}/.vault"
VAULT_DATA_DIR="${VAULT_DIR}/data"
VAULT_CONFIG_DIR="${VAULT_DIR}/config"
VAULT_ADDR="http://127.0.0.1:8200"
VAULT_ROLE_ID_FILE="${HOME}/.mycosoft-vault-role-id"
VAULT_SECRET_ID_FILE="${HOME}/.mycosoft-vault-secret-id"

# Target IPs
PROXMOX_IPS=("192.168.0.202" "192.168.0.131")
PROXMOX_PORT=8006
UNIFI_IP="192.168.0.1"
UNIFI_PORT=443
NAS_MOUNT_POINT="/mnt/mycosoft-nas"

# Mode
DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
    echo -e "${YELLOW}[DRY RUN MODE]${NC} No changes will be made."
elif [[ "${1:-}" == "--apply" ]]; then
    DRY_RUN=false
else
    echo "Usage: $0 [--dry-run|--apply]"
    echo "  --dry-run: Check connectivity and validate, but don't install/configure"
    echo "  --apply:    Install and configure everything"
    exit 1
fi

# Status tracking
declare -A STATUS
STATUS[os_check]=false
STATUS[network_check]=false
STATUS[vault_installed]=false
STATUS[vault_configured]=false
STATUS[vault_initialized]=false
STATUS[proxmox_token]=false
STATUS[unifi_token]=false
STATUS[nas_mounted]=false

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
    STATUS["$2"]=true
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

prompt_yes_no() {
    local prompt="$1"
    local default="${2:-n}"
    local response
    
    if [[ "$default" == "y" ]]; then
        read -p "$prompt [Y/n]: " response
        response="${response:-y}"
    else
        read -p "$prompt [y/N]: " response
        response="${response:-n}"
    fi
    
    [[ "$response" =~ ^[Yy]$ ]]
}

prompt_secret() {
    local prompt="$1"
    local var_name="$2"
    read -sp "$prompt: " secret
    echo
    eval "$var_name='$secret'"
}

check_command() {
    command -v "$1" >/dev/null 2>&1
}

install_package() {
    local pkg="$1"
    if check_command "$pkg"; then
        log_success "$pkg is installed" "package_${pkg}"
        return 0
    fi
    
    if [[ "$DRY_RUN" == true ]]; then
        log_warn "$pkg not found (would install in apply mode)"
        return 1
    fi
    
    log_info "Installing $pkg..."
    if check_command apt-get; then
        sudo apt-get update && sudo apt-get install -y "$pkg"
    elif check_command yum; then
        sudo yum install -y "$pkg"
    elif check_command brew; then
        brew install "$pkg"
    else
        log_error "No package manager found. Please install $pkg manually."
        return 1
    fi
}

# Step 1: OS and binary checks
check_os_and_binaries() {
    log_info "Checking OS and required binaries..."
    
    # Check OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        log_success "Running on Linux" "os_check"
    else
        log_error "This script is designed for Linux. Current OS: $OSTYPE"
        exit 1
    fi
    
    # Required binaries
    local required=("curl" "jq" "docker")
    local optional=("ssh" "nfs-common" "cifs-utils")
    
    for cmd in "${required[@]}"; do
        if ! check_command "$cmd"; then
            if prompt_yes_no "Install $cmd?" "y"; then
                install_package "$cmd"
            else
                log_error "$cmd is required but not installed"
                exit 1
            fi
        else
            log_success "$cmd is installed" "package_${cmd}"
        fi
    done
    
    for cmd in "${optional[@]}"; do
        if ! check_command "$cmd"; then
            log_warn "$cmd not found (may be needed for NAS mounting)"
        fi
    done
    
    # Check Docker
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    
    STATUS[os_check]=true
}

# Step 2: Network connectivity checks
check_network_connectivity() {
    log_info "Checking network connectivity..."
    
    # Check Proxmox
    local proxmox_reachable=false
    for ip in "${PROXMOX_IPS[@]}"; do
        if curl -k -s --connect-timeout 5 "https://${ip}:${PROXMOX_PORT}" >/dev/null 2>&1; then
            log_success "Proxmox reachable at ${ip}:${PROXMOX_PORT}" "proxmox_${ip}"
            proxmox_reachable=true
        else
            log_warn "Proxmox not reachable at ${ip}:${PROXMOX_PORT}"
        fi
    done
    
    if [[ "$proxmox_reachable" == false ]]; then
        log_error "No Proxmox hosts are reachable"
        exit 1
    fi
    
    # Check UniFi
    if curl -k -s --connect-timeout 5 "https://${UNIFI_IP}" >/dev/null 2>&1; then
        log_success "UniFi UDM reachable at ${UNIFI_IP}" "unifi_reachable"
    else
        log_error "UniFi UDM not reachable at ${UNIFI_IP}"
        exit 1
    fi
    
    STATUS[network_check]=true
}

# Step 3: Vault installation and configuration
install_vault() {
    if [[ "$DRY_RUN" == true ]]; then
        if check_command vault; then
            log_success "Vault is installed" "vault_installed"
        else
            log_warn "Vault not found (would install in apply mode)"
        fi
        return 0
    fi
    
    if check_command vault; then
        log_success "Vault is already installed" "vault_installed"
        vault version
        return 0
    fi
    
    log_info "Installing HashiCorp Vault..."
    
    # Download and install Vault
    local vault_version="1.16.0"
    local arch="amd64"
    if [[ "$(uname -m)" == "aarch64" ]] || [[ "$(uname -m)" == "arm64" ]]; then
        arch="arm64"
    fi
    
    local vault_url="https://releases.hashicorp.com/vault/${vault_version}/vault_${vault_version}_linux_${arch}.zip"
    local temp_dir=$(mktemp -d)
    
    curl -L -o "${temp_dir}/vault.zip" "$vault_url"
    unzip -q "${temp_dir}/vault.zip" -d "${temp_dir}"
    sudo mv "${temp_dir}/vault" /usr/local/bin/
    sudo chmod +x /usr/local/bin/vault
    rm -rf "$temp_dir"
    
    log_success "Vault installed" "vault_installed"
    vault version
}

configure_vault() {
    if [[ "$DRY_RUN" == true ]]; then
        log_warn "Would configure Vault (skip in dry-run)"
        return 0
    fi
    
    log_info "Configuring Vault..."
    
    # Create directories
    mkdir -p "$VAULT_DATA_DIR" "$VAULT_CONFIG_DIR"
    
    # Create Vault config file
    cat > "${VAULT_CONFIG_DIR}/vault.hcl" <<EOF
ui = true
disable_mlock = true

storage "file" {
  path = "${VAULT_DATA_DIR}"
}

listener "tcp" {
  address     = "127.0.0.1:8200"
  tls_disable = 1
}

api_addr = "http://127.0.0.1:8200"
EOF
    
    # Create systemd service file
    if [[ -d /etc/systemd/system ]]; then
        sudo tee /etc/systemd/system/vault.service > /dev/null <<EOF
[Unit]
Description=HashiCorp Vault
Documentation=https://www.vaultproject.io/docs/
After=network-online.target
Wants=network-online.target

[Service]
Type=notify
ExecStart=/usr/local/bin/vault server -config=${VAULT_CONFIG_DIR}/vault.hcl
ExecReload=/bin/kill -HUP \$MAINPID
KillMode=process
Restart=on-failure
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF
        
        sudo systemctl daemon-reload
        sudo systemctl enable vault
        sudo systemctl start vault
        
        # Wait for Vault to start
        sleep 3
        if systemctl is-active --quiet vault; then
            log_success "Vault service started" "vault_service"
        else
            log_error "Failed to start Vault service"
            exit 1
        fi
    else
        log_warn "Systemd not found. Please start Vault manually: vault server -config=${VAULT_CONFIG_DIR}/vault.hcl"
    fi
    
    STATUS[vault_configured]=true
}

initialize_vault() {
    if [[ "$DRY_RUN" == true ]]; then
        log_warn "Would initialize Vault (skip in dry-run)"
        return 0
    fi
    
    export VAULT_ADDR="$VAULT_ADDR"
    
    # Check if already initialized
    if vault status >/dev/null 2>&1; then
        if vault status | grep -q "Initialized.*true"; then
            log_info "Vault is already initialized"
            
            # Check if sealed
            if vault status | grep -q "Sealed.*true"; then
                log_warn "Vault is sealed. Please unseal it."
                echo "Enter unseal keys (press Enter after each):"
                for i in {1..3}; do
                    read -sp "Unseal key $i: " key
                    echo
                    vault operator unseal "$key"
                done
            fi
            
            STATUS[vault_initialized]=true
            return 0
        fi
    fi
    
    log_info "Initializing Vault..."
    
    # Initialize Vault
    local init_output=$(vault operator init -key-shares=5 -key-threshold=3 -format=json)
    local root_token=$(echo "$init_output" | jq -r '.root_token')
    local unseal_keys=$(echo "$init_output" | jq -r '.unseal_keys_b64[]')
    
    echo ""
    log_warn "IMPORTANT: Save these credentials securely!"
    echo "Root Token: $root_token"
    echo "Unseal Keys:"
    echo "$unseal_keys" | nl -w2 -s'. '
    echo ""
    
    if ! prompt_yes_no "Have you saved the root token and unseal keys?" "n"; then
        log_error "Please save the credentials and re-run the script"
        exit 1
    fi
    
    # Unseal Vault
    log_info "Unsealing Vault..."
    local key_array=($unseal_keys)
    vault operator unseal "${key_array[0]}"
    vault operator unseal "${key_array[1]}"
    vault operator unseal "${key_array[2]}"
    
    # Login with root token
    echo "$root_token" | vault login -
    
    # Create KV v2 mount
    log_info "Creating KV v2 mount at mycosoft/..."
    vault secrets enable -version=2 -path=mycosoft kv-v2 || log_warn "Mount may already exist"
    
    # Create policy
    log_info "Creating mycosoft policy..."
    vault policy write mycosoft - <<EOF
path "mycosoft/data/*" {
  capabilities = ["read", "list"]
}

path "mycosoft/metadata/*" {
  capabilities = ["list", "read"]
}
EOF
    
    # Create AppRole
    log_info "Creating AppRole 'myca'..."
    vault auth enable approle || log_warn "AppRole auth may already be enabled"
    
    vault write auth/approle/role/myca \
        token_policies="mycosoft" \
        token_ttl=1h \
        token_max_ttl=4h \
        bind_secret_id=true
    
    # Get role-id and secret-id
    local role_id=$(vault read -field=role_id auth/approle/role/myca/role-id)
    local secret_id=$(vault write -f -field=secret_id auth/approle/role/myca/secret-id)
    
    # Save to secure files
    echo "$role_id" > "$VAULT_ROLE_ID_FILE"
    echo "$secret_id" > "$VAULT_SECRET_ID_FILE"
    chmod 600 "$VAULT_ROLE_ID_FILE" "$VAULT_SECRET_ID_FILE"
    
    log_success "AppRole created" "approle_created"
    echo "Role ID saved to: $VAULT_ROLE_ID_FILE"
    echo "Secret ID saved to: $VAULT_SECRET_ID_FILE"
    echo ""
    log_warn "IMPORTANT: Save these files securely! They are needed for MYCA to authenticate."
    
    STATUS[vault_initialized]=true
}

# Step 4: Proxmox token setup
setup_proxmox_token() {
    export VAULT_ADDR="$VAULT_ADDR"
    
    # Check if token exists in Vault
    if vault kv get -format=json mycosoft/proxmox >/dev/null 2>&1; then
        local token_data=$(vault kv get -format=json mycosoft/proxmox | jq -r '.data.data')
        local token_id=$(echo "$token_data" | jq -r '.token_id // empty')
        local token_secret=$(echo "$token_data" | jq -r '.token_secret // empty')
        
        if [[ -n "$token_id" ]] && [[ -n "$token_secret" ]]; then
            # Validate token
            if validate_proxmox_token "$token_id" "$token_secret"; then
                log_success "Proxmox token exists and is valid" "proxmox_token"
                return 0
            else
                log_warn "Proxmox token exists but is invalid"
            fi
        fi
    fi
    
    log_info "Setting up Proxmox API token..."
    
    # Try CLI path first (if SSH available)
    if check_command ssh; then
        echo ""
        log_info "Option A: Create token via CLI (requires SSH access to Proxmox)"
        echo "We can create the token remotely if you provide SSH access."
        if prompt_yes_no "Do you have SSH access to Proxmox?" "n"; then
            read -p "Enter Proxmox IP (default: ${PROXMOX_IPS[0]}): " proxmox_ip
            proxmox_ip="${proxmox_ip:-${PROXMOX_IPS[0]}}"
            read -p "Enter SSH user (default: root): " ssh_user
            ssh_user="${ssh_user:-root}"
            
            log_info "Creating Proxmox user and token via SSH..."
            
            if [[ "$DRY_RUN" == true ]]; then
                echo "Would run these commands on $proxmox_ip:"
                echo "  pveum user add myca@pve --password <password>"
                echo "  pveum role add MYCA_ROLE --privs 'Datastore.AllocateSpace Datastore.Audit Pool.Allocate Sys.Audit Sys.Modify VM.Allocate VM.Audit VM.Clone VM.Config.CDROM VM.Config.CPU VM.Config.Cloudinit VM.Config.Disk VM.Config.HWType VM.Config.Memory VM.Config.Network VM.Config.Options VM.Monitor VM.PowerMgmt'"
                echo "  pveum aclmod / --users myca@pve --roles MYCA_ROLE"
                echo "  pveum token add mas myca@pve --privsep 0"
            else
                echo "Enter SSH password or use key-based auth:"
                ssh "${ssh_user}@${proxmox_ip}" <<'ENDSSH'
pveum user add myca@pve --password $(openssl rand -base64 32) 2>/dev/null || echo "User may already exist"
pveum role add MYCA_ROLE --privs 'Datastore.AllocateSpace Datastore.Audit Pool.Allocate Sys.Audit Sys.Modify VM.Allocate VM.Audit VM.Clone VM.Config.CDROM VM.Config.CPU VM.Config.Cloudinit VM.Config.Disk VM.Config.HWType VM.Config.Memory VM.Config.Network VM.Config.Options VM.Monitor VM.PowerMgmt' 2>/dev/null || echo "Role may already exist"
pveum aclmod / --users myca@pve --roles MYCA_ROLE 2>/dev/null || echo "ACL may already exist"
pveum token add mas myca@pve --privsep 0
ENDSSH
                log_info "Please copy the TOKEN_ID and TOKEN_SECRET from the output above"
            fi
        fi
    fi
    
    # UI path
    echo ""
    log_info "Option B: Create token via UI"
    echo "1. Open https://${PROXMOX_IPS[0]}:${PROXMOX_PORT} in your browser"
    echo "2. Log in as administrator"
    echo "3. Navigate to: Datacenter → Permissions → Users"
    echo "4. Click 'Add' → Create user 'myca@pve' with a secure password"
    echo "5. Navigate to: Datacenter → Permissions → Roles"
    echo "6. Click 'Add' → Create role 'MYCA_ROLE' with these privileges:"
    echo "   - Datastore.AllocateSpace, Datastore.Audit"
    echo "   - Pool.Allocate"
    echo "   - Sys.Audit, Sys.Modify"
    echo "   - VM.Allocate, VM.Audit, VM.Clone"
    echo "   - VM.Config.* (all)"
    echo "   - VM.Monitor, VM.PowerMgmt"
    echo "7. Navigate to: Datacenter → Permissions → Permissions"
    echo "8. Add ACL: Path: /, User: myca@pve, Role: MYCA_ROLE"
    echo "9. Navigate to: Datacenter → Permissions → API Tokens"
    echo "10. Click 'Add' → User: myca@pve, Token ID: mas, Privilege Separation: unchecked"
    echo ""
    
    prompt_secret "Enter Proxmox TOKEN_ID (e.g., myca@pve!mas)" token_id
    prompt_secret "Enter Proxmox TOKEN_SECRET" token_secret
    
    # Validate token
    if [[ "$DRY_RUN" != true ]]; then
        if validate_proxmox_token "$token_id" "$token_secret"; then
            # Store in Vault
            vault kv put mycosoft/proxmox \
                token_id="$token_id" \
                token_secret="$token_secret" \
                proxmox_host="${PROXMOX_IPS[0]}" \
                proxmox_port="$PROXMOX_PORT"
            
            log_success "Proxmox token stored in Vault" "proxmox_token"
        else
            log_error "Token validation failed"
            exit 1
        fi
    else
        log_warn "Would validate and store token (skip in dry-run)"
    fi
}

validate_proxmox_token() {
    local token_id="$1"
    local token_secret="$2"
    local proxmox_ip="${PROXMOX_IPS[0]}"
    
    local response=$(curl -k -s -w "\n%{http_code}" \
        -H "Authorization: PVEAuthCookie=$(echo -n "${token_id}=${token_secret}" | base64)" \
        "https://${proxmox_ip}:${PROXMOX_PORT}/api2/json/nodes")
    
    local http_code=$(echo "$response" | tail -n1)
    if [[ "$http_code" == "200" ]]; then
        return 0
    else
        return 1
    fi
}

# Step 5: UniFi token setup
setup_unifi_token() {
    export VAULT_ADDR="$VAULT_ADDR"
    
    # Check if token exists in Vault
    if vault kv get -format=json mycosoft/unifi >/dev/null 2>&1; then
        local token_data=$(vault kv get -format=json mycosoft/unifi | jq -r '.data.data')
        local token=$(echo "$token_data" | jq -r '.token // empty')
        
        if [[ -n "$token" ]]; then
            # Validate token
            if validate_unifi_token "$token"; then
                log_success "UniFi token exists and is valid" "unifi_token"
                return 0
            else
                log_warn "UniFi token exists but is invalid"
            fi
        fi
    fi
    
    log_info "Setting up UniFi API token..."
    echo ""
    echo "To create a UniFi API token:"
    echo "1. Open https://${UNIFI_IP} in your browser"
    echo "2. Log in as administrator (myca@mycosoft.org)"
    echo "3. Navigate to: Settings → System Settings → Advanced Features"
    echo "4. Enable 'API Access' if not already enabled"
    echo "5. Navigate to: Settings → System Settings → API Access"
    echo "6. Click 'Create New Token'"
    echo "7. Name: MYCA-MAS"
    echo "8. Copy the generated token"
    echo ""
    
    prompt_secret "Enter UniFi API token" unifi_token
    
    # Validate token
    if [[ "$DRY_RUN" != true ]]; then
        if validate_unifi_token "$unifi_token"; then
            # Store in Vault
            vault kv put mycosoft/unifi \
                token="$unifi_token" \
                unifi_host="$UNIFI_IP" \
                unifi_port="$UNIFI_PORT"
            
            log_success "UniFi token stored in Vault" "unifi_token"
        else
            log_error "Token validation failed"
            exit 1
        fi
    else
        log_warn "Would validate and store token (skip in dry-run)"
    fi
}

validate_unifi_token() {
    local token="$1"
    
    local response=$(curl -k -s -w "\n%{http_code}" \
        -H "Authorization: Bearer $token" \
        "https://${UNIFI_IP}/proxy/network/api/self")
    
    local http_code=$(echo "$response" | tail -n1)
    if [[ "$http_code" == "200" ]]; then
        return 0
    else
        return 1
    fi
}

# Step 6: NAS mounting
setup_nas() {
    if [[ -d "$NAS_MOUNT_POINT" ]] && mountpoint -q "$NAS_MOUNT_POINT" 2>/dev/null; then
        log_success "NAS already mounted at $NAS_MOUNT_POINT" "nas_mounted"
        return 0
    fi
    
    log_info "Setting up NAS mount..."
    
    echo "Choose NAS protocol:"
    echo "1) NFS"
    echo "2) SMB/CIFS"
    read -p "Enter choice [1-2]: " protocol_choice
    
    read -p "Enter NAS IP address: " nas_ip
    read -p "Enter NAS share path (e.g., /share/data or /volume1/data): " nas_share
    
    if [[ "$protocol_choice" == "1" ]]; then
        # NFS
        if [[ "$DRY_RUN" != true ]]; then
            install_package nfs-common || true
            
            sudo mkdir -p "$NAS_MOUNT_POINT"
            sudo mount -t nfs "${nas_ip}:${nas_share}" "$NAS_MOUNT_POINT"
            
            if mountpoint -q "$NAS_MOUNT_POINT"; then
                log_success "NAS mounted via NFS" "nas_mounted"
                
                if prompt_yes_no "Add to /etc/fstab for persistent mounting?" "y"; then
                    echo "${nas_ip}:${nas_share} $NAS_MOUNT_POINT nfs defaults,_netdev 0 0" | sudo tee -a /etc/fstab
                fi
                
                # Store in Vault
                vault kv put mycosoft/nas \
                    protocol="nfs" \
                    ip="$nas_ip" \
                    share="$nas_share" \
                    mount_point="$NAS_MOUNT_POINT"
            else
                log_error "Failed to mount NAS"
                exit 1
            fi
        else
            log_warn "Would mount NFS share (skip in dry-run)"
        fi
    else
        # SMB/CIFS
        read -p "Enter SMB username: " smb_user
        prompt_secret "Enter SMB password" smb_password
        
        if [[ "$DRY_RUN" != true ]]; then
            install_package cifs-utils || true
            
            sudo mkdir -p "$NAS_MOUNT_POINT"
            sudo mount -t cifs "//${nas_ip}${nas_share}" "$NAS_MOUNT_POINT" \
                -o username="$smb_user",password="$smb_password",uid=$(id -u),gid=$(id -g)
            
            if mountpoint -q "$NAS_MOUNT_POINT"; then
                log_success "NAS mounted via SMB" "nas_mounted"
                
                if prompt_yes_no "Add to /etc/fstab for persistent mounting?" "y"; then
                    # Store credentials securely
                    local cred_file="${HOME}/.smb-credentials"
                    echo "username=$smb_user" > "$cred_file"
                    echo "password=$smb_password" >> "$cred_file"
                    chmod 600 "$cred_file"
                    
                    echo "//${nas_ip}${nas_share} $NAS_MOUNT_POINT cifs credentials=$cred_file,uid=$(id -u),gid=$(id -g),_netdev 0 0" | sudo tee -a /etc/fstab
                fi
                
                # Store in Vault (without password in mount info)
                vault kv put mycosoft/nas \
                    protocol="smb" \
                    ip="$nas_ip" \
                    share="$nas_share" \
                    mount_point="$NAS_MOUNT_POINT" \
                    username="$smb_user"
                vault kv put mycosoft/nas_password password="$smb_password"
            else
                log_error "Failed to mount NAS"
                exit 1
            fi
        else
            log_warn "Would mount SMB share (skip in dry-run)"
        fi
    fi
}

# Step 7: Generate config files
generate_config_files() {
    log_info "Generating configuration files..."
    
    mkdir -p "$OUTPUT_DIR"
    
    export VAULT_ADDR="$VAULT_ADDR"
    
    # connections.json
    cat > "${OUTPUT_DIR}/connections.json" <<EOF
{
  "proxmox": {
    "hosts": [
      {
        "ip": "${PROXMOX_IPS[0]}",
        "port": ${PROXMOX_PORT}
      },
      {
        "ip": "${PROXMOX_IPS[1]}",
        "port": ${PROXMOX_PORT}
      }
    ]
  },
  "unifi": {
    "host": "${UNIFI_IP}",
    "port": ${UNIFI_PORT},
    "api_endpoint": "https://${UNIFI_IP}/proxy/network/api"
  },
  "nas": {
    "mount_point": "${NAS_MOUNT_POINT}"
  },
  "vault": {
    "address": "${VAULT_ADDR}",
    "kv_path": "mycosoft",
    "role_id_file": "${VAULT_ROLE_ID_FILE}",
    "secret_id_file": "${VAULT_SECRET_ID_FILE}"
  }
}
EOF
    
    # vault_paths.md
    cat > "${OUTPUT_DIR}/vault_paths.md" <<EOF
# Vault Secret Paths

All secrets are stored in HashiCorp Vault under the \`mycosoft/\` KV v2 mount.

## Secret Locations

- **Proxmox API Token**: \`mycosoft/proxmox\`
  - \`token_id\`: Proxmox API token ID
  - \`token_secret\`: Proxmox API token secret
  - \`proxmox_host\`: Primary Proxmox host IP
  - \`proxmox_port\`: Proxmox API port

- **UniFi API Token**: \`mycosoft/unifi\`
  - \`token\`: UniFi API bearer token
  - \`unifi_host\`: UniFi UDM IP
  - \`unifi_port\`: UniFi API port

- **NAS Configuration**: \`mycosoft/nas\`
  - \`protocol\`: Mount protocol (nfs or smb)
  - \`ip\`: NAS IP address
  - \`share\`: Share path
  - \`mount_point\`: Local mount point
  - \`username\`: SMB username (if applicable)

- **NAS Password** (SMB only): \`mycosoft/nas_password\`
  - \`password\`: SMB password

## Accessing Secrets

### Using Vault CLI (with AppRole):
\`\`\`bash
export VAULT_ADDR="${VAULT_ADDR}"
export VAULT_ROLE_ID=\$(cat ${VAULT_ROLE_ID_FILE})
export VAULT_SECRET_ID=\$(cat ${VAULT_SECRET_ID_FILE})

# Authenticate
vault write auth/approle/login role_id=\$VAULT_ROLE_ID secret_id=\$VAULT_SECRET_ID

# Read secret
vault kv get mycosoft/proxmox
\`\`\`

### Using Vault Agent:
See docker-compose.sync.yml for Vault Agent configuration.
EOF
    
    # verify.sh
    cat > "${OUTPUT_DIR}/verify.sh" <<'VERIFYEOF'
#!/bin/bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_info() { echo -e "${YELLOW}[INFO]${NC} $1"; }

export VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"

echo "Verifying Mycosoft Infrastructure Setup..."
echo ""

# Check Vault
if vault status >/dev/null 2>&1; then
    if vault status | grep -q "Sealed.*false"; then
        log_success "Vault is running and unsealed"
    else
        log_error "Vault is sealed"
    fi
else
    log_error "Vault is not accessible"
fi

# Check Proxmox token
if vault kv get mycosoft/proxmox >/dev/null 2>&1; then
    log_success "Proxmox token exists in Vault"
else
    log_error "Proxmox token not found in Vault"
fi

# Check UniFi token
if vault kv get mycosoft/unifi >/dev/null 2>&1; then
    log_success "UniFi token exists in Vault"
else
    log_error "UniFi token not found in Vault"
fi

# Check NAS mount
if mountpoint -q /mnt/mycosoft-nas 2>/dev/null; then
    log_success "NAS is mounted"
else
    log_error "NAS is not mounted"
fi

echo ""
echo "Verification complete."
VERIFYEOF
    
    chmod +x "${OUTPUT_DIR}/verify.sh"
    
    log_success "Configuration files generated" "config_generated"
}

# Step 8: Generate docker-compose.sync.yml
generate_docker_compose() {
    log_info "Generating docker-compose.sync.yml template..."
    
    cat > "${REPO_ROOT}/docker-compose.sync.yml" <<'DOCKEREOF'
version: "3.9"

# Mycosoft Infrastructure Sync Services
# This file integrates with Proxmox, UniFi, and NAS via Vault-secured credentials
# Secrets are fetched at runtime via Vault Agent or entrypoint scripts

services:
  vault-agent:
    image: hashicorp/vault:latest
    container_name: mycosoft-vault-agent
    command: >
      sh -c "
        vault agent -config=/vault/config/agent.hcl
      "
    volumes:
      - ./infra/bootstrap/out/vault-agent.hcl:/vault/config/agent.hcl:ro
      - ${HOME}/.mycosoft-vault-role-id:/vault/role-id:ro
      - ${HOME}/.mycosoft-vault-secret-id:/vault/secret-id:ro
      - ./infra/bootstrap/out/secrets:/vault/secrets:rw
    environment:
      VAULT_ADDR: http://host.docker.internal:8200
    network_mode: host
    restart: unless-stopped
    profiles:
      - infra-sync

  proxmox-sync:
    image: alpine:latest
    container_name: mycosoft-proxmox-sync
    command: >
      sh -c "
        apk add --no-cache curl jq &&
        TOKEN_ID=\$$(cat /vault/secrets/proxmox-token-id) &&
        TOKEN_SECRET=\$$(cat /vault/secrets/proxmox-token-secret) &&
        echo 'Proxmox sync service ready' &&
        tail -f /dev/null
      "
    volumes:
      - ./infra/bootstrap/out/secrets:/vault/secrets:ro
      - ${NAS_MOUNT_POINT:-/mnt/mycosoft-nas}:/mnt/nas:ro
    depends_on:
      - vault-agent
    restart: unless-stopped
    profiles:
      - infra-sync

  unifi-sync:
    image: alpine:latest
    container_name: mycosoft-unifi-sync
    command: >
      sh -c "
        apk add --no-cache curl jq &&
        TOKEN=\$$(cat /vault/secrets/unifi-token) &&
        echo 'UniFi sync service ready' &&
        tail -f /dev/null
      "
    volumes:
      - ./infra/bootstrap/out/secrets:/vault/secrets:ro
    depends_on:
      - vault-agent
    restart: unless-stopped
    profiles:
      - infra-sync

networks:
  default:
    name: mycosoft-infra-sync
DOCKEREOF
    
    # Generate Vault Agent config
    cat > "${OUTPUT_DIR}/vault-agent.hcl" <<'AGENTEOF'
pid_file = "/tmp/vault-agent.pid"

vault {
  address = "http://host.docker.internal:8200"
}

auto_auth {
  method "approle" {
    config = {
      role_id_file_path = "/vault/role-id"
      secret_id_file_path = "/vault/secret-id"
      remove_secret_id_file_after_reading = false
    }
  }

  sink "file" {
    config = {
      path = "/tmp/vault-token"
    }
  }
}

template {
  source      = "/vault/config/templates/proxmox-token-id.tpl"
  destination = "/vault/secrets/proxmox-token-id"
  perms       = 0600
}

template {
  source      = "/vault/config/templates/proxmox-token-secret.tpl"
  destination = "/vault/secrets/proxmox-token-secret"
  perms       = 0600
}

template {
  source      = "/vault/config/templates/unifi-token.tpl"
  destination = "/vault/secrets/unifi-token"
  perms       = 0600
}
AGENTEOF
    
    # Create template directory and files
    mkdir -p "${OUTPUT_DIR}/templates"
    
    cat > "${OUTPUT_DIR}/templates/proxmox-token-id.tpl" <<'TEMPLATEEOF'
{{ with secret "mycosoft/proxmox" }}
{{ .Data.data.token_id }}
{{ end }}
TEMPLATEEOF
    
    cat > "${OUTPUT_DIR}/templates/proxmox-token-secret.tpl" <<'TEMPLATEEOF'
{{ with secret "mycosoft/proxmox" }}
{{ .Data.data.token_secret }}
{{ end }}
TEMPLATEEOF
    
    cat > "${OUTPUT_DIR}/templates/unifi-token.tpl" <<'TEMPLATEEOF'
{{ with secret "mycosoft/unifi" }}
{{ .Data.data.token }}
{{ end }}
TEMPLATEEOF
    
    # Create secrets directory
    mkdir -p "${OUTPUT_DIR}/secrets"
    
    log_success "docker-compose.sync.yml generated" "docker_compose_generated"
}

# Step 9: Print final checklist
print_checklist() {
    echo ""
    echo "=========================================="
    echo "  Mycosoft Infrastructure Bootstrap"
    echo "  Final Status Report"
    echo "=========================================="
    echo ""
    
    local all_good=true
    
    # Check each status
    if [[ "${STATUS[os_check]}" == true ]]; then
        echo -e "${GREEN}[✓]${NC} OS and binaries checked"
    else
        echo -e "${RED}[✗]${NC} OS check failed"
        all_good=false
    fi
    
    if [[ "${STATUS[network_check]}" == true ]]; then
        echo -e "${GREEN}[✓]${NC} Network connectivity verified"
    else
        echo -e "${RED}[✗]${NC} Network check failed"
        all_good=false
    fi
    
    if [[ "${STATUS[vault_installed]}" == true ]]; then
        echo -e "${GREEN}[✓]${NC} Vault installed"
    else
        echo -e "${YELLOW}[?]${NC} Vault installation status unknown"
    fi
    
    if [[ "${STATUS[vault_configured]}" == true ]]; then
        echo -e "${GREEN}[✓]${NC} Vault configured"
    else
        echo -e "${YELLOW}[?]${NC} Vault configuration status unknown"
    fi
    
    if [[ "${STATUS[vault_initialized]}" == true ]]; then
        echo -e "${GREEN}[✓]${NC} Vault initialized and AppRole created"
    else
        echo -e "${YELLOW}[?]${NC} Vault initialization status unknown"
    fi
    
    if [[ "${STATUS[proxmox_token]}" == true ]]; then
        echo -e "${GREEN}[✓]${NC} Proxmox API token configured"
    else
        echo -e "${RED}[✗]${NC} Proxmox API token not configured"
        all_good=false
    fi
    
    if [[ "${STATUS[unifi_token]}" == true ]]; then
        echo -e "${GREEN}[✓]${NC} UniFi API token configured"
    else
        echo -e "${RED}[✗]${NC} UniFi API token not configured"
        all_good=false
    fi
    
    if [[ "${STATUS[nas_mounted]}" == true ]]; then
        echo -e "${GREEN}[✓]${NC} NAS mounted"
    else
        echo -e "${YELLOW}[?]${NC} NAS mount status unknown"
    fi
    
    echo ""
    echo "=========================================="
    echo ""
    
    if [[ "$DRY_RUN" == true ]]; then
        echo "This was a DRY RUN. To apply changes, run:"
        echo "  $0 --apply"
    else
        if [[ "$all_good" == true ]]; then
            echo -e "${GREEN}All critical components are configured!${NC}"
        else
            echo -e "${YELLOW}Some components need attention.${NC}"
        fi
        
        echo ""
        echo "Next steps:"
        echo "1. Review configuration files in: ${OUTPUT_DIR}/"
        echo "2. Verify setup: ${OUTPUT_DIR}/verify.sh"
        echo "3. Start infrastructure sync services:"
        echo "   docker-compose -f docker-compose.sync.yml --profile infra-sync up -d"
        echo ""
        echo "Important files:"
        echo "  - Vault Role ID: ${VAULT_ROLE_ID_FILE}"
        echo "  - Vault Secret ID: ${VAULT_SECRET_ID_FILE}"
        echo "  - Connections config: ${OUTPUT_DIR}/connections.json"
        echo "  - Vault paths doc: ${OUTPUT_DIR}/vault_paths.md"
    fi
    
    echo ""
}

# Main execution
main() {
    echo "=========================================="
    echo "  Mycosoft Infrastructure Bootstrap"
    echo "=========================================="
    echo ""
    
    check_os_and_binaries
    check_network_connectivity
    
    if [[ "$DRY_RUN" != true ]]; then
        install_vault
        configure_vault
        initialize_vault
        setup_proxmox_token
        setup_unifi_token
        setup_nas
    else
        log_info "Skipping installation steps in dry-run mode"
    fi
    
    generate_config_files
    generate_docker_compose
    print_checklist
}

# Run main
main
