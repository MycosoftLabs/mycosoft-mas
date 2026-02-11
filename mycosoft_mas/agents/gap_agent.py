"""
Gap Agent - Cross-repo and cross-agent gap detection.

Continuously looks for:
- Missing connections between repos (APIs, routes, components referenced but not implemented)
- TODOs, FIXMEs, and work that needs to be done
- "Bridge" gaps: when two projects are worked on by two agents but a third
  integration/bridge is missing
- Stub implementations and placeholder code
- Vision vs implementation gaps (from gap analysis docs)
- Suggests plans and fixes to fill gaps

No mock data. Uses real filesystem and config (workspace_roots).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from mycosoft_mas.agents.base_agent import BaseAgent
except Exception:
    BaseAgent = object  # type: ignore[misc, assignment]

logger = logging.getLogger(__name__)

# Default: MAS repo root (when running in MAS container). Override via config workspace_roots.
_MAS_ROOT = Path(__file__).resolve().parents[2]

# Patterns for gap detection
_TODO_FIXME = re.compile(r"(TODO|FIXME|XXX|HACK|BUG)\s*[:\-]?\s*(.+)", re.I)
_STUB_PATTERNS = [
    re.compile(r"raise\s+NotImplementedError", re.I),
    re.compile(r"pass\s*#\s*(stub|placeholder|todo)", re.I),
    re.compile(r'return\s*\{\s*["\']status["\']\s*:\s*["\'](?:success|ok)["\']\s*\}'),
    re.compile(r"#\s*stub|#\s*placeholder|#\s*not\s+implemented", re.I),
]
_501_PATTERN = re.compile(r"501|Not\s+implemented", re.I)
_API_ROUTE = re.compile(r"/(?:api|router)[/\w\-{}]+")
_COMPONENT_IMPORT = re.compile(r"from\s+[\w.]+\s+import\s+(\w+)|import\s+(\w+)")


def _collect_roots(config: Dict[str, Any]) -> List[Path]:
    """Return list of workspace root paths to scan."""
    roots: List[Path] = []
    for r in config.get("workspace_roots") or []:
        p = Path(r).expanduser().resolve()
        if p.is_dir():
            roots.append(p)
    if not roots:
        if _MAS_ROOT.is_dir():
            roots.append(_MAS_ROOT)
    return roots


def _scan_todos_fixmes(root: Path, extensions: tuple = (".py", ".ts", ".tsx", ".js", ".md")) -> List[Dict[str, Any]]:
    """Scan for TODO/FIXME lines. Returns list of {file, line, line_no, kind, message}."""
    out: List[Dict[str, Any]] = []
    for path in root.rglob("*"):
        if path.suffix not in extensions or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        rel = path.relative_to(root) if root != path else path.name
        for i, line in enumerate(text.splitlines(), 1):
            m = _TODO_FIXME.search(line)
            if m:
                out.append({
                    "file": str(rel),
                    "line_no": i,
                    "line": line.strip()[:120],
                    "kind": m.group(1).upper(),
                    "message": (m.group(2) or "").strip()[:200],
                    "repo": root.name,
                })
    return out


def _scan_stubs(root: Path, limit: int = 200) -> List[Dict[str, Any]]:
    """Scan for stub/placeholder patterns in Python files."""
    out: List[Dict[str, Any]] = []
    for path in root.rglob("*.py"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        rel = path.relative_to(root) if root != path else path.name
        for pat in _STUB_PATTERNS:
            for i, line in enumerate(text.splitlines(), 1):
                if pat.search(line) and len(out) < limit:
                    out.append({
                        "file": str(rel),
                        "line_no": i,
                        "snippet": line.strip()[:100],
                        "repo": root.name,
                    })
                    break
    return out


def _scan_501_routes(root: Path) -> List[Dict[str, Any]]:
    """Find routes that return 501 or 'Not implemented'."""
    out: List[Dict[str, Any]] = []
    for path in root.rglob("*.py"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if "501" not in text and "Not implemented" not in text and "not implemented" not in text.lower():
            continue
        rel = path.relative_to(root) if root != path else path.name
        for i, line in enumerate(text.splitlines(), 1):
            if _501_PATTERN.search(line):
                out.append({"file": str(rel), "line_no": i, "line": line.strip()[:120], "repo": root.name})
    return out


def _infer_bridge_gaps(roots: List[Path], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Infer potential bridge gaps: e.g. Website calls MAS, MAS calls MINDEX;
    if docs mention an integration that has no corresponding client or route, flag it.
    """
    suggestions: List[Dict[str, Any]] = []
    # Look for docs that mention "integration", "bridge", "connect" between systems
    for root in roots:
        for path in root.rglob("*.md"):
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if "bridge" in text.lower() or "integration" in text.lower():
                if "missing" in text.lower() or "not implemented" in text.lower() or "gap" in text.lower():
                    rel = path.relative_to(root) if root != path else path.name
                    suggestions.append({
                        "type": "bridge_gap",
                        "file": str(rel),
                        "repo": root.name,
                        "hint": "Doc mentions bridge/integration and missing/gap; consider adding a bridge agent or service.",
                    })
    return suggestions[:50]


