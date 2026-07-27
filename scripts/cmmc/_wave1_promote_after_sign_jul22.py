#!/usr/bin/env python3
"""Promote Wave 1 CMMC controls to implemented ONLY when Rev A gates pass.

Rev A gates (ALL required):
  1. SIGNED PDF exists on disk
  2. sha256 in WAVE1_SIGNED matches file hash
  3. REGISTER.md contains the register_id row
  4. register_id visible via GET /api/security/evidence-register (X-API-Key)
  5. Then flip CMMC-L2 + NIST twin rows with evidence_uri pattern:
     doc:cmmc_evidence/<family>/<signed_pdf>#<register_id>

DO NOT RUN until Morgan Rockcoons has signed all four artifacts and filed PDFs under
docs/cmmc_evidence/<family>/.

Controls (sign order):
  1. EV-AC-002 — AC.L2-3.1.22 / NIST 3.1.22
  2. EV-CM-001 — CM.L2-3.4.1 / NIST 3.4.1
  3. EV-AC-003 — AC.L2-3.1.4 / NIST 3.1.4
  4. EV-AC-004 — AC.L2-3.1.3 / NIST 3.1.3

IR EV-IR-001 is NOT in this script — promote separately after tabletop AAR is signed.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

MAS_API = os.getenv("MAS_API_URL", "http://192.168.0.188:8001").rstrip("/")
MAS_ROOT = Path(__file__).resolve().parents[2]
CODE_ROOT = MAS_ROOT.parent.parent
EVIDENCE_ROOT = CODE_ROOT / "docs" / "cmmc_evidence"
REGISTER_MD = EVIDENCE_ROOT / "REGISTER.md"
REGISTER_JSON = EVIDENCE_ROOT / "REGISTER.json"
BACKUP_DIR = EVIDENCE_ROOT

# After Morgan signs, fill sha256 from: Get-FileHash <pdf> -Algorithm SHA256
WAVE1_SIGNED: list[dict] = [
    {
        "register_id": "EV-AC-002",
        "control_ids": ("AC.L2-3.1.22", "3.1.22"),
        "evidence_uri": "doc:cmmc_evidence/ac/EV-AC-3.1.22_findings_SIGNED_JUL22_2026.pdf#EV-AC-002",
        "pdf": EVIDENCE_ROOT / "ac" / "EV-AC-3.1.22_findings_SIGNED_JUL22_2026.pdf",
        "sha256": "c07ce5f77ca1c3e4c73095122fe00cec33f303129d2f2315ff9c8853252068e4",
        "signer": "Morgan Rockcoons (SAO)",
        "signed_date": "2026-07-22",
    },
    {
        "register_id": "EV-CM-001",
        "control_ids": ("CM.L2-3.4.1", "3.4.1"),
        "evidence_uri": "doc:cmmc_evidence/cm/EV-CM-3.4.1_asset_inventory_SIGNED_JUL22_2026.pdf#EV-CM-001",
        "pdf": EVIDENCE_ROOT / "cm" / "EV-CM-3.4.1_asset_inventory_SIGNED_JUL22_2026.pdf",
        "sha256": "4fa012cb082b3f635eba3e370d26e9bfe718a26948f6faa376ae4903be51b2c9",
        "signer": "Morgan Rockcoons (SAO)",
        "signed_date": "2026-07-22",
    },
    {
        "register_id": "EV-AC-003",
        "control_ids": ("AC.L2-3.1.4", "3.1.4"),
        "evidence_uri": "doc:cmmc_evidence/ac/EV-AC-3.1.4_duty_separation_SIGNED_JUL22_2026.pdf#EV-AC-003",
        "pdf": EVIDENCE_ROOT / "ac" / "EV-AC-3.1.4_duty_separation_SIGNED_JUL22_2026.pdf",
        "sha256": "098f0f7adbc0a5b1bbb5cc8bf6a1c94501fafc566d01cbb7dc55a26c44615e34",
        "signer": "Morgan Rockcoons (SAO) + RJ Ricasata (ack)",
        "signed_date": "2026-07-22",
    },
    {
        "register_id": "EV-AC-004",
        "control_ids": ("AC.L2-3.1.3", "3.1.3"),
        "evidence_uri": "doc:cmmc_evidence/ac/EV-AC-3.1.3_cui_flow_SIGNED_JUL22_2026.pdf#EV-AC-004",
        "pdf": EVIDENCE_ROOT / "ac" / "EV-AC-3.1.3_cui_flow_SIGNED_JUL22_2026.pdf",
        "sha256": "713180c591675758f0d712c9d4b9ff2679613cff933fbb7860c64592dbb82660",
        "signer": "Morgan Rockcoons (SAO)",
        "signed_date": "2026-07-22",
    },
]


def _load_credentials() -> None:
    creds = MAS_ROOT / ".credentials.local"
    if not creds.is_file():
        return
    for line in creds.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _verify_register_markdown(items: list[dict]) -> None:
    if not REGISTER_MD.is_file():
        raise FileNotFoundError(f"Missing register: {REGISTER_MD}")
    content = REGISTER_MD.read_text(encoding="utf-8")
    for item in items:
        rid = item["register_id"]
        if rid not in content:
            raise ValueError(f"REGISTER.md missing entry for {rid}")


def _regenerate_register_json() -> None:
    script = MAS_ROOT / "scripts" / "cmmc" / "_regenerate_register_json_jul22.py"
    if not script.is_file():
        raise FileNotFoundError(f"Missing regenerate script: {script}")
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(MAS_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"REGISTER.json regeneration failed:\n{result.stdout}\n{result.stderr}"
        )
    print(result.stdout.strip())


async def _verify_api_visibility(items: list[dict]) -> None:
    api_key = os.getenv("MYCA_POSTURE_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "MYCA_POSTURE_API_KEY not set — required to verify evidence-register API"
        )

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{MAS_API}/api/security/evidence-register",
            headers={"X-API-Key": api_key},
        )
        if resp.status_code == 401:
            raise PermissionError("evidence-register returned 401 — check MYCA_POSTURE_API_KEY")
        resp.raise_for_status()
        payload = resp.json()
        api_ids = {entry.get("id") for entry in payload.get("entries", [])}
        missing = [item["register_id"] for item in items if item["register_id"] not in api_ids]
        if missing:
            raise ValueError(
                f"evidence-register API missing ids: {', '.join(missing)} — "
                "sync REGISTER to 188 and restart mas-orchestrator first"
            )
        print(
            f"evidence-register API OK — {payload.get('count', len(api_ids))} entries; "
            f"wave1 ids present: {', '.join(i['register_id'] for i in items)}"
        )


def _verify_signed_artifacts() -> list[dict]:
    verified: list[dict] = []
    for item in WAVE1_SIGNED:
        pdf = Path(item["pdf"])
        if not pdf.is_file():
            raise FileNotFoundError(f"Missing signed PDF: {pdf}")
        expected = (item.get("sha256") or "").strip().lower()
        if not expected:
            raise ValueError(
                f"sha256 not set for {item['register_id']} — "
                f"compute with Get-FileHash and update WAVE1_SIGNED before run"
            )
        actual = _sha256_file(pdf)
        if actual != expected:
            raise ValueError(
                f"sha256 mismatch for {item['register_id']}: expected {expected}, got {actual}"
            )
        verified.append({**item, "bytes": pdf.stat().st_size, "sha256_verified": actual})
    return verified


def _merge_snapshot(existing: dict, item: dict) -> dict:
    merged = dict(existing or {})
    current_state = dict(merged.get("current_state") or {})
    current_state.update(
        {
            "as_of": datetime.now(timezone.utc).isoformat(),
            "implementation_state": "implemented",
            "evidence_uri": item["evidence_uri"],
            "notes": f"Current implementation verified via {item['evidence_uri']}.",
        }
    )
    merged["current_state"] = current_state
    merged["evidence_register_id"] = item["register_id"]
    merged["evidence"] = {
        "register_id": item["register_id"],
        "artifact": str(item["pdf"].relative_to(CODE_ROOT)).replace("\\", "/"),
        "sha256": item["sha256_verified"],
        "bytes": item["bytes"],
        "signer": item["signer"],
        "signed_date": item["signed_date"],
    }
    merged["flip_source"] = "cursor_wave1_promote_after_sign_jul22_2026_rev_a"
    merged["flip_at"] = datetime.now(timezone.utc).date().isoformat()
    merged["note"] = f"SAO-signed Wave 1 artifact filed. Met via {item['evidence_uri']}."
    return merged


async def main() -> None:
    _load_credentials()
    verified = _verify_signed_artifacts()
    _verify_register_markdown(verified)
    _regenerate_register_json()
    await _verify_api_visibility(verified)
    print(f"Verified {len(verified)} signed PDFs — proceeding to soc_ops promotion")

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{MAS_API}/api/compliance/controls")
        resp.raise_for_status()
        controls = {c["control_id"]: c for c in resp.json().get("controls", [])}

        backup_rows: list[dict] = []
        updated: list[str] = []

        for item in verified:
            for cid in item["control_ids"]:
                if cid not in controls:
                    raise RuntimeError(f"Control not found in soc_ops: {cid}")
                backup_rows.append(controls[cid])

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_path = BACKUP_DIR / f"soc_ops_wave1_flip_backup_{ts}.json"
        backup_path.write_text(json.dumps(backup_rows, indent=2), encoding="utf-8")
        print(f"Backup: {backup_path}")

        for item in verified:
            for cid in item["control_ids"]:
                row = controls[cid]
                body = {
                    "control_id": row["control_id"],
                    "framework": row["framework"],
                    "family": row.get("family"),
                    "title": row.get("title"),
                    "implementation_state": "implemented",
                    "evidence_uri": item["evidence_uri"],
                    "state_snapshot": _merge_snapshot(row.get("state_snapshot") or {}, item),
                }
                up = await client.post(f"{MAS_API}/api/compliance/controls", json=body)
                up.raise_for_status()
                updated.append(row["control_id"])

        score = await client.get(f"{MAS_API}/api/compliance/score")
        score.raise_for_status()
        print("Updated:", ", ".join(updated))
        print("Score:", json.dumps(score.json()))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (FileNotFoundError, ValueError, PermissionError, RuntimeError) as exc:
        print(f"ABORT — honesty gate: {exc}", file=sys.stderr)
        sys.exit(1)
