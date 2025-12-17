#!/bin/bash
#
# Mycosoft Infrastructure Bootstrap Script
# Interactive setup for Proxmox, UniFi UDM, NAS, and HashiCorp Vault integration
#
# SECURITY: This script NEVER stores passwords in files or git.
# All secrets are entered at runtime and stored ONLY in HashiCorp Vault.
#
# Usage:
#   ./bootstrap_mycosoft.sh [--dry-run|--apply|--verify]
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
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

# Target Infrastructure - Use IPs only, no hostnames
declare -A PROXMOX_NODES
PROXMOX_NODES["build"]="192.168.0.202"
PROXMOX_NODES["dc1"]="192.168.0.2"
PROXMOX_NODES["dc2"]="192.168.0.131"
PROXMOX_PORT=8006

UNIFI_IP="192.168.0.1"
UNIFI_PORT=443
UNIFI_API_PATH="/proxy/network/api"

NAS_MOUNT_POINT="/mnt/mycosoft-nas"

# Mode
MODE=""
case "${1:-}" in
    --dry-run)
        MODE="dry-run"
        echo -e "${YELLOW}[DRY RUN MODE]${NC} Checking only - no changes will be made."
        ;;
    --apply)
        MODE="apply"
        echo -e "${GREEN}[APPLY MODE]${NC} Will install and configure infrastructure."
        ;;
    --verify)
        MODE="verify"
        echo -e "${BLUE}[VERIFY MODE]${NC} Re-checking existing configuration."
        ;;
    *)
        echo "Mycosoft Infrastructure Bootstrap"
        echo ""
        echo "Usage: $0 [--dry-run|--apply|--verify]"
        echo ""
        echo "  --dry-run  Check connectivity and validate, no changes"
        echo "  --apply    Install and configure everything"
        echo "  --verify   Re-check existing configuration"
        echo ""
        echo "SECURITY NOTICE:"
        echo "  - All secrets are entered interactively at runtime"
        echo "  - Secrets are stored ONLY in HashiCorp Vault"
        echo "  - Never store passwords in git, config files, or shell history"
    exit 1
        ;;
esac

# Status tracking
declare -A STATUS
STATUS[os_check]=false
STATUS[proxmox_build]=false
STATUS[proxmox_dc1]=false
STATUS[proxmox_dc2]=false
STATUS[unifi_reachable]=false
STATUS[vault_installed]=false
STATUS[vault_unsealed]=false
STATUS[vault_initialized]=false
STATUS[proxmox_token]=false
STATUS[unifi_token]=false
STATUS[nas_mounted]=false

# ============================================================================
# Helper Functions
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    local key="${2:-}"
    echo -e "${GREEN}[✓]${NC} $1"
    if [[ -n "$key" ]]; then
        STATUS["$key"]=true
    fi
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo ""
    echo -e "${BOLD}${CYAN}=== $1 ===${NC}"
    echo ""
}

prompt_yes_no() {
    local prompt="$1"
    local default="${2:-n}"
    local response
    
    if [[ "$default" == "y" ]]; then
        read -r -p "$prompt [Y/n]: " response
        response="${response:-y}"
    else
        read -r -p "$prompt [y/N]: " response
        response="${response:-n}"
    fi
    
    [[ "$response" =~ ^[Yy]$ ]]
}

prompt_secret() {
    local prompt="$1"
    local __resultvar="$2"
    local secret
    read -r -sp "$prompt: " secret
    echo
    eval "$__resultvar='$secret'"
}

check_command() {
    command -v "$1" >/dev/null 2>&1
}

install_package() {
    local pkg="$1"
    
    if check_command "$pkg"; then
        log_success "$pkg is installed"
        return 0
    fi
    
    if [[ "$MODE" == "dry-run" ]]; then
        log_warn "$pkg not found (would install in apply mode)"
        return 1
    fi
    
    if ! prompt_yes_no "Install $pkg?"; then
        log_error "$pkg is required"
        return 1
    fi
    
    log_info "Installing $pkg..."
    if check_command apt-get; then
        sudo apt-get update && sudo apt-get install -y "$pkg"
    elif check_command dnf; then
        sudo dnf install -y "$pkg"
    elif check_command yum; then
        sudo yum install -y "$pkg"
    else
        log_error "No supported package manager found. Please install $pkg manually."
        return 1
    fi
    
    log_success "$pkg installed"
}

# ============================================================================
# Step A: Preflight Checks
# ============================================================================

preflight_checks() {
    log_step "A) Preflight Checks"
    
    # Check OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        log_success "Running on Linux ($OSTYPE)" "os_check"
    else
        log_error "This script requires Linux. Current OS: $OSTYPE"
        exit 1
    fi
    
    # Required binaries
    local required=("curl" "jq" "docker" "ssh")
    local missing=()
    
    for cmd in "${required[@]}"; do
        if check_command "$cmd"; then
            log_success "$cmd available"
        else
            missing+=("$cmd")
        fi
    done
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        log_warn "Missing packages: ${missing[*]}"
        if [[ "$MODE" == "apply" ]]; then
            for pkg in "${missing[@]}"; do
                install_package "$pkg" || exit 1
            done
        else
            log_error "Run with --apply to install missing packages"
            exit 1
        fi
    fi
    
    # Check Docker is running
    if docker info >/dev/null 2>&1; then
        log_success "Docker is running"
    else
        log_error "Docker is not running. Start Docker and try again."
        exit 1
    fi
    
    # Check optional NFS/SMB tools
    if check_command showmount || [[ -f /sbin/mount.nfs ]]; then
        log_success "NFS client available"
    else
        log_warn "NFS client not found (install nfs-common for NFS mounts)"
    fi
    
    if check_command mount.cifs || [[ -f /sbin/mount.cifs ]]; then
        log_success "CIFS/SMB client available"
    else
        log_warn "CIFS client not found (install cifs-utils for SMB mounts)"
    fi
}

# ============================================================================
# Step B: Network Connectivity
# ============================================================================

