# Credential Management Best Practices

**Date:** Feb 09, 2026
**Status:** Active

---

## Overview

This document defines secure credential management practices for the Mycosoft Multi-Agent System. Following these practices prevents credential exposure in git history and ensures secrets are properly managed.

---

## Rules

### Never Commit Secrets

1. **Never commit real credentials** to git:
   - Passwords
   - API keys
   - Database connection strings with passwords
   - Private keys
   - Tokens (JWT, OAuth, etc.)

2. **Use `.env` files** for local development - these are gitignored
3. **Use `.env.example` files** with placeholder values to document required variables

### Pre-Commit Hook Enforcement

This repo uses `detect-secrets` pre-commit hook to block credential commits:

```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

If a commit is blocked, either:
1. Remove the secret and use an environment variable instead
2. If it's a false positive, add to `.secrets.baseline` (after review)

---

## Environment Variable Patterns

### Good Patterns

```bash
# Reference environment variable (never the actual value)
DATABASE_URL=${POSTGRES_CONNECTION_STRING}

# Placeholder that's obviously fake
API_KEY=your-api-key-here
DB_PASSWORD=change-me-in-production

# Empty placeholder
ANTHROPIC_API_KEY=
```

### Bad Patterns

```bash
# Actual credentials (NEVER commit these)
DB_PASSWORD=M4t51mur4$10T#
API_KEY=sk-ant-api03-xxxxxxxxxxxxx
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6...
```

---

## Where Secrets Should Live

| Environment | Secret Storage |
|------------|----------------|
| Local dev | `.env` (gitignored) |
| VM 187/188/189 | `/opt/mycosoft/.env` (protected) |
| CI/CD | GitHub Secrets |
| Production (future) | Azure Key Vault / Docker Secrets |

---

## Required Actions After Credential Exposure

If credentials are accidentally committed:

1. **Immediately rotate** the exposed credential
2. **Remove from git history** using `git filter-branch` or BFG Repo-Cleaner
3. **Force push** (coordinate with team)
4. **Audit** for unauthorized access during exposure window
5. **Document** the incident

### Credential Rotation Checklist

- [ ] PostgreSQL passwords on VMs 187, 188, 189
- [ ] Update `.env` files on all VMs
- [ ] Update any CI/CD secrets
- [ ] Verify services still work after rotation

---

## Files to Review

When auditing for hardcoded secrets, check:

- `.env` files (should be gitignored)
- `docker-compose*.yaml`
- `Dockerfile*`
- `.mcp.json`
- `.claude/` agent configurations
- Any `config.py` or `settings.py`
- Shell scripts in `scripts/`

---

## Tools

- **detect-secrets**: Pre-commit hook for scanning
- **truffleHog**: Git history scanner
- **GitHub Secret Scanning**: Automatic alerts for known secret patterns

---

## References

- `docs/SECRET_MANAGEMENT_POLICY_FEB09_2026.md` - Full policy
- `docs/SECURITY_BUGFIXES_FEB09_2026.md` - Security bug fixes
- `.pre-commit-config.yaml` - Pre-commit configuration
- `.secrets.baseline` - Detect-secrets baseline
