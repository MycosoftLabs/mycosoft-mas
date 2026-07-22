from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from mycosoft_mas.compliance import evidence_emitter


def test_validate_artifact_ref_preveil_requires_cui_prefix() -> None:
    assert evidence_emitter.validate_artifact_ref({"kind": "preveil", "path": "/CUI/foo.pdf"}) is None
    assert (
        evidence_emitter.validate_artifact_ref({"kind": "preveil", "path": "/public/foo.pdf"})
        is not None
    )


def test_validate_emit_request_rejects_empty_artifacts() -> None:
    reason = evidence_emitter.validate_emit_request(["PS.L2-3.9.1"], "personnel_screening", [])
    assert reason is not None
    assert "empty" in reason.lower()


def test_primary_evidence_uri_prefers_preveil() -> None:
    evidence_id = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeee0001")
    uri = evidence_emitter.primary_evidence_uri(
        [
            {"kind": "drive", "file_id": "1DQqQ_9oem2tirjZoi5g9PBl7Q4_tQSPz"},
            {"kind": "preveil", "path": "/CUI/Personnel-Screening/report.pdf"},
        ],
        evidence_id,
    )
    assert uri == "/CUI/Personnel-Screening/report.pdf"


@pytest.mark.asyncio
async def test_emit_evidence_rejects_invalid_artifacts(monkeypatch) -> None:
    monkeypatch.setenv("MINDEX_DATABASE_URL", "postgresql://example")

    with pytest.raises(ValueError, match="empty"):
        await evidence_emitter.emit_evidence(
            control_ids=["PS.L2-3.9.1"],
            evidence_type="personnel_screening",
            artifact_refs=[],
            actor_subject_id=None,
            verified_at=datetime.now(timezone.utc),
            notes=None,
            operator="test",
            endpoint="/test",
            purpose="test",
        )
