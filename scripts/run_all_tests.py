#!/usr/bin/env python3
"""
Master Test Runner - Executes all test phases
Created: February 5, 2026
"""
import subprocess
import sys
import time
from datetime import datetime

# Terminal colors
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

TEST_SCRIPTS = [
    ("Phase 1: Infrastructure", "test_infrastructure.py"),
    ("Phase 2: API Endpoints", "test_api_endpoints.py"),
    ("Phase 3: Frontend UI", "test_frontend.py"),
    ("Phase 4: Voice Commands", "test_voice_commands.py"),
    ("Phase 5: Agent Orchestration", "test_agent_orchestration.py"),
    ("Phase 6: Memory System", "test_memory_system.py"),
    ("Phase 7: Workflows", "test_workflows.py"),
    ("Phase 8: ETL & Data", "test_etl_data.py"),
    ("Phase 9: Search & Discovery", "test_search_discovery.py"),
    ("Phase 10: Security", "test_security.py"),
]

def run_test(name: str, script: str) -> tuple:
    """Run a single test script and return (exit_code, duration)."""
    print(f"\n{Colors.CYAN}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}Running: {name}{Colors.END}")
    print(f"{Colors.CYAN}{'='*70}{Colors.END}")
    
    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, f"scripts/{script}"],
            capture_output=False,
            timeout=300
        )
        duration = time.time() - start
        return result.returncode, duration
    except subprocess.TimeoutExpired:
        return -1, 300
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.END}")
        return -1, time.time() - start

def main():
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("=" * 70)
    print("       MYCOSOFT MAS COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    print(f"{Colors.END}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Phases to run: {len(TEST_SCRIPTS)}")
    
    results = []
    total_start = time.time()
    
    for name, script in TEST_SCRIPTS:
        exit_code, duration = run_test(name, script)
        status = "PASS" if exit_code == 0 else "FAIL"
        results.append((name, status, duration))
    
    total_duration = time.time() - total_start
    
    # Print summary
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("=" * 70)
    print("                    MASTER TEST SUMMARY")
    print("=" * 70)
    print(f"{Colors.END}")
    
    passed = sum(1 for _, status, _ in results if status == "PASS")
    failed = len(results) - passed
    
    for name, status, duration in results:
        if status == "PASS":
            icon = f"{Colors.GREEN}[PASS]{Colors.END}"
        else:
            icon = f"{Colors.RED}[FAIL]{Colors.END}"
        print(f"  {icon} {name} ({duration:.1f}s)")
    
    print(f"\n{Colors.BOLD}Overall Results:{Colors.END}")
    print(f"  Phases Passed: {Colors.GREEN}{passed}{Colors.END}")
    print(f"  Phases Failed: {Colors.RED}{failed}{Colors.END}")
    print(f"  Total Duration: {total_duration:.1f}s")
    print(f"\n{Colors.BLUE}Report: docs/COMPREHENSIVE_SYSTEM_TEST_REPORT_FEB05_2026.md{Colors.END}")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
