"""
Layer 3 — autonomous AI planning pass (sandbox scope only).

Uses Claude when ANTHROPIC_API_KEY is set; otherwise records an informational skip.
Does not execute offensive tooling — planning / prioritization only.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _pg() -> bool:
    return bool(os.getenv("MINDEX_DATABASE_URL") or os.getenv("DATABASE_URL"))


async def run_layer3_once() -> Dict[str, Any]:
    if not _pg():
        return {"skipped": True}
    from mycosoft_mas.integrations.anthropic_client import AnthropicClient
    from mycosoft_mas.soc import repository as soc_repo

    scope = os.getenv("SOC_REDTEAM_L3_SCOPE", "192.168.0.187 and https://sandbox.mycosoft.com")
    run_id = await soc_repo.create_redteam_run(
        layer=3,
        scope="sandbox_ai",
        tool="claude_planner",
        params={"scope": scope},
    )
    client = AnthropicClient()
    plan = await client.chat(
        content=(
            "You are a defensive red-team planner. Given scope: "
            f"{scope}\n"
            "List 3 safe verification steps (read-only) to validate segmentation "
            "and auth headers. One short paragraph, no attack instructions."
        ),
        system="Respond with defensive verification steps only. No exploits.",
    )
    if not plan:
        await soc_repo.insert_redteam_finding(
            run_id=run_id,
            severity="info",
            control_id="3.14.7",
            title="Layer 3 AI planner skipped (no ANTHROPIC_API_KEY or API error)",
            evidence={"scope": scope},
        )
        await soc_repo.finish_redteam_run(run_id, "completed", "L3 planner idle", None)
        return {"run_id": str(run_id), "skipped": True}

    await soc_repo.insert_redteam_finding(
        run_id=run_id,
        severity="low",
        control_id="3.14.7",
        title="AI defensive plan (sandbox scope)",
        evidence={"plan": plan[:8000], "scope": scope},
    )
    await soc_repo.finish_redteam_run(run_id, "completed", "L3 Claude planner", plan[:12000])
    return {"run_id": str(run_id), "chars": len(plan)}


async def _loop() -> None:
    interval = int(os.getenv("SOC_REDTEAM_L3_INTERVAL_SEC", "21600"))
    logger.info("Red team L3 loop starting (interval=%ss)", interval)
    while True:
        try:
            await run_layer3_once()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception("layer3 failed: %s", e)
        await asyncio.sleep(max(1800, interval))


_task: Optional[asyncio.Task[None]] = None


def start_redteam_layer3_background() -> None:
    global _task
    if os.getenv("SOC_REDTEAM_L3", "1") == "0":
        return
    if not _pg():
        return
    if _task and not _task.done():
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    _task = loop.create_task(_loop(), name="redteam-layer3")
