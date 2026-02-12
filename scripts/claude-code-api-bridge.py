#!/usr/bin/env python3
"""
Claude Code API Bridge - FastAPI server for remote task execution.
Receives tasks from VMs or other machines and queues them for local execution.
Port: 8350
"""
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Setup logging
log_file = Path(__file__).parent.parent / "data" / "logs" / "claude-api.log"
log_file.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Claude Code API Bridge",
    description="Local Claude Code task queue and execution API",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database path
DB_PATH = Path(__file__).parent.parent / "data" / "claude_code_queue.db"

# Models
class TaskCreate(BaseModel):
    description: str
    repo: str = "mas"
    priority: int = 5

class TaskResponse(BaseModel):
    id: int
    description: str
    repo: str
    status: str
    created_at: str
    result: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    queue_size: int
    active_tasks: int
    timestamp: str

# Helper functions
def get_db():
    """Get database connection."""
    if not DB_PATH.exists():
        raise HTTPException(status_code=500, detail="Queue database not initialized. Run init-claude-queue.py")
    return sqlite3.connect(DB_PATH)

def log_to_db(task_id: int, level: str, message: str):
    """Log message to database."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO logs (task_id, level, message) VALUES (?, ?, ?)",
        (task_id, level, message)
    )
    conn.commit()
    conn.close()

# Endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get queue stats
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'queued'")
        queue_size = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'running'")
        active_tasks = cursor.fetchone()[0]
        
        conn.close()
        
        return HealthResponse(
            status="healthy",
            queue_size=queue_size,
            active_tasks=active_tasks,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/task", response_model=TaskResponse)
async def create_task(task: TaskCreate):
    """Create a new coding task."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO tasks (description, repo, priority) VALUES (?, ?, ?)",
            (task.description, task.repo, task.priority)
        )
        task_id = cursor.lastrowid
        conn.commit()
        
        # Get created task
        cursor.execute("SELECT id, description, repo, status, created_at FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        conn.close()
        
        logger.info(f"Task {task_id} created: {task.description[:50]}...")
        log_to_db(task_id, "INFO", "Task created")
        
        return TaskResponse(
            id=row[0],
            description=row[1],
            repo=row[2],
            status=row[3],
            created_at=row[4]
        )
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks/recent", response_model=List[TaskResponse])
async def get_recent_tasks(limit: int = 10):
    """Get recent tasks."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, description, repo, status, created_at, result FROM tasks ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        return [
            TaskResponse(
                id=row[0],
                description=row[1],
                repo=row[2],
                status=row[3],
                created_at=row[4],
                result=row[5]
            )
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Failed to get recent tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/task/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int):
    """Get task by ID."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, description, repo, status, created_at, result FROM tasks WHERE id = ?",
            (task_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        return TaskResponse(
            id=row[0],
            description=row[1],
            repo=row[2],
            status=row[3],
            created_at=row[4],
            result=row[5]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/queue/status")
async def queue_status():
    """Get detailed queue status."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Status counts
        cursor.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status")
        status_counts = dict(cursor.fetchall())
        
        # Recent activity
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE created_at > datetime('now', '-1 hour')")
        recent_tasks = cursor.fetchone()[0]
        
        # Average task time (completed tasks)
        cursor.execute("""
            SELECT AVG(CAST((julianday(completed_at) - julianday(started_at)) * 86400 AS INTEGER))
            FROM tasks 
            WHERE status = 'completed' AND started_at IS NOT NULL AND completed_at IS NOT NULL
        """)
        avg_time = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "status_counts": status_counts,
            "recent_tasks_1h": recent_tasks,
            "avg_completion_time_seconds": avg_time,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get queue status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    logger.info("Starting Claude Code API Bridge on port 8350")
    uvicorn.run(app, host="0.0.0.0", port=8350)
