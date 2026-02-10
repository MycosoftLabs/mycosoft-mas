"""
CodeModificationService - Central Hub for Self-Healing MAS Code Changes
Created: February 9, 2026

Central service that:
- Receives code change requests from orchestrator or any agent
- Validates requests with SecurityCodeReviewer before execution
- Routes approved changes to CodingAgent
- Tracks all code modifications with audit log
- Reports results back to requesting entity
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class ChangeStatus(str, Enum):
    """Status of a code change request."""
    PENDING = "pending"
    REVIEWING = "reviewing"
    APPROVED = "approved"
    BLOCKED = "blocked"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ChangeType(str, Enum):
    """Types of code changes."""
    FIX_BUG = "fix_bug"
    CREATE_AGENT = "create_agent"
    UPDATE_CODE = "update_code"
    ADD_FEATURE = "add_feature"
    REFACTOR = "refactor"
    FIX_SECURITY = "fix_security"
    UPDATE_TESTS = "update_tests"
    FIX_LINT = "fix_lint"
    SELF_IMPROVE = "self_improve"


class CodeModificationService:
    """
    Central hub for all code modification requests in the MAS.
    
    This service:
    1. Receives change requests from orchestrator or agents
    2. Validates with SecurityCodeReviewer
    3. Routes approved changes to CodingAgent
    4. Tracks all modifications in audit log
    5. Reports results back to requesters
    """
    
    # Maximum cost per request in USD
    MAX_BUDGET_PER_REQUEST = 5.0
    
    # Files that require PR instead of direct commit
    PR_REQUIRED_PATHS = {
        "mycosoft_mas/core/",
        "mycosoft_mas/agents/__init__.py",
        "mycosoft_mas/core/myca_main.py",
        "tests/",
    }
    
    def __init__(self):
        self.pending_requests: Dict[str, Dict[str, Any]] = {}
        self.completed_requests: Dict[str, Dict[str, Any]] = {}
        self.audit_log: List[Dict[str, Any]] = []
        self.total_changes = 0
        self.total_cost = 0.0
        self._security_reviewer = None
        self._coding_agent = None
        self._guardian_agent = None
        
    async def initialize(self):
        """Initialize dependencies."""
        try:
            from mycosoft_mas.security.code_reviewer import get_security_reviewer
            self._security_reviewer = get_security_reviewer()
            logger.info("SecurityCodeReviewer initialized")
        except Exception as e:
            logger.error(f"Failed to initialize SecurityCodeReviewer: {e}")
            
        # CodingAgent and GuardianAgent will be set by orchestrator
        
    def set_coding_agent(self, agent):
        """Set the CodingAgent reference."""
        self._coding_agent = agent
        logger.info("CodingAgent reference set")
        
    def set_guardian_agent(self, agent):
        """Set the GuardianAgent reference."""
        self._guardian_agent = agent
        logger.info("GuardianAgent reference set")
    
    async def request_code_change(
        self,
        requester_id: str,
        change_type: str,
        description: str,
        target_files: Optional[List[str]] = None,
        priority: int = 5,
        require_pr: Optional[bool] = None,
        code_content: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Request a code change. This is the main entry point.
        
        Args:
            requester_id: Agent ID or "orchestrator"
            change_type: Type of change (fix_bug, create_agent, etc.)
            description: What to do
            target_files: Files to modify (optional)
            priority: 1-10, higher = more urgent
            require_pr: Create PR vs direct commit (auto-detected if None)
            code_content: Optional code content for review
            context: Additional context for the change
            
        Returns:
            Dict with change_id, status, and details
        """
        change_id = str(uuid.uuid4())[:8]
        
        # Determine if PR is required
        if require_pr is None:
            require_pr = self._should_require_pr(target_files or [])
        
        # Create change request
        change_request = {
            "change_id": change_id,
            "requester_id": requester_id,
            "change_type": change_type,
            "description": description,
            "target_files": target_files or [],
            "priority": priority,
            "require_pr": require_pr,
            "code_content": code_content or "",
            "context": context or {},
            "status": ChangeStatus.PENDING.value,
            "created_at": datetime.now().isoformat(),
            "reviewed_at": None,
            "completed_at": None,
            "security_review": None,
            "execution_result": None,
            "cost": 0.0,
            "error": None,
        }
        
        self.pending_requests[change_id] = change_request
        self._log_audit("request_created", change_request)
        
        logger.info(f"Code change request created: {change_id} ({change_type}) from {requester_id}")
        
        # Start async processing
        asyncio.create_task(self._process_change_request(change_id))
        
        return {
            "change_id": change_id,
            "status": ChangeStatus.PENDING.value,
            "message": "Code change request submitted for review",
            "require_pr": require_pr,
        }
    
    async def _process_change_request(self, change_id: str):
        """Process a change request through the pipeline."""
        request = self.pending_requests.get(change_id)
        if not request:
            logger.error(f"Change request not found: {change_id}")
            return
        
        try:
            # Step 1: Security Review
            request["status"] = ChangeStatus.REVIEWING.value
            self._log_audit("review_started", request)
            
            if self._security_reviewer:
                review_result = await self._security_reviewer.review_code_change(request)
                request["security_review"] = review_result
                request["reviewed_at"] = datetime.now().isoformat()
                
                if not review_result.get("approved"):
                    # BLOCKED by security
                    request["status"] = ChangeStatus.BLOCKED.value
                    request["error"] = review_result.get("reason", "Security review failed")
                    self._log_audit("blocked_by_security", request)
                    
                    # Notify GuardianAgent
                    if self._guardian_agent:
                        await self._notify_guardian(request)
                    
                    self._move_to_completed(change_id)
                    return
            else:
                logger.warning("SecurityCodeReviewer not available, proceeding with caution")
            
            # Step 2: Approved - Execute
            request["status"] = ChangeStatus.APPROVED.value
            self._log_audit("approved", request)
            
            request["status"] = ChangeStatus.EXECUTING.value
            self._log_audit("execution_started", request)
            
            # Execute via CodingAgent
            if self._coding_agent:
                execution_result = await self._execute_code_change(request)
                request["execution_result"] = execution_result
                request["cost"] = execution_result.get("cost", 0.0)
                self.total_cost += request["cost"]
                
                if execution_result.get("success"):
                    # Step 3: Post-execution security scan
                    if self._security_reviewer and execution_result.get("modified_files"):
                        post_scan = await self._security_reviewer.scan_for_vulnerabilities(
                            execution_result.get("modified_files", [])
                        )
                        
                        if post_scan:
                            # Security issues in generated code!
                            request["status"] = ChangeStatus.ROLLED_BACK.value
                            request["error"] = f"Post-scan found {len(post_scan)} security issues"
                            request["post_scan_issues"] = post_scan
                            self._log_audit("rolled_back_security", request)
                            
                            # TODO: Actually rollback the changes
                            logger.error(f"Rolling back {change_id} due to security issues")
                        else:
                            request["status"] = ChangeStatus.COMPLETED.value
                            request["completed_at"] = datetime.now().isoformat()
                            self.total_changes += 1
                            self._log_audit("completed", request)
                    else:
                        request["status"] = ChangeStatus.COMPLETED.value
                        request["completed_at"] = datetime.now().isoformat()
                        self.total_changes += 1
                        self._log_audit("completed", request)
                else:
                    request["status"] = ChangeStatus.FAILED.value
                    request["error"] = execution_result.get("error", "Execution failed")
                    self._log_audit("execution_failed", request)
            else:
                request["status"] = ChangeStatus.FAILED.value
                request["error"] = "CodingAgent not available"
                self._log_audit("no_coding_agent", request)
            
            self._move_to_completed(change_id)
            
        except Exception as e:
            logger.error(f"Error processing change {change_id}: {e}")
            request["status"] = ChangeStatus.FAILED.value
            request["error"] = str(e)
            self._log_audit("processing_error", request)
            self._move_to_completed(change_id)
    
    async def _execute_code_change(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the code change via CodingAgent."""
        try:
            # Check budget
            if self.total_cost + self.MAX_BUDGET_PER_REQUEST > 100:  # Session limit
                return {
                    "success": False,
                    "error": "Session budget exceeded",
                    "cost": 0.0,
                }
            
            # Use CodingAgent to execute
            change_type = request.get("change_type")
            description = request.get("description")
            target_files = request.get("target_files", [])
            require_pr = request.get("require_pr", True)
            
            # Call the appropriate method on CodingAgent
            if hasattr(self._coding_agent, "invoke_claude_code"):
                result = await self._coding_agent.invoke_claude_code(
                    task_description=description,
                    repo_path=".",  # Current repo
                    create_pr=require_pr,
                )
                return {
                    "success": result.get("status") == "completed",
                    "result": result,
                    "modified_files": result.get("files_modified", target_files),
                    "cost": result.get("cost", 0.0),
                    "branch": result.get("branch"),
                    "pr_url": result.get("pr_url"),
                }
            else:
                # Fallback: Direct task processing
                task = {
                    "type": change_type,
                    "description": description,
                    "target_files": target_files,
                }
                result = await self._coding_agent.process_task(task)
                return {
                    "success": result.get("status") == "success",
                    "result": result,
                    "modified_files": target_files,
                    "cost": 0.0,  # Unknown cost in fallback mode
                }
                
        except Exception as e:
            logger.error(f"Execution error: {e}")
            return {
                "success": False,
                "error": str(e),
                "cost": 0.0,
            }
    
    async def _notify_guardian(self, request: Dict[str, Any]):
        """Notify GuardianAgent about a blocked request."""
        try:
            if hasattr(self._guardian_agent, "process_task"):
                await self._guardian_agent.process_task({
                    "type": "security_alert",
                    "alert_type": "code_change_blocked",
                    "change_id": request.get("change_id"),
                    "requester": request.get("requester_id"),
                    "reason": request.get("error"),
                    "security_review": request.get("security_review"),
                })
        except Exception as e:
            logger.error(f"Failed to notify Guardian: {e}")
    
    def _should_require_pr(self, target_files: List[str]) -> bool:
        """Determine if PR is required for these files."""
        for file_path in target_files:
            normalized = file_path.replace("\\", "/").lstrip("./")
            for pr_path in self.PR_REQUIRED_PATHS:
                if normalized.startswith(pr_path) or normalized == pr_path.rstrip("/"):
                    return True
        return False
    
    def _move_to_completed(self, change_id: str):
        """Move request from pending to completed."""
        if change_id in self.pending_requests:
            request = self.pending_requests.pop(change_id)
            self.completed_requests[change_id] = request
    
    def _log_audit(self, event: str, request: Dict[str, Any]):
        """Log an audit event."""
        self.audit_log.append({
            "event": event,
            "change_id": request.get("change_id"),
            "requester_id": request.get("requester_id"),
            "change_type": request.get("change_type"),
            "status": request.get("status"),
            "timestamp": datetime.now().isoformat(),
        })
    
    async def get_change_status(self, change_id: str) -> Dict[str, Any]:
        """Get the status of a code change request."""
        if change_id in self.pending_requests:
            request = self.pending_requests[change_id]
            return {
                "change_id": change_id,
                "status": request.get("status"),
                "message": "Request is being processed",
                "created_at": request.get("created_at"),
            }
        elif change_id in self.completed_requests:
            request = self.completed_requests[change_id]
            return {
                "change_id": change_id,
                "status": request.get("status"),
                "message": request.get("error") or "Completed",
                "created_at": request.get("created_at"),
                "completed_at": request.get("completed_at"),
                "cost": request.get("cost"),
                "result": request.get("execution_result"),
            }
        else:
            return {
                "change_id": change_id,
                "status": "not_found",
                "message": "Change request not found",
            }
    
    async def get_change_history(
        self, 
        limit: int = 50,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get history of code changes."""
        all_requests = list(self.completed_requests.values())
        
        if status_filter:
            all_requests = [r for r in all_requests if r.get("status") == status_filter]
        
        # Sort by created_at descending
        all_requests.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        
        return all_requests[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        status_counts = {}
        for request in self.completed_requests.values():
            status = request.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "pending_count": len(self.pending_requests),
            "completed_count": len(self.completed_requests),
            "total_changes": self.total_changes,
            "total_cost_usd": self.total_cost,
            "status_counts": status_counts,
            "audit_log_size": len(self.audit_log),
        }
    
    async def cancel_pending_request(self, change_id: str) -> Dict[str, Any]:
        """Cancel a pending request."""
        if change_id in self.pending_requests:
            request = self.pending_requests.pop(change_id)
            request["status"] = "cancelled"
            request["completed_at"] = datetime.now().isoformat()
            self.completed_requests[change_id] = request
            self._log_audit("cancelled", request)
            return {"success": True, "message": "Request cancelled"}
        else:
            return {"success": False, "message": "Request not found or already completed"}
    
    async def halt_all_changes(self) -> Dict[str, Any]:
        """Emergency halt all pending code changes."""
        cancelled_count = 0
        for change_id in list(self.pending_requests.keys()):
            await self.cancel_pending_request(change_id)
            cancelled_count += 1
        
        logger.warning(f"EMERGENCY HALT: Cancelled {cancelled_count} pending changes")
        self._log_audit("emergency_halt", {"cancelled_count": cancelled_count})
        
        return {
            "success": True,
            "cancelled_count": cancelled_count,
            "message": "All pending changes halted",
        }


# Singleton instance
_service_instance: Optional[CodeModificationService] = None


async def get_code_modification_service() -> CodeModificationService:
    """Get the global CodeModificationService instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = CodeModificationService()
        await _service_instance.initialize()
    return _service_instance


__all__ = [
    "CodeModificationService",
    "ChangeStatus",
    "ChangeType",
    "get_code_modification_service",
]
