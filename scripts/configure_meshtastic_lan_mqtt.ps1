#Requires -Version 5.1
<#
.SYNOPSIS
  Configure Meshtastic radios (USB) for Mycosoft LAN MQTT (plaintext 1883 on VM 196).

.DESCRIPTION
  Stops MycoBrain briefly so it cannot hold Espressif COM ports (same VID as many Meshtastic boards).
  Loads MQTT password from WEBSITE website\.credentials.local (MQTT_BROKER_PASSWORD).

  Optional Wi-Fi (required before MQTT can reach the LAN broker): set env vars before running:
    $env:MESHTASTIC_WIFI_SSID = 'YourSSID'
    $env:MESHTASTIC_WIFI_PSK  = 'YourWiFiPassword'

  Without Wi-Fi env vars, this script only writes broker URL / auth / TLS flags and leaves mqtt.enabled false
  unless you pass -EnableMqtt (risky without Wi-Fi — can reboot/crash per firmware).

.PARAMETER Ports
  COM ports to configure, e.g. COM15 COM11. If omitted, lists current USB serial ports (you must pass explicit ports).

.PARAMETER BrokerHost
  Default 192.168.0.196 (matches docs).

.PARAMETER MqttUser
  Default mycobrain (Mosquitto ACL on VM 196).

.PARAMETER TimeoutSec
  Meshtastic CLI serial timeout (default 90).

.EXAMPLE
  .\configure_meshtastic_lan_mqtt.ps1 -Ports COM15,COM11

.EXAMPLE
  $env:MESHTASTIC_WIFI_SSID='OfficeLAN'; $env:MESHTASTIC_WIFI_PSK='***'
  .\configure_meshtastic_lan_mqtt.ps1 -Ports COM15 -EnableMqtt
#>

param(
    [Parameter(Mandatory = $false)]
    [string[]]$Ports = @(),

    [string]$BrokerHost = "192.168.0.196",

    [string]$MqttUser = "mycobrain",

    [string]$CredentialsFile = "",

    [int]$TimeoutSec = 90,

    [switch]$EnableMqtt,

    [switch]$NoStopMycoBrain,

    [switch]$NoStartMycoBrain
)

# Continue: Meshtastic CLI writes tracebacks to stderr; Stop would abort before COM15 / MycoBrain restart.
$ErrorActionPreference = "Continue"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$masRoot = Split-Path -Parent $here

function Import-DotEnvFile {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return }
    Get-Content $Path | ForEach-Object {
        if ($_ -match '^([^#=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $val = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($key, $val, "Process")
        }
    }
}

$candidates = @(
    $(Join-Path $masRoot ".credentials.local"),
    $(Join-Path (Split-Path -Parent $masRoot) "WEBSITE\website\.credentials.local"),
    $(Join-Path $env:USERPROFILE "Desktop\MYCOSOFT\CODE\WEBSITE\website\.credentials.local")
)
if ($CredentialsFile) { $candidates = @($CredentialsFile) + $candidates }
foreach ($p in $candidates) {
    Import-DotEnvFile $p
}

$mqttPass = $env:MQTT_BROKER_PASSWORD
if (-not $mqttPass) {
    Write-Error "MQTT_BROKER_PASSWORD not set. Add it to WEBSITE\website\.credentials.local or process env."
}

$wifiSsid = $env:MESHTASTIC_WIFI_SSID
$wifiPsk = $env:MESHTASTIC_WIFI_PSK

$mtCandidates = @(
    $(Join-Path $env:APPDATA "Python\Python313\Scripts\meshtastic.exe"),
    $(Join-Path $env:LOCALAPPDATA "Programs\Python\Python313\Scripts\meshtastic.exe")
)
$meshtasticExe = $null
foreach ($c in $mtCandidates) {
    if (Test-Path $c) { $meshtasticExe = $c; break }
}
if (-not $meshtasticExe) {
    $cmd = Get-Command meshtastic -ErrorAction SilentlyContinue
    if ($cmd) { $meshtasticExe = $cmd.Source }
}
if (-not $meshtasticExe) {
    Write-Error "meshtastic CLI not found. Install: pip install meshtastic"
}

