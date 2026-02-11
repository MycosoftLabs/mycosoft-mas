# Gemini API Key and VM Status Fixes – Feb 11, 2026

## Summary

- **Google key**: Correct key ends in `LoY` (not `LoG`). Set in local `.env`; on MAS VM set `GEMINI_API_KEY` in env or in the env file used by the orchestrator.
- **Gemini model**: Code now uses `gemini-2.0-flash` (v1beta). `gemini-1.5-flash` returns 404 on the paid account.
- **Intent engine**: JSON parsing fixed for nested braces and markdown code blocks so LLM intent classification works (0.95 confidence).
- **MINDEXSensor**: Import fixed from `consciousness.sensors` (not `world_model`).
- **MAS VM**: Reachable; `http://192.168.0.188:8001/health` returns 200. SSH from this machine requires key or password.

---

## 1. Google API Key

- **Correct key** (paid, unused): ends with `LoY`.
- **Wrong key** (was in env): ended with `LoG` → 400 "API key not valid".
- **Where to set**:
  - **Local**: `.env` in repo root (gitignored) – already set with correct key.
  - **MAS VM (188)**: Set `GEMINI_API_KEY` in the environment used by the orchestrator (systemd unit, Docker env, or `.env` on the VM). No keys are committed to git.

---

## 2. Code Changes (Committed and Pushed)

| File | Change |
|------|--------|
| `mycosoft_mas/consciousness/intent_engine.py` | Use `gemini-2.0-flash`; robust JSON extraction (nested `{}`, ```json blocks). |
| `mycosoft_mas/consciousness/unified_router.py` | Import `MINDEXSensor` from `mycosoft_mas.consciousness.sensors`. |

Tests: 17/18 pass (94.4%); LLM intent classification and routing work with real Gemini responses.

---

## 3. MAS VM Status

- **Ping**: `192.168.0.188` responds.
- **API**: `http://192.168.0.188:8001/health` returns **200** and `"api":"ok"`.
- **SSH from this PC**: `Permission denied (publickey,password)` with `BatchMode=yes` (no key/password in this environment).

To deploy latest code on the VM:

1. **Option A – Password**  
   Set VM password and run:
   ```powershell
   $env:VM_PASSWORD = "your-vm-password"
   python scripts/quick_deploy_mas.py
   ```
   Script pulls from GitHub and restarts `mas-orchestrator` (or Docker container).

2. **Option B – SSH key**  
   Configure SSH key for `mycosoft@192.168.0.188`, then:
   ```bash
   ssh mycosoft@192.168.0.188 "cd /home/mycosoft/mycosoft/mas && git pull origin main && sudo systemctl restart mas-orchestrator"
   ```

After deploy, set `GEMINI_API_KEY` on the VM so the orchestrator uses the correct key.

---

## 4. Verification

- **Local**: `python scripts/test_orchestrator_integration.py` → 17/18 pass, Gemini 200 OK.
- **MAS API**: `curl http://192.168.0.188:8001/health` → 200.
- **MYCA chat**: Use website or `/api/myca/route` with message; responses should be from Gemini when key is set on the server.

---

## 5. References

- Master doc index: `docs/MASTER_DOCUMENT_INDEX.md`
- Process registry: `.cursor/rules/python-process-registry.mdc`
- Deploy pipeline: `docs/DEV_TO_SANDBOX_PIPELINE_FEB06_2026.md`
