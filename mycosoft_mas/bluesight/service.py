"""In-memory BlueSight service (Phase 1)."""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from datetime import datetime
from typing import Any, Deque, DefaultDict, Dict, List, Optional

from mycosoft_mas.bluesight.adapters import SensorAdapterRegistry
from mycosoft_mas.bluesight.fusion import build_tracks, fuse_sensor_detections, reconcile_truth
from mycosoft_mas.bluesight.providers import ProviderRegistry
from mycosoft_mas.schemas.bluesight import (
    BlueSightModelHealth,
    BlueSightObservation,
    BlueSightSensorPacket,
    DeviceSceneObservation,
    EarthVisualObservation,
    PetriVisualObservation,
)
from mycosoft_mas.simulation.petri_persistence import (
    append_bluesight_observation_event,
    notify_nlm_petri_outcome,
)


class BlueSightService:
    def __init__(self) -> None:
        self._providers = ProviderRegistry()
        self._adapters = SensorAdapterRegistry()
        self._latest_by_profile: Dict[str, BlueSightObservation] = {}
        self._latest_by_run: Dict[str, BlueSightObservation] = {}
        self._queues: DefaultDict[str, Deque[BlueSightObservation]] = defaultdict(lambda: deque(maxlen=200))
        self._lock = asyncio.Lock()

    async def observe(self, packet: BlueSightSensorPacket, provider_name: str = "truth_bootstrap") -> BlueSightObservation:
        normalized = self._adapters.normalize(packet)
        provider = self._providers.provider(provider_name)
        detections = provider.detect(normalized)
        fused = fuse_sensor_detections(detections)
        tracks = build_tracks(fused, normalized.timestamp)
        truth_entities = _flatten_truth_entities(normalized.truth_state or {})
        reconciliation = reconcile_truth(fused, truth_entities)
        model_health = BlueSightModelHealth(
            model_name=provider.name,
            model_version="phase1",
            runtime="server_cpu",
            provider=provider.name,
            healthy=True,
        )
        base_kwargs = dict(
            run_id=normalized.run_id,
            frame_id=normalized.frame_id,
            timestamp=normalized.timestamp,
            source=normalized.source,
            detections=fused,
            tracks=tracks,
            reconciliation=reconciliation,
            model_health=model_health,
            truth_state_ref=f"{normalized.profile}:{normalized.run_id}:{normalized.frame_id}",
            metadata=normalized.metadata,
        )
        if normalized.profile == "petri":
            obs = PetriVisualObservation(
                **base_kwargs,
                dish=normalized.payload.get("dish", {}),
                summary=normalized.payload.get("summary", {}),
            )
        elif normalized.profile == "earth_globe":
            obs = EarthVisualObservation(
                **base_kwargs,
                geo_bounds=normalized.payload.get("geo_bounds"),
                scene_type=normalized.payload.get("scene_type"),
            )
        else:
            obs = DeviceSceneObservation(
                **base_kwargs,
                device_id=normalized.payload.get("device_id"),
                calibration_id=normalized.payload.get("calibration_id"),
            )

        async with self._lock:
            self._latest_by_profile[normalized.profile] = obs
            self._latest_by_run[normalized.run_id] = obs
            self._queues[normalized.profile].append(obs)
            self._queues[normalized.run_id].append(obs)

        append_bluesight_observation_event(obs.dict())
        if normalized.profile == "petri":
            asyncio.create_task(
                notify_nlm_petri_outcome(
                    session_id=normalized.run_id,
                    outcome_type="bluesight_observation",
                    summary={
                        "frame_id": normalized.frame_id,
                        "detection_count": len(fused),
                        "matched_sim_entities": reconciliation.matched_sim_entities,
                        "visual_truth_disagreement_score": reconciliation.visual_truth_disagreement_score,
                    },
                    metrics={"tracks": len(tracks)},
                )
            )
        return obs

    async def latest(self, profile: Optional[str] = None, run_id: Optional[str] = None) -> Optional[BlueSightObservation]:
        async with self._lock:
            if run_id:
                return self._latest_by_run.get(run_id)
            if profile:
                return self._latest_by_profile.get(profile)
            if self._latest_by_profile:
                key = sorted(self._latest_by_profile.keys())[-1]
                return self._latest_by_profile.get(key)
            return None

    async def next_for_stream(self, key: str, last_frame_id: Optional[str] = None) -> Optional[BlueSightObservation]:
        async with self._lock:
            queue = self._queues.get(key)
            if not queue:
                return None
            for obs in reversed(queue):
                if last_frame_id is None or obs.frame_id != last_frame_id:
                    return obs
            return None


def _flatten_truth_entities(truth_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    entities: List[Dict[str, Any]] = []
    for key in ("colonies", "spores", "tips", "segments", "nodes"):
        value = truth_state.get(key, [])
        if isinstance(value, list):
            entities.extend([item for item in value if isinstance(item, dict)])
    return entities


_SERVICE: Optional[BlueSightService] = None


def get_bluesight_service() -> BlueSightService:
    global _SERVICE
    if _SERVICE is None:
        _SERVICE = BlueSightService()
    return _SERVICE


def utc_now_iso() -> str:
    return datetime.utcnow().isoformat()

