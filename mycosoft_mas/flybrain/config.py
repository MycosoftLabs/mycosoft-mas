"""FlyBrain settings. Environment only; no secrets, no hardcoded VM changes."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

DEFAULT_NAS_DIR = "/mnt/mycosoft-nas/models/flybrain"
COMPLETENESS_FILE = "2025_Completeness_783.csv"
CONNECTIVITY_PARQUET = "2025_Connectivity_783.parquet"
CONNECTIVITY_NPZ = "2025_Connectivity_783.npz"
ATLAS_FILE = "flybrain_atlas.yaml"

# SHA-256 of the FlyWire v783 files as published in eonsystemspbc/fly-brain (main, Sep 2026).
KNOWN_SHA256 = {
    COMPLETENESS_FILE: "52b0ac6094cd32c546f8d4c341e094376f48f4e791f8db9b166de5dff8199ea4",
    CONNECTIVITY_PARQUET: "efeb23fb99098e9c390f6869969b2a121a2ee92c833cfc45ecb2c1d8e1af0347",
}
UPSTREAM_RAW_BASE = "https://raw.githubusercontent.com/eonsystemspbc/fly-brain/main/data"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class FlyBrainSettings:
    data_dir: Path
    atlas_path: Path
    backend: str = "auto"
    dt_ms: float = 0.1
    default_window_ms: float = 50.0
    max_sessions: int = 8
    record_dir: Path = field(
        default_factory=lambda: _repo_root() / "data" / "flybrain" / "sessions"
    )
    droid_actuate: bool = False
    yolo_weights: str = "yolo26n.pt"
    yolo_device: str = "auto"
    yolo_conf: float = 0.25
    sahi_slice: int = 640
    sahi_overlap: float = 0.2
    remote_detector_url: Optional[str] = None
    mindex_api_url: str = "http://192.168.0.189:8000"
    camera_hfov_deg: float = 90.0
    autopilot_min_period_s: float = 0.2
    torch_threads: Optional[int] = None

    @property
    def completeness_path(self) -> Path:
        return self.data_dir / COMPLETENESS_FILE

    @property
    def connectivity_parquet_path(self) -> Path:
        return self.data_dir / CONNECTIVITY_PARQUET

    @property
    def connectivity_npz_path(self) -> Path:
        return self.data_dir / CONNECTIVITY_NPZ

    def candidate_data_dirs(self) -> List[Path]:
        return [self.data_dir]


def resolve_data_dir() -> Path:
    explicit = os.getenv("FLYBRAIN_DATA_DIR", "").strip()
    if explicit:
        return Path(explicit).expanduser()
    nas = Path(DEFAULT_NAS_DIR)
    if nas.exists():
        return nas
    return _repo_root() / "data" / "flybrain"


def get_settings() -> FlyBrainSettings:
    root = _repo_root()
    atlas = os.getenv("FLYBRAIN_ATLAS_PATH", "").strip()
    remote = (
        os.getenv("FLYBRAIN_REMOTE_DETECTOR_URL", "").strip()
        or os.getenv("PSATHYRELLA_CAM_DETECT_URL", "").strip()
    )
    threads = os.getenv("FLYBRAIN_TORCH_THREADS", "").strip()
    return FlyBrainSettings(
        data_dir=resolve_data_dir(),
        atlas_path=Path(atlas) if atlas else root / "config" / ATLAS_FILE,
        backend=os.getenv("FLYBRAIN_BACKEND", "auto").strip().lower() or "auto",
        dt_ms=float(os.getenv("FLYBRAIN_DT_MS", "0.1") or 0.1),
        default_window_ms=float(os.getenv("FLYBRAIN_WINDOW_MS", "50") or 50.0),
        max_sessions=int(os.getenv("FLYBRAIN_MAX_SESSIONS", "8") or 8),
        record_dir=Path(
            os.getenv("FLYBRAIN_RECORD_DIR", "").strip()
            or (root / "data" / "flybrain" / "sessions")
        ),
        droid_actuate=_env_flag("FLYBRAIN_DROID_ACTUATE", False),
        yolo_weights=os.getenv("FLYBRAIN_YOLO_WEIGHTS", "yolo26n.pt").strip() or "yolo26n.pt",
        yolo_device=os.getenv("FLYBRAIN_YOLO_DEVICE", "auto").strip() or "auto",
        yolo_conf=float(os.getenv("FLYBRAIN_YOLO_CONF", "0.25") or 0.25),
        sahi_slice=int(os.getenv("FLYBRAIN_SAHI_SLICE", "640") or 640),
        sahi_overlap=float(os.getenv("FLYBRAIN_SAHI_OVERLAP", "0.2") or 0.2),
        remote_detector_url=remote or None,
        mindex_api_url=(os.getenv("MINDEX_API_URL", "http://192.168.0.189:8000").rstrip("/")),
        camera_hfov_deg=float(os.getenv("FLYBRAIN_CAMERA_HFOV_DEG", "90") or 90.0),
        torch_threads=int(threads) if threads.isdigit() else None,
    )
