#Requires -Version 5.1
<#
.SYNOPSIS
  Installs Microsoft OpenSSH (ssh/scp/sftp) via winget and ensures PATH includes it.
  Run on your **local dev PC** if `ssh` is not recognized.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\Install-OpenSSH-Client.ps1
#>
$ErrorActionPreference = 'Stop'

$openSshDir = 'C:\Program Files\OpenSSH'
if (Test-Path (Join-Path $openSshDir 'ssh.exe')) {
    Write-Host "Found: $openSshDir\ssh.exe" -ForegroundColor Green
} else {
    Write-Host 'Installing Microsoft.OpenSSH.Preview via winget...' -ForegroundColor Cyan
    winget install -e --id Microsoft.OpenSSH.Preview --accept-package-agreements --accept-source-agreements --disable-interactivity
}

$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if ($userPath -notlike "*$openSshDir*") {
    [Environment]::SetEnvironmentVariable('Path', "$userPath;$openSshDir", 'User')
    Write-Host "Added to user PATH: $openSshDir" -ForegroundColor Green
}

$env:Path += ";$openSshDir"
& (Join-Path $openSshDir 'ssh.exe') -V
Write-Host "`nOpen a NEW PowerShell window, then: ssh mycosoft@192.168.0.249" -ForegroundColor Cyan
