"""FlyBrain API — FlyWire whole-brain LIF as a pluggable MYCA module (spec §10).

``/api/flybrain/*`` fronts :class:`mycosoft_mas.flybrain.runtime.FlyBrainRuntime`.
Every payload carries ``origin="SIMULATED"``; nothing here invents a
detection, a rate, a probability or a green status (spec §11):

* no connectome on disk → **503** ``{error: "connectome_unavailable", reason, fetch}``
  with the exact fetch command for this host's ``FLYBRAIN_DATA_DIR``;
* no detector backend → **503** ``{error: "detector_unavailable", reason}``;
* unknown session → **404**; session cap → **429**; bad group/command → **400**.

Handlers are async and never block the event loop: engine steps run inside the
runtime's ``asyncio.to_thread``, image fetches use ``httpx.AsyncClient`` behind an
SSRF guard (public hosts only unless allow-listed, no redirects) with one overall 5 s
budget and an 8 MB cap, ``/vision/detect`` bodies are read through a bounded stream
(~10.8 MB) before any parsing, and the one-off ITDX planner runs in a worker thread.
Heavy libraries (numpy, PIL, httpx) are imported inside the handlers that need
them so this module imports cleanly under ``MAS_LIGHT_IMPORT=1``.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import ipaddress
import json
import logging
import math
import os
import socket
from typing import Any, Dict, List, Mapping, Optional, Set
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from mycosoft_mas.flybrain.connectome import FETCH_SCRIPT
from mycosoft_mas.flybrain.model import BackendUnavailable
from mycosoft_mas.flybrain.plugs import UnknownPlug
from mycosoft_mas.flybrain.plugs.earthsim import (
    DEFAULT_OBSTACLE_RADIUS_M,
    GRID_CELLS_PER_SIDE,
    MAX_GRID_SIZE_M,
    MIN_CELL_M,
    ao_center,
    ao_extent_m,
)
from mycosoft_mas.flybrain.plugs.itdx import ITDX_CHANNELS_SCHEMA_VERSION, itdx_channel_rows
from mycosoft_mas.flybrain.runtime import (
    ConnectomeUnavailable,
    FlyBrainRuntime,
    SessionLimitReached,
    SessionNotFound,
    get_runtime,
)
from mycosoft_mas.flybrain.schemas import (
    ORIGIN_SIMULATED,
    AtlasSummary,
    BrainState,
    ConnectomeManifest,
    DetectionFrame,
    FlyBrainHealth,
    GeoPoint,
    NavPath,
    SessionConfig,
    SessionInfo,
    SpikeRecord,
    StimulusCommand,
    TickRequest,
    TickResult,
    VisionHealth,
    utc_now_iso,
)
from mycosoft_mas.flybrain.vision.detector import DetectorUnavailable

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/flybrain", tags=["flybrain"])

IMAGE_MAX_BYTES = 8 * 1024 * 1024
# Whole-request cap for /vision/detect, enforced on the byte stream before any parsing:
# base64 of an 8 MB image (~10.7 MB) plus 64 KiB for the other fields / multipart framing.
DETECT_BODY_MAX_BYTES = IMAGE_MAX_BYTES * 4 // 3 + 64 * 1024
IMAGE_URL_TIMEOUT_S = 5.0
IMAGE_URL_ALLOW_HOSTS_ENV = "FLYBRAIN_IMAGE_URL_ALLOW_HOSTS"
IMAGE_URL_FETCH_FAILED_REASON = (
    "image_url could not be fetched (non-2xx, redirect, timeout, DNS or transport error); "
    "details are logged server-side only"
)
ONE_OFF_GOAL_FRACTION = 0.45
ONE_OFF_DETECTION_RADIUS_M = 10.0


# ---------------------------------------------------------------------------
# Request models (the response models all come from flybrain.schemas)
# ---------------------------------------------------------------------------


class AutopilotRequest(BaseModel):
    enabled: bool
    period_s: float = Field(default=1.0, ge=0.0, le=3600.0)


class PoseModel(BaseModel):
    lat: Optional[float] = None
    lon: Optional[float] = None
    heading_deg: Optional[float] = None


class VisionDetectJSON(BaseModel):
    image_b64: Optional[str] = None
    image_url: Optional[str] = None
    sahi: Optional[bool] = None
    conf: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    pose: Optional[PoseModel] = None
    source: str = "image"


class ITDXChannelsRequest(BaseModel):
    map_slice: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    detections: Optional[Dict[str, Any]] = None


class NLMObservationRequest(BaseModel):
    session_id: str
    cutoff: Optional[str] = None


# ---------------------------------------------------------------------------
# Error mapping (spec §11)
# ---------------------------------------------------------------------------


def fetch_command(runtime: FlyBrainRuntime) -> str:
    return f"poetry run python {FETCH_SCRIPT} --dest {runtime.settings.data_dir}"


def connectome_unavailable_detail(runtime: FlyBrainRuntime, exc: BaseException) -> Dict[str, Any]:
    return {
        "error": "connectome_unavailable",
        "reason": str(exc),
        "fetch": fetch_command(runtime),
        "data_dir": str(runtime.settings.data_dir),
        "origin": ORIGIN_SIMULATED,
    }


def _raise_mapped(exc: BaseException, runtime: FlyBrainRuntime) -> None:
    """Translate runtime exceptions into HTTP errors; re-raise anything unknown."""
    if isinstance(exc, HTTPException):
        raise exc
    if isinstance(exc, ConnectomeUnavailable):
        raise HTTPException(status_code=503, detail=connectome_unavailable_detail(runtime, exc))
    if isinstance(exc, BackendUnavailable):
        raise HTTPException(
            status_code=503, detail={"error": "backend_unavailable", "reason": str(exc)}
        )
    if isinstance(exc, DetectorUnavailable):
        raise HTTPException(
            status_code=503, detail={"error": "detector_unavailable", "reason": str(exc)}
        )
    if isinstance(exc, SessionNotFound):
        raise HTTPException(
            status_code=404,
            detail={
                "error": "session_not_found",
                "session_id": str(exc.args[0]) if exc.args else "",
            },
        )
    if isinstance(exc, SessionLimitReached):
        raise HTTPException(
            status_code=429, detail={"error": "session_limit_reached", "reason": str(exc)}
        )
    if isinstance(exc, (UnknownPlug, ValueError)):
        raise HTTPException(status_code=400, detail={"error": "bad_request", "reason": str(exc)})
    raise exc


def _runtime() -> FlyBrainRuntime:
    return get_runtime()


# ---------------------------------------------------------------------------
# Health / connectome / atlas
# ---------------------------------------------------------------------------


@router.get("/health", response_model=FlyBrainHealth)
async def flybrain_health() -> FlyBrainHealth:
    """Connectome loaded?, vision available?, backend, sessions — never forces a load."""
    runtime = _runtime()
    return await asyncio.to_thread(runtime.health)


@router.get("/connectome/manifest", response_model=ConnectomeManifest)
async def connectome_manifest() -> ConnectomeManifest:
    runtime = _runtime()
    return await asyncio.to_thread(runtime.connectome_manifest)


@router.get("/atlas", response_model=AtlasSummary)
async def atlas_summary() -> AtlasSummary:
    runtime = _runtime()
    try:
        return await asyncio.to_thread(runtime.atlas_summary)
    except Exception as exc:  # noqa: BLE001
        _raise_mapped(exc, runtime)
        raise  # pragma: no cover - _raise_mapped always raises


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


@router.get("/sessions", response_model=List[SessionInfo])
async def list_sessions() -> List[SessionInfo]:
    return _runtime().list_sessions()


@router.post("/sessions", response_model=SessionInfo)
async def create_session(cfg: Optional[SessionConfig] = None) -> SessionInfo:
    """Create an engine + plug session. 503 with fetch instructions when the connectome is missing."""
    runtime = _runtime()
    try:
        return await runtime.acreate_session(cfg or SessionConfig())
    except Exception as exc:  # noqa: BLE001
        _raise_mapped(exc, runtime)
        raise  # pragma: no cover


@router.get("/sessions/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str) -> SessionInfo:
    runtime = _runtime()
    try:
        return runtime.get_session(session_id)
    except Exception as exc:  # noqa: BLE001
        _raise_mapped(exc, runtime)
        raise  # pragma: no cover


@router.delete("/sessions/{session_id}", response_model=SessionInfo)
async def delete_session(session_id: str) -> SessionInfo:
    runtime = _runtime()
    try:
        return await runtime.delete_session(session_id)
    except Exception as exc:  # noqa: BLE001
        _raise_mapped(exc, runtime)
        raise  # pragma: no cover


@router.post("/sessions/{session_id}/tick", response_model=TickResult)
async def tick_session(session_id: str, req: Optional[TickRequest] = None) -> TickResult:
    runtime = _runtime()
    try:
        return await runtime.tick(session_id, req or TickRequest())
    except Exception as exc:  # noqa: BLE001
        _raise_mapped(exc, runtime)
        raise  # pragma: no cover


@router.post("/sessions/{session_id}/stimulate", response_model=BrainState)
async def stimulate_session(session_id: str, commands: List[StimulusCommand]) -> BrainState:
    runtime = _runtime()
    if not commands:
        raise HTTPException(
            status_code=400,
            detail={"error": "bad_request", "reason": "at least one StimulusCommand is required"},
        )
    try:
        return await runtime.stimulate(session_id, commands)
    except Exception as exc:  # noqa: BLE001
        _raise_mapped(exc, runtime)
        raise  # pragma: no cover


@router.get("/sessions/{session_id}/state", response_model=BrainState)
async def session_state(
    session_id: str,
    window_ms: Optional[float] = Query(default=None, gt=0.0, le=5000.0),
) -> BrainState:
    runtime = _runtime()
    try:
        return await runtime.state(session_id, window_ms)
    except Exception as exc:  # noqa: BLE001
        _raise_mapped(exc, runtime)
        raise  # pragma: no cover


@router.get("/sessions/{session_id}/spikes", response_model=SpikeRecord)
async def session_spikes(
    session_id: str, limit: int = Query(default=10_000, ge=0, le=200_000)
) -> SpikeRecord:
    runtime = _runtime()
    try:
        return await runtime.spikes(session_id, limit)
    except Exception as exc:  # noqa: BLE001
        _raise_mapped(exc, runtime)
        raise  # pragma: no cover


@router.post("/sessions/{session_id}/reset", response_model=SessionInfo)
async def reset_session(session_id: str) -> SessionInfo:
    runtime = _runtime()
    try:
        return await runtime.reset(session_id)
    except Exception as exc:  # noqa: BLE001
        _raise_mapped(exc, runtime)
        raise  # pragma: no cover


@router.post("/sessions/{session_id}/autopilot", response_model=SessionInfo)
async def session_autopilot(session_id: str, body: AutopilotRequest) -> SessionInfo:
    runtime = _runtime()
    try:
        return await runtime.set_autopilot(session_id, body.enabled, body.period_s)
    except Exception as exc:  # noqa: BLE001
        _raise_mapped(exc, runtime)
        raise  # pragma: no cover


# ---------------------------------------------------------------------------
# Vision
# ---------------------------------------------------------------------------


@router.get("/vision/health", response_model=VisionHealth)
async def vision_health() -> VisionHealth:
    runtime = _runtime()
    return await asyncio.to_thread(runtime.vision_health)


def _parse_pose(raw: Any) -> Optional[Dict[str, Any]]:
    if raw is None or raw == "":
        return None
    if isinstance(raw, PoseModel):
        raw = raw.model_dump()
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail={"error": "bad_request", "reason": f"pose is not JSON: {exc}"},
            ) from exc
    if not isinstance(raw, Mapping):
        raise HTTPException(
            status_code=400, detail={"error": "bad_request", "reason": "pose must be an object"}
        )
    pose: Dict[str, Any] = {}
    for key in ("lat", "lon", "heading_deg"):
        value = raw.get(key)
        if value is None:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=400,
                detail={"error": "bad_request", "reason": f"pose.{key} must be a number"},
            ) from exc
        if math.isnan(number) or math.isinf(number):
            raise HTTPException(
                status_code=400,
                detail={"error": "bad_request", "reason": f"pose.{key} must be finite"},
            )
        pose[key] = number
    return pose or None


def _parse_bool(raw: Any) -> Optional[bool]:
    if raw is None or raw == "":
        return None
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _parse_conf(raw: Any) -> Optional[float]:
    if raw is None or raw == "":
        return None
    try:
        conf = float(raw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400, detail={"error": "bad_request", "reason": "conf must be a number"}
        ) from exc
    if not 0.0 <= conf <= 1.0:
        raise HTTPException(
            status_code=400, detail={"error": "bad_request", "reason": "conf must be in [0, 1]"}
        )
    return conf


def _decode_b64(text: str) -> bytes:
    payload = text.strip()
    if payload.startswith("data:") and "," in payload:
        payload = payload.split(",", 1)[1]
    # 8 MB of bytes is ~10.7 MB of base64; refuse obviously oversized text early.
    if len(payload) > IMAGE_MAX_BYTES * 4 // 3 + 4:
        raise HTTPException(
            status_code=413,
            detail={"error": "image_too_large", "reason": f"image exceeds {IMAGE_MAX_BYTES} bytes"},
        )
    try:
        data = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(
            status_code=400, detail={"error": "bad_request", "reason": f"image_b64 invalid: {exc}"}
        ) from exc
    if not data:
        raise HTTPException(
            status_code=400, detail={"error": "bad_request", "reason": "image_b64 is empty"}
        )
    if len(data) > IMAGE_MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail={"error": "image_too_large", "reason": f"image exceeds {IMAGE_MAX_BYTES} bytes"},
        )
    return data


def _image_url_allowed_hosts(runtime: Optional[FlyBrainRuntime] = None) -> Set[str]:
    """Hosts exempt from the public-address rule (lower-cased).

    ``FLYBRAIN_IMAGE_URL_ALLOW_HOSTS`` (comma-separated) plus the host of the
    configured ``FLYBRAIN_REMOTE_DETECTOR_URL`` — the only LAN destinations a
    camera frame is expected to come from.
    """
    hosts: Set[str] = set()
    for item in os.getenv(IMAGE_URL_ALLOW_HOSTS_ENV, "").split(","):
        item = item.strip().strip("[]").lower()
        if item:
            hosts.add(item)
    settings = getattr(runtime, "settings", None)
    remote = getattr(settings, "remote_detector_url", None)
    if remote:
        try:
            remote_host = urlparse(str(remote)).hostname
        except ValueError:
            remote_host = None
        if remote_host:
            hosts.add(remote_host.lower())
    return hosts


def _is_public_address(text: str) -> bool:
    """True only for globally routable unicast addresses (no loopback/link-local/RFC1918/...)."""
    try:
        ip = ipaddress.ip_address(text.split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return not (
        ip.is_loopback
        or ip.is_link_local
        or ip.is_private
        or ip.is_multicast
        or ip.is_unspecified
        or ip.is_reserved
        or not ip.is_global
    )


async def _resolve_host(host: str) -> List[str]:
    """DNS-resolve ``host`` to its A/AAAA addresses (patched in tests; no network there)."""
    loop = asyncio.get_running_loop()
    infos = await loop.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    return sorted({str(info[4][0]) for info in infos})


def _image_url_fetch_failed() -> HTTPException:
    return HTTPException(
        status_code=502,
        detail={"error": "image_url_fetch_failed", "reason": IMAGE_URL_FETCH_FAILED_REASON},
    )


async def _check_image_url_target(host: str, allowed_hosts: Set[str]) -> None:
    """SSRF guard: the destination must resolve to public addresses only, or be allow-listed."""
    if host.lower() in allowed_hosts:
        return
    try:
        addresses = [str(ipaddress.ip_address(host))]
    except ValueError:
        try:
            addresses = await _resolve_host(host)
        except (OSError, ValueError) as exc:
            logger.info("FlyBrain: image_url host %r did not resolve: %s", host, exc)
            raise _image_url_fetch_failed() from exc
    if not addresses or not all(_is_public_address(addr) for addr in addresses):
        logger.info("FlyBrain: image_url host %r rejected (non-public: %s)", host, addresses)
        raise HTTPException(
            status_code=400,
            detail={
                "error": "image_url_forbidden",
                "reason": (
                    "image_url must resolve to a public address; loopback, link-local, "
                    "private, multicast and reserved destinations are refused unless the "
                    f"host is listed in {IMAGE_URL_ALLOW_HOSTS_ENV} or is the "
                    "FLYBRAIN_REMOTE_DETECTOR_URL host"
                ),
            },
        )


async def _fetch_image_url_bounded(url: str, host: str, allowed_hosts: Set[str]) -> bytes:
    import httpx

    await _check_image_url_target(host, allowed_hosts)
    chunks: List[bytes] = []
    total = 0
    async with httpx.AsyncClient(timeout=IMAGE_URL_TIMEOUT_S, follow_redirects=False) as client:
        async with client.stream("GET", url) as response:
            if not 200 <= response.status_code < 300:
                # Redirects are not followed: a public URL must not be able to bounce
                # the fetch onto an internal address. Status is logged, never echoed.
                logger.info("FlyBrain: image_url fetch got HTTP %s", response.status_code)
                raise _image_url_fetch_failed()
            declared = response.headers.get("content-length")
            if declared and declared.isdigit() and int(declared) > IMAGE_MAX_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail={
                        "error": "image_too_large",
                        "reason": f"image exceeds {IMAGE_MAX_BYTES} bytes",
                    },
                )
            async for chunk in response.aiter_bytes():
                total += len(chunk)
                if total > IMAGE_MAX_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail={
                            "error": "image_too_large",
                            "reason": f"image exceeds {IMAGE_MAX_BYTES} bytes",
                        },
                    )
                chunks.append(chunk)
    data = b"".join(chunks)
    if not data:
        logger.info("FlyBrain: image_url fetch returned an empty body")
        raise _image_url_fetch_failed()
    return data


async def _fetch_image_url(url: str, allowed_hosts: Optional[Set[str]] = None) -> bytes:
    """GET ``url`` (http/https, public hosts only, no redirects) within one overall
    ``IMAGE_URL_TIMEOUT_S`` budget and an 8 MB streaming cap.

    Failures collapse to a generic ``image_url_fetch_failed`` (details are logged
    server-side only) so the endpoint cannot be used as a port/status oracle.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc or not parsed.hostname:
        raise HTTPException(
            status_code=400,
            detail={"error": "bad_request", "reason": "image_url must be an http(s) URL"},
        )
    try:
        import httpx  # noqa: F401 - probe only; used inside _fetch_image_url_bounded
    except ImportError as exc:  # pragma: no cover - httpx is a MAS dependency
        raise HTTPException(
            status_code=503,
            detail={"error": "detector_unavailable", "reason": "httpx not installed"},
        ) from exc
    if allowed_hosts is None:
        allowed_hosts = _image_url_allowed_hosts(_runtime())
    try:
        return await asyncio.wait_for(
            _fetch_image_url_bounded(url, parsed.hostname, allowed_hosts), IMAGE_URL_TIMEOUT_S
        )
    except HTTPException:
        raise
    except asyncio.TimeoutError as exc:
        logger.info("FlyBrain: image_url fetch exceeded %.1f s", IMAGE_URL_TIMEOUT_S)
        raise _image_url_fetch_failed() from exc
    except Exception as exc:  # noqa: BLE001 - DNS, TLS, transport errors
        logger.info("FlyBrain: image_url fetch failed: %s: %s", type(exc).__name__, exc)
        raise _image_url_fetch_failed() from exc


