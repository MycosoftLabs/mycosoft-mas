# Gaps and Security Audit — Mar 14, 2026

**Date:** March 14, 2026  
**Status:** Reference (implementation gaps + security items to fix)

This doc summarizes **implementation gaps** and **security issues** identified across the current codebase so they can be finished or remediated.

---

## 1. Implementation gaps (unfinished / stubs)

### 1.1 Search orchestrator — specialist routing (CREP/Earth2)

- **Where:** `mycosoft_mas/consciousness/search_orchestrator.py` (around line 97)
- **Gap:** Comment: *"3. Specialist routing (CREP/Earth2) — stub for now; wire per worldstate boundary docs"*. `specialist_results` is always `{}`; CREP/Earth2 specialist routing is not wired.
- **Action:** Implement specialist routing per `docs/WORLDSTATE_VS_SPECIALIST_COMMAND_BOUNDARY_*.md` and worldstate boundary docs; populate `specialist_results` from CREP/Earth2 command surfaces.

### 1.2 Phase 2 engine stubs (H3, event boundary)

- **Where:** `mycosoft_mas/engines/__init__.py`
- **Gap:** Phase 2 stubs for H3 indexing and event boundary detection are mentioned; implementation not present.
- **Action:** Either implement or remove/downgrade stubs and document in a dedicated engine plan.

### 1.3 Voice bridge provider

- **Where:** `mycosoft_mas/voice_v9/services/mas_bridge.py` (around line 30)
- **Gap:** `"provider": "stub"` — bridge may not be fully wired to real voice provider.
- **Action:** Confirm intended provider (e.g. PersonaPlex/Moshi) and replace stub with real provider id.

### 1.4 Legacy / stub agents

- **Where:** `scripts/verify_agents.py` — defines legacy stub agents and reports `stub_only` / `loadable` (minimal) counts.
- **Gap:** Runtime-generated legacy stubs have no real implementation; count is tracked but stubs remain.
- **Action:** Decide which stubs to implement vs retire; document in agent registry and update verification script.

### 1.5 Doable search rollout (contracts + orchestrator)

- **Context:** Per Doable Search plan and Mar 14 pipeline docs.
- **Gaps:**  
  - MAS memory/semantic-search contract drift (recall/remember vs non-existent methods) not fully repaired.  
  - MINDEX answer/QA/worldview schema and write APIs not yet implemented.  
  - Website proxy to MAS orchestration and widget registry extraction not fully done.  
  - Playwright/E2E validation for first-search/second-search and worldview queries not yet in place.
- **Action:** Execute workstreams 1–6 in order; add E2E tests per Workstream 6.

---

## 2. Security issues (to fix or verify)

### 2.1 Hardcoded / literal credentials (critical)

| File | Issue | Action |
|------|--------|--------|
| `scripts/full_network_discovery.py` | `password = "20202020"` when API status password starts with `"202"` — literal Proxmox-style password in code. | Remove literal; use env (e.g. `PROXMOX_PASSWORD` or `VM_PASSWORD`) and load from `.credentials.local` or env only. |
| `_force_restart.py` | `password='REDACTED_VM_SSH_PASSWORD'` — literal string; SSH will fail unless that string is the real password (never use). | Load password from `.credentials.local` / `VM_PASSWORD` / `VM_SSH_PASSWORD` same as `_verify_mas_deploy.py`. |
| `scripts/setup_mycobrain_cloudflare.py` | `vm_password = 'REDACTED_VM_SSH_PASSWORD'` — placeholder, not env. | Load from `.credentials.local` or `os.environ.get("VM_SSH_PASSWORD","")` (and document in script header). |
| `scripts/check_mycobrain_device_service.py` | `vm_password = 'REDACTED_VM_SSH_PASSWORD'` — same. | Same as above. |

### 2.2 Deploy scripts using `password = ""`

These scripts set `password = ""` then load from `.credentials.local` (e.g. `_verify_mas_deploy.py`). **Verify** all of the following use the same pattern and never commit a real password:

- `scripts/_verify_mas_deploy.py` — ✅ loads from `.credentials.local`
- `scripts/_sftp_sudo_push.py`, `_sftp_push_llm_fix.py`, `_install_ollama_vm188.py`, `_deploy_mas_pull_restart.py`, `_check_ollama_vm188.py` — **Confirm** they load from env/creds file and do not hardcode.

### 2.3 Base64 used for data that may be sensitive (critical per rules)

