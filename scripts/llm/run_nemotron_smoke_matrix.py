"""
Nemotron migration smoke matrix runner.

Runs lightweight routing checks for corporate/infrastructure/device/route/nlm/
consciousness categories and optional live chat probes through LLMRouter.

Usage:
  poetry run python scripts/llm/run_nemotron_smoke_matrix.py
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mycosoft_mas.llm.backend_selection import (
    EMBEDDING,
    EXECUTION,
    FAST,
    MYCA_CORE,
    PLANNING,
    get_backend_for_role,
)
from mycosoft_mas.llm.providers.base import Message
from mycosoft_mas.llm.router import LLMRouter


OUTPUT_PATH = Path("tmp/nemotron_smoke_matrix_latest.json")


def _selection_check(role: str, category: str) -> dict[str, Any]:
    selection = get_backend_for_role(role)
    return {
        "kind": "selection",
        "category": category,
        "role": role,
        "provider": selection.provider,
        "model": selection.model,
        "base_url": selection.base_url,
        "status": "pass",
    }


async def _chat_check(router: LLMRouter, task_type: str, category: str, prompt: str) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    try:
        response = await router.chat(
            messages=[Message(role="user", content=prompt)],
            task_type=task_type,
            max_tokens=80,
            temperature=0.0,
        )
        routing = {}
        if isinstance(response.raw_response, dict):
            routing = response.raw_response.get("routing", {}) or {}
        return {
            "kind": "chat",
            "category": category,
            "task_type": task_type,
            "status": "pass",
            "provider": routing.get("provider", response.provider),
            "model": routing.get("model", response.model),
            "backend_mode": routing.get("backend_mode", ""),
            "fallback_used": bool(routing.get("fallback_used", False)),
            "duration_ms": response.duration_ms,
            "response_preview": (response.content or "")[:180],
            "started_at": started.isoformat(),
        }
    except Exception as exc:  # noqa: BLE001 - smoke script should not crash hard
        return {
            "kind": "chat",
            "category": category,
            "task_type": task_type,
            "status": "fail",
            "error": str(exc),
            "started_at": started.isoformat(),
        }


async def main() -> int:
    router = LLMRouter()

    results: list[dict[str, Any]] = []
    # Category mapping checks (routing-layer only).
    results.extend(
        [
            _selection_check(MYCA_CORE, "corporate"),
            _selection_check("infrastructure_ops", "infrastructure"),
            _selection_check("device_telemetry", "device"),
            _selection_check("route_dispatch", "route"),
            _selection_check("nlm_reasoning", "nlm"),
            _selection_check("consciousness_reflection", "consciousness"),
        ]
    )

    # Live chat checks through LLMRouter task types used by runtime.
    results.extend(
        [
            await _chat_check(router, PLANNING, "corporate", "Summarize migration risk in one sentence."),
            await _chat_check(router, EXECUTION, "corporate", "Return JSON with key=ok and value=true."),
            await _chat_check(router, FAST, "corporate", "One-word status response."),
            await _chat_check(router, EMBEDDING, "nlm", "Embedding path health probe."),
        ]
    )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(results),
        "passed": sum(1 for item in results if item.get("status") == "pass"),
        "failed": sum(1 for item in results if item.get("status") == "fail"),
        "results": results,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote smoke matrix: {OUTPUT_PATH}")
    print(f"Passed: {payload['passed']}  Failed: {payload['failed']}")
    return 0 if payload["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

