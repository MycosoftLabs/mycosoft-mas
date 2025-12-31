# MycoBoard Auto-Discovery Script
# Discovers MycoBoard devices via USB-C, LoRa, Bluetooth, and WiFi

$ErrorActionPreference = "Continue"

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "MycoBoard Auto-Discovery" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

$discoveredDevices = @()

# 1. USB-C / Serial Port Discovery
Write-Host "[1/4] Scanning USB-C / Serial Ports..." -ForegroundColor Yellow
try {
    $portsRes = Invoke-RestMethod -Uri "http://localhost:3000/api/mycobrain/ports" -Method GET -TimeoutSec 5 -ErrorAction Stop
    $usbPorts = $portsRes.ports | Where-Object { 
        $_.is_esp32 -or $_.is_mycobrain -or 
        ($_.vid -and $_.pid -and ($_.vid -match "303A|10C4|1A86")) # ESP32 common VID/PID
    }
    
    foreach ($port in $usbPorts) {
        Write-Host "  ✓ Found USB device: $($port.port) - $($port.description)" -ForegroundColor Green
        $discoveredDevices += @{
            type = "USB-C"
            port = $port.port
            description = $port.description
            vid = $port.vid
            pid = $port.pid
        }
    }
} catch {
    Write-Host "  ✗ USB port scan failed: $_" -ForegroundColor Red
}

# 2. LoRa Gateway Discovery
Write-Host "[2/4] Scanning LoRa Gateway..." -ForegroundColor Yellow
try {
    # Check for LoRa gateway service
    $gatewayRes = Invoke-WebRequest -Uri "http://localhost:8003/gateway/status" -Method GET -TimeoutSec 3 -ErrorAction SilentlyContinue
    if ($gatewayRes.StatusCode -eq 200) {
        $gatewayData = $gatewayRes.Content | ConvertFrom-Json
        if ($gatewayData.devices) {
            Write-Host "  ✓ LoRa Gateway active - $($gatewayData.devices.Count) devices" -ForegroundColor Green
            foreach ($device in $gatewayData.devices) {
                $discoveredDevices += @{
                    type = "LoRa"
                    device_id = $device.device_id
                    address = $device.address
                    rssi = $device.rssi
                }
            }
        }
    } else {
        Write-Host "  ⚠ LoRa Gateway not accessible" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ⚠ LoRa Gateway not running or not accessible" -ForegroundColor Yellow
}

# 3. Bluetooth Discovery (Windows)
Write-Host "[3/4] Scanning Bluetooth devices..." -ForegroundColor Yellow
try {
    if ($IsWindows -or $env:OS -match "Windows") {
        $btDevices = Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue | 
            Where-Object { $_.Status -eq "OK" -and $_.FriendlyName -match "ESP32|MycoBrain" }
        
        if ($btDevices.Count -gt 0) {
            Write-Host "  ✓ Found $($btDevices.Count) Bluetooth devices" -ForegroundColor Green
            foreach ($device in $btDevices) {
                $discoveredDevices += @{
                    type = "Bluetooth"
                    name = $device.FriendlyName
                    status = $device.Status
                }
            }
        } else {
            Write-Host "  ⚠ No MycoBrain Bluetooth devices found" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  ⚠ Bluetooth scanning requires Windows or Linux with bluetoothctl" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ⚠ Bluetooth scan failed: $_" -ForegroundColor Yellow
}

# 4. WiFi Discovery (via UniFi/Network API)
Write-Host "[4/4] Scanning WiFi devices..." -ForegroundColor Yellow
try {
    $networkRes = Invoke-RestMethod -Uri "http://localhost:3000/api/network" -Method GET -TimeoutSec 5 -ErrorAction Stop
    $wifiDevices = $networkRes.clients | Where-Object { 
        $_.name -match "MycoBrain|ESP32|mycobrain" -or 
        $_.mac -match "^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$"
    }
    
    if ($wifiDevices.Count -gt 0) {
        Write-Host "  ✓ Found $($wifiDevices.Count) WiFi devices" -ForegroundColor Green
        foreach ($device in $wifiDevices) {
            $discoveredDevices += @{
                type = "WiFi"
                name = $device.name
                ip = $device.ip
                mac = $device.mac
                signal = $device.signal
            }
        }
    } else {
        Write-Host "  ⚠ No MycoBrain WiFi devices found" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ⚠ WiFi scan failed: $_" -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Discovery Summary" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Total devices discovered: $($discoveredDevices.Count)" -ForegroundColor $(if ($discoveredDevices.Count -gt 0) { "Green" } else { "Yellow" })

$byType = $discoveredDevices | Group-Object -Property type
foreach ($group in $byType) {
    Write-Host "  $($group.Name): $($group.Count)" -ForegroundColor Gray
}

if ($discoveredDevices.Count -gt 0) {
    Write-Host ""
    Write-Host "Discovered Devices:" -ForegroundColor Cyan
    $discoveredDevices | ForEach-Object {
        Write-Host "  - [$($_.type)] $($_.port -or $_.name -or $_.device_id)" -ForegroundColor Gray
    }
}

