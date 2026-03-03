"""
MCP SSH Server — gives Claude Code SSH access to all Mycosoft VMs.

Runs on your desktop (Windows/Mac/Linux) as an MCP stdio server.
Provides tools to execute commands, upload/download files, and check
connectivity to any VM on the LAN.

Tools:
  - ssh_exec:     Run a command on any VM
  - ssh_upload:   Upload a file to a VM
  - ssh_download: Download a file from a VM
  - ssh_status:   Check connectivity to all VMs

Security:
  - Credentials loaded from environment or ~/.mycosoft-ssh-keys/
  - Only whitelisted hosts (192.168.0.x) allowed
  - All commands logged to audit file
  - No arbitrary host connections (LAN only)

Usage in .mcp.json:
  {
    "mycosoft-ssh": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "mycosoft_mas.mcp.ssh_server"],
      "env": {
        "SSH_KEY_PATH": "~/.ssh/id_ed25519",
        "SSH_DEFAULT_USER": "mycosoft"
      }
    }
  }

Run standalone:
  python -m mycosoft_mas.mcp.ssh_server
"""

import asyncio
import json
import logging
import os
import socket
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("SSHMCPServer")

# ---------------------------------------------------------------------------
# VM inventory — only these hosts are allowed
# ---------------------------------------------------------------------------

VM_INVENTORY = {
    "sandbox": {"ip": "192.168.0.187", "name": "Sandbox", "user": "mycosoft"},
    "mas": {"ip": "192.168.0.188", "name": "MAS Orchestrator", "user": "mycosoft"},
    "mindex": {"ip": "192.168.0.189", "name": "MINDEX Database", "user": "mycosoft"},
    "gpu": {"ip": "192.168.0.190", "name": "GPU Node", "user": "mycosoft"},
    "myca": {"ip": "192.168.0.191", "name": "MYCA Workspace", "user": "mycosoft"},
}

# Also allow raw IPs in the 192.168.0.x range
ALLOWED_SUBNET = "192.168.0."


@dataclass
class MCPToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any]


