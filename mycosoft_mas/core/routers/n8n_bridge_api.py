"""
N8N Bridge API - March 2, 2026

MAS endpoints for n8n workflows to access memory, sandbox, and MINDEX.
Used by MYCA autonomous omnichannel orchestrator (Phase 5).
"""

import json
import logging
import os
import re
import time
import uuid
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from mycosoft_mas.security.safety_gates import SafetyGates

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/n8n", tags=["n8n-bridge"])

# Singleton for safety gates (used by n8n workflows)
_safety_gates: Optional[SafetyGates] = None


def _get_safety_gates() -> SafetyGates:
    global _safety_gates
    if _safety_gates is None:
        _safety_gates = SafetyGates()
    return _safety_gates

MAS_URL = os.getenv("MAS_URL", "http://192.168.0.188:8001")
MINDEX_URL = os.getenv("MINDEX_URL", "http://192.168.0.189:8000")


# =============================================================================
# Memory Models
# =============================================================================


class MemoryQueryRequest(BaseModel):
    """Request to query user/conversation memory for n8n context."""
    user_id: str = Field(..., description="User ID or sender email")
    agent_id: str = Field("myca_orchestrator", description="Agent namespace")
    query: Optional[str] = Field(None, description="Semantic search query")
    limit: int = Field(10, ge=1, le=100, description="Max results")


class MemoryStoreRequest(BaseModel):
    """Request to store task result or user preference."""
    agent_id: str = Field("myca_orchestrator", description="Agent namespace")
    content: Dict[str, Any] = Field(..., description="Content to remember")
    layer: str = Field("working", description="Memory layer")
    importance: float = Field(0.5, ge=0.0, le=1.0)
    tags: Optional[list[str]] = None


# =============================================================================
# Sandbox Models
# =============================================================================


class SandboxExecuteRequest(BaseModel):
    """Request to execute code in sandbox via Gateway."""
    tool_name: str = Field("code_execute", description="Tool: code_execute, exec, browser")
    args: Dict[str, Any] = Field(..., description="Tool arguments")
    session_id: Optional[str] = Field(None, description="Session ID (auto-generated if omitted)")


# =============================================================================
# MINDEX Models
# =============================================================================


class MindexSearchRequest(BaseModel):
    """Request to search MINDEX."""
    q: str = Field(..., description="Search query")
    types: Optional[str] = Field(None, description="Comma-separated: taxa, compounds, observations, etc.")
    limit: int = Field(20, ge=1, le=100)


class EvaluateTaskCompletionRequest(BaseModel):
    """Request to evaluate if a sub-task result means the original goal is complete."""
    goal: str = Field(..., description="Original user goal")
    result: str = Field(..., description="Current sub-task result")
    iteration: int = Field(0, ge=0, le=10)
    max_iterations: int = Field(5, ge=1, le=10)
    session_start_time: Optional[float] = Field(None, description="Unix timestamp when session started (5-min timeout)")
    tokens_used: int = Field(0, ge=0, description="Cumulative tokens this session (50K budget)")
    iteration_history: Optional[list[Dict[str, Any]]] = Field(None, description="Last N iterations for duplicate detection")


# =============================================================================
# Safety Gate Models (Phase 6)
# =============================================================================


class SafetyCheckRequest(BaseModel):
    """Request to check if an action is safe (no confirmation needed) or requires confirmation."""
    action: str = Field(..., description="Action type: deploy, restart, delete, etc.")
    context: Dict[str, Any] = Field(default_factory=dict, description="Action context (resource names, targets)")


class SafetyRequestConfirmationRequest(BaseModel):
    """Request to create a confirmation request for destructive action."""
    action: str = Field(..., description="Action requiring confirmation")
    context: Dict[str, Any] = Field(default_factory=dict, description="Action context")
    approver_id: str = Field(..., description="Slack user ID or email of approver (leadership)")


