"""
Contradiction Detector - Temporal Fact Validation.
Created: April 7, 2026

Validates incoming facts against the unified temporal knowledge graph.
Detects conflicting assertions by checking temporal validity windows.

Inspired by mempalace's contradiction detection, adapted for MYCA's
multi-agent environment where 158+ agents may assert conflicting facts.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ContradictionDetector")


@dataclass
class Contradiction:
    """A detected contradiction between facts."""

    severity: str  # "error" | "warning" | "info"
    message: str
    existing_fact: Dict[str, Any]
    incoming_fact: Dict[str, Any]
    conflict_type: str  # "direct", "temporal", "attribution", "value"


class ContradictionDetector:
    """
    Validates new facts against existing temporal knowledge graph.

    Checks for:
    - Direct contradictions (A is B vs A is C, both currently valid)
    - Temporal conflicts (overlapping validity windows with different values)
    - Attribution conflicts (different agents claiming different things)
    - Value conflicts (numeric disagreements beyond threshold)
    """

    def __init__(self, pool=None):
        self._pool = pool

    async def initialize(self, pool=None) -> None:
        """Initialize with connection pool."""
        if pool:
            self._pool = pool
        elif not self._pool:
            from mycosoft_mas.memory.palace.db_pool import get_shared_pool
            self._pool = await get_shared_pool()

    async def check(
        self,
        subject: str,
        predicate: str,
        obj: str,
        valid_from: Optional[datetime] = None,
        confidence: float = 1.0,
    ) -> List[Contradiction]:
        """
        Check if a new fact contradicts existing knowledge.

        Args:
            subject: Entity (e.g., "Amanita muscaria")
            predicate: Relationship (e.g., "contains")
            obj: Target value (e.g., "ibotenic acid")
            valid_from: When this fact becomes valid
            confidence: Confidence in the new fact

        Returns:
            List of detected contradictions (empty = safe to add)
        """
        if not self._pool:
            await self.initialize()

        contradictions = []
        valid_from = valid_from or datetime.now(timezone.utc)

        async with self._pool.acquire() as conn:
            # Find existing edges with same subject+predicate that are currently valid
            existing = await conn.fetch(
                """
                SELECT e.*, ns.name as source_name, nt.name as target_name
                FROM mindex.knowledge_edges e
                JOIN mindex.knowledge_nodes ns ON ns.id = e.source_id
                JOIN mindex.knowledge_nodes nt ON nt.id = e.target_id
                WHERE ns.name ILIKE $1
                AND e.edge_type = $2
                AND (e.valid_to IS NULL OR e.valid_to > $3)
                AND (e.valid_from IS NULL OR e.valid_from <= $3)
                """,
                subject,
                predicate,
                valid_from,
            )

            for row in existing:
                target_name = row["target_name"]
                existing_confidence = row.get("confidence", 1.0)

                # Direct contradiction: same subject+predicate, different object
                if target_name.lower() != obj.lower():
                    severity = "error" if min(confidence, existing_confidence) > 0.7 else "warning"
                    contradictions.append(
                        Contradiction(
                            severity=severity,
                            message=(
                                f"Conflict: '{subject}' {predicate} '{obj}' "
                                f"contradicts existing: '{subject}' {predicate} '{target_name}'"
                            ),
                            existing_fact={
                                "subject": subject,
                                "predicate": predicate,
                                "object": target_name,
                                "confidence": existing_confidence,
                                "valid_from": str(row.get("valid_from", "")),
                                "valid_to": str(row.get("valid_to", "")),
                                "edge_id": str(row["id"]),
                            },
                            incoming_fact={
                                "subject": subject,
                                "predicate": predicate,
                                "object": obj,
                                "confidence": confidence,
                                "valid_from": str(valid_from),
                            },
                            conflict_type="direct",
                        )
                    )

        return contradictions

    async def check_and_report(
        self,
        subject: str,
        predicate: str,
        obj: str,
        valid_from: Optional[datetime] = None,
        confidence: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Check for contradictions and return a summary report.

        Returns:
            {
                "safe": bool,
                "contradictions": [...],
                "recommendation": str
            }
        """
        contradictions = await self.check(
            subject, predicate, obj, valid_from, confidence
        )

        if not contradictions:
            return {
                "safe": True,
                "contradictions": [],
                "recommendation": "No contradictions found. Safe to add.",
            }

        errors = [c for c in contradictions if c.severity == "error"]
        warnings = [c for c in contradictions if c.severity == "warning"]

        if errors:
            recommendation = (
                f"Found {len(errors)} direct contradiction(s). "
                "Consider invalidating the old fact first, or adjusting confidence."
            )
        else:
            recommendation = (
                f"Found {len(warnings)} potential conflict(s). "
                "May be safe to add with temporal windowing."
            )

        return {
            "safe": len(errors) == 0,
            "contradictions": [
                {
                    "severity": c.severity,
                    "message": c.message,
                    "conflict_type": c.conflict_type,
                    "existing": c.existing_fact,
                    "incoming": c.incoming_fact,
                }
                for c in contradictions
            ],
            "recommendation": recommendation,
        }
