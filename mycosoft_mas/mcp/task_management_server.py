"""
Task Management MCP Server for Cursor Integration.
Created: February 12, 2026

Provides MCP tools for task and plan management:
- task_create: Create tasks from natural language
- task_list: List tasks by status/agent
- task_update: Update task status
- task_assign: Assign to agent
- plan_get: Get current plan
- plan_update: Update plan progress
- gap_scan: Scan for gaps and TODOs

Connects to: plan-tracker agent, gap reports, Cursor plans.
"""

import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger("TaskManagementMCP")


@dataclass
class Task:
    """Representation of a task."""
    id: str
    title: str
    description: str
    status: str  # pending, in_progress, completed, cancelled
    priority: str  # low, medium, high, critical
    assigned_agent: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    parent_plan: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Plan:
    """Representation of a plan/roadmap."""
    id: str
    name: str
    description: str
    status: str  # draft, active, completed, abandoned
    tasks: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    phases: List[Dict[str, Any]] = field(default_factory=list)
    progress_percent: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPToolDefinition:
    """Definition of an MCP tool."""
    name: str
    description: str
    parameters: Dict[str, Any]


class TaskManagementMCPServer:
    """
    MCP Server for task and plan management.
    
    Tools:
    - task_create: Create a new task
    - task_list: List tasks with filters
    - task_update: Update task status/details
    - task_assign: Assign task to an agent
    - plan_get: Get plan details
    - plan_update: Update plan progress
    - plan_list: List available plans
    - gap_scan: Scan for code gaps and TODOs
    """
    
    def __init__(self, data_dir: Optional[str] = None):
        self._data_dir = Path(data_dir or os.getenv(
            "TASK_DATA_DIR",
            os.path.join(os.path.dirname(__file__), "../../data/tasks")
        ))
        self._data_dir.mkdir(parents=True, exist_ok=True)
        
        self._tasks: Dict[str, Task] = {}
        self._plans: Dict[str, Plan] = {}
        self._initialized = False
        
        # Paths for integration
        self._cursor_plans_dir = Path(os.getenv(
            "CURSOR_PLANS_DIR",
            "C:/Users/admin2/.cursor/plans"
        ))
        self._gap_report_path = Path(os.getenv(
            "GAP_REPORT_PATH",
            os.path.join(os.path.dirname(__file__), "../../.cursor/gap_report_latest.json")
        ))
        self._gap_index_path = Path(os.getenv(
            "GAP_INDEX_PATH",
            os.path.join(os.path.dirname(__file__), "../../.cursor/gap_report_index.json")
        ))
        
        self._tools = self._define_tools()
    
    def _define_tools(self) -> List[MCPToolDefinition]:
        """Define MCP tool specifications."""
        return [
            MCPToolDefinition(
                name="task_create",
                description="Create a new task. Use this to track work items, bugs, or features.",
                parameters={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Short title for the task"
                        },
                        "description": {
                            "type": "string",
                            "description": "Detailed description of what needs to be done"
                        },
                        "priority": {
                            "type": "string",
                            "description": "Priority level",
                            "enum": ["low", "medium", "high", "critical"]
                        },
                        "assigned_agent": {
                            "type": "string",
                            "description": "Name of the agent to assign (e.g., backend-dev, website-dev)"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags for categorization"
                        },
                        "parent_plan": {
                            "type": "string",
                            "description": "ID of the parent plan if part of a larger initiative"
                        }
                    },
                    "required": ["title", "description"]
                }
            ),
            MCPToolDefinition(
                name="task_list",
                description="List tasks with optional filters. Get all tasks or filter by status, agent, tags.",
                parameters={
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "description": "Filter by status",
                            "enum": ["pending", "in_progress", "completed", "cancelled", "all"]
                        },
                        "assigned_agent": {
                            "type": "string",
                            "description": "Filter by assigned agent"
                        },
                        "priority": {
                            "type": "string",
                            "description": "Filter by priority",
                            "enum": ["low", "medium", "high", "critical"]
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by tags (any match)"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of tasks to return",
                            "default": 50
                        }
                    }
                }
            ),
            MCPToolDefinition(
                name="task_update",
                description="Update an existing task's status or details.",
                parameters={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "ID of the task to update"
                        },
                        "status": {
                            "type": "string",
                            "description": "New status",
                            "enum": ["pending", "in_progress", "completed", "cancelled"]
                        },
                        "title": {
                            "type": "string",
                            "description": "Updated title"
                        },
                        "description": {
                            "type": "string",
                            "description": "Updated description"
                        },
                        "priority": {
                            "type": "string",
                            "description": "Updated priority",
                            "enum": ["low", "medium", "high", "critical"]
                        }
                    },
                    "required": ["task_id"]
                }
            ),
            MCPToolDefinition(
                name="task_assign",
                description="Assign a task to a specific agent.",
                parameters={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "ID of the task to assign"
                        },
                        "agent": {
                            "type": "string",
                            "description": "Name of the agent to assign (e.g., backend-dev, website-dev, security-auditor)"
                        }
                    },
                    "required": ["task_id", "agent"]
                }
            ),
            MCPToolDefinition(
                name="plan_get",
                description="Get details of a specific plan or the current active plan.",
                parameters={
                    "type": "object",
                    "properties": {
                        "plan_id": {
                            "type": "string",
                            "description": "ID of the plan to retrieve. If not provided, returns the most recent active plan."
                        },
                        "include_tasks": {
                            "type": "boolean",
                            "description": "Include full task details in the response",
                            "default": True
                        }
                    }
                }
            ),
            MCPToolDefinition(
                name="plan_update",
                description="Update plan progress or status.",
                parameters={
                    "type": "object",
                    "properties": {
                        "plan_id": {
                            "type": "string",
                            "description": "ID of the plan to update"
                        },
                        "status": {
                            "type": "string",
                            "description": "New status",
                            "enum": ["draft", "active", "completed", "abandoned"]
                        },
                        "progress_percent": {
                            "type": "integer",
                            "description": "Progress percentage (0-100)",
                            "minimum": 0,
                            "maximum": 100
                        },
                        "current_phase": {
                            "type": "string",
                            "description": "Name of the current phase"
                        }
                    },
                    "required": ["plan_id"]
                }
            ),
            MCPToolDefinition(
                name="plan_list",
                description="List all plans from Cursor plans directory and internal registry.",
                parameters={
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "description": "Filter by status",
                            "enum": ["draft", "active", "completed", "abandoned", "all"]
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of plans to return",
                            "default": 20
                        },
                        "include_cursor_plans": {
                            "type": "boolean",
                            "description": "Include plans from Cursor plans directory",
                            "default": True
                        }
                    }
                }
            ),
            MCPToolDefinition(
                name="gap_scan",
                description="Scan codebase for gaps, TODOs, FIXMEs, and incomplete implementations.",
                parameters={
                    "type": "object",
                    "properties": {
                        "repo": {
                            "type": "string",
                            "description": "Repository to scan (MAS, WEBSITE, MINDEX, etc.). If not provided, scans all."
                        },
                        "category": {
                            "type": "string",
                            "description": "Category of gaps to find",
                            "enum": ["todo", "fixme", "stub", "placeholder", "501_route", "all"]
                        },
                        "refresh": {
                            "type": "boolean",
                            "description": "Force refresh of gap report",
                            "default": False
                        }
                    }
                }
            )
        ]
    
    async def initialize(self) -> None:
        """Initialize the server and load existing data."""
        if self._initialized:
            return
        
        # Load tasks from disk
        tasks_file = self._data_dir / "tasks.json"
        if tasks_file.exists():
            try:
                with open(tasks_file, "r") as f:
                    data = json.load(f)
                    for task_data in data:
                        task = Task(**task_data)
                        self._tasks[task.id] = task
            except Exception as e:
                logger.error(f"Failed to load tasks: {e}")
        
        # Load plans from disk
        plans_file = self._data_dir / "plans.json"
        if plans_file.exists():
            try:
                with open(plans_file, "r") as f:
                    data = json.load(f)
                    for plan_data in data:
                        plan = Plan(**plan_data)
                        self._plans[plan.id] = plan
            except Exception as e:
                logger.error(f"Failed to load plans: {e}")
        
        self._initialized = True
        logger.info(f"Task Management MCP initialized with {len(self._tasks)} tasks, {len(self._plans)} plans")
    
    async def _save_tasks(self) -> None:
        """Persist tasks to disk."""
        tasks_file = self._data_dir / "tasks.json"
        try:
            with open(tasks_file, "w") as f:
                json.dump([
                    {
                        "id": t.id, "title": t.title, "description": t.description,
                        "status": t.status, "priority": t.priority,
                        "assigned_agent": t.assigned_agent, "created_at": t.created_at,
                        "updated_at": t.updated_at, "completed_at": t.completed_at,
                        "tags": t.tags, "parent_plan": t.parent_plan,
                        "dependencies": t.dependencies, "metadata": t.metadata
                    }
                    for t in self._tasks.values()
                ], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save tasks: {e}")
    
    async def _save_plans(self) -> None:
        """Persist plans to disk."""
        plans_file = self._data_dir / "plans.json"
        try:
            with open(plans_file, "w") as f:
                json.dump([
                    {
                        "id": p.id, "name": p.name, "description": p.description,
                        "status": p.status, "tasks": p.tasks, "created_at": p.created_at,
                        "updated_at": p.updated_at, "phases": p.phases,
                        "progress_percent": p.progress_percent, "metadata": p.metadata
                    }
                    for p in self._plans.values()
                ], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save plans: {e}")
    
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
            "task_create": self._handle_task_create,
            "task_list": self._handle_task_list,
            "task_update": self._handle_task_update,
            "task_assign": self._handle_task_assign,
            "plan_get": self._handle_plan_get,
            "plan_update": self._handle_plan_update,
            "plan_list": self._handle_plan_list,
            "gap_scan": self._handle_gap_scan,
        }
        
        handler = handlers.get(name)
        if not handler:
            return {"error": f"Unknown tool: {name}"}
        
        try:
            return await handler(arguments)
        except Exception as e:
            logger.error(f"Tool {name} failed: {e}")
            return {"error": str(e)}
    
    async def _handle_task_create(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new task."""
        task = Task(
            id=str(uuid4())[:8],
            title=args["title"],
            description=args["description"],
            status="pending",
            priority=args.get("priority", "medium"),
            assigned_agent=args.get("assigned_agent"),
            tags=args.get("tags", []),
            parent_plan=args.get("parent_plan")
        )
        
        self._tasks[task.id] = task
        await self._save_tasks()
        
        return {
            "success": True,
            "task_id": task.id,
            "message": f"Created task '{task.title}' with ID {task.id}"
        }
    
    async def _handle_task_list(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List tasks with filters."""
        tasks = list(self._tasks.values())
        
        # Apply filters
        status = args.get("status", "all")
        if status != "all":
            tasks = [t for t in tasks if t.status == status]
        
        agent = args.get("assigned_agent")
        if agent:
            tasks = [t for t in tasks if t.assigned_agent == agent]
        
        priority = args.get("priority")
        if priority:
            tasks = [t for t in tasks if t.priority == priority]
        
        tags = args.get("tags", [])
        if tags:
            tasks = [t for t in tasks if any(tag in t.tags for tag in tags)]
        
        # Sort by created date (newest first) and limit
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        limit = args.get("limit", 50)
        tasks = tasks[:limit]
        
        return {
            "success": True,
            "count": len(tasks),
            "tasks": [
                {
                    "id": t.id, "title": t.title, "status": t.status,
                    "priority": t.priority, "assigned_agent": t.assigned_agent,
                    "tags": t.tags, "created_at": t.created_at
                }
                for t in tasks
            ]
        }
    
    async def _handle_task_update(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Update a task."""
        task_id = args["task_id"]
        task = self._tasks.get(task_id)
        
        if not task:
            return {"error": f"Task {task_id} not found"}
        
        if "status" in args:
            task.status = args["status"]
            if args["status"] == "completed":
                task.completed_at = datetime.now(timezone.utc).isoformat()
        
        if "title" in args:
            task.title = args["title"]
        
        if "description" in args:
            task.description = args["description"]
        
        if "priority" in args:
            task.priority = args["priority"]
        
        task.updated_at = datetime.now(timezone.utc).isoformat()
        await self._save_tasks()
        
        return {
            "success": True,
            "message": f"Updated task {task_id}",
            "task": {
                "id": task.id, "title": task.title, "status": task.status,
                "priority": task.priority, "updated_at": task.updated_at
            }
        }
    
    async def _handle_task_assign(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Assign a task to an agent."""
        task_id = args["task_id"]
        agent = args["agent"]
        task = self._tasks.get(task_id)
        
        if not task:
            return {"error": f"Task {task_id} not found"}
        
        task.assigned_agent = agent
        task.updated_at = datetime.now(timezone.utc).isoformat()
        await self._save_tasks()
        
        return {
            "success": True,
            "message": f"Assigned task {task_id} to {agent}",
            "task": {"id": task.id, "title": task.title, "assigned_agent": agent}
        }
    
    async def _handle_plan_get(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get plan details."""
        plan_id = args.get("plan_id")
        include_tasks = args.get("include_tasks", True)
        
        if plan_id:
            plan = self._plans.get(plan_id)
            if not plan:
                return {"error": f"Plan {plan_id} not found"}
        else:
            # Get most recent active plan
            active_plans = [p for p in self._plans.values() if p.status == "active"]
            if not active_plans:
                return {"error": "No active plans found"}
            plan = max(active_plans, key=lambda p: p.updated_at)
        
        result = {
            "success": True,
            "plan": {
                "id": plan.id, "name": plan.name, "description": plan.description,
                "status": plan.status, "progress_percent": plan.progress_percent,
                "phases": plan.phases, "created_at": plan.created_at,
                "updated_at": plan.updated_at
            }
        }
        
        if include_tasks:
            result["tasks"] = [
                {
                    "id": t.id, "title": t.title, "status": t.status,
                    "priority": t.priority, "assigned_agent": t.assigned_agent
                }
                for t in [self._tasks.get(tid) for tid in plan.tasks]
                if t is not None
            ]
        
        return result
    
    async def _handle_plan_update(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Update plan progress."""
        plan_id = args["plan_id"]
        plan = self._plans.get(plan_id)
        
        if not plan:
            return {"error": f"Plan {plan_id} not found"}
        
        if "status" in args:
            plan.status = args["status"]
        
        if "progress_percent" in args:
            plan.progress_percent = args["progress_percent"]
        
        if "current_phase" in args:
            # Update phase status
            for phase in plan.phases:
                if phase.get("name") == args["current_phase"]:
                    phase["status"] = "in_progress"
                elif phase.get("status") == "in_progress":
                    phase["status"] = "completed"
        
        plan.updated_at = datetime.now(timezone.utc).isoformat()
        await self._save_plans()
        
        return {
            "success": True,
            "message": f"Updated plan {plan_id}",
            "plan": {
                "id": plan.id, "name": plan.name, "status": plan.status,
                "progress_percent": plan.progress_percent
            }
        }
    
    async def _handle_plan_list(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List all plans."""
        plans = list(self._plans.values())
        
        # Filter by status
        status = args.get("status", "all")
        if status != "all":
            plans = [p for p in plans if p.status == status]
        
        # Sort by updated date and limit
        plans.sort(key=lambda p: p.updated_at, reverse=True)
        limit = args.get("limit", 20)
        
        result = {
            "success": True,
            "internal_plans": [
                {
                    "id": p.id, "name": p.name, "status": p.status,
                    "progress_percent": p.progress_percent, "updated_at": p.updated_at
                }
                for p in plans[:limit]
            ]
        }
        
        # Include Cursor plans if requested
        if args.get("include_cursor_plans", True):
            cursor_plans = []
            if self._cursor_plans_dir.exists():
                plan_files = sorted(
                    self._cursor_plans_dir.glob("*.plan.md"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True
                )[:limit]
                
                for pf in plan_files:
                    cursor_plans.append({
                        "name": pf.stem.replace(".plan", ""),
                        "path": str(pf),
                        "modified": datetime.fromtimestamp(pf.stat().st_mtime).isoformat()
                    })
            
            result["cursor_plans"] = cursor_plans
            result["cursor_plans_count"] = len(list(self._cursor_plans_dir.glob("*.plan.md"))) if self._cursor_plans_dir.exists() else 0
        
        return result
    
    async def _handle_gap_scan(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Scan for code gaps."""
        repo = args.get("repo")
        category = args.get("category", "all")
        refresh = args.get("refresh", False)
        
        # Check for existing gap report
        if not refresh and self._gap_report_path.exists():
            try:
                with open(self._gap_report_path, "r") as f:
                    gap_data = json.load(f)
                
                # Filter by repo if specified
                if repo:
                    filtered = {
                        "summary": gap_data.get("summary", {}),
                        "by_repo": {repo: gap_data.get("by_repo", {}).get(repo, {})}
                    }
                    gap_data = filtered
                
                # Filter by category if specified
                if category != "all":
                    summary = gap_data.get("summary", {})
                    gap_data = {
                        "summary": {category: summary.get(category, 0)},
                        "category_filter": category
                    }
                
                return {
                    "success": True,
                    "source": "cached_report",
                    "report_path": str(self._gap_report_path),
                    "gaps": gap_data
                }
            except Exception as e:
                logger.warning(f"Failed to read gap report: {e}")
        
        # If no cached report or refresh requested, return guidance
        return {
            "success": True,
            "source": "guidance",
            "message": "Run scripts/gap_scan_cursor_background.py to generate fresh gap report",
            "gap_report_path": str(self._gap_report_path),
            "gap_index_path": str(self._gap_index_path),
            "categories": ["todo", "fixme", "stub", "placeholder", "501_route"]
        }


class MCPProtocolHandler:
    """Handle MCP JSON-RPC protocol."""
    
    def __init__(self, server: TaskManagementMCPServer):
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
                        "name": "mycosoft-task-management",
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
_mcp_server: Optional[TaskManagementMCPServer] = None


async def get_mcp_server() -> TaskManagementMCPServer:
    """Get or create the singleton MCP server instance."""
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = TaskManagementMCPServer()
        await _mcp_server.initialize()
    return _mcp_server


async def run_stdio_server():
    """Run the MCP server over stdio."""
    server = await get_mcp_server()
    handler = MCPProtocolHandler(server)
    
    logger.info("Task Management MCP Server started on stdio")
    
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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_stdio_server())
