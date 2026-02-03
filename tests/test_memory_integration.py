"""
Memory System Integration Tests - February 3, 2026

Comprehensive tests for all memory flows across the MAS.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from uuid import uuid4

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestResult:
    def __init__(self, name: str, passed: bool, message: str = "", duration_ms: float = 0):
        self.name = name
        self.passed = passed
        self.message = message
        self.duration_ms = duration_ms


async def test_memory_service_initialization():
    """Test that the unified memory service initializes correctly."""
    from mycosoft_mas.memory.service import get_memory_service
    
    service = get_memory_service()
    assert service is not None, "Memory service should be created"
    
    # Test initialization (may fail if backends not available)
    try:
        result = await service.initialize()
        return TestResult("Memory Service Init", True, "Initialized successfully")
    except Exception as e:
        return TestResult("Memory Service Init", False, f"Init failed: {e}")


async def test_memory_entry_creation():
    """Test creating memory entries."""
    from mycosoft_mas.memory.service import MemoryEntry, MemoryScope, MemorySource
    
    entry = MemoryEntry(
        scope=MemoryScope.CONVERSATION,
        namespace="test:conversation:123",
        key="message_1",
        value={"role": "user", "content": "Hello world"},
        source=MemorySource.ORCHESTRATOR,
    )
    
    assert entry.id is not None
    assert entry.scope == MemoryScope.CONVERSATION
    assert entry.confidence == 1.0
    
    return TestResult("Memory Entry Creation", True, f"Entry created: {entry.id}")


async def test_user_profile():
    """Test user profile creation and retrieval."""
    from mycosoft_mas.memory.service import UserProfile
    
    profile = UserProfile(
        user_id="test-user-123",
        preferences={"theme": "dark", "language": "en"},
        expertise_domains=["mycology", "machine-learning"],
    )
    
    assert profile.user_id == "test-user-123"
    assert profile.memory_consent == True
    assert len(profile.expertise_domains) == 2
    
    return TestResult("User Profile", True, "Profile created successfully")


async def test_voice_session_store():
    """Test voice session store operations."""
    from mycosoft_mas.voice.supabase_client import VoiceSessionStore
    
    store = VoiceSessionStore()
    
    # Test object creation (connection may fail)
    assert store._pool is None, "Pool should be None before connect"
    
    return TestResult("Voice Session Store", True, "Store created, connection pending")


async def test_natureos_connector():
    """Test NatureOS memory connector."""
    from mycosoft_mas.natureos.memory_connector import NatureOSMemoryConnector
    
    connector = NatureOSMemoryConnector()
    assert connector._pool is None
    
    return TestResult("NatureOS Connector", True, "Connector created")


async def test_mindex_bridge():
    """Test MINDEX memory bridge."""
    from mycosoft_mas.mindex.memory_bridge import MINDEXMemoryBridge
    
    bridge = MINDEXMemoryBridge()
    assert bridge._pool is None
    assert bridge._memory_pool is None
    
    return TestResult("MINDEX Bridge", True, "Bridge created")


async def test_cleanup_service():
    """Test memory cleanup service."""
    from mycosoft_mas.memory.cleanup import MemoryCleanupService
    
    service = MemoryCleanupService()
    assert service._running == False
    
    return TestResult("Cleanup Service", True, "Service created")


async def test_device_sync():
    """Test device memory sync."""
    from mycosoft_mas.devices.memory_sync import DeviceMemorySync
    
    sync = DeviceMemorySync()
    assert sync._pool is None
    
    return TestResult("Device Sync", True, "Sync created")


async def test_nlm_store():
    """Test NLM memory store."""
    from mycosoft_mas.nlm.memory_store import NLMMemoryStore
    
    store = NLMMemoryStore()
    assert store._pool is None
    
    return TestResult("NLM Store", True, "Store created")


async def test_memory_scope_routing():
    """Test that memory scopes route to correct backends."""
    from mycosoft_mas.memory.service import get_memory_service, MemoryScope
    
    service = get_memory_service()
    
    # Check scope to backend mapping
    conv_backends = service._scope_backends.get(MemoryScope.CONVERSATION)
    user_backends = service._scope_backends.get(MemoryScope.USER)
    
    assert len(conv_backends) == 1, "Conversation should use 1 backend (Redis)"
    assert len(user_backends) == 2, "User should use 2 backends (Postgres, Qdrant)"
    
    return TestResult("Scope Routing", True, "Scopes correctly mapped to backends")


async def test_short_term_memory():
    """Test short-term memory operations."""
    from mycosoft_mas.memory import ShortTermMemory
    
    stm = ShortTermMemory(max_messages=10, ttl_seconds=60)
    
    # Create context
    ctx = stm.create_context()
    assert ctx.conversation_id is not None
    
    # Add messages
    stm.add_message(ctx.conversation_id, "user", "Hello")
    stm.add_message(ctx.conversation_id, "assistant", "Hi there!")
    
    # Get messages
    messages = stm.get_recent_messages(ctx.conversation_id, n=5)
    assert len(messages) == 2
    
    # Clear
    stm.clear(ctx.conversation_id)
    ctx2 = stm.get_context(ctx.conversation_id)
    assert ctx2 is None
    
    return TestResult("Short-Term Memory", True, "STM operations work correctly")


async def test_long_term_memory():
    """Test long-term memory operations."""
    from mycosoft_mas.memory import LongTermMemory
    
    ltm = LongTermMemory()
    
    # Store fact
    fact = ltm.store_fact("user_preference", "dark_mode", scope="user")
    assert fact.fact_id is not None
    
    # Get fact
    retrieved = ltm.get_fact("user_preference")
    assert retrieved is not None
    assert retrieved.value == "dark_mode"
    
    # Search
    results = ltm.search_facts("user")
    assert len(results) >= 1
    
    return TestResult("Long-Term Memory", True, "LTM operations work correctly")


async def test_vector_memory():
    """Test vector memory operations."""
    from mycosoft_mas.memory import VectorMemory
    
    vm = VectorMemory(dimension=8)  # Small dimension for testing
    
    # Add entry
    embedding = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    entry_id = await vm.add("Test content", embedding, {"tag": "test"})
    assert entry_id is not None
    
    # Search
    results = await vm.search(embedding, top_k=1)
    assert len(results) == 1
    assert results[0][2] == "Test content"
    
    # Delete
    deleted = vm.delete(entry_id)
    assert deleted == True
    
    return TestResult("Vector Memory", True, "Vector memory operations work correctly")


async def test_graph_memory():
    """Test graph memory operations."""
    from mycosoft_mas.memory import GraphMemory
    
    gm = GraphMemory()
    
    # Add nodes
    node1 = gm.add_node("person", {"name": "Alice"})
    node2 = gm.add_node("person", {"name": "Bob"})
    
    # Add edge
    gm.add_edge(node1, node2, "knows", {"since": 2020})
    
    # Get neighbors
    neighbors = gm.get_neighbors(node1)
    assert node2 in neighbors
    
    # Find path
    path = gm.find_path(node1, node2)
    assert len(path) == 2
    
    # Query by type
    results = gm.query(node_type="person")
    assert len(results) == 2
    
    return TestResult("Graph Memory", True, "Graph memory operations work correctly")


async def run_all_tests():
    """Run all integration tests."""
    print("\n" + "=" * 60)
    print("MYCOSOFT MAS - Memory System Integration Tests")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\n")
    
    tests = [
        test_memory_entry_creation,
        test_user_profile,
        test_memory_scope_routing,
        test_short_term_memory,
        test_long_term_memory,
        test_vector_memory,
        test_graph_memory,
        test_voice_session_store,
        test_natureos_connector,
        test_mindex_bridge,
        test_cleanup_service,
        test_device_sync,
        test_nlm_store,
        test_memory_service_initialization,
    ]
    
    results = []
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            start = datetime.now()
            result = await test()
            result.duration_ms = (datetime.now() - start).total_seconds() * 1000
            results.append(result)
            
            status = "PASS" if result.passed else "FAIL"
            print(f"[{status}] {result.name}: {result.message} ({result.duration_ms:.1f}ms)")
            
            if result.passed:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            result = TestResult(test.__name__, False, str(e))
            results.append(result)
            print(f"[FAIL] {test.__name__}: {e}")
            failed += 1
    
    print("\n" + "-" * 60)
    print(f"Results: {passed} passed, {failed} failed, {len(tests)} total")
    print("-" * 60)
    
    # Save results to JSON
    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "passed": passed,
            "failed": failed,
            "total": len(tests),
        },
        "tests": [
            {
                "name": r.name,
                "passed": r.passed,
                "message": r.message,
                "duration_ms": r.duration_ms,
            }
            for r in results
        ]
    }
    
    with open("tests/memory_integration_results.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\nResults saved to tests/memory_integration_results.json")
    
    return passed, failed


if __name__ == "__main__":
    passed, failed = asyncio.run(run_all_tests())
    sys.exit(0 if failed == 0 else 1)
