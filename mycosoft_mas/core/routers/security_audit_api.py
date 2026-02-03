"""
Security Audit API - February 3, 2026

SOC Security System Integration - Audit logging and monitoring endpoints.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger("SecurityAuditAPI")

router = APIRouter(prefix="/api/security", tags=["security"])


# ============================================================================
# Models
# ============================================================================

class AuditEntry(BaseModel):
    """Audit log entry."""
    entry_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: str
    action: str
    resource: str
    details: Dict[str, Any] = Field(default_factory=dict)
    ip_address: str = ""
    success: bool = True
    severity: str = "info"  # info, warning, error, critical


class AuditLogRequest(BaseModel):
    """Request to log an audit entry."""
    user_id: str = Field(..., description="User or system ID")
    action: str = Field(..., description="Action performed")
    resource: str = Field(..., description="Resource accessed")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")
    success: bool = Field(True, description="Whether action succeeded")
    ip_address: str = Field("", description="Client IP address")
    severity: str = Field("info", description="Severity level")


class AuditQueryResponse(BaseModel):
    """Response from audit log query."""
    entries: List[AuditEntry]
    count: int
    has_more: bool


# ============================================================================
# In-memory store (should be replaced with persistent storage in production)
# ============================================================================

_audit_log: List[AuditEntry] = []


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/audit/log", response_model=AuditEntry)
async def log_audit_entry(request: AuditLogRequest):
    """Log a security audit entry."""
    entry = AuditEntry(
        user_id=request.user_id,
        action=request.action,
        resource=request.resource,
        details=request.details or {},
        ip_address=request.ip_address,
        success=request.success,
        severity=request.severity,
    )
    _audit_log.append(entry)
    
    # Also log to standard logging for SIEM integration
    log_msg = f"AUDIT: user={request.user_id} action={request.action} resource={request.resource} success={request.success}"
    if request.severity == "critical":
        logger.critical(log_msg)
    elif request.severity == "error":
        logger.error(log_msg)
    elif request.severity == "warning":
        logger.warning(log_msg)
    else:
        logger.info(log_msg)
    
    return entry


@router.get("/audit/query", response_model=AuditQueryResponse)
async def query_audit_log(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    action: Optional[str] = Query(None, description="Filter by action"),
    resource: Optional[str] = Query(None, description="Filter by resource"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    limit: int = Query(50, ge=1, le=500, description="Max entries to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """Query the audit log with optional filters."""
    results = _audit_log.copy()
    
    if user_id:
        results = [e for e in results if e.user_id == user_id]
    if action:
        results = [e for e in results if e.action == action]
    if resource:
        results = [e for e in results if resource in e.resource]
    if severity:
        results = [e for e in results if e.severity == severity]
    
    # Sort by timestamp descending
    results.sort(key=lambda x: x.timestamp, reverse=True)
    
    # Paginate
    total = len(results)
    results = results[offset:offset + limit]
    
    return AuditQueryResponse(
        entries=results,
        count=len(results),
        has_more=total > offset + limit
    )


@router.get("/audit/stats")
async def get_audit_stats():
    """Get audit log statistics for SOC dashboard."""
    now = datetime.now(timezone.utc)
    
    # Count by severity
    severity_counts = {}
    for entry in _audit_log:
        severity_counts[entry.severity] = severity_counts.get(entry.severity, 0) + 1
    
    # Count by action
    action_counts = {}
    for entry in _audit_log:
        action_counts[entry.action] = action_counts.get(entry.action, 0) + 1
    
    # Success/failure rates
    total = len(_audit_log)
    successes = len([e for e in _audit_log if e.success])
    failures = total - successes
    
    return {
        "total_entries": total,
        "by_severity": severity_counts,
        "by_action": action_counts,
        "success_count": successes,
        "failure_count": failures,
        "success_rate": (successes / total * 100) if total > 0 else 0,
        "last_entry_at": _audit_log[-1].timestamp.isoformat() if _audit_log else None,
    }


@router.get("/health")
async def security_health():
    """Security service health check."""
    return {
        "status": "healthy",
        "service": "security-audit",
        "audit_entries": len(_audit_log),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
