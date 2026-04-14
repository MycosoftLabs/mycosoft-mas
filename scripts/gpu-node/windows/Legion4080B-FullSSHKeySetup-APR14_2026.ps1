#Requires -Version 5.1
<#
  APR 14 2026 — Full SSH key setup for Legion 4080B (voice) from your DEV PC — same approach as 4080A.

  WHAT IT DOES
  - Ensures %USERPROFILE%\.ssh\id_ed25519 exists (generates if missing).
  - Uses PuTTY plink (password) to run a remote PowerShell that appends your pubkey to:
      %USERPROFILE%\.ssh\authorized_keys
      C:\ProgramData\ssh\administrators_authorized_keys  (+ icacls)  [required if account is Administrator]
  - Tests: OpenSSH ssh.exe -i id_ed25519 -o BatchMode=yes owner1@192.168.0.241 hostname

  PREREQS ON 4080B
  - OpenSSH Server installed, sshd running, TCP 22 allowed on firewall.
  - Local user (default owner2) has a NON-BLANK password (Windows blocks SSH password auth if blank).

  RUN ON DEV PC (same LAN as 192.168.0.241):
    Set-ExecutionPolicy -Scope Process Bypass -Force
    .\Legion4080B-FullSSHKeySetup-APR14_2026.ps1 -Password 'PASTE_PASSWORD_HERE'

  OPTIONAL: if auto host-key discovery fails, pass the key from plink’s error line:
    .\Legion4080B-FullSSHKeySetup-APR14_2026.ps1 -Password '...' -PlinkHostKey 'SHA256:xxxxxxxx'
#>

param(
    [Parameter(Mandatory)][string]$Password,
    [string]$HostName = '192.168.0.241',
    [string]$User = 'owner1',
    [string]$PlinkHostKey = ''
)

$ErrorActionPreference = 'Stop'

$plink = if (Test-Path (Join-Path ${env:ProgramFiles(x86)} 'PuTTY\plink.exe')) {
    Join-Path ${env:ProgramFiles(x86)} 'PuTTY\plink.exe'
} else {
    Join-Path $env:ProgramFiles 'PuTTY\plink.exe'
}
if (-not (Test-Path $plink)) {
    throw "Install PuTTY (includes plink). Example: winget install PuTTY.PuTTY"
}

$sshDir = Join-Path $env:USERPROFILE '.ssh'
if (-not (Test-Path $sshDir)) { New-Item -ItemType Directory -Path $sshDir -Force | Out-Null }
$priv = Join-Path $sshDir 'id_ed25519'
if (-not (Test-Path $priv)) {
    & (Join-Path $env:ProgramFiles 'OpenSSH\ssh-keygen.exe') -t ed25519 -f $priv -N '""' -q
}

$pub = (Get-Content "$priv.pub" -Raw).Trim()
$pubB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($pub))

$remoteTemplate = @'
$pub = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('REPLACEME'))
$d = Join-Path $env:USERPROFILE '.ssh'
New-Item -ItemType Directory -Force -Path $d | Out-Null
$f = Join-Path $d 'authorized_keys'
if (-not (Test-Path $f)) { New-Item -ItemType File -Path $f -Force | Out-Null }
$cur = @(Get-Content $f -ErrorAction SilentlyContinue)
if ($cur -notcontains $pub) { Add-Content -Path $f -Value $pub }
icacls $f /inheritance:r /grant "$($env:USERNAME):F" "SYSTEM:F" "Administrators:F" | Out-Null
$admDir = Join-Path $env:ProgramData 'ssh'
if (-not (Test-Path $admDir)) { New-Item -ItemType Directory -Force -Path $admDir | Out-Null }
$af = Join-Path $admDir 'administrators_authorized_keys'
if (-not (Test-Path $af)) { New-Item -ItemType File -Path $af -Force | Out-Null }
$curA = @(Get-Content $af -ErrorAction SilentlyContinue)
if ($curA -notcontains $pub) { Add-Content -Path $af -Value $pub }
icacls $af /inheritance:r | Out-Null
icacls $af /grant "SYSTEM:(F)" "BUILTIN\Administrators:(F)" | Out-Null
'OK'
'@
$remoteScript = $remoteTemplate -replace 'REPLACEME', $pubB64
$encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($remoteScript))
$remoteCmd = "powershell.exe -NoProfile -NonInteractive -EncodedCommand $encoded"

$target = "${User}@${HostName}"

if (-not $PlinkHostKey) {
    Write-Host 'Discovering host key (plink -batch first connect)...' -ForegroundColor Cyan
    $probe = & $plink -batch -ssh $target -pw $Password "hostname" 2>&1 | Out-String
    if ($probe -match 'SHA256:([A-Za-z0-9+/=]+)') {
        $PlinkHostKey = "SHA256:$($Matches[1])"
        Write-Host "Host key: $PlinkHostKey" -ForegroundColor Green
    } else {
        Write-Host $probe
        throw 'Could not read SHA256 host key. Fix: 4080B online, sshd on :22, password correct, or pass -PlinkHostKey manually.'
    }
}

Write-Host 'Installing authorized_keys via plink...' -ForegroundColor Cyan
& $plink -batch -ssh -hostkey $PlinkHostKey $target -pw $Password $remoteCmd

Write-Host 'Testing OpenSSH (BatchMode, id_ed25519)...' -ForegroundColor Cyan
& (Join-Path $env:ProgramFiles 'OpenSSH\ssh.exe') -i $priv -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 $target hostname

Write-Host 'Done.' -ForegroundColor Green

<# --- SET / CHANGE PASSWORD FOR THE LOGIN USER ON 4080B (run LOCALLY on 4080B) ----------
  Default SSH user is owner1. Change the name below if yours differs.

  Open PowerShell or CMD **as Administrator** on the 4080B Legion (or Chrome Remote Desktop).

  Interactive (prompts twice; hidden in CMD):
    net user owner1 *

  One line (replace with your real password):
    net user owner1 "YourStrongPassword123!"

  If the account does not exist yet:
    net user owner1 YourStrongPassword123! /add
    net localgroup Administrators owner1 /add

  Blank passwords block Windows OpenSSH — set a real password before SSH from another PC.
#>
