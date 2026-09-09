# Cursor ITDX26 Codex v1.3 connect — 09 September 2026

**Date:** 09 September 2026  
**Status:** Local connect + local demo open. Not shipped. PR #299 remains draft.  
**Authority:** `C:\Users\Owner1\Downloads\Mycosoft_ITDX26_v1.3.0_Complete_Demo\Mycosoft_ITDX26_v1.3.0\handoff` (all 18 files). Older 08 Sep pack is superseded for connect.  
**Related:** `docs/CURSOR_ITDX26_INTEGRATION_SEP08_2026.md`; website worktree `D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website-itdx-codex-v13` @ `58d58417`; GitHub PR https://github.com/MycosoftLabs/website/pull/299

## What was connected (Codex producer + Cursor Earth chrome)

| Surface | Wiring |
|---|---|
| Dedicated app | `/fusarium/itdx` (Codex `ITDXApplication` + authenticated `/api/fusarium/itdx/bridge/*`) |
| Earth left panel | Fusarium Intel Feed **MYCA LIVE \| ITDX** split; NatureOS Earth keeps full-height MYCA LIVE |
| Shared replay | `useReplay()` / `replay` + existing `ITDXReplayLayer` (`itdx-fictional-replay*` only) |
| Shared session | `useITDXContext` / `registerITDXAdapter`; one `ITDXEvidenceConsumer` for catalog consumers |
| Backend | `itdx/app/service.py` on `127.0.0.1:8765`, Bearer `ITDX_BACKEND_TOKEN` (server-only, gitignored) |

Overlay flags stay `synthetic: true`, `live: false`, `replay: true`, `version: "1.3"`. Real CREP aircraft / vessels / sats are unchanged.

## Local verify (this machine)

| Check | Result |
|---|---|
| Unauthenticated `8765/api/health` | HTTP 403 (expected) |
| Authenticated health | HTTP 200, `version: 1.3.0`, `loopback_only: true`, `transport: authenticated-service` |
| Website `http://127.0.0.1:3010` | HTTP 200 (`npm run dev:next-only` Hidden, this worktree) |
| `/fusarium/itdx` | HTTP 200 |
| `/fusarium/earth-simulator` | HTTP 200 |
| `node --test` gateway / map / session / evidence consumers | Pass |
| Sandbox `192.168.0.187:3000` | HTTP 200 — **left running; no rebuild, no cutover** |
| Exercise pack | Copied locally only (`itdx/app/exercise_packs/itdx-training-documents`, gitignored, 97 files) |
| Secrets | `.env.local` gitignored; password and token never printed |

INT-01–26 / OBJ-01–06 were **not** prefilled PASS. Browser MFA / signed-export walkthrough still requires the owner session.

## Local demo URLs opened (default browser)

1. `http://localhost:3010/fusarium/login` — owner `morgan@mycosoft.org` (password from gitignored store; not printed)
2. `http://localhost:3010/fusarium/itdx` — dedicated Fusarium ITDX app / Algorithm lab workbench (iframe after CONNECTED)
3. `http://localhost:3010/fusarium/earth-simulator` — Earth Simulator; click Intel Feed **ITDX**
4. `http://localhost:3010/fusarium` — Fusarium catalog (shared dock / consumers)

There is **no separate public Algorithm lab URL**. Handoff `:8765` is the authenticated Python backend on loopback only and was **not** opened as a demo.

**Do not** treat `sandbox.mycosoft.com` or `mycosoft.com` as this demo.

## Honesty / remaining

- PR #299 is still **OPEN, DRAFT**. No merge, no Sandbox rebuild, no Cloudflare purge.
- Dirty trees `WEBSITE/website` and `website-itdx` were not reset.
- FOUO / exercise PDFs were not git-added.
- Production ITDX backend on 187 is still pending Morgan ship.
- Pursuing CMMC L2 — not claiming compliant. RJ Ricasata is CFO.
