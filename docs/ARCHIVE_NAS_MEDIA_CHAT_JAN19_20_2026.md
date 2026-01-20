## NAS Media Integration — Chat Archive (Jan 19–20, 2026)

### Purpose
This document archives the full resolution of the “NAS-backed website media” effort for `sandbox.mycosoft.com`, including failures encountered, how we debugged them, and the final working state. Use this as the authoritative internal record when onboarding staff or spinning up agents to work on media deployment.

### Goal (what “done” means)
- Media is **not** deployed via git or Docker builds.
- Media is deployed by placing files on the NAS:
  - `\\\\192.168.0.105\\mycosoft.com\\website\\assets\\...`
- The VM mounts the NAS and the website container serves media at:
  - **URL**: `/assets/...`
  - **Container**: `/app/public/assets` (read-only)
  - **VM host**: `/opt/mycosoft/media/website/assets` (NAS-backed)
- Updates are effectively “instant” on origin; Cloudflare may require purge if cached.

### Environment / identifiers
- **NAS**: `192.168.0.105`
- **Share**: `\\\\192.168.0.105\\mycosoft.com`
- **Assets folder**: `\\\\192.168.0.105\\mycosoft.com\\website\\assets`
- **VM**: `192.168.0.187` (`mycosoft@192.168.0.187`)
- **Website origin**: `http://localhost:3000`
- **Website public**: `https://sandbox.mycosoft.com`
- **Website container**: `mycosoft-always-on-mycosoft-website-1`

### What broke (and why)
#### 1) Bash script error: `l: invalid option name`
**Cause:** The uploaded bash script had **Windows CRLF** line endings (`^M`), which causes bash to mis-parse `set -euo pipefail` and report an invalid option.

**Fix:**
- Converted the VM script to LF: `sed -i 's/\r$//' /home/mycosoft/setup_nas_website_assets.sh`
- Added repo enforcement: `.gitattributes` pins `*.sh` to **LF**.

#### 2) CIFS mount failures: `mount error(13)` + `STATUS_LOGON_FAILURE`
**Signal:** kernel log showed:
- `STATUS_LOGON_FAILURE (0xc000006d)`

**Cause:** SMB authentication rejected. Not an SMB version mismatch; it was credentials/username format.

**Fix:** We updated our process to:
- Verify via `smbclient -L //192.168.0.105 -U '<username>'` interactively
- Ensure the **SMB username** format is correct (email form may not work; plain `morgan` did)
- Updated the VM mount script to prompt for SMB username and allow “guest” test mode.

#### 3) “Mount worked” but `.../mushroom1` missing
**Cause:** The NAS folder was populated as a **flat** directory (`website/assets/*.mp4`) while the website expects subfolders like:
- `/assets/mushroom1/a.mp4`
  ↔ `...\\website\\assets\\mushroom1\\a.mp4`

**Fix:** Created the required device folder and moved the media into it:
- Created `mushroom1/` under NAS assets and moved files.

#### 4) Container did not immediately reflect the new mount
**Cause:** Docker bind mounts often use mount propagation `rprivate`. If the container starts before the host mount is applied, you may need to recreate the container so it sees the updated mountpoint.

**Fix:** Recreate the website container:
- `docker compose ... up -d --no-deps --force-recreate mycosoft-website`

### Final working state (verification)
#### VM mount state
- NAS share mounted to `/mnt/mycosoft-nas`
- Website assets path is NAS-backed at `/opt/mycosoft/media/website/assets`

#### Container mount state
- Bind mount: `/opt/mycosoft/media/website/assets` → `/app/public/assets:ro`

#### HTTP checks (confirmed)
- Origin:
  - `http://localhost:3000/assets/mushroom1/a.mp4` → **200**
  - `http://localhost:3000/assets/mushroom1/Main%20A.jpg` → **200**
- External:
  - `https://sandbox.mycosoft.com/assets/mushroom1/a.mp4` → **200**
  - `https://sandbox.mycosoft.com/assets/mushroom1/Main%20A.jpg` → **200**

### Files/scripts created or updated (repo)
#### Primary runbook
- `docs/NAS_MEDIA_INTEGRATION.md`

#### VM payload script (uploaded to VM)
- `scripts/vm_payloads/setup_nas_website_assets.sh`
  - prompts for SMB username (supports `guest`)
  - prompts for SMB password **only on VM**
  - test-mounts before writing `/etc/fstab`
  - uses `sec=ntlmssp` and prints a CIFS `dmesg` tail on failure

#### VM helper scripts
- `scripts/vm_upload_file.py` (upload payloads safely)
- `scripts/vm_read_file.py` (read remote files)
- `scripts/vm_exec.py` (execute commands via SSH; used for verification)

#### Repo line ending enforcement
- `.gitattributes`

### Staff/agent usage notes
- **Never put large media in git**; put it on the NAS at the correct subfolder path.
- If assets update but browser still shows old versions, **Purge Everything** in Cloudflare.
- If `/assets/*` 404s after new files appear on NAS, recreate the website container (mount propagation).

### References
- Runbook: `docs/NAS_MEDIA_INTEGRATION.md`
