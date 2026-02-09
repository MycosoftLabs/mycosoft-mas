# Secret Audit Report - February 9, 2026

**Auditor:** Security Auditor Agent (Workstream 2 - Security Hardening)
**Scope:** Full MAS repository (`mycosoft-mas/`)
**Date:** 2026-02-09
**Status:** CRITICAL findings requiring immediate action

---

## Executive Summary

This audit identified **27 hardcoded secrets** across the MAS repository, including database passwords, API keys, SSH credentials, and connection strings embedded directly in source code. The `.env` file itself contains real API keys and is tracked by git (modified state). Additionally, the encryption module uses base64 encoding instead of real encryption, which is a known critical vulnerability.

**Severity Breakdown:**

| Severity | Count | Description |
|----------|-------|-------------|
| CRITICAL | 6 | Real passwords/API keys hardcoded in source files |
| HIGH | 12 | Database connection strings with credentials as fallback defaults |
| MEDIUM | 5 | Hardcoded VM IPs with service URLs (infrastructure exposure) |
| LOW | 3 | Placeholder/example values and informational issues |
| INFO | 1 | base64 used as encryption (known gap, tracked separately) |

---

## CRITICAL Findings

### C-1: `.env` file contains real API keys (committed to git)

**File:** `.env`
**Lines:** 80, 90, 93-94, 83
**Issue:** The `.env` file is tracked by git (shown as modified in `git status`) and contains real, active API keys and database credentials.

| Line | Variable | Contains |
|------|----------|----------|
| 80 | `NCBI_API_KEY` | Real NCBI API key (`eb2264e1...`) |
| 83 | `MINDEX_DATABASE_URL` | Real PostgreSQL credentials (`mycosoft:mycosoft_mindex_2026@192.168.0.189`) |
| 90 | `CHEMSPIDER_API_KEY` | Real ChemSpider API key (`TSif8Na...`) |
| 93 | `NOTION_API_KEY` | Real Notion integration token (`ntn_f727...`) |
| 94 | `NOTION_DATABASE_ID` | Real Notion database ID |

**Remediation:**
1. Add `.env` to `.gitignore` (verify it is properly ignored)
2. Rotate ALL exposed keys immediately (NCBI, ChemSpider, Notion)
3. Remove `.env` from git tracking: `git rm --cached .env`
4. Use `.env.example` for documentation (created in this workstream)

---

### C-2: SSH password hardcoded in deployment scripts

**File:** `scripts/run_sandbox_pull_and_mas_deploy.py`
**Line:** 12
**Content:** `PASSWORD = "Mushroom1!Mushroom1!"`

This is the SSH password for all VMs (187, 188, 189), hardcoded in a deployment script that is committed to the repository.

**Also at line:** 32 (`ssh187.connect(...)`) and 95 (`ssh188.connect(...)`)

**Remediation:** Replace with `os.environ.get("VM_SSH_PASSWORD")` or use SSH key-based authentication exclusively.

---

### C-3: SSH password hardcoded in MINDEX check script

**File:** `scripts/check_mindex_vm_189.py`
**Line:** 12
**Content:** `c.connect("192.168.0.189", username="mycosoft", password="Mushroom1!Mushroom1!", ...)`

**Remediation:** Replace with `os.environ.get("VM_SSH_PASSWORD")`.

---

### C-4: Real database password in myca_memory.py

**File:** `mycosoft_mas/memory/myca_memory.py`
**Line:** 182
**Content:** `"postgresql://mycosoft:Mushroom1!Mushroom1!@192.168.0.189:5432/mindex"`

Production database credentials with real password hardcoded as a fallback default.

**Remediation:** Change to `os.getenv("MINDEX_DATABASE_URL", "postgresql://localhost:5432/mindex")` (no credentials in fallback).

---

### C-5: Real database password in gpu_memory.py

**File:** `mycosoft_mas/memory/gpu_memory.py`
**Line:** 160
**Content:** `"postgresql://mycosoft:Mushroom1!Mushroom1!@192.168.0.189:5432/mindex"`

