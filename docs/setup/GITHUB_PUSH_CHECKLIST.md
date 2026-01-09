# GitHub Push Checklist

> **Purpose**: Pre-push verification to ensure no secrets are exposed  
> **Run before**: Every push to GitHub

---

## Quick Verification Commands

```powershell
# Run these before pushing to GitHub

# 1. Check for hardcoded secrets (should return nothing)
Select-String -Path "*.py","*.ts","*.js" -Pattern "(password|secret|api_key|token)\s*[=:]\s*['\"][^'\"]{8,}['\"]" -Recurse

# 2. Check for common API key patterns (should return nothing)
Select-String -Path "*" -Pattern "(sk-|pk_|AKIA|ghp_|gho_)" -Recurse -Exclude "*.md"

# 3. Verify .env files are not staged
git status | Select-String ".env"

# 4. Check what will be committed
git diff --cached --name-only
```

---

## Files That Should NEVER Be Committed

| File/Pattern | Reason |
|--------------|--------|
| `.env` | Local environment with secrets |
| `.env.local` | Local overrides with secrets |
| `.env.production` | Production secrets |
| `*credentials*` | Credential files |
| `*.pem`, `*.key` | Private keys |
| `secrets/` | Secrets directory |
| `*-token`, `*-secret` | Token files |

---

## Files Fixed for This Push

The following files were updated to remove hardcoded credentials:

1. **test_unifi.py** - API key moved to `UNIFI_API_KEY` environment variable
2. **test_proxmox_simple.py** - Token moved to `PROXMOX_TOKEN_ID` and `PROXMOX_TOKEN_SECRET` environment variables

---

## Safe Files to Commit

These files contain example/placeholder values only:

| File | Content |
|------|---------|
| `env.example` | Template with placeholder values |
| `config/development.env` | Non-secret development config |
| `config/production.env` | Non-secret production config |
| `config/remote-dev.env` | Remote dev template |
| `docs/**/*.md` | Documentation (examples use fake keys) |

---

## Pre-Push Checklist

- [ ] No real API keys in code
- [ ] No real passwords in code  
- [ ] No real tokens in code
- [ ] `.env` files not staged
- [ ] `secrets/` folder not staged
- [ ] Credential files not staged
- [ ] Test files use environment variables

---

## If You Find Exposed Secrets

If you accidentally pushed secrets to GitHub:

1. **Immediately revoke the exposed credentials**
2. Generate new credentials
3. Use `git filter-branch` or BFG Repo-Cleaner to remove from history
4. Force push the cleaned history
5. Notify team members to re-clone

```bash
# Remove sensitive file from entire git history
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch PATH_TO_FILE" \
  --prune-empty --tag-name-filter cat -- --all

# Force push
git push origin --force --all
```

---

## Environment Variables for Test Files

Set these before running test scripts:

```powershell
# UniFi
$env:UNIFI_API_KEY = "your-api-key"
$env:UNIFI_HOST = "192.168.0.1"

# Proxmox  
$env:PROXMOX_TOKEN_ID = "myca@pve!mas"
$env:PROXMOX_TOKEN_SECRET = "your-token-secret"
```

Or in bash:

```bash
export UNIFI_API_KEY="your-api-key"
export PROXMOX_TOKEN_ID="myca@pve!mas"
export PROXMOX_TOKEN_SECRET="your-token-secret"
```

---

*Security first - when in doubt, don't commit it!*
