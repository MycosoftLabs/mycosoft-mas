"""Offline Mode Support. Created: February 3, 2026"""
from typing import Any, Dict, List
from datetime import datetime, timezone

class OfflineMode:
    """Manages offline operation and data queuing."""
    
    def __init__(self):
        self.is_offline = False
        self._pending_operations: List[Dict[str, Any]] = []
    
    def go_offline(self) -> None:
        self.is_offline = True
    
    def go_online(self) -> None:
        self.is_offline = False
    
    def queue_operation(self, operation_type: str, data: Dict[str, Any]) -> int:
        self._pending_operations.append({"type": operation_type, "data": data, "queued_at": datetime.now(timezone.utc).isoformat()})
        return len(self._pending_operations)
    
    async def sync_pending(self) -> Dict[str, Any]:
        synced = len(self._pending_operations)
        self._pending_operations.clear()
        return {"synced": synced, "remaining": 0}
    
    def get_pending_count(self) -> int:
        return len(self._pending_operations)
