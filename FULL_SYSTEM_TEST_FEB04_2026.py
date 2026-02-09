#!/usr/bin/env python3
"""
MYCOSOFT FULL SYSTEM AUTOMATED TEST FRAMEWORK
February 4, 2026

This script performs:
1. Full system service testing (Moshi, Bridge, MAS, Memory, MINDEX, Voice)
2. Detailed logging of all results
3. Automatic error detection and fixing
4. Re-testing after fixes
5. Comprehensive report generation

Integrates with:
- Memory Registry System (full_memory_registry_system plan)
- PersonaPlex/Moshi voice system
- MAS Orchestrator and Agents
- MYCA Brain Engine

NEVER DISABLE CUDA GRAPHS - They are essential for PersonaPlex performance.
"""

import asyncio
import json
import os
import socket
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Paths
MAS_DIR = Path(r"c:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas")
WEBSITE_DIR = Path(r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website")
LOG_DIR = MAS_DIR / "logs"
REPORT_DIR = MAS_DIR / "docs"

# Ensure log directory exists
LOG_DIR.mkdir(exist_ok=True)

# Service configuration
SERVICES = {
    "moshi": {"port": 8998, "host": "localhost", "type": "websocket"},
    "bridge": {"port": 8999, "host": "localhost", "type": "http"},
    "mas": {"port": 8001, "host": "192.168.0.188", "type": "http"},
    "website": {"port": 3010, "host": "localhost", "type": "http"},
    "redis": {"port": 6379, "host": "localhost", "type": "tcp"},
}

# Test results storage
test_results: List[Dict] = []
fixes_applied: List[Dict] = []
log_entries: List[str] = []

# Timestamp for this test run
RUN_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = LOG_DIR / f"system_test_{RUN_TIMESTAMP}.log"


def log(level: str, message: str):
    """Log a message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] [{level.upper():8s}] {message}"
    log_entries.append(entry)
    print(entry, flush=True)
    
    # Also write to log file
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry + "\n")
        f.flush()


def log_test(name: str, passed: bool, details: str = "", duration_ms: float = 0):
    """Log a test result."""
    status = "PASS" if passed else "FAIL"
    result = {
        "name": name,
        "passed": passed,
        "details": details,
        "duration_ms": duration_ms,
        "timestamp": datetime.now().isoformat(),
    }
    test_results.append(result)
    log("test", f"{status}: {name} ({duration_ms:.0f}ms) - {details}")
    return passed


def check_port(port: int, host: str = "localhost", timeout: float = 5.0) -> bool:
    """Check if a port is open. Extended timeout for remote hosts."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # Use longer timeout for remote hosts
            actual_timeout = timeout if host == "localhost" else timeout * 2
            s.settimeout(actual_timeout)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False


def http_get(url: str, timeout: float = 10.0) -> Tuple[int, Optional[Dict]]:
    """Make HTTP GET request."""
    try:
        import requests
        r = requests.get(url, timeout=timeout)
        try:
            return r.status_code, r.json()
        except:
            return r.status_code, {"text": r.text[:500]}
    except Exception as e:
        return -1, {"error": str(e)}


def http_post(url: str, data: Dict, timeout: float = 10.0) -> Tuple[int, Optional[Dict]]:
    """Make HTTP POST request."""
    try:
        import requests
        r = requests.post(url, json=data, timeout=timeout)
        try:
            return r.status_code, r.json()
        except:
            return r.status_code, {"text": r.text[:500]}
    except Exception as e:
        return -1, {"error": str(e)}


async def ws_test(url: str, timeout: float = 120.0) -> Tuple[bool, str]:
    """Test WebSocket connection with extended timeout for CUDA graphs."""
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(url, timeout=aiohttp.ClientTimeout(total=timeout + 30)) as ws:
                msg = await asyncio.wait_for(ws.receive(), timeout=timeout)
                if msg.type == aiohttp.WSMsgType.BINARY and msg.data == b"\x00":
                    return True, "Handshake OK"
                return True, f"Connected, received: {msg.type}"
    except asyncio.TimeoutError:
        return False, f"Timeout after {timeout}s waiting for handshake"
    except Exception as e:
        return False, str(e)


# =============================================================================
# SERVICE TESTS
# =============================================================================

def test_service_ports() -> int:
    """Test if all service ports are open."""
    log("info", "=" * 60)
    log("info", "PHASE 1: SERVICE PORT TESTS")
    log("info", "=" * 60)
    
    passed = 0
    for name, config in SERVICES.items():
        start = time.time()
        is_open = check_port(config["port"], config["host"])
        duration = (time.time() - start) * 1000
        
        if log_test(
            f"Port {config['port']} ({name})",
            is_open,
            f"{config['host']}:{config['port']} {'open' if is_open else 'closed'}",
            duration
        ):
            passed += 1
    
    return passed


def test_http_endpoints() -> int:
    """Test HTTP health endpoints."""
    log("info", "=" * 60)
    log("info", "PHASE 2: HTTP HEALTH ENDPOINTS")
    log("info", "=" * 60)
    
    # Using correct MAS API paths from OpenAPI schema
    endpoints = [
        ("Bridge Health", "http://localhost:8999/health"),
        ("MAS Health", "http://192.168.0.188:8001/health"),
        ("MAS Memory Health", "http://192.168.0.188:8001/api/memory/health"),
        ("MAS MINDEX Health", "http://192.168.0.188:8001/integrations/mindex/health"),
        ("MAS Agents Registry", "http://192.168.0.188:8001/agents/registry/"),
        ("MAS Integrations Status", "http://192.168.0.188:8001/integrations/status"),
        ("Website Home", "http://localhost:3010/"),
    ]
    
    passed = 0
    for name, url in endpoints:
        start = time.time()
        status, data = http_get(url)
        duration = (time.time() - start) * 1000
        
        success = status == 200
        details = f"Status: {status}"
        if isinstance(data, dict) and "status" in data:
            details += f", Health: {data.get('status')}"
        
        if log_test(name, success, details, duration):
            passed += 1
    
    return passed


def test_memory_system() -> int:
    """Test full memory system with all 8 scopes."""
    log("info", "=" * 60)
    log("info", "PHASE 3: MEMORY SYSTEM (8 SCOPES)")
    log("info", "=" * 60)
    
    scopes = ["conversation", "user", "agent", "system", "ephemeral", "device", "experiment", "workflow"]
    passed = 0
    
    for scope in scopes:
        # Write test
        start = time.time()
        status, data = http_post(
            "http://192.168.0.188:8001/api/memory/write",
            {
                "scope": scope,
                "namespace": "automated_test",
                "key": f"test_{RUN_TIMESTAMP}",
                "value": {"test": True, "timestamp": datetime.now().isoformat()}
            }
        )
        duration = (time.time() - start) * 1000
        
        success = status == 200 and data and data.get("success", False)
        if log_test(f"Memory Write ({scope})", success, f"Status: {status}", duration):
            passed += 1
        
        # Read test
        start = time.time()
        status, data = http_post(
            "http://192.168.0.188:8001/api/memory/read",
            {
                "scope": scope,
                "namespace": "automated_test",
                "key": f"test_{RUN_TIMESTAMP}"
            }
        )
        duration = (time.time() - start) * 1000
        
        success = status == 200 and data and data.get("success", False)
        if log_test(f"Memory Read ({scope})", success, f"Status: {status}", duration):
            passed += 1
    
    return passed


def test_voice_system() -> int:
    """Test voice system components."""
    log("info", "=" * 60)
    log("info", "PHASE 4: VOICE SYSTEM")
    log("info", "=" * 60)
    
    passed = 0
    
    # Test MYCA voice chat endpoint
    start = time.time()
    status, data = http_post(
        "http://192.168.0.188:8001/voice/orchestrator/chat",
        {"message": "What is your name?"}
    )
    duration = (time.time() - start) * 1000
    
    success = status == 200 and data and "MYCA" in str(data.get("response_text", ""))
    details = f"Response: {str(data.get('response_text', ''))[:100]}..." if data else "No response"
    if log_test("MYCA Voice Chat", success, details, duration):
        passed += 1
    
    # Test voice session creation
    start = time.time()
    status, data = http_post(
        "http://192.168.0.188:8001/api/voice/session/create",
        {
            "session_id": f"test_{RUN_TIMESTAMP}",
            "conversation_id": f"conv_{RUN_TIMESTAMP}",
            "mode": "personaplex",
            "persona": "myca"
        }
    )
    duration = (time.time() - start) * 1000
    
    success = status == 200 and data and data.get("session_id")
    if log_test("Voice Session Create", success, f"Session: {data.get('session_id', 'none')[:20] if data else 'none'}", duration):
        passed += 1
    
    # Test Bridge session creation
    start = time.time()
    status, data = http_post(
        "http://localhost:8999/session",
        {"persona": "myca", "voice": "myca", "enable_mas_events": True}
    )
    duration = (time.time() - start) * 1000
    
    success = status == 200 and data and data.get("session_id")
    if log_test("Bridge Session Create", success, f"Session: {data.get('session_id', 'none')[:20] if data else 'none'}", duration):
        passed += 1
    
    return passed


async def test_websocket_connections() -> int:
    """Test WebSocket connections to Moshi and Bridge."""
    log("info", "=" * 60)
    log("info", "PHASE 5: WEBSOCKET CONNECTIONS")
    log("info", "=" * 60)
    
    passed = 0
    
    # Test direct Moshi WebSocket (extended timeout for CUDA graphs)
    start = time.time()
    success, details = await ws_test("ws://localhost:8998/api/chat", timeout=120)
    duration = (time.time() - start) * 1000
    
    if log_test("Moshi WebSocket Direct", success, details, duration):
        passed += 1
    
    # Test Bridge WebSocket (need session first)
    try:
        import requests
        r = requests.post("http://localhost:8999/session", json={"persona": "myca"}, timeout=5)
        if r.status_code == 200:
            session_id = r.json()["session_id"]
            
            start = time.time()
            success, details = await ws_test(f"ws://localhost:8999/ws/{session_id}", timeout=120)
            duration = (time.time() - start) * 1000
            
            if log_test("Bridge WebSocket Pipeline", success, details, duration):
                passed += 1
        else:
            log_test("Bridge WebSocket Pipeline", False, "Could not create session", 0)
    except Exception as e:
        log_test("Bridge WebSocket Pipeline", False, str(e), 0)
    
    return passed


def test_brain_system() -> int:
    """Test MYCA Brain Engine and related endpoints."""
    log("info", "=" * 60)
    log("info", "PHASE 6: MYCA BRAIN/VOICE ENDPOINTS")
    log("info", "=" * 60)
    
    passed = 0
    
    # Test voice feedback recent (available on MAS)
    start = time.time()
    status, data = http_get("http://192.168.0.188:8001/voice/feedback/recent")
    duration = (time.time() - start) * 1000
    
    success = status == 200
    if log_test("Voice Feedback Recent", success, f"Status: {status}", duration):
        passed += 1
    
    # Test voice feedback summary
    start = time.time()
    status, data = http_get("http://192.168.0.188:8001/voice/feedback/summary")
    duration = (time.time() - start) * 1000
    
    success = status == 200
    if log_test("Voice Feedback Summary", success, f"Status: {status}", duration):
        passed += 1
    
    # Test MINDEX stats (simpler endpoint that doesn't require complex params)
    start = time.time()
    status, data = http_get("http://192.168.0.188:8001/mindex/stats")
    duration = (time.time() - start) * 1000
    
    success = status == 200
    if log_test("MINDEX Stats", success, f"Status: {status}", duration):
        passed += 1
    
    return passed


def test_agent_system() -> int:
    """Test MAS Agent Registry."""
    log("info", "=" * 60)
    log("info", "PHASE 7: AGENT REGISTRY")
    log("info", "=" * 60)
    
    passed = 0
    
    # Test agent registry list (correct endpoint from OpenAPI)
    start = time.time()
    status, data = http_get("http://192.168.0.188:8001/agents/registry/")
    duration = (time.time() - start) * 1000
    
    success = status == 200 and isinstance(data, dict)
    agent_count = data.get("total_agents", 0) if data else 0
    if log_test("Agent Registry List", success, f"Agents: {agent_count}", duration):
        passed += 1
    
    # Test agent categories (correct endpoint)
    start = time.time()
    status, data = http_get("http://192.168.0.188:8001/agents/registry/categories")
    duration = (time.time() - start) * 1000
    
    success = status == 200
    category_count = len(data) if isinstance(data, list) else 0
    if log_test("Agent Categories", success, f"Categories: {category_count}", duration):
        passed += 1
    
    # Test runner status
    start = time.time()
    status, data = http_get("http://192.168.0.188:8001/runner/status")
    duration = (time.time() - start) * 1000
    
    success = status == 200
    if log_test("Runner Status", success, f"Status: {status}", duration):
        passed += 1
    
    return passed


# =============================================================================
# AUTO-FIX FUNCTIONS
# =============================================================================

def fix_bridge_not_running() -> bool:
    """Start the PersonaPlex Bridge if not running."""
    log("fix", "Attempting to start PersonaPlex Bridge...")
    
    try:
        proc = subprocess.Popen(
            [sys.executable, str(MAS_DIR / "services" / "personaplex-local" / "personaplex_bridge_nvidia.py")],
            cwd=str(MAS_DIR),
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
        
        # Wait for it to start
        for _ in range(30):
            if check_port(8999):
                fixes_applied.append({
                    "issue": "Bridge not running",
                    "fix": "Started PersonaPlex Bridge",
                    "success": True
                })
                log("fix", "Bridge started successfully!")
                return True
            time.sleep(1)
        
        fixes_applied.append({
            "issue": "Bridge not running",
            "fix": "Attempted to start Bridge but timed out",
            "success": False
        })
        return False
    except Exception as e:
        log("error", f"Failed to start bridge: {e}")
        return False


def fix_moshi_not_running() -> bool:
    """Start Moshi server if not running."""
    log("fix", "Attempting to start Moshi Server...")
    
    try:
        proc = subprocess.Popen(
            [sys.executable, str(MAS_DIR / "start_personaplex.py")],
            cwd=str(MAS_DIR),
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
        
        # Wait for it to start (can take time for model loading)
        log("fix", "Waiting for Moshi model to load (this may take 1-2 minutes)...")
        for i in range(180):
            if check_port(8998):
                # Wait additional time for model initialization
                time.sleep(15)
                fixes_applied.append({
                    "issue": "Moshi not running",
                    "fix": "Started Moshi Server",
                    "success": True
                })
                log("fix", "Moshi started successfully!")
                return True
            if i % 30 == 0:
                log("fix", f"Still waiting for Moshi... ({i}s)")
            time.sleep(1)
        
        fixes_applied.append({
            "issue": "Moshi not running",
            "fix": "Attempted to start Moshi but timed out",
            "success": False
        })
        return False
    except Exception as e:
        log("error", f"Failed to start Moshi: {e}")
        return False


def fix_website_not_running() -> bool:
    """Start website dev server if not running."""
    log("fix", "Attempting to start Website dev server...")
    
    try:
        proc = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=str(WEBSITE_DIR),
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            shell=True,
        )
        
        # Wait for it to start
        for _ in range(30):
            if check_port(3010):
                fixes_applied.append({
                    "issue": "Website not running",
                    "fix": "Started Website dev server",
                    "success": True
                })
                log("fix", "Website started successfully!")
                return True
            time.sleep(1)
        
        fixes_applied.append({
            "issue": "Website not running",
            "fix": "Attempted to start Website but timed out",
            "success": False
        })
        return False
    except Exception as e:
        log("error", f"Failed to start website: {e}")
        return False


def apply_fixes() -> int:
    """Apply fixes for failed tests."""
    log("info", "=" * 60)
    log("info", "APPLYING AUTOMATIC FIXES")
    log("info", "=" * 60)
    
    fixes_count = 0
    
    # Check which services need fixing
    if not check_port(8998):
        log("fix", "Moshi not running - will attempt fix")
        if fix_moshi_not_running():
            fixes_count += 1
    
    if not check_port(8999):
        log("fix", "Bridge not running - will attempt fix")
        if fix_bridge_not_running():
            fixes_count += 1
    
    if not check_port(3010):
        log("fix", "Website not running - will attempt fix")
        if fix_website_not_running():
            fixes_count += 1
    
    return fixes_count


# =============================================================================
# REPORT GENERATION
# =============================================================================

def generate_report() -> str:
    """Generate comprehensive test report."""
    total = len(test_results)
    passed = sum(1 for r in test_results if r["passed"])
    failed = total - passed
    
    # Calculate pass rate
    pass_rate = (passed / total * 100) if total > 0 else 0
    
    report = f"""# MYCOSOFT Full System Test Report
## February 4, 2026 - {datetime.now().strftime("%H:%M:%S")}

## Executive Summary

| Metric | Value |
|--------|-------|
| Total Tests | {total} |
| Passed | {passed} |
| Failed | {failed} |
| Pass Rate | {pass_rate:.1f}% |
| Fixes Applied | {len(fixes_applied)} |

---

## Test Results by Phase

"""
    
    # Group tests by phase
    current_phase = None
    for result in test_results:
        name = result["name"]
        
        # Detect phase changes
        if "Port" in name and current_phase != "Ports":
            current_phase = "Ports"
            report += "\n### Phase 1: Service Ports\n\n| Test | Status | Duration | Details |\n|------|--------|----------|--------|\n"
        elif "Health" in name or "List" in name or "Home" in name:
            if current_phase != "HTTP":
                current_phase = "HTTP"
                report += "\n### Phase 2: HTTP Endpoints\n\n| Test | Status | Duration | Details |\n|------|--------|----------|--------|\n"
        elif "Memory" in name:
            if current_phase != "Memory":
                current_phase = "Memory"
                report += "\n### Phase 3: Memory System\n\n| Test | Status | Duration | Details |\n|------|--------|----------|--------|\n"
        elif "Voice" in name or "Session" in name:
            if current_phase != "Voice":
                current_phase = "Voice"
                report += "\n### Phase 4: Voice System\n\n| Test | Status | Duration | Details |\n|------|--------|----------|--------|\n"
        elif "WebSocket" in name:
            if current_phase != "WebSocket":
                current_phase = "WebSocket"
                report += "\n### Phase 5: WebSocket Connections\n\n| Test | Status | Duration | Details |\n|------|--------|----------|--------|\n"
        elif "Brain" in name or "Tool" in name:
            if current_phase != "Brain":
                current_phase = "Brain"
                report += "\n### Phase 6: Brain Engine\n\n| Test | Status | Duration | Details |\n|------|--------|----------|--------|\n"
        elif "Agent" in name:
            if current_phase != "Agent":
                current_phase = "Agent"
                report += "\n### Phase 7: Agent Registry\n\n| Test | Status | Duration | Details |\n|------|--------|----------|--------|\n"
        
        status = "PASS" if result["passed"] else "FAIL"
        details = result["details"][:50] + "..." if len(result["details"]) > 50 else result["details"]
        report += f"| {result['name']} | {status} | {result['duration_ms']:.0f}ms | {details} |\n"
    
    # Add fixes section
    if fixes_applied:
        report += "\n---\n\n## Fixes Applied\n\n"
        for fix in fixes_applied:
            status = "SUCCESS" if fix["success"] else "FAILED"
            report += f"- **{fix['issue']}**: {fix['fix']} ({status})\n"
    
    # Add failed tests section
    failed_tests = [r for r in test_results if not r["passed"]]
    if failed_tests:
        report += "\n---\n\n## Failed Tests\n\n"
        for test in failed_tests:
            report += f"- **{test['name']}**: {test['details']}\n"
    
    # Add system status
    report += f"""
---

## Current Service Status

| Service | Port | Host | Status |
|---------|------|------|--------|
| Moshi Server | 8998 | localhost | {"RUNNING" if check_port(8998) else "STOPPED"} |
| PersonaPlex Bridge | 8999 | localhost | {"RUNNING" if check_port(8999) else "STOPPED"} |
| MAS Orchestrator | 8001 | 192.168.0.188 | {"RUNNING" if check_port(8001, "192.168.0.188") else "STOPPED"} |
| Website | 3010 | localhost | {"RUNNING" if check_port(3010) else "STOPPED"} |
| Redis | 6379 | localhost | {"RUNNING" if check_port(6379) else "STOPPED"} |

---

## Test URLs

- **Test Voice Page**: http://localhost:3010/test-voice
- **Native Moshi UI**: http://localhost:8998
- **AI Studio**: http://localhost:3010/natureos/ai-studio
- **Agent Topology**: http://localhost:3010/natureos/mas/topology

---

## Log File

Full logs saved to: `{LOG_FILE}`

---

*Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
*Test Run ID: {RUN_TIMESTAMP}*
"""
    
    return report


# =============================================================================
# MAIN EXECUTION
# =============================================================================

async def run_all_tests() -> Tuple[int, int]:
    """Run all tests and return (passed, total)."""
    passed = 0
    
    passed += test_service_ports()
    passed += test_http_endpoints()
    passed += test_memory_system()
    passed += test_voice_system()
    passed += await test_websocket_connections()
    passed += test_brain_system()
    passed += test_agent_system()
    
    return passed, len(test_results)


async def main():
    """Main entry point."""
    log("info", "=" * 70)
    log("info", "MYCOSOFT FULL SYSTEM AUTOMATED TEST")
    log("info", f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("info", "=" * 70)
    
    # Install required packages
    try:
        import requests
        import aiohttp
    except ImportError:
        log("info", "Installing required packages...")
        subprocess.run([sys.executable, "-m", "pip", "install", "requests", "aiohttp", "-q"], check=True)
        import requests
        import aiohttp
    
    # Phase 1: Initial Tests
    log("info", "")
    log("info", "RUNNING INITIAL TESTS...")
    initial_passed, initial_total = await run_all_tests()
    initial_failures = [r for r in test_results if not r["passed"]]
    
    log("info", "")
    log("info", f"INITIAL RESULTS: {initial_passed}/{initial_total} tests passed")
    
    # Phase 2: Apply Fixes if needed
    if initial_failures:
        log("info", "")
        fixes = apply_fixes()
        
        if fixes > 0:
            log("info", f"Applied {fixes} fixes. Waiting 10 seconds before re-testing...")
            time.sleep(10)
            
            # Phase 3: Re-run Tests
            log("info", "")
            log("info", "RE-RUNNING TESTS AFTER FIXES...")
            test_results.clear()  # Clear previous results
            final_passed, final_total = await run_all_tests()
            
            log("info", "")
            log("info", f"FINAL RESULTS: {final_passed}/{final_total} tests passed")
        else:
            log("info", "No automatic fixes could be applied.")
            final_passed, final_total = initial_passed, initial_total
    else:
        log("info", "All tests passed on first run!")
        final_passed, final_total = initial_passed, initial_total
    
    # Phase 4: Generate Report
    log("info", "")
    log("info", "GENERATING TEST REPORT...")
    report = generate_report()
    
    report_file = REPORT_DIR / f"SYSTEM_TEST_REPORT_FEB04_2026.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    
    log("info", f"Report saved to: {report_file}")
    
    # Also save JSON results
    json_file = MAS_DIR / "tests" / f"system_test_results_{RUN_TIMESTAMP}.json"
    json_file.parent.mkdir(exist_ok=True)
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "run_id": RUN_TIMESTAMP,
            "summary": {
                "total": final_total,
                "passed": final_passed,
                "failed": final_total - final_passed,
                "pass_rate": (final_passed / final_total * 100) if final_total > 0 else 0,
            },
            "results": test_results,
            "fixes": fixes_applied,
        }, f, indent=2)
    
    log("info", f"JSON results saved to: {json_file}")
    
    # Final Summary
    log("info", "")
    log("info", "=" * 70)
    log("info", "TEST RUN COMPLETE")
    log("info", f"Final Score: {final_passed}/{final_total} ({final_passed/final_total*100:.1f}%)")
    log("info", f"Report: {report_file}")
    log("info", "=" * 70)
    
    return final_passed == final_total


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest run cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTest run failed: {e}")
        traceback.print_exc()
        sys.exit(1)
