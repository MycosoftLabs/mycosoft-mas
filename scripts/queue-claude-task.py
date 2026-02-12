#!/usr/bin/env python3
"""
Queue a task for Claude Code autonomous execution.
Usage: python queue-claude-task.py "Task description" [--repo mas] [--priority 5]
"""
import sys
import sqlite3
import argparse
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "claude_code_queue.db"

def queue_task(description: str, repo: str = "mas", priority: int = 5):
    """Queue a task for autonomous execution."""
    if not DB_PATH.exists():
        print(f"ERROR: Queue database not found at {DB_PATH}")
        print("Run: python scripts/init-claude-queue.py")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO tasks (description, repo, priority) VALUES (?, ?, ?)",
        (description, repo, priority)
    )
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    print(f"[OK] Task {task_id} queued: {description}")
    print(f"  Repo: {repo}, Priority: {priority}")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Queue a Claude Code task")
    parser.add_argument("description", help="Task description")
    parser.add_argument("--repo", default="mas", help="Repository (default: mas)")
    parser.add_argument("--priority", type=int, default=5, help="Priority 1-10 (default: 5)")
    
    args = parser.parse_args()
    
    success = queue_task(args.description, args.repo, args.priority)
    sys.exit(0 if success else 1)
