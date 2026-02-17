"""
GPU Node Client for Mycosoft MAS

Provides programmatic access to the mycosoft-gpu01 node (192.168.0.190)
for GPU workload management, container deployment, and status monitoring.

Usage:
    from mycosoft_mas.integrations.gpu_node_client import GPUNodeClient
    
    client = GPUNodeClient()
    status = await client.get_gpu_status()
    await client.deploy_container("moshi-voice", "mycosoft/moshi-voice:latest", 8998)
"""

import asyncio
import logging
import os
import subprocess
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class GPUInfo:
    """GPU status information."""
    name: str
    memory_used_mb: int
    memory_total_mb: int
    utilization_percent: int
    temperature_c: int


@dataclass
class ContainerInfo:
    """Docker container information."""
    name: str
    image: str
    status: str
    ports: str
    created: str


class GPUNodeClient:
    """Client for interacting with mycosoft-gpu01 GPU compute node."""
    
    # Node configuration
    HOSTNAME = os.getenv("GPU_NODE_HOSTNAME", "gpu01")
    IP = os.getenv("GPU_NODE_IP", "192.168.0.190")
    USER = os.getenv("GPU_NODE_USER", "mycosoft")
    
    # Known GPU services
    SERVICES = {
        "moshi-voice": {
            "image": "mycosoft/moshi-voice:latest",
            "port": 8998,
            "gpu": True,
            "health_endpoint": "/health"
        },
        "earth2-inference": {
            "image": "mycosoft/earth2-inference:latest", 
            "port": 8220,
            "gpu": True,
            "health_endpoint": "/health"
        },
        "personaplex-bridge": {
            "image": "mycosoft/personaplex-bridge:latest",
            "port": 8999,
            "gpu": False,
            "health_endpoint": "/health"
        }
    }
    
    def __init__(self, ssh_host: Optional[str] = None):
        """Initialize GPU node client.
        
        Args:
            ssh_host: SSH host alias. If omitted, uses env GPU_NODE_SSH_HOST or HOSTNAME.
        """
        self.ssh_host = ssh_host or os.getenv("GPU_NODE_SSH_HOST", self.HOSTNAME)
    
    def _run_ssh(self, command: str, timeout: int = 30) -> tuple[int, str, str]:
        """Execute SSH command on GPU node.
        
        Args:
            command: Command to execute
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        try:
            result = subprocess.run(
                ["ssh", self.ssh_host, command],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except Exception as e:
            return -1, "", str(e)
    
    async def _run_ssh_async(self, command: str, timeout: int = 30) -> tuple[int, str, str]:
        """Execute SSH command asynchronously.
        
        Args:
            command: Command to execute
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                "ssh", self.ssh_host, command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), 
                timeout=timeout
            )
            return proc.returncode, stdout.decode(), stderr.decode()
        except asyncio.TimeoutError:
            return -1, "", "Command timed out"
        except Exception as e:
            return -1, "", str(e)
    
    async def is_reachable(self) -> bool:
        """Check if GPU node is reachable via SSH.
        
        Returns:
            True if node responds to SSH, False otherwise
        """
        code, _, _ = await self._run_ssh_async("echo ok", timeout=5)
        return code == 0
    
    async def get_gpu_status(self) -> Optional[GPUInfo]:
        """Get GPU status information.
        
        Returns:
            GPUInfo dataclass or None if unavailable
        """
        cmd = "nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu --format=csv,noheader,nounits"
        code, stdout, stderr = await self._run_ssh_async(cmd)
        
        if code != 0:
            logger.error(f"Failed to get GPU status: {stderr}")
            return None
        
        try:
            parts = stdout.strip().split(", ")
            return GPUInfo(
                name=parts[0],
                memory_used_mb=int(parts[1]),
                memory_total_mb=int(parts[2]),
                utilization_percent=int(parts[3]),
                temperature_c=int(parts[4])
            )
        except (IndexError, ValueError) as e:
            logger.error(f"Failed to parse GPU status: {e}")
            return None
    
    async def list_containers(self) -> List[ContainerInfo]:
        """List all Docker containers on GPU node.
        
        Returns:
            List of ContainerInfo dataclasses
        """
        cmd = 'docker ps -a --format "{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}|{{.CreatedAt}}"'
        code, stdout, stderr = await self._run_ssh_async(cmd)
        
        if code != 0:
            logger.error(f"Failed to list containers: {stderr}")
            return []
        
        containers = []
        for line in stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|")
            if len(parts) >= 5:
                containers.append(ContainerInfo(
                    name=parts[0],
                    image=parts[1],
                    status=parts[2],
                    ports=parts[3],
                    created=parts[4]
                ))
        
        return containers
    
    async def deploy_container(
        self,
        name: str,
        image: str,
        port: int,
        gpu: bool = True,
        env_vars: Optional[Dict[str, str]] = None,
        volumes: Optional[Dict[str, str]] = None,
        restart_policy: str = "unless-stopped"
    ) -> bool:
        """Deploy a Docker container on the GPU node.
        
        Args:
            name: Container name
            image: Docker image
            port: Host port to expose
            gpu: Enable GPU access
            env_vars: Environment variables
            volumes: Volume mounts (host_path: container_path)
            restart_policy: Docker restart policy
            
        Returns:
            True if deployment succeeded
        """
        # Stop existing container if running
        await self.stop_container(name)
        
        # Build docker run command
        cmd_parts = ["docker", "run", "-d", "--name", name]
        
        if gpu:
            cmd_parts.extend(["--gpus", "all"])
        
        cmd_parts.extend(["-p", f"{port}:{port}"])
        cmd_parts.extend(["--restart", restart_policy])
        
        if env_vars:
            for key, value in env_vars.items():
                cmd_parts.extend(["-e", f"{key}={value}"])
        
        if volumes:
            for host_path, container_path in volumes.items():
                cmd_parts.extend(["-v", f"{host_path}:{container_path}"])
        
        cmd_parts.append(image)
        
        cmd = " ".join(cmd_parts)
        code, stdout, stderr = await self._run_ssh_async(cmd, timeout=120)
        
        if code != 0:
            logger.error(f"Failed to deploy {name}: {stderr}")
            return False
        
        logger.info(f"Deployed container {name} on GPU node")
        return True
    
    async def stop_container(self, name: str) -> bool:
        """Stop and remove a container.
        
        Args:
            name: Container name
            
        Returns:
            True if stopped/removed (or didn't exist)
        """
        cmd = f"docker stop {name} 2>/dev/null; docker rm {name} 2>/dev/null; echo done"
        code, _, _ = await self._run_ssh_async(cmd)
        return True
    
    async def get_container_logs(self, name: str, tail: int = 100) -> str:
        """Get container logs.
        
        Args:
            name: Container name
            tail: Number of lines to return
            
        Returns:
            Log output string
        """
        cmd = f"docker logs {name} --tail {tail} 2>&1"
        code, stdout, stderr = await self._run_ssh_async(cmd, timeout=10)
        return stdout if code == 0 else stderr
    
    async def is_container_running(self, name: str) -> bool:
        """Check if a container is running.
        
        Args:
            name: Container name
            
        Returns:
            True if container is running
        """
        cmd = f'docker ps --filter "name={name}" --format "{{{{.Names}}}}"'
        code, stdout, _ = await self._run_ssh_async(cmd)
        return name in stdout
    
    async def deploy_service(self, service_name: str) -> bool:
        """Deploy a known GPU service.
        
        Args:
            service_name: One of: moshi-voice, earth2-inference, personaplex-bridge
            
        Returns:
            True if deployment succeeded
        """
        if service_name not in self.SERVICES:
            logger.error(f"Unknown service: {service_name}")
            return False
        
        config = self.SERVICES[service_name]
        return await self.deploy_container(
            name=service_name,
            image=config["image"],
            port=config["port"],
            gpu=config["gpu"]
        )

    async def deploy_personaplex_bridge_remote(
        self,
        inference_host: str,
        inference_port: int = 8998,
        mas_orchestrator_url: str = "http://192.168.0.188:8001",
    ) -> bool:
        """Deploy bridge on gpu01 pointing to remote inference host.

        This is the split architecture:
        - Logic/interface bridge on gpu01 (1080 Ti host)
        - Heavy Moshi inference on remote host (e.g. RTX 5090 machine)
        """
        return await self.deploy_container(
            name="personaplex-bridge",
            image=self.SERVICES["personaplex-bridge"]["image"],
            port=8999,
            gpu=False,
            env_vars={
                "MOSHI_HOST": inference_host,
                "MOSHI_PORT": str(inference_port),
                "MAS_ORCHESTRATOR_URL": mas_orchestrator_url,
                "MYCA_BRAIN_ENABLED": "true",
            },
        )
    
    async def get_service_health(self, service_name: str) -> Dict[str, Any]:
        """Check health of a deployed service.
        
        Args:
            service_name: Service name
            
        Returns:
            Health status dict
        """
        if service_name not in self.SERVICES:
            return {"status": "unknown", "error": "Unknown service"}
        
        config = self.SERVICES[service_name]
        port = config["port"]
        endpoint = config.get("health_endpoint", "/health")
        
        cmd = f"curl -s --connect-timeout 5 http://localhost:{port}{endpoint}"
        code, stdout, stderr = await self._run_ssh_async(cmd, timeout=10)
        
        if code != 0:
            return {"status": "unhealthy", "error": stderr}
        
        try:
            import json
            return {"status": "healthy", "response": json.loads(stdout)}
        except:
            return {"status": "healthy", "response": stdout}
    
    async def get_system_info(self) -> Dict[str, Any]:
        """Get full system information from GPU node.
        
        Returns:
            Dict with system details
        """
        info = {}
        
        # GPU info
        gpu = await self.get_gpu_status()
        if gpu:
            info["gpu"] = {
                "name": gpu.name,
                "memory_used_mb": gpu.memory_used_mb,
                "memory_total_mb": gpu.memory_total_mb,
                "utilization_percent": gpu.utilization_percent,
                "temperature_c": gpu.temperature_c
            }
        
        # System info
        code, stdout, _ = await self._run_ssh_async("hostname; uptime -p; free -m | grep Mem")
        if code == 0:
            lines = stdout.strip().split("\n")
            info["hostname"] = lines[0] if len(lines) > 0 else "unknown"
            info["uptime"] = lines[1] if len(lines) > 1 else "unknown"
            if len(lines) > 2:
                mem_parts = lines[2].split()
                if len(mem_parts) >= 3:
                    info["memory_total_mb"] = int(mem_parts[1])
                    info["memory_used_mb"] = int(mem_parts[2])
        
        # Docker info
        code, stdout, _ = await self._run_ssh_async("docker ps --format '{{.Names}}' | wc -l")
        info["running_containers"] = int(stdout.strip()) if code == 0 else 0
        
        # Containers
        info["containers"] = [
            {"name": c.name, "status": c.status, "image": c.image}
            for c in await self.list_containers()
        ]
        
        return info
    
    async def transfer_image(self, local_image: str) -> bool:
        """Transfer a Docker image from local to GPU node.
        
        Args:
            local_image: Local Docker image name:tag
            
        Returns:
            True if transfer succeeded
        """
        # This uses docker save | ssh docker load
        cmd = f"docker save {local_image} | ssh {self.ssh_host} 'docker load'"
        
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes for large images
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to transfer image: {e}")
            return False


