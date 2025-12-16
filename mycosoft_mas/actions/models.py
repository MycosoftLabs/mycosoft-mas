from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum

class ActionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"

class ActionType(str, Enum):
    TOOL_USE = "tool_use"
    API_CALL = "api_call"
    DB_WRITE = "db_write"
    FILE_WRITE = "file_write"
    SYSTEM_CMD = "system_cmd"

class Action(BaseModel):
    id: str = Field(..., description="Unique action ID")
    agent_id: str
    action_type: ActionType
    tool_name: Optional[str] = None
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]] = None
    status: ActionStatus = ActionStatus.PENDING
    timestamp: datetime = Field(default_factory=datetime.now)
    error: Optional[str] = None
    approval_required: bool = False
    approved_by: Optional[str] = None
