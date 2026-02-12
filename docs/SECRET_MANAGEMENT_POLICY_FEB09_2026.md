# Secret Management Policy

**Date:** February 9, 2026
**Status:** Active
**Applies to:** All Mycosoft repositories (MAS, Website, MINDEX, MycoBrain, NatureOS, Mycorrhizae, NLM, SDK, Platform-Infra)

---

## 1. Core Policy: No Secrets in Code

**All secrets, credentials, API keys, tokens, and passwords MUST be stored in environment variables or approved secret stores. They MUST NEVER appear in source code, configuration files committed to git, or documentation.**

### What Counts as a Secret

- API keys and tokens (Anthropic, Notion, ChemSpider, NCBI, Cloudflare, n8n, etc.)
- Database connection strings containing passwords
- SSH passwords and private keys
- JWT signing keys and secret keys
- OAuth client secrets and refresh tokens
- Proxmox/infrastructure API tokens
- SMTP passwords
- Any credential that grants access to a system

### Approved Storage Locations

| Storage | Use Case |
|---------|----------|
| `.env` file (local, gitignored) | Local development |
| Environment variables (OS-level) | VM services, systemd units |
| Docker `--env-file` or `-e` flags | Container deployments |
| GitHub Actions Secrets | CI/CD pipelines |
| HashiCorp Vault (future) | Production secret management |

### Banned Patterns

| Pattern | Why It's Banned |
|---------|----------------|
| Hardcoded passwords in Python/TypeScript | Committed to git history permanently |
| Base64-encoded secrets in source code | Not encryption, trivially reversible |
| Connection strings with passwords in scripts | Leaks credentials in version control |
| API keys in `.json` config files | Often committed accidentally |
| Passwords in shell scripts (`.sh`, `.ps1`) | Same as above |
| `.env` files committed to git | Exposes all secrets at once |

---

## 2. The `.env.example` Pattern

Every repository MUST have a `.env.example` file at its root containing:
- All environment variable names used by the project
- Descriptive placeholder values (never real credentials)
- Comments grouping variables by category
- Instructions to copy to `.env` and fill in real values

### Format

```bash
# Category Name
VARIABLE_NAME=descriptive-placeholder-value
API_KEY=your-service-api-key
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

### Rules

1. `.env.example` IS committed to git (it contains no secrets)
2. `.env` is NEVER committed to git (it contains real secrets)
3. `.gitignore` MUST include `.env`, `.env.local`, `.env.*.local`
4. When adding a new env var, update BOTH `.env` and `.env.example`
5. New developers copy `.env.example` to `.env` and fill in values

### Repository Checklist

| Repository | `.env.example` | Status |
|------------|---------------|--------|
| MAS (`mycosoft-mas`) | `.env.example` | Created Feb 9, 2026 |
| Website | `env.local.example` | Exists |
| MINDEX | `.env.example` | Created (verified Feb 9) |
| MycoBrain | N/A (firmware) | N/A |
| NatureOS | `.env.example` | Created (verified Feb 9) |
| Mycorrhizae | `.env.example` | Created (verified Feb 9) |
| Platform-Infra | `.env.example` | Created Feb 9, 2026 |

---

## 3. Python Code: Use `os.getenv()` with Safe Defaults

All Python code that needs credentials MUST use `os.getenv()` to read from environment variables. Default values MUST NOT contain real credentials.

### Correct Pattern

```python
import os

# Good: reads from env, safe fallback for local dev
DATABASE_URL = os.getenv("MINDEX_DATABASE_URL", "postgresql://localhost:5432/mindex")

# Good: reads from env, no default (will be None if not set)
API_KEY = os.getenv("CHEMSPIDER_API_KEY")

# Good: reads from env, raises if missing
SECRET_KEY = os.environ["SECRET_KEY"]  # Fails fast if not set
```

### Incorrect Patterns

```python
# BAD: hardcoded password in connection string default
DATABASE_URL = os.getenv("DB_URL", "postgresql://mycosoft:real_password@host:5432/db")

# BAD: hardcoded API key
API_KEY = "TSif8NaGxFixrCft4O581jGjIz2GnIo4TCQqM01h"

# BAD: hardcoded SSH password
client.connect("192.168.0.188", username="mycosoft", password="Mushroom1!Mushroom1!")
```

### Safe Defaults for Connection Strings

When a fallback default is needed for local development, use credential-free forms:

```python
# OK: no password in default (assumes local trust auth)
os.getenv("DATABASE_URL", "postgresql://localhost:5432/mindex")

