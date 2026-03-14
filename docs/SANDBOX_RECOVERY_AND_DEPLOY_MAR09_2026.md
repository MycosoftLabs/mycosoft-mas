# Sandbox Recovery and Full Deploy — Mar 9, 2026

**Status:** Complete (tunnel fix pending)  
**Related:** Cloudflare error 1033, VM 187 Sandbox, MASTER_DEPLOY, MAS 188, MINDEX 189

---

## Summary

Sandbox VM was down (Cloudflare error 1033 / 530); user restarted it in Proxmox. Recovery and deployment were executed:

- **Website (Sandbox 187):** Deployed via MASTER_DEPLOY; container healthy, HTTP 200 on port 3000, NAS media mount OK
- **MAS (188):** Code pulled, mas-orchestrator restarted; health 200
- **MINDEX (189):** Code pulled, mindex-api restarted; health 200

**Remaining:** Cloudflare Tunnel (cloudflared) on Sandbox is failing. `sandbox.mycosoft.com` returns 530 until the tunnel is fixed.

---

## Actions Taken

### 1. Tunnel Restart Script

- Fixed `scripts/_restart_sandbox_tunnel.py` for Windows Unicode (replace bullets, `errors="replace"` on decode)
- Ran script: cloudflared systemd service is in **auto-restart loop** with exit code 1
- Docker container `mycosoft-tunnel` does not exist on Sandbox (tunnel runs via systemd)
- `docker-compose.production.yml` path on Sandbox is different; Sandbox uses `docker-compose.always-on.yml`

### 2. Website Deploy (MASTER_DEPLOY)

- VM connectivity verified
- Git pull had encoding noise but deploy continued
- Caches cleaned, image built, container started
- Container: `mycosoft-website` Up, healthy
- Local HTTP 200, video endpoint 200, NAS mount OK
- Cloudflare purge: 401 (API token invalid or missing)
- sandbox.mycosoft.com: 530 (tunnel down)

### 3. MAS and MINDEX Deploy

- Created `scripts/_deploy_mas_mindex_quick.py` (paramiko-based)
- MAS: git reset to `dfe2aa43`, mas-orchestrator restarted
- MINDEX: git reset to `dc7d9aa`, mindex-api restarted
- Health checks: 200 for both

---

## Cloudflare Tunnel Diagnosis

| Item | Value |
|------|-------|
| Service | `cloudflared.service` (systemd) |
| Status | `activating (auto-restart)`, exit code 1 |
| Token | Embedded in systemd unit (ExecStart) |
| Container | `mycosoft-tunnel` not present |

**Likely causes:** Expired tunnel token, network/DNS, or cloudflared version mismatch.

### How to Fix

1. **Regenerate tunnel token** in Cloudflare Zero Trust dashboard  
   - Networking → Tunnels → Select Sandbox tunnel → Configure → Token  
   - Create new token and copy it

2. **Update systemd unit on Sandbox:**
   ```bash
   sudo nano /etc/systemd/system/cloudflared.service
   # Replace the token in ExecStart=... --token <NEW_TOKEN>
   sudo systemctl daemon-reload
   sudo systemctl restart cloudflared
   ```

3. **Check logs:**
   ```bash
   journalctl -u cloudflared -n 50 --no-pager
   ```

4. **Optional:** Use Docker tunnel instead of systemd (see `docker-compose.production.yml`), but Sandbox currently uses systemd.

---

## Proxmox and Sandbox Stability

**Recommendation:** Ensure Sandbox VM (103) starts before or has higher priority than C-suite VMs that may consume resources.

- Sandbox IP: 192.168.0.187  
- Proxmox VM ID: 103  
- Consider: increase startup order, resource limits, or boot dependencies

---

## Verification Commands

```powershell
# Sandbox website (local, bypasses tunnel)
Invoke-WebRequest -Uri http://192.168.0.187:3000 -UseBasicParsing | Select-Object StatusCode

# MAS
Invoke-WebRequest -Uri http://192.168.0.188:8001/health -UseBasicParsing | Select-Object StatusCode

# MINDEX
Invoke-WebRequest -Uri http://192.168.0.189:8000/health -UseBasicParsing | Select-Object StatusCode

# Public (requires working tunnel)
Invoke-WebRequest -Uri https://sandbox.mycosoft.com -UseBasicParsing | Select-Object StatusCode
```

---

## Files Touched

| File | Change |
|------|--------|
| `WEBSITE/website/scripts/_restart_sandbox_tunnel.py` | Unicode handling, `errors="replace"` |
| `MAS/scripts/_deploy_mas_mindex_quick.py` | New quick deploy script for 188/189 |

---

## Next Steps

1. Fix cloudflared (regenerate token, update systemd unit).
2. Purge Cloudflare cache manually if `CLOUDFLARE_API_TOKEN` is not set.
3. Review Proxmox startup order for Sandbox vs C-suite VMs.