Same production credentials as C-4, duplicated in another module.

**Remediation:** Same as C-4.

---

### C-6: Real database password in earth2_memory.py

**File:** `mycosoft_mas/memory/earth2_memory.py`
**Line:** 156
**Content:** `"postgresql://mycosoft:Mushroom1!Mushroom1!@192.168.0.189:5432/mindex"`

Same production credentials as C-4, duplicated in another module.

**Remediation:** Same as C-4.

---

## HIGH Findings

### H-1: Hardcoded PostgreSQL connection string in timeline_search_tool.py

**File:** `mycosoft_mas/llm/tools/timeline_search_tool.py`
**Line:** 105
**Content:** `"postgresql://mycosoft:mycosoft@localhost:5432/mindex"`

Connection string with credentials used as fallback default in `os.getenv()`.

**Remediation:** Use `os.getenv("MINDEX_DATABASE_URL")` with no credential-bearing fallback, or use a safe fallback like `"postgresql://localhost:5432/mindex"`.

---

### H-2: Hardcoded PostgreSQL connection string in session_memory.py

**File:** `mycosoft_mas/memory/session_memory.py`
**Line:** 81
**Content:** `"postgresql://mycosoft:mycosoft@localhost:5432/mindex"`

**Remediation:** Same as H-1.

---

### H-3: Hardcoded PostgreSQL connection string in user_context.py

**File:** `mycosoft_mas/memory/user_context.py`
**Line:** 56
**Content:** `"postgresql://mycosoft:mycosoft@localhost:5432/mindex"`

**Remediation:** Same as H-1.

---

### H-4: Hardcoded PostgreSQL connection string in vector_memory.py

**File:** `mycosoft_mas/memory/vector_memory.py`
**Line:** 34
**Content:** `"postgresql://mycosoft:mycosoft@localhost:5432/mindex"`

**Remediation:** Same as H-1.

---

### H-5: Hardcoded PostgreSQL connection string in mindex_graph.py

**File:** `mycosoft_mas/memory/mindex_graph.py`
**Line:** 41
**Content:** `"postgresql://mycosoft:mycosoft@localhost:5432/mindex"`

**Remediation:** Same as H-1.

---

### H-6: Hardcoded PostgreSQL connection string in health_check.py

**File:** `mycosoft_mas/monitoring/health_check.py`
**Line:** 53
**Content:** `"postgresql://mycosoft:mycosoft@localhost:5432/mindex"`

**Remediation:** Same as H-1.

---

### H-7: Hardcoded PostgreSQL connection string in base_collector.py

**File:** `mycosoft_mas/collectors/base_collector.py`
**Line:** 143
**Content:** `"postgresql://mycosoft:mycosoft@localhost:5432/mindex"`

**Remediation:** Same as H-1.

---

### H-8: Hardcoded PostgreSQL connection string in mindex_client.py

**File:** `mycosoft_mas/integrations/mindex_client.py`
**Line:** 75
**Content:** `"postgresql://mindex:mindex@localhost:5432/mindex"`

**Remediation:** Same as H-1.

---

### H-9: Hardcoded PostgreSQL connection string in search_memory.py

**File:** `mycosoft_mas/memory/search_memory.py`
**Line:** 293
**Content:** `"postgresql://mycosoft:Mushroom1!Mushroom1!@192.168.0.189:5432/mindex"`

Production credentials with real password in fallback. Same severity as CRITICAL findings C-4/C-5/C-6.

**Remediation:** Same as C-4.

---

### H-10: Hardcoded PostgreSQL credentials in deployment script docker run

**File:** `scripts/run_sandbox_pull_and_mas_deploy.py`
**Lines:** 128-129, 138-139
**Content:** `-e DATABASE_URL=postgresql://mycosoft:mycosoft@192.168.0.188:5432/mindex`

Docker run commands embed database URLs with credentials.

**Remediation:** Use `--env-file` or Docker secrets instead of inline `-e` with credentials.

---

### H-11: Hardcoded SSH host with StrictHostKeyChecking disabled

