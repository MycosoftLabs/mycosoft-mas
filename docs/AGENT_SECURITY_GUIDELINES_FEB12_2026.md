# Agent Security Guidelines - February 12, 2026

**Status**: MANDATORY  
**Version**: 1.0  
**Date**: February 12, 2026  
**Author**: security-auditor agent  
**Applies To**: All MAS agent developers

---

## Purpose

This document provides **mandatory security guidelines** for all developers creating or modifying agents in the Mycosoft Multi-Agent System (MAS). Following these guidelines is required to maintain system security and prevent vulnerabilities.

---

## Core Security Principles

### 1. Never Hardcode Credentials

**Rule**: NEVER put passwords, API keys, tokens, or other secrets directly in source code.

**Why**: Secrets in code get committed to git, become visible to all developers, and are hard to rotate.

#### ❌ BAD Examples

```python
# BAD: Hardcoded database password
DATABASE_URL = "postgresql://mycosoft:Mushroom1!Mushroom1!@192.168.0.189:5432/mindex"

# BAD: Hardcoded API key
OPENAI_API_KEY = "sk-proj-abc123xyz789"

# BAD: Hardcoded JWT secret
JWT_SECRET = "my-super-secret-key-123"
```

#### ✅ GOOD Examples

```python
# GOOD: Required secret with no default
DATABASE_URL = os.getenv("MINDEX_DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("MINDEX_DATABASE_URL environment variable is required")

# GOOD: Optional secret with safe default
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # None if not set

# GOOD: Read from secure file
def load_jwt_secret():
    secret_file = Path("/run/secrets/jwt_secret")  # Docker secret
    if secret_file.exists():
        return secret_file.read_text().strip()
    return os.getenv("JWT_SECRET")
```

**Required Actions**:
- Use `os.getenv("VAR_NAME")` for all secrets
- No default value for required secrets (fail fast)
- Use safe defaults only for optional secrets
- Consider Docker Secrets or Azure Key Vault for production

---

### 2. Always Validate User Input

**Rule**: Assume all user input is malicious and validate/sanitize it.

**Why**: User input can contain prompt injection, SQL injection, shell injection, or path traversal attacks.

#### ❌ BAD Examples

```python
# BAD: Direct shell execution with user input
task = user_request["task"]
os.system(f"git commit -m '{task}'")

# BAD: Unsanitized SQL query
user_id = request.args.get("user_id")
query = f"SELECT * FROM users WHERE id = {user_id}"

# BAD: Unchecked file path
filename = request.args.get("file")
with open(f"/workspace/{filename}", "r") as f:
    return f.read()
```

#### ✅ GOOD Examples

```python
# GOOD: Shell-safe escaping
import shlex
task = user_request["task"]
safe_task = shlex.quote(task)
subprocess.run(["git", "commit", "-m", task], check=True)  # Even better: use list, not shell

# GOOD: Parameterized SQL query
user_id = request.args.get("user_id")
query = "SELECT * FROM users WHERE id = %s"
cursor.execute(query, (user_id,))

# GOOD: Path validation
import os.path
filename = request.args.get("file")
workspace = Path("/workspace")
filepath = (workspace / filename).resolve()
if not filepath.is_relative_to(workspace):
    raise ValueError("Invalid file path")
with open(filepath, "r") as f:
    return f.read()
```

**Required Actions**:
- Use `shlex.quote()` for shell arguments
- Use parameterized queries for SQL
- Validate file paths before accessing
- Validate URLs before fetching
- Check length limits on inputs
- Reject rather than sanitize when possible

---

### 3. Use Least Privilege

**Rule**: Request only the minimum permissions needed; run with lowest privilege possible.

**Why**: If an agent is compromised, limited permissions limit the damage.

#### ❌ BAD Examples

```python
# BAD: Connect as superuser
conn = psycopg2.connect("postgresql://postgres:password@host/db")

# BAD: Run container as root
# Dockerfile:
# USER root  # Never do this

# BAD: Mount entire host filesystem
# docker run -v /:/host ...
```

