"""
MycoBrain Edge Node Coordinator

Registers MycoBrain devices as execution nodes in the Gateway,
routing commands to physical hardware via WebSocket or MQTT.
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from mycosoft_mas.gateway.control_plane import GatewayControlPlane

logger = logging.getLogger(__name__)

MQTT_BROKER = os.getenv("MQTT_BROKER", "192.168.0.189")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))


@dataclass
class EdgeNode:
    device_id: str
    capabilities: List[str]
    ws_connection: Optional[Any] = None
    mqtt_topic: Optional[str] = None
    status: str = "online"
    metadata: Dict[str, Any] = field(default_factory=dict)


class MycoBrainCoordinator:
    """Coordinates MycoBrain edge devices as execution nodes for MYCA."""

    EDGE_TOOLS = {
        "sensor_read": "Read sensor data from edge device",
        "gpio_write": "Set GPIO pin on edge device",
        "device_command": "Send arbitrary command to edge device",
    }

    def __init__(self, gateway: Optional["GatewayControlPlane"] = None):
        self._gateway = gateway
        self._nodes: Dict[str, EdgeNode] = {}
        self._mqtt_client = None

    def register_edge_node(
        self,
        device_id: str,
        capabilities: List[str],
        ws_connection=None,
        mqtt_topic: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        node = EdgeNode(
            device_id=device_id,
            capabilities=capabilities,
            ws_connection=ws_connection,
            mqtt_topic=mqtt_topic or f"myca/devices/{device_id}/cmd",
            metadata=metadata or {},
        )
        self._nodes[device_id] = node
        logger.info("Registered edge node: %s (capabilities: %s)", device_id, capabilities)

        if self._gateway:
            for tool_name, desc in self.EDGE_TOOLS.items():
                self._gateway.register_tool(
                    name=f"{tool_name}:{device_id}",
                    handler=lambda _d=device_id, _t=tool_name, **kw: self._handle_edge_tool(_d, _t, kw),
                    description=f"{desc} ({device_id})",
                )

    def unregister_edge_node(self, device_id: str):
        self._nodes.pop(device_id, None)
        logger.info("Unregistered edge node: %s", device_id)

    def get_edge_capabilities(self, device_id: str) -> List[str]:
        node = self._nodes.get(device_id)
        return node.capabilities if node else []

    def list_nodes(self) -> List[Dict[str, Any]]:
        return [
            {
                "device_id": n.device_id,
                "capabilities": n.capabilities,
                "status": n.status,
                "has_ws": n.ws_connection is not None,
                "mqtt_topic": n.mqtt_topic,
            }
            for n in self._nodes.values()
        ]

    async def route_to_edge(self, device_id: str, command: Dict[str, Any]) -> Dict[str, Any]:
        node = self._nodes.get(device_id)
        if not node:
            return {"error": f"Unknown edge node: {device_id}"}

        if node.ws_connection:
            return await self._route_via_ws(node, command)
        elif node.mqtt_topic:
            return await self._route_via_mqtt(node, command)
        return {"error": f"No connection to edge node {device_id}"}

    async def _route_via_ws(self, node: EdgeNode, command: Dict[str, Any]) -> Dict[str, Any]:
        try:
            await node.ws_connection.send_json(command)
            response = await asyncio.wait_for(node.ws_connection.receive_json(), timeout=10)
            return response
        except asyncio.TimeoutError:
            return {"error": "Edge node timed out"}
        except Exception as exc:
            return {"error": f"WebSocket error: {exc}"}

    async def _route_via_mqtt(self, node: EdgeNode, command: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if self._mqtt_client is None:
                await self._init_mqtt()
            if self._mqtt_client:
                self._mqtt_client.publish(node.mqtt_topic, json.dumps(command))
                return {"status": "sent", "topic": node.mqtt_topic}
            return {"error": "MQTT client not available"}
        except Exception as exc:
            return {"error": f"MQTT error: {exc}"}

    async def _init_mqtt(self):
        try:
            import paho.mqtt.client as mqtt
            self._mqtt_client = mqtt.Client(client_id="myca-coordinator")
            self._mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self._mqtt_client.loop_start()
            logger.info("MQTT connected to %s:%d", MQTT_BROKER, MQTT_PORT)
        except Exception as exc:
            logger.warning("MQTT init failed: %s", exc)
            self._mqtt_client = None

    async def _handle_edge_tool(
        self, device_id: str, tool_name: str, args: Dict[str, Any],
    ) -> Dict[str, Any]:
        return await self.route_to_edge(device_id, {"tool": tool_name, **args})
