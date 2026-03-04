"""
MAS Orchestrator MCP Server for Cursor Integration.
Created: February 12, 2026

Provides MCP tools for interacting with the MAS orchestrator:
- agent_list: List all agents and their status
- agent_invoke: Invoke an agent with a task
- agent_status: Get agent health/metrics
- system_health: Full system health check
- workflow_trigger: Trigger n8n workflows

Connects to: MAS VM API at http://192.168.0.188:8001
"""

import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger("OrchestratorMCP")


@dataclass
class MCPToolDefinition:
    """Definition of an MCP tool."""
    name: str
    description: str
    parameters: Dict[str, Any]


class OrchestratorMCPServer:
    """
    MCP Server for MAS Orchestrator integration.
    
    Tools:
    - agent_list: List all registered agents
    - agent_invoke: Invoke an agent with a task
    - agent_status: Get specific agent status
    - system_health: Full system health check
    - workflow_trigger: Trigger n8n workflows
    - service_status: Check service status on VMs
    """
    
    def __init__(self, mas_url: Optional[str] = None):
        self._mas_url = mas_url or os.getenv(
            "MAS_API_URL",
            "http://192.168.0.188:8001"
        )
        self._n8n_url = os.getenv(
            "N8N_URL",
            "http://192.168.0.188:5678"
        )
        self._mindex_url = os.getenv(
            "MINDEX_API_URL",
            "http://192.168.0.189:8000"
        )
        self._client: Optional["httpx.AsyncClient"] = None
        self._initialized = False
        
        self._tools = self._define_tools()
    
    def _define_tools(self) -> List[MCPToolDefinition]:
        """Define MCP tool specifications."""
        return [
            MCPToolDefinition(
                name="agent_list",
                description="List all registered MAS agents with their status and capabilities.",
                parameters={
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Filter by agent category",
                            "enum": ["corporate", "infrastructure", "scientific", "device", 
                                    "data", "integration", "financial", "security", 
                                    "mycology", "earth2", "simulation", "business", 
                                    "core", "custom", "all"]
                        },
                        "status": {
                            "type": "string",
                            "description": "Filter by agent status",
                            "enum": ["active", "idle", "error", "offline", "all"]
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of agents to return",
                            "default": 50
                        }
                    }
                }
            ),
            MCPToolDefinition(
                name="agent_invoke",
                description="Invoke a specific MAS agent with a task. The agent will process the task asynchronously.",
                parameters={
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "ID of the agent to invoke (e.g., 'coding_agent', 'research_agent')"
                        },
                        "task": {
                            "type": "object",
                            "description": "Task object with type and parameters",
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "description": "Type of task (depends on agent capabilities)"
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Human-readable task description"
                                },
                                "parameters": {
                                    "type": "object",
                                    "description": "Task-specific parameters"
                                },
                                "priority": {
                                    "type": "string",
                                    "enum": ["low", "medium", "high", "critical"]
                                }
                            },
                            "required": ["type", "description"]
                        },
                        "wait_for_result": {
                            "type": "boolean",
                            "description": "Wait for task completion (max 30s)",
                            "default": False
                        }
                    },
                    "required": ["agent_id", "task"]
                }
            ),
            MCPToolDefinition(
                name="agent_status",
                description="Get detailed status and metrics for a specific agent.",
                parameters={
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "ID of the agent to check"
                        },
                        "include_metrics": {
                            "type": "boolean",
                            "description": "Include performance metrics",
                            "default": True
                        },
                        "include_history": {
                            "type": "boolean",
                            "description": "Include recent task history",
                            "default": False
                        }
                    },
                    "required": ["agent_id"]
                }
            ),
            MCPToolDefinition(
                name="system_health",
                description="Get comprehensive health status of all MAS systems including VMs, services, and agents.",
                parameters={
                    "type": "object",
                    "properties": {
                        "check_vms": {
                            "type": "boolean",
                            "description": "Include VM connectivity checks",
                            "default": True
                        },
                        "check_services": {
                            "type": "boolean",
                            "description": "Include service health checks",
                            "default": True
                        },
                        "check_agents": {
                            "type": "boolean",
                            "description": "Include agent health checks",
                            "default": True
                        },
                        "verbose": {
                            "type": "boolean",
                            "description": "Include detailed information",
                            "default": False
                        }
                    }
                }
            ),
            MCPToolDefinition(
                name="workflow_trigger",
                description="Trigger an n8n workflow by name or ID.",
                parameters={
                    "type": "object",
                    "properties": {
                        "workflow_id": {
                            "type": "string",
                            "description": "ID of the workflow to trigger"
                        },
                        "workflow_name": {
                            "type": "string",
                            "description": "Name of the workflow to trigger (alternative to ID)"
                        },
                        "data": {
                            "type": "object",
                            "description": "Data to pass to the workflow"
                        }
                    }
                }
            ),
            MCPToolDefinition(
                name="service_status",
                description="Check status of a specific service on the MAS infrastructure.",
                parameters={
                    "type": "object",
                    "properties": {
                        "service": {
                            "type": "string",
                            "description": "Service to check",
                            "enum": ["orchestrator", "mindex", "website", "n8n", 
                                    "postgres", "redis", "qdrant", "ollama"]
                        }
                    },
                    "required": ["service"]
                }
            )
        ]
    
    async def initialize(self) -> None:
        """Initialize the server and HTTP client."""
        if self._initialized:
            return
        
        if httpx:
            self._client = httpx.AsyncClient(timeout=30.0)
        
        self._initialized = True
        logger.info(f"Orchestrator MCP initialized, MAS URL: {self._mas_url}")
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        if self._client:
            await self._client.aclose()
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get tool definitions in MCP format."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.parameters
            }
            for tool in self._tools
        ]
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call."""
        handlers = {
            "agent_list": self._handle_agent_list,
            "agent_invoke": self._handle_agent_invoke,
            "agent_status": self._handle_agent_status,
            "system_health": self._handle_system_health,
            "workflow_trigger": self._handle_workflow_trigger,
            "service_status": self._handle_service_status,
        }
        
        handler = handlers.get(name)
        if not handler:
            return {"error": f"Unknown tool: {name}"}
        
        try:
            return await handler(arguments)
        except Exception as e:
            logger.error(f"Tool {name} failed: {e}")
            return {"error": str(e)}
    
    async def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """Make an HTTP request to MAS or other services."""
        if not self._client:
            return {"error": "HTTP client not available (install httpx)"}
        
        try:
            if method == "GET":
                response = await self._client.get(url, **kwargs)
            elif method == "POST":
                response = await self._client.post(url, **kwargs)
            else:
                return {"error": f"Unsupported method: {method}"}
            
            if response.status_code >= 400:
                return {
                    "error": f"HTTP {response.status_code}",
                    "detail": response.text[:500]
                }
            
            return response.json()
        
        except httpx.ConnectError:
            return {"error": f"Connection failed to {url}"}
        except httpx.TimeoutException:
            return {"error": f"Request to {url} timed out"}
        except Exception as e:
            return {"error": str(e)}
    
    async def _handle_agent_list(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List all registered agents."""
        # Try to get from MAS registry API
        result = await self._make_request("GET", f"{self._mas_url}/api/registry/agents")
        
        if "error" in result:
            # Fall back to known agent list
            return {
                "success": True,
                "source": "static_registry",
                "agents": [
                    {"id": "orchestrator", "name": "Orchestrator", "category": "core", "status": "active"},
                    {"id": "coding_agent", "name": "CodingAgent", "category": "core", "status": "active"},
                    {"id": "research_agent", "name": "ResearchAgent", "category": "core", "status": "active"},
                    {"id": "debug_agent", "name": "DebugAgent", "category": "core", "status": "active"},
                    {"id": "dashboard_agent", "name": "DashboardAgent", "category": "infrastructure", "status": "active"},
                    {"id": "experiment_agent", "name": "ExperimentAgent", "category": "scientific", "status": "active"},
                ],
                "note": "Showing cached registry. MAS API unavailable."
            }
        
        # Filter by category if specified
        agents = result.get("agents", result)
        category = args.get("category", "all")
        if category != "all":
            agents = [a for a in agents if a.get("category") == category]
        
        # Filter by status if specified
        status = args.get("status", "all")
        if status != "all":
            agents = [a for a in agents if a.get("status") == status]
        
        # Apply limit
        limit = args.get("limit", 50)
        agents = agents[:limit]
        
        return {
            "success": True,
            "count": len(agents),
            "agents": agents
        }
    
    async def _handle_agent_invoke(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke an agent with a task."""
        agent_id = args["agent_id"]
        task = args["task"]
        wait = args.get("wait_for_result", False)
        
        # Submit task to orchestrator
        result = await self._make_request(
            "POST",
            f"{self._mas_url}/api/orchestrator/task",
            json={
                "agent_id": agent_id,
                "task": task,
                "wait_for_result": wait
            }
        )
        
        if "error" in result:
            return result
        
        return {
            "success": True,
            "task_id": result.get("task_id"),
            "agent_id": agent_id,
            "status": result.get("status", "submitted"),
            "result": result.get("result") if wait else None
        }
    
    async def _handle_agent_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get agent status and metrics."""
        agent_id = args["agent_id"]
        include_metrics = args.get("include_metrics", True)
        include_history = args.get("include_history", False)
        
        # Get agent status from MAS
        result = await self._make_request(
            "GET",
            f"{self._mas_url}/api/registry/agents/{agent_id}"
        )
        
        if "error" in result:
            return {
                "success": False,
                "agent_id": agent_id,
                "error": result["error"]
            }
        
        response = {
            "success": True,
            "agent_id": agent_id,
            "status": result.get("status", "unknown"),
            "name": result.get("name"),
            "capabilities": result.get("capabilities", [])
        }
        
        if include_metrics:
            # Get metrics if available
            metrics_result = await self._make_request(
                "GET",
                f"{self._mas_url}/api/registry/agents/{agent_id}/metrics"
            )
            if "error" not in metrics_result:
                response["metrics"] = metrics_result
        
        if include_history:
            # Get recent task history
            history_result = await self._make_request(
                "GET",
                f"{self._mas_url}/api/orchestrator/tasks?agent_id={agent_id}&limit=10"
            )
            if "error" not in history_result:
                response["recent_tasks"] = history_result.get("tasks", [])
        
        return response
    
    async def _handle_system_health(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get comprehensive system health."""
        check_vms = args.get("check_vms", True)
        check_services = args.get("check_services", True)
        check_agents = args.get("check_agents", True)
        verbose = args.get("verbose", False)
        
        health = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall": "healthy",
            "issues": []
        }
        
        # Check VMs
        if check_vms:
            health["vms"] = {}
            
            # MAS VM (188)
            mas_health = await self._make_request("GET", f"{self._mas_url}/health")
            health["vms"]["mas_188"] = {
                "status": "healthy" if "error" not in mas_health else "unhealthy",
                "url": self._mas_url
            }
            if "error" in mas_health:
                health["issues"].append(f"MAS VM (188): {mas_health['error']}")
            
            # MINDEX VM (189)
            mindex_health = await self._make_request("GET", f"{self._mindex_url}/health")
            health["vms"]["mindex_189"] = {
                "status": "healthy" if "error" not in mindex_health else "unhealthy",
                "url": self._mindex_url
            }
            if "error" in mindex_health:
                health["issues"].append(f"MINDEX VM (189): {mindex_health['error']}")
        
        # Check services
        if check_services:
            health["services"] = {}
            
            services_to_check = [
                ("orchestrator", f"{self._mas_url}/health"),
                ("n8n", f"{self._n8n_url}/healthz"),
            ]
            
            for service_name, url in services_to_check:
                result = await self._make_request("GET", url)
                health["services"][service_name] = {
                    "status": "healthy" if "error" not in result else "unhealthy"
                }
                if "error" in result:
                    health["issues"].append(f"{service_name}: {result['error']}")
        
        # Check agents
        if check_agents:
            agents_result = await self._make_request("GET", f"{self._mas_url}/api/registry/agents")
            if "error" not in agents_result:
                agents = agents_result.get("agents", agents_result)
                health["agents"] = {
                    "total": len(agents),
                    "active": len([a for a in agents if a.get("status") == "active"]),
                    "error": len([a for a in agents if a.get("status") == "error"])
                }
            else:
                health["agents"] = {"status": "unavailable", "error": agents_result["error"]}
                health["issues"].append(f"Agent registry: {agents_result['error']}")
        
        # Determine overall health
        if health["issues"]:
            health["overall"] = "degraded" if len(health["issues"]) < 3 else "unhealthy"
        
        return health
    
    async def _handle_workflow_trigger(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger an n8n workflow."""
        workflow_id = args.get("workflow_id")
        workflow_name = args.get("workflow_name")
        data = args.get("data", {})
        
        if not workflow_id and not workflow_name:
            return {"error": "Either workflow_id or workflow_name is required"}
        
        # Trigger via webhook or API
        if workflow_id:
            url = f"{self._n8n_url}/webhook/{workflow_id}"
        else:
            # Try to find workflow by name
            url = f"{self._n8n_url}/webhook/{workflow_name}"
        
        result = await self._make_request("POST", url, json=data)
        
        if "error" in result:
            return {
                "success": False,
                "error": result["error"],
                "workflow": workflow_id or workflow_name
            }
        
        return {
            "success": True,
            "workflow": workflow_id or workflow_name,
            "result": result
        }
    
    async def _handle_service_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Check status of a specific service."""
        service = args["service"]
        
        service_urls = {
            "orchestrator": f"{self._mas_url}/health",
            "mindex": f"{self._mindex_url}/health",
            "website": "http://192.168.0.187:3000/api/health",
            "n8n": f"{self._n8n_url}/healthz",
            "postgres": f"{self._mindex_url}/api/health/postgres",
            "redis": f"{self._mindex_url}/api/health/redis",
            "qdrant": f"{self._mindex_url}/api/health/qdrant",
            "ollama": "http://192.168.0.188:11434/api/tags",
        }
        
        url = service_urls.get(service)
        if not url:
            return {"error": f"Unknown service: {service}"}
        
        result = await self._make_request("GET", url)
        
        return {
            "service": service,
            "url": url,
            "status": "healthy" if "error" not in result else "unhealthy",
            "details": result if "error" not in result else {"error": result["error"]}
        }


class MCPProtocolHandler:
    """Handle MCP JSON-RPC protocol."""
    
    def __init__(self, server: OrchestratorMCPServer):
        self._server = server
    
    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an incoming MCP message."""
        method = message.get("method", "")
        msg_id = message.get("id")
        params = message.get("params", {})
        
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "mycosoft-orchestrator",
                        "version": "1.0.0"
                    },
                    "capabilities": {
                        "tools": {}
                    }
                }
            }
        
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": self._server.get_tools()
                }
            }
        
        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            result = await self._server.call_tool(tool_name, arguments)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {"type": "text", "text": json.dumps(result, indent=2)}
                    ]
                }
            }
        
        else:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }


# Singleton instance
_mcp_server: Optional[OrchestratorMCPServer] = None


async def get_mcp_server() -> OrchestratorMCPServer:
    """Get or create the singleton MCP server instance."""
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = OrchestratorMCPServer()
        await _mcp_server.initialize()
    return _mcp_server


async def run_stdio_server():
    """Run the MCP server over stdio."""
    server = await get_mcp_server()
    handler = MCPProtocolHandler(server)
    
    logger.info("Orchestrator MCP Server started on stdio")
    
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            
            message = json.loads(line)
            response = await handler.handle_message(message)
            
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
            
        except json.JSONDecodeError:
            continue
        except KeyboardInterrupt:
            break
    
    await server.cleanup()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_stdio_server())
