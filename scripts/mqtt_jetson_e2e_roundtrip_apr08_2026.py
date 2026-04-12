#!/usr/bin/env python3
"""
End-to-end MQTT roundtrip validation with Jetson publisher.

Validates that:
1) Jetson can publish over LAN MQTT (1883)
2) Jetson can publish over public Cloudflare WSS (443)
3) Broker receives both messages (verified by local subscriber)

Date: 2026-04-08
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import paramiko
import paho.mqtt.client as mqtt

REPO = Path(__file__).resolve().parent.parent


def load_creds() -> None:
    for base in (REPO, Path.cwd()):
        for name in (".credentials.local", ".env.local", ".env"):
            p = base / name
            if not p.exists():
                continue
            for raw in p.read_text(encoding="utf-8", errors="replace").splitlines():
                if not raw or raw.startswith("#") or "=" not in raw:
                    continue
                key, _, val = raw.partition("=")
                key = key.strip()
                val = val.strip().strip("\"'")
                if key and key not in os.environ:
                    os.environ[key] = val


def run_once() -> dict:
    jetson_host = os.getenv("JETSON_IP", "192.168.0.123")
    jetson_user = os.getenv("JETSON_SSH_USER", "jetson")
    jetson_pass = os.getenv("JETSON_SSH_PASSWORD") or os.getenv("VM_PASSWORD") or os.getenv("VM_SSH_PASSWORD")
    mqtt_user = "mycobrain"
    mqtt_pass = os.getenv("MQTT_BROKER_PASSWORD") or os.getenv("VM_PASSWORD") or ""
    broker_host = "192.168.0.196"
    broker_port = 1883

    if not jetson_pass:
        raise RuntimeError("Missing Jetson SSH password in environment.")
    if not mqtt_pass:
        raise RuntimeError("Missing MQTT password in environment.")

    topic = f"mycosoft/e2e/{int(time.time())}"
    state: dict[str, str | bool] = {"connected": False, "error": ""}
    received: list[str] = []

    def on_connect(client: mqtt.Client, userdata, flags, reason_code, properties=None) -> None:
        rc = getattr(reason_code, "value", reason_code)
        try:
            rc = int(rc)
        except Exception:  # noqa: BLE001
            rc = 1
        if rc == 0:
            state["connected"] = True
            client.subscribe(topic, qos=0)
        else:
            state["error"] = f"connect_rc={rc}"

    def on_message(client: mqtt.Client, userdata, msg: mqtt.MQTTMessage) -> None:
        received.append(msg.payload.decode("utf-8", errors="replace"))

    sub = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, transport="tcp", protocol=mqtt.MQTTv311)
    sub.username_pw_set(mqtt_user, mqtt_pass)
    sub.on_connect = on_connect
    sub.on_message = on_message
    sub.connect(broker_host, broker_port, 20)
    sub.loop_start()

    t0 = time.time()
    while time.time() - t0 < 10 and not state["connected"] and not state["error"]:
        time.sleep(0.2)
    if not state["connected"]:
        sub.loop_stop()
        sub.disconnect()
        raise RuntimeError(f"Local subscriber failed: {state['error'] or 'timeout'}")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(jetson_host, username=jetson_user, password=jetson_pass, timeout=20)

    remote_template = """python3 - <<'PY'
import ssl
import time
import paho.mqtt.client as mqtt

mode = {mode!r}
topic = {topic!r}
payload = {payload!r}
user = {user!r}
pw = {pw!r}

if mode == "lan":
    host = "192.168.0.196"
    port = 1883
    transport = "tcp"
    use_tls = False
else:
    host = "mqtt.mycosoft.com"
    port = 443
    transport = "websockets"
    use_tls = True

state = {{"ok": False, "err": ""}}

def on_connect(client, userdata, flags, reason_code, properties=None):
    rc = getattr(reason_code, "value", reason_code)
    try:
        rc = int(rc)
    except Exception:
        rc = 1
    if rc == 0:
        state["ok"] = True
        client.publish(topic, payload=payload, qos=0, retain=False)
        client.disconnect()
    else:
        state["err"] = f"connect_rc={{rc}}"

cli = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, transport=transport, protocol=mqtt.MQTTv311)
cli.username_pw_set(user, pw)
if transport == "websockets":
    cli.ws_set_options(path="/")
if use_tls:
    cli.tls_set(cert_reqs=ssl.CERT_REQUIRED)
cli.on_connect = on_connect
cli.connect(host, port, 20)
cli.loop_start()
start = time.time()
while time.time() - start < 15 and not state["ok"] and not state["err"]:
    time.sleep(0.2)
cli.loop_stop()
if not state["ok"]:
    raise SystemExit("JETSON_PUBLISH_FAIL " + (state["err"] or "timeout"))
print("JETSON_PUBLISH_OK", mode)
PY"""

    results = []
    for mode in ("lan", "wss"):
        payload = f"jetson-{mode}-{int(time.time())}"
        cmd = remote_template.format(mode=mode, topic=topic, payload=payload, user=mqtt_user, pw=mqtt_pass)
        _stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
        out = stdout.read().decode("utf-8", errors="replace").strip()
        err = stderr.read().decode("utf-8", errors="replace").strip()
        code = stdout.channel.recv_exit_status()
        results.append({"mode": mode, "exit": code, "out": out, "err": err, "payload": payload})

    deadline = time.time() + 12
    while time.time() < deadline and len(received) < 2:
        time.sleep(0.2)

    sub.loop_stop()
    sub.disconnect()
    ssh.close()

    success = len(received) >= 2 and all(r["exit"] == 0 for r in results)
    return {
        "topic": topic,
        "jetson_publish_results": results,
        "received_messages": received,
        "received_count": len(received),
        "success": success,
    }


def main() -> int:
    load_creds()
    result = run_once()
    print(json.dumps(result, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
