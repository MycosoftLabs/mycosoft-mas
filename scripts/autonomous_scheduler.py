"""
Autonomous Scheduler for Self-Triggering Tasks.
Created: February 12, 2026

Watches for events and auto-triggers tasks:
- Watch for code changes
- Auto-run linting/tests
- Auto-generate documentation
- Auto-update registries
- Auto-deploy when ready

Can run as a background service or scheduled task.
"""

import asyncio
import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AutonomousScheduler")


@dataclass
class ScheduledTask:
    """Definition of a scheduled task."""
    task_id: str
    name: str
    trigger_type: str  # file_change, interval, cron, manual
    action: str  # lint, test, docs, registry, deploy, gap_scan, pattern_scan
    enabled: bool = True
    interval_seconds: Optional[int] = None
    file_patterns: List[str] = field(default_factory=list)
    last_run: Optional[str] = None
    last_result: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    """Result of a task execution."""
    task_id: str
    success: bool
    duration_seconds: float
    output: Optional[str] = None
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class FileChangeHandler(FileSystemEventHandler):
    """Handler for file system events."""
    
    def __init__(self, scheduler: "AutonomousScheduler"):
        self._scheduler = scheduler
        self._debounce_cache: Dict[str, float] = {}
        self._debounce_seconds = 2.0
    
    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        
        path = event.src_path
        
        # Debounce rapid changes
        now = time.time()
        if path in self._debounce_cache:
            if now - self._debounce_cache[path] < self._debounce_seconds:
                return
        self._debounce_cache[path] = now
        
        # Trigger relevant tasks
        self._scheduler.on_file_change(path)


