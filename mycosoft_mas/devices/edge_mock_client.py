"""
Mock Edge Node Client for testing without hardware.

Connects via WebSocket to /ws/sandbox/{device_id} and responds
to sensor_read, gpio_write, and device_command with simulated data.
"""

import asyncio
import json
import logging
import random
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class EdgeMockClient:
    """Simulated edge node for testing the MycoBrain coordinator pipeline."""

    def __init__(
        self,
        device_id: str = "mock-mycobrain-01",
        gateway_url: str = "ws://192.168.0.191:9000",
    ):
        self.device_id = device_id
        self.gateway_url = f"{gateway_url}/ws/sandbox/{device_id}"
        self._ws = None
        self._running = False
        self._gpio_state: Dict[int, int] = {}

    async def connect(self):
        import websockets
        self._ws = await websockets.connect(self.gateway_url)
        await self._ws.send(json.dumps({
            "type": "handshake",
            "payload": {
                "role": "edge",
                "device_id": self.device_id,
                "capabilities": ["sensor_read", "gpio_write", "device_command"],
                "token": "",
            },
        }))
        ack = json.loads(await self._ws.recv())
        logger.info("Edge mock connected: %s", ack)
        self._running = True

    async def listen(self):
        while self._running and self._ws:
            try:
                raw = await self._ws.recv()
                msg = json.loads(raw)
                response = self._handle_command(msg)
                await self._ws.send(json.dumps(response))
            except Exception as exc:
                logger.error("Edge mock error: %s", exc)
                break

    def _handle_command(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        tool = msg.get("tool", msg.get("type", ""))
        request_id = msg.get("id", "")

        if tool == "sensor_read":
            return {
                "id": request_id,
                "type": "result",
                "payload": {
                    "temperature_c": round(22.0 + random.uniform(-2, 5), 1),
                    "humidity_pct": round(65.0 + random.uniform(-10, 15), 1),
                    "co2_ppm": random.randint(400, 800),
                    "voc_index": random.randint(50, 200),
                    "timestamp": time.time(),
                },
            }
        elif tool == "gpio_write":
            pin = msg.get("pin", 0)
            value = msg.get("value", 0)
            self._gpio_state[pin] = value
            return {
                "id": request_id,
                "type": "result",
                "payload": {"pin": pin, "value": value, "ok": True},
            }
        elif tool == "device_command":
            cmd = msg.get("command", "")
            return {
                "id": request_id,
                "type": "result",
                "payload": {"command": cmd, "response": f"Simulated: {cmd}", "ok": True},
            }
        else:
            return {
                "id": request_id,
                "type": "error",
                "payload": {"error": f"Unknown tool: {tool}"},
            }

    async def disconnect(self):
        self._running = False
        if self._ws:
            await self._ws.close()


async def main():
    import sys
    device_id = sys.argv[1] if len(sys.argv) > 1 else "mock-mycobrain-01"
    client = EdgeMockClient(device_id=device_id)
    await client.connect()
    logger.info("Mock edge node '%s' running...", device_id)
    await client.listen()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
