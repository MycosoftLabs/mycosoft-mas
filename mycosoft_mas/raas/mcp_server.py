"""RaaS MCP Server — Model Context Protocol server for external agent integration.

Allows external agents using Claude, Cursor, or any MCP-compatible tool
to discover and consume MYCA's RaaS services programmatically.

Usage:
    python -m mycosoft_mas.raas.mcp_server

Created: March 11, 2026
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger("RaaSMCP")


@dataclass
class MCPToolDefinition:
    """MCP tool definition."""

    name: str
    description: str
    parameters: Dict[str, Any]


class RaaSMCPServer:
    """MCP Server for RaaS — external agents consume MYCA services.

    Tools:
    - raas_catalog: List available services and pricing
    - raas_register: Register as a new agent customer
    - raas_balance: Check credit balance
    - raas_purchase_credits: View credit packages
    - raas_invoke_nlm: NLM inference
    - raas_invoke_crep: CREP data query
    - raas_invoke_earth2: Earth2 forecast
    - raas_invoke_data: MINDEX data query
    """

    def __init__(self, raas_url: Optional[str] = None):
        self._raas_url = raas_url or os.getenv(
            "RAAS_API_URL", "http://192.168.0.188:8001"
        )
        self._api_key = os.getenv("RAAS_API_KEY", "")
        self._tools = self._define_tools()

    def _define_tools(self) -> List[MCPToolDefinition]:
        return [
            MCPToolDefinition(
                name="raas_catalog",
                description="List all available MYCA RaaS services with pricing and descriptions",
                parameters={"type": "object", "properties": {}, "required": []},
            ),
            MCPToolDefinition(
                name="raas_register",
                description="Register a new agent as a MYCA RaaS customer ($1 signup fee)",
                parameters={
                    "type": "object",
                    "properties": {
                        "agent_name": {
                            "type": "string",
                            "description": "Name of the agent being registered",
                        },
                        "contact_email": {
                            "type": "string",
                            "description": "Contact email for the agent owner",
                        },
                        "payment_method": {
                            "type": "string",
                            "enum": ["stripe", "crypto"],
                            "description": "Payment method (stripe for credit/debit, crypto for cryptocurrency)",
                        },
                    },
                    "required": ["agent_name"],
                },
            ),
            MCPToolDefinition(
                name="raas_balance",
                description="Check current credit balance for the authenticated agent",
                parameters={"type": "object", "properties": {}, "required": []},
            ),
            MCPToolDefinition(
                name="raas_packages",
                description="List available credit packages with pricing",
                parameters={"type": "object", "properties": {}, "required": []},
            ),
            MCPToolDefinition(
                name="raas_invoke_nlm",
                description=(
                    "Invoke MYCA's Nature Learning Model for species identification, "
                    "taxonomy, ecology, cultivation, research, or genetics queries"
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The natural language query",
                        },
                        "query_type": {
                            "type": "string",
                            "enum": [
                                "general",
                                "species_id",
                                "taxonomy",
                                "ecology",
                                "cultivation",
                                "research",
                                "genetics",
                            ],
                            "description": "Type of NLM query",
                        },
                    },
                    "required": ["query"],
                },
            ),
            MCPToolDefinition(
                name="raas_invoke_crep",
                description="Query CREP real-time data (aviation, maritime, satellite, weather)",
                parameters={
                    "type": "object",
                    "properties": {
                        "data_type": {
                            "type": "string",
                            "enum": ["aviation", "maritime", "satellite", "weather"],
                            "description": "Type of CREP data to query",
                        },
                    },
                    "required": ["data_type"],
                },
            ),
            MCPToolDefinition(
                name="raas_invoke_earth2",
                description="Run Earth2 climate simulation (forecast, nowcast, spore dispersal)",
                parameters={
                    "type": "object",
                    "properties": {
                        "forecast_type": {
                            "type": "string",
                            "enum": [
                                "medium_range",
                                "short_range",
                                "spore_dispersal",
                                "ensemble",
                            ],
                            "description": "Type of Earth2 forecast",
                        },
                        "latitude": {"type": "number", "description": "Latitude"},
                        "longitude": {"type": "number", "description": "Longitude"},
                    },
                    "required": ["forecast_type"],
                },
            ),
            MCPToolDefinition(
                name="raas_invoke_data",
                description="Query MINDEX data (species, taxonomy, compounds, knowledge graph)",
                parameters={
                    "type": "object",
                    "properties": {
                        "query_type": {
                            "type": "string",
                            "enum": [
                                "species",
                                "taxonomy",
                                "compound",
                                "knowledge_graph",
                            ],
                            "description": "Type of data query",
                        },
                        "query": {
                            "type": "string",
                            "description": "Search query",
                        },
                    },
                    "required": ["query"],
                },
            ),
        ]

    async def _call_api(
        self,
        method: str,
        path: str,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Call the RaaS API."""
        if httpx is None:
            return {"error": "httpx not installed"}
        url = f"{self._raas_url}{path}"
        headers = {}
        if self._api_key:
            headers["X-API-Key"] = self._api_key
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                if method == "GET":
                    resp = await client.get(url, headers=headers)
                else:
                    resp = await client.post(url, json=json_body or {}, headers=headers)
                return resp.json()
        except Exception as e:
            return {"error": str(e)}

    async def handle_tool_call(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Route a tool call to the appropriate handler."""
        handlers = {
            "raas_catalog": self._handle_catalog,
            "raas_register": self._handle_register,
            "raas_balance": self._handle_balance,
            "raas_packages": self._handle_packages,
            "raas_invoke_nlm": self._handle_nlm,
            "raas_invoke_crep": self._handle_crep,
            "raas_invoke_earth2": self._handle_earth2,
            "raas_invoke_data": self._handle_data,
        }
        handler = handlers.get(tool_name)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}"}
        return await handler(arguments)

    async def _handle_catalog(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return await self._call_api("GET", "/api/raas/services")

    async def _handle_register(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return await self._call_api(
            "POST",
            "/api/raas/agents/register",
            {
                "agent_name": args.get("agent_name", "MCP Agent"),
                "contact_email": args.get("contact_email"),
                "payment_method": args.get("payment_method", "stripe"),
            },
        )

    async def _handle_balance(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return await self._call_api("GET", "/api/raas/agents/me")

    async def _handle_packages(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return await self._call_api("GET", "/api/raas/payments/packages")

    async def _handle_nlm(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return await self._call_api(
            "POST",
            "/api/raas/invoke/nlm",
            {
                "query": args.get("query", ""),
                "query_type": args.get("query_type", "general"),
            },
        )

    async def _handle_crep(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return await self._call_api(
            "POST",
            "/api/raas/invoke/crep",
            {"data_type": args.get("data_type", "weather")},
        )

    async def _handle_earth2(self, args: Dict[str, Any]) -> Dict[str, Any]:
        location = {}
        if args.get("latitude") is not None and args.get("longitude") is not None:
            location = {"lat": args["latitude"], "lon": args["longitude"]}
        return await self._call_api(
            "POST",
            "/api/raas/invoke/earth2",
            {
                "forecast_type": args.get("forecast_type", "medium_range"),
                "location": location or None,
            },
        )

    async def _handle_data(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return await self._call_api(
            "POST",
            "/api/raas/invoke/data",
            {
                "query_type": args.get("query_type", "species"),
                "query": args.get("query", ""),
            },
        )

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Return tool definitions in MCP schema format."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "inputSchema": t.parameters,
            }
            for t in self._tools
        ]

    async def run_stdio(self) -> None:
        """Run as a stdio MCP server (JSON-RPC over stdin/stdout)."""
        logger.info("RaaS MCP Server starting (stdio mode)")
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

        while True:
            try:
                line = await reader.readline()
                if not line:
                    break
                request = json.loads(line.decode())
                method = request.get("method", "")
                req_id = request.get("id")

                if method == "initialize":
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {"tools": {}},
                            "serverInfo": {
                                "name": "myca-raas",
                                "version": "1.0.0",
                            },
                        },
                    }
                elif method == "tools/list":
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {"tools": self.get_tool_definitions()},
                    }
                elif method == "tools/call":
                    params = request.get("params", {})
                    tool_name = params.get("name", "")
                    arguments = params.get("arguments", {})
                    result = await self.handle_tool_call(tool_name, arguments)
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [
                                {"type": "text", "text": json.dumps(result, indent=2)}
                            ]
                        },
                    }
                else:
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {method}",
                        },
                    }

                output = json.dumps(response) + "\n"
                sys.stdout.write(output)
                sys.stdout.flush()

            except json.JSONDecodeError:
                continue
            except Exception as e:
                logger.error("MCP error: %s", e)
                continue


def main() -> None:
    """Entry point for the RaaS MCP server."""
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    server = RaaSMCPServer()
    asyncio.run(server.run_stdio())


if __name__ == "__main__":
    main()