#### ✅ GOOD Examples

```python
# GOOD: Connect with limited user
conn = psycopg2.connect(os.getenv("DATABASE_URL"))  # Non-admin user

# GOOD: Run container as non-root
# Dockerfile:
# USER mycosoft  # Or use numeric UID

# GOOD: Mount only needed directories
# docker run -v /workspace:/workspace:ro ...
```

**Required Actions**:
- Use database users with minimal permissions
- Never run containers as root
- Never use `--privileged` flag
- Set resource limits (CPU, memory)
- Use read-only filesystem where possible
- Mount only needed host paths

**Database Permissions** (planned):
| User | Permissions | Use For |
|------|-------------|---------|
| `mas_readonly` | SELECT only | Health checks, monitoring |
| `mas_memory` | SELECT, INSERT on memory tables | Memory modules |
| `mas_orchestrator` | SELECT, INSERT, UPDATE on agent tables | Orchestrator |
| `mindex_api` | SELECT, INSERT, UPDATE | MINDEX API |

---

### 4. Audit and Log Everything

**Rule**: Log all security-relevant actions with full context.

**Why**: Logs are essential for detecting attacks, debugging issues, and forensics after incidents.

#### ❌ BAD Examples

```python
# BAD: No logging
result = execute_shell_command(command)

# BAD: Insufficient context
logger.info("Command executed")

# BAD: Logging secrets
logger.info(f"Connecting to {DATABASE_URL}")  # Contains password!
```

#### ✅ GOOD Examples

```python
# GOOD: Comprehensive logging with context
logger.info(
    "Executing shell command",
    extra={
        "agent_id": self.agent_id,
        "user_id": context.get("user_id"),
        "session_id": context.get("session_id"),
        "command": command,  # Only if safe to log
        "timestamp": datetime.utcnow().isoformat(),
    }
)
result = execute_shell_command(command)
logger.info(
    "Shell command completed",
    extra={
        "agent_id": self.agent_id,
        "exit_code": result.returncode,
        "duration_ms": duration,
    }
)

# GOOD: Redacting secrets before logging
safe_url = re.sub(r'://[^:]+:[^@]+@', '://***:***@', DATABASE_URL)
logger.info(f"Connecting to {safe_url}")
```

**Required to Log**:
- Shell commands executed (with user context)
- Database queries (with user context)
- File operations (read/write/delete)
- API calls to external services
- Authentication attempts (success/failure)
- Permission denials
- Errors and exceptions

**Never Log**:
- Passwords or API keys
- JWT tokens
- Encryption keys
- Sensitive user data (PII)
- Full database connection strings

---

### 5. Handle Secrets Properly

**Rule**: Protect secrets at all times; never expose them in logs, responses, or temporary files.

**Why**: Exposed secrets can be stolen and used to compromise the system.

#### ❌ BAD Examples

```python
# BAD: Secret in URL
response = requests.get(f"https://api.example.com?api_key={API_KEY}")

# BAD: Secret in exception message
if not API_KEY:
    raise ValueError(f"Missing API key: {API_KEY}")

# BAD: Secret in temp file
with open("/tmp/config.txt", "w") as f:
    f.write(f"API_KEY={API_KEY}\n")

# BAD: Secret in response
return {"status": "success", "api_key": API_KEY}
```

#### ✅ GOOD Examples

```python
# GOOD: Secret in header
headers = {"Authorization": f"Bearer {API_KEY}"}
response = requests.get("https://api.example.com", headers=headers)

# GOOD: Generic error message
if not API_KEY:
    raise ValueError("API_KEY environment variable is required")

# GOOD: Secret in memory only (or secure storage)
config = {"api_key": API_KEY}  # Never write to disk

# GOOD: Mask secrets in responses
return {"status": "success", "api_key": API_KEY[:8] + "***"}
```

