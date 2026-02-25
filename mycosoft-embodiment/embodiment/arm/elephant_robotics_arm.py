from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx


@dataclass
class ArmPose:
    x: float
    y: float
    z: float
    roll: float
    pitch: float
    yaw: float


class ElephantRoboticsArmClient:
    """
    Thin HTTP client for ElephantRobotics arm control service.

    This module is repo-local so the `mycosoft-embodiment` project can evolve
    independently from MAS while still exposing the same action contract.
    """

    def __init__(self, base_url: str = "http://192.168.0.100:8090", timeout_s: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout_s)

    async def close(self) -> None:
        await self._client.aclose()

    async def health(self) -> Dict[str, Any]:
        response = await self._client.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()

    async def move_to_pose(self, pose: ArmPose, speed: float = 0.2) -> Dict[str, Any]:
        response = await self._client.post(
            f"{self.base_url}/arm/move",
            json={
                "x": pose.x,
                "y": pose.y,
                "z": pose.z,
                "roll": pose.roll,
                "pitch": pose.pitch,
                "yaw": pose.yaw,
                "speed": speed,
            },
        )
        response.raise_for_status()
        return response.json()

    async def open_gripper(self) -> Dict[str, Any]:
        response = await self._client.post(f"{self.base_url}/gripper/open")
        response.raise_for_status()
        return response.json()

    async def close_gripper(self, force: float = 0.3) -> Dict[str, Any]:
        response = await self._client.post(f"{self.base_url}/gripper/close", json={"force": force})
        response.raise_for_status()
        return response.json()

    async def safe_look_up(self) -> None:
        await self.move_to_pose(ArmPose(x=0.0, y=0.18, z=0.32, roll=0.0, pitch=-0.6, yaw=0.0))

