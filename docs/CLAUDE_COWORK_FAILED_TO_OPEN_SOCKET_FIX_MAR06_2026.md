# Claude Cowork FailedToOpenSocket Fix (Mar 6, 2026)

**Date**: March 6, 2026  
**Status**: Complete  
**Related**: [CLAUDE_DESKTOP_SCHEDULE_BACKUP_RESTORE_MAR03_2026.md](./CLAUDE_DESKTOP_SCHEDULE_BACKUP_RESTORE_MAR03_2026.md)

## Overview

`API Error: Unable to connect to API (FailedToOpenSocket)` on Claude Desktop Cowork means the Cowork VM **cannot open a TCP socket** to `api.anthropic.com`. This is a **Windows Cowork VM networking bug** — the host can reach the API, but the VM cannot. Root cause: the VM inherits **DNS from a disconnected network adapter** instead of your active Wi‑Fi/Ethernet, so it never resolves the hostname and the connection fails.

## Quick Diagnosis (Admin PowerShell)

Run these to confirm this is your issue:

```powershell
# 1. What DNS is the Cowork VM endpoint using?
Get-HnsEndpoint | Where-Object { $_.Name -like "cowork*" } | Format-List Name, IPAddress, GatewayAddress, DNSServerList

# 2. What DNS does your active connection use? (Wi‑Fi or Ethernet)
Get-DnsClientServerAddress -InterfaceAlias "Wi-Fi" | Select ServerAddresses
# OR
Get-DnsClientServerAddress -InterfaceAlias "Ethernet" | Select ServerAddresses

# 3. List all adapters — look for disconnected ones
Get-NetAdapter | Format-Table Name, InterfaceDescription, Status -AutoSize

# 4. Check DNS per adapter
Get-NetIPConfiguration | Select InterfaceAlias, @{N='DNS';E={$_.DNSServer.ServerAddresses}} | Format-Table -AutoSize
```

**If** `DNSServerList` on the Cowork endpoint is empty, wrong (e.g. `192.168.x.x`), or different from your Wi‑Fi/Ethernet DNS → this fix applies.

---

## Fix: Option A — Align DNS on Disconnected Adapters (Recommended)

If you have a **disconnected** Ethernet/USB/VPN adapter with bad DNS, Cowork may use it. Fix by making that adapter’s DNS match your active one.

**All commands in Admin PowerShell.**

### 1. Identify the bad adapter

```powershell
Get-NetAdapter | Format-Table Name, Status -AutoSize
# Find disconnected adapters, e.g. "Ethernet", "Ethernet 2", "Fortinet SSL VPN", etc.

# Check DNS on each
Get-DnsClientServerAddress -InterfaceAlias "Ethernet" | Select ServerAddresses
```

### 2. Set that adapter’s DNS to good public DNS (1.1.1.1, 8.8.8.8)

```powershell
# Enable adapter temporarily if disabled
Enable-NetAdapter -Name "Ethernet" -ErrorAction SilentlyContinue

# Set DNS — replace "Ethernet" with YOUR disconnected adapter name
Set-DnsClientServerAddress -InterfaceAlias "Ethernet" -ServerAddresses "1.1.1.1","8.8.8.8"

# Disable again if you don't use it
Disable-NetAdapter -Name "Ethernet" -Confirm:$false
```

### 3. Remove Cowork HNS network and endpoints (forces clean rebuild)

```powershell
Get-HnsEndpoint | Where-Object { $_.Name -like "cowork*" } | Remove-HnsEndpoint
Get-HnsNetwork | Where-Object { $_.Name -like "cowork*" } | Remove-HnsNetwork
```

### 4. Fully quit Claude

```powershell
taskkill /F /IM Claude.exe /T
```

### 5. Reopen Claude and launch Cowork

The VM will rebuild with correct DNS. Test Cowork again.

---

## Fix: Option B — Disable Bad Adapters + SharedAccess + Reboot

Use if Option A doesn’t help or you prefer a harder reset.

### 1. Disable the disconnected adapter

```powershell
Disable-NetAdapter -Name "Ethernet" -Confirm:$false
# Replace "Ethernet" with your adapter name
```

### 2. Disable SharedAccess (ICS) — can conflict with Hyper‑V NAT

```powershell
Stop-Service SharedAccess -Force
Set-Service SharedAccess -StartupType Disabled
```

### 3. Remove Cowork HNS resources

