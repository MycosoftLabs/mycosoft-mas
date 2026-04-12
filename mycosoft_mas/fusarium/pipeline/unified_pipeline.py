from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List
from uuid import uuid4


class UnifiedFusariumPipeline:
    def to_canonical_observation(self, domain: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "observation_id": payload.get("observation_id") or str(uuid4()),
            "domain": domain,
            "classification": payload.get("classification", "CUI"),
            "timestamp": payload.get("timestamp") or datetime.utcnow().isoformat(),
            "location": payload.get("location"),
            "merkle_hash": payload.get("merkle_hash"),
            "source": payload.get("source", "unknown"),
            "data": payload,
        }

    def to_provenance_record(self, canonical_observation: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "record_id": str(uuid4()),
            "observation_id": canonical_observation["observation_id"],
            "source": canonical_observation.get("source"),
            "merkle_hash": canonical_observation.get("merkle_hash"),
            "ingested_at": datetime.utcnow().isoformat(),
        }

    def batch(self, domain: str, payloads: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self.to_canonical_observation(domain, item) for item in payloads]

    def export_stix_like(self, canonical_observations: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        objects = []
        for item in canonical_observations:
            objects.append(
                {
                    "type": "x-fusarium-observation",
                    "id": f"x-fusarium-observation--{item['observation_id']}",
                    "created": item["timestamp"],
                    "labels": [item.get("domain", "unknown"), item.get("classification", "CUI")],
                    "x_fusarium_data": item,
                }
            )
        return {
            "type": "bundle",
            "id": f"bundle--{uuid4()}",
            "objects": objects,
        }
