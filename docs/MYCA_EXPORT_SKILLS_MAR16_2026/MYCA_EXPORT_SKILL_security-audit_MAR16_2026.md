# MYCA Export — Skill: Security Audit

**Export Date:** MAR16_2026  
**Skill Name:** security-audit  
**Purpose:** Run a security audit on the Mycosoft codebase. Use when checking for exposed secrets, validating authentication, auditing API keys, or before releases.  
**External Systems:** Base44, Claude, Perplexity, OpenAI, Grok — load when user requests security review.

---

## Quick Audit Checklist

```
Security Audit Progress:
- [ ] Step 1: Check for exposed secrets
- [ ] Step 2: Validate API key management
- [ ] Step 3: Check authentication/RBAC
- [ ] Step 4: Scan for vulnerabilities
- [ ] Step 5: Review container security
```

### Step 1: Check for exposed secrets

```bash
rg -i "password|secret|api_key|token|credential" --type py --type ts -g "!*.md" -g "!node_modules" -g "!.git"

git ls-files | rg "\.env"

rg "(sk-|pk-|ghp_|gho_|Bearer )" --type py --type ts
```

Things to look for:
- Hardcoded passwords (especially SSH credentials)
- API keys in source code
- Tokens in configuration files
- .env files in version control

### Step 2: Validate API key management

```bash
curl -s http://192.168.0.188:8001/api/security/audit/status
```

Verify:
- API keys are generated securely (not hardcoded)
- Keys are stored in environment variables, not code
- Key rotation is possible
- Unused keys are revoked

### Step 3: Check authentication/RBAC

Review `mycosoft_mas/security/`:
- `rbac.py` - Role-based access control
- `encryption.py` - Data encryption
- `audit.py` - Audit logging

Verify:
- All API endpoints require authentication where needed
- Role checks are enforced
- Audit logs capture security events

### Step 4: Scan for vulnerabilities

```bash
poetry run safety check
poetry run bandit -r mycosoft_mas/ -ll

cd /path/to/website
npm audit
```

### Step 5: Review container security

```bash
docker inspect <container> --format='{{.Config.User}}'
docker inspect <container> --format='{{.HostConfig.Privileged}}'
```

## Reporting

After audit, create a dated report:
`docs/SECURITY_AUDIT_MMMDD_YYYY.md`

Include:
- Findings (critical, warning, info)
- Remediation steps
- Status of previous findings
