"""Evidence gate for CMMC/NIST status decisions.

No practice may be counted as implemented/Met unless a real evidence URI exists
and Morgan Rockcoons (SAO) has validated the artifact. Drafts and templates
remain planned or partial.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

MET_STATUSES = frozenset({"met", "implemented", "yes", "compliant"})


@dataclass(frozen=True)
class EvidenceStatus:
    status: str
    evidence_uri: str | None
    sao_validated: bool
    allowed_met: bool
    reason: str


def evaluate_control_response(value: Any) -> EvidenceStatus:
    if not isinstance(value, Mapping):
        return EvidenceStatus(
            status=str(value).strip().lower(),
            evidence_uri=None,
            sao_validated=False,
            allowed_met=False,
            reason="status_without_structured_evidence",
        )

    status = str(value.get("status", value.get("assessment", "planned"))).strip().lower()
    evidence_uri_value = value.get("evidence_uri")
    evidence_uri = str(evidence_uri_value).strip() if evidence_uri_value else None
    sao_validated = value.get("sao_validated") is True

    if status not in MET_STATUSES:
        return EvidenceStatus(status, evidence_uri, sao_validated, False, "status_not_met")
    if not evidence_uri:
        return EvidenceStatus(status, None, sao_validated, False, "missing_evidence_uri")
    if not sao_validated:
        return EvidenceStatus(status, evidence_uri, False, False, "missing_sao_validation")
    return EvidenceStatus(status, evidence_uri, True, True, "evidence_and_sao_validated")


def is_control_met(value: Any) -> bool:
    return evaluate_control_response(value).allowed_met
