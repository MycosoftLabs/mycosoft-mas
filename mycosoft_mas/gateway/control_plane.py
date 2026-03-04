"""
Gateway Control Plane -- central tool routing for MYCA.

Routes every tool call to the correct execution environment:
  BUILTIN  -> in-process handler (calculator, device_status, mindex_query, ...)
  SANDBOX  -> ephemeral Docker container via Node WebSocket daemon
  WORKFLOW -> n8n workflow execution
  AGENT    -> MAS agent mesh
"""

import asyncio
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from mycosoft_mas.sandbox.container_manager import SandboxManager

logger = logging.getLogger(__name__)


class ToolRouteType(Enum):
    BUILTIN = "builtin"
    SANDBOX = "sandbox"
    WORKFLOW = "workflow"
    AGENT = "agent"


@dataclass
class ToolResult:
    success: bool
    output: Any = None
    error: Optional[str] = None
    truncated: bool = False
    sandbox_id: Optional[str] = None
    duration_ms: int = 0


@dataclass
class RegisteredTool:
    name: str
    handler: Optional[Callable] = None
    route_type: ToolRouteType = ToolRouteType.BUILTIN
    requires_sandbox: bool = False
    requires_confirmation: bool = False
    description: str = ""


BUILTIN_TOOLS = frozenset({
    "calculator", "device_status", "query_device_telemetry",
    "mindex_query", "memory_recall", "exa_search",
    "timeline_search", "memory_store", "graph_lookup",
})

SANDBOX_TOOLS = frozenset({
    "code_execute", "exec", "browser",
})

WORKFLOW_TOOLS = frozenset({
    "execute_workflow", "generate_workflow",
})

AGENT_TOOLS = frozenset({
    "agent_invoke",
})


