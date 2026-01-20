## Agent Handoff — NAS-backed Website Media (`/assets/*`)

### What is done
- VM mounts NAS share `//192.168.0.105/mycosoft.com` at `/mnt/mycosoft-nas`.
- Website media host path `/opt/mycosoft/media/website/assets` is **NAS-backed**.
- Website container mounts host assets read-only:
  - `/opt/mycosoft/media/website/assets` → `/app/public/assets:ro`
- Origin + external both return **200** for:
  - `/assets/mushroom1/a.mp4`
  - `/assets/mushroom1/Main A.jpg`

### What to tell future agents
- **Media deployment = copy to NAS**, not git, not Docker build.
- Assets MUST be placed into device folders:
  - `\\\\192.168.0.105\\mycosoft.com\\website\\assets\\mushroom1\\...`
- If `/assets/*` is stale on the public site, **Purge Everything** in Cloudflare.
- If container was started before the NAS mount, recreate it:
  - `docker compose ... up -d --force-recreate mycosoft-website`

### Main runbooks to read
- `docs/NAS_MEDIA_INTEGRATION.md`
- `docs/RUNBOOK_NAS_MEDIA_WEBSITE_ASSETS.md`
- `docs/DEPLOYMENT_INSTRUCTIONS_MASTER.md`

### Failure modes we hit (and fixes)
- **CRLF in bash script** → `l: invalid option name`
  - Fix: `sed -i 's/\r$//' <script>`
  - Prevention: `.gitattributes` enforces LF for `*.sh`
- **`mount error(13)` + `STATUS_LOGON_FAILURE`**
  - Cause: NAS SMB auth rejected; use correct username format (plain `morgan` worked)
  - Validate with `smbclient -L //192.168.0.105 -U 'morgan'`
- **Flat NAS folder** (files in `assets/` instead of `assets/mushroom1/`)
  - Fix: create folder + move files

### Scripts involved (repo)
- `scripts/vm_payloads/setup_nas_website_assets.sh` (uploaded to `/home/mycosoft/setup_nas_website_assets.sh`)
- `scripts/vm_upload_file.py`, `scripts/vm_read_file.py`, `scripts/vm_exec.py`
