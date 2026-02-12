# Setup Claude Code Autonomous Service Autostart
# Creates scheduled task to start service on user login

param(
    [switch]$Remove
)

$TaskName = "ClaudeCodeAutonomousService"
$ScriptPath = Join-Path $PSScriptRoot "claude-code-service.ps1"
$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$ScriptPath`""
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "✓ Autostart removed for Claude Code service" -ForegroundColor Green
} else {
    # Remove existing if present
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    
    # Register new task
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings | Out-Null
    
    Write-Host "✓ Autostart configured for Claude Code service" -ForegroundColor Green
    Write-Host "  Task name: $TaskName" -ForegroundColor Cyan
    Write-Host "  Trigger: At user login" -ForegroundColor Cyan
    Write-Host "  Script: $ScriptPath" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "To manually start: Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Yellow
    Write-Host "To remove: .\setup-claude-autostart.ps1 -Remove" -ForegroundColor Yellow
}