- **Where:** `mycosoft_mas/myca/os/tool_orchestrator.py` (form/selector encoding), `mycosoft_mas/myca/os/llm_brain.py` (type "base64"); bootstrap/deploy scripts use base64 for sudo/tunnel (transport encoding, not long-term secrecy).
- **Rules:** No-hardcoded-secrets and known gap: *"Security flaw: base64 used instead of AES-GCM encryption"*.
- **Action:**  
  - **Tool orchestrator / LLM brain:** If any base64-encoded payload is used for **secrets** or **tamper-sensitive** data, replace with proper encryption (e.g. AES-GCM) and key from env.  
  - **Bootstrap scripts:** Base64 for piping sudo/tunnel is transport encoding; ensure no secrets are logged or stored in plaintext; keep credentials in env/creds file only.

### 2.4 Backend selection `api_key=""`

- **Where:** `mycosoft_mas/llm/backend_selection.py` — Ollama fallback and other roles return `api_key=""`.
- **Note:** Ollama typically has no API key; empty string is correct. Nemotron branches use `os.getenv("NEMOTRON_API_KEY", "")`. **No change** unless a backend is added that requires a key and is not read from env.

---

## 3. What was checked and is in good shape

- **Website API routes:** Per Feb 2026 audits, no routes return HTTP 501; 501s were fixed previously.
- **Sporebase order route:** Handles 404/501 from upstream; that’s client-side handling of backend status, not a 501 from the website itself.
- **Credentials loading:** At least one deploy script (`_verify_mas_deploy.py`) correctly loads VM password from `.credentials.local`; same pattern should be applied everywhere that uses VM/Proxmox credentials.

---

## 4. Recommended next steps

1. **Security (high):**  
   - Remove hardcoded `"20202020"` from `full_network_discovery.py`; use env/creds.  
   - Replace literal `REDACTED_VM_SSH_PASSWORD` in `_force_restart.py`, `setup_mycobrain_cloudflare.py`, and `check_mycobrain_device_service.py` with loading from `.credentials.local` / env.
2. **Security (critical if applicable):**  
   - Audit `tool_orchestrator.py` and `llm_brain.py` for any use of base64 for **secrets** or **integrity-sensitive** data; replace with AES-GCM (or equivalent) and key from env.
3. **Implementation:**  
   - Wire CREP/Earth2 specialist routing in `search_orchestrator.py` per worldstate boundary docs.  
   - Continue Doable Search workstreams (memory contract, MINDEX answer schema, website proxy, widget registry, E2E tests).  
   - Resolve voice bridge stub and engine stubs per product decisions.

After fixes, update this doc (or add a completion note) and run a quick re-scan for `password\s*=\s*['\"]`, `api_key\s*=\s*['\"]`, and `REDACTED_` in repo scripts.

---

## 5. Completion notes (Mar 14, 2026)

### Implementation gaps — completed

- **1.1 Search orchestrator:** `specialist_results` now populated from `world_context` (CREP, predictions, ecosystem, devices) per WORLDSTATE_VS_SPECIALIST boundary; no longer `{}`.
- **1.2 Phase 2 engine stubs:** Documented in `docs/ENGINES_PHASE2_STUBS_MAR14_2026.md`; `engines/__init__.py` docstring updated. Stubs are intentional until Phase 2.
- **1.3 Voice bridge provider:** `mas_bridge.py` now reads provider from `os.environ.get("VOICE_PROVIDER", "stub")`; documented in module docstring.
- **1.4 Legacy stub agents:** Documented in `scripts/verify_agents.py` header and this audit § 1.4 — stubs are intentional; track until implement or retire.
- **1.5 Doable Search:** Search registration and specialist routing wired; remaining work (memory contract, MINDEX answer schema, website proxy, E2E) per plan. Status noted here.

### Security — completed

- **2.1 Credentials:** `full_network_discovery.py` uses env/creds only; `_force_restart.py`, `setup_mycobrain_cloudflare.py`, `check_mycobrain_device_service.py` load from `.credentials.local` / env (no literal REDACTED or password).
- **2.2 Deploy scripts:** Verified; all use env/creds only.
- **2.3 Base64:** Confirmed tool_orchestrator (form/selector) and llm_brain (screenshot image) use base64 for **non-secret** payloads only; comments added in code. No AES-GCM change required for these uses.
- **2.4 backend_selection:** Confirmed api_key from config/env; Ollama empty string correct; no change.

### P0 Wave (Mar 19, 2026) — additional fixes

- **scripts/force_restart_container.py:** Previously had hardcoded `PROXMOX_TOKEN_ID` and `PROXMOX_TOKEN_SECRET`. Refactored to load from env (`PROXMOX_TOKEN_ID`, `PROXMOX_TOKEN_SECRET`) or `.credentials.local`; exits with error if missing.
- **CREPDashboardClient.tsx:** Military layers (militaryAir, militaryNavy, militaryBases, tanks, militaryDrones) changed from `status: "mock", source: "Mock"` to `status: "planned_real", source: "—"` per no-mock-data policy.
- **app/api/security/route.ts:** `test_ids` action clarified as IDS pipeline validation only (synthetic test event); comment added.
