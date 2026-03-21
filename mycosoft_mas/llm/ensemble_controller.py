"""
Unified Ensemble Controller for MYCA Opposable Thumb architecture.

Combines internal LLM router + frontier router signals, then arbitrates with
sensor-grounded evidence.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from mycosoft_mas.llm.finger_registry import FingerRegistry
from mycosoft_mas.llm.frontier_router import ConversationContext, FrontierLLMRouter
from mycosoft_mas.llm.providers.base import Message
from mycosoft_mas.llm.router import LLMRouter
from mycosoft_mas.llm.truth_arbitrator import (
    ArbitrationCandidate,
    ArbitrationResult,
    TruthArbitrator,
)


@dataclass
class EnsembleResponse:
    """Structured result from ensemble execution."""

    content: str
    selected_source: str
    arbitration: Dict[str, Any]
    candidates: List[Dict[str, Any]] = field(default_factory=list)


class EnsembleController:
    """
    Coordinates multiple LLM "fingers" and returns an arbitrated answer.
    """

    def __init__(
        self,
        llm_router: Optional[LLMRouter] = None,
        frontier_router: Optional[FrontierLLMRouter] = None,
        finger_registry: Optional[FingerRegistry] = None,
        arbitrator: Optional[TruthArbitrator] = None,
    ) -> None:
        self.llm_router = llm_router or LLMRouter()
        self.frontier_router = frontier_router or FrontierLLMRouter()
        self.finger_registry = finger_registry or FingerRegistry()
        self.arbitrator = arbitrator or TruthArbitrator()

    @staticmethod
    def _biosphere_firewall(sensor_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Redact raw telemetry before any external-finger usage.

        Only allow summarized, non-sensitive biosphere context.
        """
        if not sensor_context:
            return {}
        allowed = {}
        for key in ("summary", "trend", "anomaly_flags", "derived_metrics", "freshness"):
            if key in sensor_context:
                allowed[key] = sensor_context[key]
        return allowed

    async def _run_llm_router(self, prompt: str, task_type: str) -> ArbitrationCandidate:
        response = await self.llm_router.chat(
            messages=[Message(role="user", content=prompt)],
            task_type=task_type,
        )
        confidence = response.raw_response.get("confidence", 0.7) if response.raw_response else 0.7
        return ArbitrationCandidate(
            source="llm_router",
            content=response.content,
            confidence=float(confidence) if isinstance(confidence, (int, float)) else 0.7,
            metadata={"provider": response.provider, "model": response.model},
        )

    async def _run_frontier(self, prompt: str, session_id: str) -> ArbitrationCandidate:
        context = ConversationContext(session_id=session_id, conversation_id=session_id)
        chunks: List[str] = []
        async for token in self.frontier_router.stream_response(prompt, context, provider="auto"):
            chunks.append(token)
        content = "".join(chunks).strip()
        return ArbitrationCandidate(
            source="frontier_router",
            content=content,
            confidence=0.68,
            metadata={"provider": "auto"},
        )

    async def route_query(
        self,
        prompt: str,
        task_type: str = "execution",
        sensor_context: Optional[Dict[str, Any]] = None,
        session_id: str = "ensemble-session",
    ) -> EnsembleResponse:
        """
        Execute parallel LLM routes, then arbitrate with sensor evidence.
        """
        firewall_context = self._biosphere_firewall(sensor_context)
        augmented_prompt = prompt
        if firewall_context:
            augmented_prompt = (
                f"{prompt}\n\nBiosphere context summary (redacted): {firewall_context}"
            )

        router_task = asyncio.create_task(self._run_llm_router(augmented_prompt, task_type))
        frontier_task = asyncio.create_task(self._run_frontier(augmented_prompt, session_id))
        results = await asyncio.gather(router_task, frontier_task, return_exceptions=True)

        candidates: List[ArbitrationCandidate] = []
        for item in results:
            if isinstance(item, ArbitrationCandidate) and item.content:
                candidates.append(item)

        if not candidates:
            raise RuntimeError("No ensemble candidates available")

        arbitration: ArbitrationResult = self.arbitrator.arbitrate(
            candidates=candidates,
            sensor_evidence=sensor_context or {},
        )
        return EnsembleResponse(
            content=arbitration.winner.content,
            selected_source=arbitration.winner.source,
            arbitration=arbitration.to_dict(),
            candidates=[
                {
                    "source": c.source,
                    "confidence": c.confidence,
                    "content": c.content,
                    "metadata": c.metadata,
                }
                for c in candidates
            ],
        )
