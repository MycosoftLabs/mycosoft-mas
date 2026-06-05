# MAS NLM Library — MINDEX Token Fix on VM 188 (June 5, 2026)

**Date:** June 5, 2026  
**Status:** Complete  
**Related:** `docs/MAS_NLM_MINDEX_LIBRARY_INTEGRATION_COMPLETE_JUN04_2026.md`, `docs/codex-handoffs/MAS_NLM_LIBRARY_CODEX_HANDOFF_JUN04_2026.md`

---

## Problem

`GET http://192.168.0.188:8001/api/mas/mindex/library/health` returned **401** because the MAS orchestrator on VM **188** did not present a valid `MINDEX_INTERNAL_TOKEN` to MINDEX **189**.

- Code at **`acab461590d26a96b830e503dc5394a1950553b0`** was already deployed.
- **`myca-orchestrator-new`** Docker container existed in **Created** state (not serving traffic).
- Production traffic on **8001** was **`mas-orchestrator`** **systemd** + **uvicorn** from `/home/mycosoft/mycosoft/mas`, loading `/home/mycosoft/mycosoft/mas/.env`.

---

## Root cause

`/home/mycosoft/mycosoft/mas/.env` on **188** had `MINDEX_INTERNAL_TOKEN` missing or out of sync with the first value in **`MINDEX_INTERNAL_TOKENS`** on the **mindex-api** container on **189**.

The library proxy (`mindex_library_proxy_api.py`) forwards `X-Internal-Token` using `MINDEX_INTERNAL_TOKEN` from the orchestrator process environment.

---

## Fix applied (2026-06-05)

1. Read first internal token from **189** `mindex-api` container env (`MINDEX_INTERNAL_TOKENS` comma-separated list).
2. Confirmed token matched dev `.credentials.local` entry `MINDEX_INTERNAL_TOKEN` (length 64; not committed).
3. Updated **188** `/home/mycosoft/mycosoft/mas/.env`:
   - `MINDEX_API_URL=http://192.168.0.189:8000`
   - `MINDEX_INTERNAL_TOKEN=<synced from 189>`
   - `MAS_API_URL=http://192.168.0.188:8001`
   - `NLM_INFERENCE_URL=http://192.168.0.188:8001`
4. Restarted **`mas-orchestrator`** via `sudo systemctl restart mas-orchestrator`.
5. Did **not** start `myca-orchestrator-new` (would conflict on port **8001**). Left container as-is.

**Automation:** `scripts/ensure_mas_mindex_env_188.py` — idempotent sync + restart + verify (reads `.credentials.local`, never logs full tokens).

---

## Verification (all passed)

| Endpoint | Expected | Result |
|----------|----------|--------|
| `GET :8001/health` | `git_sha` starts with `acab461` | OK |
| `GET :8001/api/mas/mindex/library/health` + `X-Internal-Token` | 200 | OK |
| `GET :8001/api/mas/mindex/library/blobs?limit=3` | 200, `total` > 0 | OK (2180 blobs) |
| `GET :8001/api/mas/mindex/library/sine/human-tags?limit=5` | 200 | OK |
| `GET :189:8000/api/mindex/health` + token | 200, `db: ok` | OK |

### Commands (placeholders — no secrets in repo)

```bash
export TOK="<MINDEX_INTERNAL_TOKEN>"

curl -sf http://192.168.0.188:8001/health | jq -r .git_sha

curl -sf http://192.168.0.188:8001/api/mas/mindex/library/health \
  -H "X-Internal-Token: $TOK"

curl -sf "http://192.168.0.188:8001/api/mas/mindex/library/blobs?limit=3" \
  -H "X-Internal-Token: $TOK" | jq '.total, (.items|length)'

curl -sf "http://192.168.0.188:8001/api/mas/mindex/library/sine/human-tags?limit=5" \
  -H "X-Internal-Token: $TOK"

curl -sf http://192.168.0.189:8000/api/mindex/health \
  -H "X-Internal-Token: $TOK"
```

Re-run fix/verify from dev PC:

```powershell
cd MAS\mycosoft-mas
python scripts/ensure_mas_mindex_env_188.py
```

---

## Deployment notes

| Item | Value |
|------|--------|
| **MAS runtime** | systemd `mas-orchestrator` (not Docker on 8001) |
| **Env file** | `/home/mycosoft/mycosoft/mas/.env` |
| **Git on 188** | `acab4615` @ `feature/com4-hyphae-ota-local-may29-2026` |
| **MINDEX** | `mindex-api` on **189:8000** |

If switching to Docker `myca-orchestrator-new`, pass the same env vars with `-e` and stop systemd first to avoid port **8001** conflicts.

---

## Lessons learned

- **188:8001** may be systemd even when a MAS Docker image exists in **Created** state — always check `ss -tlnp` and `systemctl is-active mas-orchestrator`.
- Token sync must target the **active** process env (`.env` for systemd, not only an unused container).
- Use `scripts/ensure_mas_mindex_env_188.py` after MINDEX token rotation on **189**.
