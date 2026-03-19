# Human Team Page Not Live — Next Steps (Mar 15, 2026)

**Issue:** Changes to https://mycosoft.com/about/human-team are not live yet. Perplexity is attempting a new deploy; if that doesn’t work, use the steps below.

---

## Why Changes Might Not Be Live

1. **Code not on `main`** — Deploy only runs when the website repo has the human-team (and related) changes on `main`.
2. **Deploy not run or failed** — Either GitHub Actions didn’t run/finish, or a manual deploy wasn’t run.
3. **Cloudflare cache** — Old HTML/JS can be cached; purge after every deploy.

---

## If Perplexity’s Deploy Doesn’t Work — Do This

### Option A: Deploy from Cursor (manual, from website repo)

1. **Open website repo:** `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website`
2. **Load credentials** (PowerShell):
   ```powershell
   Get-Content ".credentials.local" | ForEach-Object { if ($_ -match "^([^#=]+)=(.*)$") { [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process") } }
   ```
3. **Run production deploy:**
   ```powershell
   python _rebuild_sandbox.py --production
   ```
   This script SSHs to VM 187, pulls code, builds the Docker image on the VM, restarts the container, then purges Cloudflare. Allow ~15–30 min for the VM build.
4. **Verify:** Open https://mycosoft.com/about/human-team in an incognito window or hard refresh (Ctrl+Shift+R).

### Option B: Use GitHub Actions (if code is already on `main`)

1. **GitHub:** website repo → **Actions** → **Deploy to Sandbox (Production)**.
2. **Run workflow:** Click **Run workflow** → **Run workflow** (uses `workflow_dispatch`).
3. Wait for **Build** then **Deploy** jobs to finish (~5–15 min total; build in CI, VM only pulls).
4. Workflow purges Cloudflare at the end. Then verify https://mycosoft.com/about/human-team.

### Option C: Push to main to trigger auto-deploy

If changes aren’t pushed yet:

1. Commit and push to `main` in the **website** repo (path filters in the workflow include `app/**`, so human-team under `app/about/` will trigger the workflow).
2. Wait for the **Deploy to Sandbox (Production)** workflow to complete.
3. If workflow succeeded but the page still looks old, run **Purge Everything** in Cloudflare (or run the purge script in the website repo).

---

## Purge Cloudflare (after any manual deploy)

From **website repo** root:

```powershell
python -c "from _cloudflare_cache import purge_everything; purge_everything()"
```

---

## Verify

- **Page:** https://mycosoft.com/about/human-team  
- **Hard refresh or incognito** so the browser doesn’t use cached assets.

---

## Reference

- **Production route:** [MYCOSOFT_COM_PRODUCTION_SANDBOX_ROUTE_MAR13_2026](./MYCOSOFT_COM_PRODUCTION_SANDBOX_ROUTE_MAR13_2026.md)
- **CI/CD (build in CI, VM pull):** [INSTANT_UPDATES_AND_FAST_CICD_MAR15_2026](./INSTANT_UPDATES_AND_FAST_CICD_MAR15_2026.md)
- **Workflow:** `WEBSITE/website/.github/workflows/deploy-sandbox-production.yml`
