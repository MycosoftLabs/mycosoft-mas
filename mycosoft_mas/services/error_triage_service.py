"""
Error Triage Service for MYCA Autonomous Self-Healing.

Classifies errors (auto-fixable vs requires-human), stores patterns in MINDEX,
and dispatches fix requests to n8n webhook or MCP. Part of the autonomous
self-healing pipeline (FEB24_2026).

Author: MYCA / Autonomous Self-Healing Plan
Created: February 24, 2026
"""

import asyncio
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class FixFeasibility(Enum):
    """Whether an error can be auto-fixed."""
    AUTO_FIXABLE = "auto_fixable"
    REQUIRES_HUMAN = "requires_human"
    UNKNOWN = "unknown"


class ErrorSource(Enum):
    """Where the error originated."""
    CHAT = "chat"
    CONSCIOUSNESS = "consciousness"
    API = "api"
    BACKGROUND_TASK = "background_task"
    VM_HEALTH = "vm_health"


@dataclass
class TriageResult:
    """Result of error triage."""
    error_id: str
    feasibility: FixFeasibility
    suggested_fix: Optional[str] = None
    file_path: Optional[str] = None
    line_hint: Optional[str] = None
    deploy_target: Optional[str] = None  # "mas", "website", "mindex"
    dispatch_payload: Dict[str, Any] = field(default_factory=dict)


# Known auto-fixable error patterns (error_message_substring -> (file_hint, fix_hint))
AUTO_FIX_PATTERNS: Dict[str, tuple] = {
    "'dict' object has no attribute 'to_prompt_context'": (
        "mycosoft_mas/consciousness/deliberation.py",
        "Add type check: if hasattr(working_context, 'to_prompt_context') before calling",
    ),
    "AttributeError": (
        None,
        "Add hasattr/type check before attribute access",
    ),
    "ModuleNotFoundError": (
        None,
        "Add missing import or install dependency",
    ),
    "ImportError": (
        None,
        "Fix import path or circular dependency",
    ),
    "NameError": (
        None,
        "Define missing variable or fix typo",
    ),
    "TypeError": (
        None,
        "Add type check or fix argument types",
    ),
    "KeyError": (
        None,
        "Add .get() with default or check key existence",
    ),
    "connection refused": (
        None,
        "Restart service or check VM health",
    ),
    "timeout": (
        None,
        "Increase timeout or add retry",
    ),
    "ECONNREFUSED": (
        None,
        "Check VM/service is running",
    ),
}

# Patterns that require human review
HUMAN_REVIEW_PATTERNS: List[str] = [
    "security",
    "credential",
    "password",
    "secret",
    "auth",
    "permission denied",
    "unauthorized",
    "database migration",
    "schema",
]


