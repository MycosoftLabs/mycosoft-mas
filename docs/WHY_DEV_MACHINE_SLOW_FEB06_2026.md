# Why the Dev Machine Got Slow (and How to Fix It) – February 6, 2026

## What changed “today” – root cause

Docker/WSL had been running for months without issue. The slowness wasn’t caused by Docker alone. It was caused by **several things running at once and never being shut down**:

1. **Leftover GPU services (Python) from `npm run dev`**
2. **WSL/vmmem** using a lot of RAM
3. **Cursor** (and possibly many Node/Python processes) adding load on top

So the machine didn’t “suddenly” get slow; it crossed a **tipping point** when total load (CPU + RAM) got too high.

---

## 1. GPU services that never exit

When you run **`npm run dev`** on the website:

- The script starts **“GPU Services”** in a **separate window** (PersonaPlex/Moshi, Bridge, Earth2, Gateway).
- That window runs **Python processes** that are **detached** from the terminal. When you close the terminal or Cursor, **they keep running**.
- The dev server even says: *“To stop them: Close the GPU Services window or kill Python processes.”*

So every time you ran `npm run dev` and then closed the terminal **without** closing the “GPU Services” window:

- **local_gpu_services.py** kept running
- **start_personaplex.py** (Moshi, ~23GB VRAM + CPU) kept running
- **personaplex_bridge_nvidia.py** kept running
- **earth2_api_server.py** (if started) kept running

If you ran dev multiple times over days, or left the PC on with that window open, those processes could run for **days** and use huge CPU time (e.g. 88,000+ CPU seconds in one case). That’s why the machine got slow: **old GPU-related Python processes were still running and never cleaned up.**

---

## 2. WSL/vmmem

- **vmmem** is the WSL2 VM. Docker Desktop often uses WSL2.
- WSL2 can use a **large share of RAM** (e.g. 50% or more) and can grow over time.
- So: **Docker was fine for months**, but together with the **accumulated Python processes** and Cursor/Node, **total memory and CPU use** crossed the limit and the machine started swapping and feeling slow.

So vmmem didn’t “start” today; it was there. What changed is **total load** (Python + Cursor + vmmem + Node, etc.).

---

## 3. Cursor and Node

- **Cursor** runs multiple processes (Electron, Node, extensions).
- **Next.js dev** runs Node. If you had several terminals or old `next dev` instances, that’s more Node.
- More processes = more CPU and RAM contention, especially when Python and vmmem are already heavy.

---

## Summary: why “only today” and “everything slow”

| Factor | Why it matters |
|--------|----------------|
| **GPU Python processes** | Left running for days (PersonaPlex, Bridge, Earth2, local_gpu_services). High CPU and VRAM. |
| **vmmem (WSL)** | Uses a lot of RAM; combined with the above, pushed the system into swapping. |
| **Cursor + Node** | Normal use, but on top of the above made the machine hit its limit. |

So: **Docker alone wasn’t the cause.** The main new factor was **long-lived GPU-related Python processes** that were never closed, plus **vmmem**, and today the combined load made the whole system slow.

---

## What to do from now on

### When you don’t need voice or Earth2

Use **Next.js only** (no GPU services):

```bash
cd website
npm run dev:next-only
```

Or:

```bash
npm run dev:no-gpu
```

That starts only the dev server on port 3010 and **does not** start the “GPU Services” window.

### When you do use GPU (voice / Earth2)

1. Run **`npm run dev`** as usual.
2. When you’re done, **close the “GPU Services” window** (the one that opened when you started dev), **or** run the cleanup script (see below) so those Python processes don’t stay running for days.

### Free memory when things feel slow

1. **Shut down WSL** (reduces vmmem):
   ```powershell
   wsl --shutdown
   ```
   Or: `.\scripts\shutdown-wsl-free-vmmem.ps1`

2. **Kill leftover GPU-related Python processes** (see script below):
   ```powershell
   .\scripts\dev-machine-cleanup.ps1
   ```

3. **Restart Cursor** if it’s still slow after cleaning (reduces Cursor/Node process buildup).

---

## Scripts and docs

| Item | Purpose |
|------|--------|
| `scripts\dev-machine-cleanup.ps1` | Lists heavy processes; optionally kills stale GPU Python and runs `wsl --shutdown`. |
| `scripts\shutdown-wsl-free-vmmem.ps1` | Shuts down WSL to free vmmem memory. |
| `docs\WSL_VMMEM_DISABLE_FEB06_2026.md` | WSL/vmmem explanation and limits. |
| `docs\WHY_DEV_MACHINE_SLOW_FEB06_2026.md` | This document. |

---

## One-line “fix it now”

From the MAS repo:

```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\scripts
.\dev-machine-cleanup.ps1 -KillStaleGPU -ShutdownWSL
```

Then restart Cursor if needed. Use **`npm run dev:next-only`** when you don’t need voice/Earth2 so GPU services don’t pile up again.
