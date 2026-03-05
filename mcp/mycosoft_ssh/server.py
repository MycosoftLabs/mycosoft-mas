#!/usr/bin/env python3
"""
Mycosoft SSH MCP Server - Secure VM access for Claude Code, Claude Cowork, Cursor.
MAR03 2026

Provides: ssh_exec, ssh_upload, ssh_download, ssh_status.
Restricted to 192.168.0.x subnet. Credentials from .credentials.local or env.
All operations audited to ~/.mycosoft-ssh-audit.log
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

try:
    import paramiko
except ImportError:
    raise ImportError("paramiko required. Run: pip install paramiko")

try:
    from fastmcp import FastMCP
except ImportError:
    raise ImportError("fastmcp required. Run: pip install fastmcp")

# Host alias -> IP (canonical 192.168.0.x)
VM_HOSTS = {
    "sandbox": "192.168.0.187",
    "mas": "192.168.0.188",
    "mindex": "192.168.0.189",
    "gpu": "192.168.0.190",
    "myca": "192.168.0.191",
}

ALLOWED_SUBNET = re.compile(r"^192\.168\.0\.\d{1,3}$")
AUDIT_LOG = Path(os.path.expanduser("~")) / ".mycosoft-ssh-audit.log"
CREDENTIALS_PATHS = [
    Path(__file__).resolve().parents[2] / ".credentials.local",
    Path(os.path.expanduser("~")) / ".mycosoft-credentials",
]


def _load_credentials() -> tuple[str, str]:
    """Load VM_SSH_USER and VM_SSH_PASSWORD from .credentials.local or env."""
    user = os.environ.get("VM_SSH_USER", "mycosoft")
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
    if password:
        return user, password
    for p in CREDENTIALS_PATHS:
        if p.exists():
            for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip()
                if k == "VM_SSH_USER":
                    user = v
                elif k in ("VM_SSH_PASSWORD", "VM_PASSWORD"):
                    password = v
                    break
        if password:
            break
    if not password:
        raise RuntimeError(
            "Credentials not found. Set VM_PASSWORD env var or add VM_SSH_PASSWORD to "
            ".credentials.local in MAS repo."
        )
    return user, password


def _resolve_host(host: str) -> str:
    """Resolve alias to IP. Validate against allowed subnet."""
    host = host.strip().lower()
    ip = VM_HOSTS.get(host, host)
    if not ALLOWED_SUBNET.match(ip):
        raise ValueError(
            f"Host '{host}' resolves to '{ip}' which is not in allowed subnet 192.168.0.x. "
            f"Allowed aliases: {list(VM_HOSTS.keys())}"
        )
    return ip


def _audit(action: str, host: str, detail: str = "") -> None:
    """Append audit entry to ~/.mycosoft-ssh-audit.log"""
    import datetime

    ts = datetime.datetime.utcnow().isoformat() + "Z"
    line = f"{ts} | {action} | {host} | {detail}\n"
    try:
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass


def _ssh_exec_impl(host: str, command: str, sudo: bool = False, timeout: int = 120) -> dict[str, Any]:
    user, password = _load_credentials()
    ip = _resolve_host(host)
    _audit("exec", ip, f"sudo={sudo} cmd={command[:80]}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(ip, username=user, password=password, timeout=30)
        cmd = f"echo {password} | sudo -S {command}" if sudo else command
        stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        code = stdout.channel.recv_exit_status()
        return {"stdout": out, "stderr": err, "exit_code": code, "host": ip}
    finally:
        client.close()


def _sftp_upload_impl(host: str, local_path: str, remote_path: str) -> dict[str, Any]:
    user, password = _load_credentials()
    ip = _resolve_host(host)
    _audit("upload", ip, f"{local_path} -> {remote_path}")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(ip, username=user, password=password, timeout=30)
        sftp = client.open_sftp()
        sftp.put(local_path, remote_path)
        sftp.close()
        return {"status": "ok", "host": ip, "remote_path": remote_path}
    except Exception as e:
        return {"status": "error", "host": ip, "error": str(e)}
    finally:
        client.close()


def _sftp_download_impl(host: str, remote_path: str, local_path: str | None = None) -> dict[str, Any]:
    user, password = _load_credentials()
    ip = _resolve_host(host)
    _audit("download", ip, f"{remote_path} -> {local_path or '(stdout)'}")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(ip, username=user, password=password, timeout=30)
        sftp = client.open_sftp()
        if local_path:
            sftp.get(remote_path, local_path)
            sftp.close()
            return {"status": "ok", "host": ip, "local_path": local_path}
        with sftp.file(remote_path, "r") as f:
            content = f.read().decode("utf-8", errors="replace")
        sftp.close()
        return {"status": "ok", "host": ip, "content": content, "remote_path": remote_path}
    except Exception as e:
        return {"status": "error", "host": ip, "error": str(e)}
    finally:
        client.close()


def _status_impl() -> dict[str, Any]:
    """Check connectivity to all VMs."""
    user, password = _load_credentials()
    results = {}
    for alias, ip in VM_HOSTS.items():
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(ip, username=user, password=password, timeout=5)
            client.close()
            results[alias] = {"ip": ip, "status": "ok"}
        except Exception as e:
            results[alias] = {"ip": ip, "status": "error", "error": str(e)}
    return {"hosts": results}


# --- FastMCP server ---
mcp = FastMCP(
    "Mycosoft SSH",
    instructions="Secure SSH access to Mycosoft VMs (sandbox, mas, mindex, gpu, myca). "
    "Use for remote command execution, file upload/download. Restricted to 192.168.0.x.",
    version="1.0.0",
)


@mcp.tool
def ssh_exec(host: str, command: str, sudo: bool = False, timeout: int = 120) -> dict[str, Any]:
    """
    Run a command on a Mycosoft VM via SSH.
    host: sandbox|mas|mindex|gpu|myca or 192.168.0.x IP
    command: Shell command to run
    sudo: If True, run with sudo (uses VM password)
    timeout: Command timeout in seconds (default 120)
    """
    return _ssh_exec_impl(host, command, sudo=sudo, timeout=timeout)


@mcp.tool
def ssh_upload(host: str, local_path: str, remote_path: str) -> dict[str, Any]:
    """
    Upload a file to a Mycosoft VM via SFTP.
    host: sandbox|mas|mindex|gpu|myca or 192.168.0.x IP
    local_path: Path on your machine
    remote_path: Path on the VM
    """
    return _sftp_upload_impl(host, local_path, remote_path)


@mcp.tool
def ssh_download(host: str, remote_path: str, local_path: str | None = None) -> dict[str, Any]:
    """
    Download a file from a Mycosoft VM via SFTP.
    host: sandbox|mas|mindex|gpu|myca or 192.168.0.x IP
    remote_path: Path on the VM
    local_path: Optional path to save; if omitted, returns content in response
    """
    return _sftp_download_impl(host, remote_path, local_path)


@mcp.tool
def ssh_status() -> dict[str, Any]:
    """Check SSH connectivity to all 5 Mycosoft VMs (sandbox, mas, mindex, gpu, myca)."""
    return _status_impl()


if __name__ == "__main__":
    mcp.run()
