# Status and Next Steps – Feb 9, 2026

Single reference for: (1) memory/LFS crash and git issues, (2) docs created today, (3) MYCA coding system plan status, (4) what to do to test and get Claude Code working on VMs 187 and 188.

---

## 1. Memory Crash / Git LFS Issues – Status

**Docs:** `docs/PERSONAPLEX_LFS_INCIDENT_AND_PREVENTION_FEB06_2026.md`, `docs/DATA_LOSS_AND_DRIVE_FULL_RECOVERY_FEB06_2026.md`

| Item | Status |
|------|--------|
| **Root cause** | Git LFS tracked PersonaPlex model files (~30 GB). Cursor’s background git operations triggered `git-lfs smudge`; each failed download left 7–15 GB temp files in `.git/lfs/tmp/`. Over time, 1,572 failures → **1.74 TB** garbage → 8 TB drive full → Cursor crash and loss of chat history. |
| **Damage** | 1.74 TB in `.git/lfs/tmp/`; drive at 0.2 GB free; Cursor chat history lost (local-only, no recovery). |
| **Cleanup** | ~1,792 GB freed (LFS tmp + objects pruned). |
| **Prevention** | LFS auto-download disabled in `.git/config` (`filter.lfs.smudge = --skip`, `lfs.fetchexclude = *`). Script `scripts/prevent-lfs-bloat.ps1` cleans LFS temp and can re-apply config; can be scheduled hourly. |
| **Chat recovery** | Old chats unrecoverable from Cursor; shadow copies might hold an older `state.vscdb` (see DATA_LOSS doc). |
| **Current state** | **Resolved.** Prevention in place; run `prevent-lfs-bloat.ps1` periodically or on a schedule. Do not re-enable LFS smudge in this repo without a controlled process. |

---

## 2. Docs Created Today (Feb 9, 2026)

| Doc | Purpose |
|-----|--------|
| `docs/MYCA_CODING_SYSTEM_FEB09_2026.md` | MYCA autonomous coding system: architecture, CodingAgent, coding API, CLAUDE.md, subagents, safety, VM setup. |
| `docs/MINDEX_VM_189_AVX_BUN_ASSESSMENT_FEB09_2026.md` | Why VM 189 shows “bun has crashed” / AVX segfault (Claude Code/Bun, not MINDEX). 189 = data-only; do not run Claude Code on 189. MINDEX stack (Postgres, Redis, Qdrant) verified healthy. |
| `docs/STATUS_AND_NEXT_STEPS_FEB09_2026.md` | This file: memory status, today’s docs, plan status, next steps for Claude Code on 187/188. |
| `scripts/run_sandbox_pull_and_mas_deploy.py` | One script (with `ANTHROPIC_API_KEY` in env): pull on 187, set API key, optional test; then pull + rebuild + restart MAS on 188. |
| `scripts/check_mindex_vm_189.py` | Quick health check for 189: Docker containers and service ports. |

---

## 3. MYCA Coding System Plan – Status

**Plan:** `.cursor/plans/myca_autonomous_coding_system_f76c485f.plan.md`  
**Phases:** All four marked **completed** in the plan.

| Phase | Plan status | What’s done | What’s left |
|-------|-------------|-------------|-------------|
| **1. Claude Code on VM 187** | Completed | CLAUDE.md, `.claude/agents/`, `.claude/settings.json`, `.mcp.json`, hooks in repo; API key set on 187 (via script). | 187 must have **MAS as a git repo** at `/opt/mycosoft/mas` and **Claude Code CLI** installed and in PATH so `claude -p` works. |
| **2. CodingAgent + API** | Completed | CodingAgent (`coding_agent.py`), `invoke_claude_code` (SSH to 187), `coding_api.py` (e.g. `/coding/claude/task`, `/coding/claude/health`), registered in `myca_main.py`. | — |
| **3. Safety + integration** | Completed | Intent classifier coding patterns; safety hooks in repo; plan describes Guardian/CTO/CEO flow. | Optional: harden Guardian/coding risk and audit logging in code. |
| **4. Deploy + test** | Completed | MAS deployed to 188; coding router live at `http://192.168.0.188:8001/coding/...`. | **Full integration test** (voice or API → intent → CodingAgent → SSH 187 → `claude -p` → result) still to be run once 187 is ready. |

So: **code and deployment for the MYCA coding system are in place.** The remaining work is **VM 187 setup** and **running the integration test**.

---

## 4. What We Need to Do: Test and Get Claude Code Working on 187 and 188

### VM 189 (MINDEX)

- **Do not** install or run Claude Code on 189 (AVX/Bun crash; see `MINDEX_VM_189_AVX_BUN_ASSESSMENT_FEB09_2026.md`).
- Use 189 only for Postgres, Redis, Qdrant, and MINDEX API. No action for “Claude Code on 189.”

### VM 187 (Sandbox) – required for MYCA coding

CodingAgent SSHs to **187** and runs `claude -p` in the MAS repo at `/opt/mycosoft/mas`. For that to work:

