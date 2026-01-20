## NAS media integration (sandbox) — instant deployments

### Goal
Move **large media** (videos/images) out of git and out of Docker build contexts by hosting it on a **NAS share** and mounting it on the **VM host**, then bind-mounting it into the website container at:

- **Public URL**: `/assets/...`
- **Container path**: `/app/public/assets`
- **Host path (VM)**: `/opt/mycosoft/media/website/assets`

Once this is in place:
- Copying a file to the NAS is effectively “deploying media” (no rebuild).
- The website container serves the new file immediately (mount already active).
- Cloudflare may still cache; use purge when required.

### Why it wasn’t instant before
The VM currently uses **local disk** for `/opt/mycosoft/media/website/assets` (no CIFS mount), so media updates require a manual sync step.

### Architecture (recommended)
- **NAS** exports SMB share (CIFS)
- **VM** mounts SMB share to `/mnt/mycosoft-nas`, then bind-mounts the exact subfolder to `/opt/mycosoft/media/website/assets`
- **Docker compose** binds that host path into the website container (read-only)

### Concrete path mapping (your setup)
- **NAS share root**: `\\\\192.168.0.105\\mycosoft.com`
- **NAS website assets folder**: `\\\\192.168.0.105\\mycosoft.com\\website\\assets`
- **Required structure**: assets are organized into **subfolders** that match the URL paths, e.g.:
  - URL: `/assets/mushroom1/a.mp4`
  - NAS: `\\\\192.168.0.105\\mycosoft.com\\website\\assets\\mushroom1\\a.mp4`
- **VM mountpoint target**: `/opt/mycosoft/media/website/assets`
- **Container bind mount**: `/opt/mycosoft/media/website/assets:/app/public/assets:ro`
- **URL**: `/assets/...`

### Required inputs (you provide)
- **NAS host**: e.g. `192.168.0.X` or `nas.local`
- **Share name**: `mycosoft.com`
- **Subpath** (inside the share): `website/assets`
- **SMB username/password** (or guest)

### Implementation steps (VM)
**Recommended (fast + safe): run the automated VM script**

This is designed to:
- Prompt you for the NAS password **on the VM** (not stored in chat)
- **Test-mount first** (so we don’t permanently write broken `fstab` entries)
- Use the common SMB auth mode that fixes `mount error(13)` on many NAS setups (`sec=ntlmssp`)

On the VM:

```bash
sudo bash /home/mycosoft/setup_nas_website_assets.sh
```

What it sets up:
- SMB mount: `//192.168.0.105/mycosoft.com` → `/mnt/mycosoft-nas`
- Bind mount: `/mnt/mycosoft-nas/website/assets` → `/opt/mycosoft/media/website/assets`

**Manual steps (if you need them)**

1. Install CIFS support:

```bash
sudo apt-get update
sudo apt-get install -y cifs-utils
```

2. Create mountpoints:

```bash
sudo mkdir -p /mnt/mycosoft-nas
sudo mkdir -p /opt/mycosoft/media/website/assets
```

3. Create credential file:

```bash
sudo install -d -m 0700 /etc/samba
sudo tee /etc/samba/mycosoft-nas.creds >/dev/null <<'EOF'
username=morgan@mycosoft.org
password=YOUR_PASS
EOF
sudo chmod 600 /etc/samba/mycosoft-nas.creds
```

4. Test-mount first (before touching `/etc/fstab`):

```bash
sudo umount /mnt/mycosoft-nas 2>/dev/null || true
sudo mount -t cifs //192.168.0.105/mycosoft.com /mnt/mycosoft-nas \
  -o credentials=/etc/samba/mycosoft-nas.creds,vers=3.0,sec=ntlmssp,noserverino,nounix,iocharset=utf8,uid=mycosoft,gid=mycosoft,file_mode=0644,dir_mode=0755
```

5. Bind-mount the subfolder used by the website:

```bash
sudo mount --bind /mnt/mycosoft-nas/website/assets /opt/mycosoft/media/website/assets
```

6. Persist in `/etc/fstab` (example):

```bash
# mycosoft-nas-assets
//192.168.0.105/mycosoft.com /mnt/mycosoft-nas cifs credentials=/etc/samba/mycosoft-nas.creds,vers=3.0,sec=ntlmssp,noserverino,nounix,iocharset=utf8,uid=mycosoft,gid=mycosoft,file_mode=0644,dir_mode=0755,nofail,_netdev 0 0
/mnt/mycosoft-nas/website/assets /opt/mycosoft/media/website/assets none bind 0 0
```

7. Validate:

```bash
mount | grep -i cifs
mount | grep -E '/opt/mycosoft/media/website/assets|/mnt/mycosoft-nas'
ls -la /opt/mycosoft/media/website/assets/mushroom1 | head
```

8. Ensure docker compose binds the host path into the website container:
- Compose should include:

```yaml
volumes:
  - /opt/mycosoft/media/website/assets:/app/public/assets:ro
```

### Operational rule
- **Media changes**: copy to NAS (instant), then **purge Cloudflare** if the browser still serves stale content.
- **Code changes**: still require the normal docker rebuild flow.

### Critical nuance: container may need recreate after switching local → NAS
Docker mount propagation is commonly `rprivate`. If the website container was started before the host mount existed, recreate it:

```bash
cd /home/mycosoft/mycosoft/mas
docker compose -p mycosoft-always-on -f docker-compose.always-on.yml up -d --no-deps --force-recreate mycosoft-website
```

### Fixing a flat NAS assets folder (no subfolder)
If files were copied into `\\\\192.168.0.105\\mycosoft.com\\website\\assets\\` (flat) but the website requests `/assets/mushroom1/...`, create the folder and move files:

```bash
cd /mnt/mycosoft-nas/website/assets
mkdir -p mushroom1
find . -maxdepth 1 -type f -print0 | xargs -0 mv -n -t mushroom1 --
```

### Troubleshooting

#### `mount error(13): Permission denied`

Common causes:
- SMB user does not have permission to the share `mycosoft.com`
- NAS requires `sec=ntlmssp` (included above)
- NAS blocks SMB3 (try `vers=2.1` temporarily for diagnosis)

On the VM (prompts for NAS password):

```bash
smbclient -L //192.168.0.105 -U 'morgan@mycosoft.org'
smbclient //192.168.0.105/mycosoft.com -U 'morgan@mycosoft.org' -c 'ls'
```

If `smbclient` can’t list shares or `ls`, the issue is NAS-side credentials/permissions (not the VM).