# OK: explicit placeholder
os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/dbname")
```

---

## 4. Rotation Schedule

All API keys, tokens, and database passwords MUST be rotated on a quarterly basis (every 3 months).

### Rotation Calendar

| Quarter | Rotation Window | Responsible |
|---------|----------------|-------------|
| Q1 | January 1-7 | Infrastructure lead |
| Q2 | April 1-7 | Infrastructure lead |
| Q3 | July 1-7 | Infrastructure lead |
| Q4 | October 1-7 | Infrastructure lead |

### Rotation Checklist

1. **Database passwords**: PostgreSQL users on VM 189, Redis (if auth enabled)
2. **API keys**: Anthropic, Notion, ChemSpider, NCBI, Cloudflare, n8n
3. **Infrastructure tokens**: Proxmox API tokens, SSH passwords on all VMs
4. **OAuth tokens**: QuickBooks refresh token, GitHub PAT
5. **JWT signing keys**: MAS SECRET_KEY
6. **Communication tokens**: Telegram, Discord, Asana

### Rotation Procedure

1. Generate new credential
2. Update `.env` on all VMs and dev machines
3. Restart affected services
4. Verify services healthy
5. Revoke old credential
6. Log rotation in `docs/SECRET_ROTATION_LOG.md`

### Emergency Rotation

If a secret is found exposed (in git history, logs, or public), rotate IMMEDIATELY:
1. Generate new credential
2. Deploy with new credential
3. Revoke old credential
4. Audit access logs for unauthorized use
5. Run `git-filter-repo` if secret was committed to git (see Section 7)

---

## 5. CI/CD: GitHub Actions Secrets

### Rules

- All secrets used in CI/CD MUST be stored as GitHub Actions Secrets
- NEVER echo, print, or log secret values in CI/CD output
- Use `${{ secrets.SECRET_NAME }}` syntax exclusively
- Secrets are injected as environment variables at runtime

### Required GitHub Secrets

| Secret Name | Purpose |
|-------------|---------|
| `VM_SSH_KEY` | SSH private key for VM deployments |
| `CLOUDFLARE_API_TOKEN` | Cache purge after deployment |
| `DATABASE_URL` | PostgreSQL connection for migrations |
| `DOCKER_REGISTRY_TOKEN` | Docker image push (if applicable) |

### Example Workflow

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to VM
        env:
          SSH_KEY: ${{ secrets.VM_SSH_KEY }}
          CF_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}
        run: |
          # Use env vars, never hardcode
          ssh -i "$SSH_KEY" mycosoft@192.168.0.188 "cd /opt/mas && git pull"
```

---

## 6. Quarterly Audit Procedure

Run the following audit commands quarterly (at minimum) across all repositories:

### Secret Detection Scan

```bash
# Search for potential secrets in Python and TypeScript files
rg -i "password|secret|api.key|token" --type py --type ts --type json \
  --glob "!node_modules/**" --glob "!.env.example" --glob "!*.md"

# Search for hardcoded connection strings with credentials
rg "postgresql://\w+:\w+@" --type py

# Search for hardcoded SSH passwords
rg -i "password\s*=\s*[\"'][A-Za-z0-9!@#$%^&*]+" --type py

# Check .gitignore includes .env
grep -r "\.env" .gitignore
```

### Automated Tooling (Recommended)

```bash
# Python security scanner
poetry run bandit -r mycosoft_mas/ -ll

# Dependency vulnerability check
poetry run safety check

# Node.js dependency audit (website repo)
npm audit
```

### Audit Report

After each quarterly audit, create:
`docs/SECURITY_AUDIT_QUARTERLY_<QUARTER>_<YEAR>.md`

Include:
- Date and scope of audit
- Findings categorized by severity (Critical, High, Medium, Low)
- Remediation actions taken
- Outstanding items with timeline

---

## 7. Git History Remediation

If a real secret is found committed to git history, it MUST be removed.

### Using git-filter-repo

```bash
# Install git-filter-repo
pip install git-filter-repo

# Remove a file containing secrets from ALL history
git filter-repo --path <file-with-secret> --invert-paths

# Or replace specific strings in all history
git filter-repo --replace-text expressions.txt
# expressions.txt format: literal:OLD_SECRET==>REDACTED
```

### Important Notes

- `git-filter-repo` rewrites history; all team members must re-clone
- Force push is required after filtering: `git push --force --all`
- Rotate the exposed secret BEFORE running git-filter-repo
- Even after removal from git, consider the secret compromised and rotate it

---

## 8. Current Known Issues (Feb 9, 2026 Audit)

### CRITICAL: Hardcoded Secrets in `scripts/` Directory

The following scripts contain hardcoded credentials that should be replaced with `os.getenv()`:

