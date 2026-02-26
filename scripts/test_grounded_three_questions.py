#!/usr/bin/env python3
"""
Fast test script (~10s) for Grounded Cognition.

Enables MYCA_GROUNDED_COGNITION=1, asks three questions via consciousness,
verifies each response has EP, SelfState, WorldState, and ThoughtObjects with evidence.

Run from repo root: poetry run python scripts/test_grounded_three_questions.py

Created: February 17, 2026
"""

import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure package is on path
_repo = Path(__file__).resolve().parent.parent
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))

# Must set before importing consciousness modules
os.environ["MYCA_GROUNDED_COGNITION"] = "1"

# Mock heavy deps for fast run
for mod in ["mycosoft_mas.memory", "mycosoft_mas.memory.memory_coordinator",
            "mycosoft_mas.core.orchestrator_service", "mycosoft_mas.core.registry"]:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()


async def main() -> int:
    """Run three questions and report."""
    with patch("mycosoft_mas.monitoring.health_check.get_health_checker") as mock_hc:
        checker = MagicMock()
        checker.check_all = AsyncMock(return_value={"status": "healthy", "components": []})
        mock_hc.return_value = checker

        from mycosoft_mas.consciousness.core import (
            MYCAConsciousness,
            ConsciousnessState,
            get_consciousness,
        )

        import mycosoft_mas.consciousness.core as core_module
        core_module._consciousness_instance = None
        consciousness = get_consciousness()

        focus = MagicMock()
        focus.summary = "test"
        focus.id = "f1"
        focus.source = "text"
        focus.content = "test"
        focus.category = MagicMock(value="query")

        from mycosoft_mas.consciousness.working_memory import WorkingMemory
        wm = WorkingMemory()
        consciousness._working_memory = wm

        consciousness._attention = MagicMock()
        consciousness._attention.focus_on = AsyncMock(return_value=focus)
        consciousness._world_model = MagicMock()
        consciousness._world_model.get_relevant_context = AsyncMock(return_value={})
        consciousness._world_model.get_cached_context = MagicMock(
            return_value={"summary": "cached", "data": {}, "age_seconds": 0}
        )
        consciousness._get_soul_context = MagicMock(return_value={})
        consciousness._recall_relevant_memories = AsyncMock(return_value=[])
        consciousness._event_bus = MagicMock()
        consciousness._event_bus.drain = MagicMock(return_value=[])
        consciousness._intuition = MagicMock()
        consciousness._intuition.quick_response = AsyncMock(return_value=None)
        consciousness._emotions = MagicMock()
        consciousness._emotions.process_interaction = AsyncMock()
        consciousness._store_interaction = AsyncMock()
        consciousness._metrics = MagicMock()
        consciousness._metrics.thoughts_processed = 0
        consciousness._metrics.emotional_valence = 0.5
        consciousness._metrics.active_goals = []
        consciousness._state = ConsciousnessState.CONSCIOUS
        consciousness._awake = True
        consciousness._metrics.state = ConsciousnessState.CONSCIOUS

        captured_ep = []
        captured_kwargs = []

        async def _mock_think(*args, **kwargs):
            captured_ep.append(kwargs.get("experience_packet"))
            captured_kwargs.append(kwargs)
            from mycosoft_mas.schemas.thought_object import ThoughtObject, ThoughtObjectType
            ep = kwargs.get("experience_packet")
            if ep:
                root = ThoughtObject(
                    claim="User asked",
                    type=ThoughtObjectType.QUESTION,
                    evidence_links=[{"ep_id": ep.id}],
                    confidence=1.0,
                )
                wm.add_thought(root)
            async def _gen():
                yield "I understand your question."
            async for t in _gen():
                yield t
            if ep:
                result = ThoughtObject(
                    claim="I understand your question.",
                    type=ThoughtObjectType.ANSWER,
                    evidence_links=[{"ep_id": ep.id}],
                    confidence=0.85,
                )
                wm.add_thought(result)

        consciousness._deliberation = MagicMock()
        consciousness._deliberation.think_progressive = MagicMock(side_effect=_mock_think)

        questions = ["What is fungi?", "How does the system work?", "Hello!"]
        results = []
        for i, q in enumerate(questions):
            wm.clear_turn_thoughts()
            tokens = []
            async for t in consciousness.process_input(q, "text"):
                tokens.append(t)
            response = "".join(tokens)

            failed = False
            msg = ""
            if "[Grounding incomplete" in response or "[Cannot generate response" in response:
                failed = True
                msg = f"Grounding error: {response[:80]}"
            elif not captured_ep or len(captured_ep) <= i:
                failed = True
                msg = "No ExperiencePacket captured"
            else:
                ep = captured_ep[i]
                if not ep or not ep.self_state or not ep.world_state:
                    failed = True
                    msg = "EP missing self_state or world_state"
                else:
                    thoughts = wm.get_thoughts(10)
                    with_ev = [t for t in thoughts if t.has_evidence()]
                    if not with_ev:
                        failed = True
                        msg = "No ThoughtObject with evidence_links"
                    else:
                        msg = f"OK (EP={ep.id[:16]}..., {len(with_ev)} thoughts with evidence)"
            results.append((i + 1, q[:35], not failed, msg))

        print("\n=== Grounded Cognition Three Questions Test ===\n")
        all_pass = all(r[2] for r in results)
        for i, q, passed, msg in results:
            status = "PASS" if passed else "FAIL"
            print(f"  {i}. [{status}] {q}: {msg}")
        print()
        if all_pass:
            print("All checks PASSED. Grounding is used correctly.")
            return 0
        print("Some checks FAILED.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
