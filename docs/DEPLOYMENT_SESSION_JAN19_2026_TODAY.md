## Deployment Session Notes — Jan 19–20, 2026 (Today)

**Scope**: Fix Mushroom 1 mobile video behavior on `sandbox.mycosoft.com`, stabilize sandbox website container bring-up on the VM, and ensure media + Supabase integration is correctly wired for the always-on stack.

### What you asked

- **Mobile**: “I don’t see all videos running on mobile version of `sandbox.mycosoft.com`.”
- **Follow-up**: “Why did you change the Mushroom 1 hero video?”
- **Now**: “Document everything you did today.”

---

## Summary (what changed)

- **Website (code)**:
  - Updated `components/devices/mushroom1-details.tsx` to improve mobile video reliability:
    - Ensured mobile-safe video attributes (`muted`, `playsInline`, `preload="metadata"`).
    - Added a **mobile fallback hero video selection** to avoid the 8K hero MP4 on phones (iOS/Safari decode/autoplay reliability).
    - Wired **Watch Film** to a working in-page video modal.
- **Website (build/runtime)**:
  - Fixed `Dockerfile.container` to make builds more deterministic and reduce dependency install failures:
    - Prefer `npm ci` (with fallback to `npm install`) and `--legacy-peer-deps`.
    - Fixed stage separation/newline issue that broke Dockerfile parsing.
- **Sandbox VM (always-on stack)**:
  - Resolved **port 3000 already allocated** by removing the old `mycosoft-website` container and starting the always-on website container.
  - Fixed a **500 error** cause: missing Supabase env caused the website to throw and fail to render pages on sandbox.
  - Ensured `/assets/...` MP4s are served by mounting host media into the website container:
    - Host: `/opt/mycosoft/media/website/assets`
    - Container: `/app/public/assets` (read-only)
  - Added a compatibility alias for a mismatched filename:
    - Created `Walking.mp4` symlink → `mushroom 1 walking.mp4`

---

## Repos and key commits (local)

### Website repo (`CODE/WEBSITE/website`)

- **85594ff** — `Fix mobile video playback for Mushroom 1`
  - File: `components/devices/mushroom1-details.tsx`
- **762ee21** — `Fix Docker build deps resolution`
  - File: `Dockerfile.container`
- **84f7500** — `Fix Dockerfile.container stage separation`
  - File: `Dockerfile.container`

### MAS repo (`CODE/MAS/mycosoft-mas`)

- Documentation and deploy tooling work was already captured in:
  - `docs/SANDBOX_DEPLOYMENT_RUNBOOK.md`
  - `docs/DEPLOYMENT_REPORT_MUSHROOM1_MEDIA_JAN19_2026.md`
  - `docs/MEDIA_ASSETS_PIPELINE.md`

---

## Detailed timeline (what I actually did)

### 1) Mobile verification and diagnosis

- Tested `https://sandbox.mycosoft.com/devices/mushroom-1` in a mobile viewport.
- Observed that MP4 requests could load, but reliable playback on real phones is frequently blocked by:
  - Autoplay policy (needs `muted` + `playsInline`)
  - Decode constraints (very large MP4s—especially 8K—stall on mobile Safari)

### 2) Code change: make hero video mobile-safe and modal real

- Implemented:
  - A small `useIsMobile()` helper to choose a safer hero MP4 on mobile.
  - A modal flow so **Watch Film** actually plays a video (rather than being a dead CTA).

**Why the hero video was changed**:

- The original hero background video was effectively an **8K MP4** on desktop.
- Mobile Safari and many phones do not reliably autoplay or even decode 8K background MP4s; this manifests as “videos not running on mobile”.
- So the hero now selects a smaller, known-working MP4 on mobile, while keeping the high-quality hero on desktop.

### 3) Sandbox VM: website container swap (port 3000)

- Attempting to start the always-on website initially failed with:
  - `Bind for 0.0.0.0:3000 failed: port is already allocated`
- Found the existing container holding port 3000:
  - `mycosoft-website` (old container)
