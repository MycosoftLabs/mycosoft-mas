#!/usr/bin/env python3
"""
Claude Code Autonomous Service - Python version
Monitors task queue and executes coding tasks autonomously.
No external dependencies required (uses Python's built-in sqlite3).
"""
import os
import sys
import time
import logging
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

# Setup
REPO_ROOT = Path(__file__).parent.parent
DB_PATH = REPO_ROOT / "data" / "claude_code_queue.db"
LOG_FILE = REPO_ROOT / "data" / "logs" / "claude-service.log"

# Ensure log directory
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
POLL_INTERVAL = 10  # seconds
HOURLY_BUDGET_USD = 20.0
MAX_TURNS_PER_TASK = 30
COST_PER_MINUTE = 0.50  # Rough estimate

# Budget tracking
hourly_spend = 0.0
hour_start_time = datetime.now()


def get_db():
    """Get database connection."""
    return sqlite3.connect(DB_PATH)


def log_to_db(task_id: int, level: str, message: str):
    """Log message to database."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO logs (task_id, level, message) VALUES (?, ?, ?)",
            (task_id, level, message)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to log to DB: {e}")


def get_next_task():
    """Get next queued task (highest priority)."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, description, repo FROM tasks WHERE status = 'queued' ORDER BY priority DESC, created_at ASC LIMIT 1"
    )
    row = cursor.fetchone()
    conn.close()
    return row


def update_task_status(task_id: int, status: str, **kwargs):
    """Update task status and optional fields."""
    conn = get_db()
    cursor = conn.cursor()
    
    fields = ["status = ?"]
    values = [status]
    
    if status == "running":
        fields.append("started_at = datetime('now')")
    elif status in ["completed", "failed"]:
        fields.append("completed_at = datetime('now')")
    
    if "result" in kwargs:
        fields.append("result = ?")
        values.append(kwargs["result"])
    
    if "error" in kwargs:
        fields.append("error = ?")
        values.append(kwargs["error"])
    
    if "cost_usd" in kwargs:
        fields.append("cost_usd = ?")
        values.append(kwargs["cost_usd"])
    
    if "turns_used" in kwargs:
        fields.append("turns_used = ?")
        values.append(kwargs["turns_used"])
    
    values.append(task_id)
    
    query = f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?"
    cursor.execute(query, values)
    conn.commit()
    conn.close()


def execute_claude_task(description: str, repo: str) -> dict:
    """Execute a Claude Code task."""
    try:
        # Create git branch
        branch_name = f"claude-local-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        logger.info(f"Creating git branch: {branch_name}")
        
        subprocess.run(
            ["git", "checkout", "-b", branch_name],
            cwd=REPO_ROOT,
            capture_output=True,
            check=False
        )
        
        # Execute Claude Code
        logger.info(f"Executing: claude -p \"{description[:50]}...\"")
        start_time = time.time()
        
        result = subprocess.run(
            ["claude", "-p", description, "--max-turns", str(MAX_TURNS_PER_TASK), "--output-format", "json"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )
        
        duration = time.time() - start_time
        logger.info(f"Claude execution completed in {duration:.1f} seconds")
        
        # Return to main branch
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=REPO_ROOT,
            capture_output=True,
            check=False
        )
        
        # Calculate cost
        cost = round((duration / 60) * COST_PER_MINUTE, 2)
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None,
            "duration": duration,
            "cost": cost,
            "branch": branch_name
        }
        
    except subprocess.TimeoutExpired:
        logger.error("Claude execution timed out after 10 minutes")
        return {
            "success": False,
            "error": "Execution timed out after 10 minutes",
            "duration": 600,
            "cost": 5.0
        }
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "duration": 0,
            "cost": 0
        }


def main():
    """Main service loop."""
    global hourly_spend, hour_start_time
    
    # Check prerequisites
    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.error("ANTHROPIC_API_KEY not set")
        sys.exit(1)
    
    # Check Claude CLI
    try:
        subprocess.run(["claude", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("Claude Code CLI not found or not working")
        sys.exit(1)
    
    logger.info("Claude Code Autonomous Service started")
    logger.info(f"Repository: {REPO_ROOT}")
    logger.info(f"Poll interval: {POLL_INTERVAL} seconds")
    logger.info(f"Hourly budget: ${HOURLY_BUDGET_USD}")
    
    # Main loop
    while True:
        try:
            # Reset hourly budget
            now = datetime.now()
            if (now - hour_start_time).total_seconds() >= 3600:
                logger.info(f"Hourly budget reset. Previous hour spend: ${hourly_spend:.2f}")
                hour_start_time = now
                hourly_spend = 0.0
            
            # Check budget
            if hourly_spend >= HOURLY_BUDGET_USD:
                logger.warning(f"Hourly budget exceeded (${hourly_spend:.2f} >= ${HOURLY_BUDGET_USD}). Pausing.")
                time.sleep(300)  # 5 minutes
                continue
            
            # Get next task
            task = get_next_task()
            if not task:
                time.sleep(POLL_INTERVAL)
                continue
            
            task_id, description, repo = task
            logger.info(f"Processing task {task_id}: {description[:50]}...")
            log_to_db(task_id, "INFO", "Task started by autonomous service")
            
            # Update to running
            update_task_status(task_id, "running")
            
            # Execute
            result = execute_claude_task(description, repo)
            
            # Update hourly spend
            hourly_spend += result["cost"]
            
            # Update task
            if result["success"]:
                update_task_status(
                    task_id,
                    "completed",
                    result=result["output"],
                    cost_usd=result["cost"]
                )
                logger.info(f"Task {task_id} completed. Cost: ${result['cost']:.2f}, Branch: {result.get('branch', 'N/A')}")
                log_to_db(task_id, "INFO", f"Task completed. Cost: ${result['cost']:.2f}")
            else:
                update_task_status(
                    task_id,
                    "failed",
                    error=result.get("error", "Unknown error"),
                    cost_usd=result["cost"]
                )
                logger.error(f"Task {task_id} failed: {result.get('error', 'Unknown')}")
                log_to_db(task_id, "ERROR", result.get("error", "Unknown error"))
            
            logger.info(f"Hourly spend: ${hourly_spend:.2f} / ${HOURLY_BUDGET_USD}")
            
        except KeyboardInterrupt:
            logger.info("Service stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
            time.sleep(30)


if __name__ == "__main__":
    main()
