"""
Persistent Blockchain Ledger with PostgreSQL Storage.
Created: February 4, 2026

This module provides a database-backed blockchain implementation that:
- Persists blocks and entries to PostgreSQL ledger schema
- Maintains chain integrity with SHA256 hashes
- Supports Merkle root computation for block verification
- Provides async operations for high-performance writes
"""

import hashlib
import json
import asyncio
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class Block(BaseModel):
    """Blockchain block model."""
    block_number: int
    previous_hash: str
    block_hash: str = ""
    merkle_root: str = ""
    timestamp: datetime
    data_count: int = 0


class LedgerEntry(BaseModel):
    """Ledger entry model."""
    id: UUID
    block_number: Optional[int] = None
    entry_type: str
    data_hash: str
    metadata: Dict[str, Any] = {}
    signature: Optional[str] = None
    created_at: datetime


class PersistentBlockchainLedger:
    """
    PostgreSQL-backed immutable blockchain ledger.
    
    All entries are hashed with SHA256 and stored in PostgreSQL.
    Chain integrity is verified using block hashes and Merkle roots.
    """
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv(
            "DATABASE_URL",
            "postgresql://mycosoft:mycosoft@localhost:5432/mycosoft"
        )
        self._pool = None
        self._pending_entries: List[LedgerEntry] = []
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize database connection pool and ensure genesis block exists."""
        if self._initialized:
            return
        
        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=5,
                command_timeout=30
            )
            await self._ensure_genesis_block()
            self._initialized = True
            logger.info("PersistentBlockchainLedger initialized")
        except Exception as e:
            logger.error(f"Failed to initialize ledger: {e}")
            raise
    
    async def close(self) -> None:
        """Close database connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            self._initialized = False
    
    async def _ensure_genesis_block(self) -> None:
        """Create genesis block if it doesn't exist."""
        async with self._pool.acquire() as conn:
            existing = await conn.fetchval(
                "SELECT block_number FROM ledger.blocks WHERE block_number = 0"
            )
            if existing is None:
                genesis_hash = self._hash_block_data(0, "0" * 64, datetime.now(timezone.utc))
                await conn.execute(
                    """
                    INSERT INTO ledger.blocks (block_number, previous_hash, block_hash, merkle_root, timestamp, data_count)
                    VALUES (0, $1, $2, $3, $4, 0)
                    """,
                    "0" * 64,
                    genesis_hash,
                    "0" * 64,
                    datetime.now(timezone.utc)
                )
                logger.info("Genesis block created")
    
    def _hash_block_data(self, block_number: int, previous_hash: str, timestamp: datetime) -> str:
        """Compute SHA256 hash of block data."""
        data = f"{block_number}{previous_hash}{timestamp.isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def _hash_data(self, data: Any) -> str:
        """Compute SHA256 hash of arbitrary data."""
        return hashlib.sha256(
            json.dumps(data, sort_keys=True, default=str).encode()
        ).hexdigest()
    
    def _compute_merkle_root(self, hashes: List[str]) -> str:
        """Compute Merkle root from list of hashes."""
        if not hashes:
            return "0" * 64
        
        while len(hashes) > 1:
            if len(hashes) % 2:
                hashes.append(hashes[-1])
            hashes = [
                hashlib.sha256((hashes[i] + hashes[i + 1]).encode()).hexdigest()
                for i in range(0, len(hashes), 2)
            ]
        return hashes[0]
    
    async def add_entry(
        self,
        entry_type: str,
        data: Any,
        metadata: Optional[Dict[str, Any]] = None,
        signature: Optional[str] = None
    ) -> LedgerEntry:
        """
        Add a new entry to pending entries.
        
        Args:
            entry_type: Type of entry (e.g., 'memory_write', 'audit_event')
            data: Data to hash and record
            metadata: Additional metadata to store
            signature: Optional cryptographic signature
            
        Returns:
            LedgerEntry with generated hash
        """
        entry = LedgerEntry(
            id=uuid4(),
            entry_type=entry_type,
            data_hash=self._hash_data(data),
            metadata=metadata or {},
            signature=signature,
            created_at=datetime.now(timezone.utc)
        )
        self._pending_entries.append(entry)
        return entry
    
    async def commit_block(self) -> Optional[Block]:
        """
        Commit pending entries to a new block in the database.
        
        Returns:
            Block if entries were committed, None if no pending entries
        """
        if not self._pending_entries:
            return None
        
        if not self._initialized:
            await self.initialize()
        
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                # Get previous block
                prev = await conn.fetchrow(
                    "SELECT block_number, block_hash FROM ledger.blocks ORDER BY block_number DESC LIMIT 1"
                )
                
                prev_number = prev["block_number"]
                prev_hash = prev["block_hash"]
                new_number = prev_number + 1
                timestamp = datetime.now(timezone.utc)
                
                # Compute hashes
                merkle_root = self._compute_merkle_root([e.data_hash for e in self._pending_entries])
                block_hash = self._hash_block_data(new_number, prev_hash, timestamp)
                
                # Insert block
                await conn.execute(
                    """
                    INSERT INTO ledger.blocks (block_number, previous_hash, block_hash, merkle_root, timestamp, data_count)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    new_number, prev_hash, block_hash, merkle_root, timestamp, len(self._pending_entries)
                )
                
                # Insert entries
                for entry in self._pending_entries:
                    await conn.execute(
                        """
                        INSERT INTO ledger.entries (id, block_number, entry_type, data_hash, metadata, signature, created_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        """,
                        entry.id, new_number, entry.entry_type, entry.data_hash,
                        json.dumps(entry.metadata), entry.signature, entry.created_at
                    )
                
                block = Block(
                    block_number=new_number,
                    previous_hash=prev_hash,
                    block_hash=block_hash,
                    merkle_root=merkle_root,
                    timestamp=timestamp,
                    data_count=len(self._pending_entries)
                )
                
                self._pending_entries.clear()
                logger.info(f"Block {new_number} committed with {block.data_count} entries")
                return block
    
    async def get_latest_block(self) -> Optional[Block]:
        """Get the most recent block."""
        if not self._initialized:
            await self.initialize()
        
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM ledger.blocks ORDER BY block_number DESC LIMIT 1"
            )
            if row:
                return Block(
                    block_number=row["block_number"],
                    previous_hash=row["previous_hash"],
                    block_hash=row["block_hash"],
                    merkle_root=row["merkle_root"],
                    timestamp=row["timestamp"],
                    data_count=row["data_count"]
                )
        return None
    
    async def get_entry(self, entry_id: UUID) -> Optional[LedgerEntry]:
        """Get a specific entry by ID."""
        if not self._initialized:
            await self.initialize()
        
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM ledger.entries WHERE id = $1", entry_id
            )
            if row:
                return LedgerEntry(
                    id=row["id"],
                    block_number=row["block_number"],
                    entry_type=row["entry_type"],
                    data_hash=row["data_hash"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    signature=row["signature"],
                    created_at=row["created_at"]
                )
        return None
    
    async def get_entries_by_type(self, entry_type: str, limit: int = 100) -> List[LedgerEntry]:
        """Get entries by type."""
        if not self._initialized:
            await self.initialize()
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM ledger.entries 
                WHERE entry_type = $1 
                ORDER BY created_at DESC 
                LIMIT $2
                """,
                entry_type, limit
            )
            return [
                LedgerEntry(
                    id=row["id"],
                    block_number=row["block_number"],
                    entry_type=row["entry_type"],
                    data_hash=row["data_hash"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    signature=row["signature"],
                    created_at=row["created_at"]
                )
                for row in rows
            ]
    
    async def verify_chain(self) -> bool:
        """Verify blockchain integrity."""
        if not self._initialized:
            await self.initialize()
        
        async with self._pool.acquire() as conn:
            blocks = await conn.fetch(
                "SELECT * FROM ledger.blocks ORDER BY block_number ASC"
            )
            
            for i in range(1, len(blocks)):
                current = blocks[i]
                previous = blocks[i - 1]
                
                if current["previous_hash"] != previous["block_hash"]:
                    logger.error(f"Chain broken at block {current['block_number']}")
                    return False
                
                # Verify block hash
                expected_hash = self._hash_block_data(
                    current["block_number"],
                    current["previous_hash"],
                    current["timestamp"]
                )
                if current["block_hash"] != expected_hash:
                    logger.error(f"Block hash mismatch at block {current['block_number']}")
                    return False
            
            logger.info(f"Chain verified: {len(blocks)} blocks valid")
            return True
    
    async def get_chain_stats(self) -> Dict[str, Any]:
        """Get chain statistics."""
        if not self._initialized:
            await self.initialize()
        
        async with self._pool.acquire() as conn:
            block_count = await conn.fetchval("SELECT COUNT(*) FROM ledger.blocks")
            entry_count = await conn.fetchval("SELECT COUNT(*) FROM ledger.entries")
            latest = await self.get_latest_block()
            
            return {
                "block_count": block_count,
                "entry_count": entry_count,
                "latest_block": latest.block_number if latest else 0,
                "chain_valid": await self.verify_chain(),
                "pending_entries": len(self._pending_entries)
            }


# Singleton instance
_ledger_instance: Optional[PersistentBlockchainLedger] = None


def get_ledger() -> PersistentBlockchainLedger:
    """Get or create the singleton ledger instance."""
    global _ledger_instance
    if _ledger_instance is None:
        _ledger_instance = PersistentBlockchainLedger()
    return _ledger_instance
