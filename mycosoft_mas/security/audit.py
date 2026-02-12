"""
Audit Logging with Ed25519 Signing
Created: February 3, 2026
Updated: February 12, 2026 - Added Ed25519 cryptographic signing
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