**File:** `mycosoft_mas/core/routers/coding_api.py`
**Lines:** 319, 321
**Content:** `ssh -o StrictHostKeyChecking=no ... mycosoft@192.168.0.187`

SSH commands with host key checking disabled and hardcoded target host.

**Remediation:** Use `os.getenv("SANDBOX_VM_HOST", "192.168.0.187")` and enable host key checking.

---

### H-12: Hardcoded sandbox host in coding_agent.py

**File:** `mycosoft_mas/agents/coding_agent.py`
**Line:** 430
**Content:** `sandbox_host = "192.168.0.187"`

**Remediation:** Use `os.getenv("SANDBOX_VM_HOST", "192.168.0.187")`.

---

## MEDIUM Findings

### M-1: Hardcoded NAS IP in blob_manager.py

**File:** `mycosoft_mas/mindex/blob_manager.py`
**Lines:** 49, 458
**Content:** `WINDOWS_NAS_PATH = r"\\192.168.0.105\mycosoft\mindex"` and `"http://192.168.0.189:8001"`

Infrastructure IPs hardcoded as class constants.

**Remediation:** Use environment variables `NAS_PATH` and `BLOB_STORAGE_URL`.

---

### M-2: Hardcoded MINDEX URL in myca_integration.py

**File:** `mycosoft_mas/mindex/myca_integration.py`
**Line:** 23
**Content:** `MINDEX_URL = os.environ.get("MINDEX_API_URL", "http://192.168.0.189:8001")`

While this uses env var with fallback, the fallback contains internal infrastructure IP. Acceptable for dev but should be `http://localhost:8000` for safety.

**Remediation:** Change fallback to a safe localhost default.

---

### M-3: base64 used as "encryption" in security_integration.py

**File:** `mycosoft_mas/security/security_integration.py`
**Lines:** 325, 336
**Content:** `base64.b64encode(data.encode())` used in what appears to be encrypt/decrypt methods

base64 is encoding, NOT encryption. Any data "encrypted" this way is trivially reversible. This is a known gap tracked in the system registry.

**Remediation:** Replace with proper AES-GCM encryption using the `cryptography` library. See separate security ticket.

---

### M-4: Hardcoded VM IPs in myca_main.py response string

**File:** `mycosoft_mas/core/myca_main.py`
**Line:** 211
**Content:** Status message revealing infrastructure details: "running on the MAS VM at 192.168.0.188"

**Remediation:** Remove infrastructure IPs from user-facing response strings.

---

### M-5: Hardcoded VM IP in coding_api.py response

**File:** `mycosoft_mas/core/routers/coding_api.py`
**Line:** 330
**Content:** `return {"status": "available", "version": version, "vm": "192.168.0.187"}`

**Remediation:** Use env var for VM address in API responses.

---

## LOW Findings

### L-1: Example API key in client __init__.py

**File:** `mycosoft_mas/clients/__init__.py`
**Line:** 17
**Content:** `api_key="your-api-key"` (placeholder in example/docstring)

**Remediation:** Acceptable as documentation example, but add comment clarifying it's a placeholder.

---

### L-2: Enum value named "TOP_SECRET" in defense_client.py

**File:** `mycosoft_mas/integrations/defense_client.py`
**Line:** 40
**Content:** `TOP_SECRET = "TOP SECRET"` (classification level enum, not an actual secret)

**Remediation:** None needed - this is a classification label enum, not a credential.

---

### L-3: Enum value "trade_secret" in ip_agent.py

**File:** `mycosoft_mas/agents/ip_agent.py`
**Line:** 38
**Content:** `TRADE_SECRET = "trade_secret"` (IP type enum, not an actual secret)

**Remediation:** None needed - this is an IP classification enum, not a credential.

---

## INFORMATIONAL

### I-1: `.gitignore` may not properly exclude `.env`

The `.env` file appears in `git status` as modified, indicating it may be tracked. Verify that `.gitignore` properly excludes `.env` and that the file has been removed from git tracking.

