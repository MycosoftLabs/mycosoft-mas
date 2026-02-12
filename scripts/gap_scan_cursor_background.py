"""
Gap scan for Cursor background — writes latest report to .cursor/gap_report_latest.json.

Runs a full workspace scan (all known Mycosoft repos) plus index-based scan using
docs/MASTER_DOCUMENT_INDEX.md so "missing work in indexed files" is included.

If MAS gap API is available, its results are merged with local workspace findings.

Usage:
  python scripts/gap_scan_cursor_background.py

Optional env:
  MAS_API_URL            default http://192.168.0.188:8001
  GAP_REPORT_PATH        default .cursor/gap_report_latest.json (relative to MAS repo root)
  GAP_SKIP_INDEX         set to 1 to skip index-based scan
  GAP_SCAN_EXTRA_ROOTS   semicolon-separated absolute paths to additional roots
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

# Repo root = parent of scripts/
REPO_ROOT = Path(__file__).resolve().parents[1]
CURSOR_DIR = REPO_ROOT / ".cursor"
DEFAULT_REPORT_PATH = CURSOR_DIR / "gap_report_latest.json"
MAS_URL = os.environ.get("MAS_API_URL", "http://192.168.0.188:8001").rstrip("/")
REPORT_PATH = Path(os.environ.get("GAP_REPORT_PATH", str(DEFAULT_REPORT_PATH))).resolve()
if not REPORT_PATH.is_absolute():
    REPORT_PATH = REPO_ROOT / REPORT_PATH

# Workspace root: parent of MAS folder (e.g. CODE containing MAS, WEBSITE, MINDEX, ...)
CODE_ROOT = REPO_ROOT.parent.parent
KNOWN_REPOS = {
    "mas": REPO_ROOT,
    "website": CODE_ROOT / "WEBSITE" / "website",
    "mindex": CODE_ROOT / "MINDEX" / "mindex",
    "mycobrain": CODE_ROOT / "mycobrain",
    "natureos": CODE_ROOT / "NATUREOS" / "NatureOS",
    "mycorrhizae": CODE_ROOT / "Mycorrhizae",
    "nlm": CODE_ROOT / "MAS" / "NLM",
    "sdk": CODE_ROOT / "MAS" / "sdk",
    "platform-infra": CODE_ROOT / "platform-infra",
}

SKIP_DIRS = {
    ".git",
    ".next",
    ".nuxt",
    "node_modules",
    "dist",
    "build",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".coverage",
    ".pio",
    ".idea",
    ".vscode",
    "coverage",
    ".turbo",
}

TODO_PATTERN = re.compile(r"(TODO|FIXME|XXX|HACK|BUG)\s*[:\-]?\s*(.+)", re.I)
STUB_PATTERN = re.compile(
    r"NotImplementedError|placeholder|stub implementation|return\s+\{\s*['\"]status['\"]:\s*['\"]success['\"]\s*\}",
    re.I,
)
ROUTES_501_PATTERN = re.compile(r"501|Not\s+implemented|NotImplementedError", re.I)
BRIDGE_HINT_PATTERN = re.compile(r"bridge|integration", re.I)
BRIDGE_GAP_PATTERN = re.compile(r"missing|gap|not\s+implemented|pending", re.I)


def fetch_from_mas() -> dict | None:
    try:
        import urllib.request
        req = urllib.request.Request(
            f"{MAS_URL}/agents/gap/scan?full=false",
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            return data.get("result") or data
    except Exception:
        return None


def _iter_files(root: Path, suffixes: tuple[str, ...]):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in suffixes:
            continue
        yield path


def _scan_todos(root: Path, repo: str, limit: int = 200) -> list[dict[str, Any]]:
    out = []
    for path in _iter_files(root, (".py", ".ts", ".tsx", ".js", ".md", ".cs", ".cpp", ".h")):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        rel = path.relative_to(root)
        for i, line in enumerate(text.splitlines(), 1):
            if len(out) >= limit:
                return out
            m = TODO_PATTERN.search(line)
            if m:
                out.append({
                    "file": str(rel),
                    "line_no": i,
                    "line": line.strip()[:180],
                    "kind": m.group(1).upper(),
                    "message": (m.group(2) or "").strip()[:150],
                    "repo": repo,
                })
    return out


def _scan_stubs(root: Path, repo: str, limit: int = 120) -> list[dict[str, Any]]:
    out = []
    for path in _iter_files(root, (".py", ".ts", ".tsx", ".js", ".cs", ".md")):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if not STUB_PATTERN.search(text):
            continue
        rel = path.relative_to(root)
        for i, line in enumerate(text.splitlines(), 1):
            if len(out) >= limit:
                return out
            if STUB_PATTERN.search(line):
                out.append({
                    "file": str(rel),
                    "line_no": i,
                    "snippet": line.strip()[:180],
                    "repo": repo,
                })
    return out


def _scan_501(root: Path, repo: str, limit: int = 120) -> list[dict[str, Any]]:
    out = []
    for path in _iter_files(root, (".py", ".ts", ".tsx", ".js", ".cs")):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if not ROUTES_501_PATTERN.search(text):
            continue
        rel = path.relative_to(root)
        for i, line in enumerate(text.splitlines(), 1):
            if len(out) >= limit:
                return out
            if ROUTES_501_PATTERN.search(line):
                out.append({"file": str(rel), "line_no": i, "line": line.strip()[:180], "repo": repo})
    return out


def _scan_bridge_gaps(root: Path, repo: str, limit: int = 40) -> list[dict[str, Any]]:
    out = []
    docs_root = root / "docs"
    if not docs_root.exists():
        return out
    for path in _iter_files(docs_root, (".md",)):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if not BRIDGE_HINT_PATTERN.search(text):
            continue
        if not BRIDGE_GAP_PATTERN.search(text):
            continue
        out.append(
            {
                "type": "bridge_gap",
                "file": str(path.relative_to(root)),
                "repo": repo,
                "hint": "Doc mentions bridge/integration and missing/gap; consider adding a bridge service or API.",
            }
        )
        if len(out) >= limit:
            return out
    return out


def _workspace_roots() -> dict[str, Path]:
    roots: dict[str, Path] = {}
    for name, path in KNOWN_REPOS.items():
        if path.exists():
            roots[name] = path.resolve()

    extra = os.environ.get("GAP_SCAN_EXTRA_ROOTS", "").strip()
    if extra:
        for idx, raw in enumerate(extra.split(";"), start=1):
            raw = raw.strip()
            if not raw:
                continue
            p = Path(raw)
            if p.exists():
                roots[f"extra-{idx}"] = p.resolve()
    return roots


def local_scan() -> dict[str, Any]:
    roots = _workspace_roots()
    todos: list[dict[str, Any]] = []
    stubs: list[dict[str, Any]] = []
    routes_501: list[dict[str, Any]] = []
    bridge_gaps: list[dict[str, Any]] = []
    by_repo: dict[str, dict[str, int]] = {}

    for repo, root in roots.items():
        repo_todos = _scan_todos(root, repo)
        repo_stubs = _scan_stubs(root, repo)
        repo_501 = _scan_501(root, repo)
        repo_bridges = _scan_bridge_gaps(root, repo)

        todos.extend(repo_todos)
        stubs.extend(repo_stubs)
        routes_501.extend(repo_501)
        bridge_gaps.extend(repo_bridges)
        by_repo[repo] = {
            "todos_fixmes_count": len(repo_todos),
            "stubs_count": len(repo_stubs),
            "routes_501_count": len(repo_501),
            "bridge_gaps_count": len(repo_bridges),
        }

    suggested_plans = []
    if todos:
        suggested_plans.append(
            {
                "title": "Address TODOs/FIXMEs",
                "description": f"Resolve or triage {len(todos)} items across workspace repos.",
                "priority": "medium",
            }
        )
    if stubs:
        suggested_plans.append(
            {
                "title": "Replace stubs with implementations",
                "description": f"Replace or document {len(stubs)} stub/placeholder usages.",
                "priority": "medium",
            }
        )
    if routes_501:
        suggested_plans.append(
            {
                "title": "Implement 501 routes",
                "description": f"Implement {len(routes_501)} API routes currently returning 501/not implemented.",
                "priority": "high",
            }
        )
    if bridge_gaps:
        suggested_plans.append(
            {
                "title": "Add missing bridges between systems",
                "description": "Implement integration layer or API bridge where docs indicate a missing connection.",
                "priority": "high",
            }
        )
    return {
        "workspace_roots": [str(root) for root in roots.values()],
        "todos_fixmes": todos,
        "stubs": stubs,
        "routes_501": routes_501,
        "bridge_gaps": bridge_gaps,
        "suggested_plans": suggested_plans,
        "by_repo": by_repo,
        "summary": {
            "todos_fixmes_count": len(todos),
            "stubs_count": len(stubs),
            "routes_501_count": len(routes_501),
            "bridge_gaps_count": len(bridge_gaps),
            "plans_suggested": len(suggested_plans),
        },
        "source": "local_workspace_scan",
    }


def _merge_reports(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    merged["workspace_roots"] = list(
        dict.fromkeys([*(base.get("workspace_roots") or []), *(extra.get("workspace_roots") or [])])
    )
    for key in ("todos_fixmes", "stubs", "routes_501", "bridge_gaps", "suggested_plans"):
        merged[key] = [*(base.get(key) or []), *(extra.get(key) or [])]
    merged["by_repo"] = {**(base.get("by_repo") or {}), **(extra.get("by_repo") or {})}
    merged["summary"] = {
        "todos_fixmes_count": len(merged["todos_fixmes"]),
        "stubs_count": len(merged["stubs"]),
        "routes_501_count": len(merged["routes_501"]),
        "bridge_gaps_count": len(merged["bridge_gaps"]),
        "plans_suggested": len(merged["suggested_plans"]),
    }
    return merged


def run_index_scan() -> dict | None:
    """Run index-based gap scan and return report dict, or None on failure."""
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "gap_scan_cursor_index.py")],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0 and (CURSOR_DIR / "gap_report_index.json").exists():
            return json.loads((CURSOR_DIR / "gap_report_index.json").read_text(encoding="utf-8"))
    except Exception:
        pass
    return None


def main() -> int:
    mas_report = fetch_from_mas()
    local_report = local_scan()
    if mas_report is None:
        report = local_report
    else:
        report = _merge_reports(mas_report, local_report)
        report["source"] = "mas_api+local_workspace_scan"

    # Merge index-based missing work (files referenced in MASTER_DOCUMENT_INDEX with gaps)
    if os.environ.get("GAP_SKIP_INDEX") != "1":
        index_report = run_index_scan()
        if index_report:
            report["index_gaps"] = index_report
            summary = report.get("summary", {})
            summary["index_files_with_gaps"] = index_report.get("files_with_gaps", 0)
            summary["index_gaps_total"] = index_report.get("summary", {}).get("index_gaps_total", 0)
            report["summary"] = summary

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    idx = f", index_gaps={report.get('index_gaps', {}).get('files_with_gaps', 0)} files" if report.get("index_gaps") else ""
    print(f"Wrote gap report to {REPORT_PATH} ({report.get('source', 'unknown')}{idx})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
