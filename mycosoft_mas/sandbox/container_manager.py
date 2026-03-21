"""
Sandbox Container Manager -- spawn/destroy ephemeral Docker sandboxes.

Pattern based on gpu_node_client.py: SSH + Docker commands for both
local and remote Docker hosts.
"""

import asyncio
import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SandboxInfo:
    sandbox_id: str
    container_name: str
    ws_port: int = 9000
    token: str = ""
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    status: str = "running"


class SandboxManager:
    """Manages ephemeral Docker sandbox containers for tool execution."""

    SANDBOX_IMAGE = os.getenv("MYCA_SANDBOX_IMAGE", "myca-sandbox:latest")
    GATEWAY_WS_HOST = os.getenv("MYCA_GATEWAY_WS_HOST", "192.168.0.191")
    GATEWAY_WS_PORT = int(os.getenv("MYCA_GATEWAY_WS_PORT", "9000"))
    MAX_IDLE_MINUTES = int(os.getenv("SANDBOX_MAX_IDLE_MIN", "30"))

    def __init__(
        self,
        docker_host: str = "local",
        ssh_host: Optional[str] = None,
        ssh_user: str = "mycosoft",
    ):
        self._docker_host = docker_host
        self._ssh_host = ssh_host or os.getenv("MYCA_VM_IP", "192.168.0.191")
        self._ssh_user = ssh_user
        self._sandboxes: Dict[str, SandboxInfo] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

    async def _docker_cmd(self, cmd: str, timeout: int = 30) -> tuple[int, str, str]:
        if self._docker_host == "local":
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return (
                proc.returncode or 0,
                stdout.decode(errors="replace"),
                stderr.decode(errors="replace"),
            )
        else:
            proc = await asyncio.create_subprocess_exec(
                "ssh",
                f"{self._ssh_user}@{self._ssh_host}",
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return (
                proc.returncode or 0,
                stdout.decode(errors="replace"),
                stderr.decode(errors="replace"),
            )

    async def spawn_sandbox(
        self,
        session_id: str,
        image: Optional[str] = None,
    ) -> SandboxInfo:
        image = image or self.SANDBOX_IMAGE
        token = secrets.token_urlsafe(32)
        container_name = f"sandbox-{session_id[:12]}"

        run_cmd = (
            f"docker run -d --name {container_name} "
            f"--cap-drop=ALL "
            f"--read-only "
            f"--security-opt=no-new-privileges:true "
            f"--tmpfs /workspace:rw,size=512m "
            f"--tmpfs /tmp:rw,size=256m "
            f"--memory=512m --cpus=0.5 "
            f"--network=sandbox-net "
            f"-e GATEWAY_URL=ws://{self.GATEWAY_WS_HOST}:{self.GATEWAY_WS_PORT}/ws/sandbox/{session_id} "
            f"-e SANDBOX_TOKEN={token} "
            f"-e SANDBOX_ID={session_id} "
            f"{image}"
        )

        code, out, err = await self._docker_cmd(run_cmd, timeout=30)
        if code != 0:
            raise RuntimeError(f"Failed to spawn sandbox: {err}")

        info = SandboxInfo(
            sandbox_id=session_id,
            container_name=container_name,
            ws_port=self.GATEWAY_WS_PORT,
            token=token,
        )
        self._sandboxes[session_id] = info
        logger.info("Spawned sandbox %s (container %s)", session_id, container_name)

        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._auto_destroy_loop())

        return info

    async def get_or_spawn(self, session_id: str) -> SandboxInfo:
        existing = self._sandboxes.get(session_id)
        if existing and existing.status == "running":
            existing.last_activity = time.time()
            return existing
        return await self.spawn_sandbox(session_id)

    async def destroy_sandbox(self, sandbox_id: str):
        info = self._sandboxes.pop(sandbox_id, None)
        if info:
            await self._docker_cmd(
                f"docker stop {info.container_name} && docker rm {info.container_name}",
                timeout=15,
            )
            logger.info("Destroyed sandbox %s", sandbox_id)

    async def list_sandboxes(self) -> List[SandboxInfo]:
        return list(self._sandboxes.values())

    async def health_check(self, sandbox_id: str) -> Dict[str, Any]:
        info = self._sandboxes.get(sandbox_id)
        if not info:
            return {"status": "not_found"}
        code, out, _ = await self._docker_cmd(
            f"docker inspect -f '{{{{.State.Running}}}}' {info.container_name}",
            timeout=5,
        )
        running = "true" in out.lower()
        return {"status": "running" if running else "stopped", "sandbox_id": sandbox_id}

    async def _auto_destroy_loop(self):
        while self._sandboxes:
            await asyncio.sleep(60)
            now = time.time()
            idle_limit = self.MAX_IDLE_MINUTES * 60
            expired = [
                sid
                for sid, info in self._sandboxes.items()
                if (now - info.last_activity) > idle_limit
            ]
            for sid in expired:
                logger.info("Auto-destroying idle sandbox %s", sid)
                await self.destroy_sandbox(sid)
