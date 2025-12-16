"""
Action Audit Log Module

Provides persistence and retrieval of action audit logs to PostgreSQL.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


@dataclass
class AuditEntry:
    """
    An audit log entry for an action execution.
    
    This is the in-memory representation of an audit log entry
    before/after persistence to the database.
    """
    id: UUID = field(default_factory=uuid4)
    
    # Identifiers
    correlation_id: UUID = field(default_factory=uuid4)
    agent_run_id: Optional[UUID] = None
    agent_id: str = ""
    
    # Action details
    action_type: str = ""
    action_name: str = ""
    action_category: Optional[str] = None
    
    # Inputs/Outputs (redacted)
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    
    # Status
    status: str = "pending"
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    
    # Approval
    requires_approval: bool = False
    approval_status: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    approval_notes: Optional[str] = None
    
    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    
    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)
    request_metadata: dict[str, Any] = field(default_factory=dict)


class ActionAuditLog:
    """
    Action audit logging service.
    
    Provides methods to log, query, and manage action audit entries
    in PostgreSQL.
    
    Usage:
        # Log an action
        entry = await ActionAuditLog.log(
            action_name="send_email",
            action_category="email",
            inputs={"to": "user@example.com"},
            agent_id="email_agent",
            correlation_id=uuid4(),
        )
        
        # Query recent actions
        entries = await ActionAuditLog.get_recent(limit=100)
        
        # Get pending approvals
        pending = await ActionAuditLog.get_pending_approvals()
    """
    
    _pool = None
    
    @classmethod
    async def _get_pool(cls):
        """Get or create database connection pool."""
        if cls._pool is None:
            try:
                import asyncpg
                db_url = os.getenv(
                    "DATABASE_URL",
                    "postgresql://mas:maspassword@localhost:5432/mas"
                )
                cls._pool = await asyncpg.create_pool(db_url, min_size=2, max_size=10)
            except ImportError:
                logger.warning("asyncpg not installed, audit logging disabled")
                return None
            except Exception as e:
                logger.error(f"Failed to create database pool: {e}")
                return None
        return cls._pool
    
    @classmethod
    async def log(
        cls,
        action_name: str,
        action_type: str = "",
        action_category: Optional[str] = None,
        inputs: Optional[dict[str, Any]] = None,
        outputs: Optional[dict[str, Any]] = None,
        agent_id: str = "",
        correlation_id: Optional[UUID] = None,
        agent_run_id: Optional[UUID] = None,
        status: str = "pending",
        error_message: Optional[str] = None,
        requires_approval: bool = False,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AuditEntry:
        """
        Log an action execution to the audit log.
        
        Args:
            action_name: Name of the action
            action_type: Type of action (e.g., "tool_call", "api_request")
            action_category: Category for policy (e.g., "external_write")
            inputs: Action inputs (will be redacted)
            outputs: Action outputs (will be redacted)
            agent_id: ID of the executing agent
            correlation_id: Correlation ID for tracing
            agent_run_id: ID of the agent run
            status: Current status
            error_message: Error message if failed
            requires_approval: Whether approval is required
            metadata: Additional metadata
            
        Returns:
            The created AuditEntry
        """
        entry = AuditEntry(
            correlation_id=correlation_id or uuid4(),
            agent_run_id=agent_run_id,
            agent_id=agent_id,
            action_type=action_type,
            action_name=action_name,
            action_category=action_category,
            inputs=inputs or {},
            outputs=outputs or {},
            status=status,
            error_message=error_message,
            requires_approval=requires_approval,
            approval_status="pending" if requires_approval else None,
            metadata=metadata or {},
        )
        
        # Try to persist to database
        pool = await cls._get_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO audit.action_audit_log (
                            id, correlation_id, agent_run_id, agent_id,
                            action_type, action_name, action_category,
                            inputs, outputs, status, error_message,
                            requires_approval, approval_status,
                            created_at, metadata
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                        """,
                        entry.id,
                        entry.correlation_id,
                        entry.agent_run_id,
                        entry.agent_id,
                        entry.action_type,
                        entry.action_name,
                        entry.action_category,
                        json.dumps(entry.inputs),
                        json.dumps(entry.outputs),
                        entry.status,
                        entry.error_message,
                        entry.requires_approval,
                        entry.approval_status,
                        entry.created_at,
                        json.dumps(entry.metadata),
                    )
            except Exception as e:
                logger.error(f"Failed to persist audit log: {e}")
        
        return entry
    
    @classmethod
    async def update(
        cls,
        entry_id: UUID,
        status: Optional[str] = None,
        outputs: Optional[dict[str, Any]] = None,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None,
        completed_at: Optional[datetime] = None,
        duration_ms: Optional[int] = None,
        approval_status: Optional[str] = None,
        approved_by: Optional[str] = None,
        approval_notes: Optional[str] = None,
    ) -> bool:
        """
        Update an existing audit log entry.
        
        Args:
            entry_id: ID of the entry to update
            status: New status
            outputs: Action outputs
            error_message: Error message if failed
            error_type: Error type
            completed_at: Completion timestamp
            duration_ms: Duration in milliseconds
            approval_status: Approval status
            approved_by: Who approved
            approval_notes: Approval notes
            
        Returns:
            True if update succeeded
        """
        pool = await cls._get_pool()
        if not pool:
            return False
        
        try:
            async with pool.acquire() as conn:
                # Build dynamic UPDATE query
                updates = []
                params = []
                param_idx = 1
                
                if status is not None:
                    updates.append(f"status = ${param_idx}")
                    params.append(status)
                    param_idx += 1
                
                if outputs is not None:
                    updates.append(f"outputs = ${param_idx}")
                    params.append(json.dumps(outputs))
                    param_idx += 1
                
                if error_message is not None:
                    updates.append(f"error_message = ${param_idx}")
                    params.append(error_message)
                    param_idx += 1
                
                if error_type is not None:
                    updates.append(f"error_type = ${param_idx}")
                    params.append(error_type)
                    param_idx += 1
                
                if completed_at is not None:
                    updates.append(f"completed_at = ${param_idx}")
                    params.append(completed_at)
                    param_idx += 1
                
                if duration_ms is not None:
                    updates.append(f"duration_ms = ${param_idx}")
                    params.append(duration_ms)
                    param_idx += 1
                
                if approval_status is not None:
                    updates.append(f"approval_status = ${param_idx}")
                    params.append(approval_status)
                    param_idx += 1
                
                if approved_by is not None:
                    updates.append(f"approved_by = ${param_idx}")
                    params.append(approved_by)
                    param_idx += 1
                    updates.append(f"approved_at = ${param_idx}")
                    params.append(datetime.now())
                    param_idx += 1
                
                if approval_notes is not None:
                    updates.append(f"approval_notes = ${param_idx}")
                    params.append(approval_notes)
                    param_idx += 1
                
                if not updates:
                    return True
                
                params.append(entry_id)
                query = f"""
                    UPDATE audit.action_audit_log
                    SET {', '.join(updates)}
                    WHERE id = ${param_idx}
                """
                
                await conn.execute(query, *params)
                return True
                
        except Exception as e:
            logger.error(f"Failed to update audit log: {e}")
            return False
    
    @classmethod
    async def get_recent(
        cls,
        limit: int = 100,
        agent_id: Optional[str] = None,
        correlation_id: Optional[UUID] = None,
        action_category: Optional[str] = None,
    ) -> list[AuditEntry]:
        """
        Get recent audit log entries.
        
        Args:
            limit: Maximum number of entries
            agent_id: Filter by agent ID
            correlation_id: Filter by correlation ID
            action_category: Filter by category
            
        Returns:
            List of AuditEntry objects
        """
        pool = await cls._get_pool()
        if not pool:
            return []
        
        try:
            async with pool.acquire() as conn:
                # Build query with filters
                conditions = []
                params = []
                param_idx = 1
                
                if agent_id:
                    conditions.append(f"agent_id = ${param_idx}")
                    params.append(agent_id)
                    param_idx += 1
                
                if correlation_id:
                    conditions.append(f"correlation_id = ${param_idx}")
                    params.append(correlation_id)
                    param_idx += 1
                
                if action_category:
                    conditions.append(f"action_category = ${param_idx}")
                    params.append(action_category)
                    param_idx += 1
                
                where_clause = ""
                if conditions:
                    where_clause = "WHERE " + " AND ".join(conditions)
                
                params.append(limit)
                query = f"""
                    SELECT * FROM audit.action_audit_log
                    {where_clause}
                    ORDER BY created_at DESC
                    LIMIT ${param_idx}
                """
                
                rows = await conn.fetch(query, *params)
                
                return [cls._row_to_entry(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to query audit log: {e}")
            return []
    
    @classmethod
    async def get_pending_approvals(cls) -> list[AuditEntry]:
        """Get all entries pending approval."""
        pool = await cls._get_pool()
        if not pool:
            return []
        
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT * FROM audit.action_audit_log
                    WHERE requires_approval = true AND approval_status = 'pending'
                    ORDER BY created_at ASC
                    """
                )
                return [cls._row_to_entry(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to query pending approvals: {e}")
            return []
    
    @classmethod
    async def get_by_correlation_id(cls, correlation_id: UUID) -> list[AuditEntry]:
        """Get all entries for a correlation ID."""
        return await cls.get_recent(limit=1000, correlation_id=correlation_id)
    
    @classmethod
    def _row_to_entry(cls, row) -> AuditEntry:
        """Convert a database row to an AuditEntry."""
        return AuditEntry(
            id=row["id"],
            correlation_id=row["correlation_id"],
            agent_run_id=row["agent_run_id"],
            agent_id=row["agent_id"],
            action_type=row["action_type"],
            action_name=row["action_name"],
            action_category=row["action_category"],
            inputs=json.loads(row["inputs"]) if row["inputs"] else {},
            outputs=json.loads(row["outputs"]) if row["outputs"] else {},
            status=row["status"],
            error_message=row["error_message"],
            error_type=row["error_type"],
            requires_approval=row["requires_approval"],
            approval_status=row["approval_status"],
            approved_by=row["approved_by"],
            approved_at=row["approved_at"],
            approval_notes=row["approval_notes"],
            created_at=row["created_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            duration_ms=row["duration_ms"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )
