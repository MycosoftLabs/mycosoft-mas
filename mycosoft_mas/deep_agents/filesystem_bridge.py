"""
Virtual filesystem context bridge for Deep Agents.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List


def _safe_list_files(root: Path, pattern: str, limit: int) -> List[str]:
    if not root.exists():
        return []
    return [str(path) for path in sorted(root.glob(pattern), reverse=True)[:limit]]


def build_multimodal_context() -> Dict[str, Any]:
    """
    Build non-blocking multimodal context pointers.

    This only surfaces file references, never raw binary payloads.
    """
    voice_transcripts_dir = Path(
        os.getenv("MYCA_VOICE_TRANSCRIPTS_DIR", "data/personaplex/transcripts")
    )
    mycobrain_capture_dir = Path(os.getenv("MYCA_MYCOBRAIN_CAPTURE_DIR", "data/mycobrain/captures"))

    return {
        "voice_transcripts": _safe_list_files(voice_transcripts_dir, "*.json*", limit=20),
        "mycobrain_sensor_captures": _safe_list_files(mycobrain_capture_dir, "*", limit=20),
    }
