# Sandbox VM Unreachable – Status (Mar 2, 2026)

**Date:** 2026-03-02  
**Status:** Resolved – 187 was off; once back on, deploy was run (build may have completed in background).  
**Action:** Use `docs/SANDBOX_AND_PRODUCTION_ALWAYS_ON_MAR02_2026.md` so Sandbox and production never stay off.

## What was done

- **SSH from dev PC:** MAS (192.168.0.188) is reachable (SSH + plink with hostkey). Sandbox (192.168.0.187) times out / no route.
- **SSH from MAS to Sandbox:** From 188, `ping 192.168.0.187` returns **Destination Host Unreachable** (100% packet loss). So 187 is unreachable from both the dev machine and from MAS.
- **Deploy script:** `_complete_deploy_sandbox.py` was run; it fails with `ChannelException(2, 'Connect failed')` / "No route to host" because direct SSH to 187 fails and the jump-host channel (188→187) also fails when 188 tries to connect to 187.
- **Rule updated:** `.cursor/rules/agent-must-execute-operations.mdc` now states that the agent has **full SSH capability**, must run deploy/tunnel/SSH itself, and must not ask the user to run these steps.

## Blocker

**Sandbox VM 192.168.0.187 is not reachable on the network** from:

- Dev PC (192.168.0.172)
- MAS VM (192.168.0.188)

So the agent cannot SSH to 187 to restart `cloudflared` or run the website deploy until 187 is back on the network.

## When 187 is reachable again

1. **Restart tunnel (fix 1033):** Run from website repo:
   - `python scripts/_restart_sandbox_tunnel.py`
   - Or SSH to 187 and run: `sudo systemctl restart cloudflared` (and `cloudflare-tunnel` if present).
2. **Deploy latest code:** Run from website repo:
   - Load creds from `MAS/mycosoft-mas/.credentials.local`, then:
   - `python _complete_deploy_sandbox.py`
   - (Script pulls on 187, builds image, restarts container with NAS mount, purges Cloudflare.)
3. **Verify:** Open https://sandbox.mycosoft.com and https://sandbox.mycosoft.com/natureos/devices.

## Likely causes for unreachable 187

- Sandbox VM powered off or suspended (Proxmox/host).
- Network: 187 on different VLAN/subnet, or firewall blocking 187.
- NIC down or wrong IP on 187.
- UniFi/switch config changed.

## Resolved / Follow-up

- **187 was off** (VM not running). Once 187 was back on the network, deploy was run; the Docker build can take 10–15+ minutes and may have completed in the background after the 5-minute script timeout.
- **Why it must not happen for production:** See **`docs/SANDBOX_AND_PRODUCTION_ALWAYS_ON_MAR02_2026.md`** – root causes (VM not set to start on boot, tunnel not enabled at boot) and a **production clone checklist** so Sandbox and any mycosoft.com production VM never stay off after a host reboot.

## References

- **Always-on and production checklist:** `docs/SANDBOX_AND_PRODUCTION_ALWAYS_ON_MAR02_2026.md`
- VM layout: `docs/VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md`
- Deploy pipeline: `docs/DEV_TO_SANDBOX_PIPELINE_FEB06_2026.md`
- Credentials: `.credentials.local` (MAS repo); never commit; agent loads and uses for SSH.
