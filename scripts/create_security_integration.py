"""Helper script to create security_integration.py"""
import os

content = '''"""
Security Integration for MYCA Voice System
Created: February 4, 2026

SOC integration, incident management, and MINDEX cryptography.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import hashlib
import json

logger = logging.getLogger(__name__)


class SeverityLevel(Enum):
    """Incident severity levels."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    INFO = 5


class IncidentStatus(Enum):
    """Incident status."""
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    CONTAINED = "contained"
    RESOLVED = "resolved"
    CLOSED = "closed"


class ThreatCategory(Enum):
    """Threat categories."""
    MALWARE = "malware"
    INTRUSION = "intrusion"
    DATA_BREACH = "data_breach"
    DDOS = "ddos"
    PHISHING = "phishing"
    INSIDER = "insider"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    ANOMALY = "anomaly"
    OTHER = "other"


@dataclass
class SecurityIncident:
    """A security incident."""
    incident_id: str
    title: str
    description: str
    severity: SeverityLevel
    category: ThreatCategory
    status: IncidentStatus = IncidentStatus.NEW
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    assigned_to: Optional[str] = None
    source_ip: Optional[str] = None
    affected_systems: List[str] = field(default_factory=list)
    indicators: List[str] = field(default_factory=list)
    actions_taken: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditLogEntry:
    """An audit log entry."""
    log_id: str
    timestamp: datetime
    action: str
    actor: str
    resource: str
    result: str
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    session_id: Optional[str] = None


class SOCIntegration:
    """
    Security Operations Center integration.
    
    Features:
    - Incident creation and management
    - Threat detection alerts
    - Audit logging
    - Compliance reporting
    """
    
    def __init__(self, voice_announcer: Optional[Any] = None):
        self.voice_announcer = voice_announcer
        self.incidents: Dict[str, SecurityIncident] = {}
        self.audit_log: List[AuditLogEntry] = []
        
        logger.info("SOCIntegration initialized")
    
    async def create_incident(
        self,
        title: str,
        description: str,
        severity: SeverityLevel,
        category: ThreatCategory,
        source_ip: Optional[str] = None,
        affected_systems: Optional[List[str]] = None,
    ) -> SecurityIncident:
        """Create a new security incident."""
        incident_id = hashlib.md5(f"{title}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        incident = SecurityIncident(
            incident_id=incident_id,
            title=title,
            description=description,
            severity=severity,
            category=category,
            source_ip=source_ip,
            affected_systems=affected_systems or [],
        )
        
        self.incidents[incident_id] = incident
        
        # Log the creation
        await self.log_action(
            action="incident_created",
            actor="soc-integration",
            resource=incident_id,
            result="success",
            details={"severity": severity.name, "category": category.value},
        )
        
        # Voice announcement for critical/high severity
        if severity in (SeverityLevel.CRITICAL, SeverityLevel.HIGH) and self.voice_announcer:
            self.voice_announcer(f"Security Alert: {severity.name} severity incident - {title}")
        
        logger.info(f"Created incident: {incident_id} - {title}")
        return incident
    
    async def update_incident(
        self,
        incident_id: str,
        status: Optional[IncidentStatus] = None,
        assigned_to: Optional[str] = None,
        action_taken: Optional[str] = None,
    ) -> Optional[SecurityIncident]:
        """Update an incident."""
        if incident_id not in self.incidents:
            return None
        
        incident = self.incidents[incident_id]
        incident.updated_at = datetime.now()
        
        if status:
            incident.status = status
            if status == IncidentStatus.ACKNOWLEDGED:
                incident.acknowledged_at = datetime.now()
            elif status == IncidentStatus.RESOLVED:
                incident.resolved_at = datetime.now()
        
        if assigned_to:
            incident.assigned_to = assigned_to
        
        if action_taken:
            incident.actions_taken.append(action_taken)
        
        await self.log_action(
            action="incident_updated",
            actor="soc-integration",
            resource=incident_id,
            result="success",
            details={"status": incident.status.value if incident.status else None},
        )
        
        return incident
    
    async def get_active_incidents(self, severity_filter: Optional[SeverityLevel] = None) -> List[SecurityIncident]:
        """Get all active (non-closed) incidents."""
        active = [
            i for i in self.incidents.values()
            if i.status not in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED)
        ]
        
        if severity_filter:
            active = [i for i in active if i.severity == severity_filter]
        
        return sorted(active, key=lambda x: x.severity.value)
    
    async def log_action(
        self,
        action: str,
        actor: str,
        resource: str,
        result: str,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLogEntry:
        """Log an auditable action."""
        log_id = hashlib.md5(f"{action}{actor}{datetime.now().isoformat()}".encode()).hexdigest()[:16]
        
        entry = AuditLogEntry(
            log_id=log_id,
            timestamp=datetime.now(),
            action=action,
            actor=actor,
            resource=resource,
            result=result,
            details=details or {},
            ip_address=ip_address,
        )
        
        self.audit_log.append(entry)
        
        # Keep only last 10000 entries
        if len(self.audit_log) > 10000:
            self.audit_log = self.audit_log[-10000:]
        
        return entry
    
    async def get_audit_log(
        self,
        actor: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditLogEntry]:
        """Get audit log entries."""
        entries = self.audit_log
        
        if actor:
            entries = [e for e in entries if e.actor == actor]
        if action:
            entries = [e for e in entries if e.action == action]
        
        return sorted(entries, key=lambda x: x.timestamp, reverse=True)[:limit]
    
    async def threat_assessment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess threat level from provided data."""
        # Simple threat scoring
        score = 0
        indicators = []
        
        # Check for known bad patterns
        if data.get("source_ip", "").startswith("10."):
            score += 1
            indicators.append("internal_ip")
        
        if "malware" in str(data).lower():
            score += 5
            indicators.append("malware_keyword")
        
        if "unauthorized" in str(data).lower():
            score += 3
            indicators.append("unauthorized_keyword")
        
        # Determine threat level
        if score >= 5:
            level = "high"
        elif score >= 3:
            level = "medium"
        elif score >= 1:
            level = "low"
        else:
            level = "none"
        
        return {
            "threat_level": level,
            "score": score,
            "indicators": indicators,
            "recommendation": "investigate" if score >= 3 else "monitor",
        }


class MINDEXCrypto:
    """
    MINDEX cryptography engine integration.
    
    Features:
    - Secure key generation
    - Data encryption/decryption
    - Hash verification
    - Secure token generation
    """
    
    def __init__(self):
        self.key_store: Dict[str, bytes] = {}
        logger.info("MINDEXCrypto initialized")
    
    def generate_key(self, key_id: str, length: int = 32) -> str:
        """Generate a secure key."""
        import secrets
        key = secrets.token_bytes(length)
        self.key_store[key_id] = key
        return key.hex()
    
    def hash_data(self, data: str, algorithm: str = "sha256") -> str:
        """Hash data using specified algorithm."""
        if algorithm == "sha256":
            return hashlib.sha256(data.encode()).hexdigest()
        elif algorithm == "sha512":
            return hashlib.sha512(data.encode()).hexdigest()
        elif algorithm == "blake2b":
            return hashlib.blake2b(data.encode()).hexdigest()
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
    
    def verify_hash(self, data: str, expected_hash: str, algorithm: str = "sha256") -> bool:
        """Verify a hash."""
        computed = self.hash_data(data, algorithm)
        return computed == expected_hash
    
    def generate_token(self, length: int = 32) -> str:
        """Generate a secure random token."""
        import secrets
        return secrets.token_urlsafe(length)
    
    def encrypt_for_voice(self, data: str, key_id: str) -> Dict[str, str]:
        """Encrypt data for voice transmission (base64 for simplicity)."""
        import base64
        
        # In production, use proper encryption (AES-GCM)
        encoded = base64.b64encode(data.encode()).decode()
        
        return {
            "ciphertext": encoded,
            "key_id": key_id,
            "algorithm": "base64",  # Placeholder - use AES-GCM in production
        }
    
    def decrypt_from_voice(self, ciphertext: str, key_id: str) -> str:
        """Decrypt data from voice transmission."""
        import base64
        return base64.b64decode(ciphertext).decode()


class VoiceSecurityGateway:
    """
    Security gateway for voice commands.
    
    Features:
    - Command validation
    - Rate limiting
    - Threat detection
    - Audit logging
    """
    
    def __init__(self):
        self.soc = SOCIntegration()
        self.crypto = MINDEXCrypto()
        self.rate_limits: Dict[str, List[datetime]] = {}
        
        logger.info("VoiceSecurityGateway initialized")
    
    async def validate_command(
        self,
        command: str,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Validate a voice command."""
        # Rate limiting
        if not self._check_rate_limit(user_id):
            await self.soc.log_action(
                action="rate_limit_exceeded",
                actor=user_id,
                resource="voice_command",
                result="blocked",
            )
            return {"valid": False, "reason": "Rate limit exceeded"}
        
        # Threat assessment
        threat = await self.soc.threat_assessment({"command": command, "user_id": user_id})
        
        if threat["threat_level"] == "high":
            await self.soc.create_incident(
                title=f"Suspicious voice command from {user_id}",
                description=f"Command: {command}",
                severity=SeverityLevel.MEDIUM,
                category=ThreatCategory.ANOMALY,
            )
            return {"valid": False, "reason": "Command flagged for review"}
        
        # Log the validated command
        await self.soc.log_action(
            action="voice_command",
            actor=user_id,
            resource="voice_interface",
            result="validated",
            details={"command_hash": self.crypto.hash_data(command)[:16]},
        )
        
        return {"valid": True, "threat_level": threat["threat_level"]}
    
    def _check_rate_limit(self, user_id: str, max_requests: int = 60, window_seconds: int = 60) -> bool:
        """Check rate limit for user."""
        now = datetime.now()
        
        if user_id not in self.rate_limits:
            self.rate_limits[user_id] = []
        
        # Clean old entries
        cutoff = now.timestamp() - window_seconds
        self.rate_limits[user_id] = [
            t for t in self.rate_limits[user_id]
            if t.timestamp() > cutoff
        ]
        
        if len(self.rate_limits[user_id]) >= max_requests:
            return False
        
        self.rate_limits[user_id].append(now)
        return True


# Singletons
_soc_instance: Optional[SOCIntegration] = None
_crypto_instance: Optional[MINDEXCrypto] = None
_gateway_instance: Optional[VoiceSecurityGateway] = None


def get_soc_integration() -> SOCIntegration:
    global _soc_instance
    if _soc_instance is None:
        _soc_instance = SOCIntegration()
    return _soc_instance


def get_mindex_crypto() -> MINDEXCrypto:
    global _crypto_instance
    if _crypto_instance is None:
        _crypto_instance = MINDEXCrypto()
    return _crypto_instance


def get_voice_security_gateway() -> VoiceSecurityGateway:
    global _gateway_instance
    if _gateway_instance is None:
        _gateway_instance = VoiceSecurityGateway()
    return _gateway_instance


__all__ = [
    "SOCIntegration",
    "MINDEXCrypto",
    "VoiceSecurityGateway",
    "SecurityIncident",
    "AuditLogEntry",
    "SeverityLevel",
    "IncidentStatus",
    "ThreatCategory",
    "get_soc_integration",
    "get_mindex_crypto",
    "get_voice_security_gateway",
]
'''

os.makedirs('mycosoft_mas/security', exist_ok=True)
with open('mycosoft_mas/security/security_integration.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Created security_integration.py')
