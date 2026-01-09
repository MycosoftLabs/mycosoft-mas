# Security Hardening Guide

> **Version**: 1.0.0  
> **Last Updated**: January 2026  
> **Compliance Targets**: NIST SP 800-53, DoD SRG

This document outlines security hardening procedures for the MYCA infrastructure, aligning with NIST SP 800-53 controls and Department of Defense Security Requirements Guide (SRG) standards. Implementation of these controls prepares the system for enterprise and government use cases.

---

## Table of Contents

1. [Security Overview](#security-overview)
2. [NIST SP 800-53 Control Mapping](#nist-sp-800-53-control-mapping)
3. [Access Control (AC)](#access-control-ac)
4. [Audit and Accountability (AU)](#audit-and-accountability-au)
5. [Identification and Authentication (IA)](#identification-and-authentication-ia)
6. [System and Communications Protection (SC)](#system-and-communications-protection-sc)
7. [Secret Management with HashiCorp Vault](#secret-management-with-hashicorp-vault)
8. [Key and Credential Security](#key-and-credential-security)
9. [Compartmentalization Strategy](#compartmentalization-strategy)
10. [Network Segmentation](#network-segmentation)
11. [Pre-Launch Security Checklist](#pre-launch-security-checklist)
12. [Incident Response Plan](#incident-response-plan)
13. [Ongoing Security Maintenance](#ongoing-security-maintenance)

---

## Security Overview

### Security Principles

1. **Defense in Depth**: Multiple layers of security controls
2. **Least Privilege**: Minimum necessary access for each component
3. **Zero Trust**: Verify every request, assume breach
4. **Audit Everything**: Complete visibility into all actions
5. **Secure by Default**: Systems start in secure state

### Threat Model

| Threat | Mitigation | Priority |
|--------|------------|----------|
| Unauthorized API access | JWT auth, rate limiting, WAF | Critical |
| Data breach | Encryption at rest/transit, access controls | Critical |
| Credential exposure | Vault, environment variables, no hardcoding | Critical |
| DDoS attacks | Cloudflare protection, rate limiting | High |
| Internal threat | Audit logging, role-based access | High |
| Supply chain | Dependency scanning, image verification | Medium |

### Security Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          SECURITY LAYERS                                 │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 1: PERIMETER                                              │   │
│  │  - Cloudflare WAF                                                │   │
│  │  - DDoS Protection                                               │   │
│  │  - Bot Management                                                │   │
│  │  - SSL/TLS (Full Strict)                                         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 2: NETWORK                                                │   │
│  │  - VLAN Segmentation                                             │   │
│  │  - Firewall Rules                                                │   │
│  │  - Inter-VLAN ACLs                                               │   │
│  │  - Private Subnets                                               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 3: APPLICATION                                            │   │
│  │  - JWT Authentication                                            │   │
│  │  - Role-Based Access Control                                     │   │
│  │  - Input Validation                                              │   │
│  │  - Rate Limiting                                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 4: DATA                                                   │   │
│  │  - Encryption at Rest (AES-256)                                  │   │
│  │  - Encryption in Transit (TLS 1.3)                               │   │
│  │  - Database Access Controls                                       │   │
│  │  - Backup Encryption                                             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 5: SECRETS                                                │   │
│  │  - HashiCorp Vault                                               │   │
│  │  - Dynamic Secrets                                               │   │
│  │  - Secret Rotation                                               │   │
│  │  - Audit Logging                                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## NIST SP 800-53 Control Mapping

### Applicable Control Families

| Family | ID | Description | Implementation |
|--------|-----|-------------|----------------|
| Access Control | AC | User access management | RBAC, JWT, Vault |
| Audit | AU | Logging and accountability | Loki, Audit trails |
| Auth | IA | Identity verification | JWT, MFA-ready |
| System Protection | SC | Network and data protection | VLANs, TLS, encryption |
| Config Management | CM | System configuration | IaC, version control |
| Incident Response | IR | Security incident handling | Runbooks, alerts |
| Risk Assessment | RA | Threat identification | Threat modeling |
| System Integrity | SI | Integrity verification | Checksums, signing |

### DoD SRG Alignment

| Category | Control | Status |
|----------|---------|--------|
| CAT I | Critical vulnerabilities | Addressed |
| CAT II | Security misconfigurations | Addressed |
| CAT III | Best practices | In progress |

---

## Access Control (AC)

### AC-2: Account Management

**Super Admin Account Configuration:**

Only the super admin account should have access to:
- HashiCorp Vault root tokens
- Proxmox cluster administration
- UniFi network configuration
- Database direct access
- NAS administrative shares

**Implementation:**

```bash
# Create super admin user
useradd -m -G sudo,docker,admin -s /bin/bash superadmin

# Set strong password
passwd superadmin

# Configure SSH key authentication only
mkdir -p /home/superadmin/.ssh
chmod 700 /home/superadmin/.ssh
# Add public key to authorized_keys

# Disable password authentication for superadmin
echo "Match User superadmin
    PasswordAuthentication no
    AuthenticationMethods publickey" >> /etc/ssh/sshd_config
```

### AC-3: Access Enforcement

**Role-Based Access Control:**

| Role | Permissions | Scope |
|------|-------------|-------|
| super_admin | Full access | All systems |
| admin | System management | VMs, containers |
| operator | Service management | Application layer |
| developer | Read + deploy | Development resources |
| viewer | Read only | Dashboards, logs |

**API Role Implementation:**

```python
# mycosoft_mas/core/auth.py
from enum import Enum
from functools import wraps

class Role(Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    OPERATOR = "operator"
    DEVELOPER = "developer"
    VIEWER = "viewer"

ROLE_HIERARCHY = {
    Role.SUPER_ADMIN: [Role.ADMIN, Role.OPERATOR, Role.DEVELOPER, Role.VIEWER],
    Role.ADMIN: [Role.OPERATOR, Role.DEVELOPER, Role.VIEWER],
    Role.OPERATOR: [Role.VIEWER],
    Role.DEVELOPER: [Role.VIEWER],
    Role.VIEWER: [],
}

def require_role(required_role: Role):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_role = get_current_user_role()
            if not has_permission(user_role, required_role):
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

### AC-6: Least Privilege

**Service Account Permissions:**

| Service | Account | Permissions |
|---------|---------|-------------|
| MYCA API | myca-api | Database R/W, Vault read |
| Website | myca-web | API read, static serve |
| n8n | myca-n8n | Webhook endpoints only |
| Agents | myca-agent | API limited, own data only |

### AC-17: Remote Access

**SSH Hardening:**

```bash
# /etc/ssh/sshd_config
Protocol 2
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
AllowUsers superadmin myca
```

---

## Audit and Accountability (AU)

### AU-2: Auditable Events

**Events to Capture:**

| Event Category | Examples | Severity |
|----------------|----------|----------|
| Authentication | Login, logout, failed attempts | High |
| Authorization | Permission changes, access denied | High |
| Data Access | Read/write operations | Medium |
| Configuration | System changes | High |
| Administrative | User management, VM operations | High |

### AU-3: Audit Record Content

**Log Format Standard:**

```json
{
  "timestamp": "2026-01-09T12:00:00.000Z",
  "event_id": "uuid",
  "event_type": "authentication.login",
  "severity": "INFO",
  "user_id": "user-uuid",
  "user_ip": "192.168.0.x",
  "resource": "/api/v1/agents",
  "action": "POST",
  "result": "success",
  "details": {
    "user_agent": "...",
    "request_id": "..."
  }
}
```

### AU-6: Audit Review

**Audit Log Storage:**

```bash
# Audit logs stored on NAS
AUDIT_LOG_PATH=/mnt/mycosoft/audit/logs

# Retention: 365 days minimum
# Format: JSON Lines
# Rotation: Daily

# Configure rsyslog for centralized logging
cat >> /etc/rsyslog.d/50-myca.conf << 'EOF'
# MYCA Audit Logs
template(name="MYCAAudit" type="list") {
    constant(value="/mnt/mycosoft/audit/logs/")
    property(name="$year")
    constant(value="/")
    property(name="$month")
    constant(value="/")
    property(name="hostname")
    constant(value="-audit.log")
}

if $programname == 'myca-audit' then ?MYCAAudit
& stop
EOF
```

### Loki Integration

```yaml
# promtail-config.yaml for audit log ingestion
scrape_configs:
  - job_name: myca-audit
    static_configs:
      - targets:
          - localhost
        labels:
          job: audit
          __path__: /mnt/mycosoft/audit/logs/**/*.log
    pipeline_stages:
      - json:
          expressions:
            level: severity
            user: user_id
            event: event_type
```

---

## Identification and Authentication (IA)

### IA-2: User Identification

**JWT Token Structure:**

```python
# Token payload
{
    "sub": "user-uuid",
    "role": "admin",
    "permissions": ["read", "write", "admin"],
    "iat": 1704792000,
    "exp": 1704795600,  # 1 hour expiry
    "iss": "mycosoft-myca",
    "aud": "myca-api"
}
```

**Token Generation:**

```python
from datetime import datetime, timedelta
import jwt

def create_access_token(user_id: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iss": "mycosoft-myca",
        "aud": "myca-api"
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")
```

### IA-5: Authenticator Management

**Password Policy:**

| Requirement | Value |
|-------------|-------|
| Minimum length | 16 characters |
| Complexity | Upper, lower, number, special |
| History | Last 12 passwords |
| Max age | 90 days |
| Lockout | 5 failed attempts |

**API Key Management:**

```python
# API keys stored in Vault
# Format: myca_<service>_<random>
# Example: myca_agent_a1b2c3d4e5f6

# Key rotation: Every 30 days
# Key revocation: Immediate on compromise
```

### IA-8: MFA Preparation

**MFA-Ready Architecture:**

```python
# Future MFA implementation
class MFAProvider:
    def generate_totp_secret(self, user_id: str) -> str:
        """Generate TOTP secret for user"""
        pass
    
    def verify_totp(self, user_id: str, code: str) -> bool:
        """Verify TOTP code"""
        pass
    
    def send_sms_code(self, user_id: str) -> bool:
        """Send SMS verification code"""
        pass
```

---

## System and Communications Protection (SC)

### SC-8: Transmission Confidentiality

**TLS Configuration:**

```nginx
# Nginx SSL settings
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers off;
ssl_session_timeout 1d;
ssl_session_cache shared:SSL:50m;
ssl_stapling on;
ssl_stapling_verify on;
```

### SC-13: Cryptographic Protection

**Encryption Standards:**

| Use Case | Algorithm | Key Size |
|----------|-----------|----------|
| Data at rest | AES-256-GCM | 256-bit |
| Data in transit | TLS 1.3 | - |
| Password hashing | Argon2id | - |
| JWT signing | HS256/RS256 | 256-bit |
| API keys | CSPRNG | 256-bit |

### SC-28: Data at Rest Protection

**Database Encryption:**

```bash
# PostgreSQL TDE (Transparent Data Encryption)
# Configure in postgresql.conf

# Alternatively, filesystem-level encryption
cryptsetup luksFormat /dev/sdb1
cryptsetup open /dev/sdb1 mycosoft-encrypted
mkfs.ext4 /dev/mapper/mycosoft-encrypted
```

**Backup Encryption:**

```bash
# Encrypted backup script
#!/bin/bash
BACKUP_KEY=$(vault kv get -field=key secret/backup-encryption)
pg_dump mas | gpg --symmetric --cipher-algo AES256 --passphrase "$BACKUP_KEY" > backup.sql.gpg
```

---

## Secret Management with HashiCorp Vault

### Vault Installation

```bash
# Run setup script
sudo ./scripts/setup_vault.sh

# Or manual installation
wget https://releases.hashicorp.com/vault/1.15.0/vault_1.15.0_linux_amd64.zip
unzip vault_1.15.0_linux_amd64.zip
sudo mv vault /usr/local/bin/

# Configure
sudo mkdir -p /etc/vault.d
sudo cp config/vault/vault-config.hcl /etc/vault.d/vault.hcl
```

### Vault Configuration

```hcl
# /etc/vault.d/vault.hcl
storage "file" {
  path = "/mnt/mycosoft/vault/data"
}

listener "tcp" {
  address     = "127.0.0.1:8200"
  tls_disable = 0
  tls_cert_file = "/etc/vault.d/tls/vault.crt"
  tls_key_file  = "/etc/vault.d/tls/vault.key"
}

api_addr = "https://127.0.0.1:8200"

ui = true
```

### Secret Organization

```
secret/
├── myca/
│   ├── database/
│   │   ├── postgres         # PostgreSQL credentials
│   │   ├── redis            # Redis password
│   │   └── qdrant           # Qdrant API key
│   ├── api/
│   │   ├── jwt-secret       # JWT signing key
│   │   ├── api-keys         # Service API keys
│   │   └── webhook-secrets  # Webhook signatures
│   ├── integrations/
│   │   ├── proxmox          # Proxmox API token
│   │   ├── unifi            # UniFi credentials
│   │   ├── cloudflare       # Cloudflare API token
│   │   └── elevenlabs       # ElevenLabs API key
│   └── encryption/
│       ├── backup-key       # Backup encryption key
│       └── data-key         # Data encryption key
└── infrastructure/
    ├── nas-credentials      # NAS access
    └── ssh-keys             # SSH private keys
```

### AppRole Authentication

```bash
# Enable AppRole auth
vault auth enable approle

# Create policy for MYCA API
vault policy write myca-api - <<EOF
path "secret/data/myca/*" {
  capabilities = ["read"]
}
path "secret/data/myca/database/*" {
  capabilities = ["read"]
}
EOF

# Create AppRole
vault write auth/approle/role/myca-api \
    token_policies="myca-api" \
    token_ttl=1h \
    token_max_ttl=4h \
    secret_id_ttl=720h

# Get Role ID and Secret ID
vault read auth/approle/role/myca-api/role-id
vault write -f auth/approle/role/myca-api/secret-id
```

### Using Vault in Application

```python
import hvac

def get_vault_client():
    client = hvac.Client(url='https://127.0.0.1:8200')
    
    # AppRole authentication
    client.auth.approle.login(
        role_id=os.environ['VAULT_ROLE_ID'],
        secret_id=os.environ['VAULT_SECRET_ID']
    )
    
    return client

def get_secret(path: str) -> dict:
    client = get_vault_client()
    secret = client.secrets.kv.v2.read_secret_version(path=path)
    return secret['data']['data']

# Usage
db_creds = get_secret('myca/database/postgres')
DATABASE_URL = f"postgresql://{db_creds['username']}:{db_creds['password']}@localhost:5432/mas"
```

---

## Key and Credential Security

### Removing Exposed Keys from Code

**Step 1: Audit for exposed secrets**

```bash
# Scan for potential secrets
grep -rn "password\|secret\|api_key\|token" --include="*.py" --include="*.ts" --include="*.env"

# Use git-secrets or truffleHog
pip install truffleHog
trufflehog filesystem --directory=.
```

**Step 2: Move to environment variables**

```python
# Before (BAD)
API_KEY = "sk-1234567890abcdef"

# After (GOOD)
API_KEY = os.environ.get("API_KEY")
if not API_KEY:
    raise ValueError("API_KEY environment variable not set")
```

**Step 3: Add to Vault**

```bash
vault kv put secret/myca/api/elevenlabs api_key="sk-1234567890abcdef"
```

**Step 4: Update .gitignore**

```gitignore
# Secrets - NEVER commit
.env
.env.local
*.pem
*.key
credentials.json
secrets/
```

### Environment Variable Management

**Development (mycocomp):**

```powershell
# Store in user environment variables (not system)
[Environment]::SetEnvironmentVariable("VAULT_ADDR", "https://192.168.20.10:8200", "User")
[Environment]::SetEnvironmentVariable("VAULT_ROLE_ID", "<role-id>", "User")
```

**Production (VMs):**

```bash
# Use systemd environment files
# /etc/myca/environment
VAULT_ADDR=https://127.0.0.1:8200
VAULT_ROLE_ID=<role-id>
VAULT_SECRET_ID=<secret-id>

# Secure the file
chmod 600 /etc/myca/environment
chown root:myca /etc/myca/environment
```

---

## Compartmentalization Strategy

### Admin-Only Access to Sensitive Resources

**Requirement**: NAS storage, containers, and admin functions should only be accessible when the super admin is logged in.

**Implementation:**

### 1. NAS Access Control

```bash
# Create admin-only share
# In UniFi Console:
# Share: mycosoft-admin
# Access: superadmin only

# Mount only when needed
sudo mount -t cifs //192.168.0.1/mycosoft-admin /mnt/mycosoft-admin \
  -o username=superadmin,password="$(vault kv get -field=password secret/infrastructure/nas-admin)"
```

### 2. Container Access Gating

```python
# API endpoint protection
@app.get("/admin/containers")
@require_role(Role.SUPER_ADMIN)
async def list_containers():
    # Only accessible to super admin
    return docker_client.containers.list()

@app.post("/admin/containers/{container_id}/stop")
@require_role(Role.SUPER_ADMIN)
async def stop_container(container_id: str):
    container = docker_client.containers.get(container_id)
    container.stop()
    audit_log("container.stop", container_id)
    return {"status": "stopped"}
```

### 3. Session-Based Access

```python
# Admin session management
class AdminSession:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.created_at = datetime.utcnow()
        self.expires_at = self.created_at + timedelta(hours=4)
        self.resources_unlocked = []
    
    def unlock_resource(self, resource: str):
        if not self.is_valid():
            raise SessionExpired()
        self.resources_unlocked.append(resource)
        audit_log("resource.unlock", resource, self.user_id)
    
    def is_valid(self) -> bool:
        return datetime.utcnow() < self.expires_at
```

### 4. Confirmation Gates for Destructive Operations

```python
# Two-step confirmation for dangerous operations
@app.post("/admin/vm/{vmid}/delete")
@require_role(Role.SUPER_ADMIN)
async def delete_vm(vmid: int, confirmation_token: str = None):
    if not confirmation_token:
        # Generate confirmation token
        token = generate_confirmation_token(
            action="delete_vm",
            resource=vmid,
            expires_in=300  # 5 minutes
        )
        return {
            "status": "confirmation_required",
            "message": f"This will permanently delete VM {vmid}. Use the token to confirm.",
            "confirmation_token": token,
            "expires_in": 300
        }
    
    # Verify confirmation token
    if not verify_confirmation_token(confirmation_token, "delete_vm", vmid):
        raise HTTPException(status_code=400, detail="Invalid or expired confirmation token")
    
    # Proceed with deletion
    proxmox_client.delete_vm(vmid)
    audit_log("vm.delete", vmid)
    return {"status": "deleted"}
```

---

## Network Segmentation

### VLAN Security Zones

| Zone | VLAN | Trust Level | Access |
|------|------|-------------|--------|
| Management | 1 | High | Admin only |
| Production | 20 | Medium | Services + Admin |
| Agents | 30 | Low | Limited API access |
| IoT | 40 | Untrusted | Data push only |

### Firewall Implementation

See [UBIQUITI_NETWORK_INTEGRATION.md](./UBIQUITI_NETWORK_INTEGRATION.md) for detailed firewall rules.

**Key Principles:**

1. Default deny between VLANs
2. Explicit allow for required traffic
3. Log all denied traffic
4. Rate limit all allowed traffic

---

## Pre-Launch Security Checklist

### Critical (Must complete before launch)

- [ ] **Secrets**: All secrets migrated to Vault
- [ ] **Code scan**: No hardcoded credentials in codebase
- [ ] **SSL**: Valid certificates, TLS 1.2+ only
- [ ] **Auth**: JWT authentication enabled on all APIs
- [ ] **CORS**: Restricted to allowed origins
- [ ] **Headers**: Security headers configured
- [ ] **Firewall**: VLAN rules implemented
- [ ] **Audit**: Logging enabled for all actions

### High Priority (Complete within first week)

- [ ] **Rate limiting**: Configured on all endpoints
- [ ] **WAF**: Cloudflare rules enabled
- [ ] **Backups**: Encrypted backup system tested
- [ ] **Monitoring**: Security alerts configured
- [ ] **Updates**: All systems patched to latest
- [ ] **Access review**: User permissions audited

### Medium Priority (Complete within first month)

- [ ] **Penetration test**: External security assessment
- [ ] **MFA**: Multi-factor authentication enabled
- [ ] **Secret rotation**: Automated rotation configured
- [ ] **Incident response**: Runbooks documented
- [ ] **Training**: Team security awareness

---

## Incident Response Plan

### Severity Levels

| Level | Description | Response Time | Escalation |
|-------|-------------|---------------|------------|
| P1 | Data breach, service compromise | Immediate | All hands |
| P2 | Security vulnerability exploited | 1 hour | Security lead |
| P3 | Suspicious activity | 4 hours | On-call |
| P4 | Security improvement needed | 24 hours | Normal workflow |

### Response Procedures

**P1 - Critical Incident:**

1. **Contain**: Isolate affected systems
   ```bash
   # Block compromised IP
   cloudflared access block <ip>
   
   # Disable compromised service
   systemctl stop myca-api
   ```

2. **Assess**: Determine scope and impact
3. **Eradicate**: Remove threat
4. **Recover**: Restore from known-good state
5. **Document**: Full incident report

**Contact List:**

| Role | Responsibility | Contact |
|------|---------------|---------|
| Super Admin | Final authority | Primary |
| Security Lead | Incident coordination | Secondary |
| Infrastructure | System access | On-call |

---

## Ongoing Security Maintenance

### Daily

- [ ] Review security alerts
- [ ] Check audit logs for anomalies
- [ ] Verify backup completion

### Weekly

- [ ] Review access logs
- [ ] Check for security updates
- [ ] Validate firewall rules

### Monthly

- [ ] Rotate API keys and tokens
- [ ] Review user access permissions
- [ ] Update threat model
- [ ] Security patch all systems

### Quarterly

- [ ] Full security audit
- [ ] Penetration testing
- [ ] Review incident response plan
- [ ] Update security documentation

---

## Related Documents

- [MASTER_SETUP_GUIDE.md](./MASTER_SETUP_GUIDE.md) - Overall architecture
- [UBIQUITI_NETWORK_INTEGRATION.md](./UBIQUITI_NETWORK_INTEGRATION.md) - Network security
- [TESTING_DEBUGGING_PROCEDURES.md](./TESTING_DEBUGGING_PROCEDURES.md) - Security testing
- [scripts/setup_vault.sh](../../scripts/setup_vault.sh) - Vault installation

---

*Document maintained by MYCA Security Team*
