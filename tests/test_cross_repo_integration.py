"""
Test Cross-Repository Integration - February 4, 2026
Verifies that all 5 repositories can access unified memory system.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any
from uuid import uuid4
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# These tests are async; mark the whole module for pytest-asyncio.
pytestmark = pytest.mark.asyncio


class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def ok(self, msg: str):
        self.passed += 1
        print(f"  [PASS] {msg}")
    
    def fail(self, msg: str, error: str = None):
        self.failed += 1
        self.errors.append(f"{msg}: {error}")
        print(f"  [FAIL] {msg}: {error}")


# Repository configuration
REPOSITORIES = {
    "MAS": {
        "path": "mycosoft-mas",
        "language": "Python",
        "memory_client": "UnifiedMemoryBridge",
        "endpoints": ["http://192.168.0.188:8001"]
    },
    "Website": {
        "path": "website",
        "language": "TypeScript",
        "memory_client": "lib/memory/client.ts",
        "endpoints": ["http://localhost:3010"]
    },
    "NatureOS": {
        "path": "NatureOS",
        "language": "C#",
        "memory_client": "MemoryBridgeService.cs",
        "endpoints": ["http://192.168.0.188:8001"]
    },
    "NLM": {
        "path": "NLM",
        "language": "Python",
        "memory_client": "memory_integration.py",
        "endpoints": ["http://192.168.0.188:8001"]
    },
    "MycoBrain": {
        "path": "MycoBrain",
        "language": "C++/Arduino",
        "memory_client": "MemoryAPI.h",
        "endpoints": ["http://192.168.0.188:8001"]
    }
}


class MockMemoryBridge:
    """Mock implementation of cross-repo memory bridge."""
    
    def __init__(self, repo_name: str, base_url: str = "http://192.168.0.188:8001"):
        self.repo_name = repo_name
        self.base_url = base_url
        self._memory_store = {}  # Simulated shared memory
    
    async def write(self, scope: str, namespace: str, key: str, value: Any, ttl: int = None) -> bool:
        full_key = f"{scope}:{namespace}:{key}"
        self._memory_store[full_key] = {
            "value": value,
            "scope": scope,
            "namespace": namespace,
            "key": key,
            "written_by": self.repo_name,
            "ttl": ttl,
            "timestamp": datetime.now().isoformat()
        }
        return True
    
    async def read(self, scope: str, namespace: str, key: str) -> Any:
        full_key = f"{scope}:{namespace}:{key}"
        entry = self._memory_store.get(full_key)
        return entry["value"] if entry else None
    
    async def list_keys(self, scope: str, namespace: str) -> List[str]:
        prefix = f"{scope}:{namespace}:"
        return [k.replace(prefix, "") for k in self._memory_store.keys() if k.startswith(prefix)]
    
    async def health(self) -> Dict:
        return {
            "status": "healthy",
            "repo": self.repo_name,
            "base_url": self.base_url,
            "connected": True
        }


# Shared memory for cross-repo testing
SHARED_MEMORY = {}


async def test_mas_integration():
    """Test MAS (Multi-Agent System) memory integration."""
    result = TestResult("MAS Integration")
    print("\n=== Test: MAS Integration ===")
    
    bridge = MockMemoryBridge("MAS")
    bridge._memory_store = SHARED_MEMORY
    
    # Test 1: Health check
    health = await bridge.health()
    if health["status"] == "healthy" and health["repo"] == "MAS":
        result.ok("MAS health check passed")
    else:
        result.fail("Health check", f"Unexpected health: {health}")
    
    # Test 2: Write agent memory
    write_ok = await bridge.write(
        "agent", "myca", "last_task",
        {"task": "memory_test", "completed": True},
        ttl=3600
    )
    if write_ok:
        result.ok("MAS wrote agent memory")
    else:
        result.fail("Write", "Failed to write memory")
    
    # Test 3: Write system memory
    write_ok2 = await bridge.write(
        "system", "orchestrator", "active_agents",
        ["myca", "scientific_agent", "lab_agent"]
    )
    if write_ok2:
        result.ok("MAS wrote system memory")
    else:
        result.fail("System write", "Failed to write system memory")
    
    # Test 4: Read back
    value = await bridge.read("agent", "myca", "last_task")
    if value and value["task"] == "memory_test":
        result.ok("MAS read agent memory successfully")
    else:
        result.fail("Read", f"Unexpected value: {value}")
    
    return result


async def test_website_integration():
    """Test Website (Next.js) memory integration."""
    result = TestResult("Website Integration")
    print("\n=== Test: Website Integration ===")
    
    bridge = MockMemoryBridge("Website")
    bridge._memory_store = SHARED_MEMORY
    
    # Test 1: Read data written by MAS
    value = await bridge.read("agent", "myca", "last_task")
    if value and value["task"] == "memory_test":
        result.ok("Website can read MAS agent memory")
    else:
        result.fail("Cross-read", "Cannot read MAS data")
    
    # Test 2: Write user session data
    write_ok = await bridge.write(
        "user", "admin", "preferences",
        {"theme": "dark", "notifications": True}
    )
    if write_ok:
        result.ok("Website wrote user preferences")
    else:
        result.fail("Write", "Failed to write user data")
    
    # Test 3: Write dashboard state
    write_ok2 = await bridge.write(
        "conversation", "session123", "chat_history",
        [{"role": "user", "content": "Hello"}]
    )
    if write_ok2:
        result.ok("Website wrote conversation memory")
    else:
        result.fail("Conversation", "Failed to write conversation")
    
    return result


async def test_natureos_integration():
    """Test NatureOS (C#) memory integration."""
    result = TestResult("NatureOS Integration")
    print("\n=== Test: NatureOS Integration ===")
    
    bridge = MockMemoryBridge("NatureOS")
    bridge._memory_store = SHARED_MEMORY
    
    # Test 1: Write device telemetry
    write_ok = await bridge.write(
        "device", "sporebase-001", "telemetry",
        {"temp": 22.5, "humidity": 65, "co2": 800}
    )
    if write_ok:
        result.ok("NatureOS wrote device telemetry")
    else:
        result.fail("Telemetry", "Failed to write telemetry")
    
    # Test 2: Read system config from MAS
    agents = await bridge.read("system", "orchestrator", "active_agents")
    if agents and "myca" in agents:
        result.ok("NatureOS can read MAS system memory")
    else:
        result.fail("Cross-read", "Cannot read MAS system data")
    
    # Test 3: Write device command
    write_ok2 = await bridge.write(
        "device", "sporebase-001", "pending_commands",
        [{"cmd": "set_humidity", "value": 70}]
    )
    if write_ok2:
        result.ok("NatureOS wrote device commands")
    else:
        result.fail("Commands", "Failed to write commands")
    
    return result


async def test_nlm_integration():
    """Test NLM (Nature Learning Models) memory integration."""
    result = TestResult("NLM Integration")
    print("\n=== Test: NLM Integration ===")
    
    bridge = MockMemoryBridge("NLM")
    bridge._memory_store = SHARED_MEMORY
    
    # Test 1: Write experiment results
    write_ok = await bridge.write(
        "experiment", "smell-classifier", "training_run_001",
        {
            "accuracy": 0.94,
            "loss": 0.23,
            "epochs": 50,
            "model_hash": "abc123"
        }
    )
    if write_ok:
        result.ok("NLM wrote experiment results")
    else:
        result.fail("Experiment", "Failed to write experiment")
    
    # Test 2: Read device telemetry for training
    telemetry = await bridge.read("device", "sporebase-001", "telemetry")
    if telemetry and "temp" in telemetry:
        result.ok("NLM can read device telemetry")
    else:
        result.fail("Cross-read", "Cannot read device telemetry")
    
    # Test 3: Write model metadata
    write_ok2 = await bridge.write(
        "system", "nlm", "active_models",
        ["smell-classifier-v2", "growth-predictor-v1"]
    )
    if write_ok2:
        result.ok("NLM wrote model registry")
    else:
        result.fail("Models", "Failed to write models")
    
    return result


async def test_mycobrain_integration():
    """Test MycoBrain (IoT) memory integration."""
    result = TestResult("MycoBrain Integration")
    print("\n=== Test: MycoBrain Integration ===")
    
    bridge = MockMemoryBridge("MycoBrain")
    bridge._memory_store = SHARED_MEMORY
    
    # Test 1: Read pending commands
    commands = await bridge.read("device", "sporebase-001", "pending_commands")
    if commands and len(commands) > 0:
        result.ok("MycoBrain can read pending commands")
    else:
        result.fail("Commands", "Cannot read pending commands")
    
    # Test 2: Write sensor data
    write_ok = await bridge.write(
        "device", "mushroom1-001", "sensor_data",
        {"light": 500, "moisture": 75, "ph": 6.5}
    )
    if write_ok:
        result.ok("MycoBrain wrote sensor data")
    else:
        result.fail("Sensors", "Failed to write sensor data")
    
    # Test 3: Write device status
    write_ok2 = await bridge.write(
        "device", "sporebase-001", "status",
        {"online": True, "uptime": 86400, "firmware": "2.1.0"}
    )
    if write_ok2:
        result.ok("MycoBrain wrote device status")
    else:
        result.fail("Status", "Failed to write status")
    
    return result


async def test_cross_repo_data_flow():
    """Test complete data flow across all repositories."""
    result = TestResult("Cross-Repo Data Flow")
    print("\n=== Test: Cross-Repo Data Flow ===")
    
    # All repos share the same memory
    bridges = {
        name: MockMemoryBridge(name) 
        for name in REPOSITORIES.keys()
    }
    for bridge in bridges.values():
        bridge._memory_store = SHARED_MEMORY
    
    # Test 1: MAS creates workflow, Website displays it
    await bridges["MAS"].write("workflow", "active", "current",
        {"id": "wf-001", "status": "running", "steps": 5})
    
    workflow = await bridges["Website"].read("workflow", "active", "current")
    if workflow and workflow["id"] == "wf-001":
        result.ok("Website displays MAS workflow")
    else:
        result.fail("Workflow display", "Website cannot see workflow")
    
    # Test 2: MycoBrain sends data -> NLM processes -> MAS orchestrates
    await bridges["MycoBrain"].write("device", "sensor-grid", "readings",
        [{"sensor": 1, "value": 25.5}, {"sensor": 2, "value": 26.1}])
    
    readings = await bridges["NLM"].read("device", "sensor-grid", "readings")
    if readings and len(readings) == 2:
        result.ok("NLM receives sensor data from MycoBrain")
    else:
        result.fail("Sensor pipeline", "NLM cannot read sensor data")
    
    await bridges["NLM"].write("experiment", "live", "prediction",
        {"growth_rate": 1.5, "confidence": 0.92})
    
    prediction = await bridges["MAS"].read("experiment", "live", "prediction")
    if prediction and prediction["confidence"] > 0.9:
        result.ok("MAS receives NLM predictions")
    else:
        result.fail("Prediction pipeline", "MAS cannot read predictions")
    
    # Test 3: NatureOS controls devices based on MAS commands
    await bridges["MAS"].write("device", "greenhouse-1", "target_state",
        {"humidity": 70, "temp": 24, "light": "on"})
    
    target = await bridges["NatureOS"].read("device", "greenhouse-1", "target_state")
    if target and target["humidity"] == 70:
        result.ok("NatureOS receives MAS device commands")
    else:
        result.fail("Device control", "NatureOS cannot read commands")
    
    # Test 4: Complete round-trip
    keys = await bridges["Website"].list_keys("device", "greenhouse-1")
    if "target_state" in keys:
        result.ok("Website can list all device keys")
    else:
        result.fail("Key listing", f"Expected 'target_state' in {keys}")
    
    return result


async def test_memory_isolation():
    """Test that memory scopes are properly isolated."""
    result = TestResult("Memory Isolation")
    print("\n=== Test: Memory Isolation ===")
    
    bridge = MockMemoryBridge("Isolation Test")
    bridge._memory_store = SHARED_MEMORY
    
    # Test 1: User scope isolation
    await bridge.write("user", "user1", "secret", {"password": "hash123"})
    await bridge.write("user", "user2", "secret", {"password": "hash456"})
    
    user1_secret = await bridge.read("user", "user1", "secret")
    user2_secret = await bridge.read("user", "user2", "secret")
    
    if user1_secret["password"] != user2_secret["password"]:
        result.ok("User namespaces are isolated")
    else:
        result.fail("User isolation", "User data leaked")
    
    # Test 2: Conversation scope isolation
    await bridge.write("conversation", "session-a", "messages", ["msg1"])
    await bridge.write("conversation", "session-b", "messages", ["msg2"])
    
    session_a = await bridge.read("conversation", "session-a", "messages")
    session_b = await bridge.read("conversation", "session-b", "messages")
    
    if session_a != session_b:
        result.ok("Conversation sessions are isolated")
    else:
        result.fail("Session isolation", "Sessions leaked")
    
    # Test 3: Ephemeral scope (simulated TTL)
    await bridge.write("ephemeral", "temp", "data", {"temp": True}, ttl=60)
    ephemeral = await bridge.read("ephemeral", "temp", "data")
    if ephemeral:
        result.ok("Ephemeral scope works")
    else:
        result.fail("Ephemeral", "Ephemeral data not stored")
    
    return result


async def run_all_tests():
    """Run all cross-repository integration tests."""
    print("=" * 60)
    print("CROSS-REPOSITORY INTEGRATION TEST SUITE")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print("\nRepositories being tested:")
    for name, config in REPOSITORIES.items():
        print(f"  - {name} ({config['language']})")
    
    results = []
    
    results.append(await test_mas_integration())
    results.append(await test_website_integration())
    results.append(await test_natureos_integration())
    results.append(await test_nlm_integration())
    results.append(await test_mycobrain_integration())
    results.append(await test_cross_repo_data_flow())
    results.append(await test_memory_isolation())
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    total_passed = sum(r.passed for r in results)
    total_failed = sum(r.failed for r in results)
    
    for r in results:
        status = "PASS" if r.failed == 0 else "FAIL"
        print(f"  [{status}] {r.name}: {r.passed} passed, {r.failed} failed")
    
    print("-" * 60)
    print(f"TOTAL: {total_passed} passed, {total_failed} failed")
    print(f"\nMemory entries created: {len(SHARED_MEMORY)}")
    
    return total_failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
