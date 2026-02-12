"""
Pattern Scanner for Auto-Learning System.
Created: February 12, 2026

Scans the codebase for repeated patterns that could be automated:
- Common workflows (e.g., "create API endpoint" pattern)
- Repeated code structures
- Similar file templates
- Recurring task patterns

Used by the skill generator to create new skills automatically.
"""

import ast
import json
import logging
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PatternScanner")


@dataclass
class Pattern:
    """Detected code pattern."""
    pattern_id: str
    pattern_type: str  # function, class, file_structure, workflow
    name: str
    description: str
    occurrences: int
    examples: List[str] = field(default_factory=list)
    suggested_skill: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class ScanResult:
    """Result of a pattern scan."""
    timestamp: str
    patterns: List[Pattern]
    summary: Dict[str, int]
    suggestions: List[Dict[str, Any]]


class PatternScanner:
    """
    Scans codebases for repeated patterns that can be automated.
    
    Pattern Types:
    - function: Similar function signatures/structures
    - class: Similar class patterns (e.g., BaseAgent subclasses)
    - file_structure: Similar file templates
    - workflow: Multi-file patterns (e.g., create router + register + update docs)
    - import: Common import patterns
    - api: API endpoint patterns
    """
    
    def __init__(self, workspace_roots: Optional[List[str]] = None):
        self._workspace_roots = [Path(p) for p in (workspace_roots or [
            "c:/Users/admin2/Desktop/MYCOSOFT/CODE/MAS/mycosoft-mas",
            "c:/Users/admin2/Desktop/MYCOSOFT/CODE/WEBSITE/website",
            "c:/Users/admin2/Desktop/MYCOSOFT/CODE/MINDEX/mindex",
        ])]
        
        self._patterns: Dict[str, Pattern] = {}
        self._function_signatures: List[Dict[str, Any]] = []
        self._class_structures: List[Dict[str, Any]] = []
        self._file_templates: Dict[str, List[str]] = defaultdict(list)
        self._import_patterns: Counter = Counter()
        self._api_patterns: List[Dict[str, Any]] = []
        
        # Known patterns to detect
        self._known_patterns = {
            "base_agent": {
                "markers": ["class.*BaseAgent", "def process_task", "async def"],
                "description": "MAS BaseAgent subclass pattern"
            },
            "fastapi_router": {
                "markers": ["APIRouter", "@router.get", "@router.post"],
                "description": "FastAPI router pattern"
            },
            "mcp_server": {
                "markers": ["MCPToolDefinition", "run_stdio_server", "MCPProtocolHandler"],
                "description": "MCP server implementation pattern"
            },
            "nextjs_page": {
                "markers": ["export default function", "page.tsx", "use client"],
                "description": "Next.js page component pattern"
            },
            "react_component": {
                "markers": ["export function", "return.*<", "className="],
                "description": "React functional component pattern"
            },
            "api_route": {
                "markers": ["export async function", "NextRequest", "NextResponse"],
                "description": "Next.js API route pattern"
            },
            "skill_file": {
                "markers": ["SKILL.md", "## When to Use", "## Steps"],
                "description": "Cursor skill file pattern"
            },
            "agent_file": {
                "markers": ["---", "name:", "description:"],
                "description": "Cursor agent file pattern"
            }
        }
    
    def scan_all(self) -> ScanResult:
        """Scan all workspaces for patterns."""
        logger.info("Starting full pattern scan...")
        
        for root in self._workspace_roots:
            if root.exists():
                logger.info(f"Scanning {root}...")
                self._scan_workspace(root)
        
        # Analyze collected data
        self._analyze_patterns()
        
        # Build result
        result = ScanResult(
            timestamp=datetime.now().isoformat(),
            patterns=list(self._patterns.values()),
            summary=self._build_summary(),
            suggestions=self._generate_suggestions()
        )
        
        logger.info(f"Scan complete: {len(result.patterns)} patterns found")
        return result
    
    def _scan_workspace(self, root: Path) -> None:
        """Scan a single workspace."""
        # Python files
        for py_file in root.rglob("*.py"):
            if self._should_skip(py_file):
                continue
            self._scan_python_file(py_file)
        
        # TypeScript/JavaScript files
        for ts_file in root.rglob("*.ts"):
            if self._should_skip(ts_file):
                continue
            self._scan_ts_file(ts_file)
        
        for tsx_file in root.rglob("*.tsx"):
            if self._should_skip(tsx_file):
                continue
            self._scan_tsx_file(tsx_file)
        
        # Markdown files (skills, agents, docs)
        for md_file in root.rglob("*.md"):
            if self._should_skip(md_file):
                continue
            self._scan_md_file(md_file)
    
    def _should_skip(self, path: Path) -> bool:
        """Check if path should be skipped."""
        skip_patterns = [
            "node_modules", "__pycache__", ".git", ".next", 
            "dist", "build", "venv", ".venv", "env",
            "personaplex-repo", "models"
        ]
        return any(skip in str(path) for skip in skip_patterns)
    
    def _scan_python_file(self, path: Path) -> None:
        """Scan a Python file for patterns."""
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            
            # Check for known patterns
            for pattern_id, pattern_info in self._known_patterns.items():
                if all(re.search(marker, content) for marker in pattern_info["markers"][:2]):
                    self._record_pattern_occurrence(pattern_id, str(path), pattern_info["description"])
            
            # Parse AST for function/class patterns
            try:
                tree = ast.parse(content)
                self._analyze_ast(tree, path)
            except SyntaxError:
                pass
            
            # Track import patterns
            for line in content.split("\n"):
                if line.startswith("from ") or line.startswith("import "):
                    # Extract module
                    match = re.match(r"(?:from|import)\s+([\w.]+)", line)
                    if match:
                        self._import_patterns[match.group(1)] += 1
            
            # Track FastAPI patterns
            if "@router." in content or "APIRouter" in content:
                self._api_patterns.append({
                    "file": str(path),
                    "type": "fastapi",
                    "endpoints": len(re.findall(r"@router\.(get|post|put|delete|patch)", content))
                })
        
        except Exception as e:
            logger.debug(f"Error scanning {path}: {e}")
    
    def _scan_ts_file(self, path: Path) -> None:
        """Scan a TypeScript file for patterns."""
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            
            # Check for known patterns
            for pattern_id, pattern_info in self._known_patterns.items():
                if pattern_id in ["nextjs_page", "react_component", "api_route"]:
                    if all(re.search(marker, content) for marker in pattern_info["markers"][:2]):
                        self._record_pattern_occurrence(pattern_id, str(path), pattern_info["description"])
        
        except Exception as e:
            logger.debug(f"Error scanning {path}: {e}")
    
    def _scan_tsx_file(self, path: Path) -> None:
        """Scan a TSX file for patterns."""
        self._scan_ts_file(path)  # Same logic
    
    def _scan_md_file(self, path: Path) -> None:
        """Scan a Markdown file for patterns."""
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            
            # Check for skill patterns
            if "SKILL.md" in str(path):
                self._record_pattern_occurrence("skill_file", str(path), "Cursor skill file pattern")
            
            # Check for agent patterns
            if path.parent.name == "agents" and "---" in content[:50]:
                self._record_pattern_occurrence("agent_file", str(path), "Cursor agent file pattern")
        
        except Exception as e:
            logger.debug(f"Error scanning {path}: {e}")
    
    def _analyze_ast(self, tree: ast.AST, path: Path) -> None:
        """Analyze Python AST for patterns."""
        for node in ast.walk(tree):
            # Track class patterns
            if isinstance(node, ast.ClassDef):
                bases = [
                    base.id if isinstance(base, ast.Name) else 
                    base.attr if isinstance(base, ast.Attribute) else "Unknown"
                    for base in node.bases
                ]
                
                self._class_structures.append({
                    "name": node.name,
                    "file": str(path),
                    "bases": bases,
                    "methods": [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
                })
                
                # Detect BaseAgent pattern
                if "BaseAgent" in bases:
                    self._record_pattern_occurrence(
                        "base_agent", str(path), 
                        f"BaseAgent subclass: {node.name}"
                    )
            
            # Track function patterns
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._function_signatures.append({
                    "name": node.name,
                    "file": str(path),
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                    "args": [arg.arg for arg in node.args.args],
                    "decorators": [
                        d.id if isinstance(d, ast.Name) else
                        d.attr if isinstance(d, ast.Attribute) else "decorator"
                        for d in node.decorator_list
                    ]
                })
    
    def _record_pattern_occurrence(self, pattern_id: str, file_path: str, description: str) -> None:
        """Record a pattern occurrence."""
        if pattern_id not in self._patterns:
            self._patterns[pattern_id] = Pattern(
                pattern_id=pattern_id,
                pattern_type=self._get_pattern_type(pattern_id),
                name=pattern_id.replace("_", " ").title(),
                description=description,
                occurrences=0,
                examples=[]
            )
        
        self._patterns[pattern_id].occurrences += 1
        if len(self._patterns[pattern_id].examples) < 5:
            self._patterns[pattern_id].examples.append(file_path)
    
    def _get_pattern_type(self, pattern_id: str) -> str:
        """Get pattern type from ID."""
        type_map = {
            "base_agent": "class",
            "fastapi_router": "file_structure",
            "mcp_server": "file_structure",
            "nextjs_page": "file_structure",
            "react_component": "function",
            "api_route": "file_structure",
            "skill_file": "workflow",
            "agent_file": "workflow"
        }
        return type_map.get(pattern_id, "other")
    
    def _analyze_patterns(self) -> None:
        """Analyze collected data for additional patterns."""
        # Find common class bases
        base_counter = Counter()
        for cls in self._class_structures:
            for base in cls.get("bases", []):
                if base not in ["object", "Unknown"]:
                    base_counter[base] += 1
        
        # Record common base classes as patterns
        for base, count in base_counter.most_common(10):
            if count >= 3:
                self._patterns[f"class_base_{base.lower()}"] = Pattern(
                    pattern_id=f"class_base_{base.lower()}",
                    pattern_type="class",
                    name=f"Classes inheriting {base}",
                    description=f"Pattern of classes inheriting from {base}",
                    occurrences=count,
                    examples=[c["file"] for c in self._class_structures if base in c.get("bases", [])][:5]
                )
        
        # Find common function names
        func_counter = Counter(f["name"] for f in self._function_signatures)
        for func_name, count in func_counter.most_common(20):
            if count >= 5 and not func_name.startswith("_"):
                self._patterns[f"func_{func_name}"] = Pattern(
                    pattern_id=f"func_{func_name}",
                    pattern_type="function",
                    name=f"Function: {func_name}",
                    description=f"Common function pattern: {func_name}",
                    occurrences=count,
                    examples=[f["file"] for f in self._function_signatures if f["name"] == func_name][:5]
                )
    
    def _build_summary(self) -> Dict[str, int]:
        """Build summary statistics."""
        return {
            "total_patterns": len(self._patterns),
            "class_patterns": len([p for p in self._patterns.values() if p.pattern_type == "class"]),
            "function_patterns": len([p for p in self._patterns.values() if p.pattern_type == "function"]),
            "file_structure_patterns": len([p for p in self._patterns.values() if p.pattern_type == "file_structure"]),
            "workflow_patterns": len([p for p in self._patterns.values() if p.pattern_type == "workflow"]),
            "total_classes_scanned": len(self._class_structures),
            "total_functions_scanned": len(self._function_signatures),
            "unique_imports": len(self._import_patterns),
            "api_files_found": len(self._api_patterns)
        }
    
    def _generate_suggestions(self) -> List[Dict[str, Any]]:
        """Generate skill/agent suggestions based on patterns."""
        suggestions = []
        
        # Suggest skills for high-occurrence patterns
        for pattern in self._patterns.values():
            if pattern.occurrences >= 5:
                suggestions.append({
                    "type": "skill",
                    "based_on_pattern": pattern.pattern_id,
                    "suggested_name": f"create-{pattern.pattern_id.replace('_', '-')}",
                    "reason": f"Pattern '{pattern.name}' appears {pattern.occurrences} times",
                    "priority": "high" if pattern.occurrences >= 10 else "medium"
                })
        
        # Suggest agent for BaseAgent patterns
        if "base_agent" in self._patterns and self._patterns["base_agent"].occurrences >= 20:
            suggestions.append({
                "type": "agent",
                "suggested_name": "agent-generator",
                "reason": f"Many BaseAgent subclasses ({self._patterns['base_agent'].occurrences}) - could auto-generate",
                "priority": "high"
            })
        
        # Suggest skill for API patterns
        if "fastapi_router" in self._patterns and self._patterns["fastapi_router"].occurrences >= 10:
            suggestions.append({
                "type": "skill",
                "suggested_name": "create-api-router",
                "reason": f"FastAPI router pattern appears {self._patterns['fastapi_router'].occurrences} times",
                "priority": "high"
            })
        
        return suggestions
    
    def save_report(self, output_path: Optional[str] = None) -> str:
        """Save scan report to JSON file."""
        result = self.scan_all()
        
        output_path = output_path or os.path.join(
            os.path.dirname(__file__), 
            "../.cursor/pattern_scan_report.json"
        )
        
        report = {
            "timestamp": result.timestamp,
            "summary": result.summary,
            "patterns": [
                {
                    "id": p.pattern_id,
                    "type": p.pattern_type,
                    "name": p.name,
                    "description": p.description,
                    "occurrences": p.occurrences,
                    "examples": p.examples,
                    "suggested_skill": p.suggested_skill
                }
                for p in sorted(result.patterns, key=lambda x: x.occurrences, reverse=True)
            ],
            "suggestions": result.suggestions
        }
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Report saved to {output_path}")
        return output_path


def main():
    """Run pattern scanner."""
    scanner = PatternScanner()
    output_path = scanner.save_report()
    
    # Print summary
    with open(output_path, "r") as f:
        report = json.load(f)
    
    print("\n=== Pattern Scan Report ===")
    print(f"Timestamp: {report['timestamp']}")
    print(f"\nSummary:")
    for key, value in report['summary'].items():
        print(f"  {key}: {value}")
    
    print(f"\nTop Patterns (by occurrences):")
    for pattern in report['patterns'][:10]:
        print(f"  - {pattern['name']}: {pattern['occurrences']} occurrences")
    
    print(f"\nSuggestions ({len(report['suggestions'])}):")
    for suggestion in report['suggestions'][:5]:
        print(f"  - [{suggestion['priority']}] {suggestion['type']}: {suggestion['suggested_name']}")
        print(f"    Reason: {suggestion['reason']}")


if __name__ == "__main__":
    main()
