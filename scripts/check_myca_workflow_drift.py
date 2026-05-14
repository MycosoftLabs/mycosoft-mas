"""Check and optionally sync MYCA n8n workflow drift.

Source of truth policy:
* ``n8n/workflows`` is the canonical workflow library.
* ``workflows/n8n`` is the local import/deployment mirror.
* Existing mirror-only MYCA workflows are promoted into canonical during sync.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_DIR = ROOT / "n8n" / "workflows"
MIRROR_DIR = ROOT / "workflows" / "n8n"
CANONICAL_DIRS = [CANONICAL_DIR, MIRROR_DIR]


def _load_workflow(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    stable = {
        "name": data.get("name") or path.stem,
        "id": data.get("id"),
        "nodes": data.get("nodes", []),
        "connections": data.get("connections", {}),
        "settings": data.get("settings", {}),
        "trigger_count": sum(
            1
            for node in data.get("nodes", [])
            if "trigger" in str(node.get("type", "")).lower()
            or "webhook" in str(node.get("type", "")).lower()
        ),
    }
    encoded = json.dumps(stable, sort_keys=True, separators=(",", ":")).encode("utf-8")
    stable["checksum"] = hashlib.sha256(encoded).hexdigest()
    return stable


def _index(directory: Path) -> dict[str, dict[str, Any]]:
    workflows = {}
    for path in sorted(directory.glob("*.json")):
        if path.stem.upper() == "MANIFEST":
            continue
        data = _load_workflow(path)
        key = str(data.get("name") or path.stem)
        workflows[key] = {**data, "path": str(path.relative_to(ROOT))}
    return workflows


def sync_workflow_trees() -> None:
    """Promote mirror-only workflows into canonical, then mirror canonical files."""
    CANONICAL_DIR.mkdir(parents=True, exist_ok=True)
    MIRROR_DIR.mkdir(parents=True, exist_ok=True)

    canonical_names = {path.name for path in CANONICAL_DIR.glob("*.json")}
    for source in sorted(MIRROR_DIR.glob("*.json")):
        if source.stem.upper() == "MANIFEST":
            continue
        if source.name not in canonical_names:
            shutil.copy2(source, CANONICAL_DIR / source.name)

    for source in sorted(CANONICAL_DIR.glob("*.json")):
        if source.stem.upper() == "MANIFEST":
            continue
        shutil.copy2(source, MIRROR_DIR / source.name)


def main() -> int:
    if "--sync" in sys.argv:
        sync_workflow_trees()

    indexes = [_index(directory) for directory in CANONICAL_DIRS]
    names = set(indexes[0]) | set(indexes[1])
    drift: list[dict[str, Any]] = []
    for name in sorted(names):
        left = indexes[0].get(name)
        right = indexes[1].get(name)
        if not left or not right:
            drift.append(
                {
                    "workflow": name,
                    "status": "missing",
                    "n8n/workflows": bool(left),
                    "workflows/n8n": bool(right),
                }
            )
            continue
        if left["checksum"] != right["checksum"]:
            drift.append(
                {
                    "workflow": name,
                    "status": "changed",
                    "n8n/workflows": left["path"],
                    "workflows/n8n": right["path"],
                    "left_checksum": left["checksum"],
                    "right_checksum": right["checksum"],
                }
            )

    report = {
        "ok": not drift,
        "directories": [str(path.relative_to(ROOT)) for path in CANONICAL_DIRS],
        "drift": drift,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not drift else 1


if __name__ == "__main__":
    sys.exit(main())
