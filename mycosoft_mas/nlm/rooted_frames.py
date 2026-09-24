"""
RootedNatureFrame storage — NAS binaries + content hashes for MINDEX timeline.

Plan path: NAS mindex/Library/** for binaries; DB holds hashes + storage_ref only.
No mock frames. Empty timeline when none exist.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from mycosoft_mas.nlm.merkle_attest import attest_payloads, leaf_hash

logger = logging.getLogger(__name__)

DEFAULT_NAS_LIBRARY = "/mnt/mycosoft-nas/mindex/Library/nlm/rooted_frames"
FORBIDDEN = ("/mnt/mycosoft-nas/models/myca",)


def _library_root() -> Path:
    env = (os.getenv("NLM_ROOTED_FRAMES_DIR") or "").strip()
    if env:
        return Path(env)
    nas = Path(os.getenv("NLM_NAS_LIBRARY", DEFAULT_NAS_LIBRARY))
    if nas.exists() or os.name != "nt":
        return nas
    # Dev PC fallback (still real FS — not mock data)
    return Path.home() / ".mycosoft" / "nlm" / "library" / "rooted_frames"


def _ensure_library() -> Path:
    root = _library_root()
    root.mkdir(parents=True, exist_ok=True)
    index = root / "timeline_index.jsonl"
    if not index.exists():
        index.write_text("", encoding="utf-8")
    return root


def write_rooted_frame(
    *,
    device_id: str,
    sensor_id: Optional[str],
    protocol: Optional[Dict[str, Any]],
    payload: Dict[str, Any],
    source: str = "nlm_ingest",
) -> Dict[str, Any]:
    """
    Persist a rooted frame binary on NAS and return hashes + storage_ref.
    Rejects empty payloads (no invented samples).
    """
    if not payload:
        raise ValueError("rooted_frame_requires_real_payload")
    for bad in FORBIDDEN:
        if bad in str(_library_root()):
            raise ValueError("rooted_frames_must_not_use_myca_tree")

    root = _ensure_library()
    now = datetime.now(timezone.utc)
    frame_id = f"rnf_{now.strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:10]}"
    day = now.strftime("%Y/%m/%d")
    dest_dir = root / day
    dest_dir.mkdir(parents=True, exist_ok=True)

    record = {
        "frame_id": frame_id,
        "kind": "RootedNatureFrame",
        "model_kind": "nature_learning_model",
        "bound_to_ollama": False,
        "device_id": device_id,
        "sensor_id": sensor_id,
        "protocol": protocol or {},
        "source": source,
        "created_at": now.isoformat(),
        "payload": payload,
    }
    body = json.dumps(record, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    path = dest_dir / f"{frame_id}.json"
    path.write_bytes(body)

    content_sha256 = leaf_hash(record)
    attestation = attest_payloads([record], producer_id="mas-nlm-rooted-frames")
    storage_ref = str(path).replace("\\", "/")

    index_row = {
        "frame_id": frame_id,
        "device_id": device_id,
        "sensor_id": sensor_id,
        "created_at": now.isoformat(),
        "sha256": content_sha256,
        "merkle_root": attestation.get("merkle_root"),
        "storage_ref": storage_ref,
        "signed": bool((attestation.get("signature") or {}).get("signed")),
    }
    with (_ensure_library() / "timeline_index.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(index_row, default=str) + "\n")

    return {
        "ok": True,
        "frame_id": frame_id,
        "sha256": content_sha256,
        "merkle_root": attestation.get("merkle_root"),
        "signature": attestation.get("signature"),
        "inclusion_proofs": attestation.get("inclusion_proofs"),
        "storage_ref": storage_ref,
        "zk_proof": None,
        "zk_note": attestation.get("zk_note"),
        "index": index_row,
    }


async def write_rooted_frame_async(
    *,
    device_id: str,
    sensor_id: Optional[str],
    protocol: Optional[Dict[str, Any]],
    payload: Dict[str, Any],
    source: str = "nlm_ingest",
) -> Dict[str, Any]:
    """NAS write + best-effort MINDEX SQL mirror."""
    written = write_rooted_frame(
        device_id=device_id,
        sensor_id=sensor_id,
        protocol=protocol,
        payload=payload,
        source=source,
    )
    try:
        import httpx

        mindex = os.getenv("MINDEX_API_URL", "http://192.168.0.189:8000").rstrip("/")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        token = (
            os.getenv("MINDEX_INTERNAL_TOKEN")
            or (os.getenv("MINDEX_INTERNAL_TOKENS", "").split(",")[0] or "")
        ).strip()
        key = (os.getenv("MINDEX_API_KEY") or os.getenv("MINDEX_INTERNAL_KEY") or "").strip()
        if token:
            headers["X-Internal-Token"] = token
        if key:
            headers["X-API-Key"] = key
        body = {
            "frame_id": written["frame_id"],
            "device_id": device_id,
            "sensor_id": sensor_id,
            "protocol": protocol or {},
            "sha256": written["sha256"],
            "merkle_root": written.get("merkle_root"),
            "storage_ref": written["storage_ref"],
            "signed": bool((written.get("signature") or {}).get("signed")),
            "source": source,
            "labels": {"model_kind": "nature_learning_model"},
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(f"{mindex}/nlm/rooted-frames", json=body, headers=headers)
            written["mindex"] = (
                resp.json() if resp.status_code < 500 else {"status_code": resp.status_code}
            )
    except Exception as exc:
        logger.debug("MINDEX rooted-frame mirror skipped: %s", exc)
        written["mindex"] = None
    return written


def list_timeline(*, limit: int = 50, device_id: Optional[str] = None) -> Dict[str, Any]:
    """Read rooted-frame timeline index. Empty when none — not mock."""
    root = _library_root()
    index_path = root / "timeline_index.jsonl"
    rows: List[Dict[str, Any]] = []
    if index_path.exists():
        lines = index_path.read_text(encoding="utf-8").splitlines()
        for line in reversed(lines):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if device_id and row.get("device_id") != device_id:
                continue
            rows.append(row)
            if len(rows) >= max(1, min(limit, 500)):
                break
    return {
        "status": "ok",
        "empty": len(rows) == 0,
        "count": len(rows),
        "frames": rows,
        "library_root": str(root).replace("\\", "/"),
        "message": None if rows else "No rooted frames on NAS timeline yet.",
        "model_kind": "nature_learning_model",
    }


def get_frame(frame_id: str) -> Optional[Dict[str, Any]]:
    timeline = list_timeline(limit=500)
    for row in timeline.get("frames") or []:
        if row.get("frame_id") == frame_id:
            ref = row.get("storage_ref")
            if ref and Path(ref).exists():
                return {
                    "ok": True,
                    "index": row,
                    "frame": json.loads(Path(ref).read_text(encoding="utf-8")),
                }
            return {"ok": True, "index": row, "frame": None, "missing_binary": True}
    return None
