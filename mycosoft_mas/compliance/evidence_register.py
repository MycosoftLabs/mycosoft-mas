"""
CMMC evidence register reader — metadata only (no file bodies).

Prefers REGISTER.json sidecar when present; otherwise parses REGISTER.md tables.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Literal, Optional

StorageTier = Literal["preveil", "internal_repo", "google_drive", "public_repo"]

_CONTROL_RE = re.compile(
    r"(?:[A-Z]{2}\.)?L2-\d+(?:\.\d+)+|\b\d+\.\d+(?:\.\d+)+\b"
)
_SHA256_RE = re.compile(r"\b([a-fA-F0-9]{64})\b")
_ENVELOPE_UUID_RE = re.compile(
    r"\b([A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12})\b",
    re.IGNORECASE,
)
_ENVELOPE_HEX_RE = re.compile(r"\b([A-F0-9]{32})\b", re.IGNORECASE)
_BACKTICK_PATH_RE = re.compile(r"`([^`]+)`")


def resolve_register_markdown_path() -> Optional[Path]:
    explicit = os.getenv("CMMC_EVIDENCE_REGISTER_PATH", "").strip()
    if explicit:
        return Path(explicit)

    candidates: list[Path] = []
    code_root = os.getenv("CODE_ROOT", "").strip()
    if code_root:
        candidates.append(Path(code_root) / "docs" / "cmmc_evidence" / "REGISTER.md")

    mas_root = Path(__file__).resolve().parents[2]
    candidates.extend(
        [
            mas_root.parent.parent / "docs" / "cmmc_evidence" / "REGISTER.md",
            Path("/opt/mycosoft/CODE/docs/cmmc_evidence/REGISTER.md"),
            Path("/home/mycosoft/CODE/docs/cmmc_evidence/REGISTER.md"),
            Path("/home/mycosoft/mycosoft/CODE/docs/cmmc_evidence/REGISTER.md"),
        ]
    )

    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def resolve_register_json_path(markdown_path: Optional[Path]) -> Optional[Path]:
    explicit_json = os.getenv("CMMC_EVIDENCE_REGISTER_JSON", "").strip()
    if explicit_json:
        path = Path(explicit_json)
        return path if path.is_file() else None
    if markdown_path is not None:
        sidecar = markdown_path.parent / "REGISTER.json"
        if sidecar.is_file():
            return sidecar
    return None


def infer_storage_tier(storage_text: str, artifact_text: str) -> StorageTier:
    combined = f"{storage_text} {artifact_text}".lower()
    if "preveil" in combined:
        return "preveil"
    if "google" in combined and "drive" in combined:
        return "google_drive"
    if "public" in combined and "repo" in combined:
        return "public_repo"
    return "internal_repo"


def extract_controls(text: str) -> list[str]:
    seen: set[str] = set()
    controls: list[str] = []
    for match in _CONTROL_RE.findall(text or ""):
        token = match.strip()
        if token and token not in seen:
            seen.add(token)
            controls.append(token)
    return controls


def extract_sha256(text: str) -> Optional[str]:
    match = _SHA256_RE.search(text or "")
    return match.group(1).lower() if match else None


def extract_docusign_envelope(*texts: str) -> Optional[str]:
    for text in texts:
        if not text:
            continue
        match = _ENVELOPE_UUID_RE.search(text)
        if match:
            return match.group(1).upper()
        match = _ENVELOPE_HEX_RE.search(text)
        if match and "envelope" in text.lower():
            return match.group(1).upper()
    return None


def extract_artifact_path(text: str) -> Optional[str]:
    if not text:
        return None
    for match in _BACKTICK_PATH_RE.finditer(text):
        candidate = match.group(1).strip()
        if "/" in candidate or candidate.endswith((".pdf", ".md", ".png", ".jpg")):
            return candidate
    stripped = text.strip().strip("`")
    if stripped and not stripped.startswith("http"):
        first = stripped.split("+")[0].split(",")[0].strip()
        if first:
            return first
    return None


def artifact_name_from_path(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    return Path(path.replace("\\", "/")).name


def _parse_table_rows(content: str) -> list[tuple[list[str], dict[str, str]]]:
    """Return (header_cells, {header: value}) for each data row in markdown tables."""
    rows: list[tuple[list[str], dict[str, str]]] = []
    lines = content.splitlines()
    idx = 0
    while idx < len(lines):
        line = lines[idx].strip()
        if not line.startswith("|") or "id" not in line.lower():
            idx += 1
            continue

        header = [cell.strip().lower() for cell in line.strip("|").split("|")]
        idx += 1
        if idx < len(lines) and set(lines[idx].replace("|", "").replace("-", "").strip()) <= {""}:
            idx += 1

        while idx < len(lines):
            row_line = lines[idx].strip()
            if not row_line.startswith("|"):
                break
            cells = [cell.strip() for cell in row_line.strip("|").split("|")]
            if len(cells) < len(header):
                cells.extend([""] * (len(header) - len(cells)))
            row_map = {header[i]: cells[i] for i in range(len(header))}
            if row_map.get("id"):
                rows.append((header, row_map))
            idx += 1
    return rows


def _entry_from_row(header: list[str], row: dict[str, str]) -> Optional[dict[str, Any]]:
    entry_id = row.get("id", "").strip()
    if not entry_id:
        return None

    controls_col = row.get("control(s)", "") or row.get("family / controls (concepts)", "")
    artifact_col = row.get("artifact (internal path)", "") or row.get("artifact", "")
    artifact_path = extract_artifact_path(artifact_col)
    storage_col = row.get("storage", "")
    classification_col = row.get("classification", "UNCLASSIFIED")
    signer_col = row.get("signer", "")
    sha_col = row.get("sha256", "")
    envelope_col = row.get("envelope", "")

    envelope = extract_docusign_envelope(envelope_col, row.get("signed date", ""), row.get("verdict", ""), artifact_col)
    if not envelope:
        envelope = extract_docusign_envelope(signer_col)

    return {
        "id": entry_id,
        "controls": extract_controls(controls_col),
        "artifact_path": artifact_path,
        "artifact_name": artifact_name_from_path(artifact_path),
        "sha256": extract_sha256(sha_col),
        "signer": signer_col or None,
        "storage_tier": infer_storage_tier(storage_col, artifact_col),
        "classification": classification_col.strip() or "UNCLASSIFIED",
        "docusign_envelope": envelope,
    }


def enrich_envelopes_from_register(content: str, entries: list[dict[str, Any]]) -> None:
    for entry in entries:
        if entry.get("docusign_envelope"):
            continue
        marker = 0
        envelope: Optional[str] = None
        while True:
            idx = content.find(entry["id"], marker)
            if idx == -1:
                break
            snippet = content[idx : idx + 2500]
            envelope = extract_docusign_envelope(snippet)
            if envelope:
                break
            marker = idx + len(entry["id"])
        if envelope:
            entry["docusign_envelope"] = envelope


def parse_register_markdown(content: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for header, row in _parse_table_rows(content):
        entry = _entry_from_row(header, row)
        if entry and entry["id"] not in seen_ids:
            seen_ids.add(entry["id"])
            entries.append(entry)
    enrich_envelopes_from_register(content, entries)
    return entries


def load_register_json(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("entries"), list):
        raw_entries = payload["entries"]
    elif isinstance(payload, list):
        raw_entries = payload
    else:
        raise ValueError("REGISTER.json must be a list or {entries: [...]}")
    return [_normalize_json_entry(item) for item in raw_entries]


def _normalize_json_entry(item: dict[str, Any]) -> dict[str, Any]:
    artifact_path = item.get("artifact_path") or item.get("artifact")
    storage_tier = item.get("storage_tier", "internal_repo")
    if storage_tier not in {"preveil", "internal_repo", "google_drive", "public_repo"}:
        storage_tier = infer_storage_tier(str(item.get("storage", "")), str(artifact_path or ""))
    return {
        "id": item["id"],
        "controls": list(item.get("controls") or []),
        "artifact_path": artifact_path,
        "artifact_name": item.get("artifact_name") or artifact_name_from_path(str(artifact_path or "")),
        "sha256": (item.get("sha256") or "").lower() or None,
        "signer": item.get("signer"),
        "storage_tier": storage_tier,
        "classification": item.get("classification") or "UNCLASSIFIED",
        "docusign_envelope": item.get("docusign_envelope"),
    }


def load_evidence_register() -> dict[str, Any]:
    markdown_path = resolve_register_markdown_path()
    json_path = resolve_register_json_path(markdown_path)

    if json_path is not None:
        entries = load_register_json(json_path)
        return {
            "source": "REGISTER.json",
            "register_path": str(json_path),
            "count": len(entries),
            "entries": entries,
        }

    if markdown_path is None:
        raise FileNotFoundError("CMMC evidence register not found (set CMMC_EVIDENCE_REGISTER_PATH)")

    content = markdown_path.read_text(encoding="utf-8")
    entries = parse_register_markdown(content)
    return {
        "source": "REGISTER.md",
        "register_path": str(markdown_path),
        "count": len(entries),
        "entries": entries,
    }
