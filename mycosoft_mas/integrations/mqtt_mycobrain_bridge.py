"""
MQTT subscriber bridge: MycoBrain / Jetson topics → MAS device registry + MINDEX telemetry.

Topic layout (prefix configurable, default ``mycobrain``):

- ``{prefix}/{device_id}/heartbeat`` — JSON body forwarded to ``POST {MAS}/api/devices/heartbeat``
- ``{prefix}/{device_id}/envelope`` — Full MINDEX envelope (hdr/pack/ts/seq) → telemetry ingest
- ``{prefix}/{device_id}/telemetry`` — Simplified readings; envelope is synthesized for MINDEX

Environment (see docs/MQTT_MAS_MINDEX_BRIDGE_APR13_2026.md):
  MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_USERNAME, MQTT_PASSWORD,
  MQTT_TOPIC_PREFIX, MAS_API_URL, MINDEX_API_URL,
  MINDEX_INTERNAL_TOKEN or MINDEX_INTERNAL_SECRET (HMAC; preferred when set)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

_TOPIC_RE = re.compile(r"^([^/]+)/([^/]+)/(heartbeat|envelope|telemetry)$")


def _mindex_hmac_token(service_name: str, secret: str) -> str:
    """Same algorithm as mindex_api/auth/internal_auth._generate_internal_token."""
    timestamp = str(int(time.time()))
    message = f"{service_name}:{timestamp}"
    signature = hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    raw = f"{service_name}:{timestamp}:{signature}"
    return base64.b64encode(raw.encode("utf-8")).decode("utf-8")


@dataclass
class ParsedTopic:
    prefix: str
    device_id: str
    action: str


def parse_mqtt_topic(topic: str) -> Optional[ParsedTopic]:
    """Parse ``prefix/device_id/{heartbeat|envelope|telemetry}``."""
    t = topic.strip().strip("/")
    m = _TOPIC_RE.match(t)
    if not m:
        return None
    return ParsedTopic(prefix=m.group(1), device_id=m.group(2), action=m.group(3))


def synthesize_envelope_from_telemetry(
    device_slug: str,
    body: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build a MINDEX-compatible envelope from a simplified MQTT payload.

    Expected shapes:
    - ``{"pack": [{"id": "x", "v": 1.0, "u": "C"}], "ts": {"utc": "..."}}``
    - ``{"readings": [...]}`` alias for pack
    """
    pack = body.get("pack")
    if not isinstance(pack, list):
        readings = body.get("readings")
        pack = readings if isinstance(readings, list) else []
    msg_id = str(body.get("msgId") or uuid.uuid4())
    ts = body.get("ts")
    if not isinstance(ts, dict):
        ts = {"utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}
    seq_raw = body.get("seq")
    if isinstance(seq_raw, int):
        seq = seq_raw
    else:
        seq = int(time.time() * 1000) % (2**31)
    hdr = {
        "deviceId": device_slug,
        "msgId": msg_id,
        "msgType": str(body.get("msgType") or "mqtt_telemetry"),
    }
    return {"hdr": hdr, "ts": ts, "seq": seq, "pack": pack}


def normalize_heartbeat_payload(device_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Merge topic device_id with JSON for MAS DeviceHeartbeat."""
    out = dict(data)
    out["device_id"] = str(out.get("device_id") or device_id)
    out.setdefault("device_name", out["device_id"])
    out.setdefault("host", os.environ.get("MQTT_BRIDGE_DEFAULT_HOST", "127.0.0.1"))
    out.setdefault("port", int(os.environ.get("MQTT_BRIDGE_DEFAULT_PORT", "8003")))
    out.setdefault("firmware_version", "unknown")
    out.setdefault("board_type", str(os.environ.get("MQTT_BRIDGE_DEFAULT_BOARD", "jetson")))
    out.setdefault("device_role", "gateway")
    out.setdefault("connection_type", "lan")
    out.setdefault("ingestion_source", "mqtt")
    if "sensors" not in out:
        out["sensors"] = []
    if "capabilities" not in out:
        out["capabilities"] = ["mqtt"]
    if isinstance(out["sensors"], str):
        out["sensors"] = [s for s in out["sensors"].split() if s]
    if isinstance(out["capabilities"], str):
        out["capabilities"] = [s for s in out["capabilities"].split() if s]
    ex = out.get("extra")
    if not isinstance(ex, dict):
        ex = {}
    ex.setdefault("mqtt_bridge", True)
    out["extra"] = ex
    return out


class MqttMycoBrainBridge:
    """Subscribe to MQTT and forward to MAS + MINDEX using synchronous httpx."""

    def __init__(self) -> None:
        self._http = httpx.Client(timeout=30.0)

    def _mas_url(self) -> str:
        return os.environ.get("MAS_API_URL", "http://192.168.0.188:8001").rstrip("/")

    def _mindex_url(self) -> str:
        return os.environ.get("MINDEX_API_URL", "http://192.168.0.189:8000").rstrip("/")

    def _internal_token(self) -> str:
        secret = (os.environ.get("MINDEX_INTERNAL_SECRET") or "").strip()
        if secret:
            svc = (os.environ.get("MINDEX_INTERNAL_SERVICE_NAME") or "mas-mqtt-bridge").strip()
            return _mindex_hmac_token(svc, secret)
        return (
            os.environ.get("MINDEX_INTERNAL_TOKEN")
            or os.environ.get("MINDEX_INTERNAL_TOKENS", "").split(",")[0]
            or ""
        ).strip()

    def post_mas_heartbeat(self, payload: Dict[str, Any]) -> None:
        url = f"{self._mas_url()}/api/devices/heartbeat"
        r = self._http.post(url, json=payload)
        r.raise_for_status()
        logger.info("MAS heartbeat ok: %s", payload.get("device_id"))

    def post_mindex_envelope(self, envelope: Dict[str, Any]) -> None:
        token = self._internal_token()
        if not token:
            logger.warning("MINDEX_INTERNAL_TOKEN unset; skipping MINDEX telemetry ingest")
            return
        url = f"{self._mindex_url()}/api/mindex/telemetry/envelope"
        headers = {"X-Internal-Token": token, "Content-Type": "application/json"}
        r = self._http.post(url, headers=headers, json={"envelope": envelope})
        r.raise_for_status()
        inserted = None
        try:
            inserted = r.json().get("samples_inserted")
        except Exception:
            pass
        logger.info(
            "MINDEX envelope ok: device=%s samples_inserted=%s",
            envelope.get("hdr", {}).get("deviceId"),
            inserted,
        )

    def handle_payload(self, topic: str, payload: bytes) -> None:
        parsed = parse_mqtt_topic(topic)
        if not parsed:
            logger.debug("Ignore non-bridge topic: %s", topic)
            return
        try:
            data = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            logger.error("Invalid JSON on %s: %s", topic, e)
            return

        if not isinstance(data, dict):
            logger.error("Payload must be a JSON object on %s", topic)
            return

        device_id = parsed.device_id

        if parsed.action == "heartbeat":
            hb = normalize_heartbeat_payload(device_id, data)
            self.post_mas_heartbeat(hb)
            return

        if parsed.action == "envelope":
            self.post_mindex_envelope(data)
            if os.environ.get("MQTT_BRIDGE_HEARTBEAT_ON_TELEMETRY", "").lower() in ("1", "true", "yes"):
                hb = normalize_heartbeat_payload(
                    device_id,
                    {
                        "device_name": data.get("hdr", {}).get("deviceId", device_id),
                        "host": os.environ.get("MQTT_BRIDGE_DEFAULT_HOST", "127.0.0.1"),
                    },
                )
                self.post_mas_heartbeat(hb)
            return

        if parsed.action == "telemetry":
            env = synthesize_envelope_from_telemetry(device_id, data)
            self.post_mindex_envelope(env)
            if os.environ.get("MQTT_BRIDGE_HEARTBEAT_ON_TELEMETRY", "1").lower() in ("1", "true", "yes"):
                hb = normalize_heartbeat_payload(device_id, {})
                self.post_mas_heartbeat(hb)
            return

    def run_forever(self) -> None:
        try:
            import paho.mqtt.client as mqtt
        except ImportError as e:
            raise RuntimeError("Install paho-mqtt (poetry: paho-mqtt)") from e

        host = os.environ.get("MQTT_BROKER_HOST", "192.168.0.196")
        port = int(os.environ.get("MQTT_BROKER_PORT", "1883"))
        user = os.environ.get("MQTT_USERNAME") or os.environ.get("MYCOBRAIN_MQTT_USERNAME")
        password = os.environ.get("MQTT_PASSWORD") or os.environ.get("MYCOBRAIN_MQTT_PASSWORD")
        prefix = os.environ.get("MQTT_TOPIC_PREFIX", "mycobrain")
        topic = f"{prefix}/#"

        def on_connect(client: Any, _userdata: Any, _flags: Any, reason_code: Any, _properties: Any = None) -> None:
            rc = getattr(reason_code, "value", reason_code)
            try:
                rc = int(rc)
            except (TypeError, ValueError):
                rc = 0 if reason_code == 0 or str(reason_code) == "Success" else 1
            if rc != 0:
                logger.error("MQTT connect failed: %s", reason_code)
                return
            client.subscribe(topic, qos=1)
            logger.info("MQTT subscribed: %s (broker %s:%s)", topic, host, port)

        def on_message(_client: Any, _userdata: Any, msg: Any) -> None:
            try:
                self.handle_payload(msg.topic, msg.payload)
            except httpx.HTTPStatusError as e:
                logger.error("HTTP error on %s: %s %s", msg.topic, e.response.status_code, e.response.text[:500])
            except Exception as exc:
                logger.exception("Bridge error on %s: %s", msg.topic, exc)

        # paho-mqtt v2 API
        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        except AttributeError:
            client = mqtt.Client()

        if user and password is not None:
            client.username_pw_set(user, password)

        client.on_connect = on_connect
        client.on_message = on_message

        logger.info("Connecting MQTT bridge to %s:%s …", host, port)
        client.connect(host, port, keepalive=60)
        client.loop_forever()


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    bridge = MqttMycoBrainBridge()
    bridge.run_forever()


if __name__ == "__main__":
    main()
