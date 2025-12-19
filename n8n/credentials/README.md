# MYCA Integration Fabric - Credential Management

This guide covers how to securely manage credentials for the MYCA n8n Integration Fabric.

## Security Principles

1. **NEVER commit secrets to git** - Always use `.gitignore` for `.env` and credential files
2. **Use least-privilege access** - Each integration should have minimal required permissions
3. **Label credentials by scope** - read-only, write, admin
4. **Rotate regularly** - Especially for admin-level credentials
5. **Use Vault in production** - External secret management for enterprise deployments

## Credential Storage Options

### Option 1: n8n Credentials Manager (Default)

n8n stores credentials encrypted in Postgres. This is the simplest approach for getting started.

**How to add credentials:**

1. Open n8n UI: http://localhost:5678
2. Go to **Settings** → **Credentials**
3. Click **+ Add Credential**
4. Select credential type (e.g., "Postgres", "API Key", "OAuth2")
5. Fill in details
6. **Name format**: `<Service> - <Scope>` (e.g., "GitHub - ReadOnly", "Postgres - Admin")
7. Click **Save**

**Credential types used in MYCA workflows:**

| Credential Type | Used By | Scope | Notes |
|----------------|---------|-------|-------|
| **Postgres** | Audit Logger, Event Intake | Write | Connection to myca_audit database |
| **Telegram Bot** | Alerts, Confirmation Gates | Write | For notifications and confirmations |
| **HTTP Header Auth** | Proxmox, UniFi, Generic Connector | Varies | API tokens |
| **HTTP Basic Auth** | UniFi | Read | Username/password |
| **OAuth2** | Google, GitHub, Slack, etc. | Varies | OAuth flow |
| **API Key** | OpenAI, Anthropic, many others | Write | Bearer tokens |

### Option 2: Environment Variables

For simple deployments, inject credentials via `.env` file.

**Format:**
```bash
N8N_CREDENTIAL_<TYPE>_<NAME>=<value>
```

**Example:**
```bash
# OpenAI API Key
N8N_CREDENTIAL_API_KEY_OPENAI=sk-...

# Telegram Bot Token
N8N_CREDENTIAL_API_KEY_TELEGRAM=123456:ABC...

# Proxmox API Token
N8N_CREDENTIAL_HEADER_PROXMOX=PVEAPIToken=user@pam!token=...
```

Add these to `/n8n/.env` and restart n8n:
```bash
docker-compose restart n8n
```

### Option 3: HashiCorp Vault (Production)

For production deployments, use Vault as the single source of truth for secrets.

**Architecture:**
```
Vault → Vault Agent (sidecar) → template files → n8n env vars
```

**Setup:**

1. **Store secrets in Vault:**
```bash
vault kv put secret/myca/n8n/postgres \
  host=postgres \
  port=5432 \
  database=n8n \
  user=n8n \
  password=<secure-password>

vault kv put secret/myca/n8n/telegram \
  bot_token=<telegram-token>

vault kv put secret/myca/n8n/openai \
  api_key=<openai-key>
```

2. **Create Vault policy:**
```hcl
# /vault/policies/n8n-policy.hcl
path "secret/data/myca/n8n/*" {
  capabilities = ["read"]
}
```

3. **Apply policy:**
```bash
vault policy write n8n-policy /vault/policies/n8n-policy.hcl
```

4. **Configure Vault Agent:**
Create `/n8n/vault-agent-config.hcl`:
```hcl
vault {
  address = "http://vault:8200"
}

auto_auth {
  method {
    type = "approle"
    config = {
      role_id_file_path = "/vault/role-id"
      secret_id_file_path = "/vault/secret-id"
    }
  }
}

template {
  source = "/vault/templates/n8n-credentials.env.tpl"
  destination = "/vault/secrets/n8n-credentials.env"
  command = "docker-compose restart n8n"
}
```

5. **Create template:**
```bash
# /vault/templates/n8n-credentials.env.tpl
{{ with secret "secret/data/myca/n8n/postgres" }}
DB_POSTGRESDB_PASSWORD={{ .Data.data.password }}
{{ end }}

{{ with secret "secret/data/myca/n8n/telegram" }}
N8N_CREDENTIAL_API_KEY_TELEGRAM={{ .Data.data.bot_token }}
{{ end }}

{{ with secret "secret/data/myca/n8n/openai" }}
N8N_CREDENTIAL_API_KEY_OPENAI={{ .Data.data.api_key }}
{{ end }}
```

