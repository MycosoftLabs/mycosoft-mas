from typing import Dict, List, Optional
import asyncio
import websockets
import json
from datetime import datetime
from .base_agent import BaseAgent
from .metrics_collector import MetricsCollector
from .knowledge_graph import KnowledgeGraph
from .network_monitor import NetworkMonitor

class IntegrationService:
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.metrics_collector = MetricsCollector()
        self.knowledge_graph = KnowledgeGraph()
        self.network_monitor = NetworkMonitor()
        self.websocket_clients = set()
        self.metrics_update_interval = 5  # seconds
        self.status_update_interval = 10  # seconds

    async def register_agent(self, agent: BaseAgent) -> None:
        """Register a new agent with the integration service."""
        self.agents[agent.id] = agent
        await self.knowledge_graph.add_agent(agent)
        await self.broadcast_agent_status()

    async def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent from the integration service."""
        if agent_id in self.agents:
            del self.agents[agent_id]
            await self.knowledge_graph.remove_agent(agent_id)
            await self.broadcast_agent_status()

    async def start_monitoring(self) -> None:
        """Start the monitoring services."""
        await self.metrics_collector.start()
        await self.network_monitor.start()
        asyncio.create_task(self._metrics_update_loop())
        asyncio.create_task(self._status_update_loop())

    async def stop_monitoring(self) -> None:
        """Stop the monitoring services."""
        await self.metrics_collector.stop()
        await self.network_monitor.stop()

    async def _metrics_update_loop(self) -> None:
        """Periodically collect and broadcast metrics."""
        while True:
            try:
                metrics = await self.metrics_collector.collect_metrics()
                network_stats = await self.network_monitor.get_stats()
                await self.broadcast_metrics(metrics, network_stats)
            except Exception as e:
                print(f"Error in metrics update loop: {e}")
            await asyncio.sleep(self.metrics_update_interval)

    async def _status_update_loop(self) -> None:
        """Periodically update and broadcast agent statuses."""
        while True:
            try:
                await self.broadcast_agent_status()
            except Exception as e:
                print(f"Error in status update loop: {e}")
            await asyncio.sleep(self.status_update_interval)

    async def broadcast_metrics(self, metrics: Dict, network_stats: Dict) -> None:
        """Broadcast metrics to all connected WebSocket clients."""
        message = {
            "type": "metrics",
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics,
            "network": network_stats
        }
        await self._broadcast(message)

    async def broadcast_agent_status(self) -> None:
        """Broadcast agent statuses to all connected WebSocket clients."""
        agent_statuses = {
            agent_id: {
                "id": agent_id,
                "name": agent.name,
                "status": agent.status,
                "last_update": agent.last_update.isoformat() if agent.last_update else None,
                "metrics": agent.metrics
            }
            for agent_id, agent in self.agents.items()
        }
        message = {
            "type": "status",
            "timestamp": datetime.now().isoformat(),
            "agents": agent_statuses
        }
        await self._broadcast(message)

    async def _broadcast(self, message: Dict) -> None:
        """Broadcast a message to all connected WebSocket clients."""
        if not self.websocket_clients:
            return

        message_str = json.dumps(message)
        disconnected = set()
        for client in self.websocket_clients:
            try:
                await client.send(message_str)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
            except Exception as e:
                print(f"Error broadcasting to client: {e}")
                disconnected.add(client)

        self.websocket_clients -= disconnected

    async def handle_websocket(self, websocket: websockets.WebSocketServerProtocol) -> None:
        """Handle a new WebSocket connection."""
        self.websocket_clients.add(websocket)
        try:
            # Send initial data
            await self.broadcast_agent_status()
            metrics = await self.metrics_collector.collect_metrics()
            network_stats = await self.network_monitor.get_stats()
            await self.broadcast_metrics(metrics, network_stats)

            # Keep connection alive
            async for message in websocket:
                pass
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.websocket_clients.remove(websocket) 