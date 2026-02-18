# Claude CoWork virtiofs Mount Fix (Windows)

**Created:** February 12, 2026  
**Issue:** Sandbox-helper fails to find `/mnt/.virtiofs-root/shared` — virtiofs share not mounting between host and CoWork sandbox.

**Your OS:** Windows 10/11 (build 26200)

---

## Fixes to Try (in order)

### 1. Restart CoWork fully

1. Quit Claude CoWork completely (not just the window — check system tray and Task Manager).
2. In Task Manager, end any `claude-cowork`, `cowork`, or `sandbox-helper` processes if they’re still running.
3. Launch CoWork again and retry.

---

### 2. Check virtualization (required for CoWork’s VM)

CoWork uses a lightweight VM. Virtualization must be on.

**Option A — PowerShell (run as Administrator):**

```powershell
# Check if Hyper-V is available (Windows Pro/Enterprise)
Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V

# Check if WSL2 / virtual machine platform is enabled
Get-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform
Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux
```

If any of these are `Disabled`, enable them:

```powershell
# Enable WSL2 / VM platform (often enough for CoWork)
Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -All
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux -All
# Reboot when prompted
```

**Option B — System Info:**

```powershell
systeminfo | findstr /i "Hyper-V"
```

**BIOS:** If Hyper-V says “A hypervisor has been detected” or you’re on a home SKU, ensure **VT-x (Intel)** or **AMD-V** is enabled in BIOS/UEFI.

---

### 3. Reset CoWork sandbox/cache

Deleting the sandbox data forces CoWork to recreate the VM and virtiofs share.

1. **Close CoWork completely.**

2. **Open the CoWork data folder:**

   ```powershell
   explorer "$env:APPDATA\claude-cowork"
   ```

   If that path doesn’t exist, try:

   ```powershell
   explorer "$env:LOCALAPPDATA\claude-cowork"
   explorer "$env:APPDATA\Anthropic"
   ```

3. **Delete (or rename) these if present:**
   - `sandbox`
   - `cache`
   - `vm`
   - Any folder that looks like VM or sandbox state.

4. **Relaunch CoWork** and try again.

---

### 4. Run CoWork as Administrator (once)

The virtiofs mount point may need admin rights to create the shared directory.

1. Find the CoWork executable (e.g. in `%LOCALAPPDATA%\Programs\claude-cowork\` or where you installed it).
2. Right‑click → **Run as administrator**.
3. Try your workflow again. If it works, the issue is permissions; we can then look at a permanent fix (e.g. shortcut “Run as administrator” or task scheduler).

---

### 5. Update CoWork

This virtiofs error has been improved in newer builds.

- Check for updates inside CoWork (Settings / Help).
- Or reinstall from the latest installer:  
  https://support.claude.ai/hc/en-us/articles/24066365290389-Getting-started-with-Cowork

---

### 6. Antivirus / security software

Temporarily allow or exclude CoWork and its sandbox:

- Add an exclusion for:
  - `%APPDATA%\claude-cowork`
  - `%LOCALAPPDATA%\claude-cowork`
  - The CoWork install directory
- If you use Windows Defender, add these paths to “Exclusions” under Virus & threat protection → Manage settings.

---

## Quick checklist

- [ ] CoWork fully quit and restarted  
- [ ] Virtualization checked (WSL2/VM platform or Hyper-V)  
- [ ] Sandbox/cache under `%APPDATA%\claude-cowork` (or similar) cleared  
- [ ] CoWork run once as Administrator  
- [ ] CoWork updated to latest version  
- [ ] Antivirus exclusions if needed  

---

## If it still fails

Gather this and share it (e.g. with Anthropic support or in a follow-up):

1. **Exact error message** (full text or screenshot).
2. **Where CoWork is installed:**  
   `dir "$env:LOCALAPPDATA\Programs" /s /b | findstr -i cowork`
3. **What exists in AppData:**  
   `dir "$env:APPDATA\claude-cowork" 2>nul & dir "$env:LOCALAPPDATA\claude-cowork" 2>nul`
4. **Virtualization status:**  
   `systeminfo | findstr /i "Hyper-V"`

---

## Reference

- CoWork uses a sandboxed environment and shares a folder via **virtiofs**.
- The error means the sandbox-helper can’t see `/mnt/.virtiofs-root/shared` — usually the virtiofs daemon didn’t start or the shared directory wasn’t created in time.
- Restart, virtualization, resetting sandbox, and running as admin fix most cases on Windows.