6. **Uncomment vault-agent service in docker-compose.yml**

7. **Restart stack:**
```bash
docker-compose down
docker-compose up -d
```

## Required Credentials

### 1. Postgres Database (REQUIRED)

**Purpose**: Audit logging, event storage

**Type**: Postgres credential

**Details:**
- Host: `postgres` (Docker network) or `localhost` (external)
- Port: `5432`
- Database: `n8n`
- User: `n8n`
- Password: (from `.env` file)

**Test:**
```sql
docker exec -it myca-n8n-postgres psql -U n8n -c "SELECT 1;"
```

### 2. Telegram Bot (REQUIRED for alerts)

**Purpose**: Alerts, confirmation gates

**Type**: Telegram Bot API credential

**Setup:**
1. Talk to [@BotFather](https://t.me/botfather) on Telegram
2. Create new bot: `/newbot`
3. Copy bot token (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
4. Get your chat ID:
   - Send message to your bot
   - Visit: `https://api.telegram.org/bot<TOKEN>/getUpdates`
   - Find `chat.id` in response

**Add to n8n:**
- Name: `MYCA Alerts`
- Access Token: `<bot-token>`
- Base URL: `https://api.telegram.org` (default)

### 3. Proxmox API Token (REQUIRED for Ops workflows)

**Purpose**: VM management, snapshots, inventory

**Type**: HTTP Header Auth

**Setup in Proxmox:**
```bash
# Create API token
pveum user token add <user>@pam <token-id> --privsep 0

# Example:
pveum user token add root@pam n8n-token --privsep 0
```

**Add to n8n:**
- Name: `Proxmox API Token`
- Credential Type: `HTTP Header Auth`
- Header Name: `Authorization`
- Header Value: `PVEAPIToken=<user>@pam!<token-id>=<secret>`

### 4. UniFi Controller (REQUIRED for Ops workflows)

**Purpose**: Network topology, client list, traffic stats

**Type**: HTTP Basic Auth

**Setup:**
- Use existing UniFi admin account OR
- Create dedicated read-only account in UniFi controller

**Add to n8n:**
- Name: `UniFi Controller`
- Credential Type: `HTTP Basic Auth`
- Username: `<unifi-admin-user>`
- Password: `<unifi-password>`

### 5. OpenAI API Key (Optional - for AI workflows)

**Purpose**: GPT completions, embeddings

**Type**: API Key

**Setup:**
1. Go to https://platform.openai.com/api-keys
2. Create new API key
3. Set usage limits (recommended)

**Add to n8n:**
- Name: `OpenAI`
- API Key: `sk-...`

### 6. Google OAuth2 (Optional - for Google integrations)

**Purpose**: Sheets, Drive, Docs, Calendar, Gmail

**Type**: OAuth2

**Setup:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create project "MYCA Integration"
3. Enable APIs: Sheets, Drive, Docs, Calendar, Gmail
4. Create OAuth2 credentials
5. Add redirect URL: `http://localhost:5678/rest/oauth2-credential/callback`
6. Download client_id and client_secret

**Add to n8n:**
- Name: `Google OAuth2 - ReadWrite`
- Client ID: `<client-id>`
- Client Secret: `<client-secret>`
- Scopes: (n8n will prompt based on operations)

### 7. GitHub OAuth2/Token (Optional - for DevTools workflows)

**Purpose**: Repositories, issues, PRs, CI triggers

**Type**: OAuth2 or Personal Access Token

**Setup (Personal Access Token):**
1. Go to https://github.com/settings/tokens
2. Generate new token (fine-grained)
3. Set permissions: Contents (read/write), Issues (read/write), Pull requests (read/write)
4. Set expiration (90 days recommended)

**Add to n8n:**
- Name: `GitHub - ReadWrite`
- Credential Type: `GitHub OAuth2`
- Access Token: `ghp_...`

## Credential Rotation

Regular rotation schedule:

| Credential | Rotate Every | Priority |
|-----------|--------------|----------|
| Admin tokens (Proxmox, UniFi) | 90 days | HIGH |
| API keys (OpenAI, etc.) | 180 days | MEDIUM |
| OAuth2 tokens | 1 year | LOW (auto-refresh) |
| Postgres passwords | 1 year | LOW (internal) |

**Rotation process:**

1. **Generate new credential** in service (don't delete old yet)
2. **Add to n8n** with `_v2` suffix (e.g., `Proxmox API Token_v2`)
3. **Update workflows** to use new credential
4. **Test** with `test_api.ps1`
5. **Delete old credential** from service
6. **Remove old credential** from n8n

## Least Privilege Configuration

### Read-Only Credentials

For auditing and monitoring, create read-only credentials:

**Proxmox read-only:**
```bash
pveum role add ReadOnly -privs "Sys.Audit,VM.Audit"
pveum user add n8n-readonly@pve --password <password>
pveum aclmod / -user n8n-readonly@pve -role ReadOnly
```

**Postgres read-only:**
```sql
CREATE USER n8n_readonly WITH PASSWORD '<password>';
GRANT CONNECT ON DATABASE n8n TO n8n_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO n8n_readonly;
```

**GitHub read-only token:**
- Permissions: Contents (read), Issues (read), Pull requests (read)

### Write Credentials

For automation that modifies data:

**Proxmox write:**
- Include: `VM.Config,VM.Snapshot`

**Postgres write:**
```sql
GRANT INSERT, UPDATE ON myca_audit, myca_events TO n8n;
```

**GitHub write token:**
- Permissions: Contents (read/write), Issues (read/write)

### Admin Credentials

Only for critical operations requiring confirmation:

**Proxmox admin:**
- Full privileges
- Used for: VM creation/deletion, host configuration

**Always require confirm=true for admin credentials!**

## Credential Audit

Query credential usage from audit logs:

```sql
-- Credential usage by integration
SELECT 
  integration,
  COUNT(*) as usage_count,
  MAX(timestamp) as last_used
FROM myca_audit
WHERE risk_level IN ('write', 'admin')
GROUP BY integration
ORDER BY usage_count DESC;

-- Failed authentications
SELECT *
FROM myca_audit
WHERE error_message LIKE '%auth%' 
   OR error_message LIKE '%401%'
   OR error_message LIKE '%403%'
ORDER BY timestamp DESC;
```

## Emergency: Credential Compromise

If a credential is compromised:

1. **IMMEDIATELY revoke** in the source service
2. **Pause affected workflows** in n8n
3. **Generate new credential** with different name
4. **Update workflows**
5. **Review audit logs** for unauthorized usage:
```sql
SELECT * FROM myca_audit 
WHERE integration = '<compromised-integration>' 
  AND timestamp > '<compromise-date>'
ORDER BY timestamp DESC;
```
6. **Alert team** via Telegram/Slack

## Troubleshooting

### "Credential not found" error
- Check credential name matches workflow reference exactly (case-sensitive)
- Ensure credential is saved in n8n UI
- Restart n8n: `docker-compose restart n8n`

### OAuth2 token expired
- n8n should auto-refresh
- If not, re-authorize in n8n UI
- Check OAuth2 app hasn't been revoked

### Vault connection failing
- Check Vault agent logs: `docker-compose logs vault-agent`
- Verify Vault policy allows access: `vault policy read n8n-policy`
- Test token: `vault token lookup`

### API authentication failing
- Test credential directly with curl first
- Check for special characters that need escaping
- Verify API hasn't changed authentication method
- Check n8n logs for exact error: `docker-compose logs n8n | grep -i auth`

## Best Practices

1. **Use descriptive names**: `GitHub - Morgan ReadOnly` not `gh-token-1`
2. **Document scope in notes**: Add "Read-only for monitoring" in credential description
3. **Test before production**: Use test accounts/tokens first
4. **Monitor usage**: Review audit logs weekly
5. **Backup credentials**: Export credential names (not values!) to documentation
6. **Use Vault for production**: Don't rely on n8n-only storage for critical systems
7. **Enable MFA**: On all service accounts that support it
8. **Review permissions**: Quarterly audit of what each credential can access
