"""Validate n8n workflow JSON and report MAS vs MYCA tree inventory.

Source of truth (do not merge these trees):
* ``n8n/workflows`` — MAS orchestrator workflows (VM 188).
* ``workflows/n8n`` — MYCA personal workflows (VM 191).

These are separate systems. Missing-from-one-side is expected, not drift.
This check fails only on invalid JSON or the same *filename* present in both
trees with a different checksum (accidental overwrite / copy collision).
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MAS_DIR = ROOT / "n8n" / "workflows"
MYCA_DIR = ROOT / "workflows" / "n8n"


def _stable_checksum(data: dict[str, Any], path: Path) -> str:
    stable = {
        "name": data.get("name") or path.stem,
        "id": data.get("id"),
        "nodes": data.get("nodes", []),
        "connections": data.get("connections", {}),
        "settings": data.get("settings", {}),
    }
    encoded = json.dumps(stable, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _index(directory: Path) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    workflows: dict[str, dict[str, Any]] = {}
    errors: list[dict[str, Any]] = []
    if not directory.exists():
        return workflows, [{"path": str(directory.relative_to(ROOT)), "error": "directory_missing"}]
    for path in sorted(directory.glob("*.json")):
        if path.stem.upper() == "MANIFEST":
            continue
        rel = str(path.relative_to(ROOT))
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if not isinstance(data, dict):
                errors.append({"path": rel, "error": "not_an_object"})
                continue
            workflows[path.name] = {
                "name": data.get("name") or path.stem,
                "path": rel,
                "checksum": _stable_checksum(data, path),
            }
        except (OSError, json.JSONDecodeError) as exc:
            errors.append({"path": rel, "error": str(exc)})
    return workflows, errors


def main() -> int:
    mas, mas_errors = _index(MAS_DIR)
    myca, myca_errors = _index(MYCA_DIR)
    collisions: list[dict[str, Any]] = []
    for filename in sorted(set(mas) & set(myca)):
        left = mas[filename]
        right = myca[filename]
        if left["checksum"] != right["checksum"]:
            collisions.append(
                {
                    "filename": filename,
                    "status": "checksum_mismatch",
                    "n8n/workflows": left["path"],
                    "workflows/n8n": right["path"],
                    "left_checksum": left["checksum"],
                    "right_checksum": right["checksum"],
                }
            )

    errors = mas_errors + myca_errors
    report = {
        "ok": not errors and not collisions,
        "policy": "mas_and_myca_n8n_are_separate",
        "directories": {
            "n8n/workflows": {"count": len(mas), "errors": len(mas_errors)},
            "workflows/n8n": {"count": len(myca), "errors": len(myca_errors)},
        },
        "filename_collisions": collisions,
        "errors": errors,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
