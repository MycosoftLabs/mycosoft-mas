"""
Exec Tool -- execute shell commands in sandbox containers.

Routes through GatewayControlPlane -> SandboxManager -> Node daemon
for safe, isolated command execution.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from mycosoft_mas.gateway.control_plane import GatewayControlPlane
    from mycosoft_mas.sandbox.container_manager import SandboxManager

logger = logging.getLogger(__name__)


@dataclass
class ExecResult:
    exit_code: int
    stdout: str
    stderr: str
    truncated: bool = False
    pid: Optional[int] = None
    duration_ms: int = 0


@dataclass
class ProcessInfo:
    pid: int
    sandbox_id: str


class ExecTool:
    """Execute shell commands in ephemeral sandbox containers."""

    def __init__(
        self,
        sandbox_manager: Optional["SandboxManager"] = None,
        gateway: Optional["GatewayControlPlane"] = None,
    ):
        self._sandbox_manager = sandbox_manager
        self._gateway = gateway

    async def run_command(
        self,
        command: str,
        cwd: str = "/workspace",
        timeout: int = 60,
        session_id: Optional[str] = None,
    ) -> ExecResult:
        """Run a command in a sandbox and return the result."""
        if self._gateway:
            result = await self._gateway.intercept_tool_call(
                "exec",
                {"command": command, "cwd": cwd},
                session_id=session_id,
            )
            output = result.output or {}
            if isinstance(output, dict):
                return ExecResult(
                    exit_code=output.get("exit_code", -1),
                    stdout=output.get("stdout", ""),
                    stderr=output.get("stderr", ""),
                    truncated=result.truncated,
                    pid=output.get("pid"),
                    duration_ms=result.duration_ms,
                )
            return ExecResult(
                exit_code=-1,
                stdout=str(output),
                stderr=result.error or "",
                truncated=result.truncated,
                duration_ms=result.duration_ms,
            )

        return ExecResult(
            exit_code=-1, stdout="", stderr="Gateway not available",
        )

    async def run_background(
        self,
        command: str,
        session_id: Optional[str] = None,
    ) -> ProcessInfo:
        """Start a background process and return its PID."""
        if self._gateway:
            result = await self._gateway.intercept_tool_call(
                "exec",
                {"command": f"nohup {command} &"},
                session_id=session_id,
            )
            output = result.output or {}
            return ProcessInfo(
                pid=output.get("pid", -1) if isinstance(output, dict) else -1,
                sandbox_id=result.sandbox_id or "",
            )
        raise RuntimeError("Gateway not available")

    async def send_input(
        self, sandbox_id: str, pid: int, data: str,
    ):
        """Send input to an interactive process."""
        if self._gateway:
            await self._gateway.intercept_tool_call(
                "exec_input",
                {"pid": pid, "data": data},
                session_id=sandbox_id,
            )

    async def kill_process(self, sandbox_id: str, pid: int):
        """Kill a running process."""
        if self._gateway:
            await self._gateway.intercept_tool_call(
                "exec_kill",
                {"pid": pid},
                session_id=sandbox_id,
            )
