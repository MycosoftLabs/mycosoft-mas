# Sandbox Build Canceled and Recovery – February 24, 2026

**Status:** Build was canceled; recovery in progress

## What Happened

The website Docker build on Sandbox VM (192.168.0.187) failed with:
```
ERROR: failed to build: failed to solve: Canceled: context canceled
```

**Root cause:** The build was interrupted (likely Cursor crash or session disconnect). The Python deploy script `_rebuild_sandbox.py` runs the build over SSH; when the local process is killed, the remote build receives "context canceled."

**Build progress at cancel:**
- Step 1–8 completed (deps, node:18-alpine, corepack, pnpm)
- Step 9 (COPY node_modules) was in progress (~95% pnpm resolve)
- Legacy builder failed (exit -1), BuildKit retry also canceled

## Recovery Steps

1. **Clean VM:** Kill any orphaned `docker build` processes on 187
2. **Prune:** `docker container prune -f` to remove stopped build containers
3. **Fresh deploy:** Run `_rebuild_sandbox.py` again (single run, no duplicates)
4. **Purge Cloudflare** after successful deploy

## Prevention

- Avoid running multiple `_rebuild_sandbox.py` instances
- If Cursor restarts during deploy, check VM for duplicate builds before retrying
