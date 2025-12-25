"""
Agent Registry API Router

Exposes the agent registry for MYCA voice control and n8n integration.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..agent_registry import get_agent_registry, AgentCategory

router = APIRouter(prefix="/agents/registry", tags=["agent-registry"])


class AgentSearchRequest(BaseModel):
    """Request model for agent search."""
    query: str
    category: Optional[str] = None


class VoiceRouteRequest(BaseModel):
    """Request model for voice routing."""
    transcript: str
    actor: str = "morgan"
    session_id: Optional[str] = None


class VoiceRouteResponse(BaseModel):
    """Response model for voice routing."""
    matched_agents: List[Dict[str, Any]]
    primary_agent: Optional[Dict[str, Any]]
    requires_confirmation: bool
    routing_prompt: str


@router.get("/")
async def list_all_agents():
    """
    List all registered agents in the MAS.
    
    Returns the complete agent registry with categories and capabilities.
    """
    registry = get_agent_registry()
    return registry.to_dict()


@router.get("/categories")
async def list_categories():
    """List all agent categories."""
    return {
        "categories": [
            {"id": c.value, "name": c.name.title()}
            for c in AgentCategory
        ]
    }


@router.get("/category/{category}")
async def list_agents_by_category(category: str):
    """List agents in a specific category."""
    registry = get_agent_registry()
    try:
        cat = AgentCategory(category)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
    
    agents = registry.list_by_category(cat)
    return {
        "category": category,
        "agents": [
            {
                "agent_id": a.agent_id,
                "name": a.name,
                "display_name": a.display_name,
                "description": a.description,
                "capabilities": [c.value for c in a.capabilities],
                "is_active": a.is_active,
            }
            for a in agents
        ],
        "count": len(agents),
    }


@router.get("/agent/{agent_id}")
async def get_agent_details(agent_id: str):
    """Get detailed information about a specific agent."""
    registry = get_agent_registry()
    agent = registry.get(agent_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    
    return {
        "agent_id": agent.agent_id,
        "name": agent.name,
        "display_name": agent.display_name,
        "description": agent.description,
        "category": agent.category.value,
        "capabilities": [c.value for c in agent.capabilities],
        "module_path": agent.module_path,
        "class_name": agent.class_name,
        "keywords": agent.keywords,
        "voice_triggers": agent.voice_triggers,
        "requires_confirmation": agent.requires_confirmation,
        "is_active": agent.is_active,
        "config_key": agent.config_key,
    }


@router.get("/search")
async def search_agents(q: str = Query(..., description="Search query")):
    """
    Search agents by keyword.
    
    Searches agent names, descriptions, and keywords.
    """
    registry = get_agent_registry()
    agents = registry.find_by_keyword(q)
    
    return {
        "query": q,
        "results": [
            {
                "agent_id": a.agent_id,
                "name": a.name,
                "display_name": a.display_name,
                "description": a.description,
                "category": a.category.value,
                "is_active": a.is_active,
            }
            for a in agents
        ],
        "count": len(agents),
    }


@router.post("/route/voice")
async def route_voice_command(request: VoiceRouteRequest):
    """
    Route a voice command to the appropriate agent(s).
    
    Analyzes the transcript and returns matching agents based on voice triggers.
    """
    registry = get_agent_registry()
    
    # Find agents matching the voice transcript
    matches = registry.find_by_voice_trigger(request.transcript)
    
    # Also search by keywords in transcript
    words = request.transcript.lower().split()
    for word in words:
        if len(word) > 3:  # Skip short words
            keyword_matches = registry.find_by_keyword(word)
            for match in keyword_matches:
                if match not in matches:
                    matches.append(match)
    
    # Determine primary agent (first match, prefer active)
    primary = None
    if matches:
        active_matches = [m for m in matches if m.is_active]
        primary = active_matches[0] if active_matches else matches[0]
    
    # Check if confirmation is required
    requires_confirmation = primary.requires_confirmation if primary else False
    
    # Generate routing prompt
    if primary:
        routing_prompt = f"Routing to {primary.display_name}"
        if requires_confirmation:
            routing_prompt += ". This action requires confirmation."
    else:
        routing_prompt = "No specific agent matched. I'll handle this directly."
    
    return VoiceRouteResponse(
        matched_agents=[
            {
                "agent_id": a.agent_id,
                "display_name": a.display_name,
                "category": a.category.value,
                "is_active": a.is_active,
                "requires_confirmation": a.requires_confirmation,
            }
            for a in matches[:5]  # Limit to top 5
        ],
        primary_agent={
            "agent_id": primary.agent_id,
            "name": primary.name,
            "display_name": primary.display_name,
            "description": primary.description,
            "category": primary.category.value,
            "requires_confirmation": primary.requires_confirmation,
        } if primary else None,
        requires_confirmation=requires_confirmation,
        routing_prompt=routing_prompt,
    )


@router.get("/voice/prompt")
async def get_voice_routing_prompt():
    """
    Get the voice routing prompt for LLM context.
    
    Returns a formatted prompt listing all agents and their voice triggers,
    suitable for injection into the orchestrator's system prompt.
    """
    registry = get_agent_registry()
    return {
        "prompt": registry.get_voice_routing_prompt(),
        "total_agents": len(registry.list_all()),
        "active_agents": len(registry.list_active()),
    }


@router.post("/activate/{agent_id}")
async def activate_agent(agent_id: str):
    """Mark an agent as active in the registry."""
    registry = get_agent_registry()
    agent = registry.get(agent_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    
    registry.mark_active(agent_id, True)
    return {"status": "activated", "agent_id": agent_id}


@router.post("/deactivate/{agent_id}")
async def deactivate_agent(agent_id: str):
    """Mark an agent as inactive in the registry."""
    registry = get_agent_registry()
    agent = registry.get(agent_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    
    registry.mark_active(agent_id, False)
    return {"status": "deactivated", "agent_id": agent_id}


@router.get("/n8n/registry")
async def get_n8n_registry():
    """
    Get the agent registry in n8n-compatible format.
    
    Returns a simplified registry for n8n workflow integration.
    """
    registry = get_agent_registry()
    
    return {
        "agents": [
            {
                "id": a.agent_id,
                "name": a.display_name,
                "category": a.category.value,
                "triggers": a.voice_triggers,
                "confirm": a.requires_confirmation,
                "active": a.is_active,
            }
            for a in registry.list_all()
        ],
        "categories": [c.value for c in AgentCategory],
    }



