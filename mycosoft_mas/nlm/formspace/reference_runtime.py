"""Load the archived 25,728-param FormSpace checkpoint for algorithm replay.

Forecast qualification stays false. Fusarium p stays null. Never Ollama.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from .native_ssm import hazard_cumulative, inverse_variance_fusion, native_scan
from .scientific_loader import LEGACY_WEIGHTS_SHA256, DEFAULT_NLM_HOME

REFERENCE_PARAMS = 25728
REFERENCE_TENSORS = 47
REFERENCE_FAMILY = "native_tied_A_rank1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _candidate_reference_dirs() -> List[Path]:
    env_dir = os.getenv("NLM_MODEL_DIR", "").strip()
    home = Path(os.getenv("NLM_HOME", DEFAULT_NLM_HOME))
    ordered: List[Path] = []
    if env_dir:
        env_path = Path(env_dir)
        ordered.append(env_path)
        if env_path.name != "reference":
            ordered.append(env_path.parent / "reference")
    ordered.extend(
        [
            home / "reference",
            home / "archived",
            Path(DEFAULT_NLM_HOME) / "reference",
            Path(DEFAULT_NLM_HOME) / "archived",
        ]
    )
    seen = set()
    unique: List[Path] = []
    for path in ordered:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def locate_reference_dir(explicit: Optional[str] = None) -> Optional[Path]:
    dirs = [Path(explicit)] if explicit else _candidate_reference_dirs()
    for directory in dirs:
        weights = directory / "weights.pt"
        npz = directory / "reference_trained_weights.npz"
        if weights.is_file() or npz.is_file():
            return directory
    return None


@dataclass
class ReferenceRuntime:
    loaded: bool = False
    model_dir: str = ""
    weights_path: Optional[str] = None
    npz_path: Optional[str] = None
    model_json_path: Optional[str] = None
    weights_sha256: Optional[str] = None
    tensor_count: int = 0
    parameter_count: int = 0
    all_finite: bool = False
    family: str = REFERENCE_FAMILY
    training_origin: str = "SYNTHETIC_TEST"
    qualification_status: str = "candidate"
    forecast_qualified: bool = False
    warmup_status: str = "cold"
    chart_id: Optional[str] = None
    calibration_id: Optional[str] = None
    reason: str = "Reference checkpoint not loaded"
    tensors: Dict[str, np.ndarray] = field(default_factory=dict)
    state: float = 0.0

    @property
    def is_loaded(self) -> bool:
        return self.loaded and self.parameter_count == REFERENCE_PARAMS

    def reset_state(self) -> None:
        self.state = 0.0
        self.warmup_status = "reset"

    def load(self, model_dir: Optional[str] = None) -> bool:
        directory = locate_reference_dir(model_dir)
        if directory is None:
            self.reason = "No archived reference checkpoint on the NLM NAS path"
            self.loaded = False
            return False
        npz = directory / "reference_trained_weights.npz"
        weights = directory / "weights.pt"
        model_json = directory / "model.json"
        if not npz.is_file():
            self.reason = f"reference_trained_weights.npz missing under {directory}"
            self.loaded = False
            return False
        if weights.is_file():
            self.weights_sha256 = _sha256(weights)
            self.weights_path = str(weights)
            if self.weights_sha256 != LEGACY_WEIGHTS_SHA256:
                self.reason = (
                    "weights.pt hash does not match the archived reference; "
                    "refusing to treat it as the preserved checkpoint"
                )
                self.loaded = False
                return False
        arrays = np.load(npz, allow_pickle=False)
        tensors = {name: np.asarray(arrays[name], dtype=np.float32) for name in arrays.files}
        arrays.close()
        parameter_count = int(sum(int(arr.size) for arr in tensors.values()))
        finite = all(bool(np.isfinite(arr).all()) for arr in tensors.values())
        if parameter_count != REFERENCE_PARAMS or len(tensors) != REFERENCE_TENSORS or not finite:
            self.reason = (
                f"Reference inventory mismatch tensors={len(tensors)} "
                f"params={parameter_count} finite={finite}"
            )
            self.loaded = False
            return False
        meta: Dict[str, Any] = {}
        if model_json.is_file():
            try:
                loaded_meta = json.loads(model_json.read_text(encoding="utf-8"))
                if isinstance(loaded_meta, dict):
                    meta = loaded_meta
            except (OSError, json.JSONDecodeError):
                meta = {}
        atlas = meta.get("atlas") if isinstance(meta.get("atlas"), dict) else {}
        self.loaded = True
        self.model_dir = str(directory)
        self.npz_path = str(npz)
        self.model_json_path = str(model_json) if model_json.is_file() else None
        self.tensor_count = len(tensors)
        self.parameter_count = parameter_count
        self.all_finite = finite
        self.tensors = tensors
        self.chart_id = str(atlas.get("chart_id") or "environmental-ssm32/v1")
        self.calibration_id = "reference-temperature-conformal/v1"
        self.warmup_status = "cold"
        self.reason = (
            "Archived synthetic reference loaded for algorithm replay. "
            "Not a calibrated Fusarium forecast. p stays null."
        )
        return True

    def replay(self, inputs: Optional[Sequence[float]] = None) -> Dict[str, Any]:
        if not self.is_loaded:
            return {
                "ok": False,
                "p": None,
                "reason": self.reason,
                "forecast_qualified": False,
            }
        series = list(inputs) if inputs else [1.0, 2.0, 3.0, 4.0]
        a_log = self.tensors.get("sequence.blocks.0.A_log")
        a = -float(np.exp(a_log[0])) if a_log is not None and a_log.size else -2.0
        full, state = native_scan(series, dt=0.1, a=a, b=0.5, h=self.state)
        first, mid = native_scan(series[:2], dt=0.1, a=a, b=0.5, h=self.state)
        second, _ = native_scan(series[2:], dt=0.1, a=a, b=0.5, h=mid)
        chunk_err = max(abs(x - y) for x, y in zip(full, first + second)) if full else 0.0
        fused_mean, fused_var = inverse_variance_fusion([25.0, 27.0], [1.0, 4.0])
        self.state = state
        self.warmup_status = "warm"
        return {
            "ok": True,
            "p": None,
            "forecast_qualified": False,
            "training_origin": self.training_origin,
            "architecture_family": self.family,
            "weights_sha256": self.weights_sha256,
            "parameter_count": self.parameter_count,
            "tensor_count": self.tensor_count,
            "chart_id": self.chart_id,
            "calibration_id": self.calibration_id,
            "native_a": a,
            "stream_state": state,
            "chunk_abs_error": chunk_err,
            "fusion_mean": fused_mean,
            "fusion_variance": fused_var,
            "hazard_cumulative_math": hazard_cumulative([0.1, 0.2, 0.3]),
            "supported_targets": ["synthetic_pattern_replay"],
            "supported_modalities": ["scalar_environmental_chart"],
            "note": "Replay only. Not Fusarium p. Not P(truth).",
        }

    def weka_features(self) -> Dict[str, Any]:
        replay = self.replay()
        if not replay.get("ok"):
            return {
                "ok": False,
                "arff": None,
                "reason": replay.get("reason"),
                "rows": [],
            }
        a_log = self.tensors["sequence.blocks.0.A_log"]
        rows = [
            {
                "feature": "block0_A_log_0",
                "value": float(a_log[0]),
                "evidence_kind": "synthetic_parameter",
                "class": "reference_replay",
            },
            {
                "feature": "fusion_mean",
                "value": float(replay["fusion_mean"]),
                "evidence_kind": "derived_math",
                "class": "reference_replay",
            },
            {
                "feature": "chunk_abs_error",
                "value": float(replay["chunk_abs_error"]),
                "evidence_kind": "derived_math",
                "class": "reference_replay",
            },
        ]
        arff = [
            "% Mycosoft NLM reference replay features. Not live COP rows.",
            "@RELATION nlm_reference_replay",
            "@ATTRIBUTE feature string",
            "@ATTRIBUTE value numeric",
            "@ATTRIBUTE evidence_kind {synthetic_parameter,derived_math}",
            "@ATTRIBUTE class {reference_replay}",
            "@DATA",
        ]
        for row in rows:
            arff.append(
                f"'{row['feature']}',{row['value']},{row['evidence_kind']},{row['class']}"
            )
        return {
            "ok": True,
            "rows": rows,
            "arff": "\n".join(arff) + "\n",
            "weights_sha256": self.weights_sha256,
            "p": None,
            "note": "Weka may evaluate these frozen features. They are not Fusarium labels.",
        }

    def runtime_status(self) -> Dict[str, Any]:
        return {
            "model_loaded": self.is_loaded,
            "model_id": "formspace-environmental-reference/0.1.0" if self.is_loaded else None,
            "architecture_family": self.family,
            "weights_sha256": self.weights_sha256,
            "calibration_id": self.calibration_id if self.is_loaded else None,
            "chart_ids": [self.chart_id] if self.chart_id else [],
            "supported_targets": ["synthetic_pattern_replay"] if self.is_loaded else [],
            "supported_modalities": ["scalar_environmental_chart"] if self.is_loaded else [],
            "training_origin": "synthetic",
            "runtime_precision": "float32",
            "qualification_status": self.qualification_status if self.is_loaded else "unloaded",
            "forecast_qualified": False,
            "warmup_status": self.warmup_status if self.is_loaded else "cold",
            "parameter_count": self.parameter_count,
            "tensor_count": self.tensor_count,
            "model_dir": self.model_dir,
            "reason": self.reason,
        }


_RUNTIME: Optional[ReferenceRuntime] = None


def get_reference_runtime() -> ReferenceRuntime:
    global _RUNTIME
    if _RUNTIME is None:
        _RUNTIME = ReferenceRuntime()
    return _RUNTIME


def load_reference_runtime(model_dir: Optional[str] = None) -> ReferenceRuntime:
    runtime = get_reference_runtime()
    if not runtime.is_loaded:
        runtime.load(model_dir)
    return runtime
