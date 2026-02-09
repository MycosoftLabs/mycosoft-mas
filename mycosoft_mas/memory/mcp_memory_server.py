"""
MCP Memory Server for Claude Integration.
Created: February 5, 2026

Implements Model Context Protocol (MCP) server for memory operations:
- Write: Store new memories
- Read: Retrieve memories by ID or search
- Update: Modify existing memories
- Delete: Remove memories

Designed for use with Claude and other MCP-compatible AI assistants.
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger("MCPMemoryServer")


@dataclass
class MCPToolDefinition:
    """Definition of an MCP tool."""
    name: str
    description: str
    parameters: Dict[str, Any]


class MCPMemoryServer:
    """
    MCP Memory Server providing CRUD operations for AI memory.
    
    Tools:
    - memory_write: Store a new memory
    - memory_read: Read memories by ID or query
    - memory_update: Update an existing memory
    - memory_delete: Delete a memory
    - memory_search: Semantic search across memories
    - memory_list: List all memories with filters
    """
    
    def __init__(self, database_url: Optional[str] = None):
        self._database_url = database_url or os.getenv(
            "MINDEX_DATABASE_URL",
            "postgresql://mycosoft:Mushroom1!Mushroom1!@192.168.0.189:5432/mindex"
        )
        self._pool = None
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._initialized = False
        
        # Tool definitions for MCP
        self._tools = self._define_tools()
    
    def _define_tools(self) -> List[MCPToolDefinition]:
        """Define MCP tool specifications."""
        return [
            MCPToolDefinition(
                name="memory_write",
                description="Store a new memory. Use this to remember important information for future conversations.",
                parameters={
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "The content to remember"
                        },
                        "category": {
                            "type": "string",
                            "description": "Category: preference, fact, context, instruction, or general",
                            "enum": ["preference", "fact", "context", "instruction", "general"]
                        },
                        "importance": {
                            "type": "number",
                            "description": "Importance score from 0.0 to 1.0",
                            "minimum": 0.0,
                            "maximum": 1.0
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags for categorization"
                        }
                    },
                    "required": ["content"]
                }
            ),
            MCPToolDefinition(
                name="memory_read",
                description="Read a specific memory by its ID.",
                parameters={
                    "type": "object",
                    "properties": {
                        "memory_id": {
                            "type": "string",
                            "description": "The ID of the memory to read"
                        }
                    },
                    "required": ["memory_id"]
                }
            ),
            MCPToolDefinition(
                name="memory_update",
                description="Update an existing memory.",
                parameters={
                    "type": "object",
                    "properties": {
                        "memory_id": {
                            "type": "string",
                            "description": "The ID of the memory to update"
                        },
                        "content": {
                            "type": "string",
                            "description": "New content for the memory"
                        },
                        "importance": {
                            "type": "number",
                            "description": "New importance score"
                        }
                    },
                    "required": ["memory_id"]
                }
            ),
            MCPToolDefinition(
                name="memory_delete",
                description="Delete a memory by its ID.",
                parameters={
                    "type": "object",
                    "properties": {
                        "memory_id": {
                            "type": "string",
                            "description": "The ID of the memory to delete"
                        }
                    },
                    "required": ["memory_id"]
                }
            ),
            MCPToolDefinition(
                name="memory_search",
                description="Search memories by query text.",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "category": {
                            "type": "string",
                            "description": "Filter by category",
                            "enum": ["preference", "fact", "context", "instruction", "general"]
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results to return",
                            "default": 10
                        }
                    },
                    "required": ["query"]
                }
            ),
            MCPToolDefinition(
                name="memory_list",
                description="List all memories with optional filters.",
                parameters={
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Filter by category"
                        },
                        "min_importance": {
                            "type": "number",
                            "description": "Minimum importance score"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results to return",
                            "default": 50
                        }
                    }
                }
            )
        ]
    
    async def initialize(self) -> None:
        """Initialize the MCP server."""
        if self._initialized:
            return
        
        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(
                self._database_url,
                min_size=1,
                max_size=5
            )
            logger.info("MCP Memory Server connected to database")
        except Exception as e:
            logger.warning(f"Database connection failed: {e}")
        
        self._initialized = True
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get MCP tool definitions in JSON format."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.parameters
            }
            for tool in self._tools
        ]
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an MCP tool call."""
        handlers = {
            "memory_write": self._handle_write,
            "memory_read": self._handle_read,
            "memory_update": self._handle_update,
            "memory_delete": self._handle_delete,
            "memory_search": self._handle_search,
            "memory_list": self._handle_list
        }
        
        handler = handlers.get(tool_name)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}"}
        
        try:
            result = await handler(arguments)
            return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            return {"error": str(e)}
    
    async def _handle_write(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle memory_write tool call."""
        content = args.get("content", "")
        category = args.get("category", "general")
        importance = args.get("importance", 0.5)
        tags = args.get("tags", [])
        
        memory_id = str(uuid4())
        now = datetime.now(timezone.utc)
        
        memory = {
            "id": memory_id,
            "content": content,
            "category": category,
            "importance": importance,
            "tags": tags,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        # Store in cache
        self._memory_cache[memory_id] = memory
        
        # Persist to database
        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO mcp.memories (id, content, category, importance, tags, created_at, updated_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """, memory_id, content, category, importance, tags, now, now)
            except Exception as e:
                logger.error(f"Failed to persist memory: {e}")
        
        return {
            "success": True,
            "memory_id": memory_id,
            "message": f"Memory stored successfully"
        }
    
    async def _handle_read(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle memory_read tool call."""
        memory_id = args.get("memory_id")
        
        if not memory_id:
            return {"error": "memory_id is required"}
        
        # Check cache first
        if memory_id in self._memory_cache:
            return {"memory": self._memory_cache[memory_id]}
        
        # Check database
        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    row = await conn.fetchrow(
                        "SELECT * FROM mcp.memories WHERE id = $1", memory_id
                    )
                    if row:
                        memory = {
                            "id": row["id"],
                            "content": row["content"],
                            "category": row["category"],
                            "importance": row["importance"],
                            "tags": row["tags"] or [],
                            "created_at": row["created_at"].isoformat(),
                            "updated_at": row["updated_at"].isoformat()
                        }
                        self._memory_cache[memory_id] = memory
                        return {"memory": memory}
            except Exception as e:
                logger.error(f"Failed to read memory: {e}")
        
        return {"error": f"Memory {memory_id} not found"}
    
    async def _handle_update(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle memory_update tool call."""
        memory_id = args.get("memory_id")
        
        if not memory_id:
            return {"error": "memory_id is required"}
        
        # Get existing memory
        existing = await self._handle_read({"memory_id": memory_id})
        if "error" in existing:
            return existing
        
        memory = existing["memory"]
        now = datetime.now(timezone.utc)
        
        # Update fields
        if "content" in args:
            memory["content"] = args["content"]
        if "importance" in args:
            memory["importance"] = args["importance"]
        memory["updated_at"] = now.isoformat()
        
        # Update cache
        self._memory_cache[memory_id] = memory
        
        # Update database
        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE mcp.memories 
                        SET content = $1, importance = $2, updated_at = $3
                        WHERE id = $4
                    """, memory["content"], memory["importance"], now, memory_id)
            except Exception as e:
                logger.error(f"Failed to update memory: {e}")
        
        return {
            "success": True,
            "memory_id": memory_id,
            "message": "Memory updated successfully"
        }
    
    async def _handle_delete(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle memory_delete tool call."""
        memory_id = args.get("memory_id")
        
        if not memory_id:
            return {"error": "memory_id is required"}
        
        # Remove from cache
        if memory_id in self._memory_cache:
            del self._memory_cache[memory_id]
        
        # Remove from database
        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    result = await conn.execute(
                        "DELETE FROM mcp.memories WHERE id = $1", memory_id
                    )
            except Exception as e:
                logger.error(f"Failed to delete memory: {e}")
        
        return {
            "success": True,
            "memory_id": memory_id,
            "message": "Memory deleted successfully"
        }
    
    async def _handle_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle memory_search tool call."""
        query = args.get("query", "")
        category = args.get("category")
        limit = args.get("limit", 10)
        
        results = []
        
        # Search cache
        query_lower = query.lower()
        for memory in self._memory_cache.values():
            if query_lower in memory["content"].lower():
                if category is None or memory["category"] == category:
                    results.append(memory)
        
        # Search database
        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    if category:
                        rows = await conn.fetch("""
                            SELECT * FROM mcp.memories 
                            WHERE content ILIKE $1 AND category = $2
                            ORDER BY importance DESC, created_at DESC
                            LIMIT $3
                        """, f"%{query}%", category, limit)
                    else:
                        rows = await conn.fetch("""
                            SELECT * FROM mcp.memories 
                            WHERE content ILIKE $1
                            ORDER BY importance DESC, created_at DESC
                            LIMIT $2
                        """, f"%{query}%", limit)
                    
                    for row in rows:
                        results.append({
                            "id": row["id"],
                            "content": row["content"],
                            "category": row["category"],
                            "importance": row["importance"],
                            "tags": row["tags"] or [],
                            "created_at": row["created_at"].isoformat(),
                            "updated_at": row["updated_at"].isoformat()
                        })
            except Exception as e:
                logger.error(f"Failed to search memories: {e}")
        
        # Deduplicate by ID
        seen = set()
        unique = []
        for m in results:
            if m["id"] not in seen:
                seen.add(m["id"])
                unique.append(m)
        
        return {
            "query": query,
            "count": len(unique[:limit]),
            "memories": unique[:limit]
        }
    
    async def _handle_list(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle memory_list tool call."""
        category = args.get("category")
        min_importance = args.get("min_importance", 0.0)
        limit = args.get("limit", 50)
        
        results = []
        
        # Get from cache
        for memory in self._memory_cache.values():
            if memory["importance"] >= min_importance:
                if category is None or memory["category"] == category:
                    results.append(memory)
        
        # Get from database
        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    if category:
                        rows = await conn.fetch("""
                            SELECT * FROM mcp.memories 
                            WHERE importance >= $1 AND category = $2
                            ORDER BY importance DESC, created_at DESC
                            LIMIT $3
                        """, min_importance, category, limit)
                    else:
                        rows = await conn.fetch("""
                            SELECT * FROM mcp.memories 
                            WHERE importance >= $1
                            ORDER BY importance DESC, created_at DESC
                            LIMIT $2
                        """, min_importance, limit)
                    
                    for row in rows:
                        results.append({
                            "id": row["id"],
                            "content": row["content"],
                            "category": row["category"],
                            "importance": row["importance"],
                            "tags": row["tags"] or [],
                            "created_at": row["created_at"].isoformat(),
                            "updated_at": row["updated_at"].isoformat()
                        })
            except Exception as e:
                logger.error(f"Failed to list memories: {e}")
        
        # Deduplicate
        seen = set()
        unique = []
        for m in results:
            if m["id"] not in seen:
                seen.add(m["id"])
                unique.append(m)
        
        # Sort by importance
        unique.sort(key=lambda x: (x["importance"], x["created_at"]), reverse=True)
        
        return {
            "count": len(unique[:limit]),
            "memories": unique[:limit]
        }
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get server statistics."""
        return {
            "cached_memories": len(self._memory_cache),
            "tools_available": len(self._tools),
            "database_connected": self._pool is not None,
            "initialized": self._initialized
        }


# MCP Protocol Handler
class MCPProtocolHandler:
    """Handles MCP protocol messages over stdio or websocket."""
    
    def __init__(self, server: MCPMemoryServer):
        self._server = server
    
    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an incoming MCP message."""
        method = message.get("method")
        params = message.get("params", {})
        msg_id = message.get("id")
        
        if method == "initialize":
            await self._server.initialize()
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "mycosoft-memory-server",
                        "version": "1.0.0"
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
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            result = await self._server.call_tool(tool_name, arguments)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": result
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
_mcp_server: Optional[MCPMemoryServer] = None


async def get_mcp_server() -> MCPMemoryServer:
    """Get or create the singleton MCP server instance."""
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = MCPMemoryServer()
        await _mcp_server.initialize()
    return _mcp_server


# Main entry point for stdio MCP server
async def run_stdio_server():
    """Run the MCP server over stdio."""
    import sys
    
    server = await get_mcp_server()
    handler = MCPProtocolHandler(server)
    
    logger.info("MCP Memory Server started on stdio")
    
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
    asyncio.run(run_stdio_server())
