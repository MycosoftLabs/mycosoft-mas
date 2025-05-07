from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from ..security import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/")
async def get_dashboard_data(current_user: Dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Get dashboard data."""
    return {
        "metrics": {
            "agent_count": 0,
            "task_count": 0,
            "error_count": 0,
            "api_calls": 0,
            "cpu_usage": 0,
            "memory_usage": 0,
            "last_update": 0,
            "performance_data": {
                "labels": [],
                "cpu": [],
                "memory": []
            }
        }
    }

@router.get("/health")
async def get_system_health(current_user: Dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Get system health data."""
    return {
        "status": "healthy",
        "uptime": "0d 0h 0m",
        "system_health": 100,
        "active_agents": 0,
        "total_agents": 0
    } 