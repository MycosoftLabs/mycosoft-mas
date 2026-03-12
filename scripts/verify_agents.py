#!/usr/bin/env python3
"""
Mycosoft MAS Agent Verification Script
=======================================
Run this to get the REAL, LIVE count of all agents in the system.
Resolves the conflicting numbers (40, 117, 273+) once and for all.

Usage:
    python scripts/verify_agents.py
    python scripts/verify_agents.py --json
    python scripts/verify_agents.py --category corporate
"""

import argparse
import importlib
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class VerificationStatus(str, Enum):
    LIVE = "live"           # Class loads, has real implementation
    LOADABLE = "loadable"   # Class loads, but stub/minimal implementation
    BROKEN = "broken"       # Class exists but fails to import
    STUB_ONLY = "stub_only" # Runtime-generated stub, no real code
    MISSING = "missing"     # Referenced in registry but no file exists


@dataclass
class AgentVerification:
    class_name: str
    file_path: str
    category: str
    status: VerificationStatus
    base_class: str  # BaseAgent, BaseAgentV2, standalone
    has_process_task: bool
    has_execute_task: bool
    has_run_cycle: bool
    in_core_registry: bool
    in_catalog_registry: bool
    in_init_exports: bool
    import_error: Optional[str] = None
    line_count: int = 0


def scan_agent_files() -> List[AgentVerification]:
    """Scan the codebase for all agent class definitions."""
    agents = []
    base_dir = Path("mycosoft_mas/agents")

    skip_classes = {
        "AgentMemoryMixin", "AgentWebSocketMixin", "AgentStatus",
        "AgentMessage", "AgentInterface", "BaseAgent", "BaseAgentV2",
        "AgentMonitorable", "AgentSecurable", "BaseScientificAgent",
        "ScientificAgentMemory", "CorporateAgentOrchestrator",
        "AgentManager", "Message", "TaskMessage",
        "SubAgentPersona", "SubAgentRouter",
    }

    for py_file in sorted(base_dir.rglob("*.py")):
        if py_file.name == "__init__.py" or "__pycache__" in str(py_file):
            continue

        content = py_file.read_text()
        lines = content.split("\n")

        # Find agent classes
        for match in re.finditer(r"^class\s+(\w+)\s*\(([^)]*)\)\s*:", content, re.MULTILINE):
            class_name = match.group(1)
            parent = match.group(2).strip()

            if class_name in skip_classes:
                continue

            # Determine base class
            if "BaseAgentV2" in parent or "BaseScientificAgent" in parent:
                base_class = "BaseAgentV2"
            elif "BaseAgent" in parent:
                base_class = "BaseAgent"
            else:
                base_class = "standalone"

            # Check method implementations
            has_process = "async def process_task" in content
            has_execute = "async def execute_task" in content or "async def execute" in content
            has_cycle = "def run_cycle" in content

            # Determine category from file path
            category = _categorize_from_path(str(py_file), class_name)

            # Count implementation lines (rough)
            line_count = len([l for l in lines if l.strip() and not l.strip().startswith("#")])

            # Try to import
            module_path = str(py_file).replace("/", ".").replace(".py", "")
            import_error = None
            try:
                importlib.import_module(module_path)
            except Exception as e:
                import_error = str(e)[:100]

            # Determine status
            if import_error:
                status = VerificationStatus.BROKEN
            elif has_process or has_execute or has_cycle:
                if line_count > 30:
                    status = VerificationStatus.LIVE
                else:
                    status = VerificationStatus.LOADABLE
            else:
                status = VerificationStatus.LOADABLE

            agents.append(AgentVerification(
                class_name=class_name,
                file_path=str(py_file),
                category=category,
                status=status,
                base_class=base_class,
                has_process_task=has_process,
                has_execute_task=has_execute,
                has_run_cycle=has_cycle,
                in_core_registry=False,  # filled in later
                in_catalog_registry=False,  # filled in later
                in_init_exports=False,  # filled in later
                import_error=import_error,
                line_count=line_count,
            ))

    return agents


def _categorize_from_path(filepath: str, class_name: str) -> str:
    """Categorize an agent based on its file path and class name."""
    fp = filepath.lower()
    cl = class_name.lower()

    if "earth2" in fp:
        return "earth2"
    if "v2/corporate" in fp:
        return "corporate"
    if "corporate/" in fp and "v2" not in fp:
        return "corporate"
    if "natureos" in fp:
        return "natureos"
    if "mycobrain" in fp or "v2/device" in fp:
        return "device"
    if "memory/" in fp:
        return "memory"
    if "workflow" in fp:
        return "workflow"
    if "v2/scientific" in fp or "v2/lab" in fp:
        return "scientific"
    if "v2/simulation" in fp or "simulation" in fp:
        return "simulation"
    if "financial" in fp or "finance" in cl or "trading" in cl:
        return "financial"
    if "security" in fp or "guardian" in cl or "crep" in cl:
        return "security"
    if "integration" in fp or "v2/integration" in fp:
        return "integration"
    if "v2/infrastructure" in fp:
        return "infrastructure"
    if "voice" in cl or "speech" in cl or "tts" in cl or "stt" in cl or "dialog" in cl:
        return "voice"
    if "cluster" in fp:
        return "cluster"
    if "utility/" in fp:
        return "utility"
    if "mycology" in cl:
        return "mycology"
    if "dao" in cl or "ip_" in cl or "tokenization" in cl:
        return "dao"
    return "core"


def cross_reference_registries(agents: List[AgentVerification]):
    """Cross-reference agents with the two registry systems."""
    # Core registry (agent_registry.py)
    core_registry_path = Path("mycosoft_mas/core/agent_registry.py")
    if core_registry_path.exists():
        core_content = core_registry_path.read_text()
        core_classes = set(re.findall(r'class_name="(\w+)"', core_content))
    else:
        core_classes = set()

    # Catalog registry (registry/agent_registry.py)
    catalog_path = Path("mycosoft_mas/registry/agent_registry.py")
    if catalog_path.exists():
        catalog_content = catalog_path.read_text()
        catalog_classes = set(re.findall(r'"class":\s*"(\w+)"', catalog_content))
    else:
        catalog_classes = set()

    # Init exports
    init_path = Path("mycosoft_mas/agents/__init__.py")
    if init_path.exists():
        init_content = init_path.read_text()
        init_classes = set(re.findall(r'"(\w+)"', init_content))
    else:
        init_classes = set()

    for agent in agents:
        agent.in_core_registry = agent.class_name in core_classes
        agent.in_catalog_registry = agent.class_name in catalog_classes
        agent.in_init_exports = agent.class_name in init_classes


def get_legacy_stubs() -> List[AgentVerification]:
    """Get the runtime-generated legacy stub agents."""
    stubs = {
        "ContractAgent", "LegalAgent", "TechnicalAgent", "QAAgent",
        "VerificationAgent", "AuditAgent", "RegistryAgent", "AnalyticsAgent",
        "RiskAgent", "ComplianceAgent", "OperationsAgent",
    }
    return [
        AgentVerification(
            class_name=name,
            file_path="(runtime-generated in __init__.py)",
            category="legacy_stub",
            status=VerificationStatus.STUB_ONLY,
            base_class="BaseAgent",
            has_process_task=False,
            has_execute_task=False,
            has_run_cycle=True,  # has a minimal run_cycle
            in_core_registry=False,
            in_catalog_registry=False,
            in_init_exports=True,
            line_count=0,
        )
        for name in sorted(stubs)
    ]