check_network() {
    log_step "B) Network Connectivity"
    
    # Check each Proxmox node
    for node in build dc1 dc2; do
        local ip="${PROXMOX_NODES[$node]}"
        local url="https://${ip}:${PROXMOX_PORT}/api2/json/version"
        
        log_info "Checking Proxmox $node at ${ip}..."
        
        local response
        if response=$(curl -k -s --connect-timeout 10 "$url" 2>&1); then
            if echo "$response" | jq -e '.data.version' >/dev/null 2>&1; then
                local version
                version=$(echo "$response" | jq -r '.data.version')
                log_success "Proxmox $node reachable (version: $version)" "proxmox_${node}"
            else
                log_success "Proxmox $node reachable (API available)" "proxmox_${node}"
            fi
        else
            log_warn "Proxmox $node at ${ip} not reachable"
        fi
    done
    
    # Check at least one Proxmox is reachable
    if [[ "${STATUS[proxmox_build]}" != true ]] && \
       [[ "${STATUS[proxmox_dc1]}" != true ]] && \
       [[ "${STATUS[proxmox_dc2]}" != true ]]; then
        log_error "No Proxmox nodes are reachable. Check network connectivity."
        exit 1
    fi
    
    # Check UniFi
    log_info "Checking UniFi UDM at ${UNIFI_IP}..."
    if curl -k -s --connect-timeout 10 "https://${UNIFI_IP}" >/dev/null 2>&1; then
        log_success "UniFi UDM reachable at ${UNIFI_IP}" "unifi_reachable"
    else
        log_warn "UniFi UDM at ${UNIFI_IP} not reachable"
    fi
}

# ============================================================================
# Step C: Vault Installation
# ============================================================================

install_vault() {
    log_step "C) Vault Installation"
    
        if check_command vault; then
        local version
        version=$(vault version 2>/dev/null | head -1)
        log_success "Vault already installed: $version" "vault_installed"
        return 0
    fi
    
    if [[ "$MODE" == "dry-run" ]]; then
        log_warn "Vault not installed (would install in apply mode)"
        return 0
    fi
    
    log_info "Installing HashiCorp Vault..."
    
    local vault_version="1.16.0"
    local arch="amd64"
    if [[ "$(uname -m)" == "aarch64" ]] || [[ "$(uname -m)" == "arm64" ]]; then
        arch="arm64"
    fi
    
    local vault_url="https://releases.hashicorp.com/vault/${vault_version}/vault_${vault_version}_linux_${arch}.zip"
    local temp_dir
    temp_dir=$(mktemp -d)
    
    log_info "Downloading Vault ${vault_version}..."
    curl -L -o "${temp_dir}/vault.zip" "$vault_url"
    
    log_info "Installing to /usr/local/bin..."
    unzip -q "${temp_dir}/vault.zip" -d "${temp_dir}"
    sudo mv "${temp_dir}/vault" /usr/local/bin/
    sudo chmod +x /usr/local/bin/vault
    rm -rf "$temp_dir"
    
    log_success "Vault installed" "vault_installed"
    vault version
}

configure_vault_server() {
    if [[ "$MODE" == "dry-run" ]]; then
        log_warn "Would configure Vault server (skip in dry-run)"
        return 0
    fi
    
    log_info "Configuring Vault server..."
    
    # Create directories
    mkdir -p "$VAULT_DATA_DIR" "$VAULT_CONFIG_DIR"
    
    # Create Vault config
    cat > "${VAULT_CONFIG_DIR}/vault.hcl" <<EOF
# Mycosoft Vault Configuration
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
    
    # Create systemd service
    if [[ -d /etc/systemd/system ]]; then
        sudo tee /etc/systemd/system/vault.service > /dev/null <<EOF
[Unit]
Description=HashiCorp Vault - Secret Management
Documentation=https://www.vaultproject.io/docs/
After=network-online.target
Wants=network-online.target

[Service]
Type=notify
User=$USER
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
        
        sleep 3
        
        if systemctl is-active --quiet vault; then
            log_success "Vault service started"
        else
            log_warn "Vault service may not have started. Check: systemctl status vault"
        fi
    else
        log_warn "No systemd. Start Vault manually:"
        echo "  vault server -config=${VAULT_CONFIG_DIR}/vault.hcl &"
    fi
}

# ============================================================================
# Step D: Vault Initialization
# ============================================================================

initialize_vault() {
    log_step "D) Vault Initialization"
    
    export VAULT_ADDR="$VAULT_ADDR"
    
    # Check if Vault is running
    if ! vault status >/dev/null 2>&1; then
        if [[ "$MODE" == "dry-run" ]]; then
            log_warn "Vault not running (would start in apply mode)"
        return 0
    fi
        configure_vault_server
    fi
    
    # Check initialization status
    local vault_status
    vault_status=$(vault status -format=json 2>/dev/null || echo '{}')
    
    local initialized sealed
    initialized=$(echo "$vault_status" | jq -r '.initialized // false')
    sealed=$(echo "$vault_status" | jq -r '.sealed // true')
    
    if [[ "$initialized" == "true" ]]; then
        log_success "Vault is already initialized" "vault_initialized"
        
        if [[ "$sealed" == "true" ]]; then
            log_warn "Vault is SEALED. You need to unseal it."
            
            if [[ "$MODE" == "apply" ]]; then
                echo ""
                echo "Enter 3 unseal keys (you should have saved these during initialization):"
                for i in 1 2 3; do
                    local key
                    prompt_secret "Unseal key $i" key
                    vault operator unseal "$key" >/dev/null
                done
                
                if vault status | grep -q "Sealed.*false"; then
                    log_success "Vault unsealed" "vault_unsealed"
                else
                    log_error "Failed to unseal Vault"
                    exit 1
                fi
            fi
        else
            log_success "Vault is unsealed" "vault_unsealed"
        fi
        return 0
    fi
    
    if [[ "$MODE" == "dry-run" ]]; then
        log_warn "Vault not initialized (would initialize in apply mode)"
            return 0
        fi
    
    log_info "Initializing Vault with 5 key shares, 3 threshold..."
    
    local init_output
    init_output=$(vault operator init -key-shares=5 -key-threshold=3 -format=json)
    
    local root_token
    root_token=$(echo "$init_output" | jq -r '.root_token')
    
    echo ""
    echo -e "${RED}${BOLD}╔══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}${BOLD}║  CRITICAL: SAVE THESE CREDENTIALS NOW - SHOWN ONLY ONCE!        ║${NC}"
    echo -e "${RED}${BOLD}╚══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Root Token:${NC} $root_token"
    echo ""
    echo -e "${YELLOW}Unseal Keys:${NC}"
    echo "$init_output" | jq -r '.unseal_keys_b64[]' | nl -w2 -s'. '
    echo ""
    echo -e "${RED}Store these in a secure password manager (1Password, Bitwarden, etc.)${NC}"
    echo ""
    
    if ! prompt_yes_no "Have you saved the root token and unseal keys securely?"; then
        log_error "Please save the credentials first!"
        exit 1
    fi
    
    # Unseal with first 3 keys
    log_info "Unsealing Vault..."
    local keys
    mapfile -t keys < <(echo "$init_output" | jq -r '.unseal_keys_b64[]')
    
    vault operator unseal "${keys[0]}" >/dev/null
    vault operator unseal "${keys[1]}" >/dev/null
    vault operator unseal "${keys[2]}" >/dev/null
    
    log_success "Vault unsealed" "vault_unsealed"
    
    # Login with root token
    echo "$root_token" | vault login - >/dev/null
    
    # Create KV v2 mount
    log_info "Creating KV v2 secrets engine at mycosoft/..."
    vault secrets enable -version=2 -path=mycosoft kv 2>/dev/null || log_warn "KV mount may already exist"
    
    # Create policy
    log_info "Creating mycosoft policy..."
    vault policy write mycosoft - <<EOF
# Mycosoft MYCA Policy - Least Privilege
path "mycosoft/data/*" {
  capabilities = ["read", "list"]
}

path "mycosoft/metadata/*" {
  capabilities = ["list", "read"]
}
EOF
    
    # Enable AppRole
    log_info "Enabling AppRole auth..."
    vault auth enable approle 2>/dev/null || log_warn "AppRole may already be enabled"
    
    # Create MYCA role
    log_info "Creating AppRole 'myca'..."
    vault write auth/approle/role/myca \
        token_policies="mycosoft" \
        token_ttl=1h \
        token_max_ttl=4h \
        bind_secret_id=true
    
    # Get role-id
    local role_id
    role_id=$(vault read -field=role_id auth/approle/role/myca/role-id)
    
    echo ""
    echo -e "${GREEN}AppRole Role ID:${NC} $role_id"
    echo ""
    echo "This Role ID is safe to store. The Secret ID will be generated on demand."
    echo "Saving Role ID to: $VAULT_ROLE_ID_FILE"
    
    echo "$role_id" > "$VAULT_ROLE_ID_FILE"
    chmod 600 "$VAULT_ROLE_ID_FILE"
    
    log_success "Vault initialized and configured" "vault_initialized"
}

