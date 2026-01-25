"""
MAS v2 Snapshot Manager

Manages agent state snapshots for persistence and recovery.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import aiofiles

from .models import (
    AgentConfig,
    AgentState,
    AgentSnapshot,
)


logger = logging.getLogger("SnapshotManager")


class SnapshotManager:
    """
    Manages agent state snapshots.
    
    Provides methods for:
    - Creating snapshots of agent state
    - Restoring agents from snapshots
    - Listing available snapshots
    - Cleaning up old snapshots
    """
    
    def __init__(self, agent_id: str, snapshot_dir: Optional[str] = None):
        self.agent_id = agent_id
        self.snapshot_dir = Path(snapshot_dir or os.environ.get("SNAPSHOT_DIR", "/app/snapshots"))
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_snapshot(
        self,
        state: AgentState,
        config: AgentConfig,
        reason: str = "manual",
        memory_state: Optional[Dict[str, Any]] = None,
        pending_tasks: Optional[List[Dict[str, Any]]] = None,
    ) -> AgentSnapshot:
        """
        Create a snapshot of agent state.
        
        Args:
            state: Current agent state
            config: Agent configuration
            reason: Reason for snapshot
            memory_state: Optional memory/context state
            pending_tasks: Optional list of pending tasks
            
        Returns:
            Created snapshot
        """
        snapshot = AgentSnapshot(
            agent_id=self.agent_id,
            reason=reason,
            state=state.to_dict(),
            config=config.to_dict(),
            memory_state=memory_state or {},
            pending_tasks=pending_tasks or [],
        )
        
        # Save to file
        filename = f"{self.agent_id}_{snapshot.snapshot_time.strftime('%Y%m%d_%H%M%S')}_{snapshot.id[:8]}.json"
        filepath = self.snapshot_dir / filename
        
        async with aiofiles.open(filepath, "w") as f:
            await f.write(json.dumps(snapshot.to_dict(), indent=2))
        
        logger.info(f"Snapshot created: {filename}")
        
        return snapshot
    
    async def list_snapshots(self, limit: int = 10) -> List[AgentSnapshot]:
        """List available snapshots for this agent"""
        snapshots = []
        
        pattern = f"{self.agent_id}_*.json"
        files = sorted(self.snapshot_dir.glob(pattern), reverse=True)
        
        for filepath in files[:limit]:
            try:
                async with aiofiles.open(filepath, "r") as f:
                    content = await f.read()
                    data = json.loads(content)
                    data["snapshot_time"] = datetime.fromisoformat(data["snapshot_time"])
                    snapshots.append(AgentSnapshot(**data))
            except Exception as e:
                logger.warning(f"Error reading snapshot {filepath}: {e}")
        
        return snapshots
    
    async def get_latest_snapshot(self) -> Optional[AgentSnapshot]:
        """Get the most recent snapshot"""
        snapshots = await self.list_snapshots(limit=1)
        return snapshots[0] if snapshots else None
    
    async def get_snapshot_by_id(self, snapshot_id: str) -> Optional[AgentSnapshot]:
        """Get a specific snapshot by ID"""
        pattern = f"{self.agent_id}_*_{snapshot_id[:8]}.json"
        files = list(self.snapshot_dir.glob(pattern))
        
        if not files:
            return None
        
        async with aiofiles.open(files[0], "r") as f:
            content = await f.read()
            data = json.loads(content)
            data["snapshot_time"] = datetime.fromisoformat(data["snapshot_time"])
            return AgentSnapshot(**data)
    
    async def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a specific snapshot"""
        pattern = f"{self.agent_id}_*_{snapshot_id[:8]}.json"
        files = list(self.snapshot_dir.glob(pattern))
        
        if not files:
            return False
        
        files[0].unlink()
        logger.info(f"Deleted snapshot: {files[0].name}")
        return True
    
    async def cleanup_old_snapshots(self, keep_count: int = 10, max_age_days: int = 7):
        """Clean up old snapshots"""
        pattern = f"{self.agent_id}_*.json"
        files = sorted(self.snapshot_dir.glob(pattern), reverse=True)
        
        now = datetime.utcnow()
        deleted = 0
        
        for i, filepath in enumerate(files):
            # Keep recent snapshots
            if i < keep_count:
                continue
            
            # Check age
            mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
            age_days = (now - mtime).days
            
            if age_days > max_age_days:
                filepath.unlink()
                deleted += 1
        
        if deleted:
            logger.info(f"Cleaned up {deleted} old snapshots")
        
        return deleted
