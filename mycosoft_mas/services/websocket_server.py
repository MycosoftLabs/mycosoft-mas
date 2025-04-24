import asyncio
import json
import logging
import websockets
from typing import Dict, Set, Any
from datetime import datetime
from ..core.knowledge_graph import KnowledgeGraph

logger = logging.getLogger(__name__)

class WebSocketServer:
    def __init__(self, knowledge_graph: KnowledgeGraph, host: str = "0.0.0.0", port: int = 8765):
        self.knowledge_graph = knowledge_graph
        self.host = host
        self.port = port
        self.server = None
        self.metrics_buffer: Dict[str, Any] = {
            "system": {},
            "resources": {},
            "performance": {},
            "agents": {}
        }

    async def start(self) -> None:
        """Start the WebSocket server."""
        self.server = await websockets.serve(
            self.handle_connection,
            self.host,
            self.port
        )
        logger.info(f"WebSocket server started on ws://{self.host}:{self.port}")

    async def stop(self) -> None:
        """Stop the WebSocket server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("WebSocket server stopped")

    async def handle_connection(self, websocket: websockets.WebSocketServerProtocol, path: str) -> None:
        """Handle a new WebSocket connection."""
        try:
            # Handle the connection in the knowledge graph
            await self.knowledge_graph.handle_websocket(websocket)
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            logger.error(f"Error handling WebSocket connection: {e}")

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast a message to all connected clients."""
        if not self.server:
            return

        message_str = json.dumps(message)
        for websocket in self.knowledge_graph.websocket_clients:
            try:
                await websocket.send(message_str)
            except websockets.exceptions.ConnectionClosed:
                pass
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")

    async def broadcast_metrics(self, metrics_type: str, data: Dict[str, Any]):
        """Broadcast metrics to all connected clients."""
        self.metrics_buffer[metrics_type] = data
        message = json.dumps({metrics_type: data})
        
        if self.knowledge_graph.websocket_clients:
            await asyncio.gather(
                *[client.send(message) for client in self.knowledge_graph.websocket_clients],
                return_exceptions=True
            )

    async def update_system_metrics(self, cpu_usage: float, memory_usage: float):
        """Update and broadcast system metrics."""
        await self.broadcast_metrics("system", {
            "timestamp": datetime.now().isoformat(),
            "cpu": cpu_usage,
            "memory": memory_usage
        })

    async def update_resource_metrics(self, cpu: float, memory: float, disk: float, network: float):
        """Update and broadcast resource utilization metrics."""
        await self.broadcast_metrics("resources", {
            "timestamp": datetime.now().isoformat(),
            "cpu": cpu,
            "memory": memory,
            "disk": disk,
            "network": network
        })

    async def update_performance_metrics(self, response_time: float, throughput: float):
        """Update and broadcast performance metrics."""
        await self.broadcast_metrics("performance", {
            "timestamp": datetime.now().isoformat(),
            "response_time": response_time,
            "throughput": throughput
        })

    async def update_agent_status(self, agent_id: str, status: str, details: Dict[str, Any] = None):
        """Update and broadcast agent status."""
        self.metrics_buffer["agents"][agent_id] = {
            "status": status,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast_metrics("agents", self.metrics_buffer["agents"])

async def start_websocket_server(knowledge_graph: KnowledgeGraph) -> WebSocketServer:
    """Create and start a WebSocket server."""
    server = WebSocketServer(knowledge_graph)
    await server.start()
    return server 