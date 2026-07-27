"""MAS-resident integrity guard for CMMC posture reads.

The monitor treats an empty control result, a malformed unique-practice total,
or a sudden zero-Met regression as an availability incident—not a compliance
assessment.  A validated metadata snapshot is retained in Redis when
configured and is returned with ``degraded: true`` while the primary store is
unavailable.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

logger = logging.getLogger(__name__)

EXPECTED_CMMC_L2_PRACTICES = 110
REDIS_SNAPSHOT_KEY = "mas:security:posture-integrity:last-known-good:v1"


@dataclass(frozen=True)
class PostureSnapshot:
    controls: list[dict[str, Any]]
    met: int
    partial: int
    non_compliant: int
    total: int
    captured_at: str


@dataclass(frozen=True)
class IntegrityResult:
    controls: list[dict[str, Any]]
    snapshot: PostureSnapshot | None
    degraded: bool
    reason: str | None


def _practice_id(row: dict[str, Any]) -> str:
    raw = str(row.get("control_id") or row.get("id") or "").strip()
    return raw.split("-")[-1] if "-" in raw else raw


def _status_rank(row: dict[str, Any]) -> int:
    status = str(
        row.get("implementation_state") or row.get("status") or "planned"
    ).lower()
    return {"implemented": 3, "compliant": 3, "partial": 2}.get(status, 1)


def _has_evidence_uri(row: dict[str, Any]) -> bool:
    return bool(str(row.get("evidence_uri") or "").strip())


def _snapshot_from_controls(
    controls: Iterable[dict[str, Any]],
) -> tuple[PostureSnapshot | None, str | None]:
    controls_list = list(controls)
    unique: dict[str, dict[str, Any]] = {}
    for row in controls_list:
        practice_id = _practice_id(row)
        if not practice_id:
            continue
        if practice_id not in unique or _status_rank(row) > _status_rank(unique[practice_id]):
            unique[practice_id] = row

    if not unique:
        return None, "controls_empty"

    missing_evidence = [
        practice_id
        for practice_id, row in unique.items()
        if _status_rank(row) == 3 and not _has_evidence_uri(row)
    ]
    if missing_evidence:
        return None, (
            "implemented controls are missing evidence_uri: "
            + ", ".join(sorted(missing_evidence))
        )

    met = sum(_status_rank(row) == 3 for row in unique.values())
    partial = sum(_status_rank(row) == 2 for row in unique.values())
    non_compliant = sum(_status_rank(row) == 1 for row in unique.values())
    total = met + partial + non_compliant
    if total != EXPECTED_CMMC_L2_PRACTICES:
        return None, "expected_practice_count_mismatch"

    return (
        PostureSnapshot(
            controls=controls_list,
            met=met,
            partial=partial,
            non_compliant=non_compliant,
            total=total,
            captured_at=datetime.now(timezone.utc).isoformat(),
        ),
        None,
    )


class PostureIntegrityMonitor:
    """Validates, persists, and serves a last-known-good posture snapshot."""

    def __init__(self) -> None:
        self._last_good: PostureSnapshot | None = None
        self._last_reason: str | None = None
        self._task: asyncio.Task[None] | None = None

    async def validate_controls(
        self, controls: list[dict[str, Any]]
    ) -> IntegrityResult:
        snapshot, reason = _snapshot_from_controls(controls)
        if snapshot is not None and self._last_good is not None and snapshot.met == 0 and self._last_good.met > 0:
            reason = "met_count_zero_regression"
            snapshot = None

        if snapshot is not None:
            self._last_good = snapshot
            self._last_reason = None
            await self._persist_snapshot(snapshot)
            return IntegrityResult(snapshot.controls, snapshot, False, None)

        self._last_reason = reason
        logger.critical("CMMC posture integrity anomaly: %s", reason)
        persisted = await self._load_persisted_snapshot()
        fallback = persisted or self._last_good
        if fallback is not None:
            self._last_good = fallback
            return IntegrityResult(fallback.controls, fallback, True, reason)
        return IntegrityResult([], None, True, reason)

    async def health(self) -> dict[str, Any]:
        snapshot = await self._load_persisted_snapshot() or self._last_good
        return {
            "ok": snapshot is not None and self._last_reason is None,
            "degraded": self._last_reason is not None,
            "reason": self._last_reason,
            "expected_practices": EXPECTED_CMMC_L2_PRACTICES,
            "last_known_good": (
                {
                    "met": snapshot.met,
                    "partial": snapshot.partial,
                    "non_compliant": snapshot.non_compliant,
                    "total": snapshot.total,
                    "captured_at": snapshot.captured_at,
                }
                if snapshot
                else None
            ),
        }

    async def start(self, interval_seconds: int = 60) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run(interval_seconds))

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run(self, interval_seconds: int) -> None:
        while True:
            try:
                from mycosoft_mas.soc import repository as soc_repo

                controls = await soc_repo.list_compliance_controls()
                await self.validate_controls(controls)
            except Exception as exc:
                self._last_reason = "monitor_poll_failed"
                logger.critical("CMMC posture integrity monitor poll failed: %s", exc)
            await asyncio.sleep(interval_seconds)

    async def _redis(self) -> Any | None:
        url = os.getenv("REDIS_URL") or os.getenv("MINDEX_REDIS_URL")
        if not url:
            return None
        try:
            from redis import asyncio as redis_asyncio

            return redis_asyncio.from_url(url, decode_responses=True)
        except Exception as exc:
            logger.warning("CMMC posture Redis client unavailable: %s", exc)
            return None

    async def _persist_snapshot(self, snapshot: PostureSnapshot) -> None:
        client = await self._redis()
        if client is None:
            return
        try:
            await client.set(REDIS_SNAPSHOT_KEY, json.dumps(asdict(snapshot)))
        except Exception as exc:
            logger.warning("Could not persist CMMC posture snapshot: %s", exc)
        finally:
            await client.aclose()

    async def _load_persisted_snapshot(self) -> PostureSnapshot | None:
        client = await self._redis()
        if client is None:
            return None
        try:
            raw = await client.get(REDIS_SNAPSHOT_KEY)
            if not raw:
                return None
            data = json.loads(raw)
            return PostureSnapshot(**data)
        except Exception as exc:
            logger.warning("Could not read CMMC posture snapshot: %s", exc)
            return None
        finally:
            await client.aclose()


posture_integrity_monitor = PostureIntegrityMonitor()
