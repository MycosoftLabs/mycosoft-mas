"""
Security Audit API - February 4, 2026

SOC Security System Integration - Audit logging and monitoring endpoints.
Now with PostgreSQL persistence and cryptographic integrity.
"""

import os
import logging
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger("SecurityAuditAPI")

router = APIRouter(prefix="/api/security", tags=["security"])

# Integrity service import
try:
    from mycosoft_mas.security.integrity_service import hash_and_record, get_integrity_service
    INTEGRITY_AVAILABLE = True
except ImportError:
    INTEGRITY_AVAILABLE = False
    hash_and_record = None


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
    data_hash: Optional[str] = None  # SHA256 hash for integrity verification


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
    source: str = "memory"  # memory or postgres


# ============================================================================
# Persistent Audit Log with PostgreSQL
# ============================================================================

class PersistentAuditLog:
    """
    PostgreSQL-backed audit log with in-memory fallback.
    """
    
    def __init__(self):
        self._pool = None
        self._db_available = None
        self._memory_log: List[AuditEntry] = []
        self._database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://mycosoft:mycosoft@postgres:5432/mycosoft"
        )
    
    async def _get_pool(self):
        """Get or create database connection pool."""
        if self._db_available is False:
            return None
        if self._pool is None:
            try:
                import asyncpg
                self._pool = await asyncpg.create_pool(
                    self._database_url,
                    min_size=1,
                    max_size=5
                )
                # Ensure table exists
                await self._ensure_table()
                self._db_available = True
            except Exception as e:
                logger.warning(f"PostgreSQL unavailable, using in-memory fallback: {e}")
                self._db_available = False
                return None
        return self._pool
    
    async def _ensure_table(self):
        """Ensure audit_log table exists in memory schema."""
        pool = self._pool
        if not pool:
            return
        
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE SCHEMA IF NOT EXISTS memory;
                
                CREATE TABLE IF NOT EXISTS memory.audit_log (
                    entry_id UUID PRIMARY KEY,
                    timestamp TIMESTAMPTZ DEFAULT NOW(),
                    user_id VARCHAR(255) NOT NULL,
                    action VARCHAR(255) NOT NULL,
                    resource VARCHAR(512) NOT NULL,
                    details JSONB DEFAULT '{}',
                    ip_address VARCHAR(45) DEFAULT '',
                    success BOOLEAN DEFAULT TRUE,
                    severity VARCHAR(50) DEFAULT 'info',
                    data_hash VARCHAR(64)
                );
                
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON memory.audit_log(timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_audit_user ON memory.audit_log(user_id);
                CREATE INDEX IF NOT EXISTS idx_audit_action ON memory.audit_log(action);
                CREATE INDEX IF NOT EXISTS idx_audit_severity ON memory.audit_log(severity);
            """)
    
    async def log(self, entry: AuditEntry) -> AuditEntry:
        """Log an audit entry to PostgreSQL with fallback to memory."""
        pool = await self._get_pool()
        
        # Record in cryptographic ledger first
        if INTEGRITY_AVAILABLE and hash_and_record:
            try:
                integrity_result = await hash_and_record(
                    entry_type="security_audit",
                    data=entry.dict(),
                    metadata={"action": entry.action, "severity": entry.severity},
                    with_signature=True,
                )
                entry.data_hash = integrity_result.get("data_hash")
            except Exception as e:
                logger.warning(f"Integrity recording failed: {e}")
        
        if pool:
            try:
                async with pool.acquire() as conn:
                    import json
                    await conn.execute("""
                        INSERT INTO memory.audit_log 
                        (entry_id, timestamp, user_id, action, resource, details, 
                         ip_address, success, severity, data_hash)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    """,
                        UUID(entry.entry_id),
                        entry.timestamp,
                        entry.user_id,
                        entry.action,
                        entry.resource,
                        json.dumps(entry.details),
                        entry.ip_address,
                        entry.success,
                        entry.severity,
                        entry.data_hash
                    )
                logger.debug(f"Audit entry persisted to PostgreSQL: {entry.entry_id}")
            except Exception as e:
                logger.error(f"Failed to persist audit entry: {e}")
                self._memory_log.append(entry)
        else:
            self._memory_log.append(entry)
        
        return entry
    
    async def query(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> AuditQueryResponse:
        """Query audit log from PostgreSQL with fallback to memory."""
        pool = await self._get_pool()
        
        if pool:
            try:
                async with pool.acquire() as conn:
                    # Build query with filters
                    conditions = []
                    params = []
                    param_idx = 1
                    
                    if user_id:
                        conditions.append(f"user_id = ${param_idx}")
                        params.append(user_id)
                        param_idx += 1
                    if action:
                        conditions.append(f"action = ${param_idx}")
                        params.append(action)
                        param_idx += 1
                    if resource:
                        conditions.append(f"resource LIKE ${param_idx}")
                        params.append(f"%{resource}%")
                        param_idx += 1
                    if severity:
                        conditions.append(f"severity = ${param_idx}")
                        params.append(severity)
                        param_idx += 1
                    
                    where_clause = ""
                    if conditions:
                        where_clause = "WHERE " + " AND ".join(conditions)
                    
                    # Get total count
                    count_query = f"SELECT COUNT(*) FROM memory.audit_log {where_clause}"
                    total = await conn.fetchval(count_query, *params)
                    
                    # Get entries
                    query = f"""
                        SELECT entry_id, timestamp, user_id, action, resource, 
                               details, ip_address, success, severity, data_hash
                        FROM memory.audit_log
                        {where_clause}
                        ORDER BY timestamp DESC
                        LIMIT ${param_idx} OFFSET ${param_idx + 1}
                    """
                    params.extend([limit, offset])
                    
                    rows = await conn.fetch(query, *params)
                    
                    entries = []
                    for row in rows:
                        import json
                        entries.append(AuditEntry(
                            entry_id=str(row["entry_id"]),
                            timestamp=row["timestamp"],
                            user_id=row["user_id"],
                            action=row["action"],
                            resource=row["resource"],
                            details=json.loads(row["details"]) if row["details"] else {},
                            ip_address=row["ip_address"] or "",
                            success=row["success"],
                            severity=row["severity"] or "info",
                            data_hash=row["data_hash"]
                        ))
                    
                    return AuditQueryResponse(
                        entries=entries,
                        count=len(entries),
                        has_more=total > offset + limit,
                        source="postgres"
                    )
            except Exception as e:
                logger.error(f"Failed to query PostgreSQL: {e}")
        
        # Fallback to memory
        results = self._memory_log.copy()
        
        if user_id:
            results = [e for e in results if e.user_id == user_id]
        if action:
            results = [e for e in results if e.action == action]
        if resource:
            results = [e for e in results if resource in e.resource]
        if severity:
            results = [e for e in results if e.severity == severity]
        
        results.sort(key=lambda x: x.timestamp, reverse=True)
        total = len(results)
        results = results[offset:offset + limit]
        
        return AuditQueryResponse(
            entries=results,
            count=len(results),
            has_more=total > offset + limit,
            source="memory"
        )
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get audit log statistics."""
        pool = await self._get_pool()
        
        if pool:
            try:
                async with pool.acquire() as conn:
                    stats = {}
                    
                    # Total entries
                    stats["total_entries"] = await conn.fetchval(
                        "SELECT COUNT(*) FROM memory.audit_log"
                    )
                    
                    # By severity
                    severity_rows = await conn.fetch("""
                        SELECT severity, COUNT(*) as count 
                        FROM memory.audit_log 
                        GROUP BY severity
                    """)
                    stats["by_severity"] = {r["severity"]: r["count"] for r in severity_rows}
                    
                    # By action
                    action_rows = await conn.fetch("""
                        SELECT action, COUNT(*) as count 
                        FROM memory.audit_log 
                        GROUP BY action
                        ORDER BY count DESC
                        LIMIT 10
                    """)
                    stats["by_action"] = {r["action"]: r["count"] for r in action_rows}
                    
                    # Success/failure
                    stats["success_count"] = await conn.fetchval(
                        "SELECT COUNT(*) FROM memory.audit_log WHERE success = TRUE"
                    )
                    stats["failure_count"] = stats["total_entries"] - stats["success_count"]
                    stats["success_rate"] = (
                        (stats["success_count"] / stats["total_entries"] * 100)
                        if stats["total_entries"] > 0 else 0
                    )
                    
                    # Last entry
                    last = await conn.fetchval(
                        "SELECT timestamp FROM memory.audit_log ORDER BY timestamp DESC LIMIT 1"
                    )
                    stats["last_entry_at"] = last.isoformat() if last else None
                    stats["source"] = "postgres"
                    
                    return stats
            except Exception as e:
                logger.error(f"Failed to get stats from PostgreSQL: {e}")
        
        # Fallback to memory
        total = len(self._memory_log)
        severity_counts = {}
        action_counts = {}
        successes = 0
        
        for entry in self._memory_log:
            severity_counts[entry.severity] = severity_counts.get(entry.severity, 0) + 1
            action_counts[entry.action] = action_counts.get(entry.action, 0) + 1
            if entry.success:
                successes += 1
        
        return {
            "total_entries": total,
            "by_severity": severity_counts,
            "by_action": action_counts,
            "success_count": successes,
            "failure_count": total - successes,
            "success_rate": (successes / total * 100) if total > 0 else 0,
            "last_entry_at": self._memory_log[-1].timestamp.isoformat() if self._memory_log else None,
            "source": "memory"
        }


# Singleton instance
_audit_log: Optional[PersistentAuditLog] = None


def get_audit_log() -> PersistentAuditLog:
    """Get singleton audit log instance."""
    global _audit_log
    if _audit_log is None:
        _audit_log = PersistentAuditLog()
    return _audit_log


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/audit/log", response_model=AuditEntry)
async def log_audit_entry(request: AuditLogRequest):
    """Log a security audit entry with cryptographic integrity."""
    entry = AuditEntry(
        user_id=request.user_id,
        action=request.action,
        resource=request.resource,
        details=request.details or {},
        ip_address=request.ip_address,
        success=request.success,
        severity=request.severity,
    )
    
    audit_log = get_audit_log()
    entry = await audit_log.log(entry)
    
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
    audit_log = get_audit_log()
    return await audit_log.query(
        user_id=user_id,
        action=action,
        resource=resource,
        severity=severity,
        limit=limit,
        offset=offset
    )


@router.get("/audit/stats")
async def get_audit_stats():
    """Get audit log statistics for SOC dashboard."""
    audit_log = get_audit_log()
    return await audit_log.get_stats()


@router.get("/health")
async def security_health():
    """Security service health check."""
    audit_log = get_audit_log()
    stats = await audit_log.get_stats()
    
    return {
        "status": "healthy",
        "service": "security-audit",
        "audit_entries": stats.get("total_entries", 0),
        "storage": stats.get("source", "unknown"),
        "integrity_available": INTEGRITY_AVAILABLE,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
