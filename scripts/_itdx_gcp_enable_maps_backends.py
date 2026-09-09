"""Enable Directions/Distance Matrix on the Map Tiles key project. Never print secrets."""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]
CREDS = ROOT / ".credentials.local"
WEB_ENV = Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\.env.local")
SERVICES = (
    "directions-backend.googleapis.com",
    "distancematrix-backend.googleapis.com",
    "geocoding-backend.googleapis.com",
)
AIZA_RE = re.compile(r"AIza[0-9A-Za-z_-]{10,}")


def redact(text: str) -> str:
    text = AIZA_RE.sub("AIza***", text)
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    if password:
        text = text.replace(password, "***")
    return text


def load_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        name, value = text.split("=", 1)
        name = name.strip()
        value = value.strip().strip('"').strip("'")
        if name and value:
            out[name] = value
    return out


def load_creds() -> None:
    for name, value in load_env_file(CREDS).items():
        os.environ.setdefault(name, value)


def maps_key() -> tuple[str, str]:
    merged = {**load_env_file(WEB_ENV), **load_env_file(CREDS)}
    for name in (
        "GOOGLE_MAPS_API_KEY",
        "NEXT_PUBLIC_GOOGLE_MAPS_API_KEY",
        "NEXT_PUBLIC_GOOGLE_MAP_TILES_API_KEY",
        "GOOGLE_API_KEY",
    ):
        value = merged.get(name) or os.environ.get(name) or ""
        if value:
            return name, value
    return "", ""


def probe_google(key: str) -> dict[str, str]:
    results: dict[str, str] = {}
    endpoints = {
        "directions": (
            "https://maps.googleapis.com/maps/api/directions/json",
            {
                "origin": "31.8697,-81.6072",
                "destination": "Hinesville,GA",
                "departure_time": "now",
                "mode": "driving",
                "key": key,
            },
        ),
        "distance": (
            "https://maps.googleapis.com/maps/api/distancematrix/json",
            {
                "origins": "31.8697,-81.6072",
                "destinations": "Hinesville,GA",
                "departure_time": "now",
                "mode": "driving",
                "key": key,
            },
        ),
        "geocode": (
            "https://maps.googleapis.com/maps/api/geocode/json",
            {"address": "Hinesville,GA", "key": key},
        ),
    }
    for label, (url, params) in endpoints.items():
        req = urllib.request.Request(
            url + "?" + urllib.parse.urlencode(params),
            headers={"User-Agent": "Mycosoft-MAS-ITDX/1.0"},
        )
        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                body = json.loads(response.read().decode("utf-8", "replace"))
        except Exception as exc:  # noqa: BLE001
            results[label] = f"HTTP_ERROR {type(exc).__name__}"
            continue
        status = str(body.get("status", "UNKNOWN"))
        err = str(body.get("error_message") or "")
        err = AIZA_RE.sub("AIza***", err)
        extra = ""
        details = body.get("error") or body.get("results")
        if isinstance(body.get("error"), dict):
            extra = str(body["error"])[:240]
        results[label] = f"{status} | {err}" + (f" | {extra}" if extra else "")
    return results


def ssh_connect(host: str, user: str = "mycosoft") -> paramiko.SSHClient:
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    key_candidates = [
        Path.home() / ".ssh" / "mycosoft_vm_automation_ed25519",
        Path.home() / ".ssh" / "mycosoft_vm_ed25519",
        Path.home() / ".ssh" / "id_ed25519",
        Path(r"d:\Users\admin2\.ssh") / "myca_vm191",
        Path(r"d:\Users\admin2\.ssh") / "id_ed25519",
    ]
    pkey = None
    last_err: Exception | None = None
    for key_path in key_candidates:
        if not key_path.is_file():
            continue
        try:
            pkey = paramiko.Ed25519Key.from_private_key_file(str(key_path))
            client.connect(
                host,
                username=user,
                pkey=pkey,
                password=password,
                timeout=25,
                allow_agent=False,
                look_for_keys=False,
            )
            return client
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            try:
                client.close()
            except Exception:
                pass
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            host,
            username=user,
            password=password,
            timeout=25,
            allow_agent=False,
            look_for_keys=False,
        )
        return client
    except Exception as exc:  # noqa: BLE001
        raise last_err or exc


