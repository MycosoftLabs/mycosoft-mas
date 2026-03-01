"""
Graph Memory Agent - Knowledge graph memory.
Phase 1 AGENT_CATALOG implementation. No mock data.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from mycosoft_mas.memory.graph_schema import EdgeType, NodeType
from mycosoft_mas.memory.mindex_graph import get_graph

try:
    from mycosoft_mas.agents.base_agent import BaseAgent
except Exception:
    BaseAgent = object  # type: ignore[misc, assignment]

logger = logging.getLogger(__name__)


def _parse_node_type(value: Optional[str]) -> NodeType:
    if not value:
        return NodeType.ENTITY
    try:
        return NodeType(value)
    except Exception:
        return NodeType.ENTITY


def _parse_edge_type(value: Optional[str]) -> EdgeType:
    if not value:
        return EdgeType.RELATED_TO
    try:
        return EdgeType(value)
    except Exception:
        return EdgeType.RELATED_TO


class GraphMemoryAgent(BaseAgent if BaseAgent is not object else object):  # type: ignore[misc]
    """Knowledge graph memory operations."""

    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        if BaseAgent is not object:
            super().__init__(agent_id=agent_id, name=name, config=config or {})
        else:
            self.agent_id = agent_id
            self.name = name
            self.config = config or {}
        self.capabilities = ["graph", "node", "edge", "query"]

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process graph memory task."""
        task_type = task.get("type", "")
        if task_type == "continuous_cycle":
            return {"status": "success", "result": {"cycle": "idle"}}
        graph = await get_graph()
        if task_type == "add_node":
            name = str(task.get("name", "")).strip()
            if not name:
                return {"status": "error", "error": "name_required"}
            node = await graph.create_node(
                node_type=_parse_node_type(task.get("node_type")),
                name=name,
                description=task.get("description"),
                properties=task.get("properties") or {},
                embedding=task.get("embedding"),
                source=task.get("source"),
                confidence=float(task.get("confidence", 1.0)),
                importance=float(task.get("importance", 0.5)),
            )
            return {"status": "success", "result": {"node": node}}
        if task_type == "add_edge":
            source_id = str(task.get("source_id", "")).strip()
            target_id = str(task.get("target_id", "")).strip()
            if not source_id or not target_id:
                return {"status": "error", "error": "source_target_required"}
            edge = await graph.create_edge(
                source_id=source_id,
                target_id=target_id,
                edge_type=_parse_edge_type(task.get("edge_type")),
                properties=task.get("properties") or {},
                weight=float(task.get("weight", 1.0)),
                is_bidirectional=bool(task.get("is_bidirectional", False)),
            )
            return {"status": "success", "result": {"edge": edge}}
        if task_type == "get_node":
            node = await graph.get_node(task.get("node_id", ""))
            return {"status": "success", "result": {"node": node}}
        if task_type == "find_nodes":
            nodes = await graph.find_nodes(
                node_type=_parse_node_type(task.get("node_type")) if task.get("node_type") else None,
                name_contains=task.get("name_contains"),
                properties_filter=task.get("properties_filter"),
                limit=int(task.get("limit", 50)),
            )
            return {"status": "success", "result": {"nodes": nodes}}
        if task_type == "get_edges":
            edges = await graph.get_edges(
                source_id=task.get("source_id"),
                target_id=task.get("target_id"),
                edge_type=_parse_edge_type(task.get("edge_type")) if task.get("edge_type") else None,
            )
            return {"status": "success", "result": {"edges": edges}}
        if task_type == "get_neighbors":
            traversal = await graph.get_neighbors(
                node_id=task.get("node_id", ""),
                edge_type=_parse_edge_type(task.get("edge_type")) if task.get("edge_type") else None,
                direction=task.get("direction", "both"),
                max_depth=int(task.get("max_depth", 1)),
            )
            return {"status": "success", "result": {"traversal": traversal}}
        if task_type == "semantic_search":
            embedding: Optional[List[float]] = task.get("embedding")
            if not embedding:
                return {"status": "error", "error": "embedding_required"}
            results = await graph.semantic_search(
                embedding=embedding,
                node_type=_parse_node_type(task.get("node_type")) if task.get("node_type") else None,
                limit=int(task.get("limit", 10)),
                min_similarity=float(task.get("min_similarity", 0.5)),
            )
            return {"status": "success", "result": {"results": results}}
        return {"status": "success", "result": {}}

    async def run_cycle(self) -> Dict[str, Any]:
        return {
            "tasks_processed": 0,
            "insights_generated": 0,
            "knowledge_added": 0,
            "summary": "GraphMemoryAgent idle cycle complete",
        }
