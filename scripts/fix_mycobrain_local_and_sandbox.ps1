param(
  [string]$SandboxHost = "192.168.0.187",
  [string]$SandboxHostKey = "ssh-ed25519 255 SHA256:sqd0x7msXPNDhOa9h9CZR19LcdjolVVC7KoHZ33eDHc",
  [string]$LocalHealthUrl = "http://localhost:8003/health",
  [string]$SandboxHealthUrl = "http://192.168.0.187:8003/health"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-Health {
  param([string]$Url, [int]$TimeoutSec = 6)
  try {
    $r = Invoke-RestMethod -Uri $Url -TimeoutSec $TimeoutSec
    return @{ ok = $true; payload = $r }
  } catch {
    return @{ ok = $false; error = $_.Exception.Message }
  }
}

function Get-Creds {
  param([string]$RepoRoot)
  $credsFile = Join-Path $RepoRoot ".credentials.local"
  if (-not (Test-Path $credsFile)) {
    $credsFile = Join-Path $env:USERPROFILE ".mycosoft-credentials"
  }
  if (-not (Test-Path $credsFile)) {
    throw "Credentials file not found (.credentials.local or ~/.mycosoft-credentials)."
  }

  $map = @{}
  Get-Content $credsFile | ForEach-Object {
    if ($_ -match "^([^#=]+)=(.*)$") {
      $map[$matches[1].Trim()] = $matches[2].Trim()
    }
  }
  return $map
}

function Invoke-Remote {
  param(
    [string]$VmHost,
    [string]$User,
    [string]$Pass,
    [string]$HostKey,
    [string]$Command,
    [string]$StdinText = ""
  )
  $plinkPath = "C:\Program Files\PuTTY\plink.exe"
  if (-not (Test-Path $plinkPath)) {
    throw "PuTTY plink not found at $plinkPath"
  }

  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = $plinkPath
  $psi.Arguments = "-batch -hostkey `"$HostKey`" -ssh `"$User@$VmHost`" -pw `"$Pass`" `"$Command`""
  $psi.RedirectStandardInput = $true
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $psi.UseShellExecute = $false
  $psi.CreateNoWindow = $true

  $p = New-Object System.Diagnostics.Process
  $p.StartInfo = $psi
  [void]$p.Start()

  if ($StdinText) {
    $p.StandardInput.WriteLine($StdinText)
  }
  $p.StandardInput.Close()

  $stdout = $p.StandardOutput.ReadToEnd()
  $stderr = $p.StandardError.ReadToEnd()
  $p.WaitForExit()

  return @{
    ExitCode = $p.ExitCode
    StdOut = $stdout
    StdErr = $stderr
  }
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Write-Host "Checking local MycoBrain health..."
$local = Get-Health -Url $LocalHealthUrl
if (-not $local.ok) {
  Write-Host "Local MycoBrain is down. Restarting local service..."
  & (Join-Path $repoRoot "scripts\mycobrain-service.ps1") restart | Out-Null
  Start-Sleep -Seconds 2
  $local = Get-Health -Url $LocalHealthUrl
}
if (-not $local.ok) {
  throw "Local MycoBrain still unhealthy: $($local.error)"
}
Write-Host "Local MycoBrain healthy: $($local.payload | ConvertTo-Json -Compress)"

Write-Host "Checking sandbox MycoBrain health..."
$sandbox = Get-Health -Url $SandboxHealthUrl
if (-not $sandbox.ok) {
  Write-Host "Sandbox MycoBrain is down. Attempting remote recovery..."

  $creds = Get-Creds -RepoRoot $repoRoot
  $sshUser = if ($creds.ContainsKey("VM_SSH_USER")) { $creds["VM_SSH_USER"] } else { "mycosoft" }
  $sshPass = if ($creds.ContainsKey("VM_PASSWORD")) { $creds["VM_PASSWORD"] } else { $creds["VM_SSH_PASSWORD"] }
  if (-not $sshPass) {
    throw "VM password not found in credentials file."
  }

  $remote = @(
    "set -e",
    "sudo -S -k systemctl restart mycobrain-service || true",
    "sudo -S -k systemctl restart mycobrain || true",
    "sleep 2",
    "systemctl is-active mycobrain-service || true",
    "systemctl is-active mycobrain || true",
    "curl -fsS --max-time 8 http://localhost:8003/health || true"
  ) -join "; "

  $stdinPayload = "$sshPass`n$sshPass`n$sshPass"
  $remoteOut = Invoke-Remote -VmHost $SandboxHost -User $sshUser -Pass $sshPass -HostKey $SandboxHostKey -Command $remote -StdinText $stdinPayload
  Write-Host "Remote recovery output:"
  if ($remoteOut.StdOut) { Write-Host $remoteOut.StdOut }
  if ($remoteOut.StdErr) { Write-Host $remoteOut.StdErr }
  if ($remoteOut.ExitCode -ne 0) {
    Write-Host "Remote command exit code: $($remoteOut.ExitCode)"
  }

  Start-Sleep -Seconds 2
  $sandbox = Get-Health -Url $SandboxHealthUrl
}

if (-not $sandbox.ok) {
  Write-Host "Collecting sandbox diagnostics..."
  $diagCmd = @(
    "set -e",
    "ps -ef | grep -i mycobrain_service_standalone.py | grep -v grep || true",
    "sudo -S ss -ltnp | grep 8003 || true",
    "systemctl list-units --type=service | grep -i mycobrain || true",
    "sudo -S journalctl -u mycobrain-service -n 80 --no-pager || true"
  ) -join "; "
  $stdinDiag = "$sshPass`n$sshPass`n$sshPass`n$sshPass"
  $diagOut = Invoke-Remote -VmHost $SandboxHost -User $sshUser -Pass $sshPass -HostKey $SandboxHostKey -Command $diagCmd -StdinText $stdinDiag
  if ($diagOut.StdOut) { Write-Host $diagOut.StdOut }
  if ($diagOut.StdErr) { Write-Host $diagOut.StdErr }

  Write-Host "Applying hard restart sequence on sandbox..."
  $hardCmd = @(
    "set -e",
    "sudo -S systemctl stop mycobrain-proxy || true",
    "sudo -S systemctl disable mycobrain-proxy || true",
    "sudo -S pkill -9 -f 'socat.*8003' || true",
    "sudo -S pkill -9 -f mycobrain_service_standalone.py || true",
    "sudo -S fuser -k 8003/tcp || true",
    "sudo -S systemctl kill mycobrain-service || true",
    "sleep 2",
    "sudo -S systemctl reset-failed mycobrain-service || true",
    "sudo -S systemctl start mycobrain-service || true",
    "sleep 3",
    "sudo -S ss -ltnp | grep 8003 || true",
    "systemctl is-active mycobrain-service || true",
    "curl -fsS --max-time 8 http://localhost:8003/health || true"
  ) -join "; "
  $stdinHard = "$sshPass`n$sshPass`n$sshPass`n$sshPass`n$sshPass`n$sshPass`n$sshPass"
  $hardOut = Invoke-Remote -VmHost $SandboxHost -User $sshUser -Pass $sshPass -HostKey $SandboxHostKey -Command $hardCmd -StdinText $stdinHard
  if ($hardOut.StdOut) { Write-Host $hardOut.StdOut }
  if ($hardOut.StdErr) { Write-Host $hardOut.StdErr }

  $sandbox = Get-Health -Url $SandboxHealthUrl
}

if (-not $sandbox.ok) {
  throw "Sandbox MycoBrain still unhealthy after hard restart: $($sandbox.error)"
}

Write-Host "Sandbox MycoBrain healthy: $($sandbox.payload | ConvertTo-Json -Compress)"
Write-Host "MycoBrain local + sandbox recovery complete."