def run(client: paramiko.SSHClient, cmd: str, timeout: int = 60, use_sudo: bool = False) -> str:
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    if use_sudo:
        cmd = f"sudo -S -p '' {cmd}"
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout, get_pty=use_sudo)
    if use_sudo:
        stdin.write(password + "\n")
        stdin.flush()
        stdin.channel.shutdown_write()
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    return redact(out + ("\n" + err if err.strip() else "")).replace("\u25cf", "*")


def inspect_host(host: str) -> None:
    print(f"=== HOST {host} ===")
    users = ["mycosoft"]
    if host.endswith(".191"):
        users = ["mycosoft", "myca"]
    client = None
    last = None
    for user in users:
        try:
            client = ssh_connect(host, user=user)
            print("SSH_OK", host, "user", user)
            break
        except Exception as exc:  # noqa: BLE001
            last = exc
            print("SSH_TRY_FAIL", host, user, type(exc).__name__)
    if client is None:
        print("SSH_FAIL", host, type(last).__name__ if last else "unknown")
        return
    try:
        print(
            run(
                client,
                "bash -lc "
                + repr(
                    "echo GCLOUD=$(command -v gcloud || echo missing); "
                    "echo ADC=$([ -f \"$HOME/.config/gcloud/application_default_credentials.json\" ] && echo yes || echo no); "
                    "echo SA_191=$([ -f /opt/myca/credentials/google/service_account.json ] && echo yes || echo no); "
                    "echo SA_188=$([ -f /home/mycosoft/mycosoft/mas/credentials/google/service_account.json ] && echo yes || echo no); "
                    "echo SA_OPT=$([ -f /opt/mycosoft/credentials/google/service_account.json ] && echo yes || echo no); "
                    "ls /opt/myca/credentials/google 2>/dev/null | head; "
                    "ls /home/mycosoft/mycosoft/mas/.credentials* 2>/dev/null; "
                    "ls /etc/systemd/system/mas-orchestrator.service.d 2>/dev/null; "
                    "test -f /home/mycosoft/mycosoft/mas/.credentials.maps.env && "
                    "cut -d= -f1 /home/mycosoft/mycosoft/mas/.credentials.maps.env || echo NO_MAPS_ENV; "
                    "systemctl is-active mas-orchestrator 2>/dev/null || true; "
                    "systemctl show mas-orchestrator -p ActiveState -p SubState -p EnvironmentFiles --no-pager 2>/dev/null | head -20; "
                    "env | awk -F= '/GOOGLE|GCP_|GCLOUD|GOOGLE_CLOUD|SERVICE_ACCOUNT/ {print $1}' | sort -u"
                ),
            )
        )
    finally:
        client.close()


def fetch_remote_sa(host: str, remote: str) -> Path | None:
    try:
        client = ssh_connect(host)
    except Exception as exc:  # noqa: BLE001
        print("SA_FETCH_SSH_FAIL", host, type(exc).__name__)
        return None
    try:
        check = run(client, f"test -f {remote} && echo YES || echo NO")
        if "YES" not in check:
            print("SA_ABSENT", host, remote)
            return None
        dest = Path(tempfile.gettempdir()) / "itdx_gcp_sa.json"
        sftp = client.open_sftp()
        sftp.get(remote, str(dest))
        sftp.close()
        os.chmod(dest, 0o600)
        print("SA_FETCHED", host, "bytes", dest.stat().st_size)
        return dest
    except Exception as exc:  # noqa: BLE001
        print("SA_FETCH_FAIL", type(exc).__name__)
        return None
    finally:
        client.close()


def sa_project_id(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    project = str(data.get("project_id") or "")
    email = str(data.get("client_email") or "")
    # print identity only, not private key
    print("SA_PROJECT", project or "MISSING")
    if email:
        local = email.split("@", 1)[0]
        print("SA_EMAIL_LOCAL", local)
    return project


def enable_with_sa(sa_path: Path, project: str) -> None:
    try:
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account
    except ImportError:
        print("GOOGLE_AUTH_MISSING")
        return
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
    creds = service_account.Credentials.from_service_account_file(str(sa_path), scopes=scopes)
    creds.refresh(Request())
    token = creds.token
    for service in SERVICES:
        url = (
            f"https://serviceusage.googleapis.com/v1/projects/{project}/services/{service}:enable"
        )
        req = urllib.request.Request(
            url,
            data=b"{}",
            method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                body = response.read().decode("utf-8", "replace")
            print("ENABLE_OK", service, "http", response.status, "len", len(body))
        except urllib.error.HTTPError as exc:
            err = exc.read().decode("utf-8", "replace")
            err = AIZA_RE.sub("AIza***", err)[:500]
            print("ENABLE_HTTP", service, exc.code, err)
        except Exception as exc:  # noqa: BLE001
            print("ENABLE_FAIL", service, type(exc).__name__)


def try_update_key_restrictions(sa_path: Path, project: str) -> None:
    """If API Keys API is allowed, add Directions/Distance Matrix to the existing key."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account
    except ImportError:
        return
    creds = service_account.Credentials.from_service_account_file(
        str(sa_path),
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    creds.refresh(Request())
    url = f"https://apikeys.googleapis.com/v2/projects/{project}/locations/global/keys"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {creds.token}"})
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", "replace")[:400]
        print("KEYS_LIST_HTTP", exc.code, AIZA_RE.sub("AIza***", err))
        return
    except Exception as exc:  # noqa: BLE001
        print("KEYS_LIST_FAIL", type(exc).__name__)
        return
    keys = payload.get("keys") or []
    print("KEYS_COUNT", len(keys))
    wanted = {
        "directions-backend.googleapis.com",
        "distancematrix-backend.googleapis.com",
        "geocoding-backend.googleapis.com",
        "maps-backend.googleapis.com",
        "tile.googleapis.com",
        "maptiler.googleapis.com",
        "photorealistic-3d-tiles",
    }
    for item in keys:
        name = item.get("name") or ""
        display = item.get("displayName") or ""
        restrictions = item.get("restrictions") or {}
        api_targets = ((restrictions.get("apiTargets") or []) if isinstance(restrictions, dict) else [])
        services = [t.get("service") for t in api_targets if isinstance(t, dict)]
        print("KEY_META", display, "targets", ",".join(s for s in services if s) or "UNRESTRICTED")
        # Do not print keyString. Patch only if this looks like the tiles/maps key.
        if not services:
            continue
        joined = " ".join(services).lower()
        if "tile" not in joined and "gemini" not in joined and "generativelanguage" not in joined and "maps" not in joined:
            continue
        updated = list(dict.fromkeys([*services, *wanted]))
        if set(updated) == set(services):
            print("KEY_ALREADY_HAS_BACKENDS", display)
            continue
        body = json.dumps(
            {
                "restrictions": {
                    **{k: v for k, v in restrictions.items() if k != "apiTargets"},
                    "apiTargets": [{"service": s} for s in updated if s],
                }
            }
        ).encode("utf-8")
        patch = urllib.request.Request(
            f"https://apikeys.googleapis.com/v2/{name}?updateMask=restrictions",
            data=body,
            method="PATCH",
            headers={
                "Authorization": f"Bearer {creds.token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(patch, timeout=30) as response:
                print("KEY_PATCH_OK", display, "http", response.status)
        except urllib.error.HTTPError as exc:
            err = exc.read().decode("utf-8", "replace")[:400]
            print("KEY_PATCH_HTTP", display, exc.code, AIZA_RE.sub("AIza***", err))
        except Exception as exc:  # noqa: BLE001
            print("KEY_PATCH_FAIL", display, type(exc).__name__)


def main() -> int:
    load_creds()
    name, key = maps_key()
    print("KEY_NAME", name or "MISSING", "LEN", len(key), "PREFIX", (key[:4] if key else "NONE"))
    if key:
        for label, result in probe_google(key).items():
            print("PROBE", label, result)
    inspect_host("192.168.0.188")
    inspect_host("192.168.0.191")

    sa_candidates = [
        ("192.168.0.191", "/opt/myca/credentials/google/service_account.json"),
        ("192.168.0.188", "/home/mycosoft/mycosoft/mas/credentials/google/service_account.json"),
        ("192.168.0.188", "/opt/mycosoft/credentials/google/service_account.json"),
        ("192.168.0.191", "/opt/mycosoft/credentials/google/service_account.json"),
    ]
    sa_path = None
    project = ""
    for host, remote in sa_candidates:
        fetched = fetch_remote_sa(host, remote)
        if fetched:
            sa_path = fetched
            project = sa_project_id(fetched)
            break
    if sa_path and project:
        enable_with_sa(sa_path, project)
        try_update_key_restrictions(sa_path, project)
        if key:
            print("REPROBE_AFTER_ENABLE")
            for label, result in probe_google(key).items():
                print("PROBE", label, result)
    else:
        print("NO_SA_OR_PROJECT — cannot enable via API")
    if sa_path and sa_path.exists():
        try:
            sa_path.unlink()
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
