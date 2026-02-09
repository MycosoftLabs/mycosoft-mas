"""Long-term persistent memory. Created: February 3, 2026"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel

class Fact(BaseModel):
    fact_id: UUID
    scope: str
    namespace_id: Optional[UUID] = None
    key: str
    value: Any
    source: str = "user"
    confidence: float = 1.0
    created_at: datetime
    updated_at: datetime

class LongTermMemory:
    """Persistent memory across sessions."""
    
    def __init__(self):
        self._facts: Dict[UUID, Fact] = {}
        self._user_facts: Dict[UUID, List[UUID]] = {}
    
    def store_fact(self, key: str, value: Any, scope: str = "system", namespace_id: Optional[UUID] = None, source: str = "user") -> Fact:
        now = datetime.now(timezone.utc)
        fact = Fact(fact_id=uuid4(), scope=scope, namespace_id=namespace_id, key=key, value=value, source=source, created_at=now, updated_at=now)
        self._facts[fact.fact_id] = fact
        if namespace_id:
            if namespace_id not in self._user_facts:
                self._user_facts[namespace_id] = []
            self._user_facts[namespace_id].append(fact.fact_id)
        return fact
    
    def get_fact(self, key: str, namespace_id: Optional[UUID] = None) -> Optional[Fact]:
        for fact in self._facts.values():
            if fact.key == key and fact.namespace_id == namespace_id:
                return fact
        return None
    
    def update_fact(self, fact_id: UUID, value: Any) -> bool:
        if fact_id in self._facts:
            self._facts[fact_id].value = value
            self._facts[fact_id].updated_at = datetime.now(timezone.utc)
            return True
        return False
    
    def get_user_facts(self, user_id: UUID) -> List[Fact]:
        fact_ids = self._user_facts.get(user_id, [])
        return [self._facts[fid] for fid in fact_ids if fid in self._facts]
    
    def search_facts(self, query: str) -> List[Fact]:
        results = []
        for fact in self._facts.values():
            if query.lower() in fact.key.lower() or query.lower() in str(fact.value).lower():
                results.append(fact)
        return results
