"""
Audit Logging with Ed25519 Signing
Created: February 3, 2026
Updated: February 12, 2026 - Added Ed25519 cryptographic signing
Updated: February 17, 2026 - Added MYCA EventLedger integration
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel
import logging

# Import Ed25519 signing
try:
    from mycosoft_mas.security.crypto_signing import get_audit_signer, sign_audit_log, verify_audit_log
    SIGNING_AVAILABLE = True
except ImportError:
    SIGNING_AVAILABLE = False
    get_audit_signer = None
    sign_audit_log = lambda x: None
    verify_audit_log = lambda x, y: False

# Import MYCA EventLedger
try:
    from mycosoft_mas.myca.event_ledger import EventLedger, hash_args
    EVENT_LEDGER_AVAILABLE = True
except ImportError:
    EVENT_LEDGER_AVAILABLE = False
    EventLedger = None
    hash_args = lambda x: "unavailable"

logger = logging.getLogger(__name__)


class AuditEntry(BaseModel):
    """Audit entry with Ed25519 signature."""
    entry_id: UUID
    timestamp: datetime
    user_id: UUID
    action: str
    resource: str
    details: Dict[str, Any] = {}
    ip_address: str = ""
    success: bool = True
    # Ed25519 cryptographic signing (DoD compliance)
    signature: Optional[str] = None
    key_fingerprint: Optional[str] = None


class AuditLogger:
    """Audit logging for security compliance with Ed25519 signing."""
    
    def __init__(self):
        self._entries: List[AuditEntry] = []
        self._signer = get_audit_signer() if SIGNING_AVAILABLE else None
    
    def log(
        self,
        user_id: UUID,
        action: str,
        resource: str,
        details: Dict[str, Any] = None,
        success: bool = True,
        ip_address: str = "",
    ) -> UUID:
        """
        Log an audit entry with Ed25519 signature.
        
        Args:
            user_id: User performing the action
            action: Action being performed
            resource: Resource being accessed
            details: Additional details
            success: Whether action succeeded
            ip_address: Client IP address
            
        Returns:
            Entry ID
        """
        entry = AuditEntry(
            entry_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            action=action,
            resource=resource,
            details=details or {},
            ip_address=ip_address,
            success=success,
        )
        
        # Sign the entry with Ed25519
        if self._signer and self._signer.is_signing_enabled:
            try:
                entry_dict = entry.model_dump()
                # Convert UUID and datetime to strings for signing
                entry_dict["entry_id"] = str(entry_dict["entry_id"])
                entry_dict["user_id"] = str(entry_dict["user_id"])
                entry_dict["timestamp"] = entry_dict["timestamp"].isoformat()
                
                entry.signature = self._signer.sign_log_entry(entry_dict)
                entry.key_fingerprint = self._signer.get_public_key_fingerprint()
                logger.debug(f"Signed audit entry {entry.entry_id}")
            except Exception as e:
                logger.warning(f"Failed to sign audit entry: {e}")
        
        self._entries.append(entry)
        return entry.entry_id
    
    def verify(self, entry: AuditEntry) -> bool:
        """
        Verify the Ed25519 signature of an audit entry.
        
        Args:
            entry: Audit entry to verify
            
        Returns:
            True if signature is valid, False otherwise
        """
        if not entry.signature:
            logger.warning(f"Audit entry {entry.entry_id} has no signature")
            return False
        
        if not self._signer or not self._signer.is_verification_enabled:
            logger.warning("Signature verification not available")
            return False
        
        try:
            entry_dict = entry.model_dump()
            entry_dict["entry_id"] = str(entry_dict["entry_id"])
            entry_dict["user_id"] = str(entry_dict["user_id"])
            entry_dict["timestamp"] = entry_dict["timestamp"].isoformat()
            
            return self._signer.verify_log_entry(entry_dict, entry.signature)
        except Exception as e:
            logger.error(f"Failed to verify audit entry: {e}")
            return False
    
    def query(
        self,
        user_id: UUID = None,
        action: str = None,
        start_time: datetime = None,
    ) -> List[AuditEntry]:
        """Query audit entries with optional filters."""
        results = self._entries
        if user_id:
            results = [e for e in results if e.user_id == user_id]
        if action:
            results = [e for e in results if e.action == action]
        if start_time:
            results = [e for e in results if e.timestamp >= start_time]
        return results
    
    def verify_all(self) -> Dict[str, Any]:
        """
        Verify integrity of all audit entries.
        
        Returns:
            Summary of verification results
        """
        results = {
            "total": len(self._entries),
            "signed": 0,
            "unsigned": 0,
            "valid": 0,
            "invalid": 0,
            "errors": [],
        }
        
        for entry in self._entries:
            if entry.signature:
                results["signed"] += 1
                if self.verify(entry):
                    results["valid"] += 1
                else:
                    results["invalid"] += 1
                    results["errors"].append({
                        "entry_id": str(entry.entry_id),
                        "error": "Invalid signature - possible tampering",
                    })
            else:
                results["unsigned"] += 1
        
        results["integrity_percentage"] = (
            (results["valid"] / results["signed"] * 100)
            if results["signed"] > 0 else 100.0
        )
        
        return results


# ---------------------------------------------------------------------------
# MYCA EventLedger Bridge
# ---------------------------------------------------------------------------

class AuditEventBridge:
    """
    Bridge between AuditLogger and MYCA EventLedger.
    
    Provides unified logging to both the existing Ed25519-signed audit log
    and the MYCA EventLedger for tool call auditing.
    
    Created: February 17, 2026
    """
    
    def __init__(self, audit_logger: Optional[AuditLogger] = None):
        """
        Initialize the bridge.
        
        Args:
            audit_logger: Optional existing AuditLogger instance.
                         If not provided, creates a new one.
        """
        self._audit_logger = audit_logger or AuditLogger()
        self._event_ledger = EventLedger() if EVENT_LEDGER_AVAILABLE else None
        
        if not self._event_ledger:
            logger.debug("MYCA EventLedger not available - bridge will use AuditLogger only")
    
    @property
    def audit_logger(self) -> AuditLogger:
        """Get the underlying AuditLogger."""
        return self._audit_logger
    
    @property
    def event_ledger(self) -> Optional["EventLedger"]:
        """Get the MYCA EventLedger if available."""
        return self._event_ledger
    
    def log_tool_call(
        self,
        agent_id: str,
        tool: str,
        args: Dict[str, Any],
        user_id: Optional[UUID] = None,
        ip_address: str = "",
        result_summary: Optional[str] = None,
        risk_flags: Optional[List[str]] = None,
        success: bool = True,
    ) -> UUID:
        """
        Log a tool call to both AuditLogger and EventLedger.
        
        Args:
            agent_id: ID of the agent making the call
            tool: Name of the tool being called
            args: Tool arguments (will be hashed for privacy in EventLedger)
            user_id: User ID for AuditLogger
            ip_address: Client IP address
            result_summary: Brief summary of result (first 200 chars)
            risk_flags: List of risk flags (e.g., ["SECRETS_READ", "WRITE_OP"])
            success: Whether the call succeeded
            
        Returns:
            AuditLogger entry ID
        """
        # Log to AuditLogger with Ed25519 signing
        audit_user_id = user_id or uuid4()  # Use agent_id as fallback
        entry_id = self._audit_logger.log(
            user_id=audit_user_id,
            action=f"tool_call:{tool}",
            resource=agent_id,
            details={
                "tool": tool,
                "args_hash": hash_args(args) if EVENT_LEDGER_AVAILABLE else "unavailable",
                "result_summary": result_summary,
                "risk_flags": risk_flags or [],
            },
            success=success,
            ip_address=ip_address,
        )
        
        # Log to MYCA EventLedger
        if self._event_ledger:
            try:
                self._event_ledger.log_tool_call(
                    agent_id=agent_id,
                    tool=tool,
                    args=args,
                    result_summary=result_summary,
                    risk_flags=risk_flags,
                )
            except Exception as e:
                logger.warning(f"Failed to log to EventLedger: {e}")
        
        return entry_id
    
    def log_denial(
        self,
        agent_id: str,
        tool: str,
        args: Dict[str, Any],
        reason: str,
        user_id: Optional[UUID] = None,
        ip_address: str = "",
    ) -> UUID:
        """
        Log a permission denial to both AuditLogger and EventLedger.
        
        Args:
            agent_id: ID of the agent making the call
            tool: Name of the tool that was denied
            args: Tool arguments
            reason: Reason for denial
            user_id: User ID for AuditLogger
            ip_address: Client IP address
            
        Returns:
            AuditLogger entry ID
        """
        # Log to AuditLogger with Ed25519 signing
        audit_user_id = user_id or uuid4()
        entry_id = self._audit_logger.log(
            user_id=audit_user_id,
            action=f"tool_denied:{tool}",
            resource=agent_id,
            details={
                "tool": tool,
                "reason": reason,
                "args_hash": hash_args(args) if EVENT_LEDGER_AVAILABLE else "unavailable",
            },
            success=False,
            ip_address=ip_address,
        )
        
        # Log to MYCA EventLedger
        if self._event_ledger:
            try:
                self._event_ledger.log_denial(
                    agent_id=agent_id,
                    tool=tool,
                    args=args,
                    reason=reason,
                )
            except Exception as e:
                logger.warning(f"Failed to log denial to EventLedger: {e}")
        
        return entry_id
    
    def log_risk_event(
        self,
        agent_id: str,
        risk_type: str,
        details: Dict[str, Any],
        severity: str = "medium",
        user_id: Optional[UUID] = None,
        ip_address: str = "",
    ) -> UUID:
        """
        Log a security risk event to both AuditLogger and EventLedger.
        
        Args:
            agent_id: ID of the agent involved
            risk_type: Type of risk (e.g., "prompt_injection", "data_exfil")
            details: Event details
            severity: Risk severity ("low", "medium", "high", "critical")
            user_id: User ID for AuditLogger
            ip_address: Client IP address
            
        Returns:
            AuditLogger entry ID
        """
        # Log to AuditLogger with Ed25519 signing
        audit_user_id = user_id or uuid4()
        entry_id = self._audit_logger.log(
            user_id=audit_user_id,
            action=f"risk_event:{risk_type}",
            resource=agent_id,
            details={
                "risk_type": risk_type,
                "severity": severity,
                **details,
            },
            success=False,
            ip_address=ip_address,
        )
        
        # Log to MYCA EventLedger
        if self._event_ledger:
            try:
                self._event_ledger.log_risk_event(
                    agent_id=agent_id,
                    risk_type=risk_type,
                    details=details,
                    severity=severity,
                )
            except Exception as e:
                logger.warning(f"Failed to log risk event to EventLedger: {e}")
        
        return entry_id
    
    def get_failure_summary(
        self,
        since_ts: Optional[float] = None,
        agent_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get a summary of failures from EventLedger.
        
        Args:
            since_ts: Optional timestamp to filter events
            agent_filter: Optional agent ID to filter events
            
        Returns:
            Summary dictionary with failure counts and details
        """
        if not self._event_ledger:
            return {"error": "EventLedger not available", "failures": []}
        
        try:
            return self._event_ledger.summarize_failures(
                since_ts=since_ts,
                agent_filter=agent_filter,
            )
        except Exception as e:
            logger.warning(f"Failed to get failure summary: {e}")
            return {"error": str(e), "failures": []}
    
    def verify_audit_integrity(self) -> Dict[str, Any]:
        """
        Verify integrity of all audit entries.
        
        Returns:
            Combined verification results from AuditLogger and EventLedger
        """
        results = {
            "audit_logger": self._audit_logger.verify_all(),
            "event_ledger": None,
        }
        
        if self._event_ledger:
            try:
                # Get event ledger stats
                events = self._event_ledger.read_events()
                results["event_ledger"] = {
                    "total_events": len(events),
                    "by_event_type": {},
                    "by_agent": {},
                }
                
                for event in events:
                    # Count by event type
                    event_type = event.get("event_type", "unknown")
                    results["event_ledger"]["by_event_type"][event_type] = \
                        results["event_ledger"]["by_event_type"].get(event_type, 0) + 1
                    
                    # Count by agent
                    agent_id = event.get("agent_id", "unknown")
                    results["event_ledger"]["by_agent"][agent_id] = \
                        results["event_ledger"]["by_agent"].get(agent_id, 0) + 1
                        
            except Exception as e:
                results["event_ledger"] = {"error": str(e)}
        
        return results


# Singleton instance
_audit_event_bridge: Optional[AuditEventBridge] = None


def get_audit_event_bridge() -> AuditEventBridge:
    """Get or create the audit event bridge singleton."""
    global _audit_event_bridge
    if _audit_event_bridge is None:
        _audit_event_bridge = AuditEventBridge()
    return _audit_event_bridge