async def _read_bounded_body(request: Request) -> bytes:
    """Read the request body via ``request.stream()`` with a hard ``DETECT_BODY_MAX_BYTES`` cap.

    An over-cap ``Content-Length`` is refused before a single byte is read; a chunked
    or lying body is aborted the moment the running total passes the cap (413).
    """
    declared = (request.headers.get("content-length") or "").strip()
    if declared:
        if not declared.isdigit():
            raise HTTPException(
                status_code=400,
                detail={"error": "bad_request", "reason": "Content-Length is not a number"},
            )
        if int(declared) > DETECT_BODY_MAX_BYTES:
            raise HTTPException(
                status_code=413,
                detail={
                    "error": "request_too_large",
                    "reason": f"request body exceeds {DETECT_BODY_MAX_BYTES} bytes",
                },
            )
    chunks: List[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > DETECT_BODY_MAX_BYTES:
            raise HTTPException(
                status_code=413,
                detail={
                    "error": "request_too_large",
                    "reason": f"request body exceeds {DETECT_BODY_MAX_BYTES} bytes",
                },
            )
        chunks.append(chunk)
    return b"".join(chunks)


async def _read_detect_request(request: Request) -> Dict[str, Any]:
    """Multipart ``image`` (+ optional form fields) or JSON body → normalised dict."""
    content_type = (request.headers.get("content-type") or "").lower()
    body_bytes = await _read_bounded_body(request)
    if content_type.startswith("multipart/form-data"):

        async def _replay() -> Dict[str, Any]:
            return {"type": "http.request", "body": body_bytes, "more_body": False}

        try:
            # Parse only the bounded bytes (never the raw socket) with python-multipart.
            form = await Request(request.scope, _replay).form(max_files=4, max_fields=16)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=400,
                detail={"error": "bad_request", "reason": f"multipart body unreadable: {exc}"},
            ) from exc
        upload = form.get("image")
        if upload is None or not hasattr(upload, "read"):
            raise HTTPException(
                status_code=400,
                detail={"error": "bad_request", "reason": "multipart field 'image' is required"},
            )
        data = await upload.read()
        if len(data) > IMAGE_MAX_BYTES:
            raise HTTPException(
                status_code=413,
                detail={
                    "error": "image_too_large",
                    "reason": f"image exceeds {IMAGE_MAX_BYTES} bytes",
                },
            )
        if not data:
            raise HTTPException(
                status_code=400, detail={"error": "bad_request", "reason": "image is empty"}
            )
        return {
            "image": data,
            "sahi": _parse_bool(form.get("sahi")),
            "conf": _parse_conf(form.get("conf")),
            "pose": _parse_pose(form.get("pose")),
            "source": str(form.get("source") or "image"),
        }
    try:
        raw = json.loads(body_bytes)
    except ValueError as exc:  # JSONDecodeError / UnicodeDecodeError
        raise HTTPException(
            status_code=400,
            detail={
                "error": "bad_request",
                "reason": "send multipart/form-data with an 'image' file or a JSON body "
                f"{{image_b64 | image_url, sahi?, conf?, pose?}} ({exc})",
            },
        ) from exc
    try:
        body = VisionDetectJSON.model_validate(raw)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=400, detail={"error": "bad_request", "reason": str(exc)[:400]}
        ) from exc
    if body.image_b64:
        data = _decode_b64(body.image_b64)
    elif body.image_url:
        data = await _fetch_image_url(body.image_url)
    else:
        raise HTTPException(
            status_code=400,
            detail={"error": "bad_request", "reason": "image_b64 or image_url is required"},
        )
    return {
        "image": data,
        "sahi": body.sahi,
        "conf": body.conf,
        "pose": _parse_pose(body.pose),
        "source": body.source or "image",
    }


