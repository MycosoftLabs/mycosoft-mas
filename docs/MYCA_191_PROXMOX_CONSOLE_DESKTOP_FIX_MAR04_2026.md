# MYCA VM 191 — Proxmox Console Shows Desktop (Not Terminal)

**Date**: March 4, 2026  
**Status**: Implemented  
**Related**: `docs/MYCA_DESKTOP_WORKSTATION_COMPLETE_MAR03_2026.md`

## Problem

When opening the **Proxmox console** for VM 191, only a **text terminal** (tty1) was visible. MYCA needs a **visible desktop** (apps, browser) with the terminal in the background; otherwise she is not working as intended.

## Root Cause

The VM was booting to `multi-user.target` (text mode). No display manager (LightDM/GDM) was installed to run X on the physical/virtual console. The desktop was only available via:

- **XRDP** — separate X session for RDP clients
- **TigerVNC + noVNC** — virtual display `:1` for browser VNC

There was no X session on display `:0` for the Proxmox console.

## Solution

1. **Install LightDM** — display manager that runs X on the console
2. **Set default target** — `graphical.target` so VM boots into GUI
3. **Auto-login** — `mycosoft` logs in automatically, XFCE starts on boot
4. **DISPLAY=:0** — MYCA daemon and GUI apps use the visible console display

## Fix Script

| Script | Purpose |
|--------|---------|
| `scripts/_fix_proxmox_console_191.py` | Installs LightDM, configures auto-login for XFCE on :0. Restarts LightDM (reboot if needed). |

### Run the fix

```bash
cd MAS/mycosoft-mas
python scripts/_fix_proxmox_console_191.py
```

If Proxmox console still shows black: reboot VM 191, then try again.

Requires VM 191 reachable and credentials in `.credentials.local` (or SSH key `~/.ssh/myca_vm191`).

## After Fix

| Method | Result |
|--------|--------|
| **Proxmox console (VNC)** | XFCE desktop, auto-logged in as `mycosoft` |
| **noVNC** http://192.168.0.191:6080 | Still works (TigerVNC display :1) |
| **RDP** 192.168.0.191:3389 | Still works |

MYCA daemon and tools should use `DISPLAY=:0` so Chrome, Cursor, and other GUI apps appear on the visible Proxmox console desktop.

---

## Mouse Clicks Not Working (Console)

### Symptom

In the Proxmox VNC console, the **mouse cursor moves** but **clicks do nothing** (left/right click are ignored).

### Root Cause

VM 191 may boot with a **cloud kernel** (`linux-image-*-cloud-amd64`). This kernel lacks USB drivers. Proxmox uses a virtual USB tablet for mouse input; without USB modules, the tablet receives cursor position via VNC but **cannot handle button events**.

Ref: [Proxmox forum — mouse clicks not working](https://forum.proxmox.com/threads/mouse-clicks-not-working-in-console.148180/)

### Fix

Install the full generic kernel (includes USB drivers) and reboot:

| Script | Purpose |
|--------|---------|
| `scripts/_fix_proxmox_console_mouse_191.py` | Installs `linux-image-generic`, reboots VM 191. After reboot, mouse clicks work. |

```bash
cd MAS/mycosoft-mas
python scripts/_fix_proxmox_console_mouse_191.py
```

- Requires VM 191 reachable; credentials from `.credentials.local` or SSH key `~/.ssh/myca_vm191`
- VM will reboot; wait ~60–90 seconds before using the console again
- If the kernel is not a cloud kernel, script will prompt (use `-y` to skip and install anyway)