def _suggest_plans(gaps: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Turn gap summary into suggested plan items."""
    plans: List[Dict[str, Any]] = []
    if gaps.get("todos_fixmes"):
        n = len(gaps["todos_fixmes"])
        plans.append({
            "title": "Address TODOs/FIXMEs",
            "description": f"Resolve or triage {n} TODO/FIXME items across repos.",
            "priority": "medium",
        })
    if gaps.get("stubs"):
        n = len(gaps["stubs"])
        plans.append({
            "title": "Replace stubs with implementations",
            "description": f"Replace or document {n} stub/placeholder usages.",
            "priority": "medium",
        })
    if gaps.get("routes_501"):
        n = len(gaps["routes_501"])
        plans.append({
            "title": "Implement 501 routes",
            "description": f"Implement {n} API routes currently returning 501.",
            "priority": "high",
        })
    if gaps.get("bridge_gaps"):
        plans.append({
            "title": "Add missing bridges between systems",
            "description": "Implement integration layer or agent where docs indicate a bridge is missing.",
            "priority": "high",
        })
    return plans


class GapAgent(BaseAgent if BaseAgent is not object else object):  # type: ignore[misc]
    """Finds gaps between repos: missing connections, TODOs, stubs, and bridge work."""

    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        if BaseAgent is not object:
            super().__init__(agent_id=agent_id, name=name, config=config or {})
        else:
            self.agent_id = agent_id
            self.name = name
            self.config = config or {}
        self.capabilities = ["gap_scan", "cross_repo", "todo_scan", "stub_scan", "bridge_suggest", "plan_suggest"]
        self._last_report: Optional[Dict[str, Any]] = None

    def _run_scan(self, full: bool = False) -> Dict[str, Any]:
        roots = _collect_roots(self.config)
        report: Dict[str, Any] = {
            "workspace_roots": [str(r) for r in roots],
            "todos_fixmes": [],
            "stubs": [],
            "routes_501": [],
            "bridge_gaps": [],
            "suggested_plans": [],
            "summary": {},
        }
        todo_limit = 300 if full else 80
        for root in roots:
            report["todos_fixmes"].extend(_scan_todos_fixmes(root)[:todo_limit])
            report["stubs"].extend(_scan_stubs(root, limit=80))
            report["routes_501"].extend(_scan_501_routes(root))
        report["bridge_gaps"] = _infer_bridge_gaps(roots, self.config)
        report["suggested_plans"] = _suggest_plans(report)
        report["summary"] = {
            "todos_fixmes_count": len(report["todos_fixmes"]),
            "stubs_count": len(report["stubs"]),
            "routes_501_count": len(report["routes_501"]),
            "bridge_gaps_count": len(report["bridge_gaps"]),
            "plans_suggested": len(report["suggested_plans"]),
        }
        return report

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        task_type = task.get("type", "scan")
        full = task.get("full", False)
        if task_type in ("scan", "full_scan", "gap_scan"):
            self._last_report = self._run_scan(full=full or task_type == "full_scan")
            return {"status": "success", "result": self._last_report}
        if task_type == "suggest_plans":
            if not self._last_report:
                self._last_report = self._run_scan(full=False)
            return {"status": "success", "result": {"suggested_plans": self._last_report.get("suggested_plans", [])}}
        if task_type == "continuous_cycle":
            self._last_report = self._run_scan(full=False)
            return {"status": "success", "result": {"cycle": "scan_complete", "summary": self._last_report.get("summary", {})}}
        return {"status": "success", "result": {"message": "Unknown task type; use scan, full_scan, or suggest_plans"}}

    async def run_cycle(self) -> Dict[str, Any]:
        """Single cycle for 24/7 runner: lightweight scan and store report."""
        try:
            self._last_report = self._run_scan(full=False)
            summary = self._last_report.get("summary", {})
            return {
                "tasks_processed": 1,
                "insights_generated": summary.get("plans_suggested", 0),
                "knowledge_added": 0,
                "summary": f"GapAgent cycle: {summary.get('todos_fixmes_count', 0)} TODOs, {summary.get('routes_501_count', 0)} 501 routes, {len(self._last_report.get('suggested_plans', []))} plans suggested",
            }
        except Exception as e:
            logger.warning("GapAgent run_cycle error: %s", e)
            return {
                "tasks_processed": 0,
                "insights_generated": 0,
                "knowledge_added": 0,
                "summary": f"GapAgent cycle error: {e!s}",
            }
