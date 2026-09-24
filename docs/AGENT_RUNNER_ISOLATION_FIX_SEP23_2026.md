# Agent Runner Isolation Fix — Sep 23, 2026

**Date:** 2026-09-23 (verified Sep 24 UTC on MAS VM)  
**Status:** Complete  
**Scope:** MAS `192.168.0.188:8001` — 24/7 AgentRunner without wedging the API

## Honest agent counts

| Layer | Count | Notes |
|-------|------:|-------|
| Voice/registry catalog on 188 | **~47** registered definitions | Not “thousands” |
| Live runner loops (before fix) | **0** | `MAS_SKIP_BACKGROUND_STARTUP=1` kept API alive |
| Critical always-on watchers | **5** | guardian, immune_system, workspace_security, nlm-agent, security-monitor |
| Full native core load | **Do not enable** | Instantiating all active agents + sync I/O wedges `:8001` |

## Root cause

1. **Native agent cycles ran on the uvicorn event loop** with no hard timeout.  
   `WorkspaceSecurityAgent` used sync `subprocess.check_output` / `journalctl`; other agents called `record_task_completion` → Postgres via memory coordinator. Any stall stopped accepting connections → **Recv-Q buildup** and `/health` timeouts.
2. **`AgentCycleRunner.stop()` did not cancel tasks**, so restart races could leave duplicate cycle loops.
3. **Critical “light” loader still instantiated native classes** (`_load_one`) before discarding delegates — ImmuneSystem ctor creates `asyncio.Queue`s and imports scanners (unsafe from worker threads / wasteful on load).
4. **Episodic writes had no timeout**, so slow MINDEX/Postgres blocked cycles indefinitely.
5. Full background startup also started collectors + full core runner — separate wedge path (still gated by `MAS_SKIP_BACKGROUND_STARTUP=1`).

## Fix

| File | Change |
|------|--------|
| `mycosoft_mas/core/agent_runner.py` | Per-cycle `wait_for` timeout; cancelable tasks + generation counter; bounded cycle history; local storage by default; yield between agents |
| `mycosoft_mas/core/runner_agent_loader.py` | Native cycle timeout; auto-downgrade to light presence; core load defaults to light (`AGENT_RUNNER_NATIVE_CORE=0`) |
| `mycosoft_mas/core/critical_runner_loader.py` | **Never instantiate** agent classes — definition-only light presence; 60s interval |
| `mycosoft_mas/core/agent_supervisor.py` | Restarts use light presence unless native core enabled |
| `mycosoft_mas/agents/memory_mixin.py` | `record_task_completion` timeout + optional skip; `success` default for legacy callers |
| `mycosoft_mas/agents/guardian_agent.py` | Correct `record_task_completion(..., success=True)` |
| `mycosoft_mas/agents/workspace_security_agent.py` | Subprocess/auth log via `asyncio.to_thread` |

## Ops

- Keep `MAS_SKIP_BACKGROUND_STARTUP=1` until collectors are separately isolated.
- Enable watchers: `POST http://192.168.0.188:8001/runner/load-critical`
- Do **not** set `AGENT_RUNNER_NATIVE_CORE=1` on 188 until native cycles are proven under load.
- Wazuh/Shinobi remain OFF; do not touch 187 nginx.

## Verify

```text
GET  /health              → 200 (api ok; may be degraded if collectors skipped)
GET  /runner/status       → running=true, agents=5
POST /runner/load-critical → loaded 5 light_presence agents
ss -ltn sport = :8001     → Recv-Q stays low while cycling
```

## Follow-ups

- Optional: real (non-light) workspace SSH checks on a **dedicated worker process**, not uvicorn.
- Optional: isolate CREP health probe from hot `/health` path (191 polls frequently).

## Follow-up root cause (post-deploy)

data/agent_work/cycles had grown to a multi-megabyte directory (hundreds of thousands of JSON files). Each _save_cycle into that directory stalled I/O and wedged uvicorn even for light presence cycles. Persist-to-disk is now **off by default** (AGENT_RUNNER_PERSIST_CYCLES=0).


## Verification (188, Sep 24 2026 UTC)

After quieter critical boot (no supervisor, no startup notify, no disk persist, no heartbeat imports):

- `POST /runner/load-critical` ? 200 in ~1s, `running=true`, **5** light-presence agents
- `/live` + `/health` stayed **200** for >90s while cycles advanced (5 ? 20+)
- `ss` Recv-Q on `:8001` stayed **0** (no wedge)
- Honest counts: **~47** registry agents registered; **5** critical watchers live; **not** thousands

Keep `MAS_SKIP_BACKGROUND_STARTUP=1`. Do not enable `AGENT_RUNNER_NATIVE_CORE` or `AGENT_CRITICAL_START_SUPERVISOR` on 188 until separately hardened.