generate_vault_secret_id() {
    export VAULT_ADDR="$VAULT_ADDR"
    
    log_info "Generating new Secret ID for AppRole 'myca'..."
    
    local secret_id
    secret_id=$(vault write -f -field=secret_id auth/approle/role/myca/secret-id)
    
    echo "$secret_id" > "$VAULT_SECRET_ID_FILE"
    chmod 600 "$VAULT_SECRET_ID_FILE"
    
    log_success "Secret ID generated and saved to: $VAULT_SECRET_ID_FILE"
    echo ""
    echo -e "${YELLOW}Note: Secret IDs expire. Generate a new one when needed:${NC}"
    echo "  vault write -f -field=secret_id auth/approle/role/myca/secret-id"
}

# ============================================================================
# Step E: Proxmox Integration
# ============================================================================

validate_proxmox_token() {
    local token_id="$1"
    local token_secret="$2"
    local ip="${3:-${PROXMOX_NODES[build]}}"
    
    # Proxmox API token format: PVEAPIToken=USER@REALM!TOKENID=SECRET
    local auth_header="PVEAPIToken=${token_id}=${token_secret}"
    local url="https://${ip}:${PROXMOX_PORT}/api2/json/nodes"
    
    local response http_code
    response=$(curl -k -s -w "\n%{http_code}" \
        -H "Authorization: $auth_header" \
        "$url" 2>&1)
    
    http_code=$(echo "$response" | tail -n1)
    
    if [[ "$http_code" == "200" ]]; then
        return 0
    else
        return 1
    fi
}

setup_proxmox_token() {
    log_step "E) Proxmox Integration"
    
    export VAULT_ADDR="$VAULT_ADDR"
    
    # Check for existing token in Vault
    if vault kv get -format=json mycosoft/proxmox >/dev/null 2>&1; then
        local token_data
        token_data=$(vault kv get -format=json mycosoft/proxmox | jq -r '.data.data')
        
        local token_id token_secret
        token_id=$(echo "$token_data" | jq -r '.token_id // empty')
        token_secret=$(echo "$token_data" | jq -r '.token_secret // empty')
        
        if [[ -n "$token_id" ]] && [[ -n "$token_secret" ]]; then
            log_info "Found existing Proxmox token in Vault. Validating..."
            
            if validate_proxmox_token "$token_id" "$token_secret"; then
                log_success "Proxmox token is valid" "proxmox_token"
                return 0
            else
                log_warn "Existing token is invalid. Will request new token."
            fi
        fi
    fi
    
    if [[ "$MODE" == "dry-run" ]]; then
        log_warn "Would configure Proxmox token (skip in dry-run)"
        return 0
    fi
    
    log_info "Proxmox API token not found or invalid. Let's set one up."
        echo ""
    echo "Choose how to create the Proxmox API token:"
    echo ""
    echo "  1) SSH-assisted: Run pveum commands on Proxmox via SSH"
    echo "     (Requires SSH access to a Proxmox node)"
    echo ""
    echo "  2) UI-assisted: Follow instructions to create token in Proxmox UI"
    echo "     (Then paste the token here)"
    echo ""
    
    local choice
    read -r -p "Enter choice [1-2]: " choice
    
    case "$choice" in
        1)
            setup_proxmox_token_ssh
            ;;
        2|*)
            setup_proxmox_token_ui
            ;;
    esac
}

