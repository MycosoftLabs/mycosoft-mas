from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from mycosoft_mas.services.basic_actuation import BasicActuationService
from mycosoft_mas.services.first_light_rituals import FirstLightRitualService
from mycosoft_mas.services.nature_replay import NatureReplayStore

router = APIRouter(prefix="/api/first-light", tags=["first-light"])


class DailyRitualRequest(BaseModel):
    environments: List[str] = Field(default_factory=lambda: ["sky", "soil", "canopy"])


class ReplayVerifyRequest(BaseModel):
    day_key: str


class ReplayReadRequest(BaseModel):
    day_key: str
    from_ts: Optional[str] = None
    until_ts: Optional[str] = None


class ActuationRequest(BaseModel):
    action_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)


@router.post("/ritual/sky-first")
async def sky_first() -> Dict[str, Any]:
    service = FirstLightRitualService()
    return await service.run_sky_first()


@router.post("/ritual/daily")
async def daily_ritual(request: DailyRitualRequest) -> Dict[str, Any]:
    service = FirstLightRitualService()
    return await service.run_daily_ritual(request.environments)


@router.post("/replay/verify")
async def replay_verify(request: ReplayVerifyRequest) -> Dict[str, Any]:
    store = NatureReplayStore()
    return await store.verify_replayable_day(request.day_key)


@router.post("/replay/read")
async def replay_read(request: ReplayReadRequest) -> Dict[str, Any]:
    store = NatureReplayStore()
    from_ts = datetime.fromisoformat(request.from_ts) if request.from_ts else None
    until_ts = datetime.fromisoformat(request.until_ts) if request.until_ts else None
    rows = []
    async for row in store.replay(day_key=request.day_key, from_ts=from_ts, until_ts=until_ts):
        rows.append({"ts": row.ts.isoformat(), "packet": row.packet})
    return {"day_key": request.day_key, "records": rows, "count": len(rows)}


@router.post("/actuation/execute")
async def execute_action(request: ActuationRequest) -> Dict[str, Any]:
    service = BasicActuationService()
    return await service.execute(action_type=request.action_type, payload=request.payload)
