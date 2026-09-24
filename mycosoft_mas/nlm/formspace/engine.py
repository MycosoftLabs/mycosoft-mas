"""FormSpace engine façade: atlas + dynamics + graphing + evidence + memory."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Sequence
from uuid import uuid4

from .atlas import get_atlas
from .dynamics import compute_trajectory, resolve_series_for_chart, run_recovery_experiment
from .graphing import build_graph_payload
from .scientific_loader import probe_scientific_nlm


def _memory_root() -> Path:
    root = Path(
        os.getenv(
            "FORMSPACE_MEMORY_DIR",
            str(Path(os.getenv("NLM_HOME", "data/formspace")) / "memory"),
        )
    )
    root.mkdir(parents=True, exist_ok=True)
    return root


class FormSpaceEngine:
    def __init__(self) -> None:
        self.atlas = get_atlas()
        self._lock = Lock()
        self._experiments: Dict[str, Dict[str, Any]] = {}
        self._evidence: List[Dict[str, Any]] = []
        self._memory_dir = _memory_root()

    def health(self) -> Dict[str, Any]:
        probe = probe_scientific_nlm()
        demo = self.atlas.list_demo_charts()
        return {
            "status": "healthy",
            "engine": "formspace",
            "schema": "formspace.engine/v1",
            "bound_to_ollama": False,
            "model_kind": "nature_learning_model",
            "demo_chart_count": len(demo),
            "nlm_weights_loaded": bool(probe.model_loaded),
            "nlm_probe_reason": probe.reason,
            "is_legacy_reference": bool(probe.is_legacy_reference),
            "note": (
                "FormSpace interprets NLM coordinates. Not an LLM. "
                "Weights may be unloaded; engine still serves atlas/demo."
            ),
        }

    def demo(self) -> Dict[str, Any]:
        return {
            "schema": "formspace.demo/v1",
            "label": "Demo / catalog",
            "charts": self.atlas.list_demo_charts(),
            "live": False,
            "bound_to_ollama": False,
            "note": (
                "Catalog charts with provenance. Not live sensor streams. "
                "Request graph/experiment with use_demo_fixture=true to replay fixtures."
            ),
        }

    def atlas_list(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        return self.atlas.list_atlas(user_id=user_id, include_demo=True)

    def atlas_upsert(
        self, payload: Dict[str, Any], *, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        result = self.atlas.upsert_chart(payload, user_id=user_id)
        if result.get("ok"):
            self._append_evidence(
                {
                    "kind": "chart_upsert",
                    "chart_id": result["chart"].get("chart_id"),
                    "user_id": user_id,
                }
            )
        return result

    def graph(
        self,
        *,
        chart_id: str,
        series: Optional[Sequence[float]] = None,
        use_demo_fixture: bool = False,
        graph_kind: str = "trajectory",
        dt: float = 0.1,
        a: float = -0.5,
        b: float = 1.0,
    ) -> Dict[str, Any]:
        payload = build_graph_payload(
            chart_id=chart_id,
            series=series,
            use_demo_fixture=use_demo_fixture,
            graph_kind=graph_kind,
            dt=dt,
            a=a,
            b=b,
        )
        if payload.get("ok"):
            self._append_evidence(
                {
                    "kind": "graph",
                    "graph_id": payload.get("graph_id"),
                    "chart_id": chart_id,
                    "origin": payload.get("origin"),
                }
            )
        return payload

    def experiment(
        self,
        *,
        chart_id: str,
        kind: str = "recovery",
        series: Optional[Sequence[float]] = None,
        use_demo_fixture: bool = False,
        perturbation_index: int = 3,
        perturbation_delta: float = 0.3,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        resolved = resolve_series_for_chart(
            chart_id, series=series, use_demo_fixture=use_demo_fixture
        )
        input_series = resolved.get("series") or []
        if kind == "trajectory":
            result = compute_trajectory(
                input_series,
                chart_id=chart_id,
                origin=str(resolved.get("origin") or "NONE"),
            )
        else:
            result = run_recovery_experiment(
                chart_id=chart_id,
                baseline=input_series,
                perturbation_index=perturbation_index,
                perturbation_delta=perturbation_delta,
                origin=str(resolved.get("origin") or "NONE"),
            )
        result["user_id"] = user_id
        result["label"] = resolved.get("label")
        result["source"] = resolved.get("source")
        if result.get("ok"):
            exp_id = result.get("experiment_id") or result.get("job_id") or uuid4().hex
            with self._lock:
                self._experiments[str(exp_id)] = result
            self._append_evidence(
                {
                    "kind": "experiment",
                    "experiment_id": exp_id,
                    "chart_id": chart_id,
                    "recovered": result.get("recovered"),
                    "user_id": user_id,
                }
            )
            if user_id:
                self.memory_append(
                    user_id,
                    {
                        "type": "experiment",
                        "experiment_id": exp_id,
                        "chart_id": chart_id,
                        "summary": {
                            "recovered": result.get("recovered"),
                            "recovery_step": result.get("recovery_step"),
                            "status": result.get("status"),
                        },
                    },
                )
        return result

    def evidence_list(self, *, limit: int = 50) -> Dict[str, Any]:
        with self._lock:
            items = list(reversed(self._evidence[-limit:]))
        return {
            "schema": "formspace.evidence/v1",
            "count": len(items),
            "items": items,
            "note": (
                "Local engine evidence log. MINDEX Merkle roots appear when "
                "persisted; empty when none."
            ),
        }

    def memory_list(self, user_id: Optional[str]) -> Dict[str, Any]:
        if not user_id:
            return {
                "ok": False,
                "auth_required": True,
                "items": [],
                "message": "Sign in to load FormSpace memory and saved charts.",
            }
        path = self._memory_path(user_id)
        items: List[Dict[str, Any]] = []
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    items = data
            except (json.JSONDecodeError, OSError):
                items = []
        user_atlas = self.atlas.list_atlas(user_id=user_id, include_demo=False)
        return {
            "ok": True,
            "user_id": user_id,
            "items": items,
            "saved_charts": user_atlas.get("charts") or [],
            "count": len(items),
        }

    def memory_append(self, user_id: str, entry: Dict[str, Any]) -> Dict[str, Any]:
        path = self._memory_path(user_id)
        items: List[Dict[str, Any]] = []
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    items = data
            except (json.JSONDecodeError, OSError):
                items = []
        record = {
            "id": f"mem-{uuid4().hex[:12]}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            **entry,
        }
        items.append(record)
        path.write_text(json.dumps(items[-200:], indent=2, default=str), encoding="utf-8")
        return {"ok": True, "item": record}

    def _memory_path(self, user_id: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in user_id)[:64]
        return self._memory_dir / f"{safe}.json"

    def _append_evidence(self, payload: Dict[str, Any]) -> None:
        row = {
            "evidence_id": f"ev-{uuid4().hex[:12]}",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        with self._lock:
            self._evidence.append(row)
            if len(self._evidence) > 500:
                self._evidence = self._evidence[-500:]


_ENGINE: Optional[FormSpaceEngine] = None


def get_formspace_engine() -> FormSpaceEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = FormSpaceEngine()
    return _ENGINE
