# MycoBrain Side-A Upload Script with Exact Arduino IDE Settings
# 
# This script uses the EXACT board settings that are known to work:
# - CPU Frequency: 240 MHz
# - PSRAM: OPI PSRAM
# - Flash Mode: QIO @ 80 MHz
# - Flash Size: 16 MB
# - Partition Scheme: 16MB Flash, 3MB App / 9.9MB FATFS
# - USB CDC on boot: Enabled
# - USB Mode: Hardware CDC and JTAG
# - Upload Speed: 921600
# - JTAG Adapter: Integrated USB JTAG
# - Arduino runs on core 1
# - Events run on core 1
# - Wi-Fi Core debug level: None
# - Erase all flash before sketch upload: Disabled

param(
    [Parameter(Mandatory=$false)]
    [string]$Port = "",
    
    [Parameter(Mandatory=$false)]
    [string]$SketchPath = "firmware/MycoBrain_SideA_DualMode"
)

# Find COM port if not specified
if ([string]::IsNullOrEmpty($Port)) {
    Write-Host "Scanning for ESP32-S3 COM ports..." -ForegroundColor Cyan
    $ports = python -c "import serial.tools.list_ports as lp; ports = [p.device for p in lp.comports() if '303a' in p.hwid.lower() or '10c4' in p.hwid.lower()]; print('\n'.join(ports) if ports else '')" 2>$null
    if ($ports) {
        $Port = ($ports -split "`n" | Select-Object -First 1).Trim()
        Write-Host "Found ESP32-S3 on: $Port" -ForegroundColor Green
    } else {
        Write-Host "ERROR: No ESP32-S3 COM port found. Please specify -Port COMx" -ForegroundColor Red
        exit 1
    }
}

# Verify sketch exists
if (-not (Test-Path "$SketchPath/$SketchPath.ino")) {
    $sketchName = Split-Path $SketchPath -Leaf
    if (-not (Test-Path "$SketchPath/$sketchName.ino")) {
        Write-Host "ERROR: Sketch not found at $SketchPath" -ForegroundColor Red
        exit 1
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "MycoBrain Side-A Upload (Exact Settings)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Port: $Port" -ForegroundColor Yellow
Write-Host "Sketch: $SketchPath" -ForegroundColor Yellow
Write-Host ""

# Build FQBN with EXACT settings
# NOTE: USB DFU on boot was requested but requires USB-OTG mode, which conflicts with
# "Hardware CDC and JTAG" mode. Using hwcdc as specified. If DFU is needed, change USBMode to "default" (OTG).
$FQBN = "esp32:esp32:esp32s3:CPUFreq=240,PSRAM=opi,FlashMode=qio,FlashSize=16M,PartitionScheme=app3M_fat9M_16MB,CDCOnBoot=cdc,USBMode=hwcdc,EventsCore=1,EraseFlash=none,MSCOnBoot=default,UploadSpeed=921600,LoopCore=1,DebugLevel=none,JTAGAdapter=builtin,UploadMode=default"

Write-Host "Board Options:" -ForegroundColor Cyan
Write-Host "  CPU Frequency: 240 MHz" -ForegroundColor White
Write-Host "  PSRAM: OPI PSRAM" -ForegroundColor White
Write-Host "  Flash Mode: QIO @ 80 MHz" -ForegroundColor White
Write-Host "  Flash Size: 16 MB" -ForegroundColor White
Write-Host "  Partition Scheme: 16MB Flash, 3MB App / 9.9MB FATFS" -ForegroundColor White
Write-Host "  USB CDC on boot: Enabled" -ForegroundColor White
Write-Host "  USB Mode: Hardware CDC and JTAG" -ForegroundColor White
Write-Host "  Upload Speed: 921600" -ForegroundColor White
Write-Host "  JTAG Adapter: Integrated USB JTAG" -ForegroundColor White
Write-Host "  Arduino runs on: Core 1" -ForegroundColor White
Write-Host "  Events run on: Core 1" -ForegroundColor White
Write-Host "  Wi-Fi Core debug level: None" -ForegroundColor White
Write-Host "  Erase all flash: Disabled" -ForegroundColor White
Write-Host ""

# Compile
Write-Host "Compiling..." -ForegroundColor Cyan
$compileResult = arduino-cli compile --fqbn $FQBN "$SketchPath" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Compilation failed!" -ForegroundColor Red
    $compileResult | Write-Host
    exit 1
}

Write-Host "Compilation successful!" -ForegroundColor Green
Write-Host ""

# Upload
Write-Host "Uploading to $Port..." -ForegroundColor Cyan
Write-Host "NOTE: If upload fails, manually enter boot mode:" -ForegroundColor Yellow
Write-Host "  1. Unplug USB" -ForegroundColor Yellow
Write-Host "  2. Hold BOOT button" -ForegroundColor Yellow
Write-Host "  3. Plug in USB (keep holding BOOT)" -ForegroundColor Yellow
Write-Host "  4. Release BOOT button" -ForegroundColor Yellow
Write-Host "  5. Run this script again" -ForegroundColor Yellow
Write-Host ""

$uploadResult = arduino-cli upload -p $Port --fqbn $FQBN "$SketchPath" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Upload failed!" -ForegroundColor Red
    $uploadResult | Write-Host
    Write-Host "`nTry manual boot mode (see instructions above)" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Upload successful!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "Board is now running with exact settings." -ForegroundColor Green
Write-Host ""

