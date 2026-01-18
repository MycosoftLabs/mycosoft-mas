#!/usr/bin/env python3
"""Set up MycoBrain service on local Windows machine to connect COM7 and bridge to sandbox"""

import subprocess
import os
import json
from pathlib import Path

# Paths
website_dir = Path(r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website")
service_script = website_dir / "services" / "mycobrain" / "mycobrain_service.py"
logs_dir = website_dir / "logs"

print("=" * 80)
print("SETTING UP MYCOBRAIN LOCAL SERVICE FOR COM7")
print("=" * 80)

# 1. Check if service script exists
print("\n[STEP 1] Checking service script...")
if service_script.exists():
    print(f"  [OK] Found: {service_script}")
else:
    print(f"  [ERROR] Service script not found: {service_script}")
    exit(1)

# 2. Create logs directory
print("\n[STEP 2] Creating logs directory...")
logs_dir.mkdir(exist_ok=True)
print(f"  [OK] Logs directory: {logs_dir}")

# 3. Check if service is already running
print("\n[STEP 3] Checking if service is running...")
try:
    result = subprocess.run(
        ["powershell", "-Command", 
         "Get-Process python -ErrorAction SilentlyContinue | Where-Object { (Get-CimInstance Win32_Process -Filter \"ProcessId = $($_.Id)\").CommandLine -like '*mycobrain_service*' }"],
        capture_output=True,
        text=True
    )
    if result.stdout.strip():
        print("  [INFO] MycoBrain service appears to be running")
        print("  [ACTION] Will restart it")
    else:
        print("  [INFO] Service not running")
except:
    print("  [INFO] Could not check service status")

# 4. Create startup script
print("\n[STEP 4] Creating startup script...")

startup_script = website_dir / "scripts" / "start_mycobrain_service.ps1"
startup_content = f"""# Start MycoBrain Service for COM7
# Auto-starts in background and logs to file

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$websiteDir = Split-Path -Parent $scriptDir
$serviceScript = Join-Path $websiteDir "services\\mycobrain\\mycobrain_service.py"
$logFile = Join-Path $websiteDir "logs\\mycobrain-service.log"

# Create logs directory
New-Item -ItemType Directory -Force -Path (Split-Path $logFile) | Out-Null

# Stop existing service if running
Write-Host "Checking for existing MycoBrain service..."
$existing = Get-Process python -ErrorAction SilentlyContinue | Where-Object {{
    try {{
        $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
        $cmd -like "*mycobrain_service*"
    }} catch {{
        $false
    }}
}}

if ($existing) {{
    Write-Host "Stopping existing service..."
    $existing | Stop-Process -Force
    Start-Sleep -Seconds 2
}}

# Start new service
Write-Host "Starting MycoBrain service..."
Write-Host "  Service: $serviceScript"
Write-Host "  Log: $logFile"

Set-Location $websiteDir

$process = Start-Process python -ArgumentList "`"$serviceScript`"" -PassThru -WindowStyle Hidden -RedirectStandardOutput $logFile -RedirectStandardError $logFile

Start-Sleep -Seconds 3

# Check if it started
if (-not (Get-Process -Id $process.Id -ErrorAction SilentlyContinue)) {{
    Write-Host "[ERROR] Service failed to start. Check log: $logFile" -ForegroundColor Red
    exit 1
}}

Write-Host "[OK] MycoBrain service started (PID: $($process.Id))" -ForegroundColor Green
Write-Host "  Log file: $logFile"
Write-Host "  To view logs: Get-Content $logFile -Tail 50 -Wait"
"""

startup_script.write_text(startup_content)
print(f"  [OK] Created: {startup_script}")

# 5. Create scheduled task for auto-start
print("\n[STEP 5] Creating scheduled task for auto-start...")

task_name = "MycoBrainService"
task_script = f"""
$taskName = "{task_name}"
$scriptPath = "{startup_script}"

# Remove existing task if present
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

# Create new task
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""
$trigger = New-ScheduledTaskTrigger -AtLogOn
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable:$false

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Auto-start MycoBrain service for COM7 device" | Out-Null

Write-Host "[OK] Scheduled task created: $taskName"
"""

task_script_path = website_dir / "scripts" / "setup_mycobrain_task.ps1"
task_script_path.write_text(task_script)

print(f"  [OK] Task setup script created: {task_script_path}")
print("  [ACTION REQUIRED] Run as Administrator:")
print(f"    powershell -ExecutionPolicy Bypass -File \"{task_script_path}\"")

# 6. Test service startup
print("\n[STEP 6] Starting service now...")
try:
    result = subprocess.run(
        ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(startup_script)],
        capture_output=True,
        text=True,
        cwd=str(website_dir)
    )
    print(result.stdout)
    if result.returncode == 0:
        print("  [OK] Service started successfully")
    else:
        print(f"  [WARNING] Service may not have started: {result.stderr}")
except Exception as e:
    print(f"  [ERROR] Failed to start service: {e}")

# 7. Test service endpoint
print("\n[STEP 7] Testing service endpoint...")
import time
time.sleep(3)

try:
    import requests
    response = requests.get("http://localhost:8003/health", timeout=5)
    if response.status_code == 200:
        print("  [OK] Service is responding on port 8003")
        data = response.json()
        print(f"      Status: {data.get('status', 'unknown')}")
    else:
        print(f"  [WARNING] Service returned: {response.status_code}")
except Exception as e:
    print(f"  [WARNING] Could not connect to service: {e}")
    print("  [INFO] Service may still be starting. Check logs:")

print("\n" + "=" * 80)
print("SETUP COMPLETE")
print("=" * 80)
print(f"\nService script: {service_script}")
print(f"Startup script: {startup_script}")
print(f"Log file: {logs_dir / 'mycobrain-service.log'}")
print("\nTo start service manually:")
print(f"  powershell -ExecutionPolicy Bypass -File \"{startup_script}\"")
print("\nTo set up auto-start (run as Administrator):")
print(f"  powershell -ExecutionPolicy Bypass -File \"{task_script_path}\"")
