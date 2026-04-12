from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4


def build_capability_signal(observation: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "signal_id": str(uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "source": observation.get("source", "unknown"),
        "domain": observation.get("domain", "unknown"),
        "confidence": float(observation.get("confidence", 0.0)),
        "payload": observation,
    }


def fuse_capability_signals(signals: List[Dict[str, Any]]) -> Dict[str, Any]:
    max_confidence = max((float(item.get("confidence", 0.0)) for item in signals), default=0.0)
    return {
        "fusion_id": str(uuid4()),
        "created_at": datetime.utcnow().isoformat(),
        "signal_count": len(signals),
        "max_confidence": max_confidence,
        "signals": signals,
    }
