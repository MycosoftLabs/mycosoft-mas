"""
Change Detector for MYCA System Awareness.
Created: February 5, 2026

Detects and tracks changes across the Mycosoft ecosystem:
- Code deployments (Git commits, Docker image updates)
- API changes (new endpoints, schema changes)
- Service health changes (status transitions)
- Configuration changes
- Registry updates

Enables MYCA to stay informed about system evolution.
"""

import asyncio
import hashlib
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import UUID, uuid4

logger = logging.getLogger("ChangeDetector")


class ChangeType(str, Enum):
    """Types of changes that can be detected."""
    DEPLOYMENT = "deployment"      # Code/container deployment
    API_CHANGE = "api_change"      # API endpoint or schema change
    HEALTH_CHANGE = "health_change" # Service health status change
    CONFIG_CHANGE = "config_change" # Configuration change
    REGISTRY_UPDATE = "registry_update"  # Registry entry added/modified
    SCHEMA_CHANGE = "schema_change"  # Database schema change
    AGENT_STATUS = "agent_status"   # Agent status change
    DEVICE_STATUS = "device_status" # Device status change


class ChangeSeverity(str, Enum):
    """Severity levels for changes."""
    INFO = "info"          # Informational
    LOW = "low"            # Minor change
    MEDIUM = "medium"      # Moderate change
    HIGH = "high"          # Significant change
    CRITICAL = "critical"  # Critical change requiring attention


@dataclass
class DetectedChange:
    """A detected change in the system."""
    id: UUID
    change_type: ChangeType
    severity: ChangeSeverity
    source: str             # What system/component changed
    description: str        # Human-readable description
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "change_type": self.change_type.value,
            "severity": self.severity.value,
            "source": self.source,
            "description": self.description,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "detected_at": self.detected_at.isoformat(),
            "metadata": self.metadata,
            "acknowledged": self.acknowledged
        }


