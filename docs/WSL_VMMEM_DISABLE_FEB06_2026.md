# WSL / vmmem Disable and Memory Fix – February 6, 2026

## Where did this VM come from? Why is it on this machine and not Proxmox?

**Short answer:** The “VM” (vmmem) is **WSL2** — a **Windows feature**. It only exists on this PC because it’s part of Windows. It isn’t something we “put here instead of Proxmox”; Proxmox runs on the server and is a different system.

| | This Windows PC | Proxmox (e.g. 192.168.0.187) |
|--|------------------|------------------------------|
| **What** | Your dev machine (Windows 11) | Server that runs real VMs (Ubuntu, etc.) |
| **WSL / vmmem** | Can exist here (Windows feature) | Does not exist; Proxmox doesn’t use WSL |
| **Our VMs** | None (we use Proxmox for VMs) | Sandbox, MINDEX, MAS, Docker, etc. |

**How WSL usually ends up on this machine:**

1. **Docker Desktop** – When you install Docker Desktop on Windows, it often enables and uses **WSL 2** as its backend. That turns on the WSL2 “VM” (vmmem) on this PC.
2. **Optional features** – Someone (or an app) may have enabled **“Windows Subsystem for Linux”** and **“Virtual Machine Platform”** in Windows (Settings → Apps → Optional features). That installs WSL.
3. **Store / `wsl --install`** – Installing a Linux distro from the Microsoft Store (e.g. Ubuntu) or running `wsl --install` also installs WSL on this machine.

So the VM (vmmem) is here **because Windows has WSL enabled on this PC**, not because we chose to run a “dev VM” here instead of on Proxmox. Real workloads (website, MINDEX, MAS, services) run on **Proxmox VMs**. WSL is just a local Windows convenience (e.g. Linux CLI or Docker); we don’t need it for Earth2, GPU, or Mycosoft app code.

---

## What is vmmem?

**vmmem** is the Windows process for the **WSL2 (Windows Subsystem for Linux)** virtual machine. When WSL2 is installed and has been used (e.g. Docker Desktop, Ubuntu, or any WSL distro), this VM can stay running and use **a large share of system RAM** (often 50% or more by default), which slows the whole machine.

- **vmmem** = WSL2 backend VM process (high RAM use).
- **Earth2 / GPU / Omniverse** on this dev box run **natively on Windows** (Python, Node, RTX 5090). They do **not** use WSL.
- **Proxmox** is used for server VMs; there is **no need for GPU passthrough or Omniverse via WSL** on this machine.

So if you are not actively using WSL (e.g. a Linux shell or Docker), shutting down WSL and limiting it when you do use it will free memory and reduce slowness.

---

## Quick fix (free memory now)

Run in **PowerShell** (no admin required):

```powershell
wsl --shutdown
```

Within a few seconds, **vmmem** should exit and release RAM. You can run this anytime the machine feels slow.

Or use the script:

```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\scripts
.\shutdown-wsl-free-vmmem.ps1
```

---

## Limit WSL memory so vmmem never hogs RAM again

When WSL does run, you can cap its memory so vmmem stays small.

1. **Copy the config file** into your user profile:
   - From repo: `mycosoft-mas\scripts\.wslconfig`
   - To: `C:\Users\admin2\.wslconfig`

   In PowerShell:
   ```powershell
   Copy-Item "C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\scripts\.wslconfig" "$env:USERPROFILE\.wslconfig"
   ```

2. **Apply the config** (shutdown WSL so next start uses new limits):
   ```powershell
   wsl --shutdown
   ```

3. Next time you start WSL (e.g. open “Ubuntu” or start Docker Desktop), WSL2 will use at most **4GB** RAM (and 4 CPUs, 1GB swap) instead of half the machine.

---

## Optional: Disable WSL completely

If you do **not** use WSL at all (no Docker Desktop WSL2 backend, no Linux distros):

1. Open **PowerShell as Administrator**.
2. Run:
   ```powershell
   wsl --shutdown
   dism.exe /Online /Disable-Feature /FeatureName:Microsoft-Windows-Subsystem-Linux /NoRestart
   dism.exe /Online /Disable-Feature /FeatureName:VirtualMachinePlatform /NoRestart
   ```
3. Restart the PC when prompted.

After this, **vmmem will not run**. Re-enable later from **Settings → Apps → Optional features** if you need WSL again.

**Note:** If you use **Docker Desktop** with the “WSL 2 based engine”, disabling WSL will break that. Prefer the “Quick fix” and “Limit WSL memory” steps above instead.

---

## Earth2 and GPU (no WSL required)

From the project docs:

- **Earth2Studio** runs on Windows in `C:\Users\admin2\.earth2studio-venv` (Python, CUDA, RTX 5090).
- **Local GPU services** (Earth2 API, PersonaPlex, GPU Gateway) are started by `scripts/start-with-gpu.js` / `local_gpu_services.py` — **native Windows**, no WSL.
- **GPU passthrough** in the repo is for **Proxmox** (future server GPU), not for this dev machine.
- **Omniverse** is not used via WSL on this machine; passthrough is not required here.

So disabling or limiting WSL does **not** affect Earth2 or local GPU work.

---

## Scripts and files

| Item | Purpose |
|------|---------|
| `scripts/shutdown-wsl-free-vmmem.ps1` | Shutdown WSL to free vmmem memory |
| `scripts/.wslconfig` | Example WSL2 memory/CPU limits (copy to `%USERPROFILE%\.wslconfig`) |
| `docs/WSL_VMMEM_DISABLE_FEB06_2026.md` | This document |

---

## Summary

| Goal | Action |
|------|--------|
| Free memory right now | Run `wsl --shutdown` or `.\shutdown-wsl-free-vmmem.ps1` |
| Keep WSL but stop it using too much RAM | Copy `.wslconfig` to `%USERPROFILE%\.wslconfig`, then `wsl --shutdown` |
| Never run WSL (no Docker WSL2 / no Linux) | Disable “Windows Subsystem for Linux” and “Virtual Machine Platform” (optional features) |

Earth2 and local GPU workflows do not depend on WSL; fixing vmmem will not break them.
