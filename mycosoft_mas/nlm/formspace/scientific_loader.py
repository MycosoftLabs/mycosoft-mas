"""Detect FormSpace / Nature Learning Model artifacts. Never Ollama or Llama GGUF."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Frozen ITDX v1.4 synthetic reference (preserve; do not overwrite).
LEGACY_MODEL_JSON_SHA256 = "1d3fe486d94507600f5c82e2be527ac9be42ff9a8a59586e7f158397a1a3b792"
LEGACY_WEIGHTS_SHA256 = "0c5fb815bf9b1e75a0e9aa27a3c373eb675d142a93e688b20d3f1084874091b2"

MIN_WEIGHT_BYTES = 10_000
CHAT_MARKERS = (
    "llama",
    "nemotron",
    "ollama",
    "gguf",
    "personaplex",
    "moshi",
)
FORECAST_READY_MARKERS = (
    "formspace-environmental-forecast",
    "formspace-nlm-forecast",
    "nature-learning-model-forecast",
    "onset-hazard",
)


@dataclass
class ScientificNLMProbe:
    model_loaded: bool
    model_dir: str
    reason: str
    weights_path: Optional[str] = None
    model_json_path: Optional[str] = None
    schema: Optional[str] = None
    is_legacy_reference: bool = False
    notes: List[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.notes is None:
            self.notes = []


# Shared NAS mount with MYCA chat GGUF. NLM owns only this subtree.
DEFAULT_NLM_HOME = "/mnt/mycosoft-nas/models/nlm"
FORBIDDEN_SUBTREES = (
    "/mnt/mycosoft-nas/models/myca",
    "/usr/share/ollama",
)
WEIGHT_SUFFIXES = {".pt", ".npz", ".bin", ".safetensors", ".pth", ".ckpt"}


def _candidate_dirs() -> List[Path]:
    env_dir = os.getenv("NLM_MODEL_DIR", "").strip()
    home = Path(os.getenv("NLM_HOME", DEFAULT_NLM_HOME))
    ordered = []
    if env_dir:
        ordered.append(Path(env_dir))
    ordered.extend(
        [
            home,
            home / "incoming",
            home / "reference",
            home / "archived",
            Path(DEFAULT_NLM_HOME),
            Path(DEFAULT_NLM_HOME) / "incoming",
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


def _looks_like_chat(path: Path, text: str) -> bool:
    blob = f"{path} {text}".lower().replace("\\", "/")
    if any(forbidden in blob for forbidden in FORBIDDEN_SUBTREES):
        return True
    if path.suffix.lower() == ".gguf":
        return True
    return any(marker in blob for marker in CHAT_MARKERS)


def _read_model_json(path: Path) -> Optional[dict]:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def probe_scientific_nlm(model_dir: Optional[str] = None) -> ScientificNLMProbe:
    """Return model_loaded=true only for new forecast artifacts. Legacy v1.4 stays frozen."""
    dirs = [Path(model_dir)] if model_dir else _candidate_dirs()
    notes: List[str] = []
    for directory in dirs:
        if _looks_like_chat(directory, ""):
            notes.append(f"ignored chat/GGUF path {directory}")
            continue
        if not directory.exists():
            continue
        model_json = directory / "model.json"
        weights = directory / "weights.pt"
        if any(directory.glob("*.gguf")):
            notes.append(f"ignored GGUF under {directory}; NLM never loads Llama/Nemotron")
            continue
        if not weights.is_file():
            for candidate in directory.glob("*.pt"):
                if _looks_like_chat(candidate, ""):
                    continue
                if candidate.stat().st_size >= MIN_WEIGHT_BYTES:
                    weights = candidate
                    break
        meta = _read_model_json(model_json)
        schema = str((meta or {}).get("schema") or "")
        combined = schema + json.dumps(meta or {}, sort_keys=True)
        if _looks_like_chat(directory, combined):
            notes.append(f"ignored chat/GGUF path {directory}")
            continue
        if not weights.is_file() or weights.stat().st_size < MIN_WEIGHT_BYTES:
            if directory.exists():
                notes.append(f"waiting for weights under {directory}")
            continue
        weights_sha = (meta or {}).get("weights_sha256")
        model_sha = (meta or {}).get("model_sha256")
        is_legacy = (
            str(weights_sha) == LEGACY_WEIGHTS_SHA256
            or str(model_sha) == LEGACY_MODEL_JSON_SHA256
            or schema == "formspace-environmental-reference/0.1.0"
        )
        if is_legacy:
            return ScientificNLMProbe(
                model_loaded=False,
                model_dir=str(directory),
                reason=(
                    "Found frozen ITDX v1.4 synthetic reference "
                    f"(model_sha256={LEGACY_MODEL_JSON_SHA256[:12]}…). "
                    "Preserved. Not the new forecast NLM. Waiting for Morgan weights."
                ),
                weights_path=str(weights),
                model_json_path=str(model_json) if model_json.is_file() else None,
                schema=schema or None,
                is_legacy_reference=True,
                notes=notes,
            )
        forecast_ready = any(marker in schema.lower() for marker in FORECAST_READY_MARKERS)
        if not forecast_ready:
            notes.append(
                f"weights present at {weights} but schema {schema or 'missing'} "
                "is not a forecast artifact"
            )
            continue
        return ScientificNLMProbe(
            model_loaded=True,
            model_dir=str(directory),
            reason="Forecast NLM artifacts present on the scientific path",
            weights_path=str(weights),
            model_json_path=str(model_json) if model_json.is_file() else None,
            schema=schema,
            is_legacy_reference=False,
            notes=notes,
        )
    return ScientificNLMProbe(
        model_loaded=False,
        model_dir=str(dirs[0]) if dirs else "",
        reason="No scientific forecast NLM weights yet. /api/nlm stays unloaded. Not Ollama.",
        notes=notes,
    )


def _sha256_file(path: Path) -> Optional[str]:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def _artifact_role(path: Path) -> str:
    blob = str(path).replace("\\", "/").lower()
    if "/reference/" in blob or blob.endswith("/reference"):
        return "reference"
    if "/incoming/" in blob:
        return "incoming"
    if "/archived/" in blob:
        return "archived"
    if "/data/" in blob:
        return "data"
    return "local"


def nlm_home() -> Path:
    return Path(os.getenv("NLM_HOME", DEFAULT_NLM_HOME))


def inventory_nlm_weights() -> Dict[str, Any]:
    """List every on-disk NLM artifact. Never GGUF/Ollama. Never invent forecast qualification."""
    home = nlm_home()
    roots = [
        home,
        home / "reference",
        home / "incoming",
        home / "archived",
        home / "data",
    ]
    env_dir = os.getenv("NLM_MODEL_DIR", "").strip()
    if env_dir:
        roots.append(Path(env_dir))

    artifacts: List[Dict[str, Any]] = []
    seen = set()
    notes: List[str] = []
    for root in roots:
        if _looks_like_chat(root, ""):
            notes.append(f"ignored chat/GGUF path {root}")
            continue
        if not root.exists():
            continue
        try:
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                if _looks_like_chat(path, ""):
                    notes.append(f"ignored chat/GGUF file {path}")
                    continue
                suffix = path.suffix.lower()
                if suffix not in WEIGHT_SUFFIXES and path.name != "model.json":
                    continue
                try:
                    key = str(path.resolve())
                except OSError:
                    key = str(path)
                if key in seen:
                    continue
                seen.add(key)
                stat = path.stat()
                sha = _sha256_file(path) if suffix in WEIGHT_SUFFIXES else None
                artifacts.append(
                    {
                        "name": path.name,
                        "path": str(path),
                        "role": _artifact_role(path),
                        "kind": "weights" if suffix in WEIGHT_SUFFIXES else "metadata",
                        "bytes": stat.st_size,
                        "modified_at": datetime.fromtimestamp(
                            stat.st_mtime, tz=timezone.utc
                        ).isoformat(),
                        "sha256": sha,
                        "is_legacy_reference": sha == LEGACY_WEIGHTS_SHA256,
                        "forecast_qualified": False,
                        "bound_to_ollama": False,
                    }
                )
        except OSError as exc:
            notes.append(f"scan failed under {root}: {exc}")

    artifacts.sort(key=lambda row: row.get("modified_at") or "", reverse=True)
    return {
        "home": str(home),
        "count": len(artifacts),
        "weights": artifacts,
        "bound_to_ollama": False,
        "forecast_qualified": False,
        "forecast_p": None,
        "notes": notes,
        "note": (
            "On-disk NLM artifacts only. No HuggingFace/Ollama pulls. "
            "Legacy reference is not a calibrated forecast. p stays null."
        ),
    }
