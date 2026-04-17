"""FastAPI router for MYCA Harness (optional include from myca_main)."""

from __future__ import annotations

from fastapi import APIRouter

from mycosoft_mas.harness.engine import get_engine, set_engine
from mycosoft_mas.harness.models import HarnessPacket, HarnessResult

router = APIRouter(prefix="/api/harness", tags=["myca-harness"])


@router.get("/health")
async def harness_health() -> dict[str, str]:
    return {"status": "ok", "component": "myca-harness"}


@router.post("/packet", response_model=HarnessResult)
async def harness_packet(packet: HarnessPacket) -> HarnessResult:
    return await get_engine().run(packet)


def reset_engine_for_tests() -> None:
    set_engine(None)