class AutonomousScheduler:
    """
    Scheduler for autonomous task execution.
    
    Features:
    - File change watching
    - Interval-based scheduling
    - Task execution with retry
    - Result tracking and learning feedback
    """
    
    def __init__(
        self,
        workspace_root: Optional[str] = None,
        config_file: Optional[str] = None
    ):
        self._workspace_root = Path(workspace_root or 
            "c:/Users/admin2/Desktop/MYCOSOFT/CODE/MAS/mycosoft-mas"
        )
        self._config_file = Path(config_file or 
            self._workspace_root / ".cursor" / "scheduler_config.json"
        )
        
        self._tasks: Dict[str, ScheduledTask] = {}
        self._observer: Optional[Observer] = None
        self._running = False
        self._pending_actions: List[str] = []
        
        # Action handlers
        self._action_handlers: Dict[str, Callable] = {
            "lint": self._run_lint,
            "test": self._run_tests,
            "docs": self._run_docs_build,
            "registry": self._run_registry_sync,
            "deploy": self._run_deploy,
            "gap_scan": self._run_gap_scan,
            "pattern_scan": self._run_pattern_scan,
            "skill_generate": self._run_skill_generate,
        }
        
        self._load_config()
        self._register_default_tasks()
    
    def _load_config(self) -> None:
        """Load scheduler configuration."""
        if self._config_file.exists():
            try:
                with open(self._config_file, "r") as f:
                    data = json.load(f)
                    for task_data in data.get("tasks", []):
                        task = ScheduledTask(**task_data)
                        self._tasks[task.task_id] = task
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
    
    def _save_config(self) -> None:
        """Save scheduler configuration."""
        self._config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._config_file, "w") as f:
            json.dump({
                "tasks": [
                    {
                        "task_id": t.task_id, "name": t.name,
                        "trigger_type": t.trigger_type, "action": t.action,
                        "enabled": t.enabled, "interval_seconds": t.interval_seconds,
                        "file_patterns": t.file_patterns, "last_run": t.last_run,
                        "metadata": t.metadata
                    }
                    for t in self._tasks.values()
                ]
            }, f, indent=2)
    
    def _register_default_tasks(self) -> None:
        """Register default scheduled tasks."""
        defaults = [
            ScheduledTask(
                task_id="lint_on_change",
                name="Lint on Python change",
                trigger_type="file_change",
                action="lint",
                file_patterns=["*.py"]
            ),
            ScheduledTask(
                task_id="docs_on_change",
                name="Update docs on markdown change",
                trigger_type="file_change",
                action="docs",
                file_patterns=["*.md"]
            ),
            ScheduledTask(
                task_id="registry_sync",
                name="Sync registries periodically",
                trigger_type="interval",
                action="registry",
                interval_seconds=3600  # Every hour
            ),
            ScheduledTask(
                task_id="gap_scan_daily",
                name="Daily gap scan",
                trigger_type="interval",
                action="gap_scan",
                interval_seconds=86400  # Daily
            ),
            ScheduledTask(
                task_id="pattern_scan_daily",
                name="Daily pattern scan",
                trigger_type="interval",
                action="pattern_scan",
                interval_seconds=86400  # Daily
            ),
            ScheduledTask(
                task_id="skill_generate_weekly",
                name="Weekly skill generation",
                trigger_type="interval",
                action="skill_generate",
                interval_seconds=604800,  # Weekly
                enabled=False  # Disabled by default
            ),
        ]
        
        for task in defaults:
            if task.task_id not in self._tasks:
                self._tasks[task.task_id] = task
    
    def on_file_change(self, path: str) -> None:
        """Handle file change event."""
        path_obj = Path(path)
        
        # Skip if in ignored directories
        ignored = ["node_modules", "__pycache__", ".git", ".next", "venv"]
        if any(ignored_dir in path for ignored_dir in ignored):
            return
        
        # Find matching tasks
        for task in self._tasks.values():
            if not task.enabled or task.trigger_type != "file_change":
                continue
            
            # Check file patterns
            for pattern in task.file_patterns:
                if path_obj.match(pattern):
                    logger.info(f"File change matched: {path} -> {task.name}")
                    self._pending_actions.append(task.task_id)
                    break
    
    async def execute_task(self, task_id: str) -> TaskResult:
        """Execute a scheduled task."""
        task = self._tasks.get(task_id)
        if not task:
            return TaskResult(
                task_id=task_id,
                success=False,
                duration_seconds=0,
                error=f"Task not found: {task_id}"
            )
        
        handler = self._action_handlers.get(task.action)
        if not handler:
            return TaskResult(
                task_id=task_id,
                success=False,
                duration_seconds=0,
                error=f"Unknown action: {task.action}"
            )
        
        logger.info(f"Executing task: {task.name}")
        start_time = time.time()
        
        try:
            result = await handler()
            duration = time.time() - start_time
            
            task.last_run = datetime.now(timezone.utc).isoformat()
            task.last_result = result
            
            return TaskResult(
                task_id=task_id,
                success=result.get("success", False),
                duration_seconds=duration,
                output=result.get("output")
            )
        
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Task failed: {task.name} - {e}")
            return TaskResult(
                task_id=task_id,
                success=False,
                duration_seconds=duration,
                error=str(e)
            )
    
    async def _run_lint(self) -> Dict[str, Any]:
        """Run linting."""
        try:
            result = subprocess.run(
                ["poetry", "run", "black", "--check", "mycosoft_mas/"],
                capture_output=True,
                text=True,
                cwd=str(self._workspace_root),
                timeout=120
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout[:1000]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _run_tests(self) -> Dict[str, Any]:
        """Run tests."""
        try:
            result = subprocess.run(
                ["poetry", "run", "pytest", "tests/", "-v", "--tb=short", "-x"],
                capture_output=True,
                text=True,
                cwd=str(self._workspace_root),
                timeout=300
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout[:2000]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _run_docs_build(self) -> Dict[str, Any]:
        """Rebuild documentation manifest."""
        script = self._workspace_root / "scripts" / "build_docs_manifest.py"
        if not script.exists():
            return {"success": False, "error": "Script not found"}
        
        try:
            result = subprocess.run(
                ["python", str(script)],
                capture_output=True,
                text=True,
                cwd=str(self._workspace_root),
                timeout=120
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout[:500]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _run_registry_sync(self) -> Dict[str, Any]:
        """Sync registries."""
        script = self._workspace_root / "scripts" / "sync_cursor_system.py"
        if not script.exists():
            return {"success": False, "error": "Script not found"}
        
        try:
            result = subprocess.run(
                ["python", str(script)],
                capture_output=True,
                text=True,
                cwd=str(self._workspace_root),
                timeout=60
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout[:500]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _run_deploy(self) -> Dict[str, Any]:
        """Run deployment (requires confirmation)."""
        # This is a safety measure - deployments should be explicit
        logger.warning("Auto-deploy triggered but requires manual confirmation")
        return {
            "success": False,
            "output": "Auto-deploy disabled for safety. Use manual deployment."
        }
    
    async def _run_gap_scan(self) -> Dict[str, Any]:
        """Run gap scan."""
        script = self._workspace_root / "scripts" / "gap_scan_cursor_background.py"
        if not script.exists():
            return {"success": False, "error": "Script not found"}
        
        try:
            result = subprocess.run(
                ["python", str(script)],
                capture_output=True,
                text=True,
                cwd=str(self._workspace_root),
                timeout=300
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout[:500]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _run_pattern_scan(self) -> Dict[str, Any]:
        """Run pattern scan."""
        script = self._workspace_root / "scripts" / "pattern_scanner.py"
        if not script.exists():
            return {"success": False, "error": "Script not found"}
        
        try:
            result = subprocess.run(
                ["python", str(script)],
                capture_output=True,
                text=True,
                cwd=str(self._workspace_root),
                timeout=300
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout[:500]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _run_skill_generate(self) -> Dict[str, Any]:
        """Run skill generation."""
        script = self._workspace_root / "scripts" / "skill_generator.py"
        if not script.exists():
            return {"success": False, "error": "Script not found"}
        
        try:
            result = subprocess.run(
                ["python", str(script), "--max-skills", "5"],
                capture_output=True,
                text=True,
                cwd=str(self._workspace_root),
                timeout=180
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout[:500]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def start_watching(self) -> None:
        """Start file system watching."""
        if self._observer:
            return
        
        self._observer = Observer()
        handler = FileChangeHandler(self)
        
        # Watch workspace directories
        watch_dirs = [
            self._workspace_root / "mycosoft_mas",
            self._workspace_root / "scripts",
            self._workspace_root / "docs",
            self._workspace_root / ".cursor",
        ]
        
        for watch_dir in watch_dirs:
            if watch_dir.exists():
                self._observer.schedule(handler, str(watch_dir), recursive=True)
        
        self._observer.start()
        logger.info("File watching started")
    
    def stop_watching(self) -> None:
        """Stop file system watching."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
            logger.info("File watching stopped")
    
    async def run_pending(self) -> List[TaskResult]:
        """Run all pending tasks."""
        results = []
        
        # Deduplicate pending actions
        unique_actions = list(set(self._pending_actions))
        self._pending_actions.clear()
        
        for task_id in unique_actions:
            result = await self.execute_task(task_id)
            results.append(result)
        
        return results
    
    async def check_interval_tasks(self) -> List[TaskResult]:
        """Check and run interval-based tasks."""
        results = []
        now = datetime.now(timezone.utc)
        
        for task in self._tasks.values():
            if not task.enabled or task.trigger_type != "interval":
                continue
            
            if not task.interval_seconds:
                continue
            
            # Check if due
            if task.last_run:
                last_run = datetime.fromisoformat(task.last_run.replace("Z", "+00:00"))
                elapsed = (now - last_run).total_seconds()
                if elapsed < task.interval_seconds:
                    continue
            
            result = await self.execute_task(task.task_id)
            results.append(result)
        
        return results
    
    async def run_loop(self, check_interval: int = 60) -> None:
        """Run the scheduler loop."""
        self._running = True
        self.start_watching()
        
        logger.info("Autonomous scheduler started")
        
        try:
            while self._running:
                # Process pending file-change tasks
                if self._pending_actions:
                    results = await self.run_pending()
                    for result in results:
                        status = "✓" if result.success else "✗"
                        logger.info(f"{status} {result.task_id}: {result.duration_seconds:.1f}s")
                
                # Check interval tasks
                results = await self.check_interval_tasks()
                for result in results:
                    status = "✓" if result.success else "✗"
                    logger.info(f"{status} {result.task_id}: {result.duration_seconds:.1f}s")
                
                await asyncio.sleep(check_interval)
        
        finally:
            self.stop_watching()
            self._save_config()
            logger.info("Autonomous scheduler stopped")
    
    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False


def main():
    """Run the autonomous scheduler."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Autonomous task scheduler")
    parser.add_argument("--once", action="store_true", help="Run all tasks once and exit")
    parser.add_argument("--task", type=str, help="Run a specific task")
    parser.add_argument("--interval", type=int, default=60, help="Check interval in seconds")
    
    args = parser.parse_args()
    
    scheduler = AutonomousScheduler()
    
    if args.task:
        # Run specific task
        result = asyncio.run(scheduler.execute_task(args.task))
        print(f"\n{'✓' if result.success else '✗'} {result.task_id}")
        print(f"Duration: {result.duration_seconds:.1f}s")
        if result.output:
            print(f"Output: {result.output[:500]}")
        if result.error:
            print(f"Error: {result.error}")
    
    elif args.once:
        # Run all enabled tasks once
        async def run_all():
            for task_id in scheduler._tasks:
                if scheduler._tasks[task_id].enabled:
                    result = await scheduler.execute_task(task_id)
                    status = "✓" if result.success else "✗"
                    print(f"{status} {task_id}: {result.duration_seconds:.1f}s")
        
        asyncio.run(run_all())
    
    else:
        # Run continuous loop
        try:
            asyncio.run(scheduler.run_loop(check_interval=args.interval))
        except KeyboardInterrupt:
            print("\nScheduler stopped")


if __name__ == "__main__":
    main()
