# Claude Code Autonomous Service
# Monitors task queue and executes coding tasks autonomously
# Run in background: Start-Process powershell -ArgumentList "-NoExit", "-Command", ".\scripts\claude-code-service.ps1"

param(
    [int]$PollIntervalSeconds = 10,
    [string]$Repo = "C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas",
    [double]$HourlyBudgetUSD = 20.0,
    [int]$MaxTurnsPerTask = 30
)

$ErrorActionPreference = "Continue"
$RepoPath = $Repo
$DbPath = Join-Path $RepoPath "data\claude_code_queue.db"
$LogFile = Join-Path $RepoPath "data\logs\claude-service.log"

# Ensure log directory exists
$LogDir = Split-Path $LogFile -Parent
if (-not (Test-Path $LogDir)) {
    New-Item -Path $LogDir -ItemType Directory -Force | Out-Null
}

# Logging function
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] [$Level] $Message"
    Add-Content -Path $LogFile -Value $LogMessage
    Write-Host $LogMessage
}

# Log to database
function Write-DbLog {
    param([int]$TaskId, [string]$Level, [string]$Message)
    try {
        $Query = "INSERT INTO logs (task_id, level, message) VALUES ($TaskId, '$Level', '$($Message.Replace("'", "''"))')"
        sqlite3.exe $DbPath $Query 2>$null
    } catch {}
}

# Check if SQLite3 is available
if (-not (Get-Command sqlite3 -ErrorAction SilentlyContinue)) {
    Write-Log "ERROR: sqlite3.exe not found. Install SQLite3 CLI or use PowerShell SQLite module." "ERROR"
    exit 1
}

# Check if Claude is available
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    Write-Log "ERROR: Claude Code CLI not found. Install from https://claude.ai/install.ps1" "ERROR"
    exit 1
}

# Check ANTHROPIC_API_KEY
if (-not $env:ANTHROPIC_API_KEY) {
    Write-Log "ERROR: ANTHROPIC_API_KEY environment variable not set" "ERROR"
    exit 1
}

Write-Log "Claude Code Autonomous Service started"
Write-Log "Repository: $RepoPath"
Write-Log "Poll interval: $PollIntervalSeconds seconds"
Write-Log "Hourly budget: $($HourlyBudgetUSD) USD"

# Hourly budget tracking
$HourStartTime = Get-Date
$HourlySpend = 0.0

# Main loop
while ($true) {
    try {
        # Reset hourly budget if hour has elapsed
        $Now = Get-Date
        if (($Now - $HourStartTime).TotalHours -ge 1) {
            Write-Log "Hourly budget reset. Previous hour spend: $HourlySpend USD"
            $HourStartTime = $Now
            $HourlySpend = 0.0
        }

        # Check hourly budget
        if ($HourlySpend -ge $HourlyBudgetUSD) {
            Write-Log "Hourly budget exceeded ($HourlySpend >= $HourlyBudgetUSD). Pausing until next hour." "WARN"
            Start-Sleep -Seconds 300 # Sleep 5 min
            continue
        }

        # Get next queued task (highest priority first)
        $Query = "SELECT id, description, repo FROM tasks WHERE status = 'queued' ORDER BY priority DESC, created_at ASC LIMIT 1"
        $Result = sqlite3.exe $DbPath $Query 2>$null
        
        if (-not $Result) {
            Start-Sleep -Seconds $PollIntervalSeconds
            continue
        }

        # Parse task
        $TaskId, $Description, $TaskRepo = $Result -split '\|'
        Write-Log "Processing task $TaskId : $Description"
        Write-DbLog $TaskId "INFO" "Task started by autonomous service"

        # Update status to running
        $UpdateQuery = "UPDATE tasks SET status = 'running', started_at = datetime('now') WHERE id = $TaskId"
        sqlite3.exe $DbPath $UpdateQuery 2>$null

        # Create git branch
        $BranchName = "claude-local-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
        Write-Log "Creating git branch: $BranchName"
        
        Push-Location $RepoPath
        git checkout -b $BranchName 2>&1 | Out-Null

        # Execute Claude Code
        Write-Log "Executing: claude -p `"$Description`""
        $ClaudeStartTime = Get-Date
        
        $ClaudeResult = claude -p $Description --max-turns $MaxTurnsPerTask --output-format json 2>&1
        
        $Duration = ((Get-Date) - $ClaudeStartTime).TotalSeconds
        Write-Log "Claude execution completed in $Duration seconds"

        # Parse result
        $Success = $LASTEXITCODE -eq 0
        $Status = if ($Success) { "completed" } else { "failed" }
        
        # Estimate cost (rough: $0.50 per minute)
        $EstimatedCost = [math]::Round(($Duration / 60) * 0.50, 2)
        $HourlySpend += $EstimatedCost

        # Update task
        $ResultText = $ClaudeResult | Out-String
        $ResultText = $ResultText.Replace("'", "''") # Escape quotes
        
        $CompleteQuery = "UPDATE tasks SET status = '$Status', completed_at = datetime('now'), result = '$ResultText', cost_usd = $EstimatedCost WHERE id = $TaskId"
        sqlite3.exe $DbPath $CompleteQuery 2>$null

        Write-DbLog $TaskId "INFO" "Task $Status. Cost: $EstimatedCost USD"
        Write-Log "Task $TaskId $Status. Cost: $EstimatedCost USD. Hourly total: $HourlySpend USD"

        # Return to main branch
        git checkout main 2>&1 | Out-Null
        
        Pop-Location

    } catch {
        $ErrorMsg = $_.Exception.Message
        Write-Log "ERROR in main loop: $ErrorMsg" "ERROR"
        
        if ($TaskId) {
            $ErrorEscaped = $ErrorMsg.Replace("'", "''")
            $ErrorQuery = "UPDATE tasks SET status = 'failed', completed_at = datetime('now'), error = '$ErrorEscaped' WHERE id = $TaskId"
            sqlite3.exe $DbPath $ErrorQuery 2>$null
            Write-DbLog $TaskId "ERROR" $ErrorMsg
        }
        
        Start-Sleep -Seconds 30
    }
}
