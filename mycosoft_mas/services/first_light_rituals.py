from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from mycosoft_mas.services.sensor_fusion import NaturePacket, SensorFusionService


@dataclass
class RitualObservation:
    timestamp: datetime
    environment: str
    summary: str
    anomalies: List[str]
    correlations: List[str]
    questions: List[str]


class FirstLightRitualService:
    """Phase 1 orchestration: sky-first ritual, daily ritual loop, and observation diary."""

    def __init__(self, consciousness: Optional[Any] = None) -> None:
        self._consciousness = consciousness

    async def run_sky_first(self) -> Dict[str, Any]:
        fusion = SensorFusionService(interval_ms=200, include_camera=True)
        async for packet in fusion.stream():
            memory_id = await self._store_episodic_memory(
                event_type="sky_first",
                packet=packet,
                note="MYCA first light observation: sky.",
            )
            fusion.stop()
            return {
                "status": "completed",
                "memory_id": memory_id,
                "timestamp": packet.timestamp.isoformat(),
                "has_frame": packet.camera_frame_bytes is not None,
            }
        return {"status": "failed", "reason": "no_packet"}

    async def run_daily_ritual(self, environments: List[str]) -> Dict[str, Any]:
        diary: List[Dict[str, Any]] = []
        for environment in environments:
            obs = await self._observe_environment(environment=environment)
            diary.append({
                "timestamp": obs.timestamp.isoformat(),
                "environment": obs.environment,
                "summary": obs.summary,
                "questions": obs.questions,
                "correlations": obs.correlations,
                "anomalies": obs.anomalies,
            })
            await self._store_episodic_memory(
                event_type="daily_ritual_observation",
                packet=None,
                note=obs.summary,
                payload=diary[-1],
            )
        return {"status": "completed", "entries": diary}

    async def _observe_environment(self, environment: str) -> RitualObservation:
        fusion = SensorFusionService(interval_ms=300, include_camera=True)
        packet: Optional[NaturePacket] = None
        async for pkt in fusion.stream():
            packet = pkt
            fusion.stop()
            break
        now = datetime.now(timezone.utc)
        if packet is None:
            return RitualObservation(
                timestamp=now,
                environment=environment,
                summary=f"No live packet available for {environment}",
                anomalies=["missing_sensor_packet"],
                correlations=[],
                questions=["What sensors are offline?"],
            )
        bme = packet.bme688 or {}
        temp = bme.get("temperature_c")
        humidity = bme.get("humidity_percent")
        summary = f"{environment}: temp={temp}, humidity={humidity}, fungal_signal={'present' if packet.fci else 'none'}"
        correlations = []
        if temp is not None and humidity is not None:
            correlations.append("Temperature and humidity baseline captured for this environment.")
        anomalies = []
        if temp is not None and (temp < -20 or temp > 60):
            anomalies.append("temperature_out_of_expected_range")
        questions = [
            "What changed compared to previous session?",
            "Which signal is strongest right now?",
            "What should MYCA observe next?",
        ]
        return RitualObservation(
            timestamp=now,
            environment=environment,
            summary=summary,
            anomalies=anomalies,
            correlations=correlations,
            questions=questions,
        )

    async def _store_episodic_memory(
        self,
        event_type: str,
        packet: Optional[NaturePacket],
        note: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        if not self._consciousness or not getattr(self._consciousness, "_memory_coordinator", None):
            return None
        memory = self._consciousness._memory_coordinator
        data: Dict[str, Any] = payload or {}
        data.update(
            {
                "event_type": event_type,
                "note": note,
                "packet": packet.to_dict() if packet else None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        try:
            entry = await memory.agent_remember(
                agent_id="myca",
                content=data,
                layer="episodic",
                importance=0.9 if event_type == "sky_first" else 0.7,
                tags=["first_light", event_type],
            )
            return str(entry.get("memory_id")) if isinstance(entry, dict) else None
        except Exception:
            return None