class GatewayControlPlane:
    """Central control plane that intercepts and routes every tool call."""

    def __init__(
        self,
        tool_registry=None,
        session_manager=None,
        sandbox_manager: Optional["SandboxManager"] = None,
    ):
        self._tool_registry = tool_registry
        self._session_manager = session_manager
        self._sandbox_manager = sandbox_manager
        self._registered: Dict[str, RegisteredTool] = {}
        self._sandbox_connections: Dict[str, Any] = {}
        self._init_builtin_routes()

    def _init_builtin_routes(self):
        for name in BUILTIN_TOOLS:
            self._registered[name] = RegisteredTool(
                name=name, route_type=ToolRouteType.BUILTIN,
            )
        for name in SANDBOX_TOOLS:
            self._registered[name] = RegisteredTool(
                name=name, route_type=ToolRouteType.SANDBOX,
                requires_sandbox=True,
            )
        for name in WORKFLOW_TOOLS:
            self._registered[name] = RegisteredTool(
                name=name, route_type=ToolRouteType.WORKFLOW,
            )
        for name in AGENT_TOOLS:
            self._registered[name] = RegisteredTool(
                name=name, route_type=ToolRouteType.AGENT,
            )

    def register_tool(
        self,
        name: str,
        handler: Optional[Callable] = None,
        requires_sandbox: bool = False,
        route_type: Optional[ToolRouteType] = None,
        description: str = "",
        requires_confirmation: bool = False,
    ):
        if route_type is None:
            if requires_sandbox or name in SANDBOX_TOOLS:
                route_type = ToolRouteType.SANDBOX
            elif name in WORKFLOW_TOOLS:
                route_type = ToolRouteType.WORKFLOW
            elif name in AGENT_TOOLS:
                route_type = ToolRouteType.AGENT
            else:
                route_type = ToolRouteType.BUILTIN

        self._registered[name] = RegisteredTool(
            name=name,
            handler=handler,
            route_type=route_type,
            requires_sandbox=requires_sandbox,
            requires_confirmation=requires_confirmation,
            description=description,
        )
        logger.info("Registered tool '%s' -> %s", name, route_type.value)

    def get_route_type(self, tool_name: str) -> ToolRouteType:
        reg = self._registered.get(tool_name)
        if reg:
            return reg.route_type
        return ToolRouteType.BUILTIN

    async def intercept_tool_call(
        self,
        tool_name: str,
        args: Dict[str, Any],
        session_id: Optional[str] = None,
    ) -> ToolResult:
        start = time.monotonic()
        route = self.get_route_type(tool_name)
        logger.info("Gateway routing '%s' -> %s (session=%s)", tool_name, route.value, session_id)

        try:
            if route == ToolRouteType.BUILTIN:
                result = await self._execute_builtin(tool_name, args)
            elif route == ToolRouteType.SANDBOX:
                result = await self._execute_in_sandbox(tool_name, args, session_id)
            elif route == ToolRouteType.WORKFLOW:
                result = await self._execute_workflow(tool_name, args)
            elif route == ToolRouteType.AGENT:
                result = await self._execute_agent(tool_name, args)
            else:
                result = ToolResult(success=False, error=f"Unknown route: {route}")
        except Exception as exc:
            logger.exception("Tool execution failed: %s", tool_name)
            result = ToolResult(success=False, error=str(exc))

        result.duration_ms = int((time.monotonic() - start) * 1000)
        return result

    # ------------------------------------------------------------------
    # Route handlers
    # ------------------------------------------------------------------

    async def _execute_builtin(self, tool_name: str, args: Dict[str, Any]) -> ToolResult:
        reg = self._registered.get(tool_name)
        if reg and reg.handler:
            try:
                if asyncio.iscoroutinefunction(reg.handler):
                    out = await reg.handler(**args)
                else:
                    out = reg.handler(**args)
                return ToolResult(success=True, output=out)
            except Exception as exc:
                return ToolResult(success=False, error=str(exc))

        if self._tool_registry:
            tool_def = self._tool_registry.tools.get(tool_name)
            if tool_def and tool_def.handler:
                try:
                    if asyncio.iscoroutinefunction(tool_def.handler):
                        out = await tool_def.handler(**args)
                    else:
                        out = tool_def.handler(**args)
                    return ToolResult(success=True, output=out)
                except Exception as exc:
                    return ToolResult(success=False, error=str(exc))

        return ToolResult(success=False, error=f"No handler for builtin tool '{tool_name}'")

    async def _execute_in_sandbox(
        self, tool_name: str, args: Dict[str, Any], session_id: Optional[str] = None,
    ) -> ToolResult:
        if not self._sandbox_manager:
            return ToolResult(success=False, error="SandboxManager not available")

        sid = session_id or str(uuid.uuid4())
        try:
            sandbox = await self._sandbox_manager.get_or_spawn(sid)
        except Exception as exc:
            return ToolResult(success=False, error=f"Sandbox spawn failed: {exc}")

        ws = self._sandbox_connections.get(sandbox.sandbox_id)
        if not ws:
            return ToolResult(
                success=False,
                error="No WebSocket connection to sandbox",
                sandbox_id=sandbox.sandbox_id,
            )

        request_id = str(uuid.uuid4())
        msg = {"id": request_id, "type": tool_name, "payload": args}
        try:
            await ws.send_json(msg)
            response = await asyncio.wait_for(ws.receive_json(), timeout=60)
        except asyncio.TimeoutError:
            return ToolResult(
                success=False, error="Sandbox tool timed out",
                sandbox_id=sandbox.sandbox_id,
            )
        except Exception as exc:
            return ToolResult(
                success=False, error=f"Sandbox comms error: {exc}",
                sandbox_id=sandbox.sandbox_id,
            )

        output = response.get("payload", response)
        truncated = False
        if self._session_manager and isinstance(output, str) and len(output) > 5000:
            output = await self._session_manager.prune_context(output)
            truncated = True

        return ToolResult(
            success=response.get("type") != "error",
            output=output,
            truncated=truncated,
            sandbox_id=sandbox.sandbox_id,
        )

    async def _execute_workflow(self, tool_name: str, args: Dict[str, Any]) -> ToolResult:
        import httpx
        n8n_base = os.getenv("N8N_URL", "http://192.168.0.191:5679")
        n8n_url = f"{n8n_base}/api/v1/workflows"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{n8n_url}/execute",
                    json={"name": args.get("workflow_name", tool_name), "data": args},
                )
                resp.raise_for_status()
                return ToolResult(success=True, output=resp.json())
        except Exception as exc:
            return ToolResult(success=False, error=f"Workflow error: {exc}")

    async def _execute_agent(self, tool_name: str, args: Dict[str, Any]) -> ToolResult:
        import httpx
        mas_base = os.getenv("MAS_API_URL", "http://192.168.0.188:8001")
        mas_url = f"{mas_base}/api/agents/invoke"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(mas_url, json=args)
                resp.raise_for_status()
                return ToolResult(success=True, output=resp.json())
        except Exception as exc:
            return ToolResult(success=False, error=f"Agent invoke error: {exc}")

    # ------------------------------------------------------------------
    # Sandbox connection management (used by sandbox_ws router)
    # ------------------------------------------------------------------

    def register_sandbox_connection(self, sandbox_id: str, ws):
        self._sandbox_connections[sandbox_id] = ws
        logger.info("Sandbox %s connected via WebSocket", sandbox_id)

    def unregister_sandbox_connection(self, sandbox_id: str):
        self._sandbox_connections.pop(sandbox_id, None)
        logger.info("Sandbox %s disconnected", sandbox_id)

    def get_registered_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "route_type": t.route_type.value,
                "requires_sandbox": t.requires_sandbox,
                "requires_confirmation": t.requires_confirmation,
                "description": t.description,
            }
            for t in self._registered.values()
        ]