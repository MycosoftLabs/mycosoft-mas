# SSH to Mycosoft VMs - all use same user/password from .credentials.local
# Usage: .\scripts\ssh-vm.ps1 sandbox | mas | mindex | gpu | myca
# MAR03 2026

param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("sandbox", "mas", "mindex", "gpu", "myca")]
    [string]$Target
)

$VM_HOSTS = @{
    sandbox = "192.168.0.187"
    mas     = "192.168.0.188"
    mindex  = "192.168.0.189"
    gpu     = "192.168.0.190"
    myca    = "192.168.0.191"
}

$root = Split-Path $PSScriptRoot -Parent
if (-not $root) { $root = (Get-Location).Path }
$credsFile = Join-Path $root ".credentials.local"
if (-not (Test-Path $credsFile)) {
    $credsFile = Join-Path $env:USERPROFILE ".mycosoft-credentials"
}

if (Test-Path $credsFile) {
    Get-Content $credsFile | ForEach-Object {
        if ($_ -match "^([^#=]+)=(.*)$") {
            [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
        }
    }
}

$ip = $VM_HOSTS[$Target]
$user = $env:VM_SSH_USER
$pass = $env:VM_PASSWORD; if (-not $pass) { $pass = $env:VM_SSH_PASSWORD }

if (-not $pass) {
    Write-Error "Credentials not found. Set VM_PASSWORD env var or add VM_SSH_PASSWORD to .credentials.local"
    exit 1
}

if (-not $user) { $user = "mycosoft" }

# Use plink if available (non-interactive), else ssh
$plink = Get-Command plink -ErrorAction SilentlyContinue
if ($plink) {
    $env:PLINK_PROTOCOL = "ssh"
    & plink -ssh "$user@$ip" -pw $pass
} else {
    $sshpass = Get-Command sshpass -ErrorAction SilentlyContinue
    if ($sshpass) {
        & sshpass -p $pass ssh "$user@$ip"
    } else {
        & ssh "$user@$ip"
    }
}
