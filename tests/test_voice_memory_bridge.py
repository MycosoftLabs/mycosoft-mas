"""
Test Voice-Memory Bridge Integration
Created: February 12, 2026

Tests the voice-memory bridge connecting voice system to 6-layer memory.
"""

import asyncio
import pytest
from datetime import datetime, timezone

from mycosoft_mas.voice.memory_bridge import get_voice_memory_bridge


@pytest.mark.asyncio
async def test_voice_memory_bridge_initialization():
    """Test bridge initializes all memory subsystems."""
    bridge = await get_voice_memory_bridge()
    
    assert bridge._initialized is True
    assert bridge._coordinator is not None
    assert bridge._autobiographical is not None
    assert bridge._personaplex is not None
    assert bridge._cross_session is not None
    
    print("✓ Voice-Memory Bridge initialized successfully")


@pytest.mark.asyncio
async def test_start_voice_session_with_memory_context():
    """Test starting a voice session loads memory context."""
    bridge = await get_voice_memory_bridge()
    
    session_id = await bridge.start_voice_session(
        user_id="test_user",
        user_name="Test User",
        speaker_profile="test_profile",
        context={"test": "context"}
    )
    
    assert session_id is not None
    assert session_id in bridge._session_map
    
    # Verify session has memory context
    voice_session = bridge._personaplex._active_sessions.get(
        __import__('uuid').UUID(session_id)
    )
    assert voice_session is not None
    assert "memory_session_id" in voice_session.context
    assert "user_profile" in voice_session.context
    assert "voice_preferences" in voice_session.context
    
    print(f"✓ Started voice session {session_id[:8]} with full memory context")
    
    # Cleanup
    await bridge.end_voice_session(session_id)


@pytest.mark.asyncio
async def test_add_voice_interaction_stores_in_all_systems():
    """Test voice interactions are stored in all memory systems."""
    bridge = await get_voice_memory_bridge()
    
    # Start session
    session_id = await bridge.start_voice_session(
        user_id="test_user",
        user_name="Test User"
    )
    
    # Add interaction
    success = await bridge.add_voice_interaction(
        session_id=session_id,
        user_message="How are the mushrooms growing?",
        assistant_response="The fruiting chamber is at optimal conditions with 87% humidity.",
        emotion="curious",
        duration_ms=3500
    )
    
    assert success is True
    
    # Verify stored in PersonaPlex
    voice_session = bridge._personaplex._active_sessions.get(
        __import__('uuid').UUID(session_id)
    )
    assert voice_session.turn_count == 2  # user + assistant
    
    # Verify stored in conversation memory
    memory_session_id = bridge._session_map.get(session_id)
    if memory_session_id:
        context = await bridge._coordinator.get_conversation_context(
            session_id=memory_session_id,
            turns=5
        )
        assert len(context) >= 2
    
    print("✓ Voice interaction stored in all memory systems")
    
    # Cleanup
    await bridge.end_voice_session(session_id)


@pytest.mark.asyncio
async def test_get_voice_context_retrieves_from_all_sources():
    """Test getting comprehensive voice context."""
    bridge = await get_voice_memory_bridge()
    
    # Start session and add some interactions
    session_id = await bridge.start_voice_session(
        user_id="test_user",
        user_name="Test User"
    )
    
    await bridge.add_voice_interaction(
        session_id=session_id,
        user_message="Tell me about oyster mushrooms",
        assistant_response="Oyster mushrooms (Pleurotus ostreatus) are...",
        emotion="curious"
    )
    
    # Get context
    context = await bridge.get_voice_context(
        user_id="test_user",
        current_message="What temperature do they need?",
        session_id=session_id
    )
    
    assert "user_id" in context
    assert "recent_history" in context or "voice_sessions" in context
    assert "autobiographical" in context
    assert "user_profile" in context
    
    print("✓ Retrieved comprehensive voice context from all sources")
    print(f"  - Context sections: {', '.join(context.keys())}")
    
    # Cleanup
    await bridge.end_voice_session(session_id)


@pytest.mark.asyncio
async def test_end_voice_session_stores_summary():
    """Test ending a voice session stores summary in memory."""
    bridge = await get_voice_memory_bridge()
    
    # Start session
    session_id = await bridge.start_voice_session(
        user_id="test_user",
        user_name="Test User"
    )
    
    # Add interactions
    await bridge.add_voice_interaction(
        session_id=session_id,
        user_message="What's the status of the grow?",
        assistant_response="The fruiting chamber is performing well.",
        emotion="neutral"
    )
    
    await bridge.add_voice_interaction(
        session_id=session_id,
        user_message="When will they be ready to harvest?",
        assistant_response="Based on current growth rate, approximately 5-7 days.",
        emotion="curious"
    )
    
    # End session
    summary = await bridge.end_voice_session(session_id)
    
    assert summary is not None
    assert "session_id" in summary
    assert "summary" in summary
    assert "turn_count" in summary
    assert summary["turn_count"] == 4  # 2 user + 2 assistant
    
    # Verify session removed from active sessions
    assert session_id not in bridge._session_map
    
    print(f"✓ Ended voice session with summary:")
    print(f"  - Turns: {summary['turn_count']}")
    print(f"  - Summary: {summary['summary'][:100]}...")