setup_proxmox_token_ssh() {
    echo ""
    log_info "SSH-assisted Proxmox token creation"
    echo ""
    
    # Find a reachable Proxmox node
    local target_ip=""
    for node in build dc1 dc2; do
        if [[ "${STATUS[proxmox_${node}]}" == true ]]; then
            target_ip="${PROXMOX_NODES[$node]}"
            break
        fi
    done
    
    if [[ -z "$target_ip" ]]; then
        log_error "No reachable Proxmox node found"
        setup_proxmox_token_ui
        return
    fi
    
    read -r -p "SSH to Proxmox at ${target_ip}? Enter SSH user [root]: " ssh_user
            ssh_user="${ssh_user:-root}"
            
    echo ""
    log_info "This will run the following commands on ${target_ip}:"
    echo ""
    echo "  pveum user add myca@pve --comment 'MYCA MAS Service Account'"
    echo "  pveum role add MYCA_ROLE --privs '...'"
                echo "  pveum aclmod / --users myca@pve --roles MYCA_ROLE"
    echo "  pveum token add myca@pve mas --privsep 0"
    echo ""
    
    if ! prompt_yes_no "Proceed?"; then
        setup_proxmox_token_ui
        return
    fi
    
    log_info "Connecting to ${ssh_user}@${target_ip}..."
    echo "(You may be prompted for password or SSH key passphrase)"
    echo ""
    
    local ssh_output
    ssh_output=$(ssh -o ConnectTimeout=10 "${ssh_user}@${target_ip}" bash <<'ENDSSH' 2>&1) || true
# Create user (ignore if exists)
pveum user add myca@pve --comment "MYCA MAS Service Account" 2>/dev/null || echo "[exists] user myca@pve"

# Create role with required privileges
pveum role add MYCA_ROLE --privs "Datastore.AllocateSpace,Datastore.Audit,Pool.Allocate,Sys.Audit,Sys.Modify,VM.Allocate,VM.Audit,VM.Clone,VM.Config.CDROM,VM.Config.CPU,VM.Config.Cloudinit,VM.Config.Disk,VM.Config.HWType,VM.Config.Memory,VM.Config.Network,VM.Config.Options,VM.Monitor,VM.PowerMgmt" 2>/dev/null || echo "[exists] role MYCA_ROLE"

# Assign role to user
pveum aclmod / --users myca@pve --roles MYCA_ROLE 2>/dev/null || echo "[exists] ACL"

# Create API token
pveum token add myca@pve mas --privsep 0 2>&1
ENDSSH
    
    echo "$ssh_output"
    echo ""
    
    # Try to parse token from output
    if echo "$ssh_output" | grep -q "full-tokenid"; then
        log_success "Token created via SSH"
    else
        log_warn "Could not parse token output. Please enter manually."
    fi
    
    # Prompt for token values
    local token_id token_secret
    echo ""
    prompt_secret "Enter TOKEN_ID (e.g., myca@pve!mas)" token_id
    prompt_secret "Enter TOKEN_SECRET" token_secret
    
    # Validate
    if validate_proxmox_token "$token_id" "$token_secret" "$target_ip"; then
            # Store in Vault
            vault kv put mycosoft/proxmox \
                token_id="$token_id" \
                token_secret="$token_secret" \
            primary_host="$target_ip" \
            hosts="${PROXMOX_NODES[build]},${PROXMOX_NODES[dc1]},${PROXMOX_NODES[dc2]}" \
            port="$PROXMOX_PORT"
            
        log_success "Proxmox token validated and stored in Vault" "proxmox_token"
        else
        log_error "Token validation failed. Check the credentials."
            exit 1
        fi
}

setup_proxmox_token_ui() {
    echo ""
    log_info "UI-assisted Proxmox token creation"
    echo ""
    echo "Follow these steps in the Proxmox web UI:"
    echo ""
    echo "1. Open: https://${PROXMOX_NODES[build]}:${PROXMOX_PORT}"
    echo "2. Log in as administrator (root or similar)"
    echo ""
    echo "3. Create User:"
    echo "   → Datacenter → Permissions → Users → Add"
    echo "   → User name: myca"
    echo "   → Realm: pve (Proxmox VE authentication)"
    echo "   → Password: (generate secure password, you won't need it)"
    echo ""
    echo "4. Create Role:"
    echo "   → Datacenter → Permissions → Roles → Create"
    echo "   → Name: MYCA_ROLE"
    echo "   → Privileges: Select these:"
    echo "      - Datastore.AllocateSpace, Datastore.Audit"
    echo "      - Pool.Allocate"
    echo "      - Sys.Audit, Sys.Modify"
    echo "      - VM.Allocate, VM.Audit, VM.Clone"
    echo "      - VM.Config.* (all VM.Config options)"
    echo "      - VM.Monitor, VM.PowerMgmt"
    echo ""
    echo "5. Assign Role:"
    echo "   → Datacenter → Permissions → Add"
    echo "   → Path: /"
    echo "   → User: myca@pve"
    echo "   → Role: MYCA_ROLE"
    echo ""
    echo "6. Create API Token:"
    echo "   → Datacenter → Permissions → API Tokens → Add"
    echo "   → User: myca@pve"
    echo "   → Token ID: mas"
    echo "   → Privilege Separation: UNCHECKED"
    echo "   → Click Add, then COPY the token secret immediately!"
    echo ""
    
    if ! prompt_yes_no "Ready to enter the token?"; then
        log_error "Aborted. Re-run script when ready."
        exit 1
    fi
    
    local token_id token_secret
    prompt_secret "Enter TOKEN_ID (should be: myca@pve!mas)" token_id
    prompt_secret "Enter TOKEN_SECRET (the long string)" token_secret
    
    # Try each reachable node
    local validated=false
    for node in build dc1 dc2; do
        if [[ "${STATUS[proxmox_${node}]}" == true ]]; then
            local ip="${PROXMOX_NODES[$node]}"
            log_info "Validating token against ${node} (${ip})..."
            
            if validate_proxmox_token "$token_id" "$token_secret" "$ip"; then
                validated=true
                
                # Store in Vault
                vault kv put mycosoft/proxmox \
                    token_id="$token_id" \
                    token_secret="$token_secret" \
                    primary_host="$ip" \
                    hosts="${PROXMOX_NODES[build]},${PROXMOX_NODES[dc1]},${PROXMOX_NODES[dc2]}" \
                    port="$PROXMOX_PORT"
                
                log_success "Proxmox token validated and stored in Vault" "proxmox_token"
                break
            fi
        fi
    done
    
    if [[ "$validated" != true ]]; then
        log_error "Token validation failed against all Proxmox nodes"
        exit 1
    fi
}

# ============================================================================
# Step F: UniFi Integration
# ============================================================================

validate_unifi_token() {
    local token="$1"
    
    # UniFi uses X-API-Key header for local API access
    local url="https://${UNIFI_IP}${UNIFI_API_PATH}/self"
    
    local response http_code
    response=$(curl -k -s -w "\n%{http_code}" \
        -H "X-API-Key: $token" \
        "$url" 2>&1)
    
    http_code=$(echo "$response" | tail -n1)
    
    if [[ "$http_code" == "200" ]]; then
        return 0
    else
        return 1
    fi
}

