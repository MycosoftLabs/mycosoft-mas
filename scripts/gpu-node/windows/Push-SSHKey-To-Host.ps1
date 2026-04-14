#Requires -Version 5.1
<#
.SYNOPSIS
  Install local id_ed25519.pub into the remote user's authorized_keys (Windows OpenSSH).

.NOTES
  - Members of Administrators must also have the key in ProgramData\ssh\administrators_authorized_keys
    or key-based login will fail (publickey denied) even when ~/.ssh/authorized_keys looks correct.
  - If PuTTY plink.exe is present, it is used (fast, non-interactive with -PlinkHostKey).
    Otherwise falls back to Posh-SSH (Install-Module may take time on first run).
#>
param(
    [Parameter(Mandatory)][string]$HostName,
    [Parameter(Mandatory)][string]$User,
    [Parameter(Mandatory)][string]$Password,
    # Required for plink -batch on first connect, e.g. SHA256:FNcCB+... from plink's host key prompt
    [string]$PlinkHostKey = ''
)

$ErrorActionPreference = 'Stop'

$plink = Join-Path ${env:ProgramFiles(x86)} 'PuTTY\plink.exe'
if (-not (Test-Path $plink)) {
    $plink = Join-Path $env:ProgramFiles 'PuTTY\plink.exe'
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

if ((Test-Path $plink) -and $PlinkHostKey) {
    Write-Host "Using plink: $plink" -ForegroundColor Cyan
    & $plink -batch -ssh -hostkey $PlinkHostKey $target -pw $Password $remoteCmd
} elseif (Test-Path $plink) {
    throw "Plink found at $plink but -PlinkHostKey is required for non-interactive use (get fingerprint from first plink connection error)."
} else {
    Write-Host 'Plink not found; using Posh-SSH (may install modules)...' -ForegroundColor Yellow
    if (-not (Get-Module -ListAvailable -Name Posh-SSH)) {
        $null = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
        if (-not (Get-PackageProvider -Name NuGet -ErrorAction SilentlyContinue)) {
            Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Force -Scope CurrentUser | Out-Null
        }
        Set-PSRepository -Name PSGallery -InstallationPolicy Trusted -ErrorAction SilentlyContinue
        Install-Module -Name Posh-SSH -Scope CurrentUser -Force -AllowClobber -SkipPublisherCheck -Repository PSGallery
    }
    Import-Module Posh-SSH
    $sec = ConvertTo-SecureString $Password -AsPlainText -Force
    $cred = New-Object PSCredential($User, $sec)
    $sess = New-SSHSession -ComputerName $HostName -Credential $cred -AcceptKey -Force
    try {
        $r = Invoke-SSHCommand -SessionId $sess.SessionId -Command $remoteCmd
        if ($r.ExitStatus -ne 0) { throw "Remote failed: $($r.Error)" }
        Write-Host $r.Output.Trim() -ForegroundColor Green
    } finally {
        Remove-SSHSession -SessionId $sess.SessionId | Out-Null
    }
}

Write-Host "Testing: ssh -i `"$priv`" -o BatchMode=yes ${User}@${HostName} hostname" -ForegroundColor Cyan
& (Join-Path $env:ProgramFiles 'OpenSSH\ssh.exe') -i $priv -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 $target hostname
