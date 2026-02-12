#!/usr/bin/env python3
"""
Autonomous Cursor System Startup
Created: February 12, 2026

This script starts all autonomous systems for the Cursor IDE integration:
- MCP servers (registered in .mcp.json, started by Cursor)
- Autonomous scheduler (file watcher + timed tasks)
- Continuous improvement loop (daily self-improvement)

Usage:
    python scripts/start_autonomous_cursor.py [--scheduler] [--improvement] [--all]
    
Options:
    --scheduler     Start the autonomous scheduler daemon
    --improvement   Run the continuous improvement loop once
    --all           Start scheduler + run improvement loop
    --status        Show status of all autonomous systems
"""

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("data/autonomous_cursor.log"),
    ]
)
logger = logging.getLogger("autonomous_cursor")

# Paths
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
MCP_CONFIG = ROOT_DIR / ".mcp.json"
DATA_DIR = ROOT_DIR / "data"


def ensure_data_dir():
    """Ensure data directory exists."""
    DATA_DIR.mkdir(exist_ok=True)


def check_mcp_servers():
    """Check MCP server configurations."""
    if not MCP_CONFIG.exists():
        logger.error(f"MCP config not found: {MCP_CONFIG}")
        return []
    
    with open(MCP_CONFIG, "r") as f:
        config = json.load(f)
    
    servers = config.get("mcpServers", {})
    mycosoft_servers = [
        name for name in servers.keys()
        if name.startswith("mycosoft-")
    ]
    
    return mycosoft_servers


def show_status():
    """Show status of all autonomous systems."""
    print("\n" + "=" * 60)
    print("AUTONOMOUS CURSOR SYSTEM STATUS")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 60)
    
    # MCP Servers
    print("\n[MCP SERVERS]")
    servers = check_mcp_servers()
    for server in servers:
        print(f"  [OK] {server} (configured in .mcp.json)")
    if not servers:
        print("  [X] No Mycosoft MCP servers found")
    
    # Auto-Learning Scripts
    print("\n[AUTO-LEARNING SCRIPTS]")
    scripts = [
        ("pattern_scanner.py", "Code pattern detection"),
        ("skill_generator.py", "Skill auto-generation"),
        ("agent_factory.py", "Agent auto-creation"),
        ("autonomous_scheduler.py", "Task scheduler daemon"),
        ("continuous_improvement.py", "Self-improvement loop"),
    ]
    for script, desc in scripts:
        path = SCRIPT_DIR / script
        status = "[OK]" if path.exists() else "[X]"
        print(f"  {status} {script}: {desc}")
    
    # Services
    print("\n[BACKGROUND SERVICES]")
    services = [
        ("mycosoft_mas.services.learning_feedback", "Learning tracker"),
        ("mycosoft_mas.services.deployment_feedback", "Deployment monitor"),
    ]
    for module, desc in services:
        try:
            __import__(module)
            print(f"  [OK] {module}: {desc}")
        except ImportError as e:
            print(f"  [X] {module}: {e}")
    
    # Data Files
    print("\n[DATA FILES]")
    data_files = [
        "learning_feedback.json",
        "deployment_feedback.json",
        "autonomous_cursor.log",
        "improvement_report.json",
    ]
    for df in data_files:
        path = DATA_DIR / df
        if path.exists():
            size = path.stat().st_size
            print(f"  [OK] {df}: {size} bytes")
        else:
            print(f"  [ ] {df}: not created yet")
    
    print("\n" + "=" * 60)


async def run_scheduler():
    """Run the autonomous scheduler."""
    logger.info("Starting autonomous scheduler...")
    
    # Import and run scheduler
    sys.path.insert(0, str(ROOT_DIR))
    from scripts.autonomous_scheduler import AutonomousScheduler
    
    scheduler = AutonomousScheduler()
    await scheduler.start()


async def run_improvement_loop():
    """Run the continuous improvement loop once."""
    logger.info("Running continuous improvement loop...")
    
    sys.path.insert(0, str(ROOT_DIR))
    from scripts.continuous_improvement import ContinuousImprovementLoop
    
    loop = ContinuousImprovementLoop()
    report = await loop.run_improvement_cycle()
    
    # Save report
    report_path = DATA_DIR / "improvement_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    logger.info(f"Improvement report saved to {report_path}")
    return report


def main():
    parser = argparse.ArgumentParser(
        description="Start Autonomous Cursor System components"
    )
    parser.add_argument(
        "--scheduler", action="store_true",
        help="Start the autonomous scheduler daemon"
    )
    parser.add_argument(
        "--improvement", action="store_true",
        help="Run the continuous improvement loop once"
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Start scheduler and run improvement"
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Show status of all autonomous systems"
    )
    
    args = parser.parse_args()
    
    ensure_data_dir()
    
    if args.status:
        show_status()
        return
    
    if not any([args.scheduler, args.improvement, args.all]):
        # Default: show status
        show_status()
        print("\nUsage:")
        print("  --scheduler     Start autonomous scheduler daemon")
        print("  --improvement   Run improvement loop once")
        print("  --all           Start all autonomous systems")
        print("  --status        Show system status")
        return
    
    if args.all or args.improvement:
        report = asyncio.run(run_improvement_loop())
        print(f"\nImprovement cycle complete:")
        print(f"  - Gaps found: {len(report.get('gaps', []))}")
        print(f"  - Patterns found: {len(report.get('patterns', []))}")
        print(f"  - Skills suggested: {len(report.get('skills_suggested', []))}")
    
    if args.all or args.scheduler:
        print("\nStarting autonomous scheduler (Ctrl+C to stop)...")
        asyncio.run(run_scheduler())


if __name__ == "__main__":
    main()
