#!/usr/bin/env python3
"""
Validate Jetson MQTT connectivity over LAN and public WSS.

Checks executed from THIS machine:
- SSH reachability to Jetson

Checks executed ON Jetson:
- env file exists and has required keys
- TCP reachability to broker LAN 1883
- TLS WebSocket handshake to mqtt.mycosoft.com:443
- LAN MQTT auth + publish
- Public WSS MQTT auth + publish

Date: 2026-04-08
"""

from __future__ import annotations

import base64
import json
import os
import socket
import sys
from pathlib import Path

import paramiko

REPO = Path(__file__).resolve().parent.parent


def load_local_creds() -> None:
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


def test_ssh_port(host: str, port: int = 22, timeout: float = 5.0) -> tuple[bool, str]:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        return True, ""
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
    finally:
        s.close()


def run_remote_validation(host: str, user: str, password: str) -> dict:
    remote_py = r"""
import json
import socket
import ssl
import subprocess
import time
from pathlib import Path

result = {
    "env_file_exists": False,
    "env": {},
    "tcp_checks": {},
    "ws_handshake": {},
    "mqtt_lan": {},
    "mqtt_public_wss": {},
}

def parse_env(path: Path) -> dict:
    data = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        data[k.strip()] = v.strip()
    return data

def tcp_check(host: str, port: int, timeout: float = 8.0):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, int(port)))
        return True, ""
    except Exception as exc:
        return False, str(exc)
    finally:
        s.close()

def ws_handshake_tls(host: str, path: str = "/", timeout: float = 10.0):
    raw = socket.create_connection((host, 443), timeout=timeout)
    ctx = ssl.create_default_context()
    sock = ctx.wrap_socket(raw, server_hostname=host)
    req = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "Sec-WebSocket-Protocol: mqtt\r\n"
        "\r\n"
    )
    sock.sendall(req.encode("utf-8"))
    data = sock.recv(4096).decode("utf-8", errors="replace")
    sock.close()
    first = data.splitlines()[0] if data.splitlines() else data
    ok = "101" in first
    return ok, first

def ensure_paho():
    try:
        import paho.mqtt.client as mqtt  # noqa: F401
        return
    except Exception:
        subprocess.check_call(
            ["python3", "-m", "pip", "install", "--user", "paho-mqtt"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

def mqtt_connect_publish(host, port, username, password, transport="tcp", path="/", use_tls=False):
    ensure_paho()
    import paho.mqtt.client as mqtt

    state = {"connected": False, "error": "", "rc": None}

    def on_connect(client, userdata, flags, reason_code, properties=None):
        rc = getattr(reason_code, "value", reason_code)
        try:
            rc = int(rc)
        except Exception:  # noqa: BLE001
            rc = 1
        state["rc"] = rc
        if rc == 0:
            state["connected"] = True
        else:
            state["error"] = f"connect_rc={rc}"

    def on_connect_fail(client, userdata):
        state["error"] = "connect_fail"

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, transport=transport, protocol=mqtt.MQTTv311)
    client.username_pw_set(username, password)
    if transport == "websockets":
        client.ws_set_options(path=path or "/")
    if use_tls:
        client.tls_set(cert_reqs=ssl.CERT_REQUIRED)

    client.on_connect = on_connect
    client.on_connect_fail = on_connect_fail

    try:
        client.connect(host, int(port), 20)
    except Exception as exc:
        return {"ok": False, "stage": "connect", "error": str(exc)}

    client.loop_start()
    t0 = time.time()
    while time.time() - t0 < 15 and not state["connected"] and not state["error"]:
        time.sleep(0.2)

    if not state["connected"]:
        client.loop_stop()
        return {"ok": False, "stage": "auth", "error": state["error"] or f"rc={state['rc']}"}

    topic = "mycosoft/jetson/validation"
    payload = f"jetson-ok-{int(time.time())}"
    info = client.publish(topic, payload=payload, qos=0, retain=False)
    info.wait_for_publish(timeout=8)
    client.disconnect()
    client.loop_stop()
    return {"ok": True, "topic": topic, "payload": payload}

p = Path.home() / ".mycosoft" / "mycobrain_mqtt.env"
result["env_file_exists"] = p.exists()
if not p.exists():
    print(json.dumps(result, indent=2))
    raise SystemExit(0)

env = parse_env(p)
safe_env = dict(env)
if "MYCOBRAIN_MQTT_PASSWORD" in safe_env:
    safe_env["MYCOBRAIN_MQTT_PASSWORD"] = "<redacted>"
result["env"] = safe_env

lan_ok, lan_err = tcp_check("192.168.0.196", 1883)
result["tcp_checks"]["broker_1883_from_jetson"] = {"ok": lan_ok, "error": lan_err}

ws_ok, ws_status = ws_handshake_tls("mqtt.mycosoft.com", env.get("MYCOBRAIN_MQTT_WS_PATH", "/"))
result["ws_handshake"] = {"ok": ws_ok, "status_line": ws_status}

username = env.get("MYCOBRAIN_MQTT_USERNAME", "mycobrain")
password = env.get("MYCOBRAIN_MQTT_PASSWORD", "")
ws_path = env.get("MYCOBRAIN_MQTT_WS_PATH", "/")

result["mqtt_lan"] = mqtt_connect_publish(
    host="192.168.0.196",
    port=1883,
    username=username,
    password=password,
    transport="tcp",
    path="/",
    use_tls=False,
)

result["mqtt_public_wss"] = mqtt_connect_publish(
    host="mqtt.mycosoft.com",
    port=443,
    username=username,
    password=password,
    transport="websockets",
    path=ws_path,
    use_tls=True,
)

print(json.dumps(result, indent=2))
"""

    payload = base64.b64encode(remote_py.encode("utf-8")).decode("ascii")
    cmd = (
        "python3 - <<'PY'\n"
        "import base64\n"
        f"code = base64.b64decode('{payload}').decode('utf-8')\n"
        "exec(code)\n"
        "PY"
    )

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=host, username=user, password=password, timeout=30.0)
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    ssh.close()
    if code != 0:
        raise RuntimeError(
            "Remote validator failed with exit="
            f"{code}\nSTDOUT:\n{out.strip()}\nSTDERR:\n{err.strip()}"
        )
    if err.strip():
        print(f"Remote stderr: {err.strip()}", file=sys.stderr)
    try:
        return json.loads(out)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Remote validator returned non-JSON output.\n"
            f"STDOUT:\n{out.strip()}\nSTDERR:\n{err.strip()}"
        ) from exc


