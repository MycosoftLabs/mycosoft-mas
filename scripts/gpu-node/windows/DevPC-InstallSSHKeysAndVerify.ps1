#Requires -Version 5.1
<#
.SYNOPSIS
  Run on your **development PC** on the Dream Machine LAN after each Legion ran Bootstrap-Legion-GPU.ps1.

.DESCRIPTION
  - Installs Posh-SSH (SSH.NET) for password-based first login
  - Creates id_ed25519 if missing
  - Appends your public key to each host's authorized_keys (parallel)
  - Verifies ssh -o BatchMode=yes

.PARAMETER VoiceHost   Default 192.168.0.241 (4080A / voice — adjust if UniFi differs)
.PARAMETER EarthHost   Default 192.168.0.249 (4080B / Earth-2)
#>
param(
    [string]$VoiceHost = '192.168.0.241',
    [string]$EarthHost = '192.168.0.249',
    [string]$SshUser = 'mycosoft',
    [string]$SshPassword = ''
)

$ErrorActionPreference = 'Stop'

Write-Host "`n=== Posh-SSH (first-time password deploy) ===" -ForegroundColor Cyan
if (-not (Get-Module -ListAvailable -Name Posh-SSH)) {
    Install-Module -Name Posh-SSH -Scope CurrentUser -Force -AllowClobber
}
Import-Module Posh-SSH

$sshDir = Join-Path $env:USERPROFILE '.ssh'
if (-not (Test-Path $sshDir)) { New-Item -ItemType Directory -Path $sshDir -Force | Out-Null }
$priv = Join-Path $sshDir 'id_ed25519'
if (-not (Test-Path $priv)) {
    ssh-keygen -t ed25519 -f $priv -N '""' -q
}
$pub = (Get-Content "$priv.pub" -Raw).Trim()
$pubB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($pub))

if ($SshPassword) {
    $secure = ConvertTo-SecureString $SshPassword -AsPlainText -Force
} else {
    $secure = Read-Host "SSH password for '$SshUser' (set on both Legions)" -AsSecureString
}
$plainForJobs = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
)

# Remote script runs ON the Legion; REPLACEME -> base64 pubkey
$remoteTemplate = @'
$pub = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('REPLACEME'))
$d = Join-Path $env:USERPROFILE '.ssh'
New-Item -ItemType Directory -Force -Path $d | Out-Null
$f = Join-Path $d 'authorized_keys'
if (-not (Test-Path $f)) { New-Item -ItemType File -Path $f -Force | Out-Null }
$cur = @(Get-Content $f -ErrorAction SilentlyContinue)
if ($cur -notcontains $pub) { Add-Content -Path $f -Value $pub }
icacls $f /inheritance:r /grant "$($env:USERNAME):F" "SYSTEM:F" "Administrators:F" | Out-Null
'OK'
'@
$remoteScript = $remoteTemplate -replace 'REPLACEME', $pubB64
$encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($remoteScript))
$remoteCmd = "powershell.exe -NoProfile -NonInteractive -EncodedCommand $encoded"

Write-Host "`n=== Deploying key in parallel ===" -ForegroundColor Cyan
$jobs = @(
    Start-Job -ScriptBlock {
        param($VH, $U, $S, $RC)
        Import-Module Posh-SSH
        $sec = ConvertTo-SecureString $S -AsPlainText -Force
        $cred = New-Object PSCredential($U, $sec)
        $sess = New-SSHSession -ComputerName $VH -Credential $cred -AcceptKey -Force
        try {
            $r = Invoke-SSHCommand -SessionId $sess.SessionId -Command $RC
            [pscustomobject]@{ Host = $VH; Exit = $r.ExitStatus; Out = $r.Output; Err = $r.Error }
        } finally {
            Remove-SSHSession -SessionId $sess.SessionId | Out-Null
        }
    } -ArgumentList $VoiceHost, $SshUser, $plainForJobs, $remoteCmd
    Start-Job -ScriptBlock {
        param($EH, $U, $S, $RC)
        Import-Module Posh-SSH
        $sec = ConvertTo-SecureString $S -AsPlainText -Force
        $cred = New-Object PSCredential($U, $sec)
        $sess = New-SSHSession -ComputerName $EH -Credential $cred -AcceptKey -Force
        try {
            $r = Invoke-SSHCommand -SessionId $sess.SessionId -Command $RC
            [pscustomobject]@{ Host = $EH; Exit = $r.ExitStatus; Out = $r.Output; Err = $r.Error }
        } finally {
            Remove-SSHSession -SessionId $sess.SessionId | Out-Null
        }
    } -ArgumentList $EarthHost, $SshUser, $plainForJobs, $remoteCmd
)
Wait-Job $jobs | Out-Null
foreach ($j in $jobs) {
    Receive-Job $j | Format-List
    Remove-Job $j
}

Write-Host "`n=== Verify key-based SSH (no password) ===" -ForegroundColor Cyan
foreach ($h in @($VoiceHost, $EarthHost)) {
    Write-Host "--- $h ---" -ForegroundColor DarkCyan
    ssh -o BatchMode=yes -o ConnectTimeout=15 "$SshUser@$h" "hostname; whoami; nvidia-smi -L 2>nul; wsl -l -v 2>nul"
}

Write-Host "`nDone." -ForegroundColor Green
