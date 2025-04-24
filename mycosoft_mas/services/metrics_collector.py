import asyncio
import logging
import psutil
import time
from typing import Dict, Any
from datetime import datetime
from .websocket_server import WebSocketServer

logger = logging.getLogger(__name__)

class MetricsCollector:
    def __init__(self, websocket_server: WebSocketServer, interval: float = 1.0):
        self.websocket_server = websocket_server
        self.interval = interval
        self.running = False
        self.task = None
        self.last_metrics: Dict[str, Any] = {
            "system": {},
            "resources": {},
            "performance": {},
            "agents": {}
        }

    async def start(self):
        """Start the metrics collector."""
        self.running = True
        self.task = asyncio.create_task(self._collect_metrics())
        logger.info("Metrics collector started")

    async def stop(self):
        """Stop the metrics collector."""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Metrics collector stopped")

    async def _collect_metrics(self):
        """Collect and send metrics at regular intervals."""
        while self.running:
            try:
                # Collect system metrics
                cpu_usage = psutil.cpu_percent(interval=0.1)
                memory = psutil.virtual_memory()
                memory_usage = memory.percent
                
                # Collect resource metrics
                disk = psutil.disk_usage('/')
                disk_usage = disk.percent
                network = psutil.net_io_counters()
                network_usage = (network.bytes_sent + network.bytes_recv) / (1024 * 1024)  # MB
                
                # Calculate performance metrics
                current_time = time.time()
                if self.last_metrics["performance"]:
                    last_time = datetime.fromisoformat(self.last_metrics["performance"]["timestamp"]).timestamp()
                    time_diff = current_time - last_time
                    if time_diff > 0:
                        throughput = network_usage / time_diff
                    else:
                        throughput = 0
                else:
                    throughput = 0
                
                # Update metrics through WebSocket server
                await self.websocket_server.update_system_metrics(cpu_usage, memory_usage)
                await self.websocket_server.update_resource_metrics(
                    cpu_usage,
                    memory_usage,
                    disk_usage,
                    network_usage
                )
                await self.websocket_server.update_performance_metrics(
                    time.time() - current_time,
                    throughput
                )
                
                # Store last metrics for next iteration
                self.last_metrics = {
                    "system": {
                        "timestamp": datetime.now().isoformat(),
                        "cpu": cpu_usage,
                        "memory": memory_usage
                    },
                    "resources": {
                        "timestamp": datetime.now().isoformat(),
                        "cpu": cpu_usage,
                        "memory": memory_usage,
                        "disk": disk_usage,
                        "network": network_usage
                    },
                    "performance": {
                        "timestamp": datetime.now().isoformat(),
                        "response_time": time.time() - current_time,
                        "throughput": throughput
                    }
                }
                
                await asyncio.sleep(self.interval)
                
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
                await asyncio.sleep(self.interval)

    def update_agent_status(self, agent_id: str, status: str, details: Dict[str, Any] = None):
        """Update agent status in the metrics collector."""
        asyncio.create_task(
            self.websocket_server.update_agent_status(agent_id, status, details)
        ) 