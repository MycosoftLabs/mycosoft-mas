# Get the script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Split-Path -Parent $scriptDir

# Function to check if a process is running
function Test-ProcessRunning {
    param($ProcessName)
    return (Get-Process -Name $ProcessName -ErrorAction SilentlyContinue) -ne $null
}

# Function to start a process with error handling
function Start-ProcessWithCheck {
    param(
        [string]$ProcessName,
        [string]$Arguments,
        [string]$WorkingDirectory = $rootDir
    )
    
    if (-not (Test-ProcessRunning $ProcessName)) {
        try {
            Start-Process -FilePath $ProcessName -ArgumentList $Arguments -WorkingDirectory $WorkingDirectory -NoNewWindow
            Write-Host "Started $ProcessName successfully"
        }
        catch {
            Write-Host "Failed to start $ProcessName : $_"
        }
    }
    else {
        Write-Host "$ProcessName is already running"
    }
}

# Start Prometheus
Start-ProcessWithCheck -ProcessName "prometheus" -Arguments "--config.file=$rootDir\monitoring\prometheus.yml"

# Start Oxigraph
Start-ProcessWithCheck -ProcessName "oxigraph" -Arguments "serve --bind 0.0.0.0:7878"

# Start the MAS dashboard
Start-ProcessWithCheck -ProcessName "uvicorn" -Arguments "monitoring.dashboard:app --host 0.0.0.0 --port 8000"

# Start the MAS
Start-ProcessWithCheck -ProcessName "python" -Arguments "$rootDir\run.py"

Write-Host "All components started. Access the dashboard at http://localhost:8000"
Write-Host "Press Ctrl+C to stop all processes" 