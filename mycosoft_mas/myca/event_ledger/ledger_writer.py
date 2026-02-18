"""
MYCA Event Ledger Writer

Append-only logging for tool calls, denials, and risk events.
Integrates with the existing AuditLogger in mycosoft_mas/security/audit.py.

Date: February 17, 2026
"""

import hashlib
import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


def hash_args(args: dict) -> str:
    """
    Create SHA256 hash of arguments for privacy-preserving logging.
    
    Args:
        args: Dictionary of tool arguments
        
    Returns:
        SHA256 hash string prefixed with 'sha256:'
    """
    raw = json.dumps(args, sort_keys=True, default=str).encode("utf-8")
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


class EventLedger:
    """
    Append-only event ledger for MYCA tool calls.
    
    All tool executions, denials, and risk events are logged here
    for audit, analysis, and self-improvement purposes.
    """
    
    def __init__(self, ledger_dir: Optional[Path] = None):
        """
        Initialize the event ledger.
        
        Args:
            ledger_dir: Directory for ledger files. Defaults to myca/event_ledger/
        """
        if ledger_dir is None:
            ledger_dir = Path(__file__).parent
        self.ledger_dir = Path(ledger_dir)
        self.ledger_dir.mkdir(parents=True, exist_ok=True)
        self._session_id = str(uuid.uuid4())[:8]
    
    @property
    def current_ledger_file(self) -> Path:
        """Get the current day's ledger file."""
        return self.ledger_dir / "events.jsonl"
    
    def log_tool_call(
        self,
        agent: str,
        tool_name: str,
        args_hash: str,
        result_status: str,
        elapsed_ms: int = 0,
        error_class: Optional[str] = None,
        risk_flags: Optional[list[str]] = None,
        artifacts: Optional[list[str]] = None,
        session_id: Optional[str] = None
    ) -> dict:
        """
        Log a tool call event.
        
        Args:
            agent: Name of the agent that initiated the call
            tool_name: Name of the tool being called
            args_hash: SHA256 hash of arguments (use hash_args())
            result_status: One of 'success', 'error', 'denied', 'timeout'
            elapsed_ms: Execution time in milliseconds
            error_class: Error type if failed
            risk_flags: List of risk indicators
            artifacts: List of files/resources affected
            session_id: Override session ID (optional)
            
        Returns:
            The logged event dict
        """
        event = {
            "ts": int(time.time()),
            "ts_iso": datetime.utcnow().isoformat() + "Z",
            "session_id": session_id or self._session_id,
            "agent": agent,
            "tool": tool_name,
            "args_hash": args_hash,
            "result_status": result_status,
            "elapsed_ms": elapsed_ms,
            "error_class": error_class,
            "risk_flags": risk_flags or [],
            "artifacts": artifacts or []
        }
        
        self._append_event(event)
        return event
    
    def log_denial(
        self,
        agent: str,
        tool_name: str,
        args_hash: str,
        reason: str,
        risk_flags: Optional[list[str]] = None
    ) -> dict:
        """
        Log a permission denial event.
        
        Args:
            agent: Name of the agent
            tool_name: Tool that was denied
            args_hash: SHA256 hash of arguments
            reason: Why the call was denied
            risk_flags: Additional risk indicators
            
        Returns:
            The logged event dict
        """
        flags = risk_flags or []
        flags.append(f"denial:{reason}")
        
        return self.log_tool_call(
            agent=agent,
            tool_name=tool_name,
            args_hash=args_hash,
            result_status="denied",
            risk_flags=flags
        )
    
    def log_risk_event(
        self,
        agent: str,
        event_type: str,
        description: str,
        risk_flags: list[str],
        context: Optional[dict] = None
    ) -> dict:
        """
        Log a risk event that isn't a direct tool call.
        
        Args:
            agent: Agent involved
            event_type: Type of risk event (e.g., 'injection_attempt')
            description: Human-readable description
            risk_flags: Risk indicators
            context: Additional context (will be hashed)
            
        Returns:
            The logged event dict
        """
        event = {
            "ts": int(time.time()),
            "ts_iso": datetime.utcnow().isoformat() + "Z",
            "session_id": self._session_id,
            "agent": agent,
            "event_type": event_type,
            "description": description,
            "context_hash": hash_args(context or {}),
            "risk_flags": risk_flags
        }
        
        self._append_event(event)
        return event
    
    def _append_event(self, event: dict) -> None:
        """Append an event to the ledger file."""
        with self.current_ledger_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    
    def read_events(
        self,
        since_ts: Optional[int] = None,
        agent: Optional[str] = None,
        tool: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 1000
    ) -> list[dict]:
        """
        Read events from the ledger with optional filtering.
        
        Args:
            since_ts: Only events after this timestamp
            agent: Filter by agent name
            tool: Filter by tool name
            status: Filter by result_status
            limit: Maximum events to return
            
        Returns:
            List of matching events
        """
        events = []
        
        if not self.current_ledger_file.exists():
            return events
        
        with self.current_ledger_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                
                # Apply filters
                if since_ts and event.get("ts", 0) < since_ts:
                    continue
                if agent and event.get("agent") != agent:
                    continue
                if tool and event.get("tool") != tool:
                    continue
                if status and event.get("result_status") != status:
                    continue
                
                events.append(event)
                
                if len(events) >= limit:
                    break
        
        return events
    
    def get_failure_summary(self, hours: int = 24) -> dict:
        """
        Get a summary of failures in the last N hours.
        
        Args:
            hours: How many hours to look back
            
        Returns:
            Summary dict with failure counts by type
        """
        since_ts = int(time.time()) - (hours * 3600)
        events = self.read_events(since_ts=since_ts)
        
        summary = {
            "total_events": len(events),
            "denials": 0,
            "errors": 0,
            "timeouts": 0,
            "risk_flags": {},
            "by_agent": {},
            "by_tool": {}
        }
        
        for event in events:
            status = event.get("result_status", "")
            agent = event.get("agent", "unknown")
            tool = event.get("tool", "unknown")
            
            if status == "denied":
                summary["denials"] += 1
            elif status == "error":
                summary["errors"] += 1
            elif status == "timeout":
                summary["timeouts"] += 1
            
            for flag in event.get("risk_flags", []):
                summary["risk_flags"][flag] = summary["risk_flags"].get(flag, 0) + 1
            
            if status in ("denied", "error", "timeout"):
                summary["by_agent"][agent] = summary["by_agent"].get(agent, 0) + 1
                summary["by_tool"][tool] = summary["by_tool"].get(tool, 0) + 1
        
        return summary


# Module-level singleton for convenience
_default_ledger: Optional[EventLedger] = None


def get_ledger() -> EventLedger:
    """Get the default event ledger instance."""
    global _default_ledger
    if _default_ledger is None:
        _default_ledger = EventLedger()
    return _default_ledger