**Required Actions**:
- Never log secrets (even partially)
- Never pass secrets in URLs
- Never write secrets to disk (except encrypted)
- Never return secrets in API responses
- Use `Authorization` header for API keys
- Rotate secrets after exposure
- Delete secrets from memory after use (if possible)

---

### 6. Review Code for Security

**Rule**: Run security tools and review code before committing.

**Why**: Automated tools catch many common vulnerabilities; human review catches the rest.

#### Pre-Commit Checklist

**Before every commit**:
```bash
# 1. Run detect-secrets to find hardcoded secrets
detect-secrets scan

# 2. Run bandit for Python security issues
bandit -r mycosoft_mas/

# 3. Run tests (including security tests)
pytest tests/ -v

# 4. Review diff for security issues
git diff
```

**Common Issues to Look For**:
- Hardcoded credentials
- Shell command construction
- SQL query construction
- File path validation
- Unvalidated user input
- Missing error handling
- Logging of secrets

**Pre-PR Checklist**:
- [ ] No hardcoded secrets (`detect-secrets scan`)
- [ ] No security issues (`bandit -r mycosoft_mas/`)
- [ ] All tests pass (`pytest`)
- [ ] Shell commands use `shlex.quote()` or list args
- [ ] SQL queries use parameterized queries
- [ ] File paths validated before access
- [ ] User input validated and sanitized
- [ ] Security-relevant actions logged
- [ ] Secrets not logged or exposed

---

## Secure Coding Patterns

### Pattern 1: Safe Shell Command Execution

```python
import subprocess
import shlex

def execute_command_safely(command: str, args: List[str]):
    """Execute shell command safely with argument escaping."""
    # Option 1: Use list (best - no shell involved)
    result = subprocess.run([command] + args, capture_output=True, check=True)
    
    # Option 2: If you must use shell, quote everything
    safe_args = [shlex.quote(arg) for arg in args]
    cmd = f"{command} {' '.join(safe_args)}"
    result = subprocess.run(cmd, shell=True, capture_output=True, check=True)
    
    return result
```

### Pattern 2: Safe Database Query

```python
import psycopg2

def fetch_user_safely(user_id: str):
    """Fetch user with parameterized query."""
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cursor = conn.cursor()
    
    # Use %s placeholder and pass params separately
    query = "SELECT * FROM users WHERE id = %s"
    cursor.execute(query, (user_id,))
    
    return cursor.fetchone()
```

### Pattern 3: Safe File Access

```python
from pathlib import Path

def read_file_safely(filename: str, workspace: Path = Path("/workspace")):
    """Read file with path validation."""
    # Resolve to absolute path
    filepath = (workspace / filename).resolve()
    
    # Check that resolved path is still inside workspace
    if not filepath.is_relative_to(workspace):
        raise ValueError(f"Access denied: {filename} is outside workspace")
    
    # Check file exists and is a regular file
    if not filepath.is_file():
        raise ValueError(f"File not found: {filename}")
    
    # Read file
    return filepath.read_text()
```

### Pattern 4: Safe API Call

```python
import requests

def call_api_safely(url: str, api_key: str):
    """Call external API safely."""
    # Validate URL
    if not url.startswith("https://"):
        raise ValueError("Only HTTPS URLs allowed")
    
    # Don't pass secrets in URL
    headers = {"Authorization": f"Bearer {api_key}"}
    
    # Set timeout
    response = requests.get(url, headers=headers, timeout=30)
    
    # Check status
    response.raise_for_status()
    
    return response.json()
```

---

## Testing Security

### Unit Tests for Security