- Removed it and started the always-on website service:
  - `docker rm -f mycosoft-website`
  - `docker compose -f docker-compose.always-on.yml up -d --no-deps --no-build mycosoft-website`

### 4) Sandbox VM: fixed “500 everywhere” (Supabase config)

- The new container came up, but `/devices/mushroom-1` returned **500**.
- Root cause from container logs:
  - `[Supabase] Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY`
  - The code throws when Supabase client env is missing, causing client-side exceptions.

Fix:

- Wrote `/home/mycosoft/mycosoft/mas/.env` with:
  - `NEXT_PUBLIC_SUPABASE_URL`
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
  - `NEXTAUTH_URL=https://sandbox.mycosoft.com`
- Recreated the container to pick up env:
  - `docker compose -f docker-compose.always-on.yml up -d --no-deps --force-recreate mycosoft-website`

### 5) Sandbox VM: fixed `/assets/...` serving (404 for MP4s)

- After the 500 fix, `/devices/mushroom-1` returned **200**, but `/assets/mushroom1/Walking.mp4` was **404**.
- Verified the file existed on the VM media host folder, but with a different name:
  - present: `mushroom 1 walking.mp4`
  - expected by code: `Walking.mp4`

Fixes:

- Added a symlink for compatibility:
  - `/opt/mycosoft/media/website/assets/mushroom1/Walking.mp4` → `mushroom 1 walking.mp4`
- Mounted the media folder into the website container by patching `docker-compose.always-on.yml`:
  - `- /opt/mycosoft/media/website/assets:/app/public/assets:ro`
- Recreated container and verified:
  - `http://localhost:3000/assets/mushroom1/Walking.mp4` → **200**
  - `http://localhost:3000/assets/mushroom1/waterfall%201.mp4` → **200**

### 6) Sandbox VM: fixed Supabase build-time env embedding (client bundle)

- Even after runtime env was present, sandbox browser still showed:
  - “Supabase credentials not configured”
- Cause: `Dockerfile.container` did **not** accept or set Supabase `NEXT_PUBLIC_*` at build time, so the **client bundle** was built without them.

Fix:

- Patched VM `website/Dockerfile.container` to include:
  - `ARG NEXT_PUBLIC_SUPABASE_URL`
  - `ARG NEXT_PUBLIC_SUPABASE_ANON_KEY`
  - `ENV NEXT_PUBLIC_SUPABASE_URL=${NEXT_PUBLIC_SUPABASE_URL}`
  - `ENV NEXT_PUBLIC_SUPABASE_ANON_KEY=${NEXT_PUBLIC_SUPABASE_ANON_KEY}`
- Patched VM `mas/docker-compose.always-on.yml` to pass the args under `build.args`.
- Rebuilt and recreated the website container:
  - `docker compose -f docker-compose.always-on.yml build --no-cache mycosoft-website`
  - `docker compose -f docker-compose.always-on.yml up -d --no-deps --force-recreate mycosoft-website`

---

## Final verification (what is now true)

### Mobile UI (browser emulation)

- `https://sandbox.mycosoft.com/devices/mushroom-1`
  - Page renders (no client-side crash)
  - **Hero video plays on mobile** (muted + playsInline)
  - **Watch Film** opens a modal and the modal MP4 plays

### Assets

- `/assets/mushroom1/waterfall 1.mp4` → **200**
- `/assets/mushroom1/mushroom 1 walking.mp4` → **200**
- `/assets/mushroom1/Walking.mp4` → **200** (symlink alias)

---

## Files touched on the VM (operational)

- `/home/mycosoft/mycosoft/mas/.env`
  - Added `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXTAUTH_URL`
- `/home/mycosoft/mycosoft/mas/docker-compose.always-on.yml`
  - Added the media `volumes:` mount to `mycosoft-website`
  - Added Supabase `build.args` for `mycosoft-website`
- `/home/mycosoft/mycosoft/website/Dockerfile.container`
  - Added Supabase ARG/ENV for build-time embedding into client bundle
