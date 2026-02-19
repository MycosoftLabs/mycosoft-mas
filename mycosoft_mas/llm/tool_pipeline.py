"""
MYCA Tool Integration Pipeline

Enables mid-conversation tool calls during MYCA brain responses.
Tools can be executed and results injected back into the response.

MYCA Integration (Feb 17, 2026):
- Added permission enforcement via SkillRegistry
- Added EventLedger logging for tool calls and denials
- Added risk-based execution controls
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


# ---------------------------------------------------------------------------
# MYCA Permission and Audit Integration
# ---------------------------------------------------------------------------

# Import skill registry for permission checks (lazy to avoid circular imports)
_skill_registry = None
_event_ledger = None


def _get_skill_registry():
    """Get the skill registry singleton (lazy import)."""
    global _skill_registry
    if _skill_registry is None:
        try:
            from mycosoft_mas.security.skill_registry import SkillRegistry
            _skill_registry = SkillRegistry()
        except ImportError as e:
            logger.warning("SkillRegistry not available: %s", e)
    return _skill_registry


def _get_event_ledger():
    """Get the event ledger singleton (lazy import)."""
    global _event_ledger
    if _event_ledger is None:
        try:
            from mycosoft_mas.myca.event_ledger import EventLedger
            _event_ledger = EventLedger()
        except ImportError as e:
            logger.debug("EventLedger not available: %s", e)
    return _event_ledger


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
    # MYCA permission context
    skill_name: Optional[str] = None
    permission_allowed: bool = True
    permission_reason: str = ""
    risk_flags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "arguments": self.arguments,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "latency_ms": self.latency_ms,
            "skill_name": self.skill_name,
            "permission_allowed": self.permission_allowed,
            "risk_flags": self.risk_flags,
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
        
        # Generate Workflow Tool
        self.register(ToolDefinition(
            name="generate_workflow",
            description="Create a new n8n workflow from a natural language description. Saves to repo and syncs to local and cloud n8n.",
            parameters={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Natural language description of what the workflow should do"
                    },
                    "name": {
                        "type": "string",
                        "description": "Optional workflow name (auto-generated if omitted)"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional tags for the workflow"
                    }
                },
                "required": ["description"]
            },
            requires_confirmation=True,
            max_timeout_seconds=60
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
    """
    Executes tools and manages results.
    
    MYCA Integration (Feb 17, 2026):
    - Enforces skill permissions before execution
    - Logs tool calls and denials to EventLedger
    - Checks sandbox requirements for high-risk skills
    """
    
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self.mas_url = "http://192.168.0.188:8001"
        self.execution_history: List[ToolCall] = []
        self._enable_permission_checks = True  # Can be disabled for testing
    
    def _check_permission(
        self,
        tool_call: ToolCall,
    ) -> tuple[bool, str, List[str]]:
        """
        Check if the tool call is allowed by MYCA permissions.
        
        Returns (allowed, reason, risk_flags).
        """
        if not self._enable_permission_checks:
            return True, "Permission checks disabled", []
        
        skill_registry = _get_skill_registry()
        if not skill_registry:
            # No skill registry available - allow by default (legacy mode)
            return True, "SkillRegistry not available", []
        
        skill_name = tool_call.skill_name
        if not skill_name:
            # No skill context - allow for backward compatibility
            return True, "No skill context", []
        
        risk_flags = []
        
        # Check if tool is allowed for this skill
        allowed, reason = skill_registry.check_tool_permission(skill_name, tool_call.name)
        if not allowed:
            risk_flags.append("TOOL_DENIED")
            return False, reason, risk_flags
        
        # Check sandbox requirement
        if skill_registry.requires_sandbox(skill_name):
            risk_flags.append("SANDBOX_REQUIRED")
            # For now, we allow execution but flag it
            # Full sandbox enforcement would require additional infrastructure
        
        # Check risk tier
        risk_tier = skill_registry.get_risk_tier(skill_name)
        if risk_tier in ("high", "critical"):
            risk_flags.append(f"RISK_TIER_{risk_tier.upper()}")
        
        return True, "Allowed by PERMISSIONS.json", risk_flags
    
    def _log_to_ledger(self, tool_call: ToolCall, event_type: str = "tool_call"):
        """Log tool call to EventLedger."""
        ledger = _get_event_ledger()
        if not ledger:
            return
        
        try:
            if event_type == "denial":
                ledger.log_denial(
                    agent_id=tool_call.skill_name or "unknown",
                    tool=tool_call.name,
                    args=tool_call.arguments,
                    reason=tool_call.permission_reason,
                )
            else:
                ledger.log_tool_call(
                    agent_id=tool_call.skill_name or "unknown",
                    tool=tool_call.name,
                    args=tool_call.arguments,
                    result_summary=str(tool_call.result)[:200] if tool_call.result else None,
                    risk_flags=tool_call.risk_flags,
                )
        except Exception as e:
            logger.debug("Failed to log to EventLedger: %s", e)
    
    async def execute(self, tool_call: ToolCall) -> ToolCall:
        """Execute a tool call and return results."""
        tool_def = self.registry.get(tool_call.name)
        
        if not tool_def:
            tool_call.status = ToolStatus.FAILED
            tool_call.error = f"Unknown tool: {tool_call.name}"
            return tool_call
        
        # MYCA: Check permissions before execution
        allowed, reason, risk_flags = self._check_permission(tool_call)
        tool_call.permission_allowed = allowed
        tool_call.permission_reason = reason
        tool_call.risk_flags = risk_flags
        
        if not allowed:
            tool_call.status = ToolStatus.FAILED
            tool_call.error = f"Permission denied: {reason}"
            logger.warning(
                "Tool call denied: %s for skill %s - %s",
                tool_call.name, tool_call.skill_name, reason
            )
            self._log_to_ledger(tool_call, event_type="denial")
            self.execution_history.append(tool_call)
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
            elif tool_call.name == "execute_workflow":
                result = await self._execute_workflow_tool(tool_call.arguments)
            elif tool_call.name == "generate_workflow":
                result = await self._generate_workflow_tool(tool_call.arguments)
            else:
                # Call MAS API for other tools
                result = await self._call_mas_tool(tool_call.name, tool_call.arguments)
            
            tool_call.result = result
            tool_call.status = ToolStatus.COMPLETED
            
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            tool_call.status = ToolStatus.FAILED
            tool_call.error = str(e)
            tool_call.risk_flags.append("EXECUTION_ERROR")
        
        tool_call.completed_at = datetime.now()
        if tool_call.started_at:
            tool_call.latency_ms = int(
                (tool_call.completed_at - tool_call.started_at).total_seconds() * 1000
            )
        
        # MYCA: Log to event ledger
        self._log_to_ledger(tool_call)
        
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

    async def _execute_workflow_tool(self, args: Dict[str, Any]) -> Any:
        """Execute an n8n workflow by name via N8NWorkflowAgent."""
        workflow_name = args.get("workflow_name", "").strip()
        parameters = args.get("parameters") or args.get("data")
        if not workflow_name:
            return {"status": "error", "message": "workflow_name is required"}
        try:
            from mycosoft_mas.agents.workflow.n8n_workflow_agent import N8NWorkflowAgent
            agent = N8NWorkflowAgent(agent_id="n8n-llm", name="N8N Workflow", config={})
            task = {"type": "execute_workflow", "workflow_name": workflow_name}
            if parameters:
                task["data"] = parameters
            result = await agent.process_task(task)
            return result
        except Exception as e:
            logger.exception("execute_workflow tool failed: %s", e)
            return {"status": "error", "message": str(e)}

    async def _generate_workflow_tool(self, args: Dict[str, Any]) -> Any:
        """Generate a new n8n workflow from natural language via WorkflowGeneratorAgent."""
        description = args.get("description", "").strip() or args.get("query", "").strip()
        name = args.get("name", "").strip() or None
        tags = args.get("tags")
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        if not description:
            return {"status": "error", "message": "description (or query) is required"}
        try:
            from mycosoft_mas.agents.workflow_generator_agent import generate_save_and_sync_workflow
            out = await generate_save_and_sync_workflow(
                description,
                name=name or None,
                tags=tags,
            )
            return {
                "status": "success",
                "workflow_id": out.get("workflow_id"),
                "name": out.get("name"),
                "file_path": out.get("file_path"),
                "sync": out.get("sync"),
            }
        except Exception as e:
            logger.exception("generate_workflow tool failed: %s", e)
            return {"status": "error", "message": str(e)}
    
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
    
    MYCA Integration (Feb 17, 2026):
    - Supports skill context for permission enforcement
    - Provides filtered tool lists based on skill permissions
    - Reports permission denials in results
    """
    
    def __init__(self, skill_name: Optional[str] = None):
        """
        Initialize tool manager.
        
        Args:
            skill_name: Optional skill context for permission enforcement.
                       If provided, tool calls will be checked against the
                       skill's PERMISSIONS.json.
        """
        self.registry = ToolRegistry()
        self.executor = ToolExecutor(self.registry)
        self.pending_calls: List[ToolCall] = []
        self.skill_name = skill_name
    
    def set_skill_context(self, skill_name: str):
        """Set the skill context for permission enforcement."""
        self.skill_name = skill_name
    
    def get_tool_definitions_for_llm(
        self,
        filter_by_permissions: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get tool definitions in a format suitable for LLM function calling.
        
        Args:
            filter_by_permissions: If True and skill_name is set, only return
                                   tools allowed by the skill's permissions.
        """
        all_tools = self.registry.get_tool_definitions()
        
        if not filter_by_permissions or not self.skill_name:
            return all_tools
        
        # Filter by skill permissions
        skill_registry = _get_skill_registry()
        if not skill_registry:
            return all_tools
        
        allowed_tools = []
        for tool in all_tools:
            allowed, _ = skill_registry.check_tool_permission(
                self.skill_name, tool["name"]
            )
            if allowed:
                allowed_tools.append(tool)
        
        return allowed_tools
    
    async def process_tool_calls(
        self, 
        tool_calls: List[Dict[str, Any]],
        skill_name: Optional[str] = None,
    ) -> List[ToolCall]:
        """
        Process multiple tool calls and return results.
        
        Args:
            tool_calls: List of tool call dicts with id, name, arguments.
            skill_name: Optional skill context override. If not provided,
                       uses the manager's default skill_name.
        """
        results = []
        effective_skill = skill_name or self.skill_name
        
        for call_data in tool_calls:
            call = ToolCall(
                id=call_data.get("id", ""),
                name=call_data.get("name", ""),
                arguments=call_data.get("arguments", {}),
                skill_name=effective_skill,
            )
            
            result = await self.executor.execute(call)
            results.append(result)
        
        return results
    
    def format_tool_result_for_injection(self, tool_call: ToolCall) -> str:
        """Format a tool result for injection into the response."""
        if tool_call.status == ToolStatus.COMPLETED:
            result_str = json.dumps(tool_call.result) if isinstance(tool_call.result, dict) else str(tool_call.result)
            return f"[TOOL] {tool_call.name}: {result_str}"
        elif not tool_call.permission_allowed:
            return f"[TOOL] {tool_call.name}: Permission denied - {tool_call.permission_reason}"
        else:
            return f"[TOOL] {tool_call.name}: Error - {tool_call.error}"
    
    def get_denied_tools_summary(self) -> List[Dict[str, Any]]:
        """Get summary of denied tool calls from execution history."""
        denied = []
        for call in self.executor.execution_history:
            if not call.permission_allowed:
                denied.append({
                    "tool": call.name,
                    "skill": call.skill_name,
                    "reason": call.permission_reason,
                })
        return denied


# Singleton instances
_tool_registry: Optional[ToolRegistry] = None
_tool_manager: Optional[ConversationToolManager] = None


def get_tool_registry() -> ToolRegistry:
    """Get or create the tool registry singleton."""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry


def get_tool_manager(skill_name: Optional[str] = None) -> ConversationToolManager:
    """
    Get or create the tool manager singleton.
    
    Args:
        skill_name: Optional skill context for permission enforcement.
                   If provided, updates the manager's skill context.
    """
    global _tool_manager
    if _tool_manager is None:
        _tool_manager = ConversationToolManager(skill_name=skill_name)
    elif skill_name:
        _tool_manager.set_skill_context(skill_name)
    return _tool_manager


def create_tool_manager_for_skill(skill_name: str) -> ConversationToolManager:
    """
    Create a new tool manager for a specific skill context.
    
    Unlike get_tool_manager(), this always creates a new instance,
    useful for isolated skill executions.
    
    Args:
        skill_name: Skill context for permission enforcement.
    """
    return ConversationToolManager(skill_name=skill_name)
