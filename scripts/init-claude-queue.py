#!/usr/bin/env python3
"""
Initialize Claude Code task queue database.
Creates SQLite database with tasks and logs tables.
"""
import sqlite3
from pathlib import Path
from datetime import datetime

# Ensure data directory exists
data_dir = Path(__file__).parent.parent / "data"
data_dir.mkdir(exist_ok=True)

# Create logs directory
logs_dir = data_dir / "logs"
logs_dir.mkdir(exist_ok=True)

# Database path
db_path = data_dir / "claude_code_queue.db"

# Connect and create tables
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Tasks table
cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT NOT NULL,
    repo TEXT NOT NULL DEFAULT 'mas',
    priority INTEGER NOT NULL DEFAULT 5,
    status TEXT NOT NULL DEFAULT 'queued',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    result TEXT,
    error TEXT,
    cost_usd REAL,
    turns_used INTEGER
)
""")

# Logs table
cursor.execute("""
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks (id)
)
""")

# Indexes
cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_task ON logs(task_id)")

conn.commit()
conn.close()

print(f"[OK] Claude Code task queue initialized: {db_path}")
print(f"[OK] Logs directory: {logs_dir}")
print("\nNext steps:")
print("1. Set ANTHROPIC_API_KEY environment variable")
print("2. Start API bridge: python scripts/claude-code-api-bridge.py")
print("3. Start service: .\\scripts\\claude-code-service.ps1")
