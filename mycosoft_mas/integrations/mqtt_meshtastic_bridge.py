"""
MQTT subscriber: Meshtastic public/private broker → MINDEX meshtastic.* + Redis Stream ``mesh:packets``.

Topics: subscribe to ``msh/#`` (Meshtastic 2.x layout).

Environment:
  MESHTASTIC_MQTT_HOST (default ``mqtt.meshtastic.org`` for TLS or ``192.168.0.196`` plain)
  MESHTASTIC_MQTT_PORT (default ``8883`` if TLS else ``1883``)
  MESHTASTIC_MQTT_TLS: ``1``/``true`` to use TLS (default true when port 8883)
  MESHTASTIC_MQTT_USERNAME / MESHTASTIC_MQTT_PASSWORD (optional; public broker often uses apps)
  MINDEX_API_URL — origin only (``http://host:8000``) **or** Fusarium-style suffix ``.../api/mindex``
    (internal ingest URL is normalized the same way as ``meshtastic_api._mindex_meshtastic_base``).
  MINDEX_INTERNAL_SECRET or MINDEX_INTERNAL_TOKEN
  REDIS_URL (default ``redis://192.168.0.189:6379/0``)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
from typing import Any, Dict, Optional

import httpx

from mycosoft_mas.integrations.meshtastic_protocol import (
    decode_service_envelope,
    extract_payload_text_from_mesh_dict,
    topic_channel_region,
)
from mycosoft_mas.integrations.mqtt_mycobrain_bridge import _mindex_hmac_token

logger = logging.getLogger(__name__)

STREAM_KEY = "mesh:packets"


class MqttMeshtasticBridge:
    """Subscribe to Meshtastic MQTT, decode ServiceEnvelope, persist to MINDEX + Redis stream."""

    def __init__(self) -> None:
        self._http = httpx.Client(timeout=30.0)
        self._redis = self._connect_redis()

    def _connect_redis(self):  # type: ignore[no-untyped-def]
        try:
            import redis as redis_sync

            url = os.environ.get("REDIS_URL", "redis://192.168.0.189:6379/0")
            r = redis_sync.from_url(url, decode_responses=True)
            r.ping()
            logger.info("Redis connected for mesh stream: %s", url.split("@")[-1])
            return r
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis unavailable (%s); mesh:packets stream disabled", exc)
            return None

    def _mindex_internal_meshtastic_base(self) -> str:
        """Match ``meshtastic_api._mindex_meshtastic_base``: avoid ``/api/mindex/api/mindex/...`` when env includes suffix."""
        u = (os.environ.get("MINDEX_API_URL") or "http://192.168.0.189:8000").rstrip("/")
        if u.endswith("/api/mindex"):
            return f"{u}/internal/meshtastic"
        return f"{u}/api/mindex/internal/meshtastic"

    def _internal_token(self) -> str:
        secret = (os.environ.get("MINDEX_INTERNAL_SECRET") or "").strip()
        if secret:
            svc = (os.environ.get("MINDEX_INTERNAL_SERVICE_NAME") or "mas-meshtastic-bridge").strip()
            return _mindex_hmac_token(svc, secret)
        return (
            os.environ.get("MINDEX_INTERNAL_TOKEN")
            or os.environ.get("MINDEX_INTERNAL_TOKENS", "").split(",")[0]
            or ""
        ).strip()

    def _headers(self) -> Dict[str, str]:
        token = self._internal_token()
        return {"X-Internal-Token": token, "Content-Type": "application/json"}

    def _post(self, path: str, body: Dict[str, Any]) -> None:
        token = self._internal_token()
        if not token:
            logger.warning("MINDEX internal token unset; skip %s", path)
            return
        url = f"{self._mindex_internal_meshtastic_base()}{path}"
        r = self._http.post(url, headers=self._headers(), json=body)
        r.raise_for_status()

    def _push_stream(self, event: Dict[str, Any]) -> None:
        if not self._redis:
            return
        try:
            self._redis.xadd(
                STREAM_KEY,
                {"data": json.dumps(event, default=str)},
                maxlen=5000,
                approximate=True,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis XADD failed: %s", exc)

    def _packet_uid(self, topic: str, payload: bytes, decoded: Optional[Dict[str, Any]]) -> str:
        if decoded and decoded.get("protobuf_id") is not None:
            pid = decoded.get("protobuf_id")
            if isinstance(pid, (bytes, bytearray)):
                return hashlib.sha256(topic.encode() + pid + payload).hexdigest()
            return hashlib.sha256(f"{topic}:{pid}".encode()).hexdigest()
        return hashlib.sha256(topic.encode() + payload).hexdigest()

    def handle_message(self, topic: str, payload: bytes) -> None:
        if not topic.startswith("msh/"):
            return
        decoded = decode_service_envelope(topic, payload)
        if not decoded:
            # Still record minimal row for diagnostics (no mock positions)
            uid = self._packet_uid(topic, payload, None)
            body = {
                "packet_uid": uid,
                "channel": topic_channel_region(topic)[0],
                "port_num": "UNKNOWN",
                "payload": {"decode_error": True, "topic": topic},
                "payload_text": None,
                "via_mqtt": True,
                "topic": topic,
                "raw_b64": base64.b64encode(payload).decode("ascii"),
            }
            try:
                self._post("/ingest/packet", body)
            except httpx.HTTPStatusError as e:
                logger.error("MINDEX ingest failed: %s %s", e.response.status_code, e.response.text[:300])
            self._push_stream({"topic": topic, "packet_uid": uid, "decode_error": True})
            return

        mp = decoded.get("mesh_packet") or {}
        uid = self._packet_uid(topic, payload, decoded)
        ch, region = topic_channel_region(topic)
        gateway = decoded.get("gateway_id")
        if not gateway:
            parts = [p for p in topic.split("/") if p]
            gateway = parts[-1] if parts and parts[-1].startswith("!") else None

        payload_text: Optional[str] = None
        if isinstance(mp, dict):
            payload_text = extract_payload_text_from_mesh_dict(mp)

        packet_body = {
            "packet_uid": uid,
            "from_node_id": decoded.get("from_id"),
            "to_node_id": decoded.get("to_id"),
            "gateway_node_id": gateway,
            "channel": ch,
            "port_num": decoded.get("port_num_name") or "UNKNOWN",
            "payload": mp if isinstance(mp, dict) else {},
            "payload_text": payload_text,
            "rx_rssi": decoded.get("rx_rssi"),
            "rx_snr": decoded.get("rx_snr"),
            "hop_limit": decoded.get("hop_limit"),
            "hop_start": decoded.get("hop_start"),
            "want_ack": decoded.get("want_ack"),
            "via_mqtt": True,
            "topic": topic,
            "raw_b64": base64.b64encode(payload).decode("ascii"),
        }
        try:
            self._post("/ingest/packet", packet_body)
        except httpx.HTTPStatusError as e:
            logger.error("MINDEX packet ingest failed: %s %s", e.response.status_code, e.response.text[:400])
            return

        if gateway:
            try:
                self._post(
                    "/ingest/observer",
                    {
                        "observer_id": gateway,
                        "node_id": gateway,
                        "region": region,
                        "gateway_kind": "mqtt",
                        "online": True,
                        "pkts_per_min": None,
                        "metadata": {"last_topic": topic},
                    },
                )
            except httpx.HTTPStatusError:
                logger.debug("observer upsert failed for %s", gateway)

        # Position / user inside decoded payload → upsert node when coordinates exist
        lat, lon = _extract_lat_lon(mp)
        node_for_pos = decoded.get("from_id")
        if node_for_pos and lat is not None and lon is not None:
            try:
                self._post(
                    "/ingest/node",
                    {
                        "node_id": node_for_pos,
                        "lat": lat,
                        "lon": lon,
                        "last_heard_at": _iso_now(),
                        "region": region,
                        "metadata": {"source": "mesh_packet"},
                    },
                )
            except httpx.HTTPStatusError:
                logger.debug("node upsert failed for %s", node_for_pos)

        stream_evt = {
            "topic": topic,
            "packet_uid": uid,
            "from_node_id": decoded.get("from_id"),
            "to_node_id": decoded.get("to_id"),
            "gateway_node_id": gateway,
            "channel": ch,
            "region": region,
            "port_num": packet_body["port_num"],
            "rx_rssi": decoded.get("rx_rssi"),
            "rx_snr": decoded.get("rx_snr"),
            "rx_time": _iso_now(),
            "want_ack": decoded.get("want_ack"),
            "hop_limit": decoded.get("hop_limit"),
            "hop_start": decoded.get("hop_start"),
        }
        if payload_text:
            stream_evt["payload_text"] = payload_text
        if lat is not None and lon is not None:
            stream_evt["from_lat"], stream_evt["from_lon"] = lat, lon
        self._push_stream(stream_evt)

        if decoded.get("from_id") and decoded.get("to_id"):
            try:
                self._post(
                    "/ingest/route",
                    {
                        "from_node_id": decoded["from_id"],
                        "to_node_id": decoded["to_id"],
                        "hops": decoded.get("hop_limit"),
                        "snr": decoded.get("rx_snr"),
                    },
                )
            except httpx.HTTPStatusError:
                pass

    def run_forever(self) -> None:
        try:
            import paho.mqtt.client as mqtt
        except ImportError as e:
            raise RuntimeError("Install paho-mqtt") from e

        host = os.environ.get("MESHTASTIC_MQTT_HOST", "mqtt.meshtastic.org")
        port = int(os.environ.get("MESHTASTIC_MQTT_PORT", "8883"))
        tls_env = os.environ.get("MESHTASTIC_MQTT_TLS", "").lower()
        use_tls = port == 8883 or tls_env in ("1", "true", "yes")
        if tls_env in ("0", "false", "no"):
            use_tls = False

        user = os.environ.get("MESHTASTIC_MQTT_USERNAME") or os.environ.get("MQTT_USERNAME")
        password = os.environ.get("MESHTASTIC_MQTT_PASSWORD") or os.environ.get("MQTT_PASSWORD")
        topic = os.environ.get("MESHTASTIC_MQTT_SUBSCRIBE", "msh/#")

        def on_connect(client: Any, _userdata: Any, _flags: Any, reason_code: Any, _properties: Any = None) -> None:
            rc = getattr(reason_code, "value", reason_code)
            try:
                rc = int(rc)
            except (TypeError, ValueError):
                rc = 0 if reason_code == 0 or str(reason_code) == "Success" else 1
            if rc != 0:
                logger.error("MQTT connect failed: %s", reason_code)
                return
            client.subscribe(topic, qos=0)
            logger.info("Meshtastic MQTT subscribed %s (broker %s:%s tls=%s)", topic, host, port, use_tls)

        def on_message(_client: Any, _userdata: Any, msg: Any) -> None:
            try:
                self.handle_message(msg.topic, msg.payload)
            except httpx.HTTPStatusError as e:
                logger.error("HTTP error on %s: %s %s", msg.topic, e.response.status_code, e.response.text[:400])
            except Exception as exc:
                logger.exception("Meshtastic bridge error on %s: %s", msg.topic, exc)

        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        except AttributeError:
            client = mqtt.Client()

        if user and password is not None:
            client.username_pw_set(user, password)

        if use_tls:
            client.tls_set()  # default CA bundle

        client.on_connect = on_connect
        client.on_message = on_message

        logger.info("Connecting Meshtastic MQTT bridge to %s:%s …", host, port)
        client.connect(host, port, keepalive=60)
        client.loop_forever()


def _iso_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _extract_lat_lon(mesh_packet_dict: Dict[str, Any]) -> tuple[Optional[float], Optional[float]]:
    """Pull lat/lon from MessageToDict-style POSITION_APP payload if present."""
    decoded = mesh_packet_dict.get("decoded") or {}
    pos = decoded.get("position") or decoded.get("Position") or {}
    lat = pos.get("latitude") or pos.get("latitudeI")
    lon = pos.get("longitude") or pos.get("longitudeI")
    if lat is None or lon is None:
        return None, None
    try:
        la = float(lat)
        lo = float(lon)
        # Meshtastic often uses integer millionths
        if abs(la) > 90 or abs(lo) > 180:
            la /= 1e7
            lo /= 1e7
        return la, lo
    except (TypeError, ValueError):
        return None, None


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    MqttMeshtasticBridge().run_forever()


if __name__ == "__main__":
    main()
