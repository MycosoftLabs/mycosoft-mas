# Why GitHub Push Stopped Working on This Machine — Root Cause

**Date:** February 10, 2026

## Short answer

**It was the LFS config, not “many agents,” not “large files,” and not GitHub being broken.**  
After the Feb 6 PersonaPlex incident, LFS was fully disabled on this PC (`.lfsconfig`: `concurrenttransfers = 0`, `fetchexclude = *`) so Cursor wouldn’t download huge LFS files and fill the drive. **That same setting breaks push.** Git LFS treats `concurrenttransfers = 0` as “do no transfers,” so the push either never completes the LFS side or sends something GitHub’s LFS layer doesn’t accept, and you get **HTTP 500** from GitHub.

So: **turning off LFS to protect the PC is exactly what made GitHub push stop working on this Cursor machine.**

---

## What we ruled out

| Idea | Why it’s not the cause |
|------|------------------------|
| Many agents pushing at once | Only one push was run at a time; no evidence of concurrent pushes from this machine. |
| Large files | Pushing a **single small commit** (no big files) still returned HTTP 500. So size isn’t the driver. |
| GitHub “stopped working” globally | GitHub Status showed Git Operations and API as operational. Other users/orgs weren’t reporting a general push outage. |
| This machine is “blocked” | Same account/repo from another machine might work; the failure is tied to this repo’s LFS config and how this client pushes. |

---

## What actually happened

1. **Feb 6, 2026**  
   LFS was fully disabled in this repo to stop Cursor’s background git/LFS from downloading PersonaPlex files and creating 1.74 TB of temp files (see `docs/PERSONAPLEX_LFS_INCIDENT_AND_PREVENTION_FEB06_2026.md`).  
   `.lfsconfig` was set to:
   - `fetchexclude = *` — don’t fetch any LFS objects (good for this PC).
   - `concurrenttransfers = 0` — “no LFS transfers,” which also disables **upload** during push.

2. **Effect on push**  
   When you run `git push`:
   - Git sends commits and refs.
   - Git LFS is still in the loop (repo has LFS track config and possibly pointers in history).
   - With `concurrenttransfers = 0`, LFS doesn’t do proper uploads. The push can hang, or the server can receive a push that’s inconsistent from LFS’s point of view and respond with **HTTP 500**.

3. **Why it looks “machine-specific”**  
   Only this clone has that aggressive “LFS fully disabled” config. So only **this machine** was pushing with that config; hence push failed here and could work elsewhere.

---

## Fix applied

- **`.lfsconfig`** was updated to use **`concurrenttransfers = 1`** (minimum value that allows LFS uploads) while keeping **`fetchexclude = *`** so Cursor still does **not** download LFS files on this PC.
- This matches the fix in `docs/GIT_CRISIS_AND_COMPREHENSIVE_FIX_FEB10_2026.md`.

After that change, run:

```bash
git add .lfsconfig
git commit -m "fix: allow LFS push with concurrenttransfers=1, keep fetchexclude to protect PC"
git push origin main
```

---

## Summary

- **Cause:** LFS was turned off for safety on this PC (`concurrenttransfers = 0`), which also broke push and led to GitHub returning HTTP 500.
- **Not caused by:** multiple agents pushing at once, large files alone, or GitHub being down.
- **Fix:** Set `concurrenttransfers = 1` in `.lfsconfig`; keep `fetchexclude = *` so this Cursor machine still doesn’t download LFS and risk the 1.74 TB issue again.
