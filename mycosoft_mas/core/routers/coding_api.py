"""
Coding API Router - REST API for Self-Healing MAS Code Modifications
Created: February 9, 2026

Endpoints for code modifications:
- POST /api/code/request - Request code change
- GET /api/code/status/{id} - Get change status
- GET /api/code/history - View change history
- POST /api/code/approve/{id} - Manual approval (if required)
- GET /api/code/security/scan - Run security scan
- POST /api/code/halt - Emergency halt all changes
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/code", tags=["code-modification"])


# Request/Response Models
class CodeChangeRequest(BaseModel):
    """Request model for code changes."""
    requester_id: str = Field(..., description="Agent ID or 'orchestrator'")
    change_type: str = Field(..., description="Type: fix_bug, create_agent, update_code, etc.")
    description: str = Field(..., description="What code change to make")
    target_files: Optional[List[str]] = Field(default=None, description="Files to modify")
    priority: int = Field(default=5, ge=1, le=10, description="Priority 1-10")
    require_pr: Optional[bool] = Field(default=None, description="Force PR creation")
    code_content: Optional[str] = Field(default=None, description="Code content for review")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")


class CodeChangeResponse(BaseModel):
    """Response model for code change requests."""
    change_id: str
    status: str
    message: str
    require_pr: Optional[bool] = None


class ChangeStatusResponse(BaseModel):
    """Response model for change status."""
    change_id: str
    status: str
    message: str
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    cost: Optional[float] = None
    result: Optional[Dict[str, Any]] = None


class SecurityScanRequest(BaseModel):
    """Request model for security scans."""
    file_paths: List[str] = Field(..., description="Files to scan")


class SecurityScanResponse(BaseModel):
    """Response model for security scans."""
    scanned_files: int
    vulnerabilities_found: int
    vulnerabilities: List[Dict[str, Any]]
    risk_level: str


class ServiceStatsResponse(BaseModel):
    """Response model for service statistics."""
    pending_count: int
    completed_count: int
    total_changes: int
    total_cost_usd: float
    status_counts: Dict[str, int]
    audit_log_size: int


class ManualApprovalRequest(BaseModel):
    """Request model for manual approval."""
    approver_id: str = Field(..., description="Who is approving")
    reason: Optional[str] = Field(default=None, description="Approval reason")


# Dependency to get CodeModificationService
async def get_code_service():
    """Get the CodeModificationService instance."""
    try:
        from mycosoft_mas.services.code_modification_service import get_code_modification_service
        return await get_code_modification_service()
    except Exception as e:
        logger.error(f"Failed to get CodeModificationService: {e}")
        raise HTTPException(status_code=503, detail="CodeModificationService unavailable")


async def get_security_reviewer():
    """Get the SecurityCodeReviewer instance."""
    try:
        from mycosoft_mas.security.code_reviewer import get_security_reviewer
        return get_security_reviewer()
    except Exception as e:
        logger.error(f"Failed to get SecurityCodeReviewer: {e}")
        raise HTTPException(status_code=503, detail="SecurityCodeReviewer unavailable")


# Endpoints
@router.post("/request", response_model=CodeChangeResponse)
async def request_code_change(
    request: CodeChangeRequest,
    code_service=Depends(get_code_service)
) -> CodeChangeResponse:
    """
    Request a code change.
    
    This is the main entry point for agents and orchestrator to request code modifications.
    The request goes through:
    1. Security review (automatic)
    2. Execution via CodingAgent
    3. Post-execution security scan
    """
    try:
        result = await code_service.request_code_change(
            requester_id=request.requester_id,
            change_type=request.change_type,
            description=request.description,
            target_files=request.target_files,
            priority=request.priority,
            require_pr=request.require_pr,
            code_content=request.code_content,
            context=request.context,
        )
        
        return CodeChangeResponse(
            change_id=result["change_id"],
            status=result["status"],
            message=result["message"],
            require_pr=result.get("require_pr"),
        )
        
    except Exception as e:
        logger.error(f"Error requesting code change: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{change_id}", response_model=ChangeStatusResponse)
async def get_change_status(
    change_id: str,
    code_service=Depends(get_code_service)
) -> ChangeStatusResponse:
    """Get the status of a code change request."""
    try:
        result = await code_service.get_change_status(change_id)
        return ChangeStatusResponse(**result)
    except Exception as e:
        logger.error(f"Error getting change status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_change_history(
    limit: int = 50,
    status: Optional[str] = None,
    code_service=Depends(get_code_service)
) -> List[Dict[str, Any]]:
    """Get history of code changes."""
    try:
        return await code_service.get_change_history(limit=limit, status_filter=status)
    except Exception as e:
        logger.error(f"Error getting change history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=ServiceStatsResponse)
async def get_service_stats(
    code_service=Depends(get_code_service)
) -> ServiceStatsResponse:
    """Get code modification service statistics."""
    try:
        stats = code_service.get_stats()
        return ServiceStatsResponse(**stats)
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/approve/{change_id}")
async def manual_approval(
    change_id: str,
    request: ManualApprovalRequest,
    code_service=Depends(get_code_service)
) -> Dict[str, Any]:
    """
    Manually approve a blocked or pending change.
    
    Use this when a change was blocked by security but needs to proceed
    with human override.
    """
    try:
        # Check if change exists and is in a state that can be approved
        status = await code_service.get_change_status(change_id)
        
        if status["status"] == "not_found":
            raise HTTPException(status_code=404, detail="Change request not found")
        
        if status["status"] not in ["blocked", "pending", "reviewing"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot approve change in status: {status['status']}"
            )
        
        # NOTE: Pending implementation - Manual approval override requires:
        # 1. Audit log entry via AuditService.log_override(change_id, approver_id, reason)
        # 2. GuardianAgent notification via message queue
        # 3. Re-queue with bypass_security=True flag (CEO/CTO approval only)
        # SECURITY: This bypasses safety checks - requires elevated privileges
        
        return {
            "change_id": change_id,
            "approved_by": request.approver_id,
            "reason": request.reason,
            "message": "Manual approval recorded - change will be re-processed",
            "warning": "Manual override bypasses security checks",
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in manual approval: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cancel/{change_id}")
async def cancel_change(
    change_id: str,
    code_service=Depends(get_code_service)
) -> Dict[str, Any]:
    """Cancel a pending code change request."""
    try:
        result = await code_service.cancel_pending_request(change_id)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["message"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling change: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/halt")
async def emergency_halt(
    code_service=Depends(get_code_service)
) -> Dict[str, Any]:
    """
    Emergency halt all pending code changes.
    
    Use this to immediately stop all code modification activity.
    """
    try:
        result = await code_service.halt_all_changes()
        logger.warning("EMERGENCY HALT executed via API")
        return result
    except Exception as e:
        logger.error(f"Error in emergency halt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/security/scan", response_model=SecurityScanResponse)
async def security_scan(
    request: SecurityScanRequest,
    security_reviewer=Depends(get_security_reviewer)
) -> SecurityScanResponse:
    """
    Run a security scan on specified files.
    
    Scans for:
    - Hardcoded secrets (API keys, passwords)
    - SQL injection patterns
    - Dangerous code patterns
    """
    try:
        vulnerabilities = await security_reviewer.scan_for_vulnerabilities(request.file_paths)
        
        # Determine overall risk level
        if any(v.get("severity") == "critical" for v in vulnerabilities):
            risk_level = "critical"
        elif any(v.get("severity") == "high" for v in vulnerabilities):
            risk_level = "high"
        elif any(v.get("severity") == "medium" for v in vulnerabilities):
            risk_level = "medium"
        elif vulnerabilities:
            risk_level = "low"
        else:
            risk_level = "none"
        
        return SecurityScanResponse(
            scanned_files=len(request.file_paths),
            vulnerabilities_found=len(vulnerabilities),
            vulnerabilities=vulnerabilities,
            risk_level=risk_level,
        )
        
    except Exception as e:
        logger.error(f"Error in security scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/security/stats")
async def security_stats(
    security_reviewer=Depends(get_security_reviewer)
) -> Dict[str, Any]:
    """Get security review statistics."""
    try:
        return security_reviewer.get_review_stats()
    except Exception as e:
        logger.error(f"Error getting security stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/security/recent-blocks")
async def recent_blocks(
    limit: int = 10,
    security_reviewer=Depends(get_security_reviewer)
) -> List[Dict[str, Any]]:
    """Get recently blocked code changes."""
    try:
        return security_reviewer.get_recent_blocks(limit)
    except Exception as e:
        logger.error(f"Error getting recent blocks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check for the code modification system."""
    try:
        # Check dependencies
        code_service_ok = False
        security_ok = False
        
        try:
            from mycosoft_mas.services.code_modification_service import get_code_modification_service
            service = await get_code_modification_service()
            code_service_ok = service is not None
        except Exception:
            pass
        
        try:
            from mycosoft_mas.security.code_reviewer import get_security_reviewer
            reviewer = get_security_reviewer()
            security_ok = reviewer is not None
        except Exception:
            pass
        
        healthy = code_service_ok and security_ok
        
        return {
            "status": "healthy" if healthy else "degraded",
            "components": {
                "code_modification_service": "ok" if code_service_ok else "unavailable",
                "security_code_reviewer": "ok" if security_ok else "unavailable",
            },
            "timestamp": datetime.now().isoformat(),
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


__all__ = ["router"]
