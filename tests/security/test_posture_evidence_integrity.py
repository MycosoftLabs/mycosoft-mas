from __future__ import annotations

import pytest
from fastapi import HTTPException

from mycosoft_mas.core.routers.compliance_api import ControlUpsert, upsert_control
from mycosoft_mas.security.posture_integrity_monitor import _snapshot_from_controls


def test_posture_snapshot_rejects_implemented_control_without_evidence() -> None:
    controls = [
        {
            "control_id": "IR.L2-3.6.3",
            "implementation_state": "implemented",
            "evidence_uri": "",
        }
    ]

    snapshot, reason = _snapshot_from_controls(controls)

    assert snapshot is None
    assert reason is not None
    assert "evidence_uri" in reason


@pytest.mark.asyncio
async def test_implemented_control_requires_evidence_uri(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MINDEX_DATABASE_URL", "postgresql://configured")

    with pytest.raises(HTTPException) as exception_info:
        await upsert_control(
            ControlUpsert(
                control_id="IR.L2-3.6.3",
                implementation_state="implemented",
            )
        )

    assert exception_info.value.status_code == 422
    assert exception_info.value.detail == "implemented controls require a non-empty evidence_uri"