```python
import pytest

def test_shell_injection():
    """Test that shell injection is prevented."""
    malicious_input = "'; rm -rf /; echo '"
    
    # Should not execute the rm command
    with pytest.raises(ValueError):
        execute_command_safely("echo", [malicious_input])

def test_sql_injection():
    """Test that SQL injection is prevented."""
    malicious_input = "1 OR 1=1"
    
    # Should treat as literal value, not SQL
    result = fetch_user_safely(malicious_input)
    assert result is None  # No user with that ID

def test_path_traversal():
    """Test that path traversal is prevented."""
    malicious_input = "../../../etc/passwd"
    
    # Should reject access outside workspace
    with pytest.raises(ValueError):
        read_file_safely(malicious_input)
```

### Security Test Suite

Create `tests/security/` directory with:
- `test_shell_injection.py`
- `test_sql_injection.py`
- `test_path_traversal.py`
- `test_secrets_exposure.py`
- `test_authentication.py`

---

## Security Tools

### Required Tools

| Tool | Purpose | When to Run |
|------|---------|-------------|
| **detect-secrets** | Find hardcoded secrets | Pre-commit, CI |
| **bandit** | Python security scanner | Pre-commit, CI |
| **safety** | Check dependencies for CVEs | Weekly, CI |
| **pytest** | Run security tests | Pre-commit, CI |

### Installation

```bash
# Install security tools
pip install detect-secrets bandit safety pytest

# Set up pre-commit hooks
pip install pre-commit
pre-commit install
```

### Running Scans

```bash
# Scan for secrets
detect-secrets scan

# Scan for security issues
bandit -r mycosoft_mas/ -ll  # Only high/medium severity

# Check dependencies
safety check

# Run security tests
pytest tests/security/ -v
```

---

## Incident Response

### If You Discover a Vulnerability

1. **Do NOT commit the vulnerability** to git
2. **Report immediately** to security team
3. **Document** the vulnerability privately
4. **Develop fix** in private branch
5. **Test fix** thoroughly
6. **Deploy fix** to all environments
7. **Rotate credentials** if exposed
8. **Post-mortem** after resolution

### If Credentials Are Exposed

1. **Rotate immediately** (don't wait)
2. **Check logs** for unauthorized access
3. **Report** to security team
4. **Review** how exposure happened
5. **Update processes** to prevent recurrence
6. **Document** in incident report

---

## Resources

### Documentation
- `docs/SECURITY_ASSUMPTIONS_FEB12_2026.md` - Security assumptions and trust model
- `docs/AUTONOMOUS_AGENT_THREAT_MODEL_FEB12_2026.md` - Threat model for agents
- `docs/CREDENTIAL_MANAGEMENT_BEST_PRACTICES_FEB09_2026.md` - Credential management
- `docs/SECRET_MANAGEMENT_POLICY_FEB09_2026.md` - Secret management policy

### Tools
- [detect-secrets](https://github.com/Yelp/detect-secrets) - Secret scanner
- [bandit](https://bandit.readthedocs.io/) - Python security linter
- [safety](https://pyup.io/safety/) - Dependency checker
- [OWASP Top 10](https://owasp.org/www-project-top-ten/) - Common vulnerabilities

### Training
- OWASP Secure Coding Practices
- Python Security Best Practices
- Container Security Fundamentals

---

## Enforcement

These guidelines are **mandatory** for all MAS agent development. Violations will result in:

1. **First violation**: Code review feedback, must fix before merge
2. **Repeated violations**: Additional security training required
3. **Critical violations** (exposed credentials): Immediate incident response

All pull requests must pass:
- `detect-secrets scan` (no secrets)
- `bandit -r mycosoft_mas/` (no security issues)
- `pytest tests/security/` (all security tests pass)
- Manual security review

---

## Updates

This document will be updated:
- When new vulnerabilities are discovered
- When new security tools are adopted
- When security processes change
- Quarterly during security audits

**Last Updated**: February 12, 2026  
**Next Review**: May 12, 2026

---

## Acknowledgments

These guidelines were created following the discovery of hardcoded credentials in the MAS codebase (February 2026) and are designed to prevent similar issues in the future.

**Status**: MANDATORY for all agent developers
