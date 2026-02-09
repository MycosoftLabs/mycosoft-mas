"""
MYCA Tool Integration Pipeline

Enables mid-conversation tool calls during MYCA brain responses.
Tools can be executed and results injected back into the response.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
import json
import httpx

logger = logging.getLogger(__name__)


class ToolStatus(Enum):
    """Status of a tool execution."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ToolCall:
    """Represents a tool call during conversation."""
    id: str
    name: str
    arguments: Dict[str, Any]
    status: ToolStatus = ToolStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    latency_ms: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "arguments": self.arguments,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "latency_ms": self.latency_ms
        }


@dataclass
class ToolDefinition:
    """Definition of an available tool."""
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    handler: Optional[Callable] = None
    requires_confirmation: bool = False
    max_timeout_seconds: int = 30
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "requires_confirmation": self.requires_confirmation
        }


class ToolRegistry:
    """Registry of available tools for MYCA."""
    
    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}
        self._init_default_tools()
    
    def _init_default_tools(self):
        """Register default MYCA tools."""
        
        # Device Status Tool
        self.register(ToolDefinition(
            name="device_status",
            description="Get current status and readings from a NatureOS device",
            parameters={
                "type": "object",
                "properties": {
                    "device_id": {
                        "type": "string",
                        "description": "Device identifier (e.g., mushroom1, sporebase)"
                    }
                },
                "required": ["device_id"]
            }
        ))
        
        # MINDEX Query Tool
        self.register(ToolDefinition(
            name="mindex_query",
            description="Search the MINDEX fungal knowledge database",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for fungal/mycology knowledge"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        ))
        
        # Memory Recall Tool
        self.register(ToolDefinition(
            name="memory_recall",
            description="Recall information from MYCA's memory system",
            parameters={
                "type": "object",
                "properties": {
                    "scope": {
                        "type": "string",
                        "enum": ["conversation", "user", "agent", "system", "ephemeral", "device", "experiment", "workflow"],
                        "description": "Memory scope to search"
                    },
                    "query": {
                        "type": "string",
                        "description": "What to recall"
                    }
                },
                "required": ["scope", "query"]
            }
        ))
        
        # Execute Workflow Tool
        self.register(ToolDefinition(
            name="execute_workflow",
            description="Execute an n8n automation workflow",
            parameters={
                "type": "object",
                "properties": {
                    "workflow_name": {
                        "type": "string",
                        "description": "Name of the workflow to execute"
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Parameters to pass to the workflow"
                    }
                },
                "required": ["workflow_name"]
            },
            requires_confirmation=True
        ))
        
        # Agent Invoke Tool
        self.register(ToolDefinition(
            name="agent_invoke",
            description="Invoke a specialized agent for a specific task",
            parameters={
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "Name of the agent to invoke"
                    },
                    "task": {
                        "type": "string",
                        "description": "Task for the agent to perform"
                    }
                },
                "required": ["agent_name", "task"]
            }
        ))
        
        # Code Execute Tool
        self.register(ToolDefinition(
            name="code_execute",
            description="Execute code in a sandboxed environment",
            parameters={
                "type": "object",
                "properties": {
                    "language": {
                        "type": "string",
                        "enum": ["python", "javascript"],
                        "description": "Programming language"
                    },
                    "code": {
                        "type": "string",
                        "description": "Code to execute"
                    }
                },
                "required": ["language", "code"]
            },
            requires_confirmation=True
        ))
        
        # Search Documents Tool
        self.register(ToolDefinition(
            name="search_documents",
            description="Search Mycosoft documentation and files",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "file_type": {
                        "type": "string",
                        "description": "Filter by file type (md, pdf, etc.)"
                    }
                },
                "required": ["query"]
            }
        ))
        
        # Weather Tool (example external API)
        self.register(ToolDefinition(
            name="weather",
            description="Get current weather for a location",
            parameters={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City or location name"
                    }
                },
                "required": ["location"]
            }
        ))
        
        # Calculator Tool
        self.register(ToolDefinition(
            name="calculator",
            description="Perform mathematical calculations",
            parameters={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate"
                    }
                },
                "required": ["expression"]
            }
        ))
    
    def register(self, tool: ToolDefinition):
        """Register a tool."""
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
    
    def get(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool by name."""
        return self.tools.get(name)
    
    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self.tools.keys())
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get all tool definitions for LLM."""
        return [tool.to_dict() for tool in self.tools.values()]


class ToolExecutor:
    """Executes tools and manages results."""
    
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self.mas_url = "http://192.168.0.188:8001"
        self.execution_history: List[ToolCall] = []
    
    async def execute(self, tool_call: ToolCall) -> ToolCall:
        """Execute a tool call and return results."""
        tool_def = self.registry.get(tool_call.name)
        
        if not tool_def:
            tool_call.status = ToolStatus.FAILED
            tool_call.error = f"Unknown tool: {tool_call.name}"
            return tool_call
        
        tool_call.status = ToolStatus.EXECUTING
        tool_call.started_at = datetime.now()
        
        try:
            # Execute based on tool type
            if tool_call.name == "calculator":
                result = await self._execute_calculator(tool_call.arguments)
            elif tool_call.name == "device_status":
                result = await self._execute_device_status(tool_call.arguments)
            elif tool_call.name == "mindex_query":
                result = await self._execute_mindex_query(tool_call.arguments)
            elif tool_call.name == "memory_recall":
                result = await self._execute_memory_recall(tool_call.arguments)
            else:
                # Call MAS API for other tools
                result = await self._call_mas_tool(tool_call.name, tool_call.arguments)
            
            tool_call.result = result
            tool_call.status = ToolStatus.COMPLETED
            
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            tool_call.status = ToolStatus.FAILED
            tool_call.error = str(e)
        
        tool_call.completed_at = datetime.now()
        if tool_call.started_at:
            tool_call.latency_ms = int(
                (tool_call.completed_at - tool_call.started_at).total_seconds() * 1000
            )
        
        self.execution_history.append(tool_call)
        return tool_call
    
    async def _execute_calculator(self, args: Dict[str, Any]) -> Any:
        """Execute calculator tool locally."""
        expression = args.get("expression", "")
        
        # Safe evaluation of math expressions
        import ast
        import operator
        
        operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
            ast.Mod: operator.mod
        }
        
        def eval_expr(node):
            if isinstance(node, ast.Num):
                return node.n
            elif isinstance(node, ast.BinOp):
                return operators[type(node.op)](eval_expr(node.left), eval_expr(node.right))
            elif isinstance(node, ast.UnaryOp):
                return operators[type(node.op)](eval_expr(node.operand))
            else:
                raise ValueError(f"Unsupported expression: {expression}")
        
        try:
            tree = ast.parse(expression, mode="eval")
            result = eval_expr(tree.body)
            return {"result": result, "expression": expression}
        except Exception as e:
            raise ValueError(f"Invalid expression: {e}")
    
    async def _execute_device_status(self, args: Dict[str, Any]) -> Any:
        """Get device status from MAS."""
        device_id = args.get("device_id", "")
        
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{self.mas_url}/platform/devices/{device_id}/status"
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Device not found: {device_id}"}
    
    async def _execute_mindex_query(self, args: Dict[str, Any]) -> Any:
        """Query MINDEX knowledge base."""
        query = args.get("query", "")
        limit = args.get("limit", 5)
        
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{self.mas_url}/mindex/search",
                json={"query": query, "limit": limit}
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {"results": [], "message": "No results found"}
    
    async def _execute_memory_recall(self, args: Dict[str, Any]) -> Any:
        """Recall from memory system."""
        scope = args.get("scope", "conversation")
        query = args.get("query", "")
        
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{self.mas_url}/memory/recall",
                json={"scope": scope, "query": query}
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {"memories": [], "message": "Nothing recalled"}
    
    async def _call_mas_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """Call a generic MAS tool endpoint."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.mas_url}/tools/{tool_name}",
                json=args
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Tool execution failed: {response.status_code}"}


class ConversationToolManager:
    """
    Manages tool calls within a conversation context.
    Handles detecting when tools are needed and injecting results.
    """
    
    def __init__(self):
        self.registry = ToolRegistry()
        self.executor = ToolExecutor(self.registry)
        self.pending_calls: List[ToolCall] = []
    
    def get_tool_definitions_for_llm(self) -> List[Dict[str, Any]]:
        """Get tool definitions in a format suitable for LLM function calling."""
        return self.registry.get_tool_definitions()
    
    async def process_tool_calls(
        self, 
        tool_calls: List[Dict[str, Any]]
    ) -> List[ToolCall]:
        """Process multiple tool calls and return results."""
        results = []
        
        for call_data in tool_calls:
            call = ToolCall(
                id=call_data.get("id", ""),
                name=call_data.get("name", ""),
                arguments=call_data.get("arguments", {})
            )
            
            result = await self.executor.execute(call)
            results.append(result)
        
        return results
    
    def format_tool_result_for_injection(self, tool_call: ToolCall) -> str:
        """Format a tool result for injection into the response."""
        if tool_call.status == ToolStatus.COMPLETED:
            result_str = json.dumps(tool_call.result) if isinstance(tool_call.result, dict) else str(tool_call.result)
            return f"[TOOL] {tool_call.name}: {result_str}"
        else:
            return f"[TOOL] {tool_call.name}: Error - {tool_call.error}"


# Singleton instances
_tool_registry: Optional[ToolRegistry] = None
_tool_manager: Optional[ConversationToolManager] = None


def get_tool_registry() -> ToolRegistry:
    """Get or create the tool registry singleton."""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry


def get_tool_manager() -> ConversationToolManager:
    """Get or create the tool manager singleton."""
    global _tool_manager
    if _tool_manager is None:
        _tool_manager = ConversationToolManager()
    return _tool_manager
