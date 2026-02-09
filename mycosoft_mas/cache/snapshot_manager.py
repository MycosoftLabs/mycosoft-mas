"""
Snapshot Manager - February 6, 2026

Manages compressed snapshot files for archival timeline data.
Used for large time ranges (days/weeks) that don't fit in Redis.

Features:
- Compressed JSON snapshots by time bucket (hourly, daily)
- S3-compatible storage backend
- Local file cache
- Automatic snapshot creation from live data
"""

import asyncio
import gzip
import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("SnapshotManager")

# Configuration
SNAPSHOT_DIR = os.getenv("SNAPSHOT_DIR", "/tmp/crep-snapshots")
SNAPSHOT_BUCKET_HOURS = 1  # Create hourly snapshots
MAX_LOCAL_SNAPSHOTS = 168  # Keep 1 week of hourly snapshots locally


@dataclass
class SnapshotMetadata:
    """Metadata for a snapshot file."""
    entity_type: str
    bucket_start: int  # Unix timestamp (ms)
    bucket_end: int    # Unix timestamp (ms)
    entry_count: int
    file_size: int
    compressed: bool
    created_at: int
    file_path: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "bucket_start": self.bucket_start,
            "bucket_end": self.bucket_end,
            "entry_count": self.entry_count,
            "file_size": self.file_size,
            "compressed": self.compressed,
            "created_at": self.created_at,
            "file_path": self.file_path,
        }
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SnapshotMetadata":
        return cls(**d)


