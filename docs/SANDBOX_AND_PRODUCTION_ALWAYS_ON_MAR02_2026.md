# Sandbox and Production Always-On – Why Sandbox Was Off and How to Prevent It (Mar 2, 2026)

**Date:** 2026-03-02  
**Status:** Guidance  
**Related:** `SANDBOX_UNREACHABLE_STATUS_MAR02_2026.md`, `DEV_TO_SANDBOX_PIPELINE_FEB06_2026.md`, `VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md`

---

## Why Sandbox (187) Was Off

Sandbox VM **192.168.0.187** was unreachable from both the dev PC and MAS (188). The most likely causes:

1. **VM not set to start on boot** – After a Proxmox/host reboot or power cycle, the Sandbox VM may not be configured to start automatically. If "Start on boot" is disabled, 187 stays off until someone starts it manually.
2. **Host reboot or power loss** – The Proxmox host (or the physical machine hosting 187) was restarted or lost power; if 187 isn’t set to auto-start, it stays down.
3. **Manual stop** – The VM was stopped for maintenance and not restarted, or a script/tool stopped it.
4. **Resource or crash** – Less likely: the VM crashed or was shut down by the host (e.g. out-of-memory). Still results in "off" until the VM is started again.

So **“Sandbox was off”** = the VM (187) was not running. That should never be acceptable for production when you clone this setup for **mycosoft.com**.

---

## Why This Must Never Happen for Production (mycosoft.com)

If you clone the Sandbox setup for **production** (mycosoft.com):

- The production site must be **always on**. Downtime = users see errors and loss of trust.
- The same causes (no auto-start, host reboot, manual stop) would take production down.
- So the same **always-on** and **auto-start** measures that apply to Sandbox must be **required** for the production VM (and any clone).

---

## Checklist: Sandbox and Production Clone (so it never stays off)

Use this for **Sandbox (187)** and for **any production clone** (e.g. VM for mycosoft.com).

### 1. Proxmox (or host) – VM start on boot

- [ ] In Proxmox (or your hypervisor), set the **Sandbox VM (187)** to **Start on boot** / **Start at boot**.
- [ ] For production: set the **production website VM** to **Start on boot** as well.
- [ ] After a host reboot, confirm the VM(s) come up (e.g. wait 2–5 minutes, then ping or SSH).

### 2. Inside the VM – cloudflared (tunnel) starts on boot

- [ ] On 187 (and on production clone):  
  `sudo systemctl enable cloudflared`  
  (and `cloudflare-tunnel` if that’s the service name).
- [ ] Ensure the tunnel service starts after reboot:  
  `sudo systemctl start cloudflared`  
  then check:  
  `systemctl is-active cloudflared`.
- [ ] Optional: add a small cron or systemd timer that checks tunnel health and restarts it if needed.

### 3. Inside the VM – Docker website container starts on boot

- [ ] The website container is run with `--restart unless-stopped`. So once the VM is up and Docker is running, the container should start.
- [ ] Ensure Docker daemon starts on boot (default on most VMs):  
  `sudo systemctl enable docker`.
- [ ] After a VM reboot, verify:  
  `docker ps` shows `mycosoft-website` (or your production container name) running.

### 4. Optional: Lightweight monitoring

- [ ] Use a simple heartbeat (e.g. MAS or external cron) that hits `https://sandbox.mycosoft.com/health` (or production URL) and alerts if down.
- [ ] Optionally, use Proxmox or host-level alerts if the VM stops unexpectedly.

---

## Quick verification after any host/VM reboot

1. **Ping or SSH** to 187 (or production VM):  
   `ping 192.168.0.187` or `ssh mycosoft@192.168.0.187`.
2. **Tunnel** – Open https://sandbox.mycosoft.com (or production URL); no 1033 or connection errors.
3. **Container** – On the VM: `docker ps` and confirm the website container is running.

---

## References

- VM layout and dev remote: `docs/VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md`
- Deploy pipeline: `docs/DEV_TO_SANDBOX_PIPELINE_FEB06_2026.md`
- Sandbox unreachable status: `docs/SANDBOX_UNREACHABLE_STATUS_MAR02_2026.md`
- Tunnel restart script: `WEBSITE/website/scripts/_restart_sandbox_tunnel.py`
- Full deploy script: `WEBSITE/website/_complete_deploy_sandbox.py`