@dataclass
class Snapshot:
    """A snapshot of system state for comparison."""
    snapshot_id: UUID
    source: str
    data_hash: str
    data: Dict[str, Any]
    taken_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ChangeDetector:
    """
    Detects changes across the Mycosoft ecosystem.
    
    Monitors:
    - Git repository for new commits
    - Docker containers for image updates
    - API endpoints for changes
    - Service health for status transitions
    - Registry for new/modified entries
    """
    
    def __init__(self, database_url: Optional[str] = None):
        self._database_url = database_url or os.getenv(
            "MINDEX_DATABASE_URL",
            "postgresql://mycosoft:REDACTED_VM_SSH_PASSWORD@192.168.0.189:5432/mindex"
        )
        self._pool = None
        self._snapshots: Dict[str, Snapshot] = {}
        self._changes: List[DetectedChange] = []
        self._listeners: List[Callable[[DetectedChange], None]] = []
        self._detection_task: Optional[asyncio.Task] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the change detector."""
        if self._initialized:
            return
        
        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(
                self._database_url,
                min_size=1,
                max_size=3
            )
        except Exception as e:
            logger.warning(f"Database connection failed: {e}")
        
        # Take initial snapshots
        await self._take_initial_snapshots()
        
        self._initialized = True
        logger.info("Change detector initialized")
    
    async def _take_initial_snapshots(self) -> None:
        """Take initial snapshots of system state."""
        # Registry snapshots
        await self._snapshot_registry("systems")
        await self._snapshot_registry("agents")
        await self._snapshot_registry("devices")
        
        # Git snapshot
        await self._snapshot_git()
    
    def _hash_data(self, data: Any) -> str:
        """Create hash of data for comparison."""
        import json
        content = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()
    
    async def _snapshot_registry(self, table: str) -> Optional[Snapshot]:
        """Take snapshot of a registry table."""
        if not self._pool:
            return None
        
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(f"SELECT * FROM registry.{table} ORDER BY name")
                
                data = [dict(row) for row in rows]
                # Convert datetime to string
                for row in data:
                    for k, v in row.items():
                        if isinstance(v, datetime):
                            row[k] = v.isoformat()
                
                snapshot = Snapshot(
                    snapshot_id=uuid4(),
                    source=f"registry.{table}",
                    data_hash=self._hash_data(data),
                    data={"rows": data, "count": len(data)}
                )
                
                self._snapshots[f"registry.{table}"] = snapshot
                return snapshot
        except Exception as e:
            logger.warning(f"Failed to snapshot {table}: {e}")
            return None
    
    async def _snapshot_git(self) -> Optional[Snapshot]:
        """Take snapshot of Git repository state."""
        try:
            import subprocess
            
            # Get current commit
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=os.getcwd()
            )
            current_commit = result.stdout.strip() if result.returncode == 0 else None
            
            # Get branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                cwd=os.getcwd()
            )
            current_branch = result.stdout.strip() if result.returncode == 0 else None
            
            data = {
                "commit": current_commit,
                "branch": current_branch
            }
            
            snapshot = Snapshot(
                snapshot_id=uuid4(),
                source="git",
                data_hash=self._hash_data(data),
                data=data
            )
            
            self._snapshots["git"] = snapshot
            return snapshot
        except Exception as e:
            logger.warning(f"Failed to snapshot git: {e}")
            return None
    
    async def detect_registry_changes(self, table: str) -> List[DetectedChange]:
        """Detect changes in a registry table."""
        changes = []
        old_snapshot = self._snapshots.get(f"registry.{table}")
        new_snapshot = await self._snapshot_registry(table)
        
        if not old_snapshot or not new_snapshot:
            return changes
        
        if old_snapshot.data_hash != new_snapshot.data_hash:
            old_rows = {r["name"]: r for r in old_snapshot.data.get("rows", [])}
            new_rows = {r["name"]: r for r in new_snapshot.data.get("rows", [])}
            
            # Detect additions
            for name in set(new_rows.keys()) - set(old_rows.keys()):
                change = DetectedChange(
                    id=uuid4(),
                    change_type=ChangeType.REGISTRY_UPDATE,
                    severity=ChangeSeverity.MEDIUM,
                    source=f"registry.{table}",
                    description=f"New {table[:-1]} added: {name}",
                    new_value=new_rows[name]
                )
                changes.append(change)
                self._emit_change(change)
            
            # Detect removals
            for name in set(old_rows.keys()) - set(new_rows.keys()):
                change = DetectedChange(
                    id=uuid4(),
                    change_type=ChangeType.REGISTRY_UPDATE,
                    severity=ChangeSeverity.HIGH,
                    source=f"registry.{table}",
                    description=f"{table[:-1].capitalize()} removed: {name}",
                    old_value=old_rows[name]
                )
                changes.append(change)
                self._emit_change(change)
            
            # Detect modifications
            for name in set(old_rows.keys()) & set(new_rows.keys()):
                if self._hash_data(old_rows[name]) != self._hash_data(new_rows[name]):
                    change = DetectedChange(
                        id=uuid4(),
                        change_type=ChangeType.REGISTRY_UPDATE,
                        severity=ChangeSeverity.LOW,
                        source=f"registry.{table}",
                        description=f"{table[:-1].capitalize()} modified: {name}",
                        old_value=old_rows[name],
                        new_value=new_rows[name]
                    )
                    changes.append(change)
                    self._emit_change(change)
        
        return changes
    
    async def detect_git_changes(self) -> List[DetectedChange]:
        """Detect Git repository changes."""
        changes = []
        old_snapshot = self._snapshots.get("git")
        new_snapshot = await self._snapshot_git()
        
        if not old_snapshot or not new_snapshot:
            return changes
        
        old_commit = old_snapshot.data.get("commit")
        new_commit = new_snapshot.data.get("commit")
        
        if old_commit != new_commit:
            change = DetectedChange(
                id=uuid4(),
                change_type=ChangeType.DEPLOYMENT,
                severity=ChangeSeverity.MEDIUM,
                source="git",
                description=f"New commit deployed",
                old_value=old_commit,
                new_value=new_commit,
                metadata={
                    "branch": new_snapshot.data.get("branch")
                }
            )
            changes.append(change)
            self._emit_change(change)
        
        return changes
    
    async def detect_health_changes(
        self,
        current_health: Dict[str, str],
        previous_health: Dict[str, str]
    ) -> List[DetectedChange]:
        """Detect service health status changes."""
        changes = []
        
        for service, new_status in current_health.items():
            old_status = previous_health.get(service, "unknown")
            
            if old_status != new_status:
                # Determine severity based on transition
                if new_status in ["unhealthy", "offline"]:
                    severity = ChangeSeverity.CRITICAL
                elif new_status == "degraded":
                    severity = ChangeSeverity.HIGH
                elif old_status in ["unhealthy", "offline"] and new_status == "healthy":
                    severity = ChangeSeverity.MEDIUM
                else:
                    severity = ChangeSeverity.INFO
                
                change = DetectedChange(
                    id=uuid4(),
                    change_type=ChangeType.HEALTH_CHANGE,
                    severity=severity,
                    source=service,
                    description=f"{service} health changed: {old_status} -> {new_status}",
                    old_value=old_status,
                    new_value=new_status
                )
                changes.append(change)
                self._emit_change(change)
        
        return changes
    
    def _emit_change(self, change: DetectedChange) -> None:
        """Emit a detected change to listeners."""
        self._changes.append(change)
        
        # Keep last 500 changes
        if len(self._changes) > 500:
            self._changes = self._changes[-250:]
        
        # Notify listeners
        for listener in self._listeners:
            try:
                listener(change)
            except Exception as e:
                logger.error(f"Listener error: {e}")
    
    def add_listener(self, listener: Callable[[DetectedChange], None]) -> None:
        """Add a change listener."""
        self._listeners.append(listener)
    
    def remove_listener(self, listener: Callable[[DetectedChange], None]) -> None:
        """Remove a change listener."""
        if listener in self._listeners:
            self._listeners.remove(listener)
    
    async def run_detection_cycle(self) -> List[DetectedChange]:
        """Run a full detection cycle."""
        await self.initialize()
        
        all_changes = []
        
        # Detect registry changes
        for table in ["systems", "agents", "devices"]:
            changes = await self.detect_registry_changes(table)
            all_changes.extend(changes)
        
        # Detect git changes
        changes = await self.detect_git_changes()
        all_changes.extend(changes)
        
        return all_changes
    
    async def start_monitoring(self, interval_seconds: int = 60) -> None:
        """Start continuous change monitoring."""
        await self.initialize()
        
        async def monitor_loop():
            while True:
                try:
                    changes = await self.run_detection_cycle()
                    if changes:
                        logger.info(f"Detected {len(changes)} changes")
                except Exception as e:
                    logger.error(f"Detection cycle failed: {e}")
                
                await asyncio.sleep(interval_seconds)
        
        self._detection_task = asyncio.create_task(monitor_loop())
        logger.info(f"Started change monitoring (interval: {interval_seconds}s)")
    
    async def stop_monitoring(self) -> None:
        """Stop continuous monitoring."""
        if self._detection_task:
            self._detection_task.cancel()
            try:
                await self._detection_task
            except asyncio.CancelledError:
                pass
            self._detection_task = None
    
    def get_recent_changes(
        self,
        limit: int = 50,
        change_type: Optional[ChangeType] = None,
        severity: Optional[ChangeSeverity] = None,
        since: Optional[datetime] = None
    ) -> List[DetectedChange]:
        """Get recent changes with optional filters."""
        filtered = self._changes
        
        if change_type:
            filtered = [c for c in filtered if c.change_type == change_type]
        
        if severity:
            filtered = [c for c in filtered if c.severity == severity]
        
        if since:
            filtered = [c for c in filtered if c.detected_at >= since]
        
        return sorted(filtered, key=lambda c: c.detected_at, reverse=True)[:limit]
    
    def acknowledge_change(self, change_id: UUID) -> bool:
        """Acknowledge a detected change."""
        for change in self._changes:
            if change.id == change_id:
                change.acknowledged = True
                return True
        return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get detector statistics."""
        by_type = {}
        by_severity = {}
        
        for change in self._changes:
            by_type[change.change_type.value] = by_type.get(change.change_type.value, 0) + 1
            by_severity[change.severity.value] = by_severity.get(change.severity.value, 0) + 1
        
        return {
            "total_changes": len(self._changes),
            "snapshots_count": len(self._snapshots),
            "listeners_count": len(self._listeners),
            "monitoring_active": self._detection_task is not None,
            "by_type": by_type,
            "by_severity": by_severity,
            "unacknowledged": sum(1 for c in self._changes if not c.acknowledged)
        }


# Singleton instance
_change_detector: Optional[ChangeDetector] = None


async def get_change_detector() -> ChangeDetector:
    """Get or create the singleton change detector instance."""
    global _change_detector
    if _change_detector is None:
        _change_detector = ChangeDetector()
        await _change_detector.initialize()
    return _change_detector
