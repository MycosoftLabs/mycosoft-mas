from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from embodiment.arm.elephant_robotics_arm import ArmPose, ElephantRoboticsArmClient
from embodiment.camera.jetson_camera import JetsonCameraClient


@dataclass
class EmbodimentSnapshot:
    timestamp: datetime
    frame_bytes: Optional[bytes]
    arm_status: Dict[str, Any]


class EmbodimentController:
    def __init__(self, arm_base_url: str, camera_base_url: str) -> None:
        self.arm = ElephantRoboticsArmClient(base_url=arm_base_url)
        self.camera = JetsonCameraClient(base_url=camera_base_url)

    async def close(self) -> None:
        await self.arm.close()
        await self.camera.close()

    async def look_at_sky_pose(self) -> Dict[str, Any]:
        return await self.arm.move_to_pose(
            ArmPose(x=0.0, y=0.16, z=0.36, roll=0.0, pitch=-1.2, yaw=0.0),
            speed=0.15,
        )

    async def capture_snapshot(self) -> EmbodimentSnapshot:
        return EmbodimentSnapshot(
            timestamp=datetime.now(timezone.utc),
            frame_bytes=await self.camera.frame(),
            arm_status=await self.arm.health(),
        )

