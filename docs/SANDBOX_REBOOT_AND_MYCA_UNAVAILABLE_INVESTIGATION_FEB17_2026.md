# Sandbox Reboot and MYCA "Connection Unavailable" – Investigation and Fix (Feb 17, 2026)

**Purpose:** Why Sandbox was rebooting, why MYCA showed "connection to my main intelligence is currently unavailable," and what was fixed.

---

## 1. Sandbox VM rebooting

### What happened
- Sandbox (192.168.0.187) was rebooted **once** to clear a **zombie Docker daemon** (`dockerd` PID 1328) that blocked normal Docker operations after failed/aborted website builds.
- See `docs/DEPLOYMENT_STATUS_AND_FIXES_FEB24_2026.md` and `docs/SANDBOX_WEBSITE_RESTART_RESULT_FEB24_2026.md`.

### If Sandbox keeps rebooting
- **Proxmox:** Check VM logs and host for OOM, watchdog, or automatic restart policies.
- **Docker:** Avoid long `docker build` runs that can OOM or hang; use `nohup` builds or build elsewhere and pull the image.
- **Network/storage:** Ensure NAS mount and disk are healthy so the container can start cleanly.

### Current status (as of this doc)
- **MAS (188:8001):** HTTP 200 on `/health`.
- **Sandbox (187:3000):** HTTP 200; website container up.
- No indication of ongoing reboot loops; the earlier reboot was a one-time recovery step.

---

## 2. MYCA chat: "Connection to my main intelligence is currently unavailable"

### Cause
- The **website** chat calls `/api/mas/voice/orchestrator`, which first calls **MAS** `http://192.168.0.188:8001/api/myca/chat` (consciousness API).
- When MAS is down, unreachable, or times out (orchestrator uses a 4s timeout), the orchestrator falls back to LLMs (Claude, GPT, etc.). If **all** providers fail (or an LLM returns an error-style message), the user could see:
  - A generic fallback from the orchestrator, or
  - An LLM-generated phrase like: *"I apologize, but my connection to my main intelligence is currently unavailable. Please try again in a moment."*

So the message appears when:
1. MAS consciousness API is unreachable (e.g. MAS down, network, or timeout), and/or  
2. All other backends (Claude, GPT, etc.) fail or return an "unavailable" style reply.

### Fix applied (Feb 17, 2026)

**Website – `app/api/mas/voice/orchestrator/route.ts`:**

1. **Single fallback message**  
   When **all** providers fail, the orchestrator now returns one clear, actionable message instead of a generic "AI backends" line:
   - *"I'm MYCA. My connection to the main system (MAS) is temporarily unavailable. Please try again in a moment. If this persists, check that MAS is running at 192.168.0.188:8001 and that API keys are set."*

2. **Normalize "unavailable" responses**  
   Any response (from MAS or an LLM) that looks like "connection to main intelligence unavailable" or "try again in a moment" is normalized to the same message above, so users always see the same, clear text instead of varying LLM wording.

- New constant: `MYCA_UNAVAILABLE_MESSAGE`
- New helper: `normalizeMycaUnavailableMessage(text)` – detects phrases like `main intelligence`, `connection.*unavailable`, `try again in a moment` and returns `MYCA_UNAVAILABLE_MESSAGE`.

### What you should do if it happens again
1. **Check MAS:** `curl http://192.168.0.188:8001/health` (or from the website host: ensure `MAS_API_URL` is `http://192.168.0.188:8001` and that 188 is reachable).
2. **Check Sandbox:** Ensure the website container has `MAS_API_URL=http://192.168.0.188:8001` (see `docs/DEPLOYMENT_STATUS_AND_FIXES_FEB24_2026.md` for the run command).
3. **Check API keys:** If MAS is up but consciousness/LLM path fails, verify ANTHROPIC_API_KEY (and other LLM keys) where the orchestrator runs (e.g. website server env).

---

## 3. Summary

| Issue | Cause | Fix |
|-------|--------|-----|
| Sandbox rebooting | One-time zombie `dockerd`; reboot cleared it | If it recurs: check Proxmox, OOM, Docker builds; avoid blocking builds |
| MYCA "main intelligence unavailable" | MAS down/unreachable or all backends failing; sometimes LLM-generated wording | One consistent fallback message + normalization of "unavailable" responses in the orchestrator |

After deploying the website change (orchestrator normalization and fallback), redeploy the site and purge Cloudflare cache so the updated message is served.
