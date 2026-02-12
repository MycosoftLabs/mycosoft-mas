"""
Registry MCP Server for Cursor Integration.
Created: February 12, 2026

Provides MCP tools for managing agents, skills, APIs, and documentation:
- registry_add_agent: Register a new agent
- registry_add_api: Register a new API endpoint
- registry_add_skill: Register a new skill
- registry_sync: Trigger full sync
- docs_index: Index new documentation
- skill_list: List available skills
- agent_registry_list: List all registered agents

Automates registry updates after code changes.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("RegistryMCP")


@dataclass
class MCPToolDefinition:
    """Definition of an MCP tool."""
    name: str
    description: str
    parameters: Dict[str, Any]


class RegistryMCPServer:
    """
    MCP Server for registry management.
    
    Tools:
    - registry_add_agent: Register a new agent in MAS
    - registry_add_api: Register a new API endpoint
    - registry_add_skill: Register a new Cursor skill
    - registry_sync: Synchronize all registries
    - docs_index: Add document to index
    - skill_list: List available skills
    - agent_registry_list: List registered agents
    - docs_manifest_rebuild: Rebuild documentation manifest
    """
    
    def __init__(self, workspace_root: Optional[str] = None):
        self._workspace_root = Path(workspace_root or os.getenv(
            "WORKSPACE_ROOT",
            "c:/Users/admin2/Desktop/MYCOSOFT/CODE/MAS/mycosoft-mas"
        ))
        self._cursor_dir = self._workspace_root / ".cursor"
        self._docs_dir = self._workspace_root / "docs"
        self._skills_dir = self._cursor_dir / "skills"
        self._agents_dir = self._cursor_dir / "agents"
        
        # External paths
        self._user_skills_dir = Path("C:/Users/admin2/.cursor/skills")
        self._user_skills_cursor_dir = Path("C:/Users/admin2/.cursor/skills-cursor")
        
        self._initialized = False
        self._tools = self._define_tools()
    
    def _define_tools(self) -> List[MCPToolDefinition]:
        """Define MCP tool specifications."""
        return [
            MCPToolDefinition(
                name="registry_add_agent",
                description="Register a new MAS agent. Creates the agent file and updates registries.",
                parameters={
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "Unique agent identifier (e.g., 'my_new_agent')"
                        },
                        "name": {
                            "type": "string",
                            "description": "Human-readable agent name"
                        },
                        "description": {
                            "type": "string",
                            "description": "What the agent does"
                        },
                        "category": {
                            "type": "string",
                            "description": "Agent category",
                            "enum": ["core", "infrastructure", "scientific", "device", 
                                    "data", "integration", "financial", "security",
                                    "mycology", "earth2", "simulation", "business", "custom"]
                        },
                        "capabilities": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of capabilities"
                        },
                        "create_cursor_agent": {
                            "type": "boolean",
                            "description": "Also create a Cursor sub-agent .md file",
                            "default": True
                        }
                    },
                    "required": ["agent_id", "name", "description", "category"]
                }
            ),
            MCPToolDefinition(
                name="registry_add_api",
                description="Register a new API endpoint in the API catalog.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "API path (e.g., '/api/v1/users')"
                        },
                        "method": {
                            "type": "string",
                            "description": "HTTP method",
                            "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"]
                        },
                        "router": {
                            "type": "string",
                            "description": "Router file name (e.g., 'users_api.py')"
                        },
                        "description": {
                            "type": "string",
                            "description": "What the endpoint does"
                        },
                        "auth_required": {
                            "type": "boolean",
                            "description": "Whether authentication is required",
                            "default": True
                        }
                    },
                    "required": ["path", "method", "router", "description"]
                }
            ),
            MCPToolDefinition(
                name="registry_add_skill",
                description="Register a new Cursor skill.",
                parameters={
                    "type": "object",
                    "properties": {
                        "skill_id": {
                            "type": "string",
                            "description": "Unique skill identifier (e.g., 'deploy-website')"
                        },
                        "name": {
                            "type": "string",
                            "description": "Human-readable skill name"
                        },
                        "description": {
                            "type": "string",
                            "description": "One-line description of what the skill does"
                        },
                        "trigger_phrases": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Phrases that should trigger this skill"
                        },
                        "location": {
                            "type": "string",
                            "description": "Where to create the skill",
                            "enum": ["workspace", "user", "cursor"],
                            "default": "workspace"
                        }
                    },
                    "required": ["skill_id", "name", "description"]
                }
            ),
            MCPToolDefinition(
                name="registry_sync",
                description="Synchronize all registries by running sync scripts.",
                parameters={
                    "type": "object",
                    "properties": {
                        "sync_agents": {
                            "type": "boolean",
                            "description": "Sync agent registry",
                            "default": True
                        },
                        "sync_skills": {
                            "type": "boolean",
                            "description": "Sync skill registry",
                            "default": True
                        },
                        "sync_docs": {
                            "type": "boolean",
                            "description": "Rebuild docs manifest",
                            "default": True
                        },
                        "sync_gaps": {
                            "type": "boolean",
                            "description": "Run gap scan",
                            "default": False
                        }
                    }
                }
            ),
            MCPToolDefinition(
                name="docs_index",
                description="Add a new document to the documentation index.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the document relative to workspace"
                        },
                        "title": {
                            "type": "string",
                            "description": "Document title"
                        },
                        "category": {
                            "type": "string",
                            "description": "Document category",
                            "enum": ["architecture", "api", "agent", "cursor", "deployment",
                                    "memory", "integration", "scientific", "device", "other"]
                        },
                        "add_to_cursor_index": {
                            "type": "boolean",
                            "description": "Also add to CURSOR_DOCS_INDEX.md",
                            "default": False
                        }
                    },
                    "required": ["path", "title", "category"]
                }
            ),
            MCPToolDefinition(
                name="skill_list",
                description="List all available Cursor skills.",
                parameters={
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "Which skills to list",
                            "enum": ["workspace", "user", "cursor", "all"],
                            "default": "all"
                        }
                    }
                }
            ),
            MCPToolDefinition(
                name="agent_registry_list",
                description="List all registered agents from Cursor agent files.",
                parameters={
                    "type": "object",
                    "properties": {
                        "include_details": {
                            "type": "boolean",
                            "description": "Include full agent descriptions",
                            "default": False
                        }
                    }
                }
            ),
            MCPToolDefinition(
                name="docs_manifest_rebuild",
                description="Rebuild the documentation manifest (docs_manifest.json).",
                parameters={
                    "type": "object",
                    "properties": {
                        "include_all_repos": {
                            "type": "boolean",
                            "description": "Include docs from all workspace repos",
                            "default": True
                        }
                    }
                }
            )
        ]
    
    async def initialize(self) -> None:
        """Initialize the server."""
        if self._initialized:
            return
        
        # Ensure directories exist
        self._skills_dir.mkdir(parents=True, exist_ok=True)
        self._agents_dir.mkdir(parents=True, exist_ok=True)
        
        self._initialized = True
        logger.info(f"Registry MCP initialized, workspace: {self._workspace_root}")
    
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
            "registry_add_agent": self._handle_add_agent,
            "registry_add_api": self._handle_add_api,
            "registry_add_skill": self._handle_add_skill,
            "registry_sync": self._handle_sync,
            "docs_index": self._handle_docs_index,
            "skill_list": self._handle_skill_list,
            "agent_registry_list": self._handle_agent_list,
            "docs_manifest_rebuild": self._handle_docs_rebuild,
        }
        
        handler = handlers.get(name)
        if not handler:
            return {"error": f"Unknown tool: {name}"}
        
        try:
            return await handler(arguments)
        except Exception as e:
            logger.error(f"Tool {name} failed: {e}")
            return {"error": str(e)}
    
    async def _handle_add_agent(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new agent."""
        agent_id = args["agent_id"]
        name = args["name"]
        description = args["description"]
        category = args["category"]
        capabilities = args.get("capabilities", [])
        create_cursor = args.get("create_cursor_agent", True)
        
        results = {
            "agent_id": agent_id,
            "actions": []
        }
        
        # Create Cursor agent .md file if requested
        if create_cursor:
            cursor_agent_path = self._agents_dir / f"{agent_id.replace('_', '-')}.md"
            
            agent_content = f"""---
name: {agent_id.replace('_', '-')}
description: {description}
---

You are the {name} for the Mycosoft system.

## Capabilities

{chr(10).join(f'- {cap}' for cap in capabilities) if capabilities else '- Define capabilities here'}

## Category

{category}

## When to Use

Use this agent when: {description.lower()}

## How to Use

1. Analyze the request
2. Execute appropriate actions
3. Report results

## Integration Points

- MAS API: http://192.168.0.188:8001
- MINDEX API: http://192.168.0.189:8000
"""
            
            with open(cursor_agent_path, "w") as f:
                f.write(agent_content)
            
            results["actions"].append({
                "action": "created_cursor_agent",
                "path": str(cursor_agent_path)
            })
        
        # Update agent count in rules
        results["actions"].append({
            "action": "reminder",
            "message": "Update agent count in mycosoft-full-context-and-registries.mdc"
        })
        
        return {
            "success": True,
            **results
        }
    
    async def _handle_add_api(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new API endpoint."""
        path = args["path"]
        method = args["method"]
        router = args["router"]
        description = args["description"]
        
        # Update API catalog
        api_catalog_path = self._docs_dir / "API_CATALOG_FEB04_2026.md"
        
        entry = f"\n| {method} | `{path}` | {router} | {description} |"
        
        results = {
            "api": {"path": path, "method": method},
            "actions": [
                {
                    "action": "reminder",
                    "message": f"Add to API_CATALOG: {entry}"
                }
            ]
        }
        
        return {
            "success": True,
            **results
        }
    
    async def _handle_add_skill(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new skill."""
        skill_id = args["skill_id"]
        name = args["name"]
        description = args["description"]
        trigger_phrases = args.get("trigger_phrases", [])
        location = args.get("location", "workspace")
        
        # Determine skill directory
        if location == "workspace":
            skill_dir = self._skills_dir / skill_id
        elif location == "user":
            skill_dir = self._user_skills_dir / skill_id
        else:
            skill_dir = self._user_skills_cursor_dir / skill_id
        
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_path = skill_dir / "SKILL.md"
        
        # Create skill content
        skill_content = f"""# {name}

{description}

## When to Use

{chr(10).join(f'- {phrase}' for phrase in trigger_phrases) if trigger_phrases else '- When the user asks to ' + description.lower()}

## Steps

1. Analyze the request
2. Execute the skill
3. Verify completion

## Notes

- Created: {datetime.now().strftime('%Y-%m-%d')}
- Location: {location}
"""
        
        with open(skill_path, "w") as f:
            f.write(skill_content)
        
        return {
            "success": True,
            "skill_id": skill_id,
            "path": str(skill_path),
            "message": f"Created skill '{name}' at {skill_path}"
        }
    
    async def _handle_sync(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronize registries."""
        results = {"actions": []}
        
        sync_script = self._workspace_root / "scripts" / "sync_cursor_system.py"
        
        if args.get("sync_agents", True) or args.get("sync_skills", True):
            if sync_script.exists():
                try:
                    result = subprocess.run(
                        ["python", str(sync_script)],
                        capture_output=True,
                        text=True,
                        cwd=str(self._workspace_root),
                        timeout=60
                    )
                    results["actions"].append({
                        "action": "sync_cursor_system",
                        "success": result.returncode == 0,
                        "output": result.stdout[:500] if result.stdout else None
                    })
                except Exception as e:
                    results["actions"].append({
                        "action": "sync_cursor_system",
                        "success": False,
                        "error": str(e)
                    })
            else:
                results["actions"].append({
                    "action": "sync_cursor_system",
                    "success": False,
                    "error": "sync_cursor_system.py not found"
                })
        
        if args.get("sync_docs", True):
            docs_script = self._workspace_root / "scripts" / "build_docs_manifest.py"
            if docs_script.exists():
                try:
                    result = subprocess.run(
                        ["python", str(docs_script)],
                        capture_output=True,
                        text=True,
                        cwd=str(self._workspace_root),
                        timeout=120
                    )
                    results["actions"].append({
                        "action": "build_docs_manifest",
                        "success": result.returncode == 0
                    })
                except Exception as e:
                    results["actions"].append({
                        "action": "build_docs_manifest",
                        "success": False,
                        "error": str(e)
                    })
        
        if args.get("sync_gaps", False):
            gap_script = self._workspace_root / "scripts" / "gap_scan_cursor_background.py"
            if gap_script.exists():
                try:
                    result = subprocess.run(
                        ["python", str(gap_script)],
                        capture_output=True,
                        text=True,
                        cwd=str(self._workspace_root),
                        timeout=300
                    )
                    results["actions"].append({
                        "action": "gap_scan",
                        "success": result.returncode == 0
                    })
                except Exception as e:
                    results["actions"].append({
                        "action": "gap_scan",
                        "success": False,
                        "error": str(e)
                    })
        
        return {
            "success": True,
            **results
        }
    
    async def _handle_docs_index(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Add document to index."""
        path = args["path"]
        title = args["title"]
        category = args["category"]
        add_to_cursor = args.get("add_to_cursor_index", False)
        
        results = {"document": {"path": path, "title": title, "category": category}, "actions": []}
        
        # Add to MASTER_DOCUMENT_INDEX
        master_index = self._docs_dir / "MASTER_DOCUMENT_INDEX.md"
        if master_index.exists():
            results["actions"].append({
                "action": "reminder",
                "message": f"Add to MASTER_DOCUMENT_INDEX.md: - [{title}]({path})"
            })
        
        # Add to CURSOR_DOCS_INDEX if requested
        if add_to_cursor:
            cursor_index = self._cursor_dir / "CURSOR_DOCS_INDEX.md"
            if cursor_index.exists():
                results["actions"].append({
                    "action": "reminder",
                    "message": f"Add to CURSOR_DOCS_INDEX.md: - [{title}]({path})"
                })
        
        return {
            "success": True,
            **results
        }
    
    async def _handle_skill_list(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List available skills."""
        location = args.get("location", "all")
        skills = []
        
        skill_dirs = []
        if location in ["workspace", "all"]:
            skill_dirs.append(("workspace", self._skills_dir))
        if location in ["user", "all"]:
            skill_dirs.append(("user", self._user_skills_dir))
        if location in ["cursor", "all"]:
            skill_dirs.append(("cursor", self._user_skills_cursor_dir))
        
        for loc, dir_path in skill_dirs:
            if dir_path.exists():
                for skill_dir in dir_path.iterdir():
                    if skill_dir.is_dir():
                        skill_file = skill_dir / "SKILL.md"
                        if skill_file.exists():
                            # Extract first line as description
                            with open(skill_file, "r") as f:
                                lines = f.readlines()
                                title = lines[0].strip("# \n") if lines else skill_dir.name
                                desc = ""
                                for line in lines[1:5]:
                                    line = line.strip()
                                    if line and not line.startswith("#"):
                                        desc = line
                                        break
                            
                            skills.append({
                                "id": skill_dir.name,
                                "title": title,
                                "description": desc[:100] if desc else "No description",
                                "location": loc,
                                "path": str(skill_file)
                            })
        
        return {
            "success": True,
            "count": len(skills),
            "skills": skills
        }
    
    async def _handle_agent_list(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List registered Cursor agents."""
        include_details = args.get("include_details", False)
        agents = []
        
        if self._agents_dir.exists():
            for agent_file in self._agents_dir.glob("*.md"):
                agent_info = {
                    "id": agent_file.stem,
                    "path": str(agent_file)
                }
                
                if include_details:
                    with open(agent_file, "r") as f:
                        content = f.read()
                        # Extract description from frontmatter
                        if "description:" in content:
                            for line in content.split("\n"):
                                if line.startswith("description:"):
                                    agent_info["description"] = line.split(":", 1)[1].strip()
                                    break
                
                agents.append(agent_info)
        
        return {
            "success": True,
            "count": len(agents),
            "agents": agents
        }
    
    async def _handle_docs_rebuild(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Rebuild documentation manifest."""
        docs_script = self._workspace_root / "scripts" / "build_docs_manifest.py"
        
        if not docs_script.exists():
            return {
                "success": False,
                "error": "build_docs_manifest.py not found"
            }
        
        try:
            result = subprocess.run(
                ["python", str(docs_script)],
                capture_output=True,
                text=True,
                cwd=str(self._workspace_root),
                timeout=120
            )
            
            manifest_path = self._cursor_dir / "docs_manifest.json"
            
            return {
                "success": result.returncode == 0,
                "manifest_path": str(manifest_path),
                "output": result.stdout[:500] if result.stdout else None,
                "error": result.stderr[:500] if result.stderr and result.returncode != 0 else None
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


class MCPProtocolHandler:
    """Handle MCP JSON-RPC protocol."""
    
    def __init__(self, server: RegistryMCPServer):
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
                        "name": "mycosoft-registry",
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
_mcp_server: Optional[RegistryMCPServer] = None


async def get_mcp_server() -> RegistryMCPServer:
    """Get or create the singleton MCP server instance."""
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = RegistryMCPServer()
        await _mcp_server.initialize()
    return _mcp_server


async def run_stdio_server():
    """Run the MCP server over stdio."""
    server = await get_mcp_server()
    handler = MCPProtocolHandler(server)
    
    logger.info("Registry MCP Server started on stdio")
    
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
