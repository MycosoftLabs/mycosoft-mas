"""FlyBrain encoders — Observation → Poisson drive per atlas group (spec §6).

Every encoder returns ``Dict[group_name, rate_hz]`` keyed by the atlas group
names listed in the ``sensorimotor.inputs`` mapping of
``config/flybrain_atlas.yaml`` (``forward`` / ``left`` / ``right`` /
``attract``). Encoders never invent detections, never guess a heading and
never raise on user-supplied payloads: malformed or unknown fields are
skipped and reported in the ``notes`` list that accompanies every result.

Merging rule (``encode``): rates from several observations are merged by
**max** per group and then clipped to ``EncoderConfig.max_rate_hz``.

Heavy libraries are not needed here; this module is pure Python and safe
to import under ``MAS_LIGHT_IMPORT=1``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from mycosoft_mas.flybrain.schemas import Observation

Rates = Dict[str, float]
Notes = List[str]

INPUT_CHANNELS = ("forward", "left", "right", "attract")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EncoderConfig:
    """Tunable gains for the observation encoders.

    ``gain`` is the ``k`` of spec §6: each detection contributes
    ``k * conf * area`` Hz (``area`` = normalised bbox area in [0, 1]) to
    the side it lies on. With the default ``gain`` a confident detection
    covering a quarter of the frame drives its side at ~90 Hz, close to the
    100 Hz P9 drive of the Shiu et al. walking experiment.
    """

    max_rate_hz: float = 200.0
    gain: float = 400.0
    attract_categories: Tuple[str, ...] = ("food", "fungus", "plant")
    hfov_deg: float = 90.0
    # telemetry: heading error → turn drive, distance → forward drive
    telemetry_turn_max_hz: float = 100.0
    telemetry_turn_full_deg: float = 90.0
    telemetry_forward_max_hz: float = 100.0
    telemetry_arrival_m: float = 1.0
    telemetry_forward_full_m: float = 20.0
    # earthsim / itdx slice: per-item drive and density → forward
    earthsim_item_hz: float = 25.0
    earthsim_forward_max_hz: float = 100.0
    earthsim_density_ref: int = 10
    # nlm: attract drive = usable confidence * nlm_attract_max_hz
    nlm_attract_max_hz: float = 200.0


DEFAULT_CONFIG = EncoderConfig()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _as_float(value: Any) -> Optional[float]:
    """Coerce a payload scalar to a finite float, or ``None``."""
    if isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def wrap_deg(angle_deg: float) -> float:
    """Wrap an angle to (-180, 180]."""
    a = (angle_deg + 180.0) % 360.0 - 180.0
    return 180.0 if a == -180.0 else a


def _sensorimotor_inputs(sensorimotor: Any) -> Dict[str, List[str]]:
    """Return ``{channel: [group, ...]}`` from an atlas sensorimotor mapping.

    Accepts the ``sensorimotor`` mapping itself or a whole atlas dict that
    contains one. Missing or malformed channels yield empty group lists.
    """
    mapping: Any = sensorimotor
    if isinstance(mapping, Mapping) and "sensorimotor" in mapping and "inputs" not in mapping:
        mapping = mapping.get("sensorimotor")
    inputs: Any = mapping.get("inputs") if isinstance(mapping, Mapping) else None
    out: Dict[str, List[str]] = {}
    for channel in INPUT_CHANNELS:
        groups = inputs.get(channel) if isinstance(inputs, Mapping) else None
        if isinstance(groups, str):
            groups = [groups]
        if not isinstance(groups, (list, tuple)):
            groups = []
        out[channel] = [str(g) for g in groups if isinstance(g, str) and g]
    return out


def known_groups(sensorimotor: Any) -> List[str]:
    """All atlas group names referenced by the sensorimotor mapping.

    Includes ``inputs`` and ``readouts`` groups, plus an optional
    ``all_groups``/``groups`` list when the caller passes the full atlas
    group inventory alongside the mapping. Used to validate ``raw_rates``.
    """
    mapping: Any = sensorimotor
    if isinstance(mapping, Mapping) and "sensorimotor" in mapping and "inputs" not in mapping:
        mapping = mapping.get("sensorimotor")
    names: List[str] = []
    if not isinstance(mapping, Mapping):
        return names
    for section in ("inputs", "readouts"):
        block = mapping.get(section)
        if not isinstance(block, Mapping):
            continue
        for groups in block.values():
            if isinstance(groups, str):
                groups = [groups]
            if isinstance(groups, (list, tuple)):
                names.extend(str(g) for g in groups if isinstance(g, str) and g)
    for key in ("all_groups", "groups"):
        extra = mapping.get(key)
        if isinstance(extra, Mapping):
            names.extend(str(k) for k in extra.keys())
        elif isinstance(extra, (list, tuple)):
            names.extend(str(g) for g in extra if isinstance(g, str) and g)
    seen: Dict[str, None] = {}
    for n in names:
        seen.setdefault(n, None)
    return list(seen.keys())


def _channels_to_groups(
    channels: Mapping[str, float], sensorimotor: Any, cfg: EncoderConfig
) -> Rates:
    """Map channel rates onto atlas groups (max-merge), clipped to max_rate_hz."""
    inputs = _sensorimotor_inputs(sensorimotor)
    rates: Rates = {}
    for channel, hz in channels.items():
        value = _as_float(hz)
        if value is None or value <= 0.0:
            continue
        value = min(value, cfg.max_rate_hz)
        for group in inputs.get(channel, []):
            rates[group] = max(rates.get(group, 0.0), value)
    return rates


def merge_rates(*rate_maps: Mapping[str, float], max_rate_hz: float = 200.0) -> Rates:
    """Merge several ``{group: hz}`` maps by max per group and clip."""
    merged: Rates = {}
    for rate_map in rate_maps:
        if not isinstance(rate_map, Mapping):
            continue
        for group, hz in rate_map.items():
            value = _as_float(hz)
            if value is None or value <= 0.0:
                continue
            merged[str(group)] = max(merged.get(str(group), 0.0), min(value, max_rate_hz))
    return merged


def _bbox_norm(
    det: Mapping[str, Any], frame_w: Optional[float], frame_h: Optional[float]
) -> Optional[Tuple[float, float, float, float]]:
    """Return the detection bbox normalised to [0, 1] or ``None`` if unusable."""
    norm = det.get("bbox_norm")
    if isinstance(norm, (list, tuple)) and len(norm) == 4:
        vals = [_as_float(v) for v in norm]
        if all(v is not None for v in vals):
            x1, y1, x2, y2 = (min(max(float(v), 0.0), 1.0) for v in vals)  # type: ignore[arg-type]
            return x1, y1, x2, y2
    raw = det.get("bbox_xyxy", det.get("bbox"))
    if not isinstance(raw, (list, tuple)) or len(raw) != 4:
        return None
    vals = [_as_float(v) for v in raw]
    if any(v is None for v in vals):
        return None
    x1, y1, x2, y2 = (float(v) for v in vals)  # type: ignore[arg-type]
    if frame_w and frame_h and frame_w > 0 and frame_h > 0:
        return (
            min(max(x1 / frame_w, 0.0), 1.0),
            min(max(y1 / frame_h, 0.0), 1.0),
            min(max(x2 / frame_w, 0.0), 1.0),
            min(max(y2 / frame_h, 0.0), 1.0),
        )
    if all(0.0 <= v <= 1.0 for v in (x1, y1, x2, y2)):
        return x1, y1, x2, y2
    return None


def _payload_heading(payload: Mapping[str, Any]) -> Optional[float]:
    heading = _as_float(payload.get("heading_deg"))
    if heading is not None:
        return heading
    pose = payload.get("pose")
    if isinstance(pose, Mapping):
        return _as_float(pose.get("heading_deg"))
    return None


def _point_latlon(item: Any) -> Optional[Tuple[float, float]]:
    """Extract ``(lat, lon)`` from the common asset/device/point shapes."""
    if isinstance(item, (list, tuple)) and len(item) >= 2:
        lon, lat = _as_float(item[0]), _as_float(item[1])
        if lat is not None and lon is not None:
            return lat, lon
        return None
    if not isinstance(item, Mapping):
        return None
    for lat_key, lon_key in (("lat", "lon"), ("lat", "lng"), ("latitude", "longitude")):
        lat, lon = _as_float(item.get(lat_key)), _as_float(item.get(lon_key))
        if lat is not None and lon is not None:
            return lat, lon
    for nested in ("location", "position", "center", "coordinates", "coords"):
        sub = item.get(nested)
        if sub is not None and sub is not item:
            found = _point_latlon(sub)
            if found:
                return found
    geom = item.get("geometry")
    if isinstance(geom, Mapping) and geom.get("type") == "Point":
        return _point_latlon(geom.get("coordinates"))
    return None


def _bearing_deg(from_lat: float, from_lon: float, to_lat: float, to_lon: float) -> float:
    """Initial great-circle bearing in degrees clockwise from north."""
    phi1, phi2 = math.radians(from_lat), math.radians(to_lat)
    dlon = math.radians(to_lon - from_lon)
    x = math.sin(dlon) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlon)
    return math.degrees(math.atan2(x, y)) % 360.0


def _split_lateral(rel_deg: float) -> Tuple[float, float]:
    """Return (left_share, right_share) for a relative bearing; centre splits evenly."""
    if rel_deg < 0.0:
        return 1.0, 0.0
    if rel_deg > 0.0:
        return 0.0, 1.0
    return 0.5, 0.5


# ---------------------------------------------------------------------------
# Individual encoders
# ---------------------------------------------------------------------------


def encode_detections(
    payload: Any, sensorimotor: Any, cfg: Optional[EncoderConfig] = None
) -> Tuple[Rates, Notes]:
    """``DetectionFrame`` dict → left/right/attract drive (spec §6 ``detections``).

    Position rule: ``bearing_deg`` relative to the payload heading when both
    are present, otherwise the horizontal bbox centre ``cx`` (left half →
    ``inputs.left``, right half → ``inputs.right``, exact centre split).
    Contribution per detection is ``gain * conf * area`` where ``area`` is
    the *measured* normalised bbox area; a detection without a usable bbox
    (even one carrying ``bearing_deg``) gets no drive and is counted as
    skipped — no nominal area is ever substituted. Detections whose
    ``category`` (or class name) is in ``attract_categories`` also drive
    ``inputs.attract``. No detections → no drive.
    """
    cfg = cfg or DEFAULT_CONFIG
    notes: Notes = []
    if not isinstance(payload, Mapping):
        return {}, ["detections: payload is not a mapping; ignored"]
    if payload.get("available") is False:
        return {}, [
            f"detections: frame unavailable ({payload.get('note') or 'no reason'}); no drive"
        ]
    raw_list = payload.get("detections")
    if raw_list is None:
        return {}, ["detections: no 'detections' field; no drive"]
    if not isinstance(raw_list, (list, tuple)):
        return {}, ["detections: 'detections' is not a list; ignored"]
    if not raw_list:
        return {}, ["detections: empty frame; no drive"]

    frame_w = _as_float(payload.get("frame_w"))
    frame_h = _as_float(payload.get("frame_h"))
    heading = _payload_heading(payload)
    attract_set = {c.lower() for c in cfg.attract_categories}

    left = right = attract = 0.0
    used = skipped = 0
    for i, det in enumerate(raw_list):
        if hasattr(det, "model_dump") and not isinstance(det, Mapping):
            try:
                det = det.model_dump()
            except Exception:  # pragma: no cover - defensive
                det = None
        if not isinstance(det, Mapping):
            skipped += 1
            notes.append(f"detections[{i}]: not an object; skipped")
            continue
        conf = _as_float(det.get("conf", det.get("confidence")))
        if conf is None:
            skipped += 1
            notes.append(f"detections[{i}]: missing/invalid conf; skipped")
            continue
        conf = min(max(conf, 0.0), 1.0)
        box = _bbox_norm(det, frame_w, frame_h)
        bearing = _as_float(det.get("bearing_deg"))
        if box is None:
            # Spec §6: contribution = k * conf * area with a *measured* normalised bbox
            # area. Without a usable bbox there is no measured area, so the detection
            # gets no drive — never substitute a nominal area constant.
            skipped += 1
            if bearing is not None:
                notes.append(
                    f"detections[{i}]: bearing_deg given but no usable bbox area "
                    "(need frame_w/frame_h or bbox_norm); no drive; skipped"
                )
            else:
                notes.append(
                    f"detections[{i}]: no usable bbox (need frame_w/frame_h or bbox_norm); skipped"
                )
            continue
        x1, y1, x2, y2 = box
        area = max(0.0, x2 - x1) * max(0.0, y2 - y1)
        rel: float
        if bearing is not None and heading is not None:
            rel = wrap_deg(bearing - heading)
        else:
            rel = ((x1 + x2) / 2.0 - 0.5) * cfg.hfov_deg
        contribution = cfg.gain * conf * area
        l_share, r_share = _split_lateral(rel)
        left += contribution * l_share
        right += contribution * r_share
        category = str(det.get("category") or "").lower()
        cls_name = str(det.get("cls") or det.get("class") or "").lower()
        if category in attract_set or cls_name in attract_set:
            attract += contribution
        used += 1

    rates = _channels_to_groups(
        {"left": left, "right": right, "attract": attract}, sensorimotor, cfg
    )
    if used == 0:
        notes.append("detections: no usable detections; no drive")
    elif skipped:
        notes.append(f"detections: encoded {used}, skipped {skipped}")
    return rates, notes


def encode_telemetry(
    payload: Any, sensorimotor: Any, cfg: Optional[EncoderConfig] = None
) -> Tuple[Rates, Notes]:
    """``{heading_deg, target_bearing_deg?, distance_to_goal_m?}`` → drive (spec §6).

    Heading error → left/right drive proportional to ``|error|`` (≤ 100 Hz);
    forward drive from ``distance_to_goal_m`` (0 when arrived). Missing
    fields simply produce no drive on that channel, with a note.
    """
    cfg = cfg or DEFAULT_CONFIG
    notes: Notes = []
    if not isinstance(payload, Mapping):
        return {}, ["telemetry: payload is not a mapping; ignored"]
    heading = _as_float(payload.get("heading_deg"))
    target = _as_float(payload.get("target_bearing_deg"))
    distance = _as_float(payload.get("distance_to_goal_m"))
    channels: Dict[str, float] = {}
    if heading is None:
        notes.append("telemetry: heading_deg missing; no turn drive")
    elif target is None:
        notes.append("telemetry: target_bearing_deg missing; no turn drive")
    else:
        error = wrap_deg(target - heading)
        turn_hz = cfg.telemetry_turn_max_hz * min(
            1.0, abs(error) / max(cfg.telemetry_turn_full_deg, 1e-9)
        )
        if error < 0.0:
            channels["left"] = turn_hz
        elif error > 0.0:
            channels["right"] = turn_hz
    if distance is None:
        notes.append("telemetry: distance_to_goal_m missing; no forward drive")
    elif distance <= cfg.telemetry_arrival_m:
        notes.append(
            "telemetry: arrived (distance_to_goal_m within arrival radius); forward drive 0"
        )
    else:
        channels["forward"] = cfg.telemetry_forward_max_hz * min(
            1.0, distance / max(cfg.telemetry_forward_full_m, 1e-9)
        )
    return _channels_to_groups(channels, sensorimotor, cfg), notes


def encode_earthsim(
    payload: Any, sensorimotor: Any, cfg: Optional[EncoderConfig] = None
) -> Tuple[Rates, Notes]:
    """ITDX map slice ``{ao:{bbox,center}, assets:[], devices:[]}`` + ``focus`` → drive.

    Bearings of assets/devices are taken from the AO centre. The observer
    heading is the bearing from the AO centre to ``focus`` when given,
    else ``heading_deg`` in the payload, else north (noted). Items on the
    left/right drive the matching inputs; item density drives forward.
    Assets whose category is in ``attract_categories`` also drive attract.
    """
    cfg = cfg or DEFAULT_CONFIG
    notes: Notes = []
    if not isinstance(payload, Mapping):
        return {}, ["earthsim: payload is not a mapping; ignored"]
    ao = payload.get("ao")
    origin: Optional[Tuple[float, float]] = None
    if isinstance(ao, Mapping):
        origin = _point_latlon(ao.get("center"))
        if origin is None:
            bbox = ao.get("bbox")
            if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
                vals = [_as_float(v) for v in bbox]
                if all(v is not None for v in vals):
                    w, s, e, n = (float(v) for v in vals)  # type: ignore[arg-type]
                    origin = ((s + n) / 2.0, (w + e) / 2.0)
    if origin is None:
        origin = _point_latlon(payload.get("focus"))
        if origin is not None:
            notes.append("earthsim: no AO centre; using focus as bearing origin")
    items: List[Tuple[str, Any]] = []
    for key in ("assets", "devices"):
        seq = payload.get(key)
        if seq is None:
            continue
        if not isinstance(seq, (list, tuple)):
            notes.append(f"earthsim: '{key}' is not a list; ignored")
            continue
        items.extend((key, it) for it in seq)
    if not items:
        return {}, notes + ["earthsim: no assets or devices; no drive"]

    heading: Optional[float] = None
    focus = _point_latlon(payload.get("focus"))
    if origin is not None and focus is not None and focus != origin:
        heading = _bearing_deg(origin[0], origin[1], focus[0], focus[1])
    if heading is None:
        heading = _payload_heading(payload)
    if heading is None:
        heading = 0.0
        notes.append("earthsim: no focus/heading; bearings measured from north")

    attract_set = {c.lower() for c in cfg.attract_categories}
    left = right = attract = 0.0
    located = 0
    for kind, item in items:
        if not isinstance(item, Mapping):
            continue
        category = str(item.get("category") or item.get("type") or item.get("kind") or "").lower()
        if category in attract_set:
            attract += cfg.earthsim_item_hz
        if origin is None:
            continue
        pt = _point_latlon(item)
        if pt is None:
            continue
        located += 1
        bearing = _bearing_deg(origin[0], origin[1], pt[0], pt[1])
        rel = wrap_deg(bearing - heading)
        l_share, r_share = _split_lateral(rel)
        left += cfg.earthsim_item_hz * l_share
        right += cfg.earthsim_item_hz * r_share
    if origin is None:
        notes.append("earthsim: no AO centre or focus; cannot compute bearings, density drive only")
    elif located == 0:
        notes.append("earthsim: no asset/device positions found; density drive only")
    density = min(1.0, len(items) / max(cfg.earthsim_density_ref, 1))
    channels = {
        "left": left,
        "right": right,
        "attract": attract,
        "forward": cfg.earthsim_forward_max_hz * density,
    }
    return _channels_to_groups(channels, sensorimotor, cfg), notes


def _usable_nlm_confidence(confidence: Any, text: str, metadata: Optional[Dict[str, Any]]) -> bool:
    """Delegate to the NLM service helper; local fallback keeps the 0.85 stub rejected."""
    try:
        from mycosoft_mas.nlm.inference.service import is_usable_nlm_confidence

        return bool(is_usable_nlm_confidence(confidence, text, metadata))
    except Exception:
        value = _as_float(confidence)
        if value is None or not 0.0 < value <= 1.0 or abs(value - 0.85) < 1e-9:
            return False
        lowered = (text or "").lower()
        if any(m in lowered for m in ("placeholder", "stub", "not loaded", "fallback")):
            return False
        if isinstance(metadata, dict) and (
            metadata.get("stub") or metadata.get("confidence_usable") is False
        ):
            return False
        return True


def encode_nlm(
    payload: Any, sensorimotor: Any, cfg: Optional[EncoderConfig] = None
) -> Tuple[Rates, Notes]:
    """``{model_loaded, confidence?, prediction?}`` → attract drive (spec §6 ``nlm``).

    ``model_loaded=false`` → no drive and an ``UNQUALIFIED`` note. Loaded →
    attract drive scaled by a usable confidence; the 0.85 stub, stub text
    and stub metadata are rejected (never turned into drive).
    """
    cfg = cfg or DEFAULT_CONFIG
    if not isinstance(payload, Mapping):
        return {}, ["nlm: payload is not a mapping; ignored"]
    if payload.get("model_loaded") is not True:
        return {}, ["nlm: UNQUALIFIED — scientific NLM not loaded; no drive"]
    confidence = payload.get("confidence")
    text = str(payload.get("prediction") or payload.get("text") or "")
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else None
    if not _usable_nlm_confidence(confidence, text, metadata):
        return {}, ["nlm: UNQUALIFIED — confidence missing or stub (0.85/placeholder); no drive"]
    value = float(confidence)
    rates = _channels_to_groups({"attract": cfg.nlm_attract_max_hz * value}, sensorimotor, cfg)
    return rates, [f"nlm: attract drive scaled by usable confidence {value:.3f}"]


def encode_raw_rates(
    payload: Any, allowed_groups: Iterable[str], max_rate_hz: float = DEFAULT_CONFIG.max_rate_hz
) -> Tuple[Rates, Notes]:
    """``{group: hz}`` pass-through validated against the atlas group names."""
    notes: Notes = []
    if not isinstance(payload, Mapping):
        return {}, ["raw_rates: payload is not a mapping; ignored"]
    allowed = {str(g) for g in allowed_groups}
    rates: Rates = {}
    for group, hz in payload.items():
        name = str(group)
        if name not in allowed:
            notes.append(f"raw_rates: unknown group '{name}'; ignored")
            continue
        value = _as_float(hz)
        if value is None or value < 0.0:
            notes.append(f"raw_rates: invalid rate for '{name}' ({hz!r}); ignored")
            continue
        if value > max_rate_hz:
            notes.append(f"raw_rates: '{name}' clipped from {value:g} to {max_rate_hz:g} Hz")
            value = max_rate_hz
        rates[name] = max(rates.get(name, 0.0), value)
    return rates, notes


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


def encode(
    observations: Sequence[Any],
    sensorimotor: Any,
    config: Optional[EncoderConfig] = None,
) -> Tuple[Rates, Notes]:
    """Encode a batch of observations into ``{group: rate_hz}`` plus notes.

    Rates from all observations are merged by max per group and clipped to
    ``config.max_rate_hz``. Unknown kinds, malformed observations and
    encoder errors are reported as notes; this function never raises on
    user input.
    """
    cfg = config or DEFAULT_CONFIG
    notes: Notes = []
    maps: List[Rates] = []
    allowed = known_groups(sensorimotor)

    encoders: Dict[str, Callable[[Any], Tuple[Rates, Notes]]] = {
        "detections": lambda p: encode_detections(p, sensorimotor, cfg),
        "telemetry": lambda p: encode_telemetry(p, sensorimotor, cfg),
        "earthsim": lambda p: encode_earthsim(p, sensorimotor, cfg),
        "itdx_slice": lambda p: encode_earthsim(p, sensorimotor, cfg),
        "nlm": lambda p: encode_nlm(p, sensorimotor, cfg),
        "raw_rates": lambda p: encode_raw_rates(p, allowed, cfg.max_rate_hz),
    }

    for i, obs in enumerate(observations or []):
        if isinstance(obs, Observation):
            kind, payload = obs.kind, obs.payload
        elif isinstance(obs, Mapping):
            kind = str(obs.get("kind", ""))
            payload = obs.get("payload", {})
        else:
            notes.append(f"observation[{i}]: unsupported type {type(obs).__name__}; ignored")
            continue
        encoder = encoders.get(kind)
        if encoder is None:
            notes.append(f"observation[{i}]: unknown kind '{kind}'; ignored")
            continue
        try:
            rates, enc_notes = encoder(payload)
        except Exception as exc:  # never raise on user input
            notes.append(f"observation[{i}] ({kind}): encoder error {type(exc).__name__}: {exc}")
            continue
        maps.append(rates)
        notes.extend(enc_notes)

    merged = merge_rates(*maps, max_rate_hz=cfg.max_rate_hz)
    if not merged and observations:
        notes.append("encode: no drive produced from observations")
    return merged, notes


__all__ = [
    "DEFAULT_CONFIG",
    "EncoderConfig",
    "INPUT_CHANNELS",
    "encode",
    "encode_detections",
    "encode_earthsim",
    "encode_nlm",
    "encode_raw_rates",
    "encode_telemetry",
    "known_groups",
    "merge_rates",
    "wrap_deg",
]