class ErrorTriageService:
    """
    Triage errors for autonomous fix pipeline.
    Classifies, logs, and dispatches fix requests.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._error_logger: Optional[Any] = None
        self._n8n_webhook_url = os.getenv(
            "N8N_AUTONOMOUS_FIX_WEBHOOK",
            self.config.get("n8n_autonomous_fix_webhook", ""),
        )
        self._mas_api_url = os.getenv(
            "MAS_API_URL",
            self.config.get("mas_api_url", "http://192.168.0.188:8001"),
        )
        self._triage_history: List[Dict[str, Any]] = []
        self._max_history = 500

    def set_error_logger(self, error_logger: Any) -> None:
        """Inject ErrorLoggingService for persistence."""
        self._error_logger = error_logger

    def _classify_error(self, error_message: str, source: str) -> TriageResult:
        """Classify error and determine fix feasibility."""
        from uuid import uuid4

        error_id = f"triage_{uuid4().hex[:12]}"
        msg_lower = error_message.lower()

        # Check human-review patterns first
        for pattern in HUMAN_REVIEW_PATTERNS:
            if pattern in msg_lower:
                return TriageResult(
                    error_id=error_id,
                    feasibility=FixFeasibility.REQUIRES_HUMAN,
                    suggested_fix=f"Requires human review (matched: {pattern})",
                )

        # Check auto-fix patterns
        file_hint = None
        fix_hint = None
        for pattern, (fp, fh) in AUTO_FIX_PATTERNS.items():
            if pattern.lower() in msg_lower:
                file_hint = fp
                fix_hint = fh
                break

        if file_hint or fix_hint:
            # Infer deploy target from file path
            deploy_target = None
            if file_hint:
                if "consciousness" in file_hint or "mycosoft_mas" in file_hint:
                    deploy_target = "mas"
                elif "website" in file_hint or "app/" in file_hint:
                    deploy_target = "website"
                elif "mindex" in file_hint:
                    deploy_target = "mindex"
            if not deploy_target and "mycosoft" in source.lower():
                deploy_target = "mas"

            return TriageResult(
                error_id=error_id,
                feasibility=FixFeasibility.AUTO_FIXABLE,
                suggested_fix=fix_hint,
                file_path=file_hint,
                deploy_target=deploy_target,
                dispatch_payload={
                    "error_message": error_message,
                    "source": source,
                    "fix_hint": fix_hint,
                    "file_path": file_hint,
                    "deploy_target": deploy_target,
                },
            )

        return TriageResult(
            error_id=error_id,
            feasibility=FixFeasibility.UNKNOWN,
            suggested_fix="Manual triage required",
        )

    async def triage(
        self,
        error_message: str,
        source: str = "unknown",
        context: Optional[Dict[str, Any]] = None,
        traceback: Optional[str] = None,
    ) -> TriageResult:
        """
        Triage an error: classify, log, optionally dispatch.
        Returns TriageResult with feasibility and dispatch info.
        """
        result = self._classify_error(error_message, source)

        # Enrich with traceback file/line if available
        if traceback:
            match = re.search(r'File "([^"]+)", line (\d+)', traceback)
            if match and not result.file_path:
                result.file_path = match.group(1).replace("\\", "/")
                result.line_hint = match.group(2)

        # Log to ErrorLoggingService if available
        if self._error_logger and hasattr(self._error_logger, "log_error"):
            await self._error_logger.log_error(
                "triage",
                {
                    "error_id": result.error_id,
                    "message": error_message,
                    "source": source,
                    "feasibility": result.feasibility.value,
                    "suggested_fix": result.suggested_fix,
                    "file_path": result.file_path,
                    "deploy_target": result.deploy_target,
                    "context": context,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        # Store in history
        self._triage_history.append(
            {
                "error_id": result.error_id,
                "feasibility": result.feasibility.value,
                "message": error_message[:200],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        if len(self._triage_history) > self._max_history:
            self._triage_history = self._triage_history[-self._max_history :]

        # Dispatch auto-fixable errors to n8n webhook
        if (
            result.feasibility == FixFeasibility.AUTO_FIXABLE
            and self._n8n_webhook_url
        ):
            asyncio.create_task(
                self._dispatch_to_autonomous_fix(result, context, traceback)
            )

        return result

    async def _dispatch_to_autonomous_fix(
        self,
        result: TriageResult,
        context: Optional[Dict[str, Any]],
        traceback: Optional[str],
    ) -> None:
        """Dispatch fix request to n8n autonomous-fix-pipeline webhook."""
        try:
            import httpx

            payload = {
                "error_id": result.error_id,
                "feasibility": result.feasibility.value,
                "error_message": result.dispatch_payload.get("error_message", ""),
                "source": result.dispatch_payload.get("source", "unknown"),
                "suggested_fix": result.suggested_fix,
                "file_path": result.file_path,
                "line_hint": result.line_hint,
                "deploy_target": result.deploy_target,
                "context": context or {},
                "traceback": traceback or "",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    self._n8n_webhook_url,
                    json=payload,
                )
                if resp.status_code >= 400:
                    logger.warning(
                        f"Autonomous fix webhook returned {resp.status_code}: {resp.text}"
                    )
                else:
                    logger.info(
                        f"Dispatched auto-fix for {result.error_id} to n8n"
                    )
        except Exception as e:
            logger.warning(f"Failed to dispatch to autonomous fix webhook: {e}")

    def get_recent_triages(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return recent triage history."""
        return self._triage_history[-limit:]


# Singleton for use across the app
_triage_service: Optional[ErrorTriageService] = None


def get_error_triage_service(config: Optional[Dict[str, Any]] = None) -> ErrorTriageService:
    """Get or create the singleton ErrorTriageService."""
    global _triage_service
    if _triage_service is None:
        _triage_service = ErrorTriageService(config)
    return _triage_service
