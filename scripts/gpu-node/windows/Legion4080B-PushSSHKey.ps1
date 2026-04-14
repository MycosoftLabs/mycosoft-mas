#Requires -Version 5.1
<#
.SYNOPSIS
  Push this dev PC's id_ed25519.pub to Legion 4080B (voice / 192.168.0.241) for key-based SSH — same pattern as 4080A.

.DESCRIPTION
  - Ensures PuTTY plink is used (fast, reliable on Windows).
  - If you omit -PlinkHostKey, the script runs plink once, reads the SHA256 fingerprint from the "host key is not cached" message, then runs the key install.
  - Updates both ~/.ssh/authorized_keys and ProgramData\ssh\administrators_authorized_keys when the account is an Administrator.

.PARAMETER Password
  Windows password for the remote user (default owner1). Prefer passing a SecureString in a constrained run.

.PARAMETER PlinkHostKey
  Optional. Format: SHA256:xxxx... If omitted, auto-discovery is attempted (requires 4080B online and password correct).

.EXAMPLE
  Set-Location ~\Desktop\scripts   # or your folder containing this + Push-SSHKey-To-Host.ps1
  .\Legion4080B-PushSSHKey.ps1 -Password 'YourPasswordHere'

.EXAMPLE
  .\Legion4080B-PushSSHKey.ps1 -Password '...' -PlinkHostKey 'SHA256:AbCdEf+gHiJ...'

.NOTES
  After success, use: ssh owner1@192.168.0.241 hostname
  Update ~/.ssh/config Host ubiquity-gpu-voice to IdentityFile ~/.ssh/id_ed25519 if you still have id_rsa there.
#>
param(
    [Parameter(Mandatory)][string]$Password,
    [string]$PlinkHostKey = '',
    [string]$HostName = '192.168.0.241',
    [string]$User = 'owner1'
)

$ErrorActionPreference = 'Stop'

$plink = Join-Path ${env:ProgramFiles(x86)} 'PuTTY\plink.exe'
if (-not (Test-Path $plink)) {
    $plink = Join-Path $env:ProgramFiles 'PuTTY\plink.exe'
}
if (-not (Test-Path $plink)) {
    throw "PuTTY plink.exe not found. Install PuTTY or: winget install PuTTY.PuTTY"
}

$push = Join-Path $PSScriptRoot 'Push-SSHKey-To-Host.ps1'
if (-not (Test-Path $push)) {
    throw "Place this script in the same folder as Push-SSHKey-To-Host.ps1. Expected: $push"
}

if (-not $PlinkHostKey) {
    Write-Host "Discovering SSH host key from first plink connection to ${User}@${HostName} ..." -ForegroundColor Cyan
    $probe = & $plink -batch -ssh "${User}@${HostName}" -pw $Password "hostname" 2>&1 | Out-String
    if ($probe -match 'SHA256:([A-Za-z0-9+/=]+)') {
        $PlinkHostKey = "SHA256:$($Matches[1])"
        Write-Host "Using host key: $PlinkHostKey" -ForegroundColor Green
    } else {
        Write-Host $probe
        throw "Could not parse Plink host key (need port 22 open, correct password, and reachable $HostName). If the host uses a different port, edit this script or pass -PlinkHostKey manually after running plink once."
    }
}

& $push -HostName $HostName -User $User -Password $Password -PlinkHostKey $PlinkHostKey

Write-Host "`nTip: set IdentityFile ~/.ssh/id_ed25519 for Host ubiquity-gpu-voice in ~/.ssh/config (same key as 4080A)." -ForegroundColor DarkGray