class SnapshotManager:
    """
    Manages timeline snapshots for archival storage.
    
    Snapshots are organized by entity type and time bucket:
    /snapshots/
      /{entity_type}/
        /{YYYY-MM-DD}/
          /{HH}.json.gz
    """
    
    def __init__(self, base_dir: str = SNAPSHOT_DIR):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._metadata_cache: Dict[str, SnapshotMetadata] = {}
        self._index_file = self.base_dir / "index.json"
        self._load_index()
    
    def _load_index(self) -> None:
        """Load snapshot index from disk."""
        if self._index_file.exists():
            try:
                with open(self._index_file, "r") as f:
                    data = json.load(f)
                    self._metadata_cache = {
                        k: SnapshotMetadata.from_dict(v) 
                        for k, v in data.items()
                    }
                logger.info(f"Loaded {len(self._metadata_cache)} snapshot entries from index")
            except Exception as e:
                logger.error(f"Failed to load snapshot index: {e}")
    
    def _save_index(self) -> None:
        """Save snapshot index to disk."""
        try:
            with open(self._index_file, "w") as f:
                json.dump(
                    {k: v.to_dict() for k, v in self._metadata_cache.items()},
                    f,
                    indent=2
                )
        except Exception as e:
            logger.error(f"Failed to save snapshot index: {e}")
    
    def _bucket_key(self, entity_type: str, timestamp_ms: int) -> str:
        """Generate bucket key for a timestamp."""
        dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
        # Round down to bucket boundary
        bucket_hour = dt.replace(minute=0, second=0, microsecond=0)
        return f"{entity_type}/{bucket_hour.strftime('%Y-%m-%d/%H')}"
    
    def _bucket_path(self, bucket_key: str) -> Path:
        """Get file path for a bucket."""
        return self.base_dir / f"{bucket_key}.json.gz"
    
    def _bucket_time_range(self, bucket_key: str) -> Tuple[int, int]:
        """Get time range for a bucket key."""
        parts = bucket_key.split("/")
        entity_type = parts[0]
        date_str = parts[1]
        hour_str = parts[2]
        
        dt = datetime.strptime(f"{date_str} {hour_str}:00:00", "%Y-%m-%d %H:%M:%S")
        dt = dt.replace(tzinfo=timezone.utc)
        
        start_ms = int(dt.timestamp() * 1000)
        end_ms = start_ms + (SNAPSHOT_BUCKET_HOURS * 60 * 60 * 1000)
        
        return (start_ms, end_ms)
    
    async def create_snapshot(
        self,
        entity_type: str,
        entries: List[Dict[str, Any]],
        bucket_start_ms: int
    ) -> SnapshotMetadata:
        """
        Create a compressed snapshot file.
        
        Args:
            entity_type: Type of entities in snapshot
            entries: List of timeline entries
            bucket_start_ms: Start timestamp of the bucket
        
        Returns:
            SnapshotMetadata for the created file
        """
        bucket_key = self._bucket_key(entity_type, bucket_start_ms)
        file_path = self._bucket_path(bucket_key)
        
        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Compress and write
        data = json.dumps(entries).encode("utf-8")
        compressed = gzip.compress(data)
        
        with open(file_path, "wb") as f:
            f.write(compressed)
        
        # Calculate bucket end
        start_ms, end_ms = self._bucket_time_range(bucket_key)
        
        # Create metadata
        metadata = SnapshotMetadata(
            entity_type=entity_type,
            bucket_start=start_ms,
            bucket_end=end_ms,
            entry_count=len(entries),
            file_size=len(compressed),
            compressed=True,
            created_at=int(time.time() * 1000),
            file_path=str(file_path),
        )
        
        # Update cache and index
        self._metadata_cache[bucket_key] = metadata
        self._save_index()
        
        logger.info(f"Created snapshot {bucket_key}: {len(entries)} entries, {len(compressed)} bytes")
        
        return metadata
    
    async def read_snapshot(self, bucket_key: str) -> List[Dict[str, Any]]:
        """
        Read entries from a snapshot file.
        
        Args:
            bucket_key: The bucket key to read
        
        Returns:
            List of timeline entries
        """
        file_path = self._bucket_path(bucket_key)
        
        if not file_path.exists():
            return []
        
        try:
            with open(file_path, "rb") as f:
                compressed = f.read()
            
            data = gzip.decompress(compressed)
            entries = json.loads(data.decode("utf-8"))
            
            return entries
        except Exception as e:
            logger.error(f"Failed to read snapshot {bucket_key}: {e}")
            return []
    
    async def query_snapshots(
        self,
        entity_type: str,
        start_time_ms: int,
        end_time_ms: int
    ) -> List[Dict[str, Any]]:
        """
        Query entries across multiple snapshots.
        
        Args:
            entity_type: Type of entities to query
            start_time_ms: Start of time range
            end_time_ms: End of time range
        
        Returns:
            Combined list of entries from all matching snapshots
        """
        results = []
        
        # Find all buckets that overlap the time range
        current_ms = start_time_ms
        
        while current_ms < end_time_ms:
            bucket_key = self._bucket_key(entity_type, current_ms)
            
            if bucket_key in self._metadata_cache:
                entries = await self.read_snapshot(bucket_key)
                
                # Filter to exact time range
                for entry in entries:
                    ts = entry.get("timestamp", 0)
                    if start_time_ms <= ts <= end_time_ms:
                        results.append(entry)
            
            # Move to next bucket
            current_ms += SNAPSHOT_BUCKET_HOURS * 60 * 60 * 1000
        
        return results
    
    async def list_snapshots(
        self,
        entity_type: Optional[str] = None,
        since_ms: Optional[int] = None
    ) -> List[SnapshotMetadata]:
        """
        List available snapshots.
        
        Args:
            entity_type: Filter by entity type
            since_ms: Only snapshots after this time
        
        Returns:
            List of snapshot metadata
        """
        results = []
        
        for key, metadata in self._metadata_cache.items():
            if entity_type and metadata.entity_type != entity_type:
                continue
            if since_ms and metadata.bucket_start < since_ms:
                continue
            results.append(metadata)
        
        # Sort by bucket start time
        results.sort(key=lambda m: m.bucket_start)
        
        return results
    
    async def cleanup_old_snapshots(self, max_age_ms: Optional[int] = None) -> int:
        """
        Remove old snapshot files.
        
        Args:
            max_age_ms: Maximum age of snapshots to keep (default: 1 week)
        
        Returns:
            Number of snapshots removed
        """
        if max_age_ms is None:
            max_age_ms = MAX_LOCAL_SNAPSHOTS * SNAPSHOT_BUCKET_HOURS * 60 * 60 * 1000
        
        cutoff = int(time.time() * 1000) - max_age_ms
        removed = 0
        
        keys_to_remove = []
        
        for key, metadata in self._metadata_cache.items():
            if metadata.bucket_end < cutoff:
                # Remove file
                file_path = Path(metadata.file_path)
                if file_path.exists():
                    try:
                        file_path.unlink()
                        removed += 1
                    except Exception as e:
                        logger.error(f"Failed to remove snapshot {key}: {e}")
                
                keys_to_remove.append(key)
        
        # Remove from cache
        for key in keys_to_remove:
            del self._metadata_cache[key]
        
        if removed > 0:
            self._save_index()
            logger.info(f"Cleaned up {removed} old snapshots")
        
        return removed
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get snapshot storage statistics."""
        total_size = 0
        total_entries = 0
        by_entity_type: Dict[str, Dict[str, int]] = {}
        oldest_bucket = None
        newest_bucket = None
        
        for metadata in self._metadata_cache.values():
            total_size += metadata.file_size
            total_entries += metadata.entry_count
            
            if metadata.entity_type not in by_entity_type:
                by_entity_type[metadata.entity_type] = {"count": 0, "entries": 0, "size": 0}
            
            by_entity_type[metadata.entity_type]["count"] += 1
            by_entity_type[metadata.entity_type]["entries"] += metadata.entry_count
            by_entity_type[metadata.entity_type]["size"] += metadata.file_size
            
            if oldest_bucket is None or metadata.bucket_start < oldest_bucket:
                oldest_bucket = metadata.bucket_start
            if newest_bucket is None or metadata.bucket_end > newest_bucket:
                newest_bucket = metadata.bucket_end
        
        return {
            "total_snapshots": len(self._metadata_cache),
            "total_entries": total_entries,
            "total_size_bytes": total_size,
            "total_size_human": self._format_bytes(total_size),
            "by_entity_type": by_entity_type,
            "oldest_bucket_ms": oldest_bucket,
            "newest_bucket_ms": newest_bucket,
            "time_range_hours": (
                (newest_bucket - oldest_bucket) / (1000 * 60 * 60)
                if oldest_bucket and newest_bucket else 0
            ),
        }
    
    @staticmethod
    def _format_bytes(size: int) -> str:
        """Format bytes to human readable."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"


# Singleton instance
_snapshot_manager: Optional[SnapshotManager] = None


def get_snapshot_manager() -> SnapshotManager:
    """Get the singleton snapshot manager."""
    global _snapshot_manager
    if _snapshot_manager is None:
        _snapshot_manager = SnapshotManager()
    return _snapshot_manager