#Requires -Version 5.1
<#
.SYNOPSIS
  After SSH keys work (BatchMode), run quick health checks on both Legions in parallel.

.EXAMPLE
  .\Parallel-Legion-HealthCheck.ps1
#>
param(
    [string]$VoiceHost = '192.168.0.241',
    [string]$EarthHost = '192.168.0.249',
    [string]$SshUser = 'mycosoft'
)

$remote = 'hostname; whoami; nvidia-smi -L; wsl -l -v; winget --version; docker version 2>nul'
$jobs = @(
    Start-Job -ScriptBlock {
        param($H, $U, $R)
        ssh -o BatchMode=yes -o ConnectTimeout=20 "$U@$H" $R
    } -ArgumentList $VoiceHost, $SshUser, $remote
    Start-Job -ScriptBlock {
        param($H, $U, $R)
        ssh -o BatchMode=yes -o ConnectTimeout=20 "$U@$H" $R
    } -ArgumentList $EarthHost, $SshUser, $remote
)
Wait-Job $jobs | Out-Null
$i = 0
foreach ($j in $jobs) {
    $name = @($VoiceHost, $EarthHost)[$i++]
    Write-Host "`n========== $name ==========" -ForegroundColor Cyan
    Receive-Job $j
    Remove-Job $j
}
