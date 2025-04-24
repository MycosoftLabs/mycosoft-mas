from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from ..security import get_current_user

router = APIRouter(prefix="/agents", tags=["agents"])

@router.get("/")
async def get_agents(current_user: Dict = Depends(get_current_user)) -> List[Dict[str, Any]]:
    """Get all agents."""
    return []

@router.get("/{agent_id}")
async def get_agent(agent_id: str, current_user: Dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Get agent by ID."""
    return {"id": agent_id, "status": "active"}

@router.post("/{agent_id}/restart")
async def restart_agent(agent_id: str, current_user: Dict = Depends(get_current_user)) -> Dict[str, str]:
    """Restart an agent."""
    return {"status": "success", "message": f"Agent {agent_id} restarted"} 