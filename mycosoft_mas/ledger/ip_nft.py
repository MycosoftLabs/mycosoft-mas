"""IP-NFT Management. Created: February 3, 2026"""
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone
from pydantic import BaseModel

class IPNFT(BaseModel):
    nft_id: UUID
    entry_id: UUID
    title: str
    creators: List[str]
    claim_type: str
    status: str = "pending"
    minted_at: Optional[datetime] = None

class IPNFTManager:
    def __init__(self, ledger = None):
        self.ledger = ledger
        self._nfts: Dict[UUID, IPNFT] = {}
    
    async def create_ip_claim(self, title: str, creators: List[str], claim_type: str, evidence: Dict[str, Any]) -> IPNFT:
        nft_id = uuid4()
        entry_id = uuid4()
        if self.ledger:
            entry = self.ledger.add_entry("ip_claim", {"title": title, "creators": creators, "evidence": evidence})
            entry_id = entry.entry_id
        nft = IPNFT(nft_id=nft_id, entry_id=entry_id, title=title, creators=creators, claim_type=claim_type)
        self._nfts[nft_id] = nft
        return nft
    
    async def mint_nft(self, nft_id: UUID) -> bool:
        if nft_id in self._nfts:
            self._nfts[nft_id].status = "minted"
            self._nfts[nft_id].minted_at = datetime.now(timezone.utc)
            return True
        return False
    
    def get_nft(self, nft_id: UUID) -> Optional[IPNFT]:
        return self._nfts.get(nft_id)
    
    def list_nfts(self, creator: Optional[str] = None) -> List[IPNFT]:
        if creator:
            return [n for n in self._nfts.values() if creator in n.creators]
        return list(self._nfts.values())
