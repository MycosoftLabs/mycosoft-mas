# Device Media Assets Pipeline

## Overview

All device product pages serve media (images and videos) from a centralized NAS, not from the Docker build context. This enables:
- **Instant media updates** without Docker rebuilds
- **Fast deployments** (code-only, no large binary transfers)
- **Consistent asset management** across environments

## Device Folder Structure

Each device has a dedicated folder following this naming convention:

| Device | Folder Name | Public URL | Local Path |
|--------|-------------|------------|------------|
| Mushroom 1 | `mushroom1` | `/assets/mushroom1/*` | `public/assets/mushroom1/` |
| SporeBase | `sporebase` | `/assets/sporebase/*` | `public/assets/sporebase/` |
| Hyphae 1 | `hyphae1` | `/assets/hyphae1/*` | `public/assets/hyphae1/` |
| MycoNode | `myconode` | `/assets/myconode/*` | `public/assets/myconode/` |
| ALARM | `alarm` | `/assets/alarm/*` | `public/assets/alarm/` |

## Path Mapping (Full Stack)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  CONTENT CREATOR (Windows)                                               │
│  C:\Users\...\WEBSITE\website\public\assets\{device}\                   │
└────────────────────────────┬────────────────────────────────────────────┘
                             │ sync_website_media_paramiko.py (SFTP)
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  NAS SHARE (192.168.0.105)                                               │
│  \\192.168.0.105\mycosoft.com\website\assets\{device}\                  │
└────────────────────────────┬────────────────────────────────────────────┘
                             │ SMB/CIFS mount (via setup_nas_website_assets.sh)
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  VM HOST (192.168.0.187)                                                 │
│  /opt/mycosoft/media/website/assets/{device}/                           │
└────────────────────────────┬────────────────────────────────────────────┘
                             │ Docker bind mount (:ro)
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  DOCKER CONTAINER (mycosoft-website)                                     │
│  /app/public/assets/{device}/                                            │
└────────────────────────────┬────────────────────────────────────────────┘
                             │ Next.js static serving
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  PUBLIC URL (via Cloudflare)                                             │
│  https://sandbox.mycosoft.com/assets/{device}/filename.mp4              │
└─────────────────────────────────────────────────────────────────────────┘
```

## Recommended File Naming Conventions

### Images
- `main.jpg` - Primary product image (used in hero, cards)
- `main-alt.jpg` - Alternative primary image
- `{feature}.jpg` - Feature-specific images (e.g., `sensors.jpg`, `housing.jpg`)
- `gallery-{n}.jpg` - Gallery images (numbered)
- `blueprint.png` - Technical blueprint/schematic
- Keep names **lowercase with hyphens** (no spaces)

### Videos
- `hero.mp4` - Hero section background video
- `demo.mp4` - Product demonstration video
- `{feature}.mp4` - Feature-specific videos (e.g., `assembly.mp4`, `deployment.mp4`)
- `gallery-{n}.mp4` - Gallery videos (numbered)
- Use **H.264 codec** for maximum compatibility
- Consider WebM versions for browsers with VP9 support

### File Size Guidelines
- Images: Optimize to < 500KB per file (use WebP when possible)
- Videos: Keep < 50MB per clip for web streaming
- Use thumbnail/preview images for video galleries

## Workflow: Adding New Media

### 1. Add files locally
```powershell
# Copy your media to the appropriate device folder
Copy-Item "C:\Photos\sporebase-main.jpg" "C:\Users\...\WEBSITE\website\public\assets\sporebase\"
```

### 2. Sync to VM (SFTP)
```bash
# Run from MAS repo
python scripts/media/sync_website_media_paramiko.py
```

### 3. Restart container (if new files)
```bash
# On VM or via Proxmox API
docker restart mycosoft-website
```

### 4. Purge Cloudflare cache (if updating existing files)
```bash
# Via Cloudflare dashboard or API
curl -X POST "https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache" \
  -H "Authorization: Bearer {api_token}" \
  -d '{"purge_everything": true}'
```

### 5. Verify
```bash
# Check HTTP response
curl -I https://sandbox.mycosoft.com/assets/sporebase/main.jpg
```

## Docker Compose Configuration

The website container must have the media volume mount:

```yaml
services:
  mycosoft-website:
    volumes:
      - /opt/mycosoft/media/website/assets:/app/public/assets:ro
```

This is configured in `docker-compose.always-on.yml`.

## NAS Folder Setup (One-Time)

On the NAS, ensure these folders exist under `mycosoft.com\website\assets\`:

```
website/
└── assets/
    ├── mushroom1/    ✅ Already exists
    ├── sporebase/    🆕 Create
    ├── hyphae1/      🆕 Create
    ├── myconode/     🆕 Create
    └── alarm/        🆕 Create
```

Create via SMB:
```powershell
# From Windows with NAS access
New-Item -ItemType Directory -Force -Path "\\192.168.0.105\mycosoft.com\website\assets\sporebase"
New-Item -ItemType Directory -Force -Path "\\192.168.0.105\mycosoft.com\website\assets\hyphae1"
New-Item -ItemType Directory -Force -Path "\\192.168.0.105\mycosoft.com\website\assets\myconode"
New-Item -ItemType Directory -Force -Path "\\192.168.0.105\mycosoft.com\website\assets\alarm"
```

## Code References

Each device detail component references assets using the pattern:

```typescript
// In sporebase-details.tsx
const SPOREBASE_ASSETS = {
  mainImage: "/assets/sporebase/main.jpg",
  heroVideo: "/assets/sporebase/hero.mp4",
  gallery: [
    "/assets/sporebase/gallery-1.jpg",
    "/assets/sporebase/gallery-2.jpg",
  ]
}
```

Currently using placeholder URLs until media is added:
- SporeBase: Uses vercel blob storage URL
- Hyphae 1: Uses placeholder.svg
- MycoNode: Uses placeholder.svg
- ALARM: Uses vercel blob storage URL

## Known Issues & Solutions

### Next.js 404 for new files
**Symptom**: File exists on VM but URL returns 404
**Cause**: Next.js standalone caches file listings
**Fix**: `docker restart mycosoft-website`

### Cloudflare serves stale content
**Symptom**: Old file version after update
**Fix**: Purge Cloudflare cache (Dashboard → Caching → Purge Everything)

### SMB mount fails with error(13)
**Symptom**: `mount error(13): Permission denied`
**Fix**: Ensure NAS credentials are correct and `sec=ntlmssp` is used

## Related Documentation

- `docs/NAS_MEDIA_INTEGRATION.md` - NAS mounting details
- `docs/RUNBOOK_NAS_MEDIA_WEBSITE_ASSETS.md` - Operational runbook
- `docs/MEDIA_ASSETS_PIPELINE.md` - Architecture overview
- `docs/DEPLOYMENT_REPORT_MUSHROOM1_MEDIA_JAN19_2026.md` - Mushroom 1 setup reference
