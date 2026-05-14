"""
MYCA Tools API Router

Provides endpoints for tool execution and management.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mycosoft_mas.avani.enforcement import AvaniActionDenied, require_avani_for_route
from mycosoft_mas.llm.tool_pipeline import ToolCall, ToolStatus, get_tool_manager, get_tool_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tools", tags=["MYCA Tools"])


class ToolExecutionRequest(BaseModel):
    """Request to execute a tool."""

    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    session_id: Optional[str] = None


class ToolExecutionResponse(BaseModel):
    """Response from tool execution."""

    id: str
    tool_name: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None
    latency_ms: Optional[int] = None


class BatchToolRequest(BaseModel):
    """Request to execute multiple tools."""

    tools: List[ToolExecutionRequest]
    parallel: bool = True


@router.get("/list")
async def list_tools():
    """List all available tools."""
    registry = get_tool_registry()

    return {
        "tools": registry.get_tool_definitions(),
        "count": len(registry.tools),
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/{tool_name}")
async def get_tool(tool_name: str):
    """Get details for a specific tool."""
    registry = get_tool_registry()
    tool = registry.get(tool_name)

    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")

    return tool.to_dict()


@router.post("/execute")
async def execute_tool(request: ToolExecutionRequest):
    """Execute a single tool."""
    try:
        avani = await require_avani_for_route(
            route="/tools/execute",
            source_agent="tools_api",
            action_type="tool_execution",
            description=f"Execute MYCA tool {request.tool_name}.",
            metadata={"tool_name": request.tool_name, "arguments": request.arguments},
        )
    except AvaniActionDenied as exc:
        raise HTTPException(status_code=403, detail=exc.decision) from exc
    manager = get_tool_manager()

    tool_call = ToolCall(id=str(uuid4()), name=request.tool_name, arguments=request.arguments)

    result = await manager.executor.execute(tool_call)
    if isinstance(result.result, dict):
        result.result.setdefault("avani", avani)

    return ToolExecutionResponse(
        id=result.id,
        tool_name=result.name,
        status=result.status.value,
        result=result.result,
        error=result.error,
        latency_ms=result.latency_ms,
    )


@router.post("/execute/batch")
async def execute_batch(request: BatchToolRequest):
    """Execute multiple tools (optionally in parallel)."""
    import asyncio

    manager = get_tool_manager()

    approved_calls = []
    preflight_results = []
    for t in request.tools:
        try:
            avani = await require_avani_for_route(
                route="/tools/execute/batch",
                source_agent="tools_api",
                action_type="tool_execution",
                description=f"Execute MYCA batch tool {t.tool_name}.",
                metadata={"tool_name": t.tool_name, "arguments": t.arguments},
            )
            tool_call = ToolCall(id=str(uuid4()), name=t.tool_name, arguments=t.arguments)
            approved_calls.append((tool_call, avani))
        except AvaniActionDenied as exc:
            preflight_results.append(
                {
                    "id": str(uuid4()),
                    "tool_name": t.tool_name,
                    "status": "failed",
                    "result": None,
                    "error": "AVANI preflight denied",
                    "latency_ms": None,
                    "avani": exc.decision,
                }
            )

    tool_calls = [tc for tc, _ in approved_calls]

    if request.parallel:
        # Execute in parallel
        results = await asyncio.gather(*[manager.executor.execute(tc) for tc in tool_calls])
    else:
        # Execute sequentially
        results = []
        for tc in tool_calls:
            result = await manager.executor.execute(tc)
            results.append(result)

    avani_by_id = {tc.id: avani for tc, avani in approved_calls}
    return {
        "results": preflight_results + [
            ToolExecutionResponse(
                id=r.id,
                tool_name=r.name,
                status=r.status.value,
                result=r.result,
                error=r.error,
                latency_ms=r.latency_ms,
            ).model_dump()
            | {"avani": avani_by_id.get(r.id)}
            for r in results
        ],
        "count": len(results),
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/history")
async def get_execution_history(limit: int = 50):
    """Get recent tool execution history."""
    manager = get_tool_manager()

    history = manager.executor.execution_history[-limit:]

    return {
        "history": [tc.to_dict() for tc in history],
        "count": len(history),
        "timestamp": datetime.now().isoformat(),
    }


@router.post("/calculator")
async def calculator(expression: str):
    """Quick calculator endpoint."""
    manager = get_tool_manager()

    tool_call = ToolCall(id=str(uuid4()), name="calculator", arguments={"expression": expression})

    result = await manager.executor.execute(tool_call)

    if result.status == ToolStatus.COMPLETED:
        return result.result
    else:
        raise HTTPException(status_code=400, detail=result.error)


@router.get("/device/{device_id}/status")
async def device_status(device_id: str):
    """Quick device status endpoint."""
    manager = get_tool_manager()

    tool_call = ToolCall(id=str(uuid4()), name="device_status", arguments={"device_id": device_id})

    result = await manager.executor.execute(tool_call)

    if result.status == ToolStatus.COMPLETED:
        return result.result
    else:
        raise HTTPException(status_code=400, detail=result.error or "Device not found")
