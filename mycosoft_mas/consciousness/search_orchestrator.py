"""
MAS Search Orchestrator — canonical unified search pipeline.

Single authoritative orchestration for search: MINDEX -> memory -> worldstate-aware
specialist routing -> CREP/Earth2 -> LLM synthesis -> persistence.

Used by: process_search_query (consciousness), NLQ API, tool_orchestrator, llm_brain live context.

Created: March 14, 2026
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from mycosoft_mas.consciousness.core import MYCAConsciousness

logger = logging.getLogger(__name__)


async def run_unified_search(
    query: str,
    search_context: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    consciousness: Optional["MYCAConsciousness"] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """
    Run the canonical search pipeline: MINDEX -> memory -> specialists -> synthesis.

    Call from consciousness.process_search_query, NLQ execute, or tool_orchestrator.run_search_task.
    """
    search_context = search_context or {}
    focus_summary = query[:200]
    working_context: List[Dict[str, Any]] = []
    world_context: Dict[str, Any] = {}
    memories: List[Dict[str, Any]] = []
    keyword_results: List[Dict[str, Any]] = []
    semantic_results: List[Dict[str, Any]] = []

    # Optional: use consciousness for focus, working/world context, memories
    if consciousness:
        try:
            focus = await consciousness._attention.focus_on(query, "search", search_context)
            focus_summary = focus.summary
            working_context, world_context, memories = await asyncio.gather(
                consciousness._working_memory.load_context(focus, session_id, user_id),
                consciousness._world_model.get_relevant_context(focus),
                consciousness._recall_relevant_memories(query, focus, None, user_id),
                return_exceptions=False,
            )
        except Exception as e:
            logger.warning("Consciousness context for search failed: %s", e)

    # 1. MINDEX + SearchAgent (keyword + semantic)
    try:
        from mycosoft_mas.agents.clusters.search_discovery.search_agent import (
            SearchAgent,
            SearchQuery,
            SearchType,
        )

        search_agent = SearchAgent(agent_id="search-orchestrator")
        kw_q = SearchQuery(query_type=SearchType.KEYWORD, query=query, filters=search_context)
        sem_q = SearchQuery(query_type=SearchType.SEMANTIC, query=query, filters=search_context)
        keyword_results, semantic_results = await asyncio.gather(
            search_agent._keyword_search(kw_q),
            search_agent._semantic_search(sem_q),
            return_exceptions=False,
        )
        if isinstance(keyword_results, Exception):
            logger.warning("Keyword search failed: %s", keyword_results)
            keyword_results = []
        if isinstance(semantic_results, Exception):
            logger.warning("Semantic search failed: %s", semantic_results)
            semantic_results = []
    except Exception as e:
        logger.warning("SearchAgent/MINDEX step failed: %s", e)

    # 2. Memory (semantic_search + recall) if not already filled by consciousness
    if not memories or len(memories) < 3:
        try:
            from mycosoft_mas.memory.coordinator import get_memory_coordinator

            coordinator = await get_memory_coordinator()
            mem_results = await coordinator.semantic_search(query=query, limit=5)
            for r in mem_results:
                memories.append(
                    {
                        "content": r.get("content", str(r)),
                        "source": r.get("source", "memory"),
                        "score": r.get("score", 0.5),
                    }
                )
        except Exception as e:
            logger.debug("Memory semantic search fallback failed: %s", e)

    # 3. Earth Search — planetary-scale search across all 35+ domains (MINDEX-first)
    earth_search_results: List[Dict[str, Any]] = []
    crep_commands: List[Dict[str, Any]] = []
    try:
        from mycosoft_mas.earth_search.models import EarthSearchQuery
        from mycosoft_mas.earth_search.orchestrator import run_earth_search

        earth_query = EarthSearchQuery(
            query=query,
            limit=min(limit, 10),
            include_crep=True,
            user_id=user_id,
            session_id=session_id,
        )
        earth_response = await asyncio.wait_for(run_earth_search(earth_query), timeout=20.0)
        earth_search_results = [r.model_dump(mode="json") for r in earth_response.results]
        crep_commands = earth_response.crep_commands
    except Exception as e:
        logger.warning("Earth Search in unified pipeline failed: %s", e)

    # 4. Specialist routing (CREP/Earth2) — from world_context per WORLDSTATE_VS_SPECIALIST_COMMAND_BOUNDARY
    specialist_results: Dict[str, Any] = {}
    if isinstance(world_context, dict):
        if world_context.get("crep"):
            specialist_results["crep"] = world_context["crep"]
        if world_context.get("predictions"):
            specialist_results["earth2"] = world_context["predictions"]
        if world_context.get("ecosystem"):
            specialist_results["ecosystem"] = world_context["ecosystem"]
        if world_context.get("devices"):
            specialist_results["devices"] = world_context["devices"]
    if earth_search_results:
        specialist_results["earth_search"] = earth_search_results
    if crep_commands:
        specialist_results["crep_commands"] = crep_commands

    result_payload = {
        "query": query,
        "focus": focus_summary,
        "world_context": world_context,
        "working_context": working_context,
        "memories": memories,
        "results": {
            "keyword": keyword_results,
            "semantic": semantic_results,
            "specialist": specialist_results,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Persistence: store in memory for second-search / training (episodic)
    try:
        from mycosoft_mas.memory.coordinator import get_memory_coordinator

        coordinator = await get_memory_coordinator()
        await coordinator.store(
            key=f"search:{session_id or 'anon'}:{datetime.now(timezone.utc).isoformat()}",
            value=result_payload,
            layer="episodic",
        )
    except Exception as e:
        logger.warning("Search result persistence failed: %s", e)

    # Off hot path: persist to MINDEX answer schema and training sinks (fire-and-forget)
    try:
        from mycosoft_mas.consciousness.search_registration import (
            persist_search_to_mindex,
            register_etl_intake_if_live,
            register_training_sink,
        )

        asyncio.create_task(persist_search_to_mindex(query, result_payload, session_id, user_id))
        asyncio.create_task(register_training_sink(query, result_payload))
        asyncio.create_task(register_etl_intake_if_live(query, result_payload))
    except Exception as e:
        logger.debug("Search registration schedule failed: %s", e)

    return result_payload
