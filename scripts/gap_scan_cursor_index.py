"""
Index-based gap scan for Cursor development.

Uses docs/MASTER_DOCUMENT_INDEX.md (and optionally other indexes) to find all
referenced files, then scans those files for missing work:
- TODO / FIXME / XXX / HACK
- Status: not started | pending | blocked
- Unchecked list items: - [ ]
- 501 / Not implemented / NotImplementedError
- stub / placeholder (in comments or docstrings)

Filters out false positives: files that DESCRIBE gaps (like GAP_AGENT docs) 
rather than containing actual incomplete work.

Writes .cursor/gap_report_index.json so the Gap Agent and Cursor can surface
"missing work in indexed files" during development.

Usage:
  python scripts/gap_scan_cursor_index.py

Optional env:
  GAP_INDEX_REPORT_PATH — default .cursor/gap_report_index.json
  MAS_REPO_ROOT — repo root (default: parent of scripts/)
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CURSOR_DIR = REPO_ROOT / ".cursor"
DOCS_DIR = REPO_ROOT / "docs"
DEFAULT_INDEX_REPORT = CURSOR_DIR / "gap_report_index.json"
REPORT_PATH = Path(
    os.environ.get("GAP_INDEX_REPORT_PATH", str(DEFAULT_INDEX_REPORT))
).resolve()
if not REPORT_PATH.is_absolute():
    REPORT_PATH = REPO_ROOT / REPORT_PATH

# Files that DESCRIBE gaps but don't contain actual incomplete work
# These are documentation about the gap-finding system itself, or scanner code
EXCLUDE_FILE_PATTERNS = [
    "GAP_AGENT_",              # Doc about the gap agent
    "PHASE1_AGENT_RUNTIME_",   # Doc about clearing stubs (describes past work)
    "PHASE1_COMPLETION_",      # Completion report (describes what was done)
    "AGENT_REGISTRY_FULL_",    # Registry listing agents (stub column is info, not TODO)
    "WORK_TODOS_GAPS_",        # Meta-doc consolidating gaps (describes gaps)
    "PHYSICSNEMO_",            # PhysicsNemo doc (mentions 501 as example)
    "VISION_VS_IMPLEMENTATION_", # Gap analysis doc (describes gaps by design)
    "SYSTEM_GAPS_AND_REMAINING", # Meta-doc summarizing all gaps
    "gap_scan_cursor",         # Scanner scripts themselves (code that scans for gaps)
]

# Line-level patterns that indicate the line is DESCRIBING gaps, not a real gap
# These patterns indicate documentation about gap types, not actual TODOs
FALSE_POSITIVE_LINE_PATTERNS = [
    re.compile(r"finds?\s+(TODO|FIXME|stub|501)", re.I),  # "finds TODOs"
    re.compile(r"(TODO|FIXME|stub|501)\s+pattern", re.I),  # "TODO pattern"
    re.compile(r"scan\s+for\s+(TODO|FIXME|stub)", re.I),  # "scan for TODOs"
    re.compile(r"(detect|find|search|look)\s+(for\s+)?(TODO|FIXME|stub)", re.I),
    re.compile(r"marker[s]?\s*[:=]\s*(TODO|FIXME|stub)", re.I),  # "markers: TODO"
    re.compile(r"\|\s*(TODO|FIXME|stub|501)\s*\|", re.I),  # Table cells listing types
    re.compile(r"^\s*-\s*(TODO|FIXME|stub|501)\s*[-/]", re.I),  # Bullet list of types
    re.compile(r"kind[s]?\s*[:=].*(TODO|FIXME|stub|501)", re.I),  # "kinds: TODO, FIXME"
    re.compile(r'["\'](?:todo_fixme|stub|501|stubs)["\']', re.I),  # String literals like "todo_fixme"
    re.compile(r"GAP_PATTERNS|gap.?pattern|false.?positive", re.I),  # Code/config about patterns
    re.compile(r"Status:\s*\*\*", re.I),  # Bold status in table (describing, not actual)
    re.compile(r"stub.?column|todo.?column|fixme.?column", re.I),  # Describing columns
    re.compile(r"todos_fixmes|routes_501|stubs_count", re.I),  # Variable names in scanner code
    re.compile(r"_scan_todos|_scan_stubs|_scan_501", re.I),  # Function names in scanner code
    re.compile(r"STUB_PATTERN|TODO_PATTERN|ROUTES_501_PATTERN", re.I),  # Regex pattern names
    re.compile(r"repo_todos|repo_stubs|repo_501", re.I),  # Variable names in scanner code
    re.compile(r"len\(.*(?:todos|stubs|501)", re.I),  # len() calls on scanner variables
    re.compile(r':\s*len\(', re.I),  # Dict value being length (code, not task)
    re.compile(r"surfaces?\s+.*(?:TODO|stub|501)", re.I),  # "surfaces TODOs"
    re.compile(r"(?:TODO|FIXME|stub|501).*(?:items?|routes?|count)", re.I),  # "TODO items", "501 routes"
    re.compile(r"placeholder\s+values?", re.I),  # Describing placeholder values (not a gap)
    re.compile(r"descriptive.?placeholder", re.I),  # Examples of good placeholder format
    re.compile(r"explicit\s+placeholder", re.I),  # Describing explicit placeholder pattern
    re.compile(r"VARIABLE_NAME=", re.I),  # Example env var format (not a gap)
]

# File-level patterns where unchecked items are troubleshooting checklists, not work items
TROUBLESHOOTING_CHECKLIST_FILES = [
    "device-firmware.md",  # Troubleshooting checklists for user debugging
]

# Index files to parse for referenced paths
INDEX_FILES = [
    REPO_ROOT / "docs" / "MASTER_DOCUMENT_INDEX.md",
]
# Optional: add MEMORY_DOCUMENTATION_INDEX, SYSTEM_REGISTRY if they list file paths
for name in ("MEMORY_DOCUMENTATION_INDEX_FEB05_2026.md", "SYSTEM_REGISTRY_FEB04_2026.md"):
    p = REPO_ROOT / "docs" / name
    if p.exists():
        INDEX_FILES.append(p)

# Path pattern: backtick-quoted path with common extensions
PATH_PAT = re.compile(
    r"`([^`]+?(?:\.(?:md|py|ts|tsx|js|jsx|json|ps1|yaml|yml|toml)))`",
    re.I,
)
# Also lines like: - `path/to/file.ext` (already covered) or path/to/file in parens
PAREN_PATH_PAT = re.compile(
    r"\((?:docs|scripts|mycosoft_mas|services|\.cursor)/[^)\s]+\.(?:md|py|ts|tsx|js)\)",
    re.I,
)

# Gap patterns to search in file content
GAP_PATTERNS = [
    ("todo_fixme", re.compile(r"(TODO|FIXME|XXX|HACK)\s*[:\-]?\s*(.+)", re.I)),
    ("status_pending", re.compile(r"Status:\s*(?:not started|pending|blocked|in progress)", re.I)),
    ("unchecked", re.compile(r"^\s*-\s*\[\s*\]", re.M)),
    ("501", re.compile(r"501|Not\s+implemented|NotImplementedError", re.I)),
    ("stub", re.compile(r"stub|placeholder|not yet implemented", re.I)),
]


def extract_paths_from_index(index_path: Path) -> list[str]:
    """Extract file paths from an index markdown file."""
    paths = []
    try:
        text = index_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return paths
    for m in PATH_PAT.finditer(text):
        p = m.group(1).strip()
        if "/" in p or "\\" in p:
            paths.append(p.replace("\\", "/"))
    for m in PAREN_PATH_PAT.finditer(text):
        p = m.group(0)[1:-1].strip()  # strip parens
        paths.append(p.replace("\\", "/"))
    return list(dict.fromkeys(paths))  # dedupe


def resolve_path(rel_path: str) -> Path | None:
    """Resolve relative path to repo root; return Path if file exists."""
    normalized = rel_path.lstrip("/").replace("\\", "/")
    full = (REPO_ROOT / normalized).resolve()
    return full if full.is_file() else None


def should_exclude_file(file_path: Path) -> bool:
    """Return True if file should be excluded (describes gaps, not actual gaps)."""
    name = file_path.name
    for pattern in EXCLUDE_FILE_PATTERNS:
        if pattern in name:
            return True
    return False


def is_false_positive_line(line: str) -> bool:
    """Return True if line describes gaps rather than being an actual gap."""
    for pattern in FALSE_POSITIVE_LINE_PATTERNS:
        if pattern.search(line):
            return True
    return False


def is_troubleshooting_checklist(file_path: Path) -> bool:
    """Return True if file contains troubleshooting checklists (not work items)."""
    name = file_path.name
    for pattern in TROUBLESHOOTING_CHECKLIST_FILES:
        if pattern in name:
            return True
    return False


def scan_file_for_gaps(file_path: Path) -> list[dict]:
    """Scan a single file for gap markers; return list of {kind, line_no, snippet}.
    
    Filters out false positives where lines describe gaps rather than contain them.
    For troubleshooting checklist files, unchecked items are filtered out.
    """
    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    lines = text.splitlines()
    gaps = []
    is_troubleshooting = is_troubleshooting_checklist(file_path)
    
    for kind, pattern in GAP_PATTERNS:
        # Skip unchecked items in troubleshooting checklists (they're for user debugging)
        if is_troubleshooting and kind == "unchecked":
            continue
        for i, line in enumerate(lines, 1):
            if pattern.search(line):
                # Filter out false positives
                if is_false_positive_line(line):
                    continue
                snippet = line.strip()[:120]
                gaps.append({"kind": kind, "line_no": i, "snippet": snippet})
    return gaps


def run_index_scan() -> dict:
    """Parse indexes, resolve files, scan for gaps. Return report dict.
    
    Excludes files that describe gaps (meta-docs) vs contain actual incomplete work.
    """
    all_paths: set[str] = set()
    for index_path in INDEX_FILES:
        if not index_path.exists():
            continue
        for p in extract_paths_from_index(index_path):
            all_paths.add(p)

    referenced_with_gaps = []
    files_checked = 0
    files_excluded = 0
    for rel in sorted(all_paths):
        resolved = resolve_path(rel)
        if resolved is None:
            continue
        # Skip files that describe gaps (false positives at file level)
        if should_exclude_file(resolved):
            files_excluded += 1
            continue
        files_checked += 1
        gaps = scan_file_for_gaps(resolved)
        if gaps:
            try:
                rel_str = str(resolved.relative_to(REPO_ROOT))
            except ValueError:
                rel_str = str(resolved)
            referenced_with_gaps.append({
                "path": rel_str,
                "absolute": str(resolved),
                "gaps": gaps,
                "gap_count": len(gaps),
            })

    suggested = []
    if referenced_with_gaps:
        suggested.append({
            "title": "Complete indexed work",
            "description": f"{len(referenced_with_gaps)} indexed files have TODO/FIXME/501/pending work. Prioritize docs and code referenced in MASTER_DOCUMENT_INDEX.",
            "priority": "high",
        })

    report = {
        "index_sources": [str(p.relative_to(REPO_ROOT)) for p in INDEX_FILES if p.exists()],
        "referenced_paths_count": len(all_paths),
        "files_checked": files_checked,
        "files_excluded": files_excluded,
        "files_with_gaps": len(referenced_with_gaps),
        "referenced_files_with_gaps": referenced_with_gaps,
        "suggested_plans": suggested,
        "summary": {
            "index_gaps_total": sum(f["gap_count"] for f in referenced_with_gaps),
            "files_with_gaps": len(referenced_with_gaps),
            "files_excluded_as_meta_docs": files_excluded,
        },
        "source": "cursor_index_scan",
        "note": "Files describing gaps (GAP_AGENT_, PHASE1_, etc.) are excluded. Line-level false positives filtered.",
    }
    return report


def main() -> int:
    report = run_index_scan()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        f"Index gap report: {report['files_with_gaps']} files with gaps, "
        f"{report['summary']['index_gaps_total']} total gaps -> {REPORT_PATH}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
