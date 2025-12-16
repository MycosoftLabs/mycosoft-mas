"""
Action Audit Logging System

Logs all tool actions and agent operations for auditability and safety.
"""

import os
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass, asdict
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ActionStatus(Enum):
    """Status of an action."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ActionCategory(Enum):
    """Category of action for approval policy."""
    READ_ONLY = "read_only"
    INTERNAL_WRITE = "internal_write"
    EXTERNAL_WRITE = "external_write"
    DESTRUCTIVE = "destructive"
    FINANCIAL = "financial"
    SYSTEM = "system"


@dataclass
class ActionAuditLog:
    """Audit log entry for an action."""
    id: str
    agent_id: str
    agent_name: str
    action_type: str
    action_category: str
    tool_name: Optional[str]
    inputs: Dict[str, Any]
    outputs: Optional[Dict[str, Any]]
    status: str
    correlation_id: str
    run_id: Optional[str]
    error: Optional[str]
    requires_approval: bool
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    created_at: datetime
    completed_at: Optional[datetime]
    metadata: Dict[str, Any]


class ActionAuditLogger:
    """Logger for action audit trails."""
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize audit logger.
        
        Args:
            database_url: PostgreSQL connection URL
        """
        self.database_url = database_url or os.getenv("DATABASE_URL")
        self.approval_required = os.getenv("APPROVAL_REQUIRED", "false").lower() == "true"
        self.audit_enabled = os.getenv("ACTION_AUDIT_ENABLED", "true").lower() == "true"
        self._ensure_table()
    
    def _get_connection(self):
        """Get database connection."""
        if not self.database_url:
            logger.warning("No DATABASE_URL configured, audit logging disabled")
            return None
        
        try:
            parsed = urlparse(self.database_url)
            conn = psycopg2.connect(
                host=parsed.hostname or "localhost",
                port=parsed.port or 5432,
                user=parsed.username or "mas",
                password=parsed.password or "maspassword",
                dbname=parsed.path[1:] if parsed.path else "mas",
            )
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to database for audit logging: {e}")
            return None
    
    def _ensure_table(self):
        """Ensure audit log table exists."""
        if not self.audit_enabled:
            return
        
        conn = self._get_connection()
        if not conn:
            return
        
        try:
            with conn.cursor() as cur:
                # Create schema if not exists
                cur.execute("CREATE SCHEMA IF NOT EXISTS audit")
                
                # Create table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS audit.action_logs (
                        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                        agent_id VARCHAR(255) NOT NULL,
                        agent_name VARCHAR(255) NOT NULL,
                        action_type VARCHAR(100) NOT NULL,
                        action_category VARCHAR(50) NOT NULL,
                        tool_name VARCHAR(255),
                        inputs JSONB NOT NULL,
                        outputs JSONB,
                        status VARCHAR(50) NOT NULL,
                        correlation_id VARCHAR(255) NOT NULL,
                        run_id VARCHAR(255),
                        error TEXT,
                        requires_approval BOOLEAN NOT NULL DEFAULT false,
                        approved_by VARCHAR(255),
                        approved_at TIMESTAMP WITH TIME ZONE,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP WITH TIME ZONE,
                        metadata JSONB DEFAULT '{}'
                    )
                """)
                
                # Create indexes
                cur.execute("CREATE INDEX IF NOT EXISTS idx_action_logs_correlation_id ON audit.action_logs(correlation_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_action_logs_agent_id ON audit.action_logs(agent_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_action_logs_status ON audit.action_logs(status)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_action_logs_created_at ON audit.action_logs(created_at)")
                conn.commit()
                logger.info("Audit log table ensured")
        except Exception as e:
            logger.error(f"Failed to create audit log table: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def _redact_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive data from inputs/outputs."""
        sensitive_keys = ["password", "api_key", "token", "secret", "key"]
        redacted = {}
        
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                redacted[key] = "***REDACTED***"
            elif isinstance(value, dict):
                redacted[key] = self._redact_sensitive_data(value)
            elif isinstance(value, list):
                redacted[key] = [
                    self._redact_sensitive_data(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                redacted[key] = value
        
        return redacted
    
    def _requires_approval(self, category: ActionCategory) -> bool:
        """Check if action requires approval based on category."""
        if not self.approval_required:
            return False
        
        # Approval required for external writes, destructive, and financial actions
        return category in [
            ActionCategory.EXTERNAL_WRITE,
            ActionCategory.DESTRUCTIVE,
            ActionCategory.FINANCIAL,
        ]
    
    async def log_action(
        self,
        agent_id: str,
        agent_name: str,
        action_type: str,
        category: ActionCategory,
        inputs: Dict[str, Any],
        tool_name: Optional[str] = None,
        correlation_id: Optional[str] = None,
        run_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Log an action.
        
        Returns:
            Action log ID
        """
        if not self.audit_enabled:
            return ""
        
        action_id = str(uuid.uuid4())
        correlation_id = correlation_id or str(uuid.uuid4())
        requires_approval = self._requires_approval(category)
        
        # Redact sensitive data
        redacted_inputs = self._redact_sensitive_data(inputs)
        
        log_entry = ActionAuditLog(
            id=action_id,
            agent_id=agent_id,
            agent_name=agent_name,
            action_type=action_type,
            action_category=category.value,
            tool_name=tool_name,
            inputs=redacted_inputs,
            outputs=None,
            status=ActionStatus.PENDING.value if requires_approval else ActionStatus.EXECUTING.value,
            correlation_id=correlation_id,
            run_id=run_id,
            error=None,
            requires_approval=requires_approval,
            approved_by=None,
            approved_at=None,
            created_at=datetime.now(),
            completed_at=None,
            metadata=metadata or {},
        )
        
        conn = self._get_connection()
        if not conn:
            logger.warning("Cannot log action - no database connection")
            return action_id
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO audit.action_logs (
                        id, agent_id, agent_name, action_type, action_category,
                        tool_name, inputs, status, correlation_id, run_id,
                        requires_approval, created_at, metadata
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """, (
                    log_entry.id,
                    log_entry.agent_id,
                    log_entry.agent_name,
                    log_entry.action_type,
                    log_entry.action_category,
                    log_entry.tool_name,
                    json.dumps(log_entry.inputs),
                    log_entry.status,
                    log_entry.correlation_id,
                    log_entry.run_id,
                    log_entry.requires_approval,
                    log_entry.created_at,
                    json.dumps(log_entry.metadata),
                ))
                conn.commit()
                logger.debug(f"Logged action {action_id} for agent {agent_name}")
        except Exception as e:
            logger.error(f"Failed to log action: {e}")
            conn.rollback()
        finally:
            conn.close()
        
        return action_id
    
    async def update_action(
        self,
        action_id: str,
        status: Optional[ActionStatus] = None,
        outputs: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ):
        """Update an action log entry."""
        if not self.audit_enabled:
            return
        
        conn = self._get_connection()
        if not conn:
            return
        
        try:
            updates = []
            params = []
            
            if status:
                updates.append("status = %s")
                params.append(status.value)
            
            if outputs is not None:
                redacted_outputs = self._redact_sensitive_data(outputs)
                updates.append("outputs = %s")
                params.append(json.dumps(redacted_outputs))
            
            if error:
                updates.append("error = %s")
                params.append(error)
            
            if status in [ActionStatus.COMPLETED, ActionStatus.FAILED, ActionStatus.CANCELLED]:
                updates.append("completed_at = %s")
                params.append(datetime.now())
            
            if updates:
                params.append(action_id)
                with conn.cursor() as cur:
                    cur.execute(
                        f"UPDATE audit.action_logs SET {', '.join(updates)} WHERE id = %s",
                        params
                    )
                    conn.commit()
        except Exception as e:
            logger.error(f"Failed to update action log: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    async def approve_action(self, action_id: str, approved_by: str) -> bool:
        """Approve a pending action."""
        if not self.audit_enabled:
            return True
        
        conn = self._get_connection()
        if not conn:
            return False
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE audit.action_logs
                    SET status = %s, approved_by = %s, approved_at = %s
                    WHERE id = %s AND status = %s
                """, (
                    ActionStatus.APPROVED.value,
                    approved_by,
                    datetime.now(),
                    action_id,
                    ActionStatus.PENDING.value,
                ))
                conn.commit()
                return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to approve action: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    async def get_action_logs(
        self,
        agent_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get action logs."""
        if not self.audit_enabled:
            return []
        
        conn = self._get_connection()
        if not conn:
            return []
        
        try:
            conditions = []
            params = []
            
            if agent_id:
                conditions.append("agent_id = %s")
                params.append(agent_id)
            
            if correlation_id:
                conditions.append("correlation_id = %s")
                params.append(correlation_id)
            
            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            params.append(limit)
            
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"""
                    SELECT * FROM audit.action_logs
                    {where_clause}
                    ORDER BY created_at DESC
                    LIMIT %s
                """, params)
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get action logs: {e}")
            return []
        finally:
            conn.close()


# Global audit logger instance
_audit_logger: Optional[ActionAuditLogger] = None


def get_audit_logger() -> ActionAuditLogger:
    """Get or create global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = ActionAuditLogger()
    return _audit_logger
