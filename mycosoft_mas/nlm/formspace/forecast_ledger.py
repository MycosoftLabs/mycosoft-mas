"""Immutable forecast ledger. Late labels never overwrite issued rows."""

from __future__ import annotations

import json
import os
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional

from .contracts import ForecastEnvelope

_DEFAULT_LEDGER = Path(
    os.getenv(
        "NLM_FORECAST_LEDGER_DIR",
        str(Path(os.getenv("NLM_HOME", "data/formspace")) / "forecast_ledger"),
    )
)


class ForecastLedger:
    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = Path(root or _DEFAULT_LEDGER)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def _path(self, forecast_id: str) -> Path:
        safe = forecast_id.replace("/", "_").replace("\\", "_")
        return self.root / f"{safe}.json"

    def persist(self, envelope: ForecastEnvelope) -> Dict[str, Any]:
        path = self._path(envelope.forecast_id)
        payload = envelope.model_dump(mode="json")
        with self._lock:
            if path.exists():
                existing = json.loads(path.read_text(encoding="utf-8"))
                return {
                    "status": "idempotent",
                    "forecast": existing,
                    "overwritten": False,
                }
            path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        return {"status": "committed", "forecast": payload, "overwritten": False}

    def get(self, forecast_id: str) -> Optional[Dict[str, Any]]:
        path = self._path(forecast_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def refuse_overwrite(self, forecast_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        existing = self.get(forecast_id)
        if existing is None:
            return {"status": "missing", "forecast_id": forecast_id}
        return {
            "status": "refused",
            "forecast_id": forecast_id,
            "overwritten": False,
            "note": "Late labels or observations cannot replace an issued forecast.",
            "ignored_patch_keys": sorted(patch.keys()),
            "forecast": existing,
        }


_LEDGER: Optional[ForecastLedger] = None


def get_forecast_ledger() -> ForecastLedger:
    global _LEDGER
    if _LEDGER is None:
        _LEDGER = ForecastLedger()
    return _LEDGER