@router.post("/vision/detect", response_model=DetectionFrame)
async def vision_detect(request: Request) -> DetectionFrame:
    """YOLO26 + SAHI detection on an uploaded image, base64 image or http(s) URL.

    503 when no detector backend is available — never synthetic boxes.
    """
    runtime = _runtime()
    try:
        detector = runtime._detector()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=503,
            detail={
                "error": "detector_unavailable",
                "reason": f"detector probe failed: {type(exc).__name__}: {exc}",
            },
        ) from exc
    health = await asyncio.to_thread(detector.health)
    if not health.available:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "detector_unavailable",
                "reason": health.reason or "no detector backend",
                "vision": health.model_dump(),
            },
        )
    payload = await _read_detect_request(request)
    try:
        frame = await detector.adetect(
            payload["image"],
            sahi=payload["sahi"],
            conf=payload["conf"],
            pose=payload["pose"],
            source=payload["source"],
        )
    except DetectorUnavailable as exc:
        raise HTTPException(
            status_code=503, detail={"error": "detector_unavailable", "reason": str(exc)}
        ) from exc
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=400, detail={"error": "bad_request", "reason": str(exc)[:400]}
        ) from exc
    if not frame.available:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "detector_unavailable",
                "reason": frame.note or "detector reported unavailable",
            },
        )
    return frame


