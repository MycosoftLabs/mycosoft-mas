"""
Memory System Integration Tests - Feb 3, 2026

This file originally contained an async CLI-style runner. It is now a normal
pytest suite with assertions.
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

