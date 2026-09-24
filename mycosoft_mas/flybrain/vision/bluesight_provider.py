"""BlueSight ``DetectionProvider`` adapters for the FlyBrain vision stack (spec §9).

* ``Yolo26SahiProvider`` (``"yolo26_sahi"``): raw YOLO26 + SAHI boxes.
* ``FlyBrainVisionProvider`` (``"flybrain_vision"``): same detector, plus ontology
  enrichment (category, bearing/range/location when the packet carries a pose,
  cached MINDEX taxon → ``linked_entity``).

Both read ``packet.frame_ref`` as a local file path or an ``http(s)`` URL. An
unreadable frame, a missing detector or any inference failure yields ``[]`` —
never an invented detection — but the failure is never silent: it is logged at
WARNING, exposed on the provider as ``last_error`` / ``healthy``, and stamped into
``packet.metadata[DETECTOR_STATUS_KEY]`` so the persisted ``BlueSightObservation``
says "detector did not run" rather than "detector ran and saw nothing".

``register_flybrain_providers(registry)`` injects both into a
``ProviderRegistry`` without touching the bluesight package.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from mycosoft_mas.bluesight.providers import ProviderRegistry
from mycosoft_mas.flybrain.schemas import Detection, DetectionFrame
from mycosoft_mas.flybrain.vision.detector import (
    DetectorUnavailable,
    FlyBrainDetector,
    get_detector,
)
from mycosoft_mas.schemas.bluesight import (
    BlueSightDetection,
    BlueSightLinkedEntity,
    BlueSightSensorPacket,
)

logger = logging.getLogger(__name__)

PROVIDER_NAMES = ("yolo26_sahi", "flybrain_vision")
DETECTOR_STATUS_KEY = "flybrain_detector"
FRAME_FETCH_TIMEOUT_S = 4.0
MAX_FRAME_BYTES = 32 * 1024 * 1024


def _is_http_url(ref: str) -> bool:
    try:
        parsed = urlparse(ref)
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def read_frame_ref(
    frame_ref: Optional[str], *, timeout_s: float = FRAME_FETCH_TIMEOUT_S
) -> Optional[bytes]:
    """Return the frame bytes for a local path or http(s) URL, or ``None`` if unreadable."""
    if not frame_ref or not isinstance(frame_ref, str):
        return None
    ref = frame_ref.strip()
    if not ref:
        return None
    if ref.startswith("file://"):
        ref = ref[len("file://") :]
    if _is_http_url(ref):
        try:
            import httpx
        except ImportError:
            logger.warning("httpx not installed; cannot fetch frame_ref %s", ref)
            return None
        try:
            with httpx.Client(timeout=timeout_s, follow_redirects=True) as client:
                response = client.get(ref)
            if response.status_code >= 400 or not response.content:
                return None
            if len(response.content) > MAX_FRAME_BYTES:
                return None
            return response.content
        except Exception as exc:  # noqa: BLE001
            logger.debug("frame_ref fetch failed (%s): %s", ref, exc)
            return None
    path = os.path.expanduser(ref)
    if not os.path.isfile(path):
        return None
    try:
        if os.path.getsize(path) > MAX_FRAME_BYTES:
            return None
        with open(path, "rb") as fh:
            return fh.read()
    except OSError:
        return None


def _pose_from_packet(packet: BlueSightSensorPacket) -> Optional[Dict[str, Any]]:
    for container in (packet.payload, packet.metadata):
        if not isinstance(container, dict):
            continue
        pose = container.get("pose")
        if isinstance(pose, dict) and pose:
            return dict(pose)
        if any(k in container for k in ("lat", "lon", "heading_deg")):
            return {
                k: container[k] for k in ("lat", "lon", "heading_deg", "hfov_deg") if k in container
            }
    return None


def to_bluesight_detection(
    packet: BlueSightSensorPacket, det: Detection, frame: DetectionFrame, *, enriched: bool
) -> BlueSightDetection:
    x1, y1, x2, y2 = det.bbox_xyxy
    attributes: Dict[str, Any] = {
        "category": det.category,
        "engine": frame.engine,
        "model": frame.model,
        "sahi": frame.sahi,
        "slices": frame.slices,
        "bbox_units": "pixels",
        "frame_w": det.attributes.get("frame_w", frame.frame_w),
        "frame_h": det.attributes.get("frame_h", frame.frame_h),
        "origin": "detector",
    }
    if det.bbox_norm is not None:
        attributes["bbox_norm"] = list(det.bbox_norm)
    if enriched:
        attributes.update(
            {
                "bearing_deg": det.bearing_deg,
                "range_m": det.range_m,
                "range_source": det.range_source,
                "location": det.location.model_dump() if det.location else None,
                "perimeter": det.perimeter,
                "pathway": det.pathway,
            }
        )
        if det.taxon is not None:
            attributes["taxon"] = det.taxon.model_dump()
    linked: Optional[BlueSightLinkedEntity] = None
    if det.taxon is not None and det.taxon.matched and det.taxon.taxon_id:
        linked = BlueSightLinkedEntity(
            type="taxon", id=det.taxon.taxon_id, taxon_id=det.taxon.taxon_id
        )
    return BlueSightDetection(
        detection_id=f"{packet.frame_id}:{det.id}",
        class_name=det.cls,
        confidence=det.conf,
        track_id=det.track_id,
        bbox_xyxy=(x1, y1, x2, y2),
        centroid_xy=((x1 + x2) / 2.0, (y1 + y2) / 2.0),
        linked_entity=linked,
        visual_label=det.taxon.scientific_name if (det.taxon and det.taxon.matched) else det.cls,
        attributes=attributes,
    )


@dataclass
class Yolo26SahiProvider:
    """Raw YOLO26 + SAHI detections on ``packet.frame_ref``."""

    name: str = "yolo26_sahi"
    detector: Optional[FlyBrainDetector] = None
    sahi: bool = True
    enrich: bool = field(default=False)
    #: Reason the most recent ``detect()`` call could not run the detector; ``None`` after a
    #: call in which the detector actually ran (even if it found nothing).
    last_error: Optional[str] = field(default=None, init=False)

    @property
    def healthy(self) -> bool:
        """``True`` only if the most recent ``detect()`` call actually ran the detector."""
        return self.last_error is None

    def _detector(self) -> FlyBrainDetector:
        return self.detector if self.detector is not None else get_detector()

    def _fail(
        self, packet: BlueSightSensorPacket, status: str, reason: str
    ) -> List[BlueSightDetection]:
        """Record a did-not-run outcome loudly and return the (honest) empty list."""
        self.last_error = f"{status}: {reason}"
        logger.warning(
            "%s: detector did not run for frame %s (%s): %s",
            self.name,
            packet.frame_id,
            status,
            reason,
        )
        if isinstance(packet.metadata, dict):
            packet.metadata[DETECTOR_STATUS_KEY] = {
                "provider": self.name,
                "ran": False,
                "healthy": False,
                "status": status,
                "reason": reason,
            }
        return []

    def _mark_ran(self, packet: BlueSightSensorPacket, frame: DetectionFrame) -> None:
        self.last_error = None
        if isinstance(packet.metadata, dict):
            packet.metadata[DETECTOR_STATUS_KEY] = {
                "provider": self.name,
                "ran": True,
                "healthy": True,
                "status": "ok",
                "engine": frame.engine,
                "model": frame.model,
            }

    def detect(self, packet: BlueSightSensorPacket) -> List[BlueSightDetection]:
        image = read_frame_ref(packet.frame_ref)
        if image is None:
            return self._fail(
                packet, "frame_unreadable", f"frame_ref unreadable: {packet.frame_ref!r}"
            )
        detector = self._detector()
        pose = _pose_from_packet(packet) if self.enrich else None
        try:
            frame = detector.detect(image, sahi=self.sahi, pose=pose, source=str(packet.source))
        except DetectorUnavailable as exc:
            return self._fail(packet, "detector_unavailable", str(exc))
        except (ValueError, TypeError, OSError) as exc:
            return self._fail(packet, "frame_undecodable", str(exc))
        if not frame.available:
            return self._fail(
                packet, "detector_unavailable", frame.note or "frame.available is False"
            )
        self._mark_ran(packet, frame)
        return [
            to_bluesight_detection(packet, det, frame, enriched=self.enrich)
            for det in frame.detections
        ]


@dataclass
class FlyBrainVisionProvider(Yolo26SahiProvider):
    """YOLO26 + SAHI plus ontology enrichment (category, geometry from packet pose, taxon)."""

    name: str = "flybrain_vision"
    enrich: bool = field(default=True)


def register_flybrain_providers(
    registry: ProviderRegistry, *, detector: Optional[FlyBrainDetector] = None
) -> List[str]:
    """Add ``yolo26_sahi`` and ``flybrain_vision`` to ``registry`` (no bluesight edits)."""
    providers = [
        Yolo26SahiProvider(detector=detector),
        FlyBrainVisionProvider(detector=detector),
    ]
    store = getattr(registry, "_providers", None)
    if not isinstance(store, dict):
        raise TypeError("registry has no _providers mapping; is it a bluesight ProviderRegistry?")
    names: List[str] = []
    for provider in providers:
        store[provider.name] = provider
        names.append(provider.name)
    return names


__all__ = [
    "DETECTOR_STATUS_KEY",
    "FlyBrainVisionProvider",
    "PROVIDER_NAMES",
    "Yolo26SahiProvider",
    "read_frame_ref",
    "register_flybrain_providers",
    "to_bluesight_detection",
]