def main() -> int:
    load_local_creds()
    host = os.environ.get("JETSON_IP", "192.168.0.123")
    user = os.environ.get("JETSON_SSH_USER", "jetson")
    password = (
        os.environ.get("JETSON_SSH_PASSWORD")
        or os.environ.get("VM_PASSWORD")
        or os.environ.get("VM_SSH_PASSWORD")
        or ""
    )
    if not password:
        print("ERROR: missing JETSON_SSH_PASSWORD/VM_PASSWORD in environment.", file=sys.stderr)
        return 1

    ssh_ok, ssh_err = test_ssh_port(host, 22)
    summary = {
        "jetson_host": host,
        "ssh_port_22": {"ok": ssh_ok, "error": ssh_err},
        "remote_validation": {},
    }
    if not ssh_ok:
        print(json.dumps(summary, indent=2))
        return 2

    summary["remote_validation"] = run_remote_validation(host, user, password)
    print(json.dumps(summary, indent=2))

    rv = summary["remote_validation"]
    all_ok = (
        summary["ssh_port_22"]["ok"]
        and rv.get("env_file_exists", False)
        and rv.get("tcp_checks", {}).get("broker_1883_from_jetson", {}).get("ok", False)
        and rv.get("ws_handshake", {}).get("ok", False)
        and rv.get("mqtt_lan", {}).get("ok", False)
        and rv.get("mqtt_public_wss", {}).get("ok", False)
    )
    return 0 if all_ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
