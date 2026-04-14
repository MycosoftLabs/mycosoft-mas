#Requires -Version 5.1
<#
.SYNOPSIS
  From dev PC: test TCP/22 → deploy SSH keys → parallel health check.

  Legions must already have run Bootstrap-Legion-GPU.ps1 (Admin, via CRD).

  Optional non-interactive:
    .\Invoke-FullLegionAutomation.ps1 -SshPassword '***'
  Or:
    $env:MYCOSOFT_LEGION_SSH_PASSWORD = '***'; .\Invoke-FullLegionAutomation.ps1
#>
param(
    [string]$VoiceHost = '192.168.0.241',
    [string]$EarthHost = '192.168.0.249',
    [string]$SshUser = 'mycosoft',
    [string]$SshPassword = '',
    [switch]$SkipKeyDeploy
)

$ErrorActionPreference = 'Continue'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

if ($env:MYCOSOFT_LEGION_SSH_PASSWORD -and -not $SshPassword) {
    $SshPassword = $env:MYCOSOFT_LEGION_SSH_PASSWORD
    Remove-Item Env:MYCOSOFT_LEGION_SSH_PASSWORD -ErrorAction SilentlyContinue
}

function Test-Port([string]$ComputerName, [int]$Port = 22, [int]$Ms = 3000) {
    try {
        $c = New-Object System.Net.Sockets.TcpClient
        $iar = $c.BeginConnect($ComputerName, $Port, $null, $null)
        if (-not $iar.AsyncWaitHandle.WaitOne($Ms, $false)) { $c.Close(); return $false }
        $c.EndConnect($iar)
        $c.Close()
        return $true
    } catch {
        return $false
    }
}

Write-Host "`n=== 1) TCP port 22 ===" -ForegroundColor Cyan
$v22 = Test-Port $VoiceHost 22
$e22 = Test-Port $EarthHost 22
Write-Host "  ${VoiceHost}:22 -> $(if ($v22) { 'OPEN' } else { 'CLOSED' })"
Write-Host "  ${EarthHost}:22 -> $(if ($e22) { 'OPEN' } else { 'CLOSED' })"

if (-not $v22 -or -not $e22) {
    Write-Host @"

BLOCKED: OpenSSH not reachable. On EACH Legion (CRD), run as Admin:
  .\Bootstrap-Legion-GPU.ps1 -Role Voice   # 4080A
  .\Bootstrap-Legion-GPU.ps1 -Role Earth2  # 4080B

Path: $here

"@ -ForegroundColor Yellow
    exit 1
}

if (-not $SkipKeyDeploy) {
    Write-Host "`n=== 2) SSH key deploy ===" -ForegroundColor Cyan
    if (-not $SshPassword) {
        Write-Host "Pass -SshPassword '...' or set `$env:MYCOSOFT_LEGION_SSH_PASSWORD for unattended deploy." -ForegroundColor DarkYellow
    }
    & "$here\DevPC-InstallSSHKeysAndVerify.ps1" -VoiceHost $VoiceHost -EarthHost $EarthHost -SshUser $SshUser -SshPassword $SshPassword
}

Write-Host "`n=== 3) Parallel health ===" -ForegroundColor Cyan
& "$here\Parallel-Legion-HealthCheck.ps1" -VoiceHost $VoiceHost -EarthHost $EarthHost -SshUser $SshUser

Write-Host "`nDone." -ForegroundColor Green
