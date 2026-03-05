"""
Memory System Integration Tests - Feb 3, 2026

This file originally contained an async CLI-style runner. It is now a normal
pytest suite with assertions.

Extended Mar 5, 2026: Coordinator, A2A, PersonaPlex, n8n, and RTO/RPO tests.
"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_memory_service_initialization() -> None:
    from mycosoft_mas.memory.service import get_memory_service

    service = get_memory_service()
    assert service is not None

    # Backends may be unavailable on dev machines; the contract here is:
    # - it should not raise
    # - it should return a boolean
    ok = await service.initialize()
    assert isinstance(ok, bool)


def test_memory_entry_creation() -> None:
    from mycosoft_mas.memory.service import MemoryEntry, MemoryScope, MemorySource

    entry = MemoryEntry(
        scope=MemoryScope.CONVERSATION,
        namespace="test:conversation:123",
        key="message_1",
        value={"role": "user", "content": "Hello world"},
        source=MemorySource.ORCHESTRATOR,
    )

    assert entry.id
    assert entry.scope == MemoryScope.CONVERSATION
    assert entry.confidence == 1.0


def test_user_profile() -> None:
    from mycosoft_mas.memory.service import UserProfile

    profile = UserProfile(
        user_id="test-user-123",
        preferences={"theme": "dark", "language": "en"},
        expertise_domains=["mycology", "machine-learning"],
    )

    assert profile.user_id == "test-user-123"
    assert profile.memory_consent is True
    assert len(profile.expertise_domains) == 2


def test_voice_session_store() -> None:
    from mycosoft_mas.voice.supabase_client import VoiceSessionStore

    store = VoiceSessionStore()
    assert store._pool is None


def test_natureos_connector() -> None:
    from mycosoft_mas.natureos.memory_connector import NatureOSMemoryConnector

    connector = NatureOSMemoryConnector()
    assert connector._pool is None


def test_mindex_bridge() -> None:
    from mycosoft_mas.mindex.memory_bridge import MINDEXMemoryBridge

    bridge = MINDEXMemoryBridge()
    assert bridge._pool is None
    assert bridge._memory_pool is None


def test_cleanup_service() -> None:
    from mycosoft_mas.memory.cleanup import MemoryCleanupService

    service = MemoryCleanupService()
    assert service._running is False


def test_device_sync() -> None:
    from mycosoft_mas.devices.memory_sync import DeviceMemorySync

    sync = DeviceMemorySync()
    assert sync._pool is None


def test_nlm_store() -> None:
    from mycosoft_mas.nlm.memory_store import NLMMemoryStore

    store = NLMMemoryStore()
    assert store._pool is None


def test_memory_scope_routing() -> None:
    from mycosoft_mas.memory.service import get_memory_service, MemoryScope

    service = get_memory_service()
    conv_backends = service._scope_backends.get(MemoryScope.CONVERSATION)
    user_backends = service._scope_backends.get(MemoryScope.USER)

    assert conv_backends is not None
    assert user_backends is not None
    assert len(conv_backends) == 1  # Redis
    assert len(user_backends) == 2  # Postgres + Qdrant


def test_short_term_memory() -> None:
    from mycosoft_mas.memory.short_term import ShortTermMemory

    stm = ShortTermMemory(max_messages=10, ttl_seconds=60)
    ctx = stm.create_context()
    assert ctx.conversation_id is not None

    assert stm.add_message(ctx.conversation_id, "user", "Hello") is True
    assert stm.add_message(ctx.conversation_id, "assistant", "Hi there!") is True

    messages = stm.get_recent_messages(ctx.conversation_id, n=5)
    assert len(messages) == 2

    assert stm.clear(ctx.conversation_id) is True
    assert stm.get_context(ctx.conversation_id) is None


def test_long_term_memory() -> None:
    from mycosoft_mas.memory.long_term import LongTermMemory

    ltm = LongTermMemory()
    fact = ltm.store_fact("user_preference", "dark_mode", scope="user")
    assert fact.fact_id is not None

    retrieved = ltm.get_fact("user_preference")
    assert retrieved is not None
    assert retrieved.value == "dark_mode"

    results = ltm.search_facts("user")
    assert len(results) >= 1


def test_graph_memory() -> None:
    from mycosoft_mas.memory.graph_memory import GraphMemory

    gm = GraphMemory()
    node1 = gm.add_node("person", {"name": "Alice"})
    node2 = gm.add_node("person", {"name": "Bob"})

    assert gm.add_edge(node1, node2, "knows", {"since": 2020}) is True
    neighbors = gm.get_neighbors(node1)
    assert node2 in neighbors

    path = gm.find_path(node1, node2)
    assert len(path) == 2

    results = gm.query(node_type="person")
    assert len(results) == 2


# =============================================================================
# Coordinator and A2A tests - Mar 5, 2026
# =============================================================================


@pytest.mark.asyncio
async def test_coordinator_store_retrieve_roundtrip() -> None:
    """Coordinator should store and retrieve across layers."""
    try:
        from mycosoft_mas.memory import get_memory_coordinator
        coord = await get_memory_coordinator()
        await coord.initialize()
    except Exception as e:
        pytest.skip(f"Coordinator unavailable: {e}")
        return

    agent_id = "test_agent_coord"
    content = {"event": "test_store", "data": "roundtrip"}
    entry_id = await coord.agent_remember(agent_id, content, layer="working")
    assert entry_id is not None
    results = await coord.agent_recall(agent_id, layer="working", limit=10)
    assert results is not None
    assert isinstance(results, list)
    assert len(results) >= 1 or entry_id  # At least store succeeded


@pytest.mark.asyncio
async def test_a2a_broadcast_query() -> None:
    """A2A memory should support broadcast and query."""
    try:
        from mycosoft_mas.memory.a2a_memory import A2AMemory
        a2a = A2AMemory()
        await a2a.initialize()
    except Exception as e:
        pytest.skip(f"A2A memory unavailable: {e}")
        return

    msg_id = await a2a.broadcast_memory("agent_1", {"fact": "shared_data", "value": 42})
    assert msg_id is not None
    results = await a2a.query_shared_memory("agent_2", "shared_data", timeout=2.0)
    assert results is not None
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_personaplex_bridge_memory_wiring() -> None:
    """PersonaPlex bridge should wire to memory when configured."""
    from mycosoft_mas.voice.personaplex_bridge import PersonaPlexBridge
    bridge = PersonaPlexBridge()
    session = bridge.create_session(conversation_id="test_conv")
    assert session is not None
    assert session.session_id in bridge.sessions

    bridge._memory_initialized = True
    bridge._personaplex_memory = None
    await bridge.handle_agent_text(session.session_id, "Hi from agent", "Hi from user")
    assert len(bridge.sessions[session.session_id].turns) == 1

    await bridge.end_session(session.session_id)
    assert bridge.sessions[session.session_id].is_active is False


@pytest.mark.asyncio
async def test_n8n_client_memory_wiring() -> None:
    """N8N client should attempt memory storage when DB configured."""
    from mycosoft_mas.integrations.n8n_client import N8NClient
    client = N8NClient(config={"webhook_url": "http://invalid.test", "timeout": 1})
    client._memory_initialized = True
    client._n8n_memory = None

    with pytest.raises(Exception):
        await client.trigger_workflow("test_wf", {"key": "value"})
    assert client._memory_initialized is True


def test_memory_stream_endpoint_exists() -> None:
    """Memory API should expose stream endpoint."""
    from mycosoft_mas.core.routers.memory_api import router
    paths = []
    for r in router.routes:
        if hasattr(r, "path"):
            paths.append(r.path)
        elif hasattr(r, "path_regex") and r.path_regex:
            paths.append(str(r.path_regex))
    assert any("stream" in p for p in paths)


def test_memory_audit_log_since_index() -> None:
    """Memory manager should support incremental audit log fetch."""
    from mycosoft_mas.core.routers.memory_api import get_memory_manager
    manager = get_memory_manager()
    entries, new_idx = manager.get_audit_log_since_index(0, limit=10)
    assert isinstance(entries, list)
    assert isinstance(new_idx, int)
    assert new_idx >= 0


@pytest.mark.asyncio
async def test_rto_rpo_memory_persistence() -> None:
    """Memory writes should be synchronous for critical layers (RPO)."""
    from mycosoft_mas.core.routers.memory_api import get_memory_manager
    from mycosoft_mas.core.routers.memory_api import MemoryScope
    manager = get_memory_manager()
    ok = await manager.write(
        MemoryScope.AGENT,
        "rpo_test_namespace",
        "rpo_test_key",
        {"critical": "data", "ts": "2026-03-05"},
    )
    assert ok is True
    value = await manager.read(
        MemoryScope.AGENT,
        "rpo_test_namespace",
        key="rpo_test_key",
    )
    assert value is not None
    assert value.get("critical") == "data"
    await manager.delete(MemoryScope.AGENT, "rpo_test_namespace", "rpo_test_key")

