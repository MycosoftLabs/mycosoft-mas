from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Set

from fastapi import Header, HTTPException


CLASSIFICATION_ORDER = {
    "UNCLASSIFIED": 0,
    "CUI": 1,
    "SECRET": 2,
    "TS_SCI": 3,
}


@dataclass
class DefenseIdentity:
    subject: str
    clearance: str
    compartments: Set[str]
    is_cac_authenticated: bool


def build_identity(x_subject: str | None, x_clearance: str | None, x_compartments: str | None, x_cac_auth: str | None) -> DefenseIdentity:
    compartments = {c.strip() for c in (x_compartments or "").split(",") if c.strip()}
    return DefenseIdentity(
        subject=x_subject or "unknown",
        clearance=(x_clearance or "UNCLASSIFIED").upper(),
        compartments=compartments,
        is_cac_authenticated=(x_cac_auth or "false").lower() == "true",
    )


def enforce_classification(identity: DefenseIdentity, required: str) -> None:
    if CLASSIFICATION_ORDER.get(identity.clearance, -1) < CLASSIFICATION_ORDER.get(required, 99):
        raise HTTPException(status_code=403, detail="insufficient_clearance")


def enforce_compartments(identity: DefenseIdentity, required_compartments: Iterable[str]) -> None:
    required = {c.strip() for c in required_compartments if c.strip()}
    if required and not required.issubset(identity.compartments):
        raise HTTPException(status_code=403, detail="missing_compartment_access")


def require_defense_identity(
    x_subject: str | None = Header(default=None),
    x_clearance: str | None = Header(default=None),
    x_compartments: str | None = Header(default=None),
    x_cac_auth: str | None = Header(default=None),
) -> DefenseIdentity:
    identity = build_identity(x_subject, x_clearance, x_compartments, x_cac_auth)
    if not identity.is_cac_authenticated:
        raise HTTPException(status_code=401, detail="cac_or_piv_auth_required")
    return identity
