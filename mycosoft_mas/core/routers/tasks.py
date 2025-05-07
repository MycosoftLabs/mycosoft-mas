from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from ..security import get_current_user

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("/")
async def get_tasks(current_user: Dict = Depends(get_current_user)) -> List[Dict[str, Any]]:
    """Get all tasks."""
    return []

@router.get("/{task_id}")
async def get_task(task_id: str, current_user: Dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Get task by ID."""
    return {"id": task_id, "status": "running"}

@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str, current_user: Dict = Depends(get_current_user)) -> Dict[str, str]:
    """Cancel a task."""
    return {"status": "success", "message": f"Task {task_id} cancelled"} 