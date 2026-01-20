## Runbook — NAS-backed Website Media (`/assets/*`)

### Audience
- **Staff / Ops** deploying media for `sandbox.mycosoft.com` and future environments
- **Agents** needing deterministic steps and failure-mode handling

### Goal
Serve website media from the NAS without rebuilding Docker images:
- NAS is the **source of truth** for large media.
- VM mounts NAS.
- Website container reads media via a read-only bind mount.

### Required paths (canonical)
- **NAS share**: `\\\\192.168.0.105\\mycosoft.com`
- **NAS website assets root**: `\\\\192.168.0.105\\mycosoft.com\\website\\assets`
- **Device folder rule** (important):
  - Put files into per-device folders, e.g.:
    - `\\\\192.168.0.105\\mycosoft.com\\website\\assets\\mushroom1\\a.mp4`
- **VM mount root**: `/mnt/mycosoft-nas`
- **VM website assets**: `/opt/mycosoft/media/website/assets`
- **Container website assets**: `/app/public/assets` (**read-only**)
- **Public URL**: `/assets/...`

### One-command setup on VM (recommended)
On the VM:

```bash
sudo bash /home/mycosoft/setup_nas_website_assets.sh
```

Notes:
- Prompts for NAS password on the VM (never in chat).
- Test-mounts before writing `/etc/fstab`.
- Uses `sec=ntlmssp` for SMB auth compatibility.

### Verification checklist (must pass)
#### VM mounts

```bash
mount | egrep -i '192\\.168\\.0\\.105|/mnt/mycosoft-nas|/opt/mycosoft/media/website/assets'
ls -la /opt/mycosoft/media/website/assets/mushroom1 | head
```

#### Container mount

```bash
docker inspect mycosoft-always-on-mycosoft-website-1 --format '{{json .Mounts}}'
docker exec mycosoft-always-on-mycosoft-website-1 ls -la /app/public/assets/mushroom1 | head
```

#### Origin and public checks

```bash
curl -I http://localhost:3000/assets/mushroom1/a.mp4
curl -I https://sandbox.mycosoft.com/assets/mushroom1/a.mp4
```

Expected: **HTTP 200**.

### Known failure modes & fixes
#### `l: invalid option name` when running the script
Cause: CRLF line endings.

Fix on VM:

```bash
sed -i 's/\r$//' /home/mycosoft/setup_nas_website_assets.sh
```

Repo prevention: `.gitattributes` enforces LF for `*.sh`.

#### `mount error(13)` + `STATUS_LOGON_FAILURE`
Cause: NAS rejected SMB auth (username format / password / share permissions).

Fix: validate login with `smbclient`:

```bash
smbclient -L //192.168.0.105 -U 'morgan'
smbclient //192.168.0.105/mycosoft.com -U 'morgan' -c 'ls'
```

#### `/assets/mushroom1/*` requested but NAS files are “flat”
If you mistakenly placed files directly under:
- `\\\\192.168.0.105\\mycosoft.com\\website\\assets\\*.mp4`

Fix by creating the folder and moving files:

```bash
cd /mnt/mycosoft-nas/website/assets
mkdir -p mushroom1
find . -maxdepth 1 -type f -print0 | xargs -0 mv -n -t mushroom1 --
```

#### Container doesn’t see updated mountpoint
Fix: recreate the website container (mount propagation):

```bash
cd /home/mycosoft/mycosoft/mas
docker compose -p mycosoft-always-on -f docker-compose.always-on.yml up -d --no-deps --force-recreate mycosoft-website
```

### Ops rule
- **Media-only change**: Copy files to NAS → verify URL → purge Cloudflare if stale.
- **Code change**: follow `docs/DEPLOYMENT_INSTRUCTIONS_MASTER.md` (rebuild Docker, restart, purge Cloudflare).
