# SSH tunnel to n8n on VM 191
# Run this, leave the window open, then open http://localhost:15679 in your browser
# Press Ctrl+C to close the tunnel

$sshExe = "C:\Windows\System32\OpenSSH\ssh.exe"
$keyPath = Join-Path $env:USERPROFILE ".ssh\myca_vm191"

if (-not (Test-Path $sshExe)) {
  Write-Error "OpenSSH not found at $sshExe. Install: Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0"
  exit 1
}

if (-not (Test-Path $keyPath)) {
  Write-Warning "Key not found: $keyPath. You may be prompted for password."
  & $sshExe -L 15679:localhost:5679 mycosoft@192.168.0.191
} else {
  & $sshExe -i $keyPath -L 15679:localhost:5679 mycosoft@192.168.0.191
}
