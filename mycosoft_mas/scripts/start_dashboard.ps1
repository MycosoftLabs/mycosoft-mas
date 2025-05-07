# Get the script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Split-Path -Parent $scriptDir
$projectDir = Split-Path -Parent $rootDir

# Set up logging
$logFile = "$rootDir\dashboard.log"
Start-Transcript -Path $logFile -Append

try {
    # Activate virtual environment
    if (Test-Path "$rootDir\venv\Scripts\activate.ps1") {
        & "$rootDir\venv\Scripts\activate.ps1"
    } else {
        Write-Host "Virtual environment not found. Creating one..."
        python -m venv "$rootDir\venv"
        & "$rootDir\venv\Scripts\activate.ps1"
    }

    # Install package in development mode
    Write-Host "Installing package in development mode..."
    pip install -e "$projectDir"

    # Check if MAS components are running
    $masComponents = @(
        @{Name="Agent Manager"; Port=7878},
        @{Name="Knowledge Graph"; Port=7879},
        @{Name="Metrics Collector"; Port=9090}
    )

    foreach ($component in $masComponents) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:$($component.Port)/health" -UseBasicParsing -ErrorAction Stop
            Write-Host "$($component.Name) is running"
        } catch {
            Write-Host "Warning: $($component.Name) is not running. Some dashboard features may be limited."
        }
    }

    # Start the dashboard
    Write-Host "Starting dashboard on port 8080..."
    $env:PYTHONPATH = "$projectDir"
    $dashboardProcess = Start-Process -FilePath "python" -ArgumentList "-m uvicorn mycosoft_mas.monitoring.dashboard:app --host 0.0.0.0 --port 8080 --reload --log-level debug" -NoNewWindow -PassThru

    # Wait for the dashboard to start
    Start-Sleep -Seconds 5

    # Check if the dashboard is running
    $dashboardUrl = "http://localhost:8080"
    try {
        $response = Invoke-WebRequest -Uri "$dashboardUrl/api/health" -UseBasicParsing -ErrorAction Stop
        Write-Host "Dashboard is running at $dashboardUrl"
        Write-Host "API Keys page: $dashboardUrl/api-keys"
        Write-Host "Metrics page: $dashboardUrl/metrics"
    } catch {
        Write-Host "Error: Unable to connect to the remote server"
        Write-Host "Check the log file at $logFile for details"
        exit 1
    }

    Write-Host "Press Ctrl+C to stop the dashboard"
    $dashboardProcess.WaitForExit()
} catch {
    Write-Host "Error: $_"
    Write-Host "Check the log file at $logFile for details"
    exit 1
} finally {
    Stop-Transcript
} 