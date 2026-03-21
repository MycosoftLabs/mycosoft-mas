"""
CFO MCP API — REST endpoints for the Meridian adapter.

Exposes the CFO MCP server over HTTP so the Perplexity desktop adapter on the CFO VM
can discover and call finance tools without MCP protocol dependency.

Endpoints:
- GET /api/cfo-mcp/tools — List available MCP tools
- POST /api/cfo-mcp/tools/call — Call a tool by name with arguments

Created: March 8, 2026
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mycosoft_mas.mcp.cfo_mcp_server import get_cfo_mcp_server

logger = logging.getLogger("CFO_MCP_API")

router = APIRouter(prefix="/api/cfo-mcp", tags=["cfo-mcp"])


class ToolCallRequest(BaseModel):
    """Request to call a CFO MCP tool."""

    name: str = Field(..., description="Tool name (e.g., list_finance_agents)")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")


@router.get("/tools", summary="List CFO MCP tools")
async def list_tools() -> Dict[str, Any]:
    """Return available CFO MCP tools for the Meridian adapter."""
    server = get_cfo_mcp_server()
    tools = server.get_tools()
    return {"success": True, "count": len(tools), "tools": tools}


@router.post("/tools/call", summary="Call a CFO MCP tool")
async def call_tool(req: ToolCallRequest) -> Dict[str, Any]:
    """Execute a CFO MCP tool and return the result."""
    server = get_cfo_mcp_server()
    try:
        result = await server.call_tool(req.name, req.arguments or {})
        if "error" in result and result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("CFO MCP tool %s failed", req.name)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/health", summary="CFO MCP health check")
async def health() -> Dict[str, str]:
    """Health check for the CFO MCP API."""
    return {"status": "ok", "service": "cfo-mcp"}
