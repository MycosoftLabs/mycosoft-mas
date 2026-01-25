#!/usr/bin/env python3
"""Verify MAS v2 implementation files."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

# Key files that should exist
KEY_FILES = [
    # Runtime
    "mycosoft_mas/runtime/__init__.py",
    "mycosoft_mas/runtime/models.py",
    "mycosoft_mas/runtime/agent_runtime.py",
    "mycosoft_mas/runtime/agent_pool.py",
    "mycosoft_mas/runtime/message_broker.py",
    "mycosoft_mas/runtime/snapshot_manager.py",
    "mycosoft_mas/runtime/memory_manager.py",
    "mycosoft_mas/runtime/gap_detector.py",
    "mycosoft_mas/runtime/agent_factory.py",
    # Core
    "mycosoft_mas/core/orchestrator_service.py",
    "mycosoft_mas/core/dashboard_api.py",
    # Agents
    "mycosoft_mas/agents/v2/__init__.py",
    "mycosoft_mas/agents/v2/base_agent_v2.py",
    "mycosoft_mas/agents/v2/corporate_agents.py",
    "mycosoft_mas/agents/v2/infrastructure_agents.py",
    "mycosoft_mas/agents/v2/device_agents.py",
    "mycosoft_mas/agents/v2/data_agents.py",
    "mycosoft_mas/agents/v2/integration_agents.py",
    # Docker
    "docker/Dockerfile.agent",
    "docker/docker-compose.agents.yml",
    # Database
    "migrations/003_agent_logging.sql",
    # Docs
    "docs/MAS_V2_IMPLEMENTATION_SUMMARY.md",
    "docs/MAS_VM_PROVISIONING_GUIDE.md",
    "docs/DASHBOARD_COMPONENTS.md",
    # Other
    "requirements-agent.txt",
]

def main():
    print("=" * 60)
    print("MAS v2 Implementation Verification")
    print("=" * 60)
    print()
    
    found = 0
    missing = 0
    
    for file in KEY_FILES:
        path = BASE_DIR / file
        if path.exists():
            size = path.stat().st_size
            print(f"  [OK] {file} ({size} bytes)")
            found += 1
        else:
            print(f"  [MISSING] {file}")
            missing += 1
    
    print()
    print("-" * 60)
    print(f"Total: {found} files found, {missing} missing")
    print()
    
    # Count agents
    agents_dir = BASE_DIR / "mycosoft_mas" / "agents" / "v2"
    if agents_dir.exists():
        agent_files = list(agents_dir.glob("*_agents.py"))
        print(f"Agent modules: {len(agent_files)}")
        
        # Count agent classes
        total_classes = 0
        for af in agent_files:
            content = af.read_text()
            classes = content.count("class ") - content.count("class Base")
            total_classes += classes
            print(f"  - {af.name}: ~{classes} agent classes")
        print(f"Total agent classes: ~{total_classes}")
    
    print()
    print("=" * 60)
    
    return missing == 0


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
