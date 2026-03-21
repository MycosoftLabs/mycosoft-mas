"""
Observer MYCA Integration for Ethics Training

Watches sandbox sessions, generates notes/summaries from grading, and provides
batch report ingestion for production MYCA memory.

Created: March 4, 2026
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# In-memory observer notes (also used by ethics_training_api)
_observer_notes: List[Dict[str, Any]] = []


def get_observer_notes() -> List[Dict[str, Any]]:
    """Return the shared observer notes list."""
    return _observer_notes


def record_grade_observation(
    session_id: str,
    scenario_id: str,
    vessel_stage: str,
    grade: Dict[str, Any],
) -> None:
    """
    Record an observer note when a sandbox response is graded.
    Called by the ethics training API after run_scenario completes.
    """
    note = {
        "session_id": session_id,
        "scenario_id": scenario_id,
        "vessel_stage": vessel_stage,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "score": grade.get("score"),
        "letter_grade": grade.get("letter_grade"),
        "note": f"Observer graded {vessel_stage} sandbox: {grade.get('letter_grade', '?')} ({grade.get('score', 0)}/100) on scenario {scenario_id}",
        "summary": grade.get("observer_notes", ""),
    }
    _observer_notes.append(note)
    logger.debug(f"Observer note recorded for session {session_id} scenario {scenario_id}")


def generate_batch_summary(limit: int = 50) -> Dict[str, Any]:
    """
    Generate a batch report summary from recent grades for production MYCA ingestion.
    Returns a dict suitable for feeding into the memory system.

    TODO: Wire to production MYCA memory API when available.
    """
    from mycosoft_mas.ethics.grading_engine import get_grading_engine

    grading = get_grading_engine()
    report = grading.generate_report(group_by="vessel_stage")
    recent = _observer_notes[-limit:][::-1]

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "group_by": report.get("group_by", "vessel_stage"),
        "groups": report.get("groups", {}),
        "total_grades": report.get("total_grades", 0),
        "recent_observations": len(recent),
        "findings": [
            {
                "vessel_stage": r.get("vessel_stage", "unknown"),
                "scenario_id": r.get("scenario_id", ""),
                "score": r.get("score"),
                "letter_grade": r.get("letter_grade"),
            }
            for r in recent[:20]
        ],
    }
    logger.info(
        f"Batch summary generated: {summary.get('total_grades', 0)} grades, {len(recent)} observations"
    )
    return summary


async def ingest_batch_to_production(summary: Dict[str, Any]) -> bool:
    """
    Ingest batch report into production MYCA memory.
    Stub: logs the summary; full implementation would call memory API.

    Returns True if ingestion succeeded (or was skipped), False on error.
    """
    try:
        # TODO: Call production MYCA memory API to store learned ethical knowledge
        # e.g. memory.learn_fact("ethics_training_batch", summary)
        logger.info(f"Batch report ready for ingestion: {summary.get('total_grades', 0)} grades")
        return True
    except Exception as e:
        logger.warning(f"Batch ingestion stub: {e}")
        return False
