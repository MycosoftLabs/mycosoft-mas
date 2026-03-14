[CmdletBinding()]
param(
    [string]$AllowedPorts = "COM7",
    [string]$GatewayName = "MycoBrain Gateway Node",
    [string]$GatewayLocation = "Yard Gateway",
    [string]$MasRegistryUrl = "http://192.168.0.188:8001",
    [switch]$RunLoraPrep
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$serviceManager = Join-Path $scriptRoot "mycobrain-service.ps1"
if (-not (Test-Path $serviceManager)) {
    throw "mycobrain-service.ps1 not found at $serviceManager"
}

function Invoke-MasDeviceCommand {
    param(
        [Parameter(Mandatory = $true)][string]$RegistryUrl,
        [Parameter(Mandatory = $true)][string]$DeviceId,
        [Parameter(Mandatory = $true)][string]$Command
    )

    $uri = "$($RegistryUrl.TrimEnd('/'))/api/devices/$DeviceId/command?use_mycorrhizae=false"
    $payload = @{
        command = $Command
        params   = @{}
        timeout  = 12
    } | ConvertTo-Json -Depth 6

    return Invoke-RestMethod -Uri $uri -Method Post -ContentType "application/json" -Body $payload -TimeoutSec 20
}

# Force gateway semantics so MAS/device-network recognize this node as a gateway.
[Environment]::SetEnvironmentVariable("MYCOBRAIN_DEVICE_ROLE", "gateway", "Process")
[Environment]::SetEnvironmentVariable("MYCOBRAIN_DEVICE_NAME", $GatewayName, "Process")
[Environment]::SetEnvironmentVariable("MYCOBRAIN_DEVICE_LOCATION", $GatewayLocation, "Process")
[Environment]::SetEnvironmentVariable("MYCOBRAIN_ALLOWED_PORTS", $AllowedPorts, "Process")
[Environment]::SetEnvironmentVariable("MAS_REGISTRY_URL", $MasRegistryUrl, "Process")
[Environment]::SetEnvironmentVariable("MYCOBRAIN_HEARTBEAT_ENABLED", "true", "Process")

$localIp = (
    Get-NetIPConfiguration |
    Where-Object { $_.IPv4DefaultGateway -and $_.IPv4Address } |
    Select-Object -First 1 -ExpandProperty IPv4Address |
    Select-Object -ExpandProperty IPAddress
)
# Force LAN classification. PUBLIC_HOST can cause cloudflare classification and break MAS direct command routing.
[Environment]::SetEnvironmentVariable("MYCOBRAIN_PUBLIC_HOST", $null, "Process")

Write-Host "[INFO] Starting MycoBrain in gateway mode..." -ForegroundColor Cyan
Write-Host "[INFO] Allowed ports: $AllowedPorts" -ForegroundColor Gray

powershell -ExecutionPolicy Bypass -File $serviceManager restart -Mode gateway -AllowedPorts $AllowedPorts
Start-Sleep -Seconds 4

$health = Invoke-RestMethod -Uri "http://localhost:8003/health" -TimeoutSec 8
Write-Host "[OK] Local health: $($health | ConvertTo-Json -Compress)" -ForegroundColor Green

$mas = Invoke-RestMethod -Uri "$($MasRegistryUrl.TrimEnd('/'))/api/devices?include_offline=true" -TimeoutSec 8
$gatewayDevices = @($mas.devices | Where-Object {
    $_.device_role -eq "gateway" -and ($localIp -and $_.host -eq $localIp)
})
Write-Host "[OK] Gateway entries on MAS from this machine: $($gatewayDevices.Count)" -ForegroundColor Green

if ($gatewayDevices.Count -gt 0) {
    $gatewayId = $gatewayDevices[0].device_id
    Write-Host "[OK] Active gateway device_id: $gatewayId" -ForegroundColor Green

    if ($RunLoraPrep) {
        Write-Host "[INFO] Running LoRa prep commands on $gatewayId via MAS..." -ForegroundColor Cyan
        foreach ($cmd in @("lora init", "lora status", "mesh status")) {
            try {
                $resp = Invoke-MasDeviceCommand -RegistryUrl $MasRegistryUrl -DeviceId $gatewayId -Command $cmd
                $respText = ($resp.response | Out-String).Trim()
                if ($respText -match '"ok"\s*:\s*false' -or $respText -match "unknown command") {
                    Write-Host "[WARN] $cmd rejected by device firmware -> $respText" -ForegroundColor Yellow
                } else {
                    Write-Host "[OK] $cmd -> $respText" -ForegroundColor Green
                }
            } catch {
                Write-Host "[WARN] $cmd failed: $($_.Exception.Message)" -ForegroundColor Yellow
            }
        }
    }
}
