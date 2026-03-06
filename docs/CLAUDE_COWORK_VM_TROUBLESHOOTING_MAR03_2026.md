# Claude Cowork VM — Windows Troubleshooting

**Date:** March 3, 2026 (updated Mar 6)  
**Issues:** VM service not running; connection abort / ECONNRESET / exit code 255; **process already running**  
**Cause:** Known regressions in Claude Desktop v1.1.3189+ (Feb 2026); MSIX installs; API unreachable from VM; stale session state

---

## Error: "process with name already running" (RPC error -1)

**Symptom:** `RPC error -1: process with name "nifty-trusting-gauss" already running (id: ...)` — Cowork won't start or follow-up messages fail.

**Cause:** A previous Cowork VM session did not shut down cleanly. Claude thinks that session is still running and blocks starting a new one. This is a **local state bug**, not a Claude status page outage. [status.claude.com](https://status.claude.com/) shows systems operational.

### Fix (run in order)

1. **Run the dedicated fix script:**
   ```powershell
   cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
   .\scripts\fix-claude-cowork-process-already-running.ps1
   ```
   If the service restart fails, run the script **as Administrator**.

2. **Manual steps** (if script doesn't work):
   - Close Claude Desktop completely
   - Task Manager → Details → End all `Claude.exe` and any `claude-code`, `CoworkVM` processes
   - In **elevated** PowerShell: `Restart-Service CoworkVMService -Force`
   - Delete: `%APPDATA%\Claude\vm_bundles`, `%LOCALAPPDATA%\Claude\claude-code-vm`, `%APPDATA%\Claude\cowork`
   - Reopen Claude Desktop

3. If it persists: force-close and restart Claude 2–3 times; some users report this clears the stale state.

---

## Error: "Connection aborted" / "failed to write data" / exit 255

**Symptom:** `failed to write data: An established connection was aborted by the software in your host machine` → Claude Code process exits with code 255.

**Cause:** ECONNRESET — something on your machine (firewall, antivirus, network stack) is terminating the connection between Claude Desktop and the Cowork VM / Anthropic API.

### Fixes (try in order)

1. **Add firewall rules** (run as Administrator):
   ```powershell
   cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
   .\scripts\fix-claude-cowork-firewall.ps1
   ```

2. **Temporarily disable Windows Defender real-time protection** (Settings → Privacy & Security → Windows Security → Virus & threat protection → Manage settings → Real-time protection Off) and test. If Cowork works, add an exclusion for Claude instead.

3. **Use exe installer** (avoids MSIX and CSP bugs): Uninstall Claude, download Claude-Setup-x64.exe from https://claude.ai/download, install, reboot.

4. **Update Claude Desktop** to the latest version (CSP fix for a-api.anthropic.com was completed in v1.1.x; newer builds may resolve API unreachability).

5. **Check logs** for CSP blocking: `%APPDATA%\Claude\Logs\claude.ai-web.log` — search for "violates" or "CSP". If you see `a-api.anthropic.com` blocked, you need a newer build or the exe install.

---

## Quick Fixes (Try in Order)

### 1. Run the fix script

```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
.\scripts\fix-claude-cowork-vm.ps1
```

### 2. Try non-MSIX install

The MSIX (Microsoft Store–style) install has path-resolution bugs. Use the **exe installer** instead:

1. Uninstall Claude Desktop (Settings → Apps → Claude → Uninstall)
2. Download **Claude-Setup-x64.exe** from https://claude.ai/download (not the MSIX/Store version)
3. Install to a normal path (e.g. `C:\Program Files\Claude`)
4. Reboot and try Cowork again

### 3. Enable Hyper-V (required for Cowork)

Run PowerShell **as Administrator**:

```powershell
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All
Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -All
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux -All
# Reboot after
Restart-Computer
```

### 4. Manually start Cowork VM service

```powershell
Start-Service CoworkVMService
# If it fails, check Event Viewer → Windows Logs → Application
```

### 5. Clear VM bundle and retry

```powershell
# Close Claude Desktop first
Remove-Item -Recurse -Force "$env:APPDATA\Claude\vm_bundles" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\Claude\claude-code-vm" -ErrorAction SilentlyContinue
# Reopen Claude Desktop; it will re-download the VM bundle
```

---

## Root Causes (from GitHub issues)

| Cause | Symptom | Fix |
|-------|---------|-----|
| **Stale session / process already running** | "process with name 'nifty-trusting-gauss' already running", RPC error -1 | Run `fix-claude-cowork-process-already-running.ps1`; kill Claude, restart CoworkVMService, clear vm_bundles |
| **ECONNRESET / connection abort** | "failed to write data", "connection aborted by software in host", exit 255 | Firewall rules, disable Defender temporarily, exe install |
| **CSP blocks a-api.anthropic.com** | VM starts but API unreachable; "violates Content Security Policy" in logs | Update Claude or use exe installer (fixed in newer builds) |
| **MSIX path resolution** | "signature verification initialization failed: failed to get service executable path" | Use exe installer instead of MSIX |
| **NAT / 172.16.0.0 conflict** | VM has no internet; routing conflicts with VPN/home network | [Elliot Segler fix](https://www.elliotsegler.com/fixing-claude-coworks-network-conflict-on-windows.html): create HNS network on different subnet |
| **DCOM permissions** | Event 10016: "do not grant Local Activation permission for COM Server" | Run Claude as admin once, or disable/re-enable Hyper-V |
| **EXDEV rename** | "EXDEV: cross-device link not permitted, rename rootfs.vhdx" | Ensure TEMP and APPDATA are on same drive |
| **yukonSilver unsupported** | "VM not supported (win32/x64), skipping" on Build 26200 | Known on Insider builds; wait for Anthropic fix |

---

## Diagnostics

Check these if fixes above don't work:

```powershell
# Cowork VM service status
Get-Service CoworkVMService -ErrorAction SilentlyContinue

# Hyper-V status
Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V | Select State
Get-Service vmcompute, vmms | Format-Table Name, Status

# Logs (run Claude, try Cowork, then check)
Get-Content "$env:APPDATA\Claude\Logs\cowork-service.log" -Tail 50
Get-Content "$env:APPDATA\Claude\Logs\cowork_vm_node.log" -Tail 50
```

---

## Related

- [GitHub #27801](https://github.com/anthropics/claude-code/issues/27801) — VM service not running
- [GitHub #29941](https://github.com/anthropics/claude-code/issues/29941) — MSIX path resolution failure
- [MYCOSOFT_SSH_MCP_MAR03_2026.md](./MYCOSOFT_SSH_MCP_MAR03_2026.md) — mycosoft-ssh MCP for VM access (when Cowork works)