# Singleton instance
_client: Optional[GPUNodeClient] = None


def get_gpu_client() -> GPUNodeClient:
    """Get or create GPU node client singleton."""
    global _client
    if _client is None:
        _client = GPUNodeClient()
    return _client


# Convenience functions
async def check_gpu_node() -> Dict[str, Any]:
    """Quick check of GPU node status."""
    client = get_gpu_client()
    
    if not await client.is_reachable():
        return {"status": "offline", "reachable": False}
    
    return {
        "status": "online",
        "reachable": True,
        **await client.get_system_info()
    }


async def deploy_gpu_service(service_name: str) -> Dict[str, Any]:
    """Deploy a known GPU service."""
    client = get_gpu_client()
    
    if not await client.is_reachable():
        return {"success": False, "error": "GPU node not reachable"}
    
    success = await client.deploy_service(service_name)
    
    if success:
        # Wait a moment for container to start
        await asyncio.sleep(3)
        health = await client.get_service_health(service_name)
        return {"success": True, "health": health}
    
    return {"success": False, "error": "Deployment failed"}


async def deploy_personaplex_split(
    inference_host: str,
    inference_port: int = 8998,
    mas_orchestrator_url: str = "http://192.168.0.188:8001",
) -> Dict[str, Any]:
    """Deploy split PersonaPlex with bridge on gpu01 and remote inference."""
    client = get_gpu_client()

    if not await client.is_reachable():
        return {"success": False, "error": "GPU logic node not reachable"}

    ok = await client.deploy_personaplex_bridge_remote(
        inference_host=inference_host,
        inference_port=inference_port,
        mas_orchestrator_url=mas_orchestrator_url,
    )
    if not ok:
        return {"success": False, "error": "Failed to deploy bridge on gpu01"}

    await asyncio.sleep(3)
    bridge_health = await client.get_service_health("personaplex-bridge")
    return {
        "success": True,
        "architecture": "split",
        "logic_host": client.IP,
        "bridge_endpoint": f"http://{client.IP}:8999",
        "inference_endpoint": f"ws://{inference_host}:{inference_port}",
        "bridge_health": bridge_health,
    }