def print_report(agents: List[AgentVerification], output_json: bool = False,
                 filter_category: Optional[str] = None):
    """Print the verification report."""
    if filter_category:
        agents = [a for a in agents if a.category == filter_category]

    if output_json:
        print(json.dumps([asdict(a) for a in agents], indent=2, default=str))
        return

    # Header
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print("=" * 80)
    print(f"  MYCOSOFT MAS - AGENT VERIFICATION REPORT")
    print(f"  Generated: {now}")
    print("=" * 80)

    # Summary counts
    by_status = defaultdict(int)
    by_category = defaultdict(int)
    by_base = defaultdict(int)
    for a in agents:
        by_status[a.status.value] += 1
        by_category[a.category] += 1
        by_base[a.base_class] += 1

    total = len(agents)
    live = by_status.get("live", 0)
    loadable = by_status.get("loadable", 0)
    broken = by_status.get("broken", 0)
    stub_only = by_status.get("stub_only", 0)

    print(f"\n  TOTAL AGENTS: {total}")
    print(f"  ├── LIVE (real implementation): {live}")
    print(f"  ├── LOADABLE (minimal/stub):    {loadable}")
    print(f"  ├── BROKEN (import fails):      {broken}")
    print(f"  └── STUB ONLY (no real code):   {stub_only}")

    print(f"\n  BY ARCHITECTURE:")
    for base, count in sorted(by_base.items()):
        print(f"  ├── {base}: {count}")

    registered_core = sum(1 for a in agents if a.in_core_registry)
    registered_catalog = sum(1 for a in agents if a.in_catalog_registry)
    unregistered = sum(1 for a in agents if not a.in_core_registry and not a.in_catalog_registry)

    print(f"\n  REGISTRY STATUS:")
    print(f"  ├── In Core Registry (voice-routable): {registered_core}")
    print(f"  ├── In Catalog Registry:               {registered_catalog}")
    print(f"  └── UNREGISTERED (not in any registry):{unregistered}")

    # By category
    print(f"\n  {'CATEGORY':<20} {'COUNT':>6}  {'LIVE':>5}  {'LOAD':>5}  {'BROKE':>5}")
    print(f"  {'-'*20} {'-'*6}  {'-'*5}  {'-'*5}  {'-'*5}")
    for cat in sorted(by_category.keys()):
        cat_agents = [a for a in agents if a.category == cat]
        cat_live = sum(1 for a in cat_agents if a.status == VerificationStatus.LIVE)
        cat_load = sum(1 for a in cat_agents if a.status == VerificationStatus.LOADABLE)
        cat_broke = sum(1 for a in cat_agents if a.status == VerificationStatus.BROKEN)
        print(f"  {cat:<20} {len(cat_agents):>6}  {cat_live:>5}  {cat_load:>5}  {cat_broke:>5}")

    # Broken agents (need attention)
    broken_agents = [a for a in agents if a.status == VerificationStatus.BROKEN]
    if broken_agents:
        print(f"\n  BROKEN AGENTS (NEED FIXING):")
        for a in broken_agents:
            print(f"  ! {a.class_name}: {a.import_error}")

    # Unregistered agents
    unreg = [a for a in agents if not a.in_core_registry and not a.in_catalog_registry
             and a.status != VerificationStatus.STUB_ONLY]
    if unreg:
        print(f"\n  UNREGISTERED AGENTS ({len(unreg)} agents not in any registry):")
        for a in unreg[:20]:
            print(f"  ? {a.class_name} ({a.category}) - {a.file_path}")
        if len(unreg) > 20:
            print(f"  ... and {len(unreg) - 20} more")

    print(f"\n{'=' * 80}")
    print(f"  THE REAL NUMBER: {total} total agents")
    print(f"  WORKING EMPLOYEES: {live} fully implemented")
    print(f"  NEED ATTENTION: {broken} broken + {stub_only} stubs")
    print(f"{'=' * 80}")


def main():
    parser = argparse.ArgumentParser(description="Verify all MAS agents")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--category", type=str, help="Filter by category")
    args = parser.parse_args()

    # Scan codebase
    agents = scan_agent_files()

    # Add legacy stubs
    agents.extend(get_legacy_stubs())

    # Cross-reference registries
    cross_reference_registries(agents)

    # Deduplicate by class name (keep most complete version)
    seen = {}
    for a in agents:
        key = a.class_name
        if key not in seen or a.status.value < seen[key].status.value:
            seen[key] = a
    agents = sorted(seen.values(), key=lambda x: (x.category, x.class_name))

    # Print report
    print_report(agents, output_json=args.json, filter_category=args.category)


if __name__ == "__main__":
    main()
