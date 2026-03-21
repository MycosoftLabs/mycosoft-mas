"""
Ethics Review Gate — Pre-execution task ethics check.

Runs every autonomous action through the ethics pipeline before execution.
Returns PASS (proceed), WARN (proceed with caution, log to Morgan), or BLOCK (do not execute).

Wired into MYCA OS executive decision pipeline — every autonomous action passes this gate.
Created: March 5, 2026 — MYCA Loop Closure
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from mycosoft_mas.ethics.engine import EthicsEngine, EthicsResult, EthicsRiskLevel

logger = logging.getLogger(__name__)


class ReviewOutcome(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    BLOCK = "BLOCK"


@dataclass
class ReviewResult:
    outcome: ReviewOutcome
    reasons: list = field(default_factory=list)
    ethics_result: Optional[EthicsResult] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "outcome": self.outcome.value,
            "reasons": self.reasons,
            "blocked_reason": self.ethics_result.blocked_reason if self.ethics_result else None,
            "risk_level": self.ethics_result.risk_level.value if self.ethics_result else None,
        }


def _load_checklist_for_task_type(task_type: str) -> Optional[Dict[str, Any]]:
    """Load ethics checklist YAML for task_type if it maps to a sector (e.g. defense, public, hardware)."""
    try:
        import yaml

        checklists_dir = Path(__file__).resolve().parents[2] / "config" / "ethics_checklists"
        if not checklists_dir.exists():
            return None
        # task_type can map to checklist: defense_sector, public_sector, hardware_deployment, general_operations
        mapping = {
            "deployment": "hardware_deployment",
            "infrastructure_change": "hardware_deployment",
            "security_change": "defense_sector",
            "new_integration": "general_operations",
        }
        checklist_name = mapping.get(task_type, "general_operations")
        path = checklists_dir / f"{checklist_name}.yaml"
        if path.exists():
            return yaml.safe_load(path.read_text())
    except Exception as e:
        logger.debug("Checklist load failed: %s", e)
    return None


async def run_ethics_review(
    task: Dict[str, Any],
    mindex_client=None,
    simulator=None,
) -> ReviewResult:
    """
    Run ethics review on a task before autonomous execution.

    Args:
        task: Task dict with title, description, type, etc.
        mindex_client: Optional MINDEX client for fact verification
        simulator: Optional SecondOrderSimulator for horizon gate

    Returns:
        ReviewResult with outcome (PASS/WARN/BLOCK) and reasons
    """
    title = task.get("title", "")
    description = task.get("description", "")
    task_type = task.get("type", "general")
    content = f"{title}\n\n{description}".strip() or "No description"
    context = {"task_type": task_type, "source": task.get("source", "self")}

    try:
        engine = EthicsEngine(mindex_client=mindex_client, simulator=simulator)
        result = await engine.evaluate(content, context)
    except Exception as e:
        logger.warning("Ethics engine failed, defaulting to WARN: %s", e)
        return ReviewResult(
            outcome=ReviewOutcome.WARN,
            reasons=[f"Ethics engine error: {e}"],
        )

    # Map EthicsResult to ReviewOutcome
    if result.passed:
        if result.risk_level in (EthicsRiskLevel.MEDIUM, EthicsRiskLevel.HIGH):
            return ReviewResult(
                outcome=ReviewOutcome.WARN,
                reasons=result.gate_reports or [],
                ethics_result=result,
            )
        return ReviewResult(
            outcome=ReviewOutcome.PASS,
            reasons=[],
            ethics_result=result,
        )

    # Failed — BLOCK
    reasons = [result.blocked_reason or "Ethics gates failed"]
    if result.gate_reports:
        reasons.extend(result.gate_reports[:3])
    return ReviewResult(
        outcome=ReviewOutcome.BLOCK,
        reasons=reasons,
        ethics_result=result,
    )
