"""Blockchain Ledger Implementation. Created: February 3, 2026"""
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel

class Block(BaseModel):
    block_number: int
    previous_hash: str
    block_hash: str = ""
    merkle_root: str = ""
    timestamp: datetime
    entries: List[Dict[str, Any]] = []

class LedgerEntry(BaseModel):
    entry_id: UUID
    entry_type: str
    data_hash: str
    metadata: Dict[str, Any] = {}
    signature: Optional[str] = None
    created_at: datetime

class BlockchainLedger:
    """Immutable ledger for scientific data provenance."""
    
    def __init__(self):
        self.blocks: List[Block] = []
        self._pending_entries: List[LedgerEntry] = []
        self._create_genesis_block()
    
    def _create_genesis_block(self) -> None:
        genesis = Block(block_number=0, previous_hash="0" * 64, timestamp=datetime.now(timezone.utc))
        genesis.block_hash = self._hash_block(genesis)
        self.blocks.append(genesis)
    
    def _hash_block(self, block: Block) -> str:
        data = f"{block.block_number}{block.previous_hash}{block.timestamp.isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def _hash_data(self, data: Any) -> str:
        return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()
    
    def add_entry(self, entry_type: str, data: Any, metadata: Dict[str, Any] = None) -> LedgerEntry:
        entry = LedgerEntry(entry_id=uuid4(), entry_type=entry_type, data_hash=self._hash_data(data), metadata=metadata or {}, created_at=datetime.now(timezone.utc))
        self._pending_entries.append(entry)
        return entry
    
    def commit_block(self) -> Optional[Block]:
        if not self._pending_entries:
            return None
        prev = self.blocks[-1]
        block = Block(block_number=prev.block_number + 1, previous_hash=prev.block_hash, timestamp=datetime.now(timezone.utc), entries=[e.dict() for e in self._pending_entries])
        block.merkle_root = self._compute_merkle_root([e.data_hash for e in self._pending_entries])
        block.block_hash = self._hash_block(block)
        self.blocks.append(block)
        self._pending_entries.clear()
        return block
    
    def _compute_merkle_root(self, hashes: List[str]) -> str:
        if not hashes: return "0" * 64
        while len(hashes) > 1:
            if len(hashes) % 2: hashes.append(hashes[-1])
            hashes = [hashlib.sha256((hashes[i] + hashes[i+1]).encode()).hexdigest() for i in range(0, len(hashes), 2)]
        return hashes[0]
    
    def verify_chain(self) -> bool:
        for i in range(1, len(self.blocks)):
            if self.blocks[i].previous_hash != self.blocks[i-1].block_hash:
                return False
        return True
    
    def get_entry(self, entry_id: UUID) -> Optional[LedgerEntry]:
        for block in self.blocks:
            for entry in block.entries:
                if entry.get("entry_id") == str(entry_id):
                    return LedgerEntry(**entry)
        return None
