[CmdletBinding()]
param(
    [string]$MasRegistryUrl = "http://192.168.0.188:8001",
    [string]$GatewayDeviceId = "",
    [string]$PeerDeviceId = "",
    [int]$CommandTimeoutSec = 15
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-MasDeviceCommand {
    param(
        [Parameter(Mandatory = $true)][string]$RegistryUrl,
        [Parameter(Mandatory = $true)][string]$DeviceId,
        [Parameter(Mandatory = $true)][string]$Command,
        [int]$TimeoutSec = 15
    )

    $uri = "$($RegistryUrl.TrimEnd('/'))/api/devices/$DeviceId/command?use_mycorrhizae=false"
    $payload = @{
        command = $Command
        params  = @{}
        timeout = $TimeoutSec
    } | ConvertTo-Json -Depth 6

    return Invoke-RestMethod -Uri $uri -Method Post -ContentType "application/json" -Body $payload -TimeoutSec ($TimeoutSec + 10)
}

function Resolve-GatewayDevice {
    param(
        [Parameter(Mandatory = $true)][string]$RegistryUrl
    )

    $devices = Invoke-RestMethod -Uri "$($RegistryUrl.TrimEnd('/'))/api/devices?include_offline=true" -TimeoutSec 12
    $gateway = @($devices.devices | Where-Object { $_.device_role -eq "gateway" -and $_.status -eq "online" })
    if ($gateway.Count -eq 0) {
        throw "No online gateway device found in MAS registry."
    }

    $localIp = (
        Get-NetIPConfiguration |
        Where-Object { $_.IPv4DefaultGateway -and $_.IPv4Address } |
        Select-Object -First 1 -ExpandProperty IPv4Address |
        Select-Object -ExpandProperty IPAddress
    )

    if ($localIp) {
        $localGateway = @($gateway | Where-Object {
            $_.host -eq $localIp -and $_.device_id -like "mycobrain-*"
        })
        if ($localGateway.Count -gt 0) {
            return $localGateway[0].device_id
        }
    }

    $serialGateway = @($gateway | Where-Object { $_.device_id -like "mycobrain-*" })
    if ($serialGateway.Count -gt 0) {
        return $serialGateway[0].device_id
    }

    return $gateway[0].device_id
}

$resolvedGatewayId = $GatewayDeviceId
if ([string]::IsNullOrWhiteSpace($resolvedGatewayId)) {
    $resolvedGatewayId = Resolve-GatewayDevice -RegistryUrl $MasRegistryUrl
}

Write-Host "[INFO] MAS: $MasRegistryUrl" -ForegroundColor Cyan
Write-Host "[INFO] Gateway device: $resolvedGatewayId" -ForegroundColor Cyan
if ($PeerDeviceId) {
    Write-Host "[INFO] Peer device: $PeerDeviceId" -ForegroundColor Cyan
}

$results = @()

function Invoke-TestStep {
    param(
        [string]$Name,
        [string]$DeviceId,
        [string]$Command
    )

    Write-Host "[STEP] $Name :: $DeviceId :: $Command" -ForegroundColor Yellow
    try {
        $resp = Invoke-MasDeviceCommand -RegistryUrl $MasRegistryUrl -DeviceId $DeviceId -Command $Command -TimeoutSec $CommandTimeoutSec
        $respText = ($resp.response | Out-String).Trim()
        $deviceAccepted = $true
        if ($resp.PSObject.Properties.Name -contains "response") {
            $rawResponse = [string]$resp.response
            if ($rawResponse -match '"ok"\s*:\s*false' -or $rawResponse -match "unknown command") {
                $deviceAccepted = $false
            } elseif ($rawResponse.Trim().StartsWith("{")) {
                try {
                    $parsed = $rawResponse | ConvertFrom-Json -ErrorAction Stop
                    if ($parsed.PSObject.Properties.Name -contains "ok" -and -not [bool]$parsed.ok) {
                        $deviceAccepted = $false
                    }
                } catch {
                    # Keep best-effort parsing; raw string checks above already applied.
                }
            }
        }

        if ($deviceAccepted) {
            Write-Host "[OK] $respText" -ForegroundColor Green
        } else {
            Write-Host "[FAIL] Device rejected command: $respText" -ForegroundColor Red
        }
        $script:results += [PSCustomObject]@{
            step = $Name
            device_id = $DeviceId
            command = $Command
            status = $(if ($deviceAccepted) { "ok" } else { "fail" })
            response = $respText
        }
    } catch {
        Write-Host "[FAIL] $($_.Exception.Message)" -ForegroundColor Red
        $script:results += [PSCustomObject]@{
            step = $Name
            device_id = $DeviceId
            command = $Command
            status = "fail"
            response = $_.Exception.Message
        }
    }
}

# Gateway baseline
Invoke-TestStep -Name "gateway-status" -DeviceId $resolvedGatewayId -Command "status"
Invoke-TestStep -Name "gateway-lora-init" -DeviceId $resolvedGatewayId -Command "lora init"
Invoke-TestStep -Name "gateway-lora-status" -DeviceId $resolvedGatewayId -Command "lora status"
Invoke-TestStep -Name "gateway-mesh-status" -DeviceId $resolvedGatewayId -Command "mesh status"

# Gateway beacon transmission
$beacon = "GW_BEACON_{0}" -f (Get-Date -Format "yyyyMMddHHmmss")
Invoke-TestStep -Name "gateway-lora-send-beacon" -DeviceId $resolvedGatewayId -Command ("lora send {0}" -f $beacon)

if ($PeerDeviceId) {
    Invoke-TestStep -Name "peer-status" -DeviceId $PeerDeviceId -Command "status"
    Invoke-TestStep -Name "peer-lora-init" -DeviceId $PeerDeviceId -Command "lora init"
    Invoke-TestStep -Name "peer-lora-status" -DeviceId $PeerDeviceId -Command "lora status"

    $peerMessage = "PEER_HELLO_{0}" -f (Get-Date -Format "yyyyMMddHHmmss")
    Invoke-TestStep -Name "peer-lora-send" -DeviceId $PeerDeviceId -Command ("lora send {0}" -f $peerMessage)

    Start-Sleep -Seconds 2
    Invoke-TestStep -Name "gateway-post-peer-status" -DeviceId $resolvedGatewayId -Command "status"
}

$failed = @($results | Where-Object { $_.status -ne "ok" }).Count
$summary = [PSCustomObject]@{
    timestamp = (Get-Date).ToString("o")
    mas_registry_url = $MasRegistryUrl
    gateway_device_id = $resolvedGatewayId
    peer_device_id = $PeerDeviceId
    failed_steps = $failed
    total_steps = $results.Count
    results = $results
}

Write-Host ""
Write-Host "========== LoRa Link Test Summary ==========" -ForegroundColor Cyan
Write-Host ($summary | ConvertTo-Json -Depth 8)

if ($failed -gt 0) {
    exit 1
}
