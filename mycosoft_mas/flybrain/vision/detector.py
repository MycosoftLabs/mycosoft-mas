"""YOLO26 + SAHI detector with honest unavailability (spec §9).

Backends, probed lazily:

* ``ultralytics`` — ``from ultralytics import YOLO``; weights ``FLYBRAIN_YOLO_WEIGHTS``
  (default ``yolo26n.pt``). The model is constructed on the first ``detect()`` (or on
  ``health(probe_model=True)``) so a download/IO failure (air-gapped VM) is caught and
  surfaced in ``health().reason``. ``health()`` never claims ``available=True`` for an
  unverified model unless the weights file is at least present on disk.
  SAHI uses the ``sahi`` library when importable, else ``vision/slicing.py``.
* MINDEX taxa (spec §9): ``adetect()`` / ``asnapshot()`` run the backend in a worker
  thread and then ``await aenrich(...)`` with the detector's ``TaxonResolver``; the
  sync ``detect()`` / ``snapshot()`` attach only already-cached taxa (no network).
* ``remote`` — ``RemoteDetector(url)`` against the Jetson ``:8792/detect`` shape
  (GET snapshot; POST multipart image when the remote accepts it).
* ``none`` — nothing; ``available=False`` and ``detect()`` raises ``DetectorUnavailable``.

Class names always come from the model (``model.names`` / the remote payload).
There are no synthetic boxes anywhere in this file.

All heavy imports (numpy, PIL, httpx, ultralytics, sahi, torch) are local to the
methods that use them so this module imports under ``MAS_LIGHT_IMPORT=1`` and when
none of them is installed.
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from mycosoft_mas.flybrain.config import FlyBrainSettings, get_settings
from mycosoft_mas.flybrain.schemas import Detection, DetectionFrame, VisionHealth

logger = logging.getLogger(__name__)

BACKENDS = ("auto", "ultralytics", "remote", "none")
REMOTE_PROBE_TTL_S = 30.0
DEFAULT_REMOTE_SOURCE = "quad360"


class DetectorUnavailable(RuntimeError):
    """Raised when no detector backend can produce a real detection."""


def _now_ms() -> float:
    return time.time() * 1000.0


def _iso_to_ms(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp() * 1000.0
    except ValueError:
        return None


def _num(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if out != out or out in (float("inf"), float("-inf")):
        return None
    return out


# ---------------------------------------------------------------------------
# Remote detector (Jetson /detect)
# ---------------------------------------------------------------------------


class RemoteDetector:
    """Client for a remote ``/detect`` service.

    Verified payload (website ``camera/[feedId]/detections/route.ts``, Aug 2026)::

        { ok, ts, engine, deepstream, device, note, license?, sahi?,
          detections: [ {source, class, confidence, bbox:[x1,y1,x2,y2], trackId?} ],
          frames: { source: {frameW, frameH} }, frameW?, frameH? }

    ``bbox`` is absolute pixels, corner form, on the tagged ``source`` surface; every
    source has its own coordinate space, so per-detection frame dims are recorded in
    ``Detection.attributes["frame_w"/"frame_h"]`` and ``bbox_norm`` is computed per
    source. Untagged boxes are attributed to ``default_source``.

    ``transport`` is an optional ``httpx`` transport (tests inject ``httpx.MockTransport``).
    """

    def __init__(
        self,
        url: str,
        *,
        timeout_s: float = 4.0,
        transport: Any = None,
        default_source: str = DEFAULT_REMOTE_SOURCE,
        retries: int = 2,
    ) -> None:
        self.url = (url or "").strip()
        self.timeout_s = float(timeout_s)
        self._transport = transport
        self.default_source = default_source
        self.retries = max(1, int(retries))
        self._probe_cache: Optional[Tuple[float, bool, str]] = None
        self.last_error: str = ""

    # -- transport ----------------------------------------------------------

    def _client(self) -> Any:
        try:
            import httpx
        except ImportError as exc:  # pragma: no cover - httpx is a MAS dependency
            raise DetectorUnavailable("httpx not installed; remote detector unusable") from exc
        kwargs: Dict[str, Any] = {"timeout": self.timeout_s}
        if self._transport is not None:
            kwargs["transport"] = self._transport
        return httpx.Client(**kwargs)

    def _get_json(self) -> Dict[str, Any]:
        last_exc: Optional[BaseException] = None
        # The dev-PC → Jetson link has a documented first-SYN stall; retry fresh.
        for _ in range(self.retries):
            try:
                with self._client() as client:
                    response = client.get(self.url, headers={"Accept": "application/json"})
                if response.status_code >= 400:
                    raise DetectorUnavailable(
                        f"remote detector HTTP {response.status_code} from {self.url}"
                    )
                data = response.json()
                if not isinstance(data, dict):
                    raise DetectorUnavailable("remote detector returned a non-object payload")
                return data
            except DetectorUnavailable:
                raise
            except Exception as exc:  # noqa: BLE001 - transport failure
                last_exc = exc
        self.last_error = f"{type(last_exc).__name__}: {str(last_exc)[:160]}"
        raise DetectorUnavailable(f"remote detector unreachable at {self.url}: {self.last_error}")

    def probe(self, force: bool = False) -> Tuple[bool, str]:
        """GET the endpoint once (cached ``REMOTE_PROBE_TTL_S``); ``(ok, reason)``."""
        now = time.monotonic()
        if not force and self._probe_cache and (now - self._probe_cache[0]) < REMOTE_PROBE_TTL_S:
            return self._probe_cache[1], self._probe_cache[2]
        if not self.url:
            result = (False, "remote detector URL not configured")
        else:
            try:
                data = self._get_json()
                ok = bool(data.get("ok", True)) and isinstance(data.get("detections", []), list)
                reason = "" if ok else f"remote detector reported ok={data.get('ok')!r}"
                if ok and data.get("engine"):
                    reason = ""
                result = (ok, reason)
            except DetectorUnavailable as exc:
                result = (False, str(exc))
        self._probe_cache = (now, result[0], result[1])
        return result

    # -- payload mapping ----------------------------------------------------

    def parse_payload(
        self, raw: Dict[str, Any], *, source: Optional[str] = None, t_ms: Optional[float] = None
    ) -> DetectionFrame:
        frames_raw = raw.get("frames") if isinstance(raw.get("frames"), dict) else {}
        dims: Dict[str, Tuple[Optional[int], Optional[int]]] = {}
        for name, entry in (frames_raw or {}).items():
            if not isinstance(entry, dict):
                continue
            fw = _num(entry.get("frameW", entry.get("frame_w")))
            fh = _num(entry.get("frameH", entry.get("frame_h")))
            dims[str(name)] = (
                int(fw) if fw and fw > 0 else None,
                int(fh) if fh and fh > 0 else None,
            )
        top_w = _num(raw.get("frameW", raw.get("frame_w")))
        top_h = _num(raw.get("frameH", raw.get("frame_h")))

        detections: List[Detection] = []
        raw_dets = raw.get("detections") if isinstance(raw.get("detections"), list) else []
        for i, d in enumerate(raw_dets):
            if not isinstance(d, dict):
                continue
            bbox = d.get("bbox")
            if not isinstance(bbox, (list, tuple)) or len(bbox) < 4:
                continue
            coords = [_num(v) for v in bbox[:4]]
            if any(c is None for c in coords):
                continue
            x1, y1, x2, y2 = coords  # type: ignore[misc]
            conf = _num(d.get("confidence", d.get("conf")))
            cls = d.get("class", d.get("cls"))
            if conf is None or not cls:
                continue
            conf = min(max(conf, 0.0), 1.0)
            det_source = str(d.get("source") or self.default_source)
            if source and det_source != source:
                continue
            fw, fh = dims.get(det_source, (None, None))
            if fw is None and top_w and top_w > 0:
                fw = int(top_w)
            if fh is None and top_h and top_h > 0:
                fh = int(top_h)
            track_raw = d.get("trackId", d.get("track_id"))
            track_id = None if track_raw is None else str(track_raw)
            box = (
                float(min(x1, x2)),
                float(min(y1, y2)),
                float(max(x1, x2)),
                float(max(y1, y2)),
            )
            bbox_norm = None
            if fw and fh:
                bbox_norm = (
                    min(max(box[0] / fw, 0.0), 1.0),
                    min(max(box[1] / fh, 0.0), 1.0),
                    min(max(box[2] / fw, 0.0), 1.0),
                    min(max(box[3] / fh, 0.0), 1.0),
                )
            attributes: Dict[str, Any] = {"bbox_units": "pixels"}
            if fw is not None:
                attributes["frame_w"] = fw
            if fh is not None:
                attributes["frame_h"] = fh
            detections.append(
                Detection(
                    id=f"{det_source}:{i}",
                    cls=str(cls),
                    conf=conf,
                    bbox_xyxy=box,
                    bbox_norm=bbox_norm,
                    source=det_source,
                    track_id=track_id,
                    attributes=attributes,
                )
            )

        # Frame-level dims: the requested source, else the default source, else a
        # single-source payload, else the top-level dims.
        frame_w: Optional[int] = None
        frame_h: Optional[int] = None
        pick = source or (self.default_source if self.default_source in dims else None)
        if pick is None and len(dims) == 1:
            pick = next(iter(dims))
        if pick and pick in dims:
            frame_w, frame_h = dims[pick]
        if frame_w is None and top_w and top_w > 0:
            frame_w = int(top_w)
        if frame_h is None and top_h and top_h > 0:
            frame_h = int(top_h)

        engine = raw.get("engine")
        ts_ms = _iso_to_ms(raw.get("ts"))
        note_parts = [str(raw.get("note"))] if raw.get("note") else []
        if raw.get("ok") is False:
            note_parts.append("remote reported ok=false")
        return DetectionFrame(
            t_ms=ts_ms if ts_ms is not None else t_ms,
            frame_w=frame_w,
            frame_h=frame_h,
            engine=f"remote:{engine}" if engine else "remote",
            model=str(engine) if engine else None,
            device=str(raw.get("device")) if raw.get("device") else None,
            sahi=raw.get("sahi") is True,
            slices=int(raw.get("slices") or 0),
            license=str(raw.get("license")) if raw.get("license") else None,
            available=raw.get("ok", True) is not False,
            detections=detections,
            note="; ".join(note_parts),
            source=source or (pick or "remote"),
        )

    # -- public -------------------------------------------------------------

    def snapshot(self, source: Optional[str] = None) -> DetectionFrame:
        """One-shot GET (the Jetson endpoint is JSON, not SSE; poll, never stream)."""
        if not self.url:
            raise DetectorUnavailable("remote detector URL not configured")
        raw = self._get_json()
        frame = self.parse_payload(raw, source=source)
        self._probe_cache = (time.monotonic(), True, "")
        return frame

    def post_image(
        self,
        image_bytes: bytes,
        *,
        filename: str = "frame.jpg",
        content_type: str = "image/jpeg",
        conf: Optional[float] = None,
        sahi: Optional[bool] = None,
        source: str = "image",
    ) -> DetectionFrame:
        """POST the image as multipart ``image``. A remote that answers 404/405/415
        does not accept uploads → ``DetectorUnavailable`` (no snapshot substitution)."""
        if not self.url:
            raise DetectorUnavailable("remote detector URL not configured")
        data: Dict[str, Any] = {}
        if conf is not None:
            data["conf"] = str(conf)
        if sahi is not None:
            data["sahi"] = "1" if sahi else "0"
        try:
            with self._client() as client:
                response = client.post(
                    self.url,
                    files={"image": (filename, image_bytes, content_type)},
                    data=data or None,
                    headers={"Accept": "application/json"},
                )
        except Exception as exc:  # noqa: BLE001
            self.last_error = f"{type(exc).__name__}: {str(exc)[:160]}"
            raise DetectorUnavailable(
                f"remote detector unreachable at {self.url}: {self.last_error}"
            ) from exc
        if response.status_code in (404, 405, 415, 501):
            raise DetectorUnavailable(
                f"remote detector at {self.url} does not accept image uploads "
                f"(HTTP {response.status_code})"
            )
        if response.status_code >= 400:
            raise DetectorUnavailable(f"remote detector HTTP {response.status_code} on upload")
        try:
            raw = response.json()
        except ValueError as exc:
            raise DetectorUnavailable("remote detector returned non-JSON on upload") from exc
        if not isinstance(raw, dict):
            raise DetectorUnavailable("remote detector returned a non-object payload on upload")
        frame = self.parse_payload(raw, t_ms=_now_ms())
        return frame.model_copy(update={"source": source})


# ---------------------------------------------------------------------------
# Local / auto detector
# ---------------------------------------------------------------------------


class FlyBrainDetector:
    """YOLO26 (ultralytics) + SAHI detector with a remote fallback.

    ``backend``: ``"auto"`` prefers ultralytics when importable, then a configured
    remote URL, else none. ``"ultralytics"`` / ``"remote"`` / ``"none"`` force one.
    """

    def __init__(self, settings: Optional[FlyBrainSettings] = None, backend: str = "auto") -> None:
        if backend not in BACKENDS:
            raise ValueError(f"backend must be one of {BACKENDS}, got {backend!r}")
        self.settings = settings or get_settings()
        self.requested_backend = backend
        self._lock = threading.RLock()
        self._resolved: Optional[str] = None  # "ultralytics" | "remote" | "none"
        self._reason: str = ""
        self._yolo_cls: Any = None
        self._model: Any = None
        self._model_error: str = ""
        self._model_names: Dict[int, str] = {}
        self._device: Optional[str] = None
        self._sahi_impl: Optional[str] = None
        self._sahi_model: Any = None
        self._sahi_error: str = ""
        self._remote: Optional[RemoteDetector] = None
        if self.settings.remote_detector_url:
            self._remote = RemoteDetector(self.settings.remote_detector_url)
        from mycosoft_mas.flybrain.vision.ontology import TaxonResolver, TrackMemory

        self._tracks = TrackMemory(max_points=50)
        # MINDEX taxon lookup (spec §9): async in adetect()/asnapshot(); the sync
        # detect()/snapshot() only ever attach what this resolver already cached.
        self._resolver = TaxonResolver(self.settings.mindex_api_url)

    # -- probing ------------------------------------------------------------

    def _probe_ultralytics(self) -> Tuple[bool, str]:
        if self._yolo_cls is not None:
            return True, ""
        try:
            from ultralytics import YOLO  # type: ignore[import-not-found]
        except Exception as exc:  # noqa: BLE001 - ImportError or a broken install
            return False, f"ultralytics not importable: {type(exc).__name__}: {str(exc)[:120]}"
        self._yolo_cls = YOLO
        return True, ""

    def _probe_sahi(self) -> str:
        if self._sahi_impl is not None:
            return self._sahi_impl
        try:
            import sahi  # type: ignore[import-not-found]  # noqa: F401
            from sahi.predict import (  # type: ignore[import-not-found]  # noqa: F401
                get_sliced_prediction,
            )

            self._sahi_impl = "sahi"
        except Exception:  # noqa: BLE001
            self._sahi_impl = "slicing"
        return self._sahi_impl

    def _resolve(self) -> str:
        with self._lock:
            if self._resolved is not None:
                return self._resolved
            reasons: List[str] = []
            want = self.requested_backend
            if want in ("auto", "ultralytics"):
                ok, reason = self._probe_ultralytics()
                if ok:
                    self._resolved = "ultralytics"
                    self._reason = ""
                    self._probe_sahi()
                    return self._resolved
                reasons.append(reason)
                if want == "ultralytics":
                    self._resolved = "none"
                    self._reason = reason
                    return self._resolved
            if want in ("auto", "remote"):
                if self._remote is not None and self._remote.url:
                    self._resolved = "remote"
                    self._reason = ""
                    return self._resolved
                reasons.append(
                    "no remote detector URL (set FLYBRAIN_REMOTE_DETECTOR_URL or "
                    "PSATHYRELLA_CAM_DETECT_URL)"
                )
            if want == "none":
                reasons.append("detector backend disabled (backend='none')")
            self._resolved = "none"
            self._reason = "; ".join(r for r in reasons if r) or "no detector backend"
            return self._resolved

    @property
    def backend(self) -> str:
        return self._resolve()

    @property
    def remote(self) -> Optional[RemoteDetector]:
        return self._remote

    @property
    def available(self) -> bool:
        return self.health().available

    @property
    def resolver(self) -> Any:
        """The MINDEX ``TaxonResolver`` used by ``adetect()`` / ``asnapshot()``."""
        return self._resolver

    @staticmethod
    def _vision_health(*, verified: bool, **fields: Any) -> VisionHealth:
        """Build a ``VisionHealth``; ``verified`` is passed only once the shared
        schema declares it (``VisionHealth.verified``) so this module never forks
        the contract."""
        if "verified" in getattr(VisionHealth, "model_fields", {}):
            fields["verified"] = verified
        return VisionHealth(**fields)

    def health(self, probe_model: bool = False) -> VisionHealth:
        """Honest availability (spec §9.1 / §11.2).

        For the ultralytics backend ``available=True`` is claimed only when the
        weights are actually loaded (``verified=True``) or, short of that, when the
        weights file exists on disk (``verified=False`` — load still deferred). An
        importable ``ultralytics`` with no weights on disk and no verified load is
        ``available=False``; ``probe_model=True`` attempts the load right now so the
        real failure reason (air-gapped download, bad file) is what gets reported.
        """
        backend = self._resolve()
        weights = self.settings.yolo_weights
        remote_url = self._remote.url if self._remote else None
        if backend == "ultralytics":
            if probe_model and self._model is None and not self._model_error:
                try:
                    self._ensure_model()
                except DetectorUnavailable:
                    pass
            sahi_impl = self._probe_sahi()
            common: Dict[str, Any] = {
                "engine": "ultralytics",
                "model": os.path.basename(weights),
                "weights_path": weights,
                "device": self._device,
                "sahi_impl": sahi_impl,
                "remote_url": remote_url,
            }
            if self._model is not None:
                return self._vision_health(
                    verified=True, available=True, sahi=True, reason="", **common
                )
            if self._model_error:
                return self._vision_health(
                    verified=False, available=False, sahi=False, reason=self._model_error, **common
                )
            if os.path.isfile(weights):
                return self._vision_health(
                    verified=False,
                    available=True,
                    sahi=True,
                    reason=(
                        f"YOLO weights '{weights}' present on disk; load not yet verified "
                        "(deferred to first detect)"
                    ),
                    **common,
                )
            return self._vision_health(
                verified=False,
                available=False,
                sahi=False,
                reason=(
                    f"YOLO weights not loaded/verified: '{weights}' is not on disk and no "
                    "load has succeeded (ultralytics importable; probe with probe_model=True)"
                ),
                **common,
            )
        if backend == "remote" and self._remote is not None:
            ok, reason = self._remote.probe()
            return self._vision_health(
                verified=ok,
                available=ok,
                engine="remote",
                model=None,
                weights_path=None,
                device=None,
                sahi=False,
                sahi_impl=None,
                remote_url=self._remote.url,
                reason=reason if not ok else "",
            )
        return self._vision_health(
            verified=False,
            available=False,
            engine=None,
            model=None,
            weights_path=weights,
            device=None,
            sahi=False,
            sahi_impl=None,
            remote_url=remote_url,
            reason=self._reason or "no detector backend",
        )

    # -- model loading ------------------------------------------------------

    def _ensure_model(self) -> Any:
        with self._lock:
            if self._model is not None:
                return self._model
            if self._model_error:
                raise DetectorUnavailable(self._model_error)
            ok, reason = self._probe_ultralytics()
            if not ok:
                self._model_error = reason
                raise DetectorUnavailable(reason)
            weights = self.settings.yolo_weights
            try:
                model = self._yolo_cls(weights)
                names = getattr(model, "names", None)
                if isinstance(names, dict):
                    self._model_names = {int(k): str(v) for k, v in names.items()}
                elif isinstance(names, (list, tuple)):
                    self._model_names = {i: str(v) for i, v in enumerate(names)}
                else:
                    self._model_names = {}
                self._model = model
                device = getattr(model, "device", None)
                if device is not None:
                    self._device = str(device)
            except Exception as exc:  # noqa: BLE001 - download/IO/format failures
                self._model_error = (
                    f"YOLO weights '{weights}' could not be loaded: "
                    f"{type(exc).__name__}: {str(exc)[:200]}"
                )
                logger.warning("FlyBrainDetector: %s", self._model_error)
                raise DetectorUnavailable(self._model_error) from exc
            return self._model

    def _predict_device(self) -> Optional[str]:
        device = (self.settings.yolo_device or "auto").strip().lower()
        return None if device in ("", "auto") else device

    # -- image decoding -----------------------------------------------------

    @staticmethod
    def _decode_image(image: Any) -> Any:
        """bytes | path | ndarray → HWC RGB uint8 numpy array."""
        import numpy as np

        if isinstance(image, np.ndarray):
            arr = image
            if arr.ndim == 2:
                arr = np.stack([arr] * 3, axis=-1)
            return arr
        if isinstance(image, (bytes, bytearray, memoryview)):
            payload = bytes(image)
            try:
                from PIL import Image  # type: ignore[import-not-found]
            except Exception as exc:  # noqa: BLE001
                raise DetectorUnavailable(
                    "Pillow not installed; cannot decode image bytes"
                ) from exc
            try:
                with Image.open(io.BytesIO(payload)) as img:
                    return np.asarray(img.convert("RGB"))
            except Exception as exc:  # noqa: BLE001
                raise ValueError(f"image bytes could not be decoded: {exc}") from exc
        if isinstance(image, (str, os.PathLike)):
            path = os.fspath(image)
            if not os.path.isfile(path):
                raise FileNotFoundError(path)
            try:
                from PIL import Image  # type: ignore[import-not-found]
            except Exception as exc:  # noqa: BLE001
                raise DetectorUnavailable("Pillow not installed; cannot decode image file") from exc
            try:
                with Image.open(path) as img:
                    return np.asarray(img.convert("RGB"))
            except Exception as exc:  # noqa: BLE001
                raise ValueError(f"image file could not be decoded: {exc}") from exc
        raise TypeError(f"unsupported image type {type(image).__name__}")

    @staticmethod
    def _image_bytes(image: Any) -> bytes:
        """bytes | path | ndarray → encoded bytes for upload (PNG for arrays)."""
        if isinstance(image, (bytes, bytearray, memoryview)):
            return bytes(image)
        if isinstance(image, (str, os.PathLike)):
            with open(os.fspath(image), "rb") as fh:
                return fh.read()
        try:
            import numpy as np
            from PIL import Image  # type: ignore[import-not-found]
        except Exception as exc:  # noqa: BLE001
            raise DetectorUnavailable(
                "Pillow not installed; cannot encode array for remote upload"
            ) from exc
        if isinstance(image, np.ndarray):
            buf = io.BytesIO()
            Image.fromarray(np.ascontiguousarray(image)).save(buf, format="PNG")
            return buf.getvalue()
        raise TypeError(f"unsupported image type {type(image).__name__}")

    # -- ultralytics inference ---------------------------------------------

    def _run_yolo(
        self, array: Any, conf: float
    ) -> List[Tuple[float, float, float, float, float, str]]:
        model = self._ensure_model()
        kwargs: Dict[str, Any] = {"conf": conf, "verbose": False}
        device = self._predict_device()
        if device:
            kwargs["device"] = device
        results = model.predict(array, **kwargs)
        out: List[Tuple[float, float, float, float, float, str]] = []
        if not results:
            return out
        result = results[0]
        names = getattr(result, "names", None) or self._model_names
        boxes = getattr(result, "boxes", None)
        if boxes is None or len(boxes) == 0:
            return out
        xyxy = boxes.xyxy
        confs = boxes.conf
        classes = boxes.cls
        try:
            xyxy = xyxy.cpu().numpy()
            confs = confs.cpu().numpy()
            classes = classes.cpu().numpy()
        except AttributeError:
            pass
        if self._device is None:
            try:
                self._device = str(getattr(model, "device", None) or device or "unknown")
            except Exception:  # noqa: BLE001
                self._device = None
        for k in range(len(xyxy)):
            cid = int(classes[k])
            name = names.get(cid) if isinstance(names, dict) else None
            if name is None:
                name = self._model_names.get(cid, str(cid))
            x1, y1, x2, y2 = (float(v) for v in xyxy[k][:4])
            out.append((x1, y1, x2, y2, float(confs[k]), str(name)))
        return out

    def _run_sahi_lib(
        self, array: Any, conf: float
    ) -> Tuple[List[Tuple[float, float, float, float, float, str]], int]:
        from sahi import AutoDetectionModel  # type: ignore[import-not-found]
        from sahi.predict import get_sliced_prediction  # type: ignore[import-not-found]

        from mycosoft_mas.flybrain.vision.slicing import slice_boxes

        with self._lock:
            if self._sahi_model is None:
                kwargs: Dict[str, Any] = {
                    "model_type": "ultralytics",
                    "model_path": self.settings.yolo_weights,
                    "confidence_threshold": conf,
                }
                device = self._predict_device()
                if device:
                    kwargs["device"] = device
                self._sahi_model = AutoDetectionModel.from_pretrained(**kwargs)
        self._sahi_model.confidence_threshold = conf
        slice_px = int(self.settings.sahi_slice)
        overlap = float(self.settings.sahi_overlap)
        result = get_sliced_prediction(
            array,
            self._sahi_model,
            slice_height=slice_px,
            slice_width=slice_px,
            overlap_height_ratio=overlap,
            overlap_width_ratio=overlap,
            verbose=0,
        )
        out: List[Tuple[float, float, float, float, float, str]] = []
        for pred in getattr(result, "object_prediction_list", []) or []:
            x1, y1, x2, y2 = pred.bbox.to_xyxy()
            out.append(
                (
                    float(x1),
                    float(y1),
                    float(x2),
                    float(y2),
                    float(pred.score.value),
                    str(pred.category.name),
                )
            )
        h, w = int(array.shape[0]), int(array.shape[1])
        return out, len(slice_boxes(w, h, slice_px, overlap))

    def _detect_ultralytics(
        self, image: Any, *, sahi: bool, conf: float, source: str, t_ms: Optional[float]
    ) -> DetectionFrame:
        array = self._decode_image(image)
        h, w = int(array.shape[0]), int(array.shape[1])
        self._ensure_model()
        slices = 0
        sahi_used = False
        impl: Optional[str] = None
        raw: List[Tuple[float, float, float, float, float, str]]
        if sahi:
            impl = self._probe_sahi()
            if impl == "sahi":
                try:
                    raw, slices = self._run_sahi_lib(array, conf)
                    sahi_used = True
                except Exception as exc:  # noqa: BLE001 - fall back to in-house slicing
                    self._sahi_error = f"{type(exc).__name__}: {str(exc)[:120]}"
                    logger.warning(
                        "sahi library failed (%s); using in-house slicing", self._sahi_error
                    )
                    self._sahi_impl = "slicing"
                    impl = "slicing"
            if impl == "slicing":
                from mycosoft_mas.flybrain.vision.slicing import sliced_predict

                pred = sliced_predict(
                    lambda tile: self._run_yolo(tile, conf),
                    array,
                    int(self.settings.sahi_slice),
                    float(self.settings.sahi_overlap),
                    conf,
                )
                raw, slices = pred.detections, pred.slices
                sahi_used = True
        else:
            raw = self._run_yolo(array, conf)

        detections = [
            Detection(
                id=f"{source}:{i}",
                cls=cls,
                conf=min(max(c, 0.0), 1.0),
                bbox_xyxy=(x1, y1, x2, y2),
                bbox_norm=(
                    min(max(x1 / w, 0.0), 1.0),
                    min(max(y1 / h, 0.0), 1.0),
                    min(max(x2 / w, 0.0), 1.0),
                    min(max(y2 / h, 0.0), 1.0),
                ),
                source=source,
                attributes={"bbox_units": "pixels"},
            )
            for i, (x1, y1, x2, y2, c, cls) in enumerate(raw)
        ]
        weights = self.settings.yolo_weights
        return DetectionFrame(
            t_ms=t_ms if t_ms is not None else _now_ms(),
            frame_w=w,
            frame_h=h,
            engine=f"ultralytics:{os.path.basename(weights)}",
            model=os.path.basename(weights),
            device=self._device,
            sahi=sahi_used,
            slices=slices,
            license=None,
            available=True,
            detections=detections,
            note=(f"sahi_impl={impl}" if impl else ""),
            source=source,
        )

    # -- public API ---------------------------------------------------------

    def _detect_raw(
        self,
        image: Any,
        *,
        sahi: Optional[bool],
        conf: Optional[float],
        source: str,
        t_ms: Optional[float],
    ) -> DetectionFrame:
        """Run the resolved backend and return the un-enriched frame (sync, blocking)."""
        backend = self._resolve()
        use_sahi = True if sahi is None else bool(sahi)
        threshold = float(conf) if conf is not None else float(self.settings.yolo_conf)
        if backend == "ultralytics":
            return self._detect_ultralytics(
                image, sahi=use_sahi, conf=threshold, source=source, t_ms=t_ms
            )
        if backend == "remote" and self._remote is not None:
            payload = self._image_bytes(image)
            frame = self._remote.post_image(payload, conf=threshold, sahi=sahi, source=source)
            if t_ms is not None:
                frame = frame.model_copy(update={"t_ms": t_ms})
            return frame
        raise DetectorUnavailable(self._reason or "no detector backend")

    def _snapshot_raw(self, source: Optional[str]) -> DetectionFrame:
        if self._remote is None or not self._remote.url:
            raise DetectorUnavailable("no remote detector URL configured")
        return self._remote.snapshot(source=source)

    def detect(
        self,
        image: Any,
        *,
        sahi: Optional[bool] = None,
        conf: Optional[float] = None,
        pose: Optional[Dict[str, Any]] = None,
        source: str = "image",
        t_ms: Optional[float] = None,
    ) -> DetectionFrame:
        """Detect on ``image`` (bytes, path or HWC ndarray). Raises ``DetectorUnavailable``
        when no backend can run; never returns invented boxes.

        Sync path: geometry enrichment plus taxa **from the resolver cache only** (no
        network). Use ``adetect`` for the MINDEX lookup."""
        frame = self._detect_raw(image, sahi=sahi, conf=conf, source=source, t_ms=t_ms)
        from mycosoft_mas.flybrain.vision.ontology import enrich

        return enrich(
            frame, pose, self.settings, track_memory=self._tracks, resolver=self._resolver
        )

    async def adetect(
        self,
        image: Any,
        *,
        sahi: Optional[bool] = None,
        conf: Optional[float] = None,
        pose: Optional[Dict[str, Any]] = None,
        source: str = "image",
        t_ms: Optional[float] = None,
    ) -> DetectionFrame:
        """``detect`` with the backend in a worker thread and the async MINDEX taxon
        lookup (spec §9) for animal/plant/fungus detections."""
        frame = await asyncio.to_thread(
            self._detect_raw, image, sahi=sahi, conf=conf, source=source, t_ms=t_ms
        )
        from mycosoft_mas.flybrain.vision.ontology import aenrich

        return await aenrich(
            frame, pose, self.settings, track_memory=self._tracks, resolver=self._resolver
        )

    def snapshot(
        self, source: Optional[str] = None, *, pose: Optional[Dict[str, Any]] = None
    ) -> DetectionFrame:
        """Remote one-shot snapshot (works regardless of the local backend).
        Sync: taxa from the resolver cache only; use ``asnapshot`` for the lookup."""
        frame = self._snapshot_raw(source)
        from mycosoft_mas.flybrain.vision.ontology import enrich

        return enrich(
            frame, pose, self.settings, track_memory=self._tracks, resolver=self._resolver
        )

    async def asnapshot(
        self, source: Optional[str] = None, *, pose: Optional[Dict[str, Any]] = None
    ) -> DetectionFrame:
        frame = await asyncio.to_thread(self._snapshot_raw, source)
        from mycosoft_mas.flybrain.vision.ontology import aenrich

        return await aenrich(
            frame, pose, self.settings, track_memory=self._tracks, resolver=self._resolver
        )

    @property
    def class_names(self) -> Sequence[str]:
        """Class names of the loaded model (empty until weights are loaded)."""
        return [self._model_names[k] for k in sorted(self._model_names)]

    @property
    def track_memory(self) -> Any:
        return self._tracks


# ---------------------------------------------------------------------------
# Module cache
# ---------------------------------------------------------------------------

_DETECTOR: Optional[FlyBrainDetector] = None
_DETECTOR_LOCK = threading.Lock()


def get_detector(settings: Optional[FlyBrainSettings] = None) -> FlyBrainDetector:
    global _DETECTOR
    with _DETECTOR_LOCK:
        if _DETECTOR is None:
            _DETECTOR = FlyBrainDetector(settings=settings, backend="auto")
        return _DETECTOR


def set_detector_for_tests(detector: Optional[FlyBrainDetector]) -> None:
    """Replace (or clear with ``None``) the module-level detector."""
    global _DETECTOR
    with _DETECTOR_LOCK:
        _DETECTOR = detector


__all__ = [
    "BACKENDS",
    "DetectorUnavailable",
    "FlyBrainDetector",
    "RemoteDetector",
    "get_detector",
    "set_detector_for_tests",
]
