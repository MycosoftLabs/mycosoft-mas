# Disable VMware on Local Dev Machine – February 6, 2026

## Purpose

Mycosoft runs all VMs on **Proxmox servers**. VMware should not run on the local Windows dev machine. It uses memory and CPU and can make the dev environment slow.

This doc and script ensure VMware is turned off and does not start again.

---

## Quick steps

### 0. Close VMware app and stop its processes (do this first)

If VMware is running, close it and stop leftover processes:

1. **Close VMware Workstation** from the taskbar or File → Exit.
2. In **PowerShell (Run as Administrator)** run once to stop all VMware-related processes:

```powershell
Get-Process | Where-Object { $_.ProcessName -match "vmware|vmnat|vmnet|vmount|vmvga" } | Stop-Process -Force
```

After this, VMware will not be running. To prevent it from starting again, do step 1 and 2 below.

### 1. Run the disable script (as Administrator)

1. Right-click **PowerShell** → **Run as administrator**.
2. Run:

```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\scripts
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
.\disable-vmware-services.ps1
```

If you get “cannot be loaded because running scripts is disabled”, use:

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\scripts\disable-vmware-services.ps1"
```

### 2. If VMware Workstation is open

- Close **VMware Workstation** from the system tray or from the app.
- Do not start it again; use Proxmox for VMs.

### 3. Optional: remove from startup

- **Settings → Apps → Startup**  
  Turn off any **VMware** or **VMware Workstation** entry.
- Or run `shell:startup` and remove VMware shortcuts if present.

---

## Services the script disables

| Service name (typical) | Purpose |
|------------------------|--------|
| VMAuthdService         | VMware Authorization |
| VMUSBArbService        | VMware USB |
| VMnetDHCP              | VMware DHCP |
| VMware NAT Service     | VMware NAT |
| VMwareHostOpen         | VMware Host |
| VGAuthService          | VMware Guest Auth |

The script also disables any service whose **Display name** contains “VMware”.

---

## After running

- VMware will **not** start automatically at boot.
- To use VMs, use **Proxmox** (e.g. 192.168.0.187 sandbox, other Proxmox hosts).
- Re-enabling VMware later: in **Services** (`services.msc`), set the desired VMware services to **Manual** or **Automatic** and start them (not recommended for this dev box).

---

## Reference

- **Proxmox / sandbox VM:** 192.168.0.187 (and other Proxmox hosts).
- **This script:** `scripts/disable-vmware-services.ps1`
- **Doc date:** Feb 6, 2026
