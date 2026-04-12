from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, Iterable, List
from uuid import UUID, uuid4

from mycosoft_mas.fusarium.data.schemas import IntelligenceProduct


class FusionEngine:
    def __init__(self) -> None:
        self.weights = {
            "hydrosphere": 0.28,
            "atmosphere": 0.14,
            "biosphere": 0.18,
            "geosphere": 0.14,
            "space_environment": 0.12,
            "infrastructure": 0.14,
        }

    def resolve_entities(self, domain_assessments: Iterable[Dict[str, Any]]) -> Dict[str, List[str]]:
        entities_by_domain: Dict[str, List[str]] = defaultdict(list)
        for item in domain_assessments:
            domain = item.get("domain", "unknown")
            entities = [str(entity) for entity in item.get("entities", [])]
            entities_by_domain[domain].extend(entities)
        return dict(entities_by_domain)

    def score_threat(self, domain_assessments: Iterable[Dict[str, Any]]) -> float:
        weighted_sum = 0.0
        total_weight = 0.0
        for item in domain_assessments:
            domain = item.get("domain", "unknown")
            confidence = float(item.get("confidence", 0.0))
            weight = self.weights.get(domain, 0.08)
            weighted_sum += confidence * weight
            total_weight += weight
        if total_weight <= 0:
            return 0.0
        return round(min(max(weighted_sum / total_weight, 0.0), 1.0), 3)

    def correlate(self, domain_assessments: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        correlations: List[Dict[str, Any]] = []
        by_key: Dict[str, List[str]] = defaultdict(list)
        for item in domain_assessments:
            for entity in item.get("entities", []):
                by_key[str(entity)].append(item.get("domain", "unknown"))
        for entity_id, domains in by_key.items():
            unique_domains = sorted(set(domains))
            if len(unique_domains) > 1:
                correlations.append(
                    {
                        "correlation_id": str(uuid4()),
                        "entity_id": entity_id,
                        "domains": unique_domains,
                        "created_at": datetime.utcnow().isoformat(),
                    }
                )
        return correlations

    def generate_product(self, title: str, body: str, sources: List[str], confidence: float) -> IntelligenceProduct:
        return IntelligenceProduct(
            title=title,
            body=body,
            domain="multi-domain",
            classification="CUI",
            confidence=confidence,
            sources=sources,
            tags=["fusarium", "fusion", "envint"],
        )