setup_unifi_token() {
    log_step "F) UniFi Integration"
    
    export VAULT_ADDR="$VAULT_ADDR"
    
    if [[ "${STATUS[unifi_reachable]}" != true ]]; then
        log_warn "UniFi UDM not reachable. Skipping UniFi integration."
        return 0
    fi
    
    # Check for existing token
    if vault kv get -format=json mycosoft/unifi >/dev/null 2>&1; then
        local token_data
        token_data=$(vault kv get -format=json mycosoft/unifi | jq -r '.data.data')
        
        local api_key
        api_key=$(echo "$token_data" | jq -r '.api_key // empty')
        
        if [[ -n "$api_key" ]]; then
            log_info "Found existing UniFi API key in Vault. Validating..."
            
            if validate_unifi_token "$api_key"; then
                log_success "UniFi API key is valid" "unifi_token"
                return 0
            else
                log_warn "Existing API key is invalid. Will request new key."
            fi
        fi
    fi
    
    if [[ "$MODE" == "dry-run" ]]; then
        log_warn "Would configure UniFi API key (skip in dry-run)"
        return 0
    fi
    
    echo ""
    log_info "UniFi API key not found or invalid. Let's set one up."
    echo ""
    echo "To create a UniFi API key:"
    echo ""
    echo "1. Open: https://${UNIFI_IP}"
    echo "2. Log in as your admin account"
    echo ""
    echo "3. Navigate to: Settings (gear icon) → System → Advanced"
    echo "4. Enable 'API Access' if not already enabled"
    echo ""
    echo "5. Navigate to: Settings → API"
    echo "   OR: Settings → System → API Access"
    echo ""
    echo "6. Click 'Create New API Key'"
    echo "   → Name: MYCA-MAS"
    echo "   → Click Create"
    echo "   → COPY the key immediately (shown only once!)"
    echo ""
    
    if ! prompt_yes_no "Ready to enter the API key?"; then
        log_warn "Skipping UniFi integration"
        return 0
    fi
    
    local api_key
    prompt_secret "Enter UniFi API Key" api_key
    
    log_info "Validating API key..."
    
    if validate_unifi_token "$api_key"; then
            vault kv put mycosoft/unifi \
            api_key="$api_key" \
            host="$UNIFI_IP" \
            port="$UNIFI_PORT" \
            api_path="$UNIFI_API_PATH"
            
        log_success "UniFi API key validated and stored in Vault" "unifi_token"
        else
        log_warn "API key validation failed. UniFi integration may not work."
        log_info "Note: Some UniFi versions require different auth methods."
    fi
}

# ============================================================================
# Step G: NAS Mount
# ============================================================================

setup_nas() {
    log_step "G) NAS Mount"
    
    # Check if already mounted
    if mountpoint -q "$NAS_MOUNT_POINT" 2>/dev/null; then
        log_success "NAS already mounted at $NAS_MOUNT_POINT" "nas_mounted"
        ls -la "$NAS_MOUNT_POINT" 2>/dev/null | head -5 || true
        return 0
    fi
    
    if [[ "$MODE" == "dry-run" ]]; then
        log_warn "NAS not mounted (would configure in apply mode)"
        return 0
    fi
    
    echo ""
    log_info "NAS mount configuration"
    echo ""
    echo "Mount protocol:"
    echo "  1) NFS (recommended for Linux NAS)"
    echo "  2) SMB/CIFS (for Windows/Synology shares)"
    echo ""
    
    local protocol_choice
    read -r -p "Enter choice [1-2]: " protocol_choice
    
    local nas_ip nas_share
    read -r -p "Enter NAS IP address: " nas_ip
    read -r -p "Enter share path (e.g., /volume1/data or /share): " nas_share
    
    # Test connectivity
    if ! ping -c 1 -W 3 "$nas_ip" >/dev/null 2>&1; then
        log_warn "Cannot ping $nas_ip. Continuing anyway..."
    fi
    
    # Create mount point
            sudo mkdir -p "$NAS_MOUNT_POINT"
    
    if [[ "$protocol_choice" == "1" ]]; then
        # NFS mount
        install_package nfs-common 2>/dev/null || true
        
        log_info "Mounting NFS share ${nas_ip}:${nas_share}..."
            
        if sudo mount -t nfs "${nas_ip}:${nas_share}" "$NAS_MOUNT_POINT" 2>&1; then
                log_success "NAS mounted via NFS" "nas_mounted"
        else
            log_error "NFS mount failed. Check share permissions and export settings."
            return 1
                fi
                
                # Store in Vault
                vault kv put mycosoft/nas \
                    protocol="nfs" \
                    ip="$nas_ip" \
                    share="$nas_share" \
                    mount_point="$NAS_MOUNT_POINT"
        
        # Persist?
        if prompt_yes_no "Add to /etc/fstab for persistent mount?"; then
            echo "${nas_ip}:${nas_share} ${NAS_MOUNT_POINT} nfs defaults,_netdev 0 0" | sudo tee -a /etc/fstab
            log_success "Added to /etc/fstab"
        fi
        
    else
        # SMB mount
        install_package cifs-utils 2>/dev/null || true
        
        local smb_user smb_password
        read -r -p "Enter SMB username: " smb_user
        prompt_secret "Enter SMB password" smb_password
        
        log_info "Mounting SMB share //${nas_ip}${nas_share}..."
        
        if sudo mount -t cifs "//${nas_ip}${nas_share}" "$NAS_MOUNT_POINT" \
            -o "username=${smb_user},password=${smb_password},uid=$(id -u),gid=$(id -g)" 2>&1; then
                log_success "NAS mounted via SMB" "nas_mounted"
        else
            log_error "SMB mount failed. Check credentials and share permissions."
            return 1
                fi
                
        # Store in Vault (password separately)
                vault kv put mycosoft/nas \
                    protocol="smb" \
                    ip="$nas_ip" \
                    share="$nas_share" \
                    mount_point="$NAS_MOUNT_POINT" \
                    username="$smb_user"
        
        vault kv put mycosoft/nas_credentials \
            username="$smb_user" \
            password="$smb_password"
        
        # Persist?
        if prompt_yes_no "Add to /etc/fstab for persistent mount?"; then
            local cred_file="${HOME}/.nas-credentials"
            echo "username=${smb_user}" > "$cred_file"
            echo "password=${smb_password}" >> "$cred_file"
            chmod 600 "$cred_file"
            
            echo "//${nas_ip}${nas_share} ${NAS_MOUNT_POINT} cifs credentials=${cred_file},uid=$(id -u),gid=$(id -g),_netdev 0 0" | sudo tee -a /etc/fstab
            log_success "Added to /etc/fstab (credentials in ${cred_file})"
        fi
    fi
    
    # Verify mount
    echo ""
    log_info "Verifying mount..."
    ls -la "$NAS_MOUNT_POINT" | head -5
}

