"""Execution planning with intention-brain alignment."""

from __future__ import annotations

from typing import Any

from mycosoft_mas.harness.intention_brain import IntentionBrain
from mycosoft_mas.harness.models import HarnessPacket, HarnessResult, RouteType


class HarnessPlanner:
    def __init__(self, brain: IntentionBrain | None = None) -> None:
        self._brain = brain

    def plan(self, packet: HarnessPacket, route: RouteType) -> dict[str, Any]:
        steps: list[str] = []
        if self._brain:
            task = self._brain.get_next_task()
            if task:
                steps.append(f"consider_goal:{task.goal_id}")
        if route == RouteType.STATIC:
            steps.append("static_lookup")
        elif route == RouteType.MINDEX_GROUNDED:
            steps.append("mindex_unified_search")
            steps.append("nemotron_generate_with_context")
        elif route == RouteType.NLM:
            steps.append("build_frame")
            steps.append("nlm_predict")
        elif route == RouteType.NEMOTRON:
            steps.append("nemotron_generate")
        elif route == RouteType.PERSONAPLEX_VOICE:
            steps.append("asr")
            steps.append("route_inner")
            steps.append("tts")
        else:
            steps.append("nemotron_generate")
        return {"steps": steps, "route": route.value}


def attach_result_meta(result: HarnessResult, plan: dict[str, Any]) -> HarnessResult:
    result.structured["plan"] = plan
    return result