class SSHMCPServer:
    """MCP Server providing SSH access to Mycosoft VMs."""

    def __init__(self):
        self._default_user = os.getenv("SSH_DEFAULT_USER", "mycosoft")
        self._ssh_key_path = os.getenv("SSH_KEY_PATH", "")
        self._ssh_password = os.getenv("SSH_PASSWORD", os.getenv("VM_PASSWORD", ""))
        self._timeout = int(os.getenv("SSH_TIMEOUT", "30"))
        self._audit_log_path = os.getenv(
            "SSH_AUDIT_LOG",
            str(Path.home() / ".mycosoft-ssh-audit.log"),
        )
        self._paramiko = None
        self._tools = self._define_tools()

    async def initialize(self):
        """Lazy import paramiko."""
        try:
            import paramiko
            self._paramiko = paramiko
            logger.info("SSH MCP Server initialized (paramiko %s)", paramiko.__version__)
        except ImportError:
            logger.error(
                "paramiko not installed. Run: pip install paramiko"
            )
            raise

    def _define_tools(self) -> List[MCPToolDefinition]:
        return [
            MCPToolDefinition(
                name="ssh_exec",
                description=(
                    "Execute a command on a Mycosoft VM via SSH. "
                    "Use host aliases (sandbox, mas, mindex, gpu, myca) or IPs (192.168.0.x)."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "host": {
                            "type": "string",
                            "description": "VM alias (sandbox, mas, mindex, gpu, myca) or IP (192.168.0.x)",
                        },
                        "command": {
                            "type": "string",
                            "description": "Shell command to execute",
                        },
                        "user": {
                            "type": "string",
                            "description": f"SSH username (default: {os.getenv('SSH_DEFAULT_USER', 'mycosoft')})",
                        },
                        "sudo": {
                            "type": "boolean",
                            "description": "Run with sudo (default: false)",
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Command timeout in seconds (default: 30)",
                        },
                    },
                    "required": ["host", "command"],
                },
            ),
            MCPToolDefinition(
                name="ssh_upload",
                description="Upload a file to a Mycosoft VM via SFTP.",
                parameters={
                    "type": "object",
                    "properties": {
                        "host": {
                            "type": "string",
                            "description": "VM alias or IP",
                        },
                        "local_path": {
                            "type": "string",
                            "description": "Local file path to upload",
                        },
                        "remote_path": {
                            "type": "string",
                            "description": "Destination path on the VM",
                        },
                        "user": {
                            "type": "string",
                            "description": "SSH username",
                        },
                    },
                    "required": ["host", "local_path", "remote_path"],
                },
            ),
            MCPToolDefinition(
                name="ssh_download",
                description="Download a file from a Mycosoft VM via SFTP.",
                parameters={
                    "type": "object",
                    "properties": {
                        "host": {
                            "type": "string",
                            "description": "VM alias or IP",
                        },
                        "remote_path": {
                            "type": "string",
                            "description": "File path on the VM to download",
                        },
                        "local_path": {
                            "type": "string",
                            "description": "Local destination path (default: temp file)",
                        },
                        "user": {
                            "type": "string",
                            "description": "SSH username",
                        },
                    },
                    "required": ["host", "remote_path"],
                },
            ),
            MCPToolDefinition(
                name="ssh_status",
                description="Check SSH connectivity to all Mycosoft VMs.",
                parameters={
                    "type": "object",
                    "properties": {
                        "host": {
                            "type": "string",
                            "description": "Specific VM to check (default: check all)",
                        },
                    },
                },
            ),
        ]

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "inputSchema": t.parameters,
            }
            for t in self._tools
        ]

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        handlers = {
            "ssh_exec": self._tool_ssh_exec,
            "ssh_upload": self._tool_ssh_upload,
            "ssh_download": self._tool_ssh_download,
            "ssh_status": self._tool_ssh_status,
        }
        handler = handlers.get(name)
        if not handler:
            return {"error": f"Unknown tool: {name}"}
        try:
            return await handler(arguments)
        except Exception as exc:
            logger.exception("Tool %s failed", name)
            return {"error": str(exc)}

    # ------------------------------------------------------------------
    # Host resolution & validation
    # ------------------------------------------------------------------

    def _resolve_host(self, host_input: str) -> tuple[str, str]:
        """Resolve alias to (ip, user). Raises ValueError if not allowed."""
        host_lower = host_input.lower().strip()

        # Check aliases
        if host_lower in VM_INVENTORY:
            vm = VM_INVENTORY[host_lower]
            return vm["ip"], vm.get("user", self._default_user)

        # Check raw IP
        if host_lower.startswith(ALLOWED_SUBNET):
            return host_lower, self._default_user

        raise ValueError(
            f"Host '{host_input}' not allowed. "
            f"Use aliases ({', '.join(VM_INVENTORY.keys())}) or IPs in {ALLOWED_SUBNET}0/24"
        )

    # ------------------------------------------------------------------
    # SSH connection helper
    # ------------------------------------------------------------------

    def _connect(self, ip: str, user: str) -> "paramiko.SSHClient":
        """Create an SSH connection."""
        ssh = self._paramiko.SSHClient()
        ssh.set_missing_host_key_policy(self._paramiko.AutoAddPolicy())

        connect_kwargs = {
            "hostname": ip,
            "username": user,
            "timeout": self._timeout,
        }

        # Try key-based auth first, then password
        key_path = self._ssh_key_path
        if not key_path:
            # Try common key locations
            for candidate in [
                Path.home() / ".ssh" / "id_ed25519",
                Path.home() / ".ssh" / "id_rsa",
                Path.home() / ".ssh" / "mycosoft_key",
            ]:
                if candidate.exists():
                    key_path = str(candidate)
                    break

        if key_path and Path(key_path).exists():
            connect_kwargs["key_filename"] = key_path
        elif self._ssh_password:
            connect_kwargs["password"] = self._ssh_password
        else:
            # Let paramiko try the SSH agent
            connect_kwargs["allow_agent"] = True

        ssh.connect(**connect_kwargs)
        return ssh

    def _audit(self, action: str, host: str, detail: str):
        """Write to audit log."""
        try:
            ts = datetime.now(timezone.utc).isoformat()
            entry = f"{ts} | {action} | {host} | {detail}\n"
            with open(self._audit_log_path, "a") as f:
                f.write(entry)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------

    async def _tool_ssh_exec(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a command on a VM."""
        ip, default_user = self._resolve_host(args["host"])
        user = args.get("user", default_user)
        command = args["command"]
        use_sudo = args.get("sudo", False)
        timeout = args.get("timeout", self._timeout)

        self._audit("exec", ip, command[:200])

        if use_sudo and self._ssh_password:
            command = f"echo '{self._ssh_password}' | sudo -S bash -c '{command}'"
        elif use_sudo:
            command = f"sudo {command}"

        ssh = self._connect(ip, user)
        try:
            _, stdout, stderr = ssh.exec_command(command, timeout=timeout)
            exit_code = stdout.channel.recv_exit_status()
            out = stdout.read().decode(errors="replace")
            err = stderr.read().decode(errors="replace")

            # Truncate very long output
            max_len = 50000
            if len(out) > max_len:
                out = out[:max_len] + f"\n... (truncated, {len(out)} total chars)"
            if len(err) > max_len:
                err = err[:max_len] + f"\n... (truncated)"

            return {
                "host": args["host"],
                "ip": ip,
                "exit_code": exit_code,
                "stdout": out,
                "stderr": err,
            }
        finally:
            ssh.close()

    async def _tool_ssh_upload(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Upload a file to a VM."""
        ip, default_user = self._resolve_host(args["host"])
        user = args.get("user", default_user)
        local_path = args["local_path"]
        remote_path = args["remote_path"]

        if not Path(local_path).exists():
            return {"error": f"Local file not found: {local_path}"}

        self._audit("upload", ip, f"{local_path} -> {remote_path}")

        ssh = self._connect(ip, user)
        try:
            sftp = ssh.open_sftp()
            sftp.put(local_path, remote_path)
            stat = sftp.stat(remote_path)
            sftp.close()
            return {
                "status": "uploaded",
                "host": args["host"],
                "remote_path": remote_path,
                "size_bytes": stat.st_size,
            }
        finally:
            ssh.close()

    async def _tool_ssh_download(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Download a file from a VM."""
        ip, default_user = self._resolve_host(args["host"])
        user = args.get("user", default_user)
        remote_path = args["remote_path"]
        local_path = args.get("local_path", "")

        if not local_path:
            # Create temp file
            suffix = Path(remote_path).suffix or ".txt"
            fd, local_path = tempfile.mkstemp(suffix=suffix, prefix="myca_ssh_")
            os.close(fd)

        self._audit("download", ip, f"{remote_path} -> {local_path}")

        ssh = self._connect(ip, user)
        try:
            sftp = ssh.open_sftp()
            sftp.get(remote_path, local_path)
            sftp.close()
            size = Path(local_path).stat().st_size
            return {
                "status": "downloaded",
                "host": args["host"],
                "remote_path": remote_path,
                "local_path": local_path,
                "size_bytes": size,
            }
        finally:
            ssh.close()

    async def _tool_ssh_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Check SSH connectivity to VMs."""
        target = args.get("host", "")
        results = {}

        hosts_to_check = {}
        if target:
            try:
                ip, user = self._resolve_host(target)
                hosts_to_check[target] = {"ip": ip, "user": user}
            except ValueError as e:
                return {"error": str(e)}
        else:
            for alias, info in VM_INVENTORY.items():
                hosts_to_check[alias] = {"ip": info["ip"], "user": info.get("user", self._default_user)}

        for alias, info in hosts_to_check.items():
            ip = info["ip"]
            # Quick TCP check first
            try:
                sock = socket.create_connection((ip, 22), timeout=5)
                sock.close()
                port_open = True
            except (socket.timeout, ConnectionRefusedError, OSError):
                port_open = False

            if port_open:
                # Try actual SSH auth
                try:
                    ssh = self._connect(ip, info["user"])
                    ssh.close()
                    results[alias] = {
                        "ip": ip,
                        "status": "connected",
                        "ssh_auth": "ok",
                    }
                except Exception as e:
                    results[alias] = {
                        "ip": ip,
                        "status": "port_open",
                        "ssh_auth": f"failed: {e}",
                    }
            else:
                results[alias] = {
                    "ip": ip,
                    "status": "unreachable",
                }

        return {"hosts": results}

    async def cleanup(self):
        pass


# ---------------------------------------------------------------------------
# MCP Protocol Handler (JSON-RPC over stdio)
# ---------------------------------------------------------------------------

class MCPProtocolHandler:
    def __init__(self, server: SSHMCPServer):
        self._server = server

    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        method = message.get("method", "")
        msg_id = message.get("id")
        params = message.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "mycosoft-ssh",
                        "version": "1.0.0",
                    },
                    "capabilities": {"tools": {}},
                },
            }

        elif method == "notifications/initialized":
            return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": self._server.get_tools()},
            }

        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            result = await self._server.call_tool(tool_name, arguments)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {"type": "text", "text": json.dumps(result, indent=2)}
                    ]
                },
            }

        else:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

_mcp_server: Optional[SSHMCPServer] = None


async def get_mcp_server() -> SSHMCPServer:
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = SSHMCPServer()
        await _mcp_server.initialize()
    return _mcp_server


async def run_stdio_server():
    """Run the SSH MCP server over stdio."""
    server = await get_mcp_server()
    handler = MCPProtocolHandler(server)

    logger.info("SSH MCP Server started on stdio")

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            message = json.loads(line)
            response = await handler.handle_message(message)

            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()

        except json.JSONDecodeError:
            continue
        except KeyboardInterrupt:
            break

    await server.cleanup()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stderr,  # Log to stderr, stdout is for MCP protocol
    )
    asyncio.run(run_stdio_server())