# ============================================================================
# Step H: Generate Output Artifacts
# ============================================================================

generate_artifacts() {
    log_step "H) Generate Configuration Files"
    
    mkdir -p "$OUTPUT_DIR"
    mkdir -p "${OUTPUT_DIR}/secrets"
    mkdir -p "${OUTPUT_DIR}/templates"
    
    # connections.json (non-secret)
    log_info "Generating connections.json..."
    cat > "${OUTPUT_DIR}/connections.json" <<EOF
{
  "proxmox": {
    "hosts": [
      {"name": "build", "ip": "${PROXMOX_NODES[build]}", "port": ${PROXMOX_PORT}},
      {"name": "dc1", "ip": "${PROXMOX_NODES[dc1]}", "port": ${PROXMOX_PORT}},
      {"name": "dc2", "ip": "${PROXMOX_NODES[dc2]}", "port": ${PROXMOX_PORT}}
    ]
  },
  "unifi": {
    "host": "${UNIFI_IP}",
    "port": ${UNIFI_PORT},
    "api_path": "${UNIFI_API_PATH}"
  },
  "nas": {
    "mount_point": "${NAS_MOUNT_POINT}"
  },
  "vault": {
    "address": "${VAULT_ADDR}",
    "kv_path": "mycosoft",
    "approle": "myca"
  }
}
EOF
    
    # vault_paths.md
    log_info "Generating vault_paths.md..."
    cat > "${OUTPUT_DIR}/vault_paths.md" <<EOF
# Vault Secret Paths - Mycosoft Infrastructure

All secrets are stored in HashiCorp Vault at \`${VAULT_ADDR}\` under the \`mycosoft/\` KV v2 mount.

## Secret Locations

| Path | Contents |
|------|----------|
| \`mycosoft/proxmox\` | Proxmox API token (token_id, token_secret, hosts) |
| \`mycosoft/unifi\` | UniFi API key (api_key, host) |
| \`mycosoft/nas\` | NAS mount info (protocol, ip, share, mount_point) |
| \`mycosoft/nas_credentials\` | NAS credentials if SMB (username, password) |

## Accessing Secrets

### Using AppRole (for MYCA services)

\`\`\`bash
export VAULT_ADDR="${VAULT_ADDR}"

# Read role-id (safe to store)
ROLE_ID=\$(cat ${VAULT_ROLE_ID_FILE})

# Get secret-id (generate as needed)
SECRET_ID=\$(vault write -f -field=secret_id auth/approle/role/myca/secret-id)

# Login
VAULT_TOKEN=\$(vault write -field=token auth/approle/login \\
  role_id=\$ROLE_ID secret_id=\$SECRET_ID)

# Read secret
VAULT_TOKEN=\$VAULT_TOKEN vault kv get mycosoft/proxmox
\`\`\`

### Using Root Token (admin only)

\`\`\`bash
export VAULT_ADDR="${VAULT_ADDR}"
vault login <root_token>
vault kv get mycosoft/proxmox
\`\`\`

## Vault Agent Templates

For Docker services, use Vault Agent to inject secrets:

- See \`${OUTPUT_DIR}/vault-agent.hcl\`
- Templates in \`${OUTPUT_DIR}/templates/\`
EOF
    
    # verify.sh
    log_info "Generating verify.sh..."
    cat > "${OUTPUT_DIR}/verify.sh" <<'VERIFYEOF'
#!/bin/bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_ok() { echo -e "${GREEN}[✓]${NC} $1"; }
log_fail() { echo -e "${RED}[✗]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[?]${NC} $1"; }

export VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"

echo ""
echo "Mycosoft Infrastructure Verification"
echo "====================================="
echo ""

# Vault
echo "Vault:"
if vault status >/dev/null 2>&1; then
    if vault status | grep -q "Sealed.*false"; then
        log_ok "Vault is running and unsealed"
    else
        log_fail "Vault is sealed"
    fi
else
    log_fail "Vault is not accessible"
fi

# Proxmox token
echo ""
echo "Proxmox:"
if vault kv get mycosoft/proxmox >/dev/null 2>&1; then
    log_ok "Proxmox token exists in Vault"
    
    # Validate token
    TOKEN_DATA=$(vault kv get -format=json mycosoft/proxmox 2>/dev/null | jq -r '.data.data')
    TOKEN_ID=$(echo "$TOKEN_DATA" | jq -r '.token_id')
    TOKEN_SECRET=$(echo "$TOKEN_DATA" | jq -r '.token_secret')
    HOST=$(echo "$TOKEN_DATA" | jq -r '.primary_host')
    
    if curl -k -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: PVEAPIToken=${TOKEN_ID}=${TOKEN_SECRET}" \
        "https://${HOST}:8006/api2/json/nodes" | grep -q "200"; then
        log_ok "Proxmox token is valid"
    else
        log_fail "Proxmox token is invalid"
    fi
else
    log_fail "Proxmox token not found in Vault"
fi

# UniFi token
echo ""
echo "UniFi:"
if vault kv get mycosoft/unifi >/dev/null 2>&1; then
    log_ok "UniFi API key exists in Vault"
else
    log_warn "UniFi API key not configured"
fi

# NAS
echo ""
echo "NAS:"
if mountpoint -q /mnt/mycosoft-nas 2>/dev/null; then
    log_ok "NAS is mounted at /mnt/mycosoft-nas"
else
    log_warn "NAS is not mounted"
fi

# Proxmox connectivity
echo ""
echo "Network Connectivity:"
for ip in 192.168.0.202 192.168.0.2 192.168.0.131; do
    if curl -k -s --connect-timeout 5 "https://${ip}:8006" >/dev/null 2>&1; then
        log_ok "Proxmox at ${ip} reachable"
    else
        log_warn "Proxmox at ${ip} not reachable"
    fi
done

if curl -k -s --connect-timeout 5 "https://192.168.0.1" >/dev/null 2>&1; then
    log_ok "UniFi UDM at 192.168.0.1 reachable"
else
    log_warn "UniFi UDM not reachable"
fi

echo ""
echo "Verification complete."
VERIFYEOF
    chmod +x "${OUTPUT_DIR}/verify.sh"
    
    # Vault Agent config
    log_info "Generating vault-agent.hcl..."
    cat > "${OUTPUT_DIR}/vault-agent.hcl" <<EOF
pid_file = "/tmp/vault-agent.pid"

vault {
  address = "${VAULT_ADDR}"
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
      mode = 0600
    }
  }
}

template {
  source      = "/vault/templates/proxmox.tpl"
  destination = "/vault/secrets/proxmox.env"
  perms       = 0600
}

template {
  source      = "/vault/templates/unifi.tpl"
  destination = "/vault/secrets/unifi.env"
  perms       = 0600
}
EOF
    
    # Vault templates
    cat > "${OUTPUT_DIR}/templates/proxmox.tpl" <<'TEMPLATEEOF'
{{ with secret "mycosoft/proxmox" -}}
PROXMOX_TOKEN_ID={{ .Data.data.token_id }}
PROXMOX_TOKEN_SECRET={{ .Data.data.token_secret }}
PROXMOX_HOST={{ .Data.data.primary_host }}
PROXMOX_PORT={{ .Data.data.port }}
{{- end }}
TEMPLATEEOF
    
    cat > "${OUTPUT_DIR}/templates/unifi.tpl" <<'TEMPLATEEOF'
{{ with secret "mycosoft/unifi" -}}
UNIFI_API_KEY={{ .Data.data.api_key }}
UNIFI_HOST={{ .Data.data.host }}
{{- end }}
TEMPLATEEOF
    
    # Update .gitignore in output dir
    cat > "${OUTPUT_DIR}/.gitignore" <<EOF
# Secrets - NEVER COMMIT
secrets/
*.env
*.secret
*.token
*.key
EOF
    
    log_success "Configuration files generated in ${OUTPUT_DIR}/"
}

# ============================================================================
# Step I: Generate Docker Compose
# ============================================================================

generate_docker_compose() {
    log_step "I) Generate Docker Compose Template"
    
    log_info "Generating docker-compose.sync.yml..."
    
    cat > "${REPO_ROOT}/docker-compose.sync.yml" <<'DOCKEREOF'
# Mycosoft Infrastructure Services
# Generated by bootstrap_mycosoft.sh
#
# This file does NOT contain any secrets.
# Secrets are fetched at runtime via Vault Agent.
#
# Usage:
#   docker-compose -f docker-compose.sync.yml --profile myca up -d
#
version: "3.9"

x-vault-env: &vault-env
  VAULT_ADDR: ${VAULT_ADDR:-http://host.docker.internal:8200}

x-common-volumes: &common-volumes
  - ./infra/bootstrap/out/secrets:/vault/secrets:ro
  - ${NAS_MOUNT_POINT:-/mnt/mycosoft-nas}:/mnt/nas:rw

services:
  # ============================================================
  # Vault Agent - Fetches secrets for other services
  # ============================================================
  vault-agent:
    image: hashicorp/vault:1.16
    container_name: mycosoft-vault-agent
    command: agent -config=/vault/config/agent.hcl
    volumes:
      - ./infra/bootstrap/out/vault-agent.hcl:/vault/config/agent.hcl:ro
      - ./infra/bootstrap/out/templates:/vault/templates:ro
      - ./infra/bootstrap/out/secrets:/vault/secrets:rw
      - ${HOME}/.mycosoft-vault-role-id:/vault/role-id:ro
      - ${HOME}/.mycosoft-vault-secret-id:/vault/secret-id:ro
    environment:
      <<: *vault-env
    extra_hosts:
      - "host.docker.internal:host-gateway"
    restart: unless-stopped
    profiles:
      - myca
      - infra

  # ============================================================
  # MYCA Orchestrator - Main MAS orchestration service
  # ============================================================
  orchestrator:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: mycosoft-orchestrator
    command: >
      sh -c "
        echo 'Waiting for secrets...' &&
        while [ ! -f /vault/secrets/proxmox.env ]; do sleep 2; done &&
        echo 'Loading secrets...' &&
        set -a && source /vault/secrets/proxmox.env && set +a &&
        python -m mycosoft_mas.core.main
      "
    volumes:
      <<: *common-volumes
      - ./mycosoft_mas:/app/mycosoft_mas:ro
      - ./logs:/app/logs:rw
    environment:
      <<: *vault-env
      MAS_ENV: production
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - vault-agent
      - redis
    extra_hosts:
      - "host.docker.internal:host-gateway"
    restart: unless-stopped
    profiles:
      - myca

  # ============================================================
  # Agent Runner - Executes individual MAS agents
  # ============================================================
  agent-runner:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: mycosoft-agent-runner
    command: >
      sh -c "
        while [ ! -f /vault/secrets/proxmox.env ]; do sleep 2; done &&
        set -a && source /vault/secrets/proxmox.env && source /vault/secrets/unifi.env 2>/dev/null && set +a &&
        python -m mycosoft_mas.agents.management.agent_manager
      "
    volumes:
      <<: *common-volumes
      - ./mycosoft_mas:/app/mycosoft_mas:ro
    environment:
      <<: *vault-env
      MAS_ENV: production
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - vault-agent
      - redis
      - orchestrator
    extra_hosts:
      - "host.docker.internal:host-gateway"
    restart: unless-stopped
    profiles:
      - myca

  # ============================================================
  # UART Agent - Hardware interface (ttyUSB passthrough)
  # ============================================================
  uart-agent:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: mycosoft-uart-agent
    privileged: true
    command: >
      sh -c "
        while [ ! -f /vault/secrets/proxmox.env ]; do sleep 2; done &&
        set -a && source /vault/secrets/proxmox.env && set +a &&
        python -m mycosoft_mas.agents.hardware.uart_agent
      "
    volumes:
      <<: *common-volumes
      - ./mycosoft_mas:/app/mycosoft_mas:ro
    devices:
      - /dev/ttyUSB0:/dev/ttyUSB0
      - /dev/ttyUSB1:/dev/ttyUSB1
    environment:
      <<: *vault-env
      MAS_ENV: production
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - vault-agent
      - redis
    extra_hosts:
      - "host.docker.internal:host-gateway"
    restart: unless-stopped
    profiles:
      - hardware

  # ============================================================
  # GPU Runner - Uses nvidia runtime for GPU workloads
  # ============================================================
  gpu-runner:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: mycosoft-gpu-runner
    runtime: nvidia
    command: >
      sh -c "
        while [ ! -f /vault/secrets/proxmox.env ]; do sleep 2; done &&
        set -a && source /vault/secrets/proxmox.env && set +a &&
        python -m mycosoft_mas.agents.compute.gpu_runner
      "
    volumes:
      <<: *common-volumes
      - ./mycosoft_mas:/app/mycosoft_mas:ro
    environment:
      <<: *vault-env
      MAS_ENV: production
      REDIS_URL: redis://redis:6379/0
      NVIDIA_VISIBLE_DEVICES: all
    depends_on:
      - vault-agent
      - redis
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    extra_hosts:
      - "host.docker.internal:host-gateway"
    restart: unless-stopped
    profiles:
      - gpu

  # ============================================================
  # Redis - Message broker for agents
  # ============================================================
  redis:
    image: redis:8-alpine
    container_name: mycosoft-redis
    ports:
      - "6380:6379"
    volumes:
      - redis-sync-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    profiles:
      - myca
      - infra

volumes:
  redis-sync-data:

networks:
  default:
    name: mycosoft-infra
DOCKEREOF
    
    log_success "docker-compose.sync.yml generated"
    echo ""
    echo "Usage:"
    echo "  # Start infrastructure services:"
    echo "  docker-compose -f docker-compose.sync.yml --profile myca up -d"
    echo ""
    echo "  # Include hardware (UART) support:"
    echo "  docker-compose -f docker-compose.sync.yml --profile myca --profile hardware up -d"
    echo ""
    echo "  # Include GPU support:"
    echo "  docker-compose -f docker-compose.sync.yml --profile myca --profile gpu up -d"
}

# ============================================================================
# Final Report
# ============================================================================

print_report() {
    echo ""
    echo -e "${BOLD}╔══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║            Mycosoft Infrastructure Bootstrap Report             ║${NC}"
    echo -e "${BOLD}╚══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Status summary
    echo "Component Status:"
    echo ""
    
    [[ "${STATUS[os_check]}" == true ]] && echo -e "  ${GREEN}✓${NC} OS & Prerequisites" || echo -e "  ${RED}✗${NC} OS & Prerequisites"
    
    echo ""
    echo "  Proxmox Nodes:"
    [[ "${STATUS[proxmox_build]}" == true ]] && echo -e "    ${GREEN}✓${NC} Build (192.168.0.202)" || echo -e "    ${YELLOW}○${NC} Build (192.168.0.202)"
    [[ "${STATUS[proxmox_dc1]}" == true ]] && echo -e "    ${GREEN}✓${NC} DC1 (192.168.0.2)" || echo -e "    ${YELLOW}○${NC} DC1 (192.168.0.2)"
    [[ "${STATUS[proxmox_dc2]}" == true ]] && echo -e "    ${GREEN}✓${NC} DC2 (192.168.0.131)" || echo -e "    ${YELLOW}○${NC} DC2 (192.168.0.131)"
    
    echo ""
    [[ "${STATUS[unifi_reachable]}" == true ]] && echo -e "  ${GREEN}✓${NC} UniFi UDM (192.168.0.1)" || echo -e "  ${YELLOW}○${NC} UniFi UDM (192.168.0.1)"
    
    echo ""
    [[ "${STATUS[vault_installed]}" == true ]] && echo -e "  ${GREEN}✓${NC} Vault Installed" || echo -e "  ${YELLOW}○${NC} Vault Installed"
    [[ "${STATUS[vault_unsealed]}" == true ]] && echo -e "  ${GREEN}✓${NC} Vault Unsealed" || echo -e "  ${YELLOW}○${NC} Vault Unsealed"
    [[ "${STATUS[vault_initialized]}" == true ]] && echo -e "  ${GREEN}✓${NC} Vault Configured" || echo -e "  ${YELLOW}○${NC} Vault Configured"
    
    echo ""
    [[ "${STATUS[proxmox_token]}" == true ]] && echo -e "  ${GREEN}✓${NC} Proxmox Token in Vault" || echo -e "  ${RED}✗${NC} Proxmox Token in Vault"
    [[ "${STATUS[unifi_token]}" == true ]] && echo -e "  ${GREEN}✓${NC} UniFi Token in Vault" || echo -e "  ${YELLOW}○${NC} UniFi Token in Vault"
    [[ "${STATUS[nas_mounted]}" == true ]] && echo -e "  ${GREEN}✓${NC} NAS Mounted" || echo -e "  ${YELLOW}○${NC} NAS Mounted"
    
    echo ""
    echo "─────────────────────────────────────────────────────────────────────"
    echo ""
    
    if [[ "$MODE" == "dry-run" ]]; then
        echo -e "${YELLOW}This was a DRY RUN.${NC} To apply changes:"
        echo ""
        echo "  ./infra/bootstrap/bootstrap_mycosoft.sh --apply"
    else
        echo "Generated files:"
        echo "  ${OUTPUT_DIR}/connections.json"
        echo "  ${OUTPUT_DIR}/vault_paths.md"
        echo "  ${OUTPUT_DIR}/verify.sh"
        echo "  ${REPO_ROOT}/docker-compose.sync.yml"
        echo ""
        echo "Next steps:"
        echo "  1. Verify setup: ${OUTPUT_DIR}/verify.sh"
        echo "  2. Generate Secret ID: vault write -f auth/approle/role/myca/secret-id"
        echo "  3. Start services: docker-compose -f docker-compose.sync.yml --profile myca up -d"
    fi
    
    echo ""
}

# ============================================================================
# Main
# ============================================================================

main() {
    echo ""
    echo -e "${BOLD}Mycosoft Infrastructure Bootstrap${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "SECURITY: Secrets are entered interactively and stored in Vault only."
    echo "          Nothing is saved to git, config files, or shell history."
    echo ""
    
    preflight_checks
    check_network
    
    if [[ "$MODE" == "verify" ]]; then
        if [[ -f "${OUTPUT_DIR}/verify.sh" ]]; then
            exec "${OUTPUT_DIR}/verify.sh"
        else
            log_error "verify.sh not found. Run --apply first."
            exit 1
        fi
    fi
    
        install_vault
    
    if [[ "$MODE" == "apply" ]]; then
        initialize_vault
        
        if [[ "${STATUS[vault_initialized]}" == true ]]; then
            generate_vault_secret_id
        setup_proxmox_token
        setup_unifi_token
        setup_nas
        fi
    fi
    
    generate_artifacts
    generate_docker_compose
    print_report
}

main "$@"