# ---------------------------------------------------------------------------
# ITDX channels
# ---------------------------------------------------------------------------


def _num(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def _slice_bbox(map_slice: Mapping[str, Any]) -> Optional[List[float]]:
    ao = map_slice.get("ao") if isinstance(map_slice, Mapping) else None
    if not isinstance(ao, Mapping):
        return None
    bbox = ao.get("bbox")
    if not (isinstance(bbox, (list, tuple)) and len(bbox) == 4):
        return None
    vals = [_num(v) for v in bbox]
    if any(v is None for v in vals):
        return None
    return [float(v) for v in vals]  # type: ignore[arg-type]


def plan_one_off(
    map_slice: Mapping[str, Any], detections: Optional[DetectionFrame] = None
) -> NavPath:
    """One-off ITDX plan with no brain state: AO centre → far bbox corner, ``turn_bias=0``.

    The grid is the smaller AO side capped at ``MAX_GRID_SIZE_M``; when the far
    (north-east) corner lies outside that grid the goal is the point on the bearing
    to the corner at ``ONE_OFF_GOAL_FRACTION`` of the grid size. Assets, devices
    and located detections are obstacles. Turn bias is 0 because no brain ticked.
    """
    from mycosoft_mas.flybrain.navigation import OccupancyGrid, enu_from_geo, geo_from_enu, plan
    from mycosoft_mas.flybrain.plugs.earthsim import _latlon

    center = ao_center(map_slice)
    if center is None:
        return NavPath(feasible=False, note="map slice has no AO centre or bbox; cannot plan")
    extent = ao_extent_m(map_slice)
    size = min(extent, MAX_GRID_SIZE_M) if extent else 2000.0
    size = max(size, 200.0)
    cell = max(MIN_CELL_M, size / GRID_CELLS_PER_SIDE)
    grid = OccupancyGrid(center, size_m=size, cell_m=cell)

    bbox = _slice_bbox(map_slice)
    if bbox is not None:
        corner = GeoPoint(lat=bbox[3], lon=bbox[2])  # north-east corner
    else:
        corner = geo_from_enu(0.0, ONE_OFF_GOAL_FRACTION * size, center)
    east, north = enu_from_geo(corner.lat, corner.lon, center)
    reach = math.hypot(east, north)
    limit = ONE_OFF_GOAL_FRACTION * size
    if reach > limit and reach > 0.0:
        scale = limit / reach
        goal = geo_from_enu(east * scale, north * scale, center)
        goal_note = f"far bbox corner is {reach:.0f} m away; goal clamped to {limit:.0f} m"
    else:
        goal = corner
        goal_note = f"goal = far (north-east) bbox corner, {reach:.0f} m from AO centre"

    n_obstacles = 0
    for key in ("assets", "devices"):
        seq = map_slice.get(key)
        if not isinstance(seq, (list, tuple)):
            continue
        for item in seq:
            pt = _latlon(item)
            if pt is None:
                continue
            if grid.add_point(pt[0], pt[1], DEFAULT_OBSTACLE_RADIUS_M):
                n_obstacles += 1
    n_det = 0
    if detections is not None and detections.available:
        for det in detections.detections:
            if det.perimeter:
                if grid.add_perimeter(det.perimeter):
                    n_det += 1
            elif det.location is not None:
                if grid.add_point(det.location.lat, det.location.lon, ONE_OFF_DETECTION_RADIUS_M):
                    n_det += 1
    nav = plan(grid, center, goal, turn_bias=0.0)
    rule = (
        f"one-off plan without brain state (turn_bias=0): {goal_note}; "
        f"grid {size:.0f} m / {cell:.1f} m cells; obstacles: {n_obstacles} assets/devices, "
        f"{n_det} detections"
    )
    nav.note = f"{nav.note}; {rule}" if nav.note else rule
    return nav


def _default_map_slice() -> Optional[Dict[str, Any]]:
    try:
        from mycosoft_mas.flybrain.plugs.earthsim import default_map_slice

        return default_map_slice()
    except Exception as exc:  # noqa: BLE001
        logger.warning("FlyBrain: default ITDX map slice unavailable: %s", exc)
        return None


@router.post("/itdx/channels")
async def itdx_channels(body: ITDXChannelsRequest) -> Dict[str, Any]:
    """``pathways``/``navigation``/``biology``/``information`` rows (``itdx_api._channel`` shape).

    With ``session_id`` the rows come from that session's last tick; without one a
    one-off plan runs from the AO centre to the far bbox corner with no brain state,
    so brain-derived fields are ``NOT_SUPPLIED``.
    """
    runtime = _runtime()
    map_slice = body.map_slice
    if map_slice is None:
        map_slice = await asyncio.to_thread(_default_map_slice)
        if map_slice is None:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "bad_request",
                    "reason": "map_slice is required (the Fort Stewart demo slice is unavailable)",
                },
            )
    frame: Optional[DetectionFrame] = None
    if body.detections is not None:
        try:
            frame = DetectionFrame.model_validate(body.detections)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "bad_request",
                    "reason": f"detections is not a DetectionFrame: {str(exc)[:300]}",
                },
            ) from exc
    if body.session_id:
        try:
            return runtime.itdx_channels(map_slice, session_id=body.session_id, detections=frame)
        except Exception as exc:  # noqa: BLE001
            _raise_mapped(exc, runtime)
            raise  # pragma: no cover
    nav = await asyncio.to_thread(plan_one_off, map_slice, frame)
    rows = itdx_channel_rows(map_slice, None, None, nav, frame)
    return {
        "schema_version": ITDX_CHANNELS_SCHEMA_VERSION,
        "origin": ORIGIN_SIMULATED,
        "channels": rows,
        "nav": nav.model_dump(),
        "session_id": None,
        "tick": None,
        "generated_at": utc_now_iso(),
        "note": "one-off: no session, no brain state; brain-derived fields are NOT_SUPPLIED",
    }


