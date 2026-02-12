#!/usr/bin/env python3
"""Clear all pending tasks from the Claude Code queue."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "claude_code_queue.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Get counts before
cursor.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status")
before = dict(cursor.fetchall())

# Cancel all queued/running tasks
cursor.execute("UPDATE tasks SET status = 'cancelled' WHERE status IN ('queued', 'running')")
cancelled_count = cursor.rowcount

# Get counts after
cursor.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status")
after = dict(cursor.fetchall())

conn.commit()
conn.close()

print("\n=== Queue Cleared ===")
print(f"Cancelled: {cancelled_count} tasks")
print(f"\nBefore: {before}")
print(f"After: {after}")
print("\nQueue is now safe from wasting more money.")
