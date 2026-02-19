# PersonaPlex Startup Hardening & Git Bloat Cleanup — Feb 09, 2026

## Summary

This session covered two areas: (1) cleaning up git bloat and GitHub hygiene, and (2) systematically hardening the PersonaPlex voice server startup scripts to fail fast with clear diagnostics instead of crashing with cryptic runtime errors.

---

## 1. Git Bloat Cleanup (earlier in session)

### What was removed from git tracking

| Item | Reason |
|------|--------|
| `venv/`, `venv311/` | Python virtualenvs — never committed |
| `*.log` files | Log files bloating repo |
| `firmware/**/build**/` | Compiled firmware artifacts |
| Backup files (`*.bak`, `*.backup`) | Redundant snapshots |
| `personaplex-repo/` | External submodule — not tracked in git |
| `.coverage` | Test coverage data file |
| `.wav` files | Audio files — binary blobs |

### `.gitignore` fixes

- **Corruption fix**: End of `.gitignore` had wide-character (UTF-16) corruption (`\u0000#\u0000 \u0000C...`). File was rewritten clean.
- **Pattern hardening**: `firmware/**/build*/` was supplemented with `firmware/**/build*/**` for robust content exclusion across all Git versions.

### Secrets removed from code

The following files had hardcoded credentials moved to environment variables:

| File | Was hardcoded | Now uses |
|------|---------------|----------|
| `_full_mindex_sync.py` | `NCBI_API_KEY`, DB password | `os.environ.get()` |
| `_quick_mindex_sync.py` | `NCBI_API_KEY`, DB password | `os.environ.get()` |

New env vars added to `.env.example`:
- `MINDEX_DB_HOST`, `MINDEX_DB_PORT`, `MINDEX_DB_USER`, `MINDEX_DB_PASSWORD`, `MINDEX_DB_NAME`
- `NCBI_API_KEY`, `SLACK_OAUTH_TOKEN`

---

## 2. PersonaPlex Startup Script Hardening

### Problem

Both startup scripts (`start_personaplex.py` and `_start_personaplex_no_cuda_graphs.py`) had:
- **Hardcoded absolute paths** that only worked on one machine
- **No validation** of dependencies before use → cryptic `ModuleNotFoundError` or silent path failures
- **Inconsistent error handling** between the two scripts

### Scripts fixed

| Script | Purpose |
|--------|---------|
| `start_personaplex.py` | Main server — CUDA graphs ENABLED (30ms/step, RTX 5090 performance mode) |
| `_start_personaplex_no_cuda_graphs.py` | Stability mode — CUDA graphs DISABLED (200ms/step, for debugging hangs) |

### Validation layers added (both scripts)

**Layer 1 — `personaplex-repo/moshi` directory**

```python
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
personaplex_path = os.path.join(SCRIPT_DIR, "personaplex-repo", "moshi")

if not os.path.isdir(personaplex_path):
    print("ERROR: personaplex-repo directory not found!")
    print("  git clone https://github.com/mycosoft/personaplex-repo.git personaplex-repo")
    sys.exit(1)
```

**Layer 2 — `models/personaplex-7b-v1` model directory** (`start_personaplex.py` only)

```python
model_dir = os.path.join(SCRIPT_DIR, "models", "personaplex-7b-v1")

if not os.path.isdir(model_dir):
    print("ERROR: PersonaPlex model directory not found!")
    print("  huggingface-cli download nvidia/personaplex-7b-v1 --local-dir models/personaplex-7b-v1")
    sys.exit(1)
```

**Layer 3 — Individual model files** (`start_personaplex.py` only)

```python
missing_files = []
for fpath, fname in [
    (moshi_weight, "Moshi weights"),
    (mimi_weight, "Mimi tokenizer weights"),
    (tokenizer, "Tokenizer model"),
]:
    if not os.path.isfile(fpath):
        missing_files.append(f"  - {fname}: {fpath}")

if missing_files:
    print("ERROR: Required model files missing!")
    # ... list missing files + download command
    sys.exit(1)
```

