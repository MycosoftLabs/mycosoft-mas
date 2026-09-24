"""FormSpace atlas: versioned charts and Form States.

Demo charts are server-side catalog registry rows (provenance-labeled).
They are not live sensor streams and do not invent ecology probabilities.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional
from uuid import uuid4

# Canonical demo chart IDs aligned with website NLM catalog formspace_chart_ids.
DEMO_CHARTS: List[Dict[str, Any]] = [
    {
        "chart_id": "fs-spectral-demo-v1",
        "name": "Spectral state atlas",
        "version": "v1",
        "modalities": ["rgb", "ir", "multispectral", "lifi"],
        "axes": ["spectral_energy", "stress_index", "object_patch"],
        "nlm_model_ids": ["nlm-spectral-base-v1"],
        "scope": "demo_catalog",
        "provenance": "plan-sep23-2026-seed",
        "fixture_series": [0.12, 0.18, 0.22, 0.19, 0.25, 0.31, 0.28, 0.33],
    },
    {
        "chart_id": "fs-acoustic-air-demo-v1",
        "name": "Air acoustic atlas",
        "version": "v1",
        "modalities": ["mic", "stft", "mel"],
        "axes": ["band_energy", "event_onset", "anomaly_score"],
        "nlm_model_ids": ["nlm-acoustic-air-v1"],
        "scope": "demo_catalog",
        "provenance": "plan-sep23-2026-seed;acoustic-library-encoder-baseline",
        "fixture_series": [0.05, 0.08, 0.4, 0.55, 0.2, 0.12, 0.1, 0.09],
    },
    {
        "chart_id": "fs-acoustic-hydro-demo-v1",
        "name": "Hydro acoustic atlas",
        "version": "v1",
        "modalities": ["hydrophone"],
        "axes": ["band_energy", "mammal_call", "vessel_tone"],
        "nlm_model_ids": ["nlm-acoustic-hydro-v1"],
        "scope": "demo_catalog",
        "provenance": "plan-sep23-2026-seed;mbari-encoder-baseline",
        "fixture_series": [0.02, 0.03, 0.15, 0.45, 0.5, 0.3, 0.12, 0.06],
    },
    {
        "chart_id": "fs-fci-demo-v1",
        "name": "FCI bioelectric atlas",
        "version": "v1",
        "modalities": ["fci_voltage", "impedance"],
        "axes": ["voltage", "impedance", "transition_likelihood"],
        "nlm_model_ids": ["nlm-bioelectric-fci-v1"],
        "scope": "demo_catalog",
        "provenance": "plan-sep23-2026-seed",
        "fixture_series": [0.4, 0.42, 0.41, 0.55, 0.62, 0.58, 0.5, 0.48],
    },
    {
        "chart_id": "fs-thermal-demo-v1",
        "name": "Thermal gradient atlas",
        "version": "v1",
        "modalities": ["bme_temp", "ir"],
        "axes": ["temp_c", "gradient", "onset_feature"],
        "nlm_model_ids": ["nlm-thermal-base-v1"],
        "scope": "demo_catalog",
        "provenance": "plan-sep23-2026-seed",
        "fixture_series": [0.2, 0.22, 0.28, 0.35, 0.5, 0.7, 0.65, 0.4],
    },
    {
        "chart_id": "fs-voc-demo-v1",
        "name": "VOC / chemical atlas",
        "version": "v1",
        "modalities": ["bme688", "voc", "co2"],
        "axes": ["voc_index", "drift_corrected", "gas_class"],
        "nlm_model_ids": ["nlm-chemical-voc-v1"],
        "scope": "demo_catalog",
        "provenance": "plan-sep23-2026-seed",
        "fixture_series": [0.1, 0.15, 0.2, 0.35, 0.4, 0.32, 0.25, 0.18],
    },
    {
        "chart_id": "fs-mech-demo-v1",
        "name": "Mechanical vibration atlas",
        "version": "v1",
        "modalities": ["accel", "pressure", "seismic"],
        "axes": ["rms", "peak_freq", "structural"],
        "nlm_model_ids": ["nlm-mechanical-vib-v1"],
        "scope": "demo_catalog",
        "provenance": "plan-sep23-2026-seed",
        "fixture_series": [0.08, 0.1, 0.6, 0.7, 0.2, 0.15, 0.12, 0.1],
    },
    {
        "chart_id": "fs-soil-demo-v1",
        "name": "Soil environment atlas",
        "version": "v1",
        "modalities": ["moisture", "ec", "ph", "temp"],
        "axes": ["moisture", "ec", "ph"],
        "nlm_model_ids": ["nlm-soil-env-v1"],
        "scope": "demo_catalog",
        "provenance": "plan-sep23-2026-seed",
        "fixture_series": [0.3, 0.32, 0.35, 0.33, 0.31, 0.29, 0.28, 0.3],
    },
    {
        "chart_id": "fs-weather-demo-v1",
        "name": "Microclimate atlas",
        "version": "v1",
        "modalities": ["station", "era5"],
        "axes": ["temp", "humidity", "pressure"],
        "nlm_model_ids": ["nlm-weather-micro-v1"],
        "scope": "demo_catalog",
        "provenance": "plan-sep23-2026-seed",
        "fixture_series": [0.25, 0.26, 0.27, 0.28, 0.3, 0.29, 0.27, 0.26],
    },
    {
        "chart_id": "fs-fusion-demo-v1",
        "name": "Multimodal fusion atlas",
        "version": "v1",
        "modalities": ["cross_modal"],
        "axes": ["fused_state", "support", "abstain"],
        "nlm_model_ids": ["nlm-fusion-multimodal-v1"],
        "scope": "demo_catalog",
        "provenance": "plan-sep23-2026-seed",
        "fixture_series": [0.2, 0.25, 0.3, 0.35, 0.4, 0.38, 0.36, 0.34],
    },
    {
        "chart_id": "fs-mycelium-demo-v1",
        "name": "Mycelium growth scenario atlas",
        "version": "v1",
        "modalities": ["imagery", "bioelectric", "humidity"],
        "axes": ["colony_extent", "bioelectric", "humidity"],
        "nlm_model_ids": ["nlm-scen-mycelium-growth-v1"],
        "scope": "demo_catalog",
        "provenance": "plan-sep23-2026-seed",
        "fixture_series": [0.1, 0.15, 0.22, 0.3, 0.38, 0.45, 0.5, 0.52],
    },
    {
        "chart_id": "fs-fire-demo-v1",
        "name": "Fire / wildfire onset atlas",
        "version": "v1",
        "modalities": ["thermal", "voc", "weather"],
        "axes": ["thermal", "voc", "wind_context"],
        "nlm_model_ids": ["nlm-scen-fire-thermal-v1"],
        "scope": "demo_catalog",
        "provenance": "plan-sep23-2026-seed",
        "fixture_series": [0.15, 0.2, 0.35, 0.55, 0.75, 0.8, 0.6, 0.4],
    },
]


def _store_root() -> Path:
    root = Path(
        os.getenv(
            "FORMSPACE_ATLAS_DIR",
            str(Path(os.getenv("NLM_HOME", "data/formspace")) / "atlas"),
        )
    )
    root.mkdir(parents=True, exist_ok=True)
    return root


class FormSpaceAtlas:
    """In-process + disk atlas for charts and user Form States."""

    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = Path(root or _store_root())
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._user_charts: Dict[str, Dict[str, Any]] = {}
        self._load_user_charts()

    def _user_path(self) -> Path:
        return self.root / "user_charts.json"

    def _load_user_charts(self) -> None:
        path = self._user_path()
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self._user_charts = data
        except (json.JSONDecodeError, OSError):
            self._user_charts = {}

    def _save_user_charts(self) -> None:
        path = self._user_path()
        path.write_text(
            json.dumps(self._user_charts, indent=2, default=str),
            encoding="utf-8",
        )

    def list_demo_charts(self) -> List[Dict[str, Any]]:
        """Public demo catalog — registry metadata only (no live streams)."""
        out: List[Dict[str, Any]] = []
        for chart in DEMO_CHARTS:
            row = {k: v for k, v in chart.items() if k != "fixture_series"}
            row["label"] = "Demo / catalog"
            row["has_fixture"] = bool(chart.get("fixture_series"))
            row["live"] = False
            out.append(row)
        return out

    def get_chart(self, chart_id: str) -> Optional[Dict[str, Any]]:
        for chart in DEMO_CHARTS:
            if chart["chart_id"] == chart_id:
                return dict(chart)
        with self._lock:
            return self._user_charts.get(chart_id)

    def list_atlas(
        self,
        *,
        user_id: Optional[str] = None,
        include_demo: bool = True,
    ) -> Dict[str, Any]:
        charts: List[Dict[str, Any]] = []
        if include_demo:
            charts.extend(self.list_demo_charts())
        with self._lock:
            for chart_id, chart in self._user_charts.items():
                owner = chart.get("owner_user_id")
                if user_id and owner == user_id:
                    charts.append({**chart, "scope": "user", "live": False})
                elif not user_id and chart.get("public"):
                    charts.append({**chart, "scope": "public", "live": False})
        return {
            "schema": "formspace.atlas/v1",
            "chart_count": len(charts),
            "charts": charts,
            "auth": "logged_in" if user_id else "logged_out",
            "note": (
                "Demo charts are catalog registry rows. Live panels abstain "
                "when sensors/weights are unavailable."
            ),
        }

    def upsert_chart(
        self,
        payload: Dict[str, Any],
        *,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not user_id:
            return {
                "ok": False,
                "error": "auth_required",
                "message": "Sign in to save FormSpace charts to your atlas.",
            }
        chart_id = str(payload.get("chart_id") or f"fs-user-{uuid4().hex[:12]}")
        now = datetime.now(timezone.utc).isoformat()
        chart = {
            "chart_id": chart_id,
            "name": payload.get("name") or chart_id,
            "version": payload.get("version") or "v1",
            "modalities": payload.get("modalities") or [],
            "axes": payload.get("axes") or [],
            "nlm_model_ids": payload.get("nlm_model_ids") or [],
            "owner_user_id": user_id,
            "scope": "user",
            "provenance": payload.get("provenance") or f"user:{user_id}",
            "public": bool(payload.get("public", False)),
            "updated_at": now,
            "created_at": payload.get("created_at") or now,
            "form_state": payload.get("form_state") or {},
            "live": False,
        }
        with self._lock:
            existing = self._user_charts.get(chart_id)
            if existing and existing.get("owner_user_id") != user_id:
                return {
                    "ok": False,
                    "error": "forbidden",
                    "message": "Chart owned by another user.",
                }
            if existing:
                chart["created_at"] = existing.get("created_at") or now
            self._user_charts[chart_id] = chart
            self._save_user_charts()
        return {"ok": True, "chart": chart}


_ATLAS: Optional[FormSpaceAtlas] = None


def get_atlas() -> FormSpaceAtlas:
    global _ATLAS
    if _ATLAS is None:
        _ATLAS = FormSpaceAtlas()
    return _ATLAS
