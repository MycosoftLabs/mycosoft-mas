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
- **VM** mounts SMB share to `/opt/mycosoft/media/website/assets`
- **Docker compose** binds that host path into the website container (read-only)

### Concrete path mapping (your setup)
- **NAS share root**: `\\\\192.168.0.105\\mycosoft.com`
- **NAS website assets folder**: `\\\\192.168.0.105\\mycosoft.com\\website\\assets`
- **VM mountpoint target**: `/opt/mycosoft/media/website/assets`
- **Container bind mount**: `/opt/mycosoft/media/website/assets:/app/public/assets:ro`
- **URL**: `/assets/...`

### Required inputs (you provide)
- **NAS host**: e.g. `192.168.0.X` or `nas.local`
- **Share name**: `mycosoft.com`
- **Subpath** (inside the share): `website/assets`
- **SMB username/password** (or guest)

### Implementation steps (VM)
1. Install CIFS support:

```bash
sudo apt-get update
sudo apt-get install -y cifs-utils
```

2. Create mountpoint:

```bash
sudo mkdir -p /opt/mycosoft/media/website/assets
```

3. Create credential file:

```bash
sudo install -d -m 0700 /etc/samba
sudo tee /etc/samba/mycosoft-nas.creds >/dev/null <<'EOF'
username=YOUR_USER
password=YOUR_PASS
EOF
sudo chmod 600 /etc/samba/mycosoft-nas.creds
```

4. Add `/etc/fstab` entry (example):

```bash
//NAS_HOST/SHARE_NAME /mnt/mycosoft-nas cifs \
credentials=/etc/samba/mycosoft-nas.creds,vers=3.0,iocharset=utf8,uid=mycosoft,gid=mycosoft,file_mode=0644,dir_mode=0755,nofail,_netdev 0 0
```

Then bind-mount the exact subfolder your website needs:

```bash
sudo mkdir -p /opt/mycosoft/media/website/assets
sudo mount --bind /mnt/mycosoft-nas/website/assets /opt/mycosoft/media/website/assets
```

5. Mount now:

```bash
sudo mount -a
```

6. Validate:

```bash
mount | grep -i cifs
mount | grep -E '/opt/mycosoft/media/website/assets|/mnt/mycosoft-nas'
ls -la /opt/mycosoft/media/website/assets/mushroom1 | head
```

7. Ensure docker compose binds the host path into the website container:
- Compose should include:

```yaml
volumes:
  - /opt/mycosoft/media/website/assets:/app/public/assets:ro
```

### Operational rule
- **Media changes**: copy to NAS (instant), then **purge Cloudflare** if the browser still serves stale content.
- **Code changes**: still require the normal docker rebuild flow.