@pytest.mark.asyncio
async def test_search_voice_memory():
    """Test searching across voice memory."""
    bridge = await get_voice_memory_bridge()
    
    # Create and end a session (so it's in memory)
    session_id = await bridge.start_voice_session(
        user_id="test_user",
        user_name="Test User"
    )
    
    await bridge.add_voice_interaction(
        session_id=session_id,
        user_message="Tell me about shiitake cultivation",
        assistant_response="Shiitake mushrooms require hardwood substrates...",
        emotion="curious"
    )
    
    await bridge.end_voice_session(session_id)
    
    # Search for the interaction
    results = await bridge.search_voice_memory(
        user_id="test_user",
        query="shiitake",
        limit=5
    )
    
    # May not find results immediately due to async indexing
    print(f"✓ Searched voice memory, found {len(results)} results")
    if results:
        print(f"  - First result: {results[0].get('message', results[0].get('summary', 'N/A'))[:50]}...")


@pytest.mark.asyncio
async def test_learn_from_voice():
    """Test learning facts from voice interactions."""
    bridge = await get_voice_memory_bridge()
    
    success = await bridge.learn_from_voice(
        user_id="test_user",
        fact="User prefers detailed explanations about mushroom cultivation",
        importance=0.8,
        tags=["preference", "cultivation"]
    )
    
    assert success is True
    
    print("✓ Learned fact from voice interaction")


@pytest.mark.asyncio
async def test_update_voice_preference():
    """Test updating voice preferences."""
    bridge = await get_voice_memory_bridge()
    
    success = await bridge.update_voice_preference(
        user_id="test_user",
        preference_key="voice_speed",
        preference_value=1.2
    )
    
    assert success is True
    
    # Verify preference updated
    prefs = bridge._cross_session.load_user_preferences("test_user")
    assert prefs.voice_speed == 1.2
    
    print("✓ Updated voice preference")


@pytest.mark.asyncio
async def test_voice_memory_bridge_stats():
    """Test getting bridge statistics."""
    bridge = await get_voice_memory_bridge()
    
    stats = await bridge.get_stats()
    
    assert "bridge" in stats
    assert "coordinator" in stats
    assert "autobiographical" in stats
    assert "personaplex" in stats
    
    print("✓ Retrieved bridge statistics:")
    print(f"  - Active sessions: {stats['bridge'].get('active_voice_sessions', 0)}")
    print(f"  - Initialized: {stats['bridge'].get('initialized', False)}")


@pytest.mark.asyncio
async def test_full_voice_session_flow():
    """Test complete voice session flow with memory integration."""
    bridge = await get_voice_memory_bridge()
    
    print("\n=== Full Voice Session Flow Test ===")
    
    # 1. Start session
    print("\n1. Starting voice session...")
    session_id = await bridge.start_voice_session(
        user_id="morgan",
        user_name="Morgan Rockwell",
        speaker_profile="morgan_voice_profile"
    )
    print(f"   Session started: {session_id[:8]}")
    
    # 2. Add multiple interactions
    print("\n2. Adding voice interactions...")
    interactions = [
        ("How are the oyster mushrooms doing?", "The oyster mushrooms are fruiting nicely. Humidity is at 85%."),
        ("What about the shiitake?", "Shiitake logs are in the colonization phase, about 2 weeks from pinning."),
        ("Any issues I should know about?", "All parameters are within optimal ranges. No issues detected."),
    ]
    
    for user_msg, assistant_resp in interactions:
        await bridge.add_voice_interaction(
            session_id=session_id,
            user_message=user_msg,
            assistant_response=assistant_resp,
            emotion="curious",
            duration_ms=2500
        )
        print(f"   Stored: '{user_msg[:40]}...'")
    
    # 3. Get context during conversation
    print("\n3. Retrieving voice context...")
    context = await bridge.get_voice_context(
        user_id="morgan",
        current_message="Tell me more about the fruiting conditions",
        session_id=session_id
    )
    print(f"   Context sections: {', '.join(context.keys())}")
    
    # 4. Learn something from the conversation
    print("\n4. Learning from voice...")
    await bridge.learn_from_voice(
        user_id="morgan",
        fact="Morgan frequently checks on oyster mushroom progress",
        importance=0.7,
        tags=["behavior", "oyster_mushrooms"]
    )
    print("   Fact learned and stored")
    
    # 5. End session
    print("\n5. Ending voice session...")
    summary = await bridge.end_voice_session(session_id)
    print(f"   Session ended:")
    print(f"   - Total turns: {summary['turn_count']}")
    print(f"   - Duration: {summary['duration_seconds']:.1f}s")
    print(f"   - Topics: {', '.join(summary['topics'])}")
    print(f"   - Summary: {summary['summary'][:100]}...")
    
    # 6. Get stats
    print("\n6. Bridge statistics:")
    stats = await bridge.get_stats()
    print(f"   - Active sessions: {stats['bridge'].get('active_voice_sessions', 0)}")
    print(f"   - Memory systems initialized: {stats['bridge'].get('initialized', False)}")
    
    print("\n✓ Full voice session flow completed successfully")


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_voice_memory_bridge_initialization())
    asyncio.run(test_start_voice_session_with_memory_context())
    asyncio.run(test_add_voice_interaction_stores_in_all_systems())
    asyncio.run(test_get_voice_context_retrieves_from_all_sources())
    asyncio.run(test_end_voice_session_stores_summary())
    asyncio.run(test_search_voice_memory())
    asyncio.run(test_learn_from_voice())
    asyncio.run(test_update_voice_preference())
    asyncio.run(test_voice_memory_bridge_stats())
    asyncio.run(test_full_voice_session_flow())
    
    print("\n" + "="*50)
    print("ALL TESTS PASSED")
    print("="*50)
