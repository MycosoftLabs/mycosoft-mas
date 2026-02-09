#!/usr/bin/env python3
"""
Mycosoft Documentation Watcher → Notion Auto-Sync (Feb 08, 2026)

Watches all docs folders across Mycosoft repos for new or changed .md files
and automatically pushes them to Notion. Runs as a persistent background process.

Features:
- Monitors all repo docs/ folders + .cursor/plans for .md file changes
- Auto-syncs new documents immediately
- Auto-syncs changed documents as new versions (never replaces)
- Debounces rapid changes (waits for file to stabilize)
- Logs all activity
- Can run as Windows service or scheduled task

Usage:
    python scripts/notion_docs_watcher.py          # Run watcher (foreground)
    python scripts/notion_docs_watcher.py --daemon  # Run in background (Windows)

Requires:
    pip install watchdog requests
"""

import os
import sys
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime
from threading import Timer

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent
except ImportError:
    print("ERROR: 'watchdog' package required. Run: pip install watchdog")
    sys.exit(1)

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from notion_docs_sync import NotionDocsSync, REPO_CONFIGS

# ─── Configuration ──────────────────────────────────────────────────────────────

# Debounce time in seconds (wait for file to stop changing)
DEBOUNCE_SECONDS = 3.0

# Log file
LOG_FILE = Path(__file__).parent.parent / "data" / "notion_watcher.log"

# ─── Logging ─────────────────────────────────────────────────────────────────────

LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(str(LOG_FILE), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("notion_watcher")


class DebouncedHandler(FileSystemEventHandler):
    """
    Handles file system events with debouncing.
    Waits for a file to stop changing before syncing.
    """

    def __init__(self, syncer: NotionDocsSync):
        super().__init__()
        self.syncer = syncer
        self._timers = {}
        self._synced_count = 0

    def _on_file_ready(self, file_path: str):
        """Called when a file has stabilized (no more changes for DEBOUNCE_SECONDS)."""
        fp = Path(file_path)
        if not fp.exists():
            return
        if not fp.suffix.lower() == ".md":
            return
        if fp.stat().st_size == 0:
            return

        logger.info(f"Syncing: {file_path}")
        try:
            success = self.syncer.sync_single_file(file_path)
            if success:
                self._synced_count += 1
                logger.info(f"Synced successfully ({self._synced_count} total this session)")
            else:
                logger.info(f"Skipped (unchanged or not in tracked folder)")
        except Exception as e:
            logger.error(f"Sync failed for {file_path}: {e}")

        # Remove timer reference
        self._timers.pop(file_path, None)

    def _debounce(self, file_path: str):
        """Debounce file events - wait for file to stop changing."""
        # Cancel existing timer for this file
        if file_path in self._timers:
            self._timers[file_path].cancel()

        # Start new timer
        timer = Timer(DEBOUNCE_SECONDS, self._on_file_ready, args=[file_path])
        timer.daemon = True
        timer.start()
        self._timers[file_path] = timer

    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith(".md"):
            logger.info(f"New file detected: {event.src_path}")
            self._debounce(event.src_path)

    def on_modified(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith(".md"):
            logger.debug(f"File modified: {event.src_path}")
            self._debounce(event.src_path)


def get_watch_paths() -> list:
    """Get all valid docs paths to watch."""
    paths = []
    for repo_name, config in REPO_CONFIGS.items():
        docs_path = Path(config["docs_path"])
        if docs_path.exists():
            paths.append((repo_name, str(docs_path)))
            logger.info(f"  Watching: {repo_name} -> {docs_path}")
        else:
            logger.warning(f"  Skip (not found): {repo_name} -> {docs_path}")
    return paths


def run_watcher(syncer: NotionDocsSync):
    """Run the file watcher."""
    logger.info("=" * 60)
    logger.info("MYCOSOFT NOTION DOCS WATCHER")
    logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    watch_paths = get_watch_paths()
    if not watch_paths:
        logger.error("No valid docs paths found to watch!")
        return

    handler = DebouncedHandler(syncer)
    observer = Observer()

    for repo_name, path in watch_paths:
        observer.schedule(handler, path, recursive=True)

    observer.start()
    logger.info(f"\nWatching {len(watch_paths)} directories for .md changes...")
    logger.info("Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\nStopping watcher...")
        observer.stop()
    observer.join()
    logger.info("Watcher stopped.")


def main():
    parser = argparse.ArgumentParser(
        description="Mycosoft Docs Watcher - Auto-sync .md files to Notion"
    )
    parser.add_argument("--daemon", action="store_true", help="Run as background process")
    args = parser.parse_args()

    # Load env from .env file
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and value and key not in os.environ:
                    os.environ[key] = value

    api_key = os.environ.get("NOTION_API_KEY", "")
    database_id = os.environ.get("NOTION_DATABASE_ID", "")

    if not api_key or not database_id:
        logger.error("NOTION_API_KEY and NOTION_DATABASE_ID must be set.")
        logger.error("Run: python scripts/notion_docs_sync.py --setup")
        sys.exit(1)

    syncer = NotionDocsSync(api_key, database_id)

    # Verify connection
    logger.info("Verifying Notion API connection...")
    if not syncer.health_check():
        logger.error("Cannot connect to Notion API. Check credentials.")
        sys.exit(1)

    if args.daemon:
        # On Windows, run detached
        import subprocess
        script = str(Path(__file__).resolve())
        python = sys.executable
        proc = subprocess.Popen(
            [python, script],
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info(f"Watcher started as background process (PID: {proc.pid})")
        logger.info(f"Log file: {LOG_FILE}")
        return

    run_watcher(syncer)


if __name__ == "__main__":
    main()