class SafetySubmitConfirmationRequest(BaseModel):
    """Request to approve or deny a pending confirmation."""
    request_id: str = Field(..., description="Confirmation request ID")
    approved: bool = Field(..., description="True to approve, False to deny")


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/memory/query")
async def memory_query(request: MemoryQueryRequest) -> Dict[str, Any]:
    """
    Retrieve user/conversation memory for n8n orchestrator context.
    Proxies to MAS /api/memory/recall.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(
                f"{MAS_URL}/api/memory/recall",
                json={
                    "agent_id": request.agent_id or f"user_{request.user_id}",
                    "query": request.query or f"context for user {request.user_id}",
                    "limit": request.limit,
                },
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.warning("Memory recall failed: %s", e)
            return {
                "success": True,
                "agent_id": request.agent_id,
                "memories": [],
                "count": 0,
                "timestamp": None,
                "fallback": "memory_service_unavailable",
            }
        except Exception as e:
            logger.error("Memory query error: %s", e)
            raise HTTPException(status_code=503, detail=str(e))


@router.post("/memory/store")
async def memory_store(request: MemoryStoreRequest) -> Dict[str, Any]:
    """
    Persist task results or user preferences for n8n.
    Proxies to MAS /api/memory/remember.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(
                f"{MAS_URL}/api/memory/remember",
                json={
                    "agent_id": request.agent_id,
                    "content": request.content,
                    "layer": request.layer,
                    "importance": request.importance,
                    "tags": request.tags,
                },
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.warning("Memory remember failed: %s", e)
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except Exception as e:
            logger.error("Memory store error: %s", e)
            raise HTTPException(status_code=503, detail=str(e))


@router.post("/sandbox/execute")
async def sandbox_execute(req: SandboxExecuteRequest, request: Request) -> Dict[str, Any]:
    """
    Execute tool in sandbox via Gateway.
    Proxies to orchestrator's gateway control plane.
    """
    session_id = req.session_id or str(uuid.uuid4())
    gateway = getattr(request.app.state, "gateway", None)
    if not gateway:
        raise HTTPException(
            status_code=503,
            detail="Gateway control plane not available",
        )

    try:
        result = await gateway.intercept_tool_call(
            tool_name=req.tool_name,
            args=req.args,
            session_id=session_id,
        )
        return {
            "success": result.success,
            "output": result.output,
            "error": result.error,
            "sandbox_id": result.sandbox_id,
            "duration_ms": result.duration_ms,
            "session_id": session_id,
        }
    except Exception as e:
        logger.error("Sandbox execute error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mindex/search")
async def mindex_search(request: MindexSearchRequest) -> Dict[str, Any]:
    """
    Semantic search across MINDEX (company data, species, docs).
    Proxies to MINDEX API.
    """
    params: Dict[str, Any] = {"q": request.q, "limit": request.limit}
    if request.types:
        params["types"] = request.types

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # MINDEX canonical unified-search endpoint
            response = await client.get(
                f"{MINDEX_URL}/api/mindex/unified-search",
                params=params,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.warning("MINDEX search failed: %s", e)
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except Exception as e:
            logger.error("MINDEX search error: %s", e)
            raise HTTPException(status_code=503, detail=str(e))


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://192.168.0.188:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
SESSION_TIMEOUT_SECONDS = int(os.getenv("MYCA_SESSION_TIMEOUT", "300"))  # 5 minutes
TOKEN_BUDGET = int(os.getenv("MYCA_TOKEN_BUDGET", "50000"))


@router.post("/evaluate-task-completion")
async def evaluate_task_completion(req: EvaluateTaskCompletionRequest) -> Dict[str, Any]:
    """
    LLM evaluates if the original goal is achieved given the sub-task result.
    Returns {complete: bool, next_prompt?: str, reason?: str}.
    Used by n8n self-prompting loop. Includes Phase 6 loop mitigation:
    - 5-min timeout, token budget, duplicate detection, hallucination guard.
    Uses direct Ollama call (no voice orchestrator) to avoid recursion.
    """
    # Loop mitigation: timeout
    if req.session_start_time and (time.time() - req.session_start_time) > SESSION_TIMEOUT_SECONDS:
        return {"complete": True, "reason": "session_timeout_5min"}
    # Loop mitigation: token budget
    if req.tokens_used > TOKEN_BUDGET:
        return {"complete": True, "reason": "token_budget_exceeded"}
    # Loop mitigation: duplicate detection (same intent/prompt 3x consecutively)
    if req.iteration_history and len(req.iteration_history) >= 3:
        last_three = req.iteration_history[-3:]
        intents = [h.get("intent", "") for h in last_three]
        prompts = [str(h.get("message_text", h.get("prompt", "")))[:100] for h in last_three]
        if len(set(intents)) == 1 and len(set(prompts)) == 1:
            return {"complete": True, "reason": "duplicate_detection_break"}
    # Hallucination guard: if result looks like error or empty, acknowledge limitation
    result_lower = (req.result or "").strip().lower()
    error_patterns = ("error", "failed", "exception", "traceback", "not found", "unavailable")
    if not req.result or not result_lower:
        return {"complete": True, "reason": "empty_result_acknowledge_limitation"}
    if any(p in result_lower for p in error_patterns) and len(req.result) < 500:
        return {"complete": True, "reason": "sub_agent_error_acknowledge_limitation"}

    eval_prompt = f"""You are a task completion evaluator. Given:
- Original goal: {req.goal}
- Current sub-task result: {req.result}
- Iteration: {req.iteration}/{req.max_iterations}

Answer with ONLY valid JSON, no other text:
{{"complete": true or false, "next_prompt": "optional next sub-task if not complete", "reason": "brief explanation"}}

Rules: complete=true if the goal is fully achieved or iteration >= max_iterations. complete=false only if more work is clearly needed."""

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": eval_prompt}],
        "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            text = (data.get("message", {}).get("content") or "").strip()
    except (httpx.HTTPStatusError, Exception) as e:
        logger.warning("Evaluate-task-completion LLM call failed: %s", e)
        return {
            "complete": True,
            "reason": "evaluation_unavailable_default_complete",
        }

    # Parse JSON from response (LLM may wrap in markdown or add text)
    complete = True
    next_prompt: Optional[str] = None
    reason = "parse_failed_default_complete"

    json_match = re.search(r"\{[^{}]*\"complete\"[^{}]*\}", text, re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group())
            complete = bool(parsed.get("complete", True))
            next_prompt = parsed.get("next_prompt")
            reason = parsed.get("reason") or reason
        except json.JSONDecodeError:
            pass

    # Force complete if at max iterations (safety)
    if req.iteration >= req.max_iterations:
        complete = True
        reason = "max_iterations_reached"

    out: Dict[str, Any] = {"complete": complete, "reason": reason}
    if next_prompt:
        out["next_prompt"] = next_prompt
    return out


# =============================================================================
# Safety Gate Endpoints (Phase 6)
# =============================================================================


@router.post("/safety/check")
async def safety_check(req: SafetyCheckRequest) -> Dict[str, Any]:
    """
    Check if action is safe. Returns {safe, requires_confirmation, risk_level, reason}.
    n8n workflows call this before destructive actions (deploy, restart, delete).
    """
    gates = _get_safety_gates()
    result = await gates.check_safety(req.action, req.context)
    return {
        "safe": result.safe,
        "requires_confirmation": result.requires_confirmation,
        "risk_level": result.risk_level.value if hasattr(result.risk_level, "value") else str(result.risk_level),
        "reason": result.reason,
    }


@router.post("/safety/request-confirmation")
async def safety_request_confirmation(req: SafetyRequestConfirmationRequest) -> Dict[str, Any]:
    """
    Create a confirmation request for destructive action.
    Returns {request_id}. n8n should then send Slack DM to approver_id and poll /safety/pending or await.
    """
    gates = _get_safety_gates()
    request_id = await gates.request_confirmation(
        action=req.action,
        context=req.context,
        approver_id=req.approver_id,
    )
    return {"request_id": request_id}


@router.post("/safety/submit-confirmation")
async def safety_submit_confirmation(req: SafetySubmitConfirmationRequest) -> Dict[str, Any]:
    """
    Approve or deny a pending confirmation. Called by n8n when leadership responds.
    """
    gates = _get_safety_gates()
    ok = await gates.submit_confirmation(req.request_id, req.approved)
    return {"success": ok}


@router.get("/safety/pending")
async def safety_pending() -> Dict[str, Any]:
    """List pending confirmation requests for n8n workflow polling."""
    gates = _get_safety_gates()
    pending = gates.list_pending()  # sync method
    return {"pending": pending}


@router.get("/health")
async def bridge_health() -> Dict[str, Any]:
    """Health check for n8n bridge."""
    return {
        "status": "ok",
        "service": "n8n-bridge",
        "mas_url": MAS_URL,
        "mindex_url": MINDEX_URL,
    }
