"""
Audit Logger for MYCA

Structured JSON logging for all MYCA actions with daily rotation
and 90-day retention.
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_LOG_DIR = os.getenv("MYCA_LOG_DIR", "/opt/myca/logs")


class AuditLogger:
    """Structured audit logging with daily file rotation."""

    SUBDIRS = ("workflows", "api", "credentials", "security")
    RETENTION_DAYS = 90

    def __init__(self, log_dir: str = DEFAULT_LOG_DIR):
        self._log_dir = Path(log_dir)
        self._ensure_dirs()

    def _ensure_dirs(self):
        for sub in self.SUBDIRS:
            d = self._log_dir / sub
            d.mkdir(parents=True, exist_ok=True)

    def _get_log_file(self, category: str) -> Path:
        if category not in self.SUBDIRS:
            category = "api"
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self._log_dir / category / f"{date_str}.jsonl"

    async def log_action(
        self,
        actor: str,
        action: str,
        target: str,
        result: str,
        category: str = "api",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": actor,
            "action": action,
            "target": target,
            "result": result,
            "metadata": metadata or {},
        }

        log_file = self._get_log_file(category)
        try:
            with open(log_file, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception as exc:
            logger.error("Failed to write audit log: %s", exc)

    async def log_tool_call(
        self,
        tool_name: str,
        args: Dict[str, Any],
        result: str,
        session_id: Optional[str] = None,
        actor: str = "myca",
    ):
        await self.log_action(
            actor=actor,
            action=f"tool:{tool_name}",
            target=str(args.get("command", args.get("url", "")))[:200],
            result=result,
            category="api",
            metadata={"session_id": session_id, "args_preview": str(args)[:500]},
        )

    async def log_security_event(
        self,
        event_type: str,
        details: Dict[str, Any],
        severity: str = "info",
    ):
        await self.log_action(
            actor="security",
            action=event_type,
            target=details.get("target", ""),
            result=severity,
            category="security",
            metadata=details,
        )

    async def cleanup_old_logs(self):
        """Remove log files older than RETENTION_DAYS."""
        cutoff = time.time() - (self.RETENTION_DAYS * 86400)
        removed = 0
        for sub in self.SUBDIRS:
            d = self._log_dir / sub
            if not d.exists():
                continue
            for f in d.iterdir():
                if f.suffix == ".jsonl" and f.stat().st_mtime < cutoff:
                    f.unlink()
                    removed += 1
        if removed:
            logger.info("Cleaned up %d old audit log files", removed)
