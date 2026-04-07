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

from mycosoft_mas.mcp.progress_notifier import emit_progress

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
        self._database_url = database_url or os.getenv("MINDEX_DATABASE_URL")
        if not self._database_url:
            raise ValueError(
                "MINDEX_DATABASE_URL environment variable is required. "
                "Please set it to your PostgreSQL connection string."
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
                        "content": {"type": "string", "description": "The content to remember"},
                        "category": {
                            "type": "string",
                            "description": "Category: preference, fact, context, instruction, or general",
                            "enum": ["preference", "fact", "context", "instruction", "general"],
                        },
                        "importance": {
                            "type": "number",
                            "description": "Importance score from 0.0 to 1.0",
                            "minimum": 0.0,
                            "maximum": 1.0,
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags for categorization",
                        },
                    },
                    "required": ["content"],
                },
            ),
            MCPToolDefinition(
                name="memory_read",
                description="Read a specific memory by its ID.",
                parameters={
                    "type": "object",
                    "properties": {
                        "memory_id": {
                            "type": "string",
                            "description": "The ID of the memory to read",
                        }
                    },
                    "required": ["memory_id"],
                },
            ),
            MCPToolDefinition(
                name="memory_update",
                description="Update an existing memory.",
                parameters={
                    "type": "object",
                    "properties": {
                        "memory_id": {
                            "type": "string",
                            "description": "The ID of the memory to update",
                        },
                        "content": {"type": "string", "description": "New content for the memory"},
                        "importance": {"type": "number", "description": "New importance score"},
                    },
                    "required": ["memory_id"],
                },
            ),
            MCPToolDefinition(
                name="memory_delete",
                description="Delete a memory by its ID.",
                parameters={
                    "type": "object",
                    "properties": {
                        "memory_id": {
                            "type": "string",
                            "description": "The ID of the memory to delete",
                        }
                    },
                    "required": ["memory_id"],
                },
            ),
            MCPToolDefinition(
                name="memory_search",
                description="Search memories by query text.",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "category": {
                            "type": "string",
                            "description": "Filter by category",
                            "enum": ["preference", "fact", "context", "instruction", "general"],
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results to return",
                            "default": 10,
                        },
                    },
                    "required": ["query"],
                },
            ),
            MCPToolDefinition(
                name="memory_list",
                description="List all memories with optional filters.",
                parameters={
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "description": "Filter by category"},
                        "min_importance": {
                            "type": "number",
                            "description": "Minimum importance score",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results to return",
                            "default": 50,
                        },
                    },
                },
            ),
            # =================================================================
            # Palace Navigation Tools (April 7, 2026)
            # =================================================================
            MCPToolDefinition(
                name="palace_status",
                description="Get memory palace overview: wing/room/drawer/tunnel counts.",
                parameters={"type": "object", "properties": {}},
            ),
            MCPToolDefinition(
                name="palace_list_wings",
                description="List all wings (domains) in the memory palace with counts.",
                parameters={"type": "object", "properties": {}},
            ),
            MCPToolDefinition(
                name="palace_list_rooms",
                description="List rooms in a wing.",
                parameters={"type": "object", "properties": {
                    "wing": {"type": "string", "description": "Wing name to list rooms for"},
                }},
            ),
            MCPToolDefinition(
                name="palace_get_taxonomy",
                description="Get full palace taxonomy: wing -> room -> hall hierarchy.",
                parameters={"type": "object", "properties": {}},
            ),
            MCPToolDefinition(
                name="palace_search",
                description="Search memory palace drawers with wing/room/hall filters.",
                parameters={"type": "object", "properties": {
                    "query": {"type": "string", "description": "Search text"},
                    "wing": {"type": "string", "description": "Filter by wing"},
                    "room": {"type": "string", "description": "Filter by room"},
                    "hall": {"type": "string", "description": "Filter by hall (facts/events/discoveries/preferences/advice)"},
                    "limit": {"type": "integer", "description": "Max results", "default": 20},
                }},
            ),
            MCPToolDefinition(
                name="palace_check_duplicate",
                description="Check if content already exists in the palace.",
                parameters={"type": "object", "properties": {
                    "content": {"type": "string", "description": "Content to check"},
                }, "required": ["content"]},
            ),
            MCPToolDefinition(
                name="palace_traverse",
                description="Walk the graph from a wing, showing connected rooms and tunnels.",
                parameters={"type": "object", "properties": {
                    "wing": {"type": "string", "description": "Wing to start traversal from"},
                }, "required": ["wing"]},
            ),
            MCPToolDefinition(
                name="palace_find_tunnels",
                description="Find cross-wing connections (rooms bridging two wings).",
                parameters={"type": "object", "properties": {
                    "wing_a": {"type": "string", "description": "First wing"},
                    "wing_b": {"type": "string", "description": "Second wing (optional)"},
                }, "required": ["wing_a"]},
            ),
            MCPToolDefinition(
                name="palace_file_drawer",
                description="File new content into the palace with spatial classification.",
                parameters={"type": "object", "properties": {
                    "content": {"type": "string", "description": "Content to file"},
                    "wing": {"type": "string", "description": "Wing (auto-detected if omitted)"},
                    "room": {"type": "string", "description": "Room (auto-detected if omitted)"},
                    "hall": {"type": "string", "description": "Hall type", "enum": ["facts", "events", "discoveries", "preferences", "advice"]},
                    "importance": {"type": "number", "description": "Importance 0.0-1.0"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                }, "required": ["content"]},
            ),
            # Knowledge Graph Tools
            MCPToolDefinition(
                name="kg_query",
                description="Query entity relationships with optional temporal filtering (as_of date).",
                parameters={"type": "object", "properties": {
                    "entity": {"type": "string", "description": "Entity name to query"},
                    "as_of": {"type": "string", "description": "ISO date for historical query (optional)"},
                    "limit": {"type": "integer", "default": 20},
                }, "required": ["entity"]},
            ),
            MCPToolDefinition(
                name="kg_add",
                description="Add a temporal fact triple to the knowledge graph.",
                parameters={"type": "object", "properties": {
                    "subject": {"type": "string"},
                    "predicate": {"type": "string"},
                    "object": {"type": "string"},
                    "confidence": {"type": "number", "default": 1.0},
                    "source": {"type": "string", "default": "mcp"},
                }, "required": ["subject", "predicate", "object"]},
            ),
            MCPToolDefinition(
                name="kg_invalidate",
                description="Mark a fact as no longer valid (set end date).",
                parameters={"type": "object", "properties": {
                    "edge_id": {"type": "string", "description": "Edge UUID to invalidate"},
                }, "required": ["edge_id"]},
            ),
            MCPToolDefinition(
                name="kg_timeline",
                description="Get chronological timeline of facts about an entity.",
                parameters={"type": "object", "properties": {
                    "entity": {"type": "string"},
                    "limit": {"type": "integer", "default": 50},
                }, "required": ["entity"]},
            ),
            MCPToolDefinition(
                name="kg_contradictions",
                description="Check if a new fact contradicts existing knowledge.",
                parameters={"type": "object", "properties": {
                    "subject": {"type": "string"},
                    "predicate": {"type": "string"},
                    "object": {"type": "string"},
                }, "required": ["subject", "predicate", "object"]},
            ),
            # Agent Diary Tools
            MCPToolDefinition(
                name="agent_diary_write",
                description="Write an AAAK-compressed diary entry for an agent.",
                parameters={"type": "object", "properties": {
                    "agent_id": {"type": "string", "description": "Agent identifier"},
                    "summary": {"type": "string", "description": "Session summary to compress"},
                    "wing": {"type": "string", "default": "agents"},
                }, "required": ["agent_id", "summary"]},
            ),
            MCPToolDefinition(
                name="agent_diary_read",
                description="Read recent diary entries for an agent.",
                parameters={"type": "object", "properties": {
                    "agent_id": {"type": "string"},
                    "limit": {"type": "integer", "default": 5},
                }, "required": ["agent_id"]},
            ),
            # Context Loading Tools
            MCPToolDefinition(
                name="palace_wake_up",
                description="Load L0+L1 context (~170 tokens) for session initialization.",
                parameters={"type": "object", "properties": {
                    "wing": {"type": "string", "description": "Optional wing focus"},
                }},
            ),
            MCPToolDefinition(
                name="palace_recall",
                description="L2 room-scoped context recall.",
                parameters={"type": "object", "properties": {
                    "wing": {"type": "string"},
                    "room": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                }, "required": ["wing"]},
            ),
            MCPToolDefinition(
                name="palace_deep_search",
                description="L3 deep semantic search across all palace memory.",
                parameters={"type": "object", "properties": {
                    "query": {"type": "string"},
                    "wing": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                }, "required": ["query"]},
            ),
        ]

    async def initialize(self) -> None:
        """Initialize the MCP server."""
        if self._initialized:
            return

        try:
            import asyncpg

            self._pool = await asyncpg.create_pool(self._database_url, min_size=1, max_size=2)
            logger.info("MCP Memory Server connected to database")
        except Exception as e:
            logger.warning(f"Database connection failed: {e}")

        self._initialized = True

    def get_tools(self) -> List[Dict[str, Any]]:
        """Get MCP tool definitions in JSON format."""
        return [
            {"name": tool.name, "description": tool.description, "inputSchema": tool.parameters}
            for tool in self._tools
        ]

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an MCP tool call."""
        handlers = {
            # Original memory tools
            "memory_write": self._handle_write,
            "memory_read": self._handle_read,
            "memory_update": self._handle_update,
            "memory_delete": self._handle_delete,
            "memory_search": self._handle_search,
            "memory_list": self._handle_list,
            # Palace navigation tools
            "palace_status": self._handle_palace_status,
            "palace_list_wings": self._handle_palace_list_wings,
            "palace_list_rooms": self._handle_palace_list_rooms,
            "palace_get_taxonomy": self._handle_palace_get_taxonomy,
            "palace_search": self._handle_palace_search,
            "palace_check_duplicate": self._handle_palace_check_duplicate,
            "palace_traverse": self._handle_palace_traverse,
            "palace_find_tunnels": self._handle_palace_find_tunnels,
            "palace_file_drawer": self._handle_palace_file_drawer,
            # Knowledge graph tools
            "kg_query": self._handle_kg_query,
            "kg_add": self._handle_kg_add,
            "kg_invalidate": self._handle_kg_invalidate,
            "kg_timeline": self._handle_kg_timeline,
            "kg_contradictions": self._handle_kg_contradictions,
            # Agent diary tools
            "agent_diary_write": self._handle_diary_write,
            "agent_diary_read": self._handle_diary_read,
            # Context loading tools
            "palace_wake_up": self._handle_palace_wake_up,
            "palace_recall": self._handle_palace_recall,
            "palace_deep_search": self._handle_palace_deep_search,
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
            "updated_at": now.isoformat(),
        }

        # Store in cache
        self._memory_cache[memory_id] = memory

        # Persist to database
        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO mcp.memories (id, content, category, importance, tags, created_at, updated_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                        memory_id,
                        content,
                        category,
                        importance,
                        tags,
                        now,
                        now,
                    )
            except Exception as e:
                logger.error(f"Failed to persist memory: {e}")

        return {"success": True, "memory_id": memory_id, "message": "Memory stored successfully"}

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
                    row = await conn.fetchrow("SELECT * FROM mcp.memories WHERE id = $1", memory_id)
                    if row:
                        memory = {
                            "id": row["id"],
                            "content": row["content"],
                            "category": row["category"],
                            "importance": row["importance"],
                            "tags": row["tags"] or [],
                            "created_at": row["created_at"].isoformat(),
                            "updated_at": row["updated_at"].isoformat(),
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
                    await conn.execute(
                        """
                        UPDATE mcp.memories 
                        SET content = $1, importance = $2, updated_at = $3
                        WHERE id = $4
                    """,
                        memory["content"],
                        memory["importance"],
                        now,
                        memory_id,
                    )
            except Exception as e:
                logger.error(f"Failed to update memory: {e}")

        return {"success": True, "memory_id": memory_id, "message": "Memory updated successfully"}

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
                    await conn.execute("DELETE FROM mcp.memories WHERE id = $1", memory_id)
            except Exception as e:
                logger.error(f"Failed to delete memory: {e}")

        return {"success": True, "memory_id": memory_id, "message": "Memory deleted successfully"}

    async def _handle_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle memory_search tool call."""
        await emit_progress("memory_search", 0, 2, "Searching memories")
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
                        rows = await conn.fetch(
                            """
                            SELECT * FROM mcp.memories 
                            WHERE content ILIKE $1 AND category = $2
                            ORDER BY importance DESC, created_at DESC
                            LIMIT $3
                        """,
                            f"%{query}%",
                            category,
                            limit,
                        )
                    else:
                        rows = await conn.fetch(
                            """
                            SELECT * FROM mcp.memories 
                            WHERE content ILIKE $1
                            ORDER BY importance DESC, created_at DESC
                            LIMIT $2
                        """,
                            f"%{query}%",
                            limit,
                        )

                    for row in rows:
                        results.append(
                            {
                                "id": row["id"],
                                "content": row["content"],
                                "category": row["category"],
                                "importance": row["importance"],
                                "tags": row["tags"] or [],
                                "created_at": row["created_at"].isoformat(),
                                "updated_at": row["updated_at"].isoformat(),
                            }
                        )
            except Exception as e:
                logger.error(f"Failed to search memories: {e}")

        await emit_progress("memory_search", 2, 2, "Memory search complete")
        # Deduplicate by ID
        seen = set()
        unique = []
        for m in results:
            if m["id"] not in seen:
                seen.add(m["id"])
                unique.append(m)

        return {"query": query, "count": len(unique[:limit]), "memories": unique[:limit]}

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
                        rows = await conn.fetch(
                            """
                            SELECT * FROM mcp.memories 
                            WHERE importance >= $1 AND category = $2
                            ORDER BY importance DESC, created_at DESC
                            LIMIT $3
                        """,
                            min_importance,
                            category,
                            limit,
                        )
                    else:
                        rows = await conn.fetch(
                            """
                            SELECT * FROM mcp.memories 
                            WHERE importance >= $1
                            ORDER BY importance DESC, created_at DESC
                            LIMIT $2
                        """,
                            min_importance,
                            limit,
                        )

                    for row in rows:
                        results.append(
                            {
                                "id": row["id"],
                                "content": row["content"],
                                "category": row["category"],
                                "importance": row["importance"],
                                "tags": row["tags"] or [],
                                "created_at": row["created_at"].isoformat(),
                                "updated_at": row["updated_at"].isoformat(),
                            }
                        )
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

        return {"count": len(unique[:limit]), "memories": unique[:limit]}

    async def get_stats(self) -> Dict[str, Any]:
        """Get server statistics."""
        return {
            "cached_memories": len(self._memory_cache),
            "tools_available": len(self._tools) + 19,  # +19 palace tools
            "database_connected": self._pool is not None,
            "initialized": self._initialized,
        }

    # =========================================================================
    # Palace Tool Handlers (April 7, 2026)
    # =========================================================================

    async def _get_palace_navigator(self):
        """Lazy-load palace navigator."""
        try:
            from mycosoft_mas.memory.palace.navigator import get_palace_navigator
            return await get_palace_navigator()
        except Exception as e:
            logger.error(f"Failed to get palace navigator: {e}")
            return None

    async def _get_retrieval_stack(self):
        """Lazy-load retrieval stack."""
        try:
            from mycosoft_mas.memory.palace.retrieval_stack import get_retrieval_stack
            return await get_retrieval_stack()
        except Exception as e:
            logger.error(f"Failed to get retrieval stack: {e}")
            return None

    async def _handle_palace_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        nav = await self._get_palace_navigator()
        if not nav:
            return {"error": "Palace not initialized"}
        return await nav.get_status()

    async def _handle_palace_list_wings(self, args: Dict[str, Any]) -> Dict[str, Any]:
        nav = await self._get_palace_navigator()
        if not nav:
            return {"error": "Palace not initialized"}
        wings = await nav.list_wings()
        return {"wings": [{"name": w.name, "description": w.description,
                           "source_type": w.source_type.value if hasattr(w.source_type, 'value') else str(w.source_type),
                           "room_count": w.room_count, "drawer_count": w.drawer_count}
                          for w in wings]}

    async def _handle_palace_list_rooms(self, args: Dict[str, Any]) -> Dict[str, Any]:
        nav = await self._get_palace_navigator()
        if not nav:
            return {"error": "Palace not initialized"}
        rooms = await nav.list_rooms(wing_name=args.get("wing"))
        return {"rooms": [{"name": r.name, "wing": r.wing_name,
                           "drawer_count": r.drawer_count, "description": r.description}
                          for r in rooms]}

    async def _handle_palace_get_taxonomy(self, args: Dict[str, Any]) -> Dict[str, Any]:
        nav = await self._get_palace_navigator()
        if not nav:
            return {"error": "Palace not initialized"}
        taxonomy = await nav.get_taxonomy()
        return {"taxonomy": taxonomy.to_dict()}

    async def _handle_palace_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        nav = await self._get_palace_navigator()
        if not nav:
            return {"error": "Palace not initialized"}
        results = await nav.search_drawers(
            query=args.get("query"),
            wing=args.get("wing"),
            room=args.get("room"),
            hall=args.get("hall"),
            limit=args.get("limit", 20),
        )
        return {"results": results, "count": len(results)}

    async def _handle_palace_check_duplicate(self, args: Dict[str, Any]) -> Dict[str, Any]:
        nav = await self._get_palace_navigator()
        if not nav:
            return {"error": "Palace not initialized"}
        content = args.get("content", "")
        result = await nav.check_duplicate(content)
        if result:
            return {"duplicate": True, **result}
        return {"duplicate": False}

    async def _handle_palace_traverse(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Graph traversal — find connected rooms from a starting room."""
        nav = await self._get_palace_navigator()
        if not nav:
            return {"error": "Palace not initialized"}
        wing = args.get("wing", "")
        rooms = await nav.list_rooms(wing_name=wing)
        tunnels = await nav.find_tunnels(wing)
        return {
            "wing": wing,
            "rooms": [{"name": r.name, "drawer_count": r.drawer_count} for r in rooms],
            "tunnels": [{"room": t.room_name, "connects_to": t.wing_b if t.wing_a == wing else t.wing_a}
                        for t in tunnels],
        }

    async def _handle_palace_find_tunnels(self, args: Dict[str, Any]) -> Dict[str, Any]:
        nav = await self._get_palace_navigator()
        if not nav:
            return {"error": "Palace not initialized"}
        tunnels = await nav.find_tunnels(
            wing_a=args.get("wing_a", ""),
            wing_b=args.get("wing_b"),
        )
        return {"tunnels": [{"room": t.room_name, "wing_a": t.wing_a,
                             "wing_b": t.wing_b, "strength": t.strength}
                            for t in tunnels]}

    async def _handle_palace_file_drawer(self, args: Dict[str, Any]) -> Dict[str, Any]:
        nav = await self._get_palace_navigator()
        if not nav:
            return {"error": "Palace not initialized"}
        entry_id = await nav.file_drawer(
            content=args.get("content", ""),
            wing=args.get("wing"),
            room=args.get("room"),
            hall=args.get("hall"),
            importance=args.get("importance", 0.5),
            tags=args.get("tags", []),
            agent_id=args.get("agent_id", "mcp"),
        )
        return {"success": entry_id is not None, "entry_id": str(entry_id) if entry_id else None}

    # Knowledge Graph handlers
    async def _handle_kg_query(self, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            from mycosoft_mas.memory.persistent_graph import get_knowledge_graph
            graph = get_knowledge_graph()
            await graph.initialize()

            entity = args.get("entity", "")
            as_of_str = args.get("as_of")

            if as_of_str:
                from datetime import datetime
                as_of = datetime.fromisoformat(as_of_str)
                return {"facts": await graph.query_as_of(entity, as_of)}
            else:
                return {"facts": await graph.get_timeline(entity, limit=args.get("limit", 20))}
        except Exception as e:
            return {"error": str(e)}

    async def _handle_kg_add(self, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            from mycosoft_mas.memory.persistent_graph import get_knowledge_graph
            graph = get_knowledge_graph()
            await graph.initialize()
            result = await graph.add_fact(
                subject=args.get("subject", ""),
                predicate=args.get("predicate", "related_to"),
                obj=args.get("object", ""),
                confidence=args.get("confidence", 1.0),
                source_file=args.get("source", "mcp"),
            )
            return {"success": True, **result}
        except Exception as e:
            return {"error": str(e)}

    async def _handle_kg_invalidate(self, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            from mycosoft_mas.memory.persistent_graph import get_knowledge_graph
            from uuid import UUID
            graph = get_knowledge_graph()
            await graph.initialize()
            edge_id = UUID(args.get("edge_id", ""))
            success = await graph.invalidate_edge(edge_id)
            return {"success": success}
        except Exception as e:
            return {"error": str(e)}

    async def _handle_kg_timeline(self, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            from mycosoft_mas.memory.persistent_graph import get_knowledge_graph
            graph = get_knowledge_graph()
            await graph.initialize()
            return {"timeline": await graph.get_timeline(
                args.get("entity", ""), limit=args.get("limit", 50)
            )}
        except Exception as e:
            return {"error": str(e)}

    async def _handle_kg_contradictions(self, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            from mycosoft_mas.memory.palace.contradiction_detector import ContradictionDetector
            detector = ContradictionDetector()
            await detector.initialize()
            return await detector.check_and_report(
                subject=args.get("subject", ""),
                predicate=args.get("predicate", ""),
                obj=args.get("object", ""),
            )
        except Exception as e:
            return {"error": str(e)}

    # Agent diary handlers
    async def _handle_diary_write(self, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            from mycosoft_mas.memory.palace.aaak_dialect import AAKEncoder
            from mycosoft_mas.memory.palace.db_pool import get_shared_pool

            encoder = AAKEncoder()
            agent_id = args.get("agent_id", "mcp")
            summary = args.get("summary", "")
            wing = args.get("wing", "agents")

            aaak = encoder.compress(content=summary, wing=wing, room=agent_id, agent_id=agent_id)

            pool = await get_shared_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO mindex.agent_diaries (agent_id, entry_aaak, entry_raw, wing, room)
                    VALUES ($1, $2, $3::jsonb, $4, $5)""",
                    agent_id, aaak, json.dumps({"summary": summary}), wing, agent_id,
                )
            return {"success": True, "aaak": aaak}
        except Exception as e:
            return {"error": str(e)}

    async def _handle_diary_read(self, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            from mycosoft_mas.memory.palace.db_pool import get_shared_pool
            pool = await get_shared_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """SELECT entry_aaak, entry_raw, created_at FROM mindex.agent_diaries
                    WHERE agent_id = $1 ORDER BY created_at DESC LIMIT $2""",
                    args.get("agent_id", "mcp"), args.get("limit", 5),
                )
            return {"entries": [{"aaak": r["entry_aaak"], "raw": r["entry_raw"],
                                 "created_at": r["created_at"].isoformat()} for r in rows]}
        except Exception as e:
            return {"error": str(e)}

    # Context loading handlers
    async def _handle_palace_wake_up(self, args: Dict[str, Any]) -> Dict[str, Any]:
        stack = await self._get_retrieval_stack()
        if not stack:
            return {"error": "Retrieval stack not initialized"}
        context = await stack.wake_up(wing=args.get("wing"))
        return {"context": context, "tokens_estimate": len(context) // 4}

    async def _handle_palace_recall(self, args: Dict[str, Any]) -> Dict[str, Any]:
        stack = await self._get_retrieval_stack()
        if not stack:
            return {"error": "Retrieval stack not initialized"}
        context = await stack.recall(
            wing=args.get("wing", ""),
            room=args.get("room"),
            limit=args.get("limit", 10),
        )
        return {"context": context, "tokens_estimate": len(context) // 4}

    async def _handle_palace_deep_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        stack = await self._get_retrieval_stack()
        if not stack:
            return {"error": "Retrieval stack not initialized"}
        context = await stack.search(
            query=args.get("query", ""),
            wing=args.get("wing"),
            limit=args.get("limit", 10),
        )
        return {"context": context, "tokens_estimate": len(context) // 4}


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
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "mycosoft-memory-server", "version": "1.0.0"},
                },
            }

        elif method == "tools/list":
            return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": self._server.get_tools()}}

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            result = await self._server.call_tool(tool_name, arguments)
            return {"jsonrpc": "2.0", "id": msg_id, "result": result}

        else:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
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
