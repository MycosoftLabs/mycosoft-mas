"""
Decode Meshtastic MQTT payloads (ServiceEnvelope + MeshPacket) to plain dicts.

Requires the ``meshtastic`` PyPI package (protobuf definitions). If unavailable,
callers should skip decode and optionally store raw payload metadata only.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def normalize_node_id(raw: Optional[Any]) -> Optional[str]:
    """Return Meshtastic-style ``!xxxxxxxx`` node id or None."""
    if raw is None:
        return None
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return None
    return f"!{n & 0xFFFFFFFF:08x}"


def _mesh_packet_dict(mp: Any) -> Dict[str, Any]:
    try:
        from google.protobuf.json_format import MessageToDict

        return MessageToDict(mp, preserving_proto_field_name=True)
    except Exception as exc:  # noqa: BLE001
        logger.debug("MessageToDict mesh packet failed: %s", exc)
        return {}


def _extract_mesh_packet(envelope: Any) -> Optional[Any]:
    """Return protobuf MeshPacket from ServiceEnvelope for supported meshtastic versions."""
    for field in ("mesh_packet", "packet"):
        if hasattr(envelope, field):
            try:
                if envelope.HasField(field):
                    return getattr(envelope, field)
            except Exception:
                continue
    return None


def decode_service_envelope(topic: str, payload: bytes) -> Optional[Dict[str, Any]]:
    """
    Parse MQTT body as ``ServiceEnvelope``.

    Returns dict with keys including: ``topic``, ``gateway_id``, ``channel_id``,
    ``mesh_packet`` (dict), ``from_id``, ``to_id``, ``port_num_name``, ``rx_rssi``, ``rx_snr``.
    """
    try:
        from meshtastic.protobuf import mqtt_pb2  # type: ignore
    except ImportError:
        logger.warning("meshtastic protobuf not installed; cannot decode MQTT payload")
        return None

    env = mqtt_pb2.ServiceEnvelope()
    try:
        env.ParseFromString(payload)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Not a ServiceEnvelope on %s: %s", topic, exc)
        return None

    mp = _extract_mesh_packet(env)
    if mp is None:
        return {
            "topic": topic,
            "gateway_id": getattr(env, "gateway_id", None) or None,
            "channel_id": getattr(env, "channel_id", None) or None,
            "mesh_packet": None,
        }

    mesh_d = _mesh_packet_dict(mp)
    from_raw = getattr(mp, "from_", None) or getattr(mp, "from", None)
    to_raw = getattr(mp, "to", None)
    from_id = normalize_node_id(from_raw)
    to_id = normalize_node_id(to_raw)

    port_name: Optional[str] = None
    decoded = getattr(mp, "decoded", None)
    if decoded is not None:
        try:
            pvn = int(getattr(decoded, "portnum", 0) or 0)
        except (TypeError, ValueError):
            pvn = 0
        if pvn != 0:
            try:
                from meshtastic.protobuf import portnums_pb2  # type: ignore

                port_name = portnums_pb2.PortNum.Name(pvn)
            except Exception:  # noqa: BLE001
                port_name = str(pvn)

    rx_rssi = None
    rx_snr = None
    if mp.HasField("rx_rssi"):
        rx_rssi = float(mp.rx_rssi)
    if mp.HasField("rx_snr"):
        rx_snr = float(mp.rx_snr)

    gateway_id = None
    if getattr(env, "gateway_id", None):
        gateway_id = str(env.gateway_id).strip()
    elif topic:
        parts = [p for p in topic.split("/") if p]
        if parts:
            gateway_id = parts[-1] if parts[-1].startswith("!") else None

    pid = getattr(mp, "id", None)
    if isinstance(pid, (bytes, bytearray)):
        protobuf_id: Optional[str] = bytes(pid).hex()
    elif pid is not None:
        protobuf_id = str(pid)
    else:
        protobuf_id = None

    return {
        "topic": topic,
        "gateway_id": gateway_id,
        "channel_id": getattr(env, "channel_id", None) or None,
        "mesh_packet": mesh_d,
        "from_id": from_id,
        "to_id": to_id,
        "port_num_name": port_name,
        "rx_rssi": rx_rssi,
        "rx_snr": rx_snr,
        "hop_limit": int(mp.hop_limit) if mp.HasField("hop_limit") else None,
        "hop_start": int(mp.hop_start) if mp.HasField("hop_start") else None,
        "want_ack": bool(mp.want_ack) if mp.HasField("want_ack") else False,
        "protobuf_id": protobuf_id,
    }


def parse_meshtastic_topic(topic: str) -> Dict[str, Optional[str]]:
    """
    Parse ``msh/{region}/{modem}/{extra}/{channel}/{gateway}`` style topics.

    Extra segment is often ``e`` (encrypted) per Meshtastic 2.x public broker layout.
    """
    parts = [p for p in topic.strip("/").split("/") if p]
    out: Dict[str, Optional[str]] = {
        "region": None,
        "modem": None,
        "channel": None,
        "gateway": None,
    }
    if not parts or parts[0] != "msh":
        return out
    if len(parts) >= 2:
        out["region"] = parts[1]
    if len(parts) >= 3:
        out["modem"] = parts[2]
    if len(parts) >= 5:
        out["channel"] = parts[4]
    if len(parts) >= 6:
        out["gateway"] = parts[5]
    elif len(parts) >= 1:
        out["gateway"] = parts[-1] if parts[-1].startswith("!") else None
    return out


def topic_channel_region(topic: str) -> Tuple[Optional[str], Optional[str]]:
    meta = parse_meshtastic_topic(topic)
    return meta.get("channel"), meta.get("region")


def extract_payload_text_from_mesh_dict(mesh_d: Dict[str, Any]) -> Optional[str]:
    """
    Best-effort human-readable line from protobuf-as-dict ``mesh_packet`` (MessageToDict).

    Primary path: ``decoded.text`` (TEXT_MESSAGE_APP / similar). Extend as new decode fields are needed.
    """
    dec = mesh_d.get("decoded")
    if not isinstance(dec, dict):
        return None
    text = dec.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip()
    return None
