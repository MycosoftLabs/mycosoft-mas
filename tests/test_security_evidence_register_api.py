from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from mycosoft_mas.compliance import evidence_register
from mycosoft_mas.core.routers import security_evidence_api


SAMPLE_REGISTER = """\
| id | control(s) | verdict | artifact (internal path) | sha256 | bytes | signer | signed date | storage | classification |
|---|---|---|---|---|---|---|---|---|---|
| EV-PS-001 | PS.L2-3.9.2 (+ NIST twin 3.9.2) | filed | `docs/cmmc_evidence/ps/agreement.pdf` | `b2a49cec9d291eade0737baa5ba96d6fc9777cb3406b99174884290eab0dc435` | 319846 | RJ Ricasata | 2026-07-15 (DocuSign AC00FC6C-EDA2-84FE-82C7-391A5236C1D9) | internal CODE | UNCLASSIFIED |
| EV-POL-CERT-SC | SC-bundle | PARTIAL | `docs/cmmc_evidence/policies/signed/CERT_SC.pdf` | `17084ceeba34d5ef2c3919eb8cc1de8413444fa53da71ef498f4fff8ba724c14` | 99082 | Morgan Rockcoons | 2026-07-16 | internal CODE | UNCLASSIFIED |
"""


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(security_evidence_api.router)
    return TestClient(app)


def test_parse_register_markdown_extracts_metadata() -> None:
    entries = evidence_register.parse_register_markdown(SAMPLE_REGISTER)
    by_id = {entry["id"]: entry for entry in entries}

    ps = by_id["EV-PS-001"]
    assert ps["controls"] == ["PS.L2-3.9.2", "3.9.2"]
    assert ps["artifact_path"] == "docs/cmmc_evidence/ps/agreement.pdf"
    assert ps["artifact_name"] == "agreement.pdf"
    assert ps["sha256"] == "b2a49cec9d291eade0737baa5ba96d6fc9777cb3406b99174884290eab0dc435"
    assert ps["signer"] == "RJ Ricasata"
    assert ps["storage_tier"] == "internal_repo"
    assert ps["classification"] == "UNCLASSIFIED"
    assert ps["docusign_envelope"] == "AC00FC6C-EDA2-84FE-82C7-391A5236C1D9"


def test_evidence_register_requires_api_key(monkeypatch) -> None:
    monkeypatch.setenv("MYCA_POSTURE_API_KEY", "test-posture-key")

    response = _client().get("/api/security/evidence-register")

    assert response.status_code == 401


def test_evidence_register_returns_metadata_shape(monkeypatch) -> None:
    monkeypatch.setenv("MYCA_POSTURE_API_KEY", "test-posture-key")
    monkeypatch.setattr(
        security_evidence_api,
        "load_evidence_register",
        lambda: {
            "source": "REGISTER.md",
            "register_path": "/tmp/REGISTER.md",
            "count": 1,
            "entries": [
                {
                    "id": "EV-PS-001",
                    "controls": ["PS.L2-3.9.2", "3.9.2"],
                    "artifact_path": "docs/cmmc_evidence/ps/agreement.pdf",
                    "artifact_name": "agreement.pdf",
                    "sha256": "b2a49cec9d291eade0737baa5ba96d6fc9777cb3406b99174884290eab0dc435",
                    "signer": "RJ Ricasata",
                    "storage_tier": "internal_repo",
                    "classification": "UNCLASSIFIED",
                    "docusign_envelope": "AC00FC6C-EDA2-84FE-82C7-391A5236C1D9",
                }
            ],
        },
    )

    response = _client().get(
        "/api/security/evidence-register",
        headers={"X-API-Key": "test-posture-key"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    entry = body["entries"][0]
    assert set(entry.keys()) == {
        "id",
        "controls",
        "artifact_path",
        "artifact_name",
        "sha256",
        "signer",
        "storage_tier",
        "classification",
        "docusign_envelope",
    }
    assert ".pdf" not in response.text or "artifact_path" in response.text
    assert "BEGIN PDF" not in response.text