| File | Line | Secret Type | Severity |
|------|------|-------------|----------|
| `scripts/run_sandbox_pull_and_mas_deploy.py` | 12 | SSH password | Critical |
| `scripts/check_mindex_vm_189.py` | 12 | SSH password | Critical |
| `scripts/check_nas_mount.py` | 10 | SSH password | Critical |
| `scripts/fix_orchestrator.py` | 10 | SSH password | Critical |
| `scripts/check_mushroom1_videos.py` | 10 | SSH password | Critical |
| `scripts/direct_deploy_and_purge.py` | 19 | Cloudflare API token | Critical |
| `scripts/ssh_proxmox.py` | 9 | Proxmox password | Critical |
| `scripts/network_health_check.py` | 17 | Proxmox API token | Critical |
| `scripts/list_n8n_cred_types.py` | 6 | n8n JWT API key | Critical |
| `scripts/list_vms.py` | 8 | Proxmox API token | Critical |
| `scripts/check_gpu_availability.py` | 15 | Proxmox API token | Critical |
| `scripts/setup_mas_vm_auto.py` | 160 | DB password | Critical |

### HIGH: Hardcoded DB Connection Defaults in Library Code

These files use `os.getenv()` but have credentials in fallback defaults:

| File | Line | Default Contains |
|------|------|-----------------|
| `mycosoft_mas/llm/tools/timeline_search_tool.py` | 105 | `mycosoft:mycosoft` |
| `mycosoft_mas/memory/session_memory.py` | 81 | `mycosoft:mycosoft` |
| `mycosoft_mas/memory/user_context.py` | 56 | `mycosoft:mycosoft` |
| `mycosoft_mas/memory/vector_memory.py` | 34 | `mycosoft:mycosoft` |
| `mycosoft_mas/memory/mindex_graph.py` | 41 | `mycosoft:mycosoft` |
| `mycosoft_mas/monitoring/health_check.py` | 53 | `mycosoft:mycosoft` |
| `mycosoft_mas/collectors/base_collector.py` | 143 | `mycosoft:mycosoft` |
| `mycosoft_mas/integrations/mindex_client.py` | 75 | `mindex:mindex` |
| `mycosoft_mas/voice/supabase_client.py` | 27 | `postgres:postgres` |
| `mycosoft_mas/nlm/memory_store.py` | 22 | `postgres:postgres` |
| `mycosoft_mas/natureos/memory_connector.py` | 22 | `postgres:postgres` |
| `mycosoft_mas/mindex/memory_bridge.py` | 23 | `postgres:postgres` |

### HIGH: Hardcoded DB URIs in Deploy Scripts

| File | Lines | Contains |
|------|-------|----------|
| `scripts/run_sandbox_pull_and_mas_deploy.py` | 129, 139 | Full connection string |
| `scripts/deploy_full_production.py` | 282, 413 | Full connection strings |
| `scripts/fix_vm_docker_compose.py` | 195 | `mas:maspassword` |
| `scripts/deploy_to_vm.py` | 272 | `mas:maspassword` |
| `scripts/setup_mas_vm_auto.py` | 160 | `mycosoft_secure_2026` |

### MEDIUM: `.env` Contains Real API Keys

The `.env` file contains real API keys that are tracked by git (file is modified in git status). These keys should be in `.env` (gitignored) only:

- `NCBI_API_KEY` (real key)
- `CHEMSPIDER_API_KEY` (real key)
- `NOTION_API_KEY` (real key)
- `MINDEX_DATABASE_URL` (real credentials)

### FIXED: `mycosoft_mas/services/security.py`

- Line 12: `secret_key` now reads from `os.getenv("SECRET_KEY")` instead of hardcoded string.

---

## 9. Remediation Priority

| Priority | Action | Timeline |
|----------|--------|----------|
| 1 (Immediate) | Rotate all secrets found in git history | This week |
| 2 (Immediate) | Fix all CRITICAL hardcoded secrets in `scripts/` | This week |
| 3 (This sprint) | Replace credential-containing defaults in library code | 2 weeks |
| 4 (This sprint) | Ensure `.env` is properly gitignored and not tracked | 2 weeks |
| 5 (Next sprint) | Add pre-commit hook for secret detection | 1 month |
| 6 (Next sprint) | Set up automated secret scanning in CI/CD | 1 month |
| 7 (Quarterly) | First scheduled rotation | April 1-7, 2026 |

---

## 10. Pre-Commit Hook (Recommended)

Add a pre-commit hook to prevent accidental secret commits:

```bash
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
```

Install with:
```bash
pip install pre-commit
pre-commit install
detect-secrets scan > .secrets.baseline
```

---

## References

- `docs/SECURITY_BUGFIXES_FEB09_2026.md` - Previous security fixes
- `docs/APIS_AND_KEYS_AUDIT_FEB06_2026.md` - API keys audit
- `docs/PRODUCTION_MIGRATION_RUNBOOK_FEB09_2026.md` - Rotation schedule in runbook
- `.env.example` - Template for environment variables
