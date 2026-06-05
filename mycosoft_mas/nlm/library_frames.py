"""
Resolve MINDEX library blobs into NLM WaveformRef and frame metadata.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from mycosoft_mas.integrations.mindex_library_client import MindexLibraryClient


def waveform_ref_from_blob(blob: Dict[str, Any]) -> Dict[str, Any]:
    """Build a serializable WaveformRef dict from a library blob record."""
    return {
        "mindex_id": str(blob.get("id") or ""),
        "sample_rate_hz": int(blob.get("sample_rate_hz") or 0),
        "duration_seconds": float(blob.get("duration_sec") or 0.0),
        "channel_count": int(blob.get("channels") or 1),
        "content_hash": b"",
        "filename": blob.get("filename"),
        "label_primary": blob.get("label_primary"),
        "stream_url": blob.get("stream_url"),
    }


async def resolve_waveform_ref(
    blob_id: str,
    client: Optional[MindexLibraryClient] = None,
) -> Dict[str, Any]:
    """Fetch blob from MINDEX and return WaveformRef-shaped dict."""
    lib = client or MindexLibraryClient()
    blob = await lib.get_blob(blob_id)
    ref = waveform_ref_from_blob(blob)
    if not ref.get("stream_url"):
        ref["stream_url"] = lib.stream_url(blob_id)
    return ref


async def build_library_frame_extras(
    blob_id: str,
    *,
    classify: bool = False,
    client: Optional[MindexLibraryClient] = None,
) -> Dict[str, Any]:
    """
    Attach library_blob_id, waveform_refs, labels, and optional SINE classification.
    """
    lib = client or MindexLibraryClient()
    blob = await lib.get_blob(blob_id)
    extras: Dict[str, Any] = {
        "library_blob_id": blob_id,
        "waveform_refs": [waveform_ref_from_blob(blob)],
        "blob_metadata": {
            "filename": blob.get("filename"),
            "label_primary": blob.get("label_primary"),
            "duration_sec": blob.get("duration_sec"),
            "sample_rate_hz": blob.get("sample_rate_hz"),
            "origin_dataset_id": blob.get("origin_dataset_id"),
        },
    }
    human = blob.get("latest_human_identification") or {}
    if human:
        extras["human_label"] = human.get("human_label")
        extras["human_category"] = human.get("human_category")
        extras["training_eligible"] = human.get("training_eligible")
    if classify:
        extras["sine_classification"] = await lib.classify_blob(blob_id)
    return extras


def waveform_refs_to_nlm(waveform_ref_dicts: List[Dict[str, Any]]) -> List[Any]:
    """Convert dict refs to NLM WaveformRef dataclass instances when package is installed."""
    try:
        from nlm.core.frames import WaveformRef

        refs = []
        for item in waveform_ref_dicts:
            refs.append(
                WaveformRef(
                    mindex_id=str(item.get("mindex_id") or ""),
                    content_hash=item.get("content_hash") or b"",
                    sample_rate_hz=int(item.get("sample_rate_hz") or 0),
                    duration_seconds=float(item.get("duration_seconds") or 0.0),
                    channel_count=int(item.get("channel_count") or 1),
                )
            )
        return refs
    except ImportError:
        return waveform_ref_dicts
