"""Probe Google Maps APIs and inspect 188 NLM/Ollama. Never print secrets."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import httpx
import paramiko

CREDS = Path(__file__).resolve().parents[1] / ".credentials.local"
KEY_CANDIDATES = [
    Path.home() / ".ssh" / "mycosoft_vm_ed25519",
    Path.home() / ".ssh" / "mycosoft_vm_automation_ed25519",
    Path.home() / ".ssh" / "id_ed25519",
]
GOOGLE_KEY_NAMES = (
    "GOOGLE_MAPS_API_KEY",
    "NEXT_PUBLIC_GOOGLE_MAPS_API_KEY",
    "GOOGLE_API_KEY",
    "NEXT_PUBLIC_GOOGLE_MAP_TILES_API_KEY",
)
ORIGIN = "31.8697,-81.6072"
DEST = "Hunter Army Airfield, Savannah, GA"


def load_creds() -> None:
    if not CREDS.exists():
        return
    for line in CREDS.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def first_key() -> tuple[str, str]:
    for name in GOOGLE_KEY_NAMES:
        value = (os.environ.get(name) or "").strip()
        if value:
            return name, value
    return "", ""


def ssh_client(host: str = "192.168.0.188") -> paramiko.SSHClient:
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    last: Exception | None = None
    for key_path in KEY_CANDIDATES:
        if not key_path.exists():
            continue
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                host,
                username="mycosoft",
                key_filename=str(key_path),
                timeout=15,
                allow_agent=False,
                look_for_keys=False,
            )
            return client
        except Exception as exc:
            last = exc
            client.close()
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        host,
        username="mycosoft",
        password=password,
        timeout=15,
        allow_agent=False,
        look_for_keys=False,
    )
    return client


def run(client: paramiko.SSHClient, cmd: str, timeout: int = 45) -> str:
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    return (out + ("\nSTDERR:\n" + err if err.strip() else "")).strip()


def probe_google(key: str) -> dict:
    endpoints = {
        "directions": (
            "https://maps.googleapis.com/maps/api/directions/json",
            {
                "origin": ORIGIN,
                "destination": DEST,
                "mode": "driving",
                "departure_time": "now",
                "key": key,
            },
        ),
        "distance_matrix": (
            "https://maps.googleapis.com/maps/api/distancematrix/json",
            {
                "origins": ORIGIN,
                "destinations": DEST,
                "mode": "driving",
                "departure_time": "now",
                "key": key,
            },
        ),
        "geocoding": (
            "https://maps.googleapis.com/maps/api/geocode/json",
            {"address": "Fort Stewart, Georgia, USA", "key": key},
        ),
    }
    results = {}
    with httpx.Client(timeout=12.0) as client:
        for name, (url, params) in endpoints.items():
            response = client.get(url, params=params)
            body = {}
            try:
                body = response.json()
            except Exception:
                body = {"raw": response.text[:200]}
            results[name] = {
                "http": response.status_code,
                "status": body.get("status"),
                "error_message": body.get("error_message"),
                "has_routes": bool(body.get("routes")),
                "has_rows": bool(body.get("rows")),
                "has_results": bool(body.get("results")),
            }
    return results


def main() -> int:
    load_creds()
    name, key = first_key()
    digest = hashlib.sha256(key.encode()).hexdigest()[:12] if key else "none"
    print(f"local_key_name={name or 'MISSING'} sha25612={digest} len={len(key)}")
    if key:
        print("local_google_probe=", json.dumps(probe_google(key)))

    client = ssh_client()
    print("\n===== 188 maps.env names =====")
    print(
        run(
            client,
            r"""
set +e
if [ -f /home/mycosoft/mycosoft/mas/.credentials.maps.env ]; then
  awk -F= '/^[A-Z]/ {print $1}' /home/mycosoft/mycosoft/mas/.credentials.maps.env
else
  echo 'NO_maps.env'
fi
echo '--- gcloud ---'
command -v gcloud || echo 'gcloud_missing'
echo '--- :8200 ---'
curl -sS -m 3 -o /tmp/nlm8200.txt -w 'nlm8200_http=%{http_code}\n' http://127.0.0.1:8200/health || true
head -c 200 /tmp/nlm8200.txt 2>/dev/null; echo
echo '--- ollama ---'
curl -sS -m 3 http://127.0.0.1:11434/api/tags | python3 -c "import sys,json; d=json.load(sys.stdin); print([m.get('name') for m in d.get('models',[])])"
echo '--- nlm health ---'
curl -sS -m 5 http://127.0.0.1:8001/api/nlm/health
echo
echo '--- disk ---'
df -h / | tail -1
""",
        )
    )

    print("\n===== 188 google probe (key never printed) =====")
    print(
        run(
            client,
            r"""
python3 - <<'PY'
import hashlib, json, os, urllib.parse, urllib.request
from pathlib import Path

def load(path):
    env = {}
    p = Path(path)
    if not p.is_file():
        return env
    for line in p.read_text(errors="replace").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        k,v = line.split("=",1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env

names = [
    "GOOGLE_MAPS_API_KEY",
    "NEXT_PUBLIC_GOOGLE_MAPS_API_KEY",
    "GOOGLE_API_KEY",
    "NEXT_PUBLIC_GOOGLE_MAP_TILES_API_KEY",
]
files = [
    "/home/mycosoft/mycosoft/mas/.credentials.maps.env",
    "/home/mycosoft/mycosoft/mas/.credentials.local",
    "/home/mycosoft/mycosoft/mas/.env",
]
env = {}
for f in files:
    for k,v in load(f).items():
        env.setdefault(k,v)
name = next((n for n in names if env.get(n) or os.environ.get(n)), "")
key = (env.get(name) or os.environ.get(name) or "").strip()
print("188_key_name", name or "MISSING", "sha25612", hashlib.sha256(key.encode()).hexdigest()[:12] if key else "none", "len", len(key))
if not key:
    raise SystemExit(0)

def get(url, params):
    q = urllib.parse.urlencode(params)
    req = urllib.request.Request(url + "?" + q, headers={"User-Agent": "Mycosoft-ITDX/1.0"})
    with urllib.request.urlopen(req, timeout=12) as resp:
        body = json.loads(resp.read().decode())
        return resp.status, body

origin = "31.8697,-81.6072"
dest = "Hunter Army Airfield, Savannah, GA"
probes = {
    "directions": ("https://maps.googleapis.com/maps/api/directions/json",
                   {"origin": origin, "destination": dest, "mode": "driving", "departure_time": "now", "key": key}),
    "distance_matrix": ("https://maps.googleapis.com/maps/api/distancematrix/json",
                        {"origins": origin, "destinations": dest, "mode": "driving", "departure_time": "now", "key": key}),
    "geocoding": ("https://maps.googleapis.com/maps/api/geocode/json",
                  {"address": "Fort Stewart, Georgia, USA", "key": key}),
}
out = {}
for n,(url,params) in probes.items():
    try:
        status, body = get(url, params)
        out[n] = {
            "http": status,
            "status": body.get("status"),
            "error_message": body.get("error_message"),
            "has_routes": bool(body.get("routes")),
            "has_rows": bool(body.get("rows")),
            "has_results": bool(body.get("results")),
        }
    except Exception as exc:
        out[n] = {"error": type(exc).__name__}
print(json.dumps(out))
PY
""",
            timeout=40,
        )
    )
    client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