**Check:** `git ls-files --error-unmatch .env` -- if this succeeds, the file IS tracked and must be removed with `git rm --cached .env`.

---

## Consolidated Remediation Plan

### Phase 1: Immediate (Today)

1. **Rotate all exposed keys:** NCBI, ChemSpider, Notion API keys (exposed in `.env`)
2. **Change VM SSH password** on all VMs (187, 188, 189) since `Mushroom1!Mushroom1!` is in source code
3. **Change MINDEX database password** since `Mushroom1!Mushroom1!` and `mycosoft_mindex_2026` are in source code
4. **Ensure `.env` is in `.gitignore`** and run `git rm --cached .env` if tracked

### Phase 2: This Week

5. **Replace all hardcoded connection strings** in Python files with `os.getenv("MINDEX_DATABASE_URL")` -- no credential-bearing fallbacks
6. **Replace hardcoded SSH passwords** in scripts with env var lookups
7. **Replace hardcoded VM IPs** in agents/routers with env var lookups
8. **Add pre-commit hook** to detect secrets before they are committed

### Phase 3: This Month

9. **Replace base64 "encryption"** with AES-GCM in `security_integration.py`
10. **Implement Docker secrets** for container deployments instead of `-e` flags
11. **Set up credential rotation schedule** (quarterly minimum)
12. **Audit other repos** (Website, MINDEX, MycoBrain, NatureOS) for similar issues

---

## Files Requiring Changes (Summary)

| File | Lines | Severity | Issue |
|------|-------|----------|-------|
| `.env` | 80,83,90,93-94 | CRITICAL | Real API keys/credentials committed |
| `scripts/run_sandbox_pull_and_mas_deploy.py` | 12,32,95,128-129,138-139 | CRITICAL | Hardcoded SSH password and DB credentials |
| `scripts/check_mindex_vm_189.py` | 12 | CRITICAL | Hardcoded SSH password |
| `mycosoft_mas/memory/myca_memory.py` | 182 | CRITICAL | Real DB password in fallback |
| `mycosoft_mas/memory/gpu_memory.py` | 160 | CRITICAL | Real DB password in fallback |
| `mycosoft_mas/memory/earth2_memory.py` | 156 | CRITICAL | Real DB password in fallback |
| `mycosoft_mas/memory/search_memory.py` | 293 | HIGH | Real DB password in fallback |
| `mycosoft_mas/llm/tools/timeline_search_tool.py` | 105 | HIGH | DB credentials in fallback |
| `mycosoft_mas/memory/session_memory.py` | 81 | HIGH | DB credentials in fallback |
| `mycosoft_mas/memory/user_context.py` | 56 | HIGH | DB credentials in fallback |
| `mycosoft_mas/memory/vector_memory.py` | 34 | HIGH | DB credentials in fallback |
| `mycosoft_mas/memory/mindex_graph.py` | 41 | HIGH | DB credentials in fallback |
| `mycosoft_mas/monitoring/health_check.py` | 53 | HIGH | DB credentials in fallback |
| `mycosoft_mas/collectors/base_collector.py` | 143 | HIGH | DB credentials in fallback |
| `mycosoft_mas/integrations/mindex_client.py` | 75 | HIGH | DB credentials in fallback |
| `mycosoft_mas/core/routers/coding_api.py` | 319,321,330 | HIGH | Hardcoded SSH target, disabled host key checking |
| `mycosoft_mas/agents/coding_agent.py` | 430 | HIGH | Hardcoded VM IP |
| `mycosoft_mas/security/security_integration.py` | 325,336 | MEDIUM | base64 as encryption |
| `mycosoft_mas/mindex/blob_manager.py` | 49,458 | MEDIUM | Hardcoded NAS/service IPs |
| `mycosoft_mas/mindex/myca_integration.py` | 23 | MEDIUM | Internal IP in fallback |
| `mycosoft_mas/core/myca_main.py` | 211 | MEDIUM | Infrastructure IPs in user-facing text |

---

*This report was generated as part of Workstream 2 (Security Hardening) of the Mycosoft System-Wide Prioritization Rollout.*