if __name__ == "__main__":
    # CLI for quick checks
    import sys
    
    async def main():
        client = GPUNodeClient()
        
        if len(sys.argv) < 2:
            print("Usage: python gpu_node_client.py <command>")
            print("Commands: status, containers, gpu, deploy <service>, stop <container>")
            return
        
        cmd = sys.argv[1]
        
        if cmd == "status":
            info = await client.get_system_info()
            print(f"Hostname: {info.get('hostname')}")
            print(f"Uptime: {info.get('uptime')}")
            if "gpu" in info:
                gpu = info["gpu"]
                print(f"GPU: {gpu['name']}")
                print(f"  Memory: {gpu['memory_used_mb']}/{gpu['memory_total_mb']} MB")
                print(f"  Utilization: {gpu['utilization_percent']}%")
                print(f"  Temperature: {gpu['temperature_c']}°C")
            print(f"Containers: {info.get('running_containers', 0)} running")
        
        elif cmd == "containers":
            containers = await client.list_containers()
            for c in containers:
                print(f"{c.name}: {c.status} ({c.image})")
        
        elif cmd == "gpu":
            gpu = await client.get_gpu_status()
            if gpu:
                print(f"GPU: {gpu.name}")
                print(f"Memory: {gpu.memory_used_mb}/{gpu.memory_total_mb} MB")
                print(f"Utilization: {gpu.utilization_percent}%")
                print(f"Temperature: {gpu.temperature_c}°C")
        
        elif cmd == "deploy" and len(sys.argv) > 2:
            service = sys.argv[2]
            result = await deploy_gpu_service(service)
            print(f"Deploy result: {result}")
        
        elif cmd == "stop" and len(sys.argv) > 2:
            container = sys.argv[2]
            success = await client.stop_container(container)
            print(f"Stopped: {success}")
        
        else:
            print(f"Unknown command: {cmd}")
    
    asyncio.run(main())
