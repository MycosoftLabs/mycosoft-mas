# Provision MycoDAO Pulse VM on Proxmox (Ubuntu 24.04 cloud-init).
# Loads MAS .credentials.local then runs Python provisioner.
#
# Usage (from repo root):
#   .\scripts\provision-mycodao-pulse-vm.ps1
#   .\scripts\provision-mycodao-pulse-vm.ps1 -DryRun
#
# Prerequisites: Python 3, paramiko (via poetry/pip as for other MAS scripts).
# Secrets: PROXMOX_PASSWORD / PROXMOX202_PASSWORD / VM_PASSWORD — never commit.

param(
    [switch] $DryRun,
    [switch] $Recreate
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

$credsFile = Join-Path $root ".credentials.local"
if (Test-Path $credsFile) {
    Get-Content $credsFile | ForEach-Object {
        if ($_ -match "^([^#=]+)=(.*)$") {
            $k = $matches[1].Trim()
            $v = $matches[2].Trim()
            if (-not [string]::IsNullOrEmpty($k)) {
                [Environment]::SetEnvironmentVariable($k, $v, "Process")
            }
        }
    }
}

$args = @("scripts\provision_mycodao_pulse_vm.py")
if ($DryRun) { $args += "--dry-run" }
if ($Recreate) { $args += "--recreate" }

& python @args
exit $LASTEXITCODE
