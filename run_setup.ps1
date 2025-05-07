# Script to run setup with administrator privileges
$scriptPath = $PSScriptRoot
$setupScript = Join-Path $scriptPath "setup_all.ps1"

# Create a temporary script that will run with elevated privileges
$tempScript = Join-Path $env:TEMP "run_setup_elevated.ps1"
@"
# Set execution policy
Set-ExecutionPolicy Bypass -Scope Process -Force
Set-ExecutionPolicy Bypass -Scope CurrentUser -Force

# Run the setup script
& '$setupScript'
"@ | Out-File -FilePath $tempScript -Encoding UTF8

# Create a scheduled task to run the script
$taskName = "MycosoftMASSetup"
$taskDescription = "Run Mycosoft MAS setup script with administrator privileges"

# Create the task action
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$tempScript`""

# Create the task trigger (run once)
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddSeconds(2)

# Create the task settings
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Register the task
Register-ScheduledTask -TaskName $taskName `
    -Description $taskDescription `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -RunLevel Highest `
    -Force

# Start the task
Start-ScheduledTask -TaskName $taskName

# Wait for the task to complete
Write-Host "Setup is running with administrator privileges..."
Write-Host "Please wait for the installation to complete."

# Monitor the task
while ((Get-ScheduledTask -TaskName $taskName).State -eq 'Running') {
    Start-Sleep -Seconds 5
}

# Remove the task when done
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false

# Clean up
Remove-Item $tempScript -Force

Write-Host "Setup completed. Please restart your computer to ensure all installations are properly configured." 