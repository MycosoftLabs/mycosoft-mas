#!/usr/bin/env python3
"""Start local n8n, import workflow files, and activate MYCA workflows.

This script never prints API keys. It uses N8N_API_KEY when available and falls
back to the n8n container CLI for local imports.
"""

from __future__ import annotations

import json
import os
import hashlib
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / "n8n" / "workflows"
MIRROR_DIR = ROOT / "workflows" / "n8n"


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value


for env_file in (
    ROOT / ".credentials.local",
    ROOT / ".env.local",
    ROOT / ".env",
    ROOT / "n8n" / ".env",
    ROOT / "n8n" / ".env.local",
):
    load_env_file(env_file)

N8N_URL = os.getenv("N8N_URL", "http://localhost:5678").rstrip("/")
N8N_CONTAINER = os.getenv("N8N_CONTAINER", "myca-n8n")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")


def log(message: str) -> None:
    print(message, flush=True)


def run(cmd: list[str], *, check: bool = False, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=check,
    )


def health() -> bool:
    try:
        with urllib.request.urlopen(f"{N8N_URL}/healthz", timeout=5) as response:
            return 200 <= response.status < 300
    except Exception:
        return False


def start_compose() -> None:
    compose = ROOT / "n8n" / "docker-compose.yml"
    if compose.exists():
        cmd = ["docker", "compose", "-f", str(compose), "up", "-d"]
    else:
        cmd = ["docker", "compose", "up", "-d", "n8n"]
    result = run(cmd)
    if result.returncode != 0:
        log("n8n docker compose start failed:")
        log(result.stderr.strip() or result.stdout.strip())
        raise SystemExit(result.returncode)


def wait_for_health(seconds: int = 90) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if health():
            return True
        time.sleep(3)
    return False


def request_json(method: str, path: str, payload: dict[str, Any] | None = None) -> tuple[int, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if N8N_API_KEY:
        headers["X-N8N-API-KEY"] = N8N_API_KEY
    req = urllib.request.Request(f"{N8N_URL}{path}", method=method, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            body = response.read().decode("utf-8", errors="replace")
            return response.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, {"error": body[:500]}


def import_with_api() -> tuple[int, int]:
    imported = 0
    failed = 0
    for path in sorted(WORKFLOW_DIR.glob("*.json")):
        if path.stem.upper() == "MANIFEST":
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload.pop("id", None)
        status, body = request_json("POST", "/api/v1/workflows", payload)
        if status in {200, 201}:
            imported += 1
        elif status == 401:
            log("n8n API key rejected with HTTP 401; skipping API import and using CLI fallback")
            return 0, 1
        elif status == 409 or "already" in str(body).lower():
            imported += 1
        else:
            failed += 1
            log(f"import failed {path.name}: HTTP {status}")
    return imported, failed


def workflow_id_for(path: Path) -> str:
    digest = hashlib.sha1(path.stem.encode("utf-8")).hexdigest()[:14]
    return f"wf{digest}"


def prepare_cli_import_dir() -> Path:
    temp_root = Path(tempfile.mkdtemp(prefix="myca-n8n-import-"))
    for path in sorted(WORKFLOW_DIR.glob("*.json")):
        if path.stem.upper() == "MANIFEST":
            continue
        workflow = json.loads(path.read_text(encoding="utf-8"))
        workflow["id"] = workflow.get("id") or workflow_id_for(path)
        workflow["active"] = False
        workflow.pop("tags", None)
        workflow.pop("tagIds", None)
        (temp_root / path.name).write_text(json.dumps(workflow), encoding="utf-8")
    return temp_root


def import_with_cli() -> tuple[int, int]:
    temp_root = prepare_cli_import_dir()
    container_dir = "/tmp/myca-n8n-import"
    try:
        run(["docker", "exec", N8N_CONTAINER, "rm", "-rf", container_dir])
        run(["docker", "exec", N8N_CONTAINER, "mkdir", "-p", container_dir], check=True)
        copied = run(["docker", "cp", f"{temp_root}{os.sep}.", f"{N8N_CONTAINER}:{container_dir}"])
        if copied.returncode != 0:
            log(copied.stderr.strip() or copied.stdout.strip())
            return 0, 1

        imported = 0
        failed = 0
        for path in sorted(temp_root.glob("*.json")):
            result = run(
                [
                    "docker",
                    "exec",
                    N8N_CONTAINER,
                    "n8n",
                    "import:workflow",
                    "--overwrite",
                    f"--input={container_dir}/{path.name}",
                ]
            )
            combined = f"{result.stdout}\n{result.stderr}"
            if result.returncode == 0:
                imported += 1
            elif "duplicate key value violates unique constraint" in combined:
                imported += 1
                log(f"CLI import already present or webhook conflict: {path.name}")
            else:
                failed += 1
                log(f"CLI import failed {path.name}: {(result.stderr or result.stdout).strip()[:180]}")
        return imported, failed
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def activate_key_workflows() -> tuple[int, int]:
    if not N8N_API_KEY:
        return 0, 0
    status, body = request_json("GET", "/api/v1/workflows")
    if status != 200:
        log(f"workflow list failed: HTTP {status}")
        return 0, 1
    workflows = body.get("data", body if isinstance(body, list) else [])
    keys = ("myca", "command", "event", "speech", "orchestrator", "master", "router")
    activated = 0
    failed = 0
    for workflow in workflows:
        name = str(workflow.get("name", ""))
        workflow_id = workflow.get("id")
        if not workflow_id or not any(key in name.lower() for key in keys) or workflow.get("active"):
            continue
        code, _ = request_json("POST", f"/api/v1/workflows/{workflow_id}/activate")
        if code in {200, 201}:
            activated += 1
        else:
            failed += 1
            log(f"activation failed {name}: HTTP {code}")
    return activated, failed


def activate_key_workflows_cli() -> tuple[int, int]:
    result = run(["docker", "exec", N8N_CONTAINER, "n8n", "list:workflow"])
    if result.returncode != 0:
        log(result.stderr.strip() or result.stdout.strip())
        return 0, 1
    keys = ("myca", "command", "event", "speech", "orchestrator", "master", "router")
    activated = 0
    failed = 0
    for line in result.stdout.splitlines():
        if "|" not in line:
            continue
        workflow_id, name = line.split("|", 1)
        if not any(key in name.lower() for key in keys):
            continue
        code = run(["docker", "exec", N8N_CONTAINER, "n8n", "update:workflow", f"--id={workflow_id}", "--active=true"])
        if code.returncode == 0:
            activated += 1
        else:
            failed += 1
            log(f"CLI activation failed {name}: {(code.stderr or code.stdout).strip()[:180]}")
    return activated, failed


def main() -> int:
    if not WORKFLOW_DIR.is_dir():
        raise SystemExit(f"missing workflow dir: {WORKFLOW_DIR}")
    MIRROR_DIR.mkdir(parents=True, exist_ok=True)
    log(f"local n8n url: {N8N_URL}")
    log(f"canonical workflows: {WORKFLOW_DIR}")
    start_compose()
    if not wait_for_health():
        log("n8n did not become healthy")
        return 1
    log("n8n health: ok")

    if N8N_API_KEY:
        imported, failed = import_with_api()
        log(f"API import: imported_or_present={imported} failed={failed}")
        if failed and imported == 0:
            log("API import failed completely; falling back to local container CLI import")
            imported, failed = import_with_cli()
            log(f"CLI import: imported_or_present={imported} failed={failed}")
    else:
        log("N8N_API_KEY missing; trying local container CLI import")
        imported, failed = import_with_cli()
        log(f"CLI import: imported_or_present={imported} failed={failed}")
    activated, activation_failed = activate_key_workflows()
    if activation_failed or (not N8N_API_KEY and activated == 0):
        log("API activation unavailable; falling back to local container CLI activation")
        activated, activation_failed = activate_key_workflows_cli()
    log(f"activation: activated={activated} failed={activation_failed}")
    return 1 if failed or activation_failed else 0


if __name__ == "__main__":
    sys.exit(main())