- `/opt/mycosoft/media/website/assets/mushroom1/Walking.mp4`
  - Symlink to normalize filename expected by the website

---

## Notes / follow-ups for future upgrades

- **Do not rely on runtime env alone** for `NEXT_PUBLIC_*` variables. If the client code reads env at build time, you must pass them as `ARG` → `ENV` in the build stage.
- **Keep hero videos mobile-friendly**:
  - Use smaller resolutions/bitrates for background videos on mobile; keep 8K for desktop if desired.
- **Prefer the mounted media path**:
  - Put new videos into `/opt/mycosoft/media/website/assets/...` and restart/recreate the website container (or ensure it’s already mounting that folder) instead of rebuilding images.

---

## Next upgrades (action list — prioritized)

### P0 — Sandbox reliability (stop regressions)

- **Lock in Supabase env as a first-class requirement**
  - Ensure `/home/mycosoft/mycosoft/mas/.env` always contains:
    - `NEXT_PUBLIC_SUPABASE_URL`
    - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
    - `NEXTAUTH_URL=https://sandbox.mycosoft.com`
    - (and add `NEXTAUTH_SECRET` so NextAuth stops warning + sessions are secure)
- **Bake `NEXT_PUBLIC_*` properly for Docker builds**
  - Keep `Dockerfile.container` accepting `ARG NEXT_PUBLIC_*` and setting `ENV NEXT_PUBLIC_*` **in the build stage**.
  - Keep `docker-compose.always-on.yml` passing required `build.args` for any `NEXT_PUBLIC_*` variables used by the client.
- **Make “website up” a single command**
  - Add a script (MAS repo) that runs:
    - `docker compose -f docker-compose.always-on.yml build --no-cache mycosoft-website`
    - `docker compose -f docker-compose.always-on.yml up -d --no-deps --force-recreate mycosoft-website`
  - Follow immediately with a smoke test:
    - `curl -I http://localhost:3000/devices/mushroom-1`
    - `curl -I http://localhost:3000/assets/mushroom1/waterfall%201.mp4`

### P0 — Media pipeline hardening (no more filename surprises)

- **Normalize filenames in `/assets/mushroom1/`**
  - Decide a canonical naming scheme (lowercase + dashes) and enforce it:
    - Example: `walking.mp4`, `waterfall.mp4`, `hero.mp4`
  - Remove reliance on spaces (or add a permanent alias step during sync).
- **Add an automated “asset alias” step to the sync process**
  - After sync, ensure expected paths exist (create symlinks if needed):
    - `Walking.mp4` → `mushroom 1 walking.mp4` (current example)
- **Document + enforce the mount**
  - Ensure the always-on website service always mounts:
    - `/opt/mycosoft/media/website/assets:/app/public/assets:ro`

### P1 — Performance (mobile first)

- **Replace 8K MP4 hero with responsive encodes**
  - Create a dedicated hero set:
    - Mobile: 720p/1080p low bitrate
    - Desktop: 1440p/2160p
  - Update `MUSHROOM1_ASSETS` to reference those explicit files rather than “b.mp4”.
- **Add a graceful fallback poster**
  - Provide `poster=` for hero videos so slow devices show a clean image while video buffers.

### P1 — Security/auth correctness

- **Set real `NEXTAUTH_SECRET` on the VM**
  - Remove “Defaulting to blank string” warnings and ensure secure auth cookies.
- **Decide sandbox vs prod Supabase projects**
  - Confirm whether sandbox should use a dedicated Supabase project (recommended) vs sharing prod keys.
  - If dedicated: create a separate `.env` profile and rotate keys accordingly.

### P2 — Observability (so you can move faster next time)

- **Add a “one screen” health dashboard**
  - Website: `/api/health`
  - MINDEX API: `/api/mindex/health`
  - MycoBrain: `/api/mycobrain/health`
  - Cloudflare tunnel: status + last reload timestamp
- **Add log capture helpers**
  - `docker logs --tail 200 mycosoft-always-on-mycosoft-website-1`
  - `docker logs --tail 200 mycosoft-always-on-mindex-api-1`

