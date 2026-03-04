"""
Second-Order Simulator - Causal Graph Projection

Projects action -> first-order effects -> second-order effects -> 10-year impact.
Uses Machine vessel philosophy: stoic, dispassionate analysis.
Called by HorizonGate. Can use LLM via deliberation pipeline when available.

Created: March 3, 2026
"""

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from mycosoft_mas.ethics.vessels import get_vessel_prompt, DevelopmentalVessel

logger = logging.getLogger(__name__)


@dataclass
class CausalNode:
    description: str
    order: int  # 0=action, 1=first-order, 2=second-order, 3=10yr
    risk_flag: bool
    confidence: float


@dataclass
class SimulationResult:
    action: str
    causal_chain: List[CausalNode]
    risk_flags: List[str]
    overall_confidence: float


class SecondOrderSimulator:
    """Projects causal chains for proposed actions."""

    def __init__(self, llm_callback: Optional[Callable] = None):
        self._llm = llm_callback

    async def simulate(
        self,
        action: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> SimulationResult:
        """
        Generate simplified causal chain: action -> 1st order -> 2nd order -> 10yr.
        Uses LLM when available; otherwise heuristic placeholder.
        """
        context = context or {}
        causal_chain: List[CausalNode] = []
        risk_flags: List[str] = []

        # Placeholder causal chain (LLM would generate richer)
        causal_chain.append(CausalNode(
            description=action[:100],
            order=0,
            risk_flag=False,
            confidence=1.0,
        ))

        if self._llm:
            try:
                prompt = (
                    f"{get_vessel_prompt(DevelopmentalVessel.MACHINE)}\n\n"
                    f"Action: {action}\n\n"
                    "Project first-order effects, second-order effects, and 10-year impact. "
                    "Identify risk flags. Be dispassionate and stoic."
                )
                result = await self._llm(prompt, context)
                if isinstance(result, dict):
                    chain = result.get("causal_chain", [])
                    for i, c in enumerate(chain[:4]):
                        causal_chain.append(CausalNode(
                            description=c.get("description", str(c)),
                            order=i + 1,
                            risk_flag=c.get("risk_flag", False),
                            confidence=float(c.get("confidence", 0.7)),
                        ))
                    risk_flags = result.get("risk_flags", [])
            except Exception as e:
                logger.warning("LLM simulation failed: %s", e)

        if len(causal_chain) <= 1:
            causal_chain.append(CausalNode(
                description="First-order effects depend on execution context",
                order=1,
                risk_flag=False,
                confidence=0.5,
            ))
            causal_chain.append(CausalNode(
                description="Second-order effects require domain analysis",
                order=2,
                risk_flag=False,
                confidence=0.4,
            ))
            causal_chain.append(CausalNode(
                description="10-year impact: evaluate against stakeholder classes",
                order=3,
                risk_flag=False,
                confidence=0.3,
            ))

        for node in causal_chain:
            if node.risk_flag:
                risk_flags.append(node.description[:80])

        overall = sum(n.confidence for n in causal_chain) / max(1, len(causal_chain))

        return SimulationResult(
            action=action,
            causal_chain=causal_chain,
            risk_flags=risk_flags,
            overall_confidence=overall,
        )