```powershell
Get-HnsEndpoint | Where-Object { $_.Name -like "cowork*" } | Remove-HnsEndpoint
Get-HnsNetwork | Where-Object { $_.Name -like "cowork*" } | Remove-HnsNetwork
```

### 4. Reboot

```powershell
Restart-Computer
```

### 5. After reboot

Open Claude Desktop and launch Cowork again.

---

## Fix: Option C — No Adapter Changes (HNS Cleanup Only)

**Use this if you will NOT modify Ethernet adapters.** Run as Administrator.

### 1. Run the no-adapter fix script

```powershell
# From MAS repo — MUST run as Administrator
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
.\scripts\_cowork_fix_no_adapters.ps1
```

This script: stops **CoworkVMService** (correct name), kills Claude, kills the cowork VM via `hcsdiag`, removes Cowork HNS endpoints/networks, then **restarts CoworkVMService**. **It does NOT change DNS or any adapter.**

### 2. Update Claude or Repair

- **Update** (recommended): Download latest from [claude.ai/download](https://claude.ai/download). Anthropic fixed networking issues in v1.1.4328+ ([GitHub #28516](https://github.com/anthropics/claude-code/issues/28516)).
- **Repair**: Settings → Apps → Installed apps → Claude → Advanced options → **Repair**
- **Reset** (if Repair fails): Same path → **Reset** — will require sign-in again.

### 3. Reopen Claude and launch Cowork

---

## "VM service not running. The service failed to start."

This error means the **CoworkVMService** (DisplayName: Claude) failed to start. Common causes:

1. **Race condition** — Claude connects before the service is ready. Fix: run `_cowork_fix_no_adapters.ps1`, wait 5 seconds, then open Claude.
2. **Corrupted VM state** — HNS or Hyper-V compute state is stuck. Fix: Repair or Reinstall (Option D).
3. **MSIX / Windows Store install** — Some MSIX installs have different service behavior. Fix: Repair from Settings → Apps → Claude → Advanced options → **Repair**.

**Verify service:** `Get-Service CoworkVMService` — should show Status: Running. If Stopped and won't start, use Repair or Reinstall.

---

## HCS operation failed: 0x800707de / Construct (Mar 11, 2026)

**Symptom:** Cowork VM fails with:

```
HCS operation failed: failed to create compute system: HcsWaitForOperationResult failed with HRESULT 0x800707de
{"Error":-2147022882,"ErrorMessage":"","Attribution":[{"OperationFailure":{"Detail":"Construct"}}]}
```

This is a Windows Host Compute Service (HCS) failure during VM construction. Common causes:

1. **NTFS compression** – VHDX files must be uncompressed; Hyper-V rejects compressed disks.
2. **Stale HNS/VM state** – Leftover HNS networks and HCS registration from failed attempts.
3. **Hyper‑V service state** – vmcompute or vmms stuck.

**Fix (NO adapter changes):**

### Step 1: Check and disable NTFS compression

If your C: drive has "Compress this drive to save disk space" enabled, VHDX files inherit compression and Hyper‑V fails.

```powershell
# Check if Claude package dir is compressed
Get-ChildItem "$env:LOCALAPPDATA\Packages" -Directory | Where-Object { $_.Name -like "Claude*" } | ForEach-Object {
  (Get-Item $_.FullName -Force).Attributes  # Look for Compressed
}

# Decompress the Claude package directory (run as Admin)
$claudePkg = (Get-ChildItem "$env:LOCALAPPDATA\Packages" -Directory | Where-Object { $_.Name -like "Claude*" }).FullName
if ($claudePkg) { compact /u /s:"$claudePkg" *.* }
```

Also: Right‑click C: drive → Properties → **uncheck** "Compress this drive to save disk space" if it’s enabled.

### Step 2: Run the fix script (HNS + VM cleanup + Hyper‑V restart)

```powershell
# Run as Administrator
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
.\scripts\_cowork_fix_no_adapters.ps1
```

The script now restarts vmcompute and vmms in addition to HNS cleanup.

### Step 3: Repair or Reinstall Claude

- **Repair:** Settings → Apps → Claude → Advanced options → **Repair**
- **Reinstall:** Uninstall, delete `%AppData%\Claude` and `%LocalAppData%\Packages\Claude*`, reboot, then reinstall from [claude.ai/download](https://claude.ai/download)

**Reference:** [anthropics/claude-code #25914](https://github.com/anthropics/claude-code/issues/25914) – HCS 0x800707de and NTFS compression fix.

---

## "Plan9 mount failed: bad address" / virtiofs Spawn Failed (Mar 10, 2026)

**Symptom:** Cowork VM connects, but spawn fails with:

```
Spawn failed: RPC error -1: failed to ensure virtiofs mount: Plan9 mount failed: bad address
```

This happens when Cowork mounts workspace folders into the VM via virtiofs/Plan9. Stale or corrupt VM bundle/temp cache causes the mount step to fail.

**Fix (NO adapter changes):** Run the script — it now deletes `vm_bundles` and `claude-code-vm` to force a fresh VM runtime download:

```powershell
# Run as Administrator
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
.\scripts\_cowork_fix_no_adapters.ps1
```

The script also deletes `%TEMP%\claude` and clears HNS. **First Cowork launch after the fix will re-download the VM bundle** (~500MB) — that's expected.

**If still failing:** Try opening Cowork with a **single folder** instead of the multi-root workspace (17 folders). If that works, the project path or folder count may be causing the failure — consider moving the project to `C:\Work\Project` or simplifying the workspace.

---

## Fix: Option E — Full DNS + HNS Cleanup (Ethernet-only / Multi-adapter)

**Use when:** Cowork still fails after Option A–C, or you use Ethernet only (no Wi‑Fi) with multiple adapters. This script sets DNS on **all** adapters, disables SharedAccess (ICS), and forces a full Cowork VM rebuild.

### 1. Run the full fix script (Admin PowerShell)

```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
.\scripts\_cowork_fix_dns_all_adapters.ps1
```

**What it does:**
- Sets DNS (1.1.1.1, 8.8.8.8) on all adapters; keeps gateway DNS (e.g. 192.168.0.1) on active Ethernet
- Stops CoworkVMService, kills Claude, deletes vm_bundles and claude-code-vm
- Disables SharedAccess (ICS) — can conflict with Hyper‑V NAT
- Kills cowork VM, restarts vmcompute and vmms, removes HNS and cowork NetNat
- Restarts CoworkVMService

**Note:** If you use Internet Connection Sharing, re-enable SharedAccess afterward:
```powershell
Set-Service SharedAccess -StartupType Automatic
Start-Service SharedAccess
```

### 2. Repair Claude (required)

- **Settings** → **Apps** → **Installed apps** → **Claude** → **⋮** → **Advanced options** → **Repair**
- Or **Reset** if Repair fails (clears local data, requires sign-in again)

### 3. Reopen Claude and launch Cowork

---

## Fix: Option D — Claude Repair/Reset (Last Resort)

As a last resort, force a full Cowork VM rebuild:

1. **Settings → Apps → Installed apps → Claude → Advanced options**
2. **Repair** (or **Reset** if Repair fails)
3. Reopen Claude and sign in again
4. Launch Cowork

**Reinstall**: If Repair and Reset both fail, uninstall Claude and reinstall from [claude.ai/download](https://claude.ai/download).

Your **schedules are preserved** if you ran the backup script first; use the restore script afterward if needed.

---

## Verify the Fix

After applying a fix:

```powershell
# VM should now have correct DNS
Get-HnsEndpoint | Where-Object { $_.Name -like "cowork*" } | Format-List Name, DNSServerList
# DNSServerList should match 1.1.1.1, 8.8.8.8 or your Wi‑Fi DNS
```

---

## Moving Cowork to a VM Later

Once Cowork works on this PC, you can plan a move to a dedicated VM. That VM will need:

- Hyper‑V or equivalent for the Cowork VM service
- Stable internet and correct DNS
- No competing VPN/virtual adapters affecting routing

This doc fixes the current PC so you can validate Cowork before migrating.

---

## References

- [anthropics/claude-code #28516](https://github.com/anthropics/claude-code/issues/28516) — Networking issues fixed in v1.1.4328; update or reinstall recommended
- [anthropics/claude-code #25144](https://github.com/anthropics/claude-code/issues/25144) — Cowork VM uses DNS from disconnected adapter (closed, workaround confirmed)
- [anthropics/claude-code #24918](https://github.com/anthropics/claude-code/issues/24918) — Root cause analysis, Microsoft Wi‑Fi Direct Virtual Adapter
- [anthropics/claude-code #26567](https://github.com/anthropics/claude-code/issues/26567) — ECONNRESET / API unreachable (duplicate)
