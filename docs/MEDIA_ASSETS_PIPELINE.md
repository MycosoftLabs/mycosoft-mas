# Media Assets Pipeline (Videos / Large Files)

## Goal

Stop spending hours moving videos during deployments.

**Rule**: large media (mp4/webm) must not be part of the Docker image build context whenever possible.

## Recommended Architecture

- **Source of truth**: NAS share or Google Drive folder (staging).
- **Serve path**: a stable directory on the VM (example: `/opt/mycosoft/media/website`).
- **Website container**: mounts the media directory as a **read-only volume** so updating videos does **not** require a rebuild.

### Why this works

- Docker rebuilds are slow when the build context includes large binaries.
- Git pushes/pulls become slow and error-prone with large assets.
- A volume mount lets you update media independently from code deploys.

## VM Layout

Create a media directory on the VM:

```bash
sudo mkdir -p /opt/mycosoft/media/website
sudo chown -R mycosoft:mycosoft /opt/mycosoft/media
```

## Docker Compose (Website) Mount

In the **VM main compose** (`/opt/mycosoft/docker-compose.yml`), mount the media directory into the website container:

- **Host**: `/opt/mycosoft/media/website`
- **Container**: `/app/public/media` (or `/app/public/assets` depending on preference)

Example snippet:

```yaml
services:
  mycosoft-website:
    volumes:
      - /opt/mycosoft/media/website:/app/public/media:ro
```

Then in the website code, reference videos as:

- `/media/mushroom1/waterfall-1.mp4`

## Sync Options (Fast)

### Option A — NAS (best on LAN)

1. Put videos on NAS under a predictable folder:
   - `\\MYCOSOFT-NAS\mycosoft-media\website\...`
2. Mount NAS on VM (NFS/SMB) **or** sync from Windows → VM (see scripts below).

### Option B — Google Drive (staging only)

Google Drive is fine as a staging source, but it’s **not ideal as the public origin** for MP4 streaming.

Use Drive → VM sync (or Drive → object storage/CDN), then serve from the VM mount or CDN.

## Scripts

- `scripts/media/sync-website-media.ps1`
  - Syncs local `website/public/...` media to a target (NAS path or VM path).

## Deployment Impact

With this pipeline:

- **Code deploy**: fast (git pull + docker build without large assets)
- **Media update**: fast (sync only changed files)
- **No rebuild needed** for media-only updates (container reads from volume)

