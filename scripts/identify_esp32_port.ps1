# Identify ESP32 COM Port
# Run this script to find which COM port is your ESP32

Write-Host "Scanning for COM ports..." -ForegroundColor Cyan
Write-Host ""

# Method 1: WMI
$ports = Get-WmiObject Win32_SerialPort | Select-Object DeviceID, Description, Name
Write-Host "=== COM Ports (WMI) ===" -ForegroundColor Yellow
foreach ($port in $ports) {
    $isESP32 = $false
    $desc = $port.Description -join " "
    if ($desc -match "USB.*Serial|CH340|CP210|FTDI|Silicon|ESP32|ESP" -or $port.Name -match "USB") {
        $isESP32 = $true
        Write-Host "$($port.DeviceID) - $desc" -ForegroundColor Green
        Write-Host "  ^ Likely ESP32!" -ForegroundColor Green
    } else {
        Write-Host "$($port.DeviceID) - $desc"
    }
}

Write-Host ""
Write-Host "=== PnP Devices ===" -ForegroundColor Yellow
$pnpPorts = Get-PnpDevice -Class Ports | Where-Object { $_.Status -eq 'OK' }
foreach ($pnp in $pnpPorts) {
    $name = $pnp.FriendlyName
    if ($name -match "USB.*Serial|CH340|CP210|FTDI|Silicon|ESP32|ESP|COM") {
        Write-Host "$name" -ForegroundColor Green
        Write-Host "  Status: $($pnp.Status)" -ForegroundColor Green
    } else {
        Write-Host "$name"
    }
}

Write-Host ""
Write-Host "=== Recommendations ===" -ForegroundColor Cyan
Write-Host "1. Check Device Manager:"
Write-Host "   - Press Win+X, select 'Device Manager'"
Write-Host "   - Look under 'Ports (COM & LPT)'"
Write-Host "   - ESP32 usually shows as 'USB Serial' or 'CH340' or 'CP210x'"
Write-Host ""
Write-Host "2. Try each COM port:"
Write-Host "   - COM1, COM2, COM3"
Write-Host "   - In Arduino IDE, try uploading to each one"
Write-Host "   - The correct one will show 'Connecting...' during upload"
Write-Host ""
Write-Host "3. If no ESP32 found:"
Write-Host "   - Install CH340 or CP210x drivers"
Write-Host "   - Unplug and replug USB cable"
Write-Host "   - Try different USB port on computer"