$mycobrainScript = Join-Path $here "mycobrain-service.ps1"
$stoppedMycoBrain = $false
if (-not $NoStopMycoBrain -and (Test-Path $mycobrainScript)) {
    Write-Host "[INFO] Stopping MycoBrain so ESP32 COM ports are free for Meshtastic CLI..."
    & $mycobrainScript stop
    $stoppedMycoBrain = $true
    Start-Sleep -Seconds 2
}

if ($Ports.Count -eq 0) {
    Write-Host "[INFO] No -Ports specified. USB serial COM devices:"
    Get-PnpDevice -Class Ports -ErrorAction SilentlyContinue |
        Where-Object { $_.Status -eq 'OK' -and $_.FriendlyName -match 'USB' } |
        ForEach-Object { $_.FriendlyName }
    Write-Host "Re-run with: .\configure_meshtastic_lan_mqtt.ps1 -Ports COM15,COM11,..."
    if ($stoppedMycoBrain -and -not $NoStartMycoBrain -and (Test-Path $mycobrainScript)) {
        & $mycobrainScript start
    }
    exit 0
}

try {
    foreach ($port in $Ports) {
        Write-Host "`n=== Configuring $port ==="
        $mtArgs = @(
            "--port", $port,
            "--timeout", "$TimeoutSec",
            "--set", "mqtt.address", $BrokerHost,
            "--set", "mqtt.tls_enabled", "false",
            "--set", "mqtt.username", $MqttUser,
            "--set", "mqtt.password", $mqttPass
        )

        # Payload encryption over MQTT — disable for plaintext LAN broker path (see team doc).
        $mtArgs += @("--set", "mqtt.encryption_enabled", "false")

        if ($wifiSsid -and $wifiPsk) {
            $mtArgs += @(
                "--set", "network.wifi_ssid", $wifiSsid,
                "--set", "network.wifi_psk", $wifiPsk,
                "--set", "network.wifi_enabled", "true"
            )
        }

        if ($EnableMqtt) {
            $mtArgs += @("--set", "mqtt.enabled", "true")
        }
        else {
            $mtArgs += @("--set", "mqtt.enabled", "false")
            Write-Host "[INFO] mqtt.enabled left false (omit -EnableMqtt). Enable Wi-Fi env vars first; then re-run with -EnableMqtt."
        }

        $rawOut = & $meshtasticExe @mtArgs 2>&1
        $exitCode = $LASTEXITCODE
        foreach ($line in $rawOut) {
            $s = "$line"
            if ($s -match '(?i)mqtt\.password|password\s+to') {
                Write-Host "Set mqtt.password to **** (hidden)"
            }
            else {
                Write-Host $s
            }
        }
        if ($exitCode -ne 0) {
            Write-Warning "meshtastic exited $exitCode for $port - check cable, driver, or double-reset the radio."
        }
        else {
            Write-Host "[OK] $port configured."
            $verifyOut = & $meshtasticExe "--port", $port, "--timeout", "$TimeoutSec", "--get", "mqtt.address", "--get", "mqtt.enabled", "--get", "mqtt.tls_enabled" 2>&1
            foreach ($line in $verifyOut) { Write-Host "$line" }
        }
    }
}
finally {
    if ($stoppedMycoBrain -and -not $NoStartMycoBrain -and (Test-Path $mycobrainScript)) {
        Write-Host "`n[INFO] Restarting MycoBrain..."
        & $mycobrainScript start
    }
}

Write-Host ""
Write-Host "Done."
Write-Host "If Meshtastic CLI fails with access denied or timeouts while MycoBrain is running, set MYCOBRAIN_ALLOWED_PORTS"
Write-Host 'Example: set MYCOBRAIN_ALLOWED_PORTS=COM7 so Meshtastic radios are not opened as MDP devices.'