**Layer 4 — `voices/` directory (both scripts)**

`start_personaplex.py`:
```python
voice_prompt_dir = os.path.join(model_dir, "voices")

if not os.path.isdir(voice_prompt_dir):
    print("ERROR: Voice prompts directory not found!")
    print("  huggingface-cli download nvidia/personaplex-7b-v1 --local-dir models/personaplex-7b-v1")
    sys.exit(1)
```

`_start_personaplex_no_cuda_graphs.py` (with HuggingFace cache fallback):
```python
voice_prompt_dir = os.path.join(model_dir, "voices")
hf_cache_voice_dir = os.path.expanduser(r"~\.cache\huggingface\hub\models--nvidia--personaplex-7b-v1\...")

if not os.path.isdir(voice_prompt_dir):
    voice_prompt_dir = hf_cache_voice_dir  # Try cache

if not os.path.isdir(voice_prompt_dir):
    print("ERROR: Voice prompts directory not found!")
    print("Checked: local + HuggingFace cache")
    sys.exit(1)
```

### Path portability fix

All paths changed from hardcoded absolute (e.g. `r"c:\Users\admin2\..."`) to dynamic relative:

```python
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
personaplex_path = os.path.join(SCRIPT_DIR, "personaplex-repo", "moshi")
```

---

## 3. Required Setup for PersonaPlex (fresh clone)

### Step 1 — Clone personaplex-repo (not in git)
```powershell
cd c:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
git clone https://github.com/mycosoft/personaplex-repo.git personaplex-repo
```

### Step 2 — Download NVIDIA PersonaPlex model
```powershell
pip install huggingface_hub
huggingface-cli download nvidia/personaplex-7b-v1 --local-dir models/personaplex-7b-v1
```

### Step 3 — Start the server

Performance mode (CUDA graphs ON — required for real-time):
```powershell
python start_personaplex.py
```

Stability mode (CUDA graphs OFF — for debugging hangs):
```powershell
python _start_personaplex_no_cuda_graphs.py
```

Both scripts will now **fail fast** with clear instructions if any dependency is missing.

---

## 4. Commits Made This Session

| Commit | Description |
|--------|-------------|
| `fead85a78` | Git bloat cleanup — venv, logs, firmware builds, backups |
| `65e994aad` | Remove additional bloat — venv311, wav files |
| `d94dcbc07` | Untrack `.coverage` file |
| `48be27a7f` | Fix `.gitignore` corruption + fix `start_personaplex.py` hardcoded paths |
| `19d0e6434` | Fix `_start_personaplex_no_cuda_graphs.py` hardcoded paths |
| `e6f231ee9` | Make firmware build gitignore pattern more robust |
| `52e8ee2ee` | Add `model_dir` validation to `start_personaplex.py` |
| `cea6fac7a` | Add `voice_prompt_dir` validation to `_start_personaplex_no_cuda_graphs.py` |
| `665f73019` | Add `voice_prompt_dir` validation to `start_personaplex.py` |

---

## 5. Key Rules Established

1. **Never hardcode absolute paths** in startup scripts — always use `os.path.dirname(os.path.abspath(__file__))` as `SCRIPT_DIR`
2. **Validate all dependencies before use** — check existence of directories and files before adding to `sys.path` or passing to server
3. **Fail fast with actionable messages** — each validation error prints the exact command needed to fix it
4. **Both startup scripts must be consistent** — same validation logic, same error message format
5. **Never commit** `personaplex-repo/` or `models/` directories — they are gitignored
6. **Never hardcode secrets** — use `os.environ.get()` with no default for passwords/API keys

---

## Related Agents

- `voice-engineer` — PersonaPlex startup and GPU service management
- `myca-voice` — MYCA voice consciousness and bridge architecture
- `process-manager` — GPU cleanup, port conflict resolution
- `bug-fixer` — Runtime error investigation
- `code-auditor` — Finding hardcoded paths, secrets, missing validations