| # | Task | How to verify |
|---|------|----------------|
| 1 | **MAS as git repo on 187** | On 187: `cd /opt/mycosoft/mas && git status`. If “not a git repository”, clone or copy the repo so it’s a real git clone (e.g. `git clone https://github.com/MycosoftLabs/mycosoft-mas.git /opt/mycosoft/mas` or fix path). |
| 2 | **Claude Code CLI on 187** | You said you installed it. On 187: `claude --version` and `claude -p "What is this project? One sentence." --output-format json` (with `ANTHROPIC_API_KEY` set). |
| 3 | **ANTHROPIC_API_KEY on 187** | Already set in `~/.bashrc` by `run_sandbox_pull_and_mas_deploy.py`. For non-interactive use: `export ANTHROPIC_API_KEY=...` or ensure it’s in the environment when `claude` runs. |
| 4 | **Pull latest on 187** | After the repo is git: `cd /opt/mycosoft/mas && git fetch origin && git reset --hard origin/main` so CLAUDE.md and `.claude/` are current. |

When 1–4 are done, the MYCA coding flow (SSH to 187 → `claude -p`) can run successfully.

### VM 188 (MAS)

- **MAS app and coding API** are already deployed and live (e.g. `GET http://192.168.0.188:8001/coding/claude/health`).
- **Claude Code on 188** is optional (for your own manual use). The **automated** coding system only uses 187 for Claude Code; 188 just runs the API and SSHs to 187.
- If you want Claude Code on 188 for manual use: install and configure it the same way as on 187 (no special plan steps).

### SSH from MAS (188) to 187

- `/coding/claude/health` runs **inside the MAS container on 188** and does `ssh mycosoft@192.168.0.187 "claude --version"`.
- The MAS Docker image now includes **openssh-client** so `ssh` is available in the container.
- For non-interactive SSH (no password prompt), use **key-based auth** as below.

### SSH key setup (MAS container → 187)

1. **Generate a dedicated key pair** (on your PC or on 188):  
   `ssh-keygen -t ed25519 -f mas_to_sandbox -N ""`
2. **Install the public key on 187:**  
   Append contents of `mas_to_sandbox.pub` to `~mycosoft/.ssh/authorized_keys` on 187. Ensure `~/.ssh` is mode 700 and `authorized_keys` is 600.
3. **Copy the private key to 188** (e.g. to `/home/mycosoft/.ssh/mas_to_sandbox`) and chmod 600.
4. **Run the MAS container with the key mounted:**  
   The deploy script (`scripts/run_sandbox_pull_and_mas_deploy.py`) and `_rebuild_mas_container.py` automatically add `-e MAS_SSH_KEY_PATH=/run/secrets/mas_ssh_key` and `-v /home/mycosoft/.ssh/mas_to_sandbox:/run/secrets/mas_ssh_key:ro` when that key file exists on 188. Rebuild the image and restart the container so the container can SSH to 187 without a password.

### Integration test (once 187 is ready)

1. **From 187:**  
   `cd /opt/mycosoft/mas && export ANTHROPIC_API_KEY=... && claude -p "What is this project? One sentence." --output-format json`  
   → Should return JSON (no “command not found”, no LFS errors).

2. **From browser or curl:**  
   `POST http://192.168.0.188:8001/coding/claude/task` with body e.g.  
   `{"description": "List the first 5 lines of CLAUDE.md", "target_repo": "mas"}`  
   → Should trigger CodingAgent → SSH to 187 → `claude -p` → result (if SSH from 188 to 187 is set up).

3. **Voice (optional):**  
   “MYCA, create a new agent that prints hello” (or similar) → intent → orchestrator → CodingAgent → 187 → Claude Code. Depends on voice pipeline and intent routing already in place.

---

## 5. Short Checklist

- [ ] **187:** `/opt/mycosoft/mas` is a git repo (clone or fix; deploy script can clone if dir is empty).
- [ ] **187:** `git pull` (or fetch/reset) so CLAUDE.md and `.claude/` are up to date.
- [ ] **187:** `claude --version` and `claude -p "What is this project?"` work (with `ANTHROPIC_API_KEY` set).
- [ ] **188:** MAS image includes **openssh-client** (done in Dockerfile). Deploy and coding API live.
- [ ] **188 → 187 SSH key:** Generate key pair, add pubkey to 187 `authorized_keys`, place private key at `/home/mycosoft/.ssh/mas_to_sandbox` on 188; deploy script / _rebuild_mas_container add volume and `MAS_SSH_KEY_PATH` when key exists.
- [ ] **189:** Do not run Claude Code; use only for MINDEX (done).
- [ ] **Integration test:** Run one coding task via API (and optionally voice) after 187 and SSH key are ready.

---

## 6. Related Docs

| Topic | Doc |
|-------|-----|
| Memory / LFS crash and prevention | `docs/PERSONAPLEX_LFS_INCIDENT_AND_PREVENTION_FEB06_2026.md`, `docs/DATA_LOSS_AND_DRIVE_FULL_RECOVERY_FEB06_2026.md` |
| MYCA coding system | `docs/MYCA_CODING_SYSTEM_FEB09_2026.md` |
| VM 189 AVX/Bun | `docs/MINDEX_VM_189_AVX_BUN_ASSESSMENT_FEB09_2026.md` |
| VM layout and dev | `docs/VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md` |
| MINDEX VM 189 | `docs/MINDEX_VM_DEPLOYMENT_STATUS_FEB04_2026.md` |
| Master doc index | `docs/MASTER_DOCUMENT_INDEX.md` |