# ---------------------------------------------------------------------------
# NLM coupling / droid guidance
# ---------------------------------------------------------------------------


@router.post("/nlm/observation")
async def nlm_observation(body: NLMObservationRequest) -> Dict[str, Any]:
    """Session rates → ``formspace.observation/v1`` envelope → ``CausalObservationPipeline``."""
    runtime = _runtime()
    try:
        return await runtime.nlm_observation(body.session_id, body.cutoff)
    except Exception as exc:  # noqa: BLE001
        _raise_mapped(exc, runtime)
        raise  # pragma: no cover


@router.get("/droid/{device_id}/guidance")
async def droid_guidance(
    device_id: str, session_id: Optional[str] = Query(default=None)
) -> Dict[str, Any]:
    """Dry-run guidance for a Psathyrella droid. Read-only: never actuates."""
    runtime = _runtime()
    try:
        guidance = await runtime.droid_guidance(device_id, session_id)
    except Exception as exc:  # noqa: BLE001
        _raise_mapped(exc, runtime)
        raise  # pragma: no cover
    guidance["dry_run"] = True
    guidance["actuated"] = False
    guidance.setdefault("origin", ORIGIN_SIMULATED)
    return guidance


__all__ = [
    "AutopilotRequest",
    "ITDXChannelsRequest",
    "NLMObservationRequest",
    "VisionDetectJSON",
    "connectome_unavailable_detail",
    "fetch_command",
    "plan_one_off",
    "router",
]
