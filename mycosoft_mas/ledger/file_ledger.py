"""
File-based Append-Only Ledger Backup.
Created: February 4, 2026

This module provides an append-only JSONL file backup for the blockchain ledger.
Each entry is written as a single line JSON object, providing:
- Immutable audit trail
- Human-readable backup
- Fast recovery in case of database failure
- Independent verification of chain integrity
"""

import json
import os
import hashlib
import asyncio
import aiofiles
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
from pathlib import Path
import logging
import fcntl

logger = logging.getLogger(__name__)


class FileLedger:
    """
    Append-only file-based ledger for backup and audit purposes.
    
    Writes entries to a JSONL file with atomic appends.
    Supports both block and entry level logging.
    """
    
    def __init__(self, ledger_path: Optional[str] = None):
        self.ledger_path = Path(ledger_path or os.getenv(
            "LEDGER_FILE_PATH",
            "data/ledger/chain.jsonl"
        ))
        self._ensure_directory()
    
    def _ensure_directory(self) -> None:
        """Ensure ledger directory exists."""
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _serialize_entry(self, record: Dict[str, Any]) -> str:
        """Serialize a record to JSON string."""
        def default_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, UUID):
                return str(obj)
            return str(obj)
        
        return json.dumps(record, default=default_serializer, sort_keys=True)
    
    async def append_entry(
        self,
        entry_type: str,
        entry_id: UUID,
        data_hash: str,
        metadata: Optional[Dict[str, Any]] = None,
        block_number: Optional[int] = None
    ) -> bool:
        """
        Append a ledger entry to the JSONL file.
        
        Args:
            entry_type: Type of entry
            entry_id: Unique entry ID
            data_hash: SHA256 hash of the data
            metadata: Additional metadata
            block_number: Block number if committed
            
        Returns:
            True if successfully appended
        """
        record = {
            "record_type": "entry",
            "entry_id": str(entry_id),
            "entry_type": entry_type,
            "data_hash": data_hash,
            "metadata": metadata or {},
            "block_number": block_number,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return await self._append_line(record)
    
    async def append_block(
        self,
        block_number: int,
        previous_hash: str,
        block_hash: str,
        merkle_root: str,
        data_count: int
    ) -> bool:
        """
        Append a block record to the JSONL file.
        
        Args:
            block_number: Block number
            previous_hash: Hash of previous block
            block_hash: Hash of this block
            merkle_root: Merkle root of entries
            data_count: Number of entries in block
            
        Returns:
            True if successfully appended
        """
        record = {
            "record_type": "block",
            "block_number": block_number,
            "previous_hash": previous_hash,
            "block_hash": block_hash,
            "merkle_root": merkle_root,
            "data_count": data_count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return await self._append_line(record)
    
    async def _append_line(self, record: Dict[str, Any]) -> bool:
        """Atomically append a line to the ledger file."""
        try:
            line = self._serialize_entry(record) + "\n"
            
            async with aiofiles.open(self.ledger_path, "a", encoding="utf-8") as f:
                await f.write(line)
            
            return True
        except Exception as e:
            logger.error(f"Failed to append to ledger file: {e}")
            return False
    
    def append_entry_sync(
        self,
        entry_type: str,
        entry_id: UUID,
        data_hash: str,
        metadata: Optional[Dict[str, Any]] = None,
        block_number: Optional[int] = None
    ) -> bool:
        """Synchronous version of append_entry for non-async contexts."""
        record = {
            "record_type": "entry",
            "entry_id": str(entry_id),
            "entry_type": entry_type,
            "data_hash": data_hash,
            "metadata": metadata or {},
            "block_number": block_number,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return self._append_line_sync(record)
    
    def _append_line_sync(self, record: Dict[str, Any]) -> bool:
        """Synchronously append a line with file locking."""
        try:
            line = self._serialize_entry(record) + "\n"
            
            with open(self.ledger_path, "a", encoding="utf-8") as f:
                # Use file locking on Unix systems
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                except (AttributeError, OSError):
                    pass  # Windows or unsupported
                
                f.write(line)
                f.flush()
                os.fsync(f.fileno())
            
            return True
        except Exception as e:
            logger.error(f"Failed to append to ledger file (sync): {e}")
            return False
    
    async def read_all_entries(self) -> List[Dict[str, Any]]:
        """Read all entries from the ledger file."""
        entries = []
        
        if not self.ledger_path.exists():
            return entries
        
        try:
            async with aiofiles.open(self.ledger_path, "r", encoding="utf-8") as f:
                async for line in f:
                    line = line.strip()
                    if line:
                        entries.append(json.loads(line))
        except Exception as e:
            logger.error(f"Failed to read ledger file: {e}")
        
        return entries
    
    async def read_blocks(self) -> List[Dict[str, Any]]:
        """Read only block records from the ledger."""
        all_entries = await self.read_all_entries()
        return [e for e in all_entries if e.get("record_type") == "block"]
    
    async def read_entries_by_type(self, entry_type: str) -> List[Dict[str, Any]]:
        """Read entries of a specific type."""
        all_entries = await self.read_all_entries()
        return [
            e for e in all_entries 
            if e.get("record_type") == "entry" and e.get("entry_type") == entry_type
        ]
    
    async def verify_file_integrity(self) -> Dict[str, Any]:
        """
        Verify the integrity of the ledger file.
        
        Checks:
        - Block chain continuity
        - Hash consistency
        
        Returns:
            Verification result with status and details
        """
        entries = await self.read_all_entries()
        blocks = [e for e in entries if e.get("record_type") == "block"]
        
        if not blocks:
            return {"valid": True, "message": "No blocks to verify", "block_count": 0}
        
        # Sort by block number
        blocks.sort(key=lambda b: b.get("block_number", 0))
        
        errors = []
        
        # Verify chain continuity
        for i in range(1, len(blocks)):
            current = blocks[i]
            previous = blocks[i - 1]
            
            if current.get("previous_hash") != previous.get("block_hash"):
                errors.append(
                    f"Chain break at block {current.get('block_number')}: "
                    f"previous_hash mismatch"
                )
        
        return {
            "valid": len(errors) == 0,
            "block_count": len(blocks),
            "entry_count": len([e for e in entries if e.get("record_type") == "entry"]),
            "errors": errors
        }
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get ledger file statistics."""
        if not self.ledger_path.exists():
            return {
                "exists": False,
                "size_bytes": 0,
                "block_count": 0,
                "entry_count": 0
            }
        
        entries = await self.read_all_entries()
        blocks = [e for e in entries if e.get("record_type") == "block"]
        data_entries = [e for e in entries if e.get("record_type") == "entry"]
        
        return {
            "exists": True,
            "size_bytes": self.ledger_path.stat().st_size,
            "block_count": len(blocks),
            "entry_count": len(data_entries),
            "path": str(self.ledger_path)
        }


# Singleton instance
_file_ledger_instance: Optional[FileLedger] = None


def get_file_ledger() -> FileLedger:
    """Get or create the singleton file ledger instance."""
    global _file_ledger_instance
    if _file_ledger_instance is None:
        _file_ledger_instance = FileLedger()
    return _file_ledger_instance
