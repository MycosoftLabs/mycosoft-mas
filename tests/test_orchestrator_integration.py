"""
MYCA Orchestrator Integration Tests - February 2026

Comprehensive test suite for:
- PromptManager functionality
- Memory API operations
- Voice Session Manager
- Orchestrator endpoints
- End-to-end voice flow
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestResult:
    """Individual test result."""
    def __init__(self, name: str, passed: bool, message: str = "", duration_ms: float = 0):
        self.name = name
        self.passed = passed
        self.message = message
        self.duration_ms = duration_ms
    
    def to_dict(self):
        return {
            "name": self.name,
            "passed": self.passed,
            "message": self.message,
            "duration_ms": round(self.duration_ms, 2),
        }


class IntegrationTestSuite:
    """
    Integration test suite for MYCA orchestrator components.
    """
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.start_time = None
    
    def log(self, message: str):
        """Log a test message."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    async def run_all(self):
        """Run all integration tests."""
        self.start_time = datetime.now(timezone.utc)
        self.log("=" * 60)
        self.log("MYCA Orchestrator Integration Test Suite")
        self.log("=" * 60)
        
        # Test 1: PromptManager
        await self.test_prompt_manager()
        
        # Test 2: Memory API
        await self.test_memory_api()
        
        # Test 3: Voice Session Manager
        await self.test_voice_session_manager()
        
        # Test 4: Memory Summarization
        await self.test_memory_summarization()
        
        # Test 5: Orchestrator Chat Endpoint (mock)
        await self.test_orchestrator_chat()
        
        # Print summary
        self.print_summary()
        
        return self.results
    
    async def test_prompt_manager(self):
        """Test PromptManager functionality."""
        self.log("\n--- Test 1: PromptManager ---")
        
        import time
        start = time.monotonic()
        
        try:
            from mycosoft_mas.core.prompt_manager import PromptManager, get_prompt_manager, reset_prompt_manager
            
            # Reset and get fresh instance
            reset_prompt_manager()
            pm = get_prompt_manager()
            
            # Test 1.1: Full prompt loaded
            full_prompt = pm.full_prompt
            assert len(full_prompt) > 100, "Full prompt too short"
            self.log(f"  Full prompt: {len(full_prompt)} chars")
            
            # Test 1.2: Condensed prompt loaded
            condensed = pm.condensed_prompt
            assert len(condensed) > 50, "Condensed prompt too short"
            assert len(condensed) < 1500, "Condensed prompt too long"
            self.log(f"  Condensed prompt: {len(condensed)} chars")
            
            # Test 1.3: Orchestrator prompt with context
            orchestrator_prompt = pm.get_orchestrator_prompt(
                context={"test": "value"},
                active_agents=["agent1", "agent2"],
                user_info={"name": "Morgan", "role": "admin"},
            )
            assert "CURRENT OPERATIONAL CONTEXT" in orchestrator_prompt
            assert "Morgan" in orchestrator_prompt
            self.log(f"  Orchestrator prompt with context: {len(orchestrator_prompt)} chars")
            
            # Test 1.4: Voice prompt for Moshi
            voice_prompt = pm.get_voice_prompt_for_moshi(max_length=500)
            assert len(voice_prompt) <= 500
            self.log(f"  Moshi voice prompt: {len(voice_prompt)} chars")
            
            # Test 1.5: Info method
            info = pm.get_info()
            assert info["full_prompt_loaded"]
            assert info["condensed_prompt_loaded"]
            
            duration = (time.monotonic() - start) * 1000
            self.results.append(TestResult("PromptManager", True, "All checks passed", duration))
            self.log("  PASSED")
            
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            self.results.append(TestResult("PromptManager", False, str(e), duration))
            self.log(f"  FAILED: {e}")
    
    async def test_memory_api(self):
        """Test Memory API operations."""
        self.log("\n--- Test 2: Memory API ---")
        
        import time
        start = time.monotonic()
        
        try:
            from mycosoft_mas.core.routers.memory_api import (
                NamespacedMemoryManager,
                MemoryScope,
                get_memory_manager,
            )
            
            # Get memory manager (uses Redis)
            mm = get_memory_manager()
            
            # Test 2.1: Write operation
            test_namespace = f"test_{int(time.time())}"
            result = await mm.write(
                scope=MemoryScope.EPHEMERAL,
                namespace=test_namespace,
                key="test_key",
                value={"message": "Hello from test"},
                metadata={"test": True},
            )
            self.log(f"  Write: {'OK' if result else 'FAILED'}")
            
            # Test 2.2: Read operation
            value = await mm.read(
                scope=MemoryScope.EPHEMERAL,
                namespace=test_namespace,
                key="test_key",
            )
            assert value is not None
            assert value.get("message") == "Hello from test"
            self.log(f"  Read: OK (value: {value})")
            
            # Test 2.3: List keys
            keys = await mm.list_keys(MemoryScope.EPHEMERAL, test_namespace)
            assert "test_key" in keys
            self.log(f"  List keys: {keys}")
            
            # Test 2.4: Delete operation
            deleted = await mm.delete(
                scope=MemoryScope.EPHEMERAL,
                namespace=test_namespace,
                key="test_key",
            )
            self.log(f"  Delete: {'OK' if deleted else 'FAILED'}")
            
            # Test 2.5: Verify deletion
            value_after = await mm.read(
                scope=MemoryScope.EPHEMERAL,
                namespace=test_namespace,
                key="test_key",
            )
            assert value_after is None
            self.log(f"  Verify deletion: OK")
            
            # Test 2.6: Audit log
            audit = mm.get_audit_log(limit=10)
            assert len(audit) > 0
            self.log(f"  Audit log: {len(audit)} entries")
            
            duration = (time.monotonic() - start) * 1000
            self.results.append(TestResult("Memory API", True, "All operations passed", duration))
            self.log("  PASSED")
            
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            error_msg = str(e)
            if "redis" in error_msg.lower() or "connection" in error_msg.lower():
                self.results.append(TestResult("Memory API", False, f"Redis not available: {e}", duration))
                self.log(f"  SKIPPED (Redis not available)")
            else:
                self.results.append(TestResult("Memory API", False, error_msg, duration))
                self.log(f"  FAILED: {e}")
    
    async def test_voice_session_manager(self):
        """Test Voice Session Manager."""
        self.log("\n--- Test 3: Voice Session Manager ---")
        
        import time
        start = time.monotonic()
        
        try:
            from mycosoft_mas.voice.session_manager import (
                VoiceSession,
                VoiceConfig,
                VoiceSessionManager,
                VoiceMode,
                RTFStatus,
                get_session_manager,
            )
            
            # Test 3.1: Create VoiceSession
            session = VoiceSession(
                session_id="test_session_123",
                conversation_id="conv_456",
                user_id="test_user",
                persona_id="myca_default",
            )
            
            assert session.topology_node_id == "voice_session:conv_456"
            assert session.memory_namespace == "voice_conv_456"
            self.log(f"  Session created: {session.session_id}")
            
            # Test 3.2: RTF tracking
            session.record_rtf(generation_ms=30, audio_duration_ms=50)
            session.record_rtf(generation_ms=35, audio_duration_ms=50)
            session.record_rtf(generation_ms=40, audio_duration_ms=50)
            
            assert session.rtf_current == 0.8  # 40/50
            assert session.rtf_status == RTFStatus.WARNING  # 0.7-0.9
            self.log(f"  RTF tracking: current={session.rtf_current}, status={session.rtf_status.value}")
            
            # Test 3.3: Turn recording
            session.record_turn(agents_invoked=["code_review_agent", "monitoring_agent"])
            assert session.turn_count == 1
            assert "code_review_agent" in session.invoked_agents
            self.log(f"  Turn count: {session.turn_count}, agents: {session.invoked_agents}")
            
            # Test 3.4: to_dict
            session_dict = session.to_dict()
            assert session_dict["session_id"] == "test_session_123"
            assert "rtf" in session_dict
            self.log(f"  Session dict: OK")
            
            # Test 3.5: to_topology_node
            node = session.to_topology_node()
            assert node["id"] == "voice_session:conv_456"
            assert node["type"] == "voice_session"
            assert node["lifetime"] == "ephemeral"
            self.log(f"  Topology node: {node['id']}")
            
            # Test 3.6: VoiceSessionManager
            manager = get_session_manager()
            assert manager is not None
            self.log(f"  Manager initialized")
            
            # Test 3.7: RTF status escalation
            for i in range(30):
                session.record_rtf(generation_ms=60, audio_duration_ms=50)  # RTF = 1.2
            assert session.rtf_status in [RTFStatus.CRITICAL, RTFStatus.STUTTERING]
            self.log(f"  RTF escalation: {session.rtf_status.value}")
            
            duration = (time.monotonic() - start) * 1000
            self.results.append(TestResult("Voice Session Manager", True, "All checks passed", duration))
            self.log("  PASSED")
            
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            self.results.append(TestResult("Voice Session Manager", False, str(e), duration))
            self.log(f"  FAILED: {e}")
    
    async def test_memory_summarization(self):
        """Test Memory Summarization service."""
        self.log("\n--- Test 4: Memory Summarization ---")
        
        import time
        start = time.monotonic()
        
        try:
            from mycosoft_mas.core.memory_summarization import (
                MemorySummarizationService,
                get_summarization_service,
            )
            
            # Test 4.1: Get service
            service = get_summarization_service()
            assert service is not None
            self.log("  Service initialized")
            
            # Test 4.2: Extract topics
            messages = [
                "Check the status of proxmox server",
                "Show me the network health",
                "Deploy the new agent workflow",
            ]
            topics = service._extract_topics(messages)
            assert "status" in topics or "health" in topics or "agent" in topics
            self.log(f"  Topics extracted: {topics}")
            
            # Test 4.3: Extract key info
            turns = [
                {"role": "user", "content": "I prefer dark mode for all interfaces"},
                {"role": "assistant", "content": "I've noted your preference for dark mode."},
                {"role": "user", "content": "There's an error with the monitoring agent"},
                {"role": "assistant", "content": "Let me check that error for you."},
            ]
            info = service._extract_key_info(turns)
            assert len(info["preferences"]) > 0 or len(info["errors_mentioned"]) > 0
            self.log(f"  Key info: preferences={len(info['preferences'])}, errors={len(info['errors_mentioned'])}")
            
            # Test 4.4: Generate summary (local fallback)
            summary = await service._generate_summary(turns)
            assert "4 turns" in summary or "Conversation" in summary
            self.log(f"  Summary: {summary[:100]}...")
            
            duration = (time.monotonic() - start) * 1000
            self.results.append(TestResult("Memory Summarization", True, "All checks passed", duration))
            self.log("  PASSED")
            
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            self.results.append(TestResult("Memory Summarization", False, str(e), duration))
            self.log(f"  FAILED: {e}")
    
    async def test_orchestrator_chat(self):
        """Test Orchestrator chat endpoint logic."""
        self.log("\n--- Test 5: Orchestrator Chat ---")
        
        import time
        start = time.monotonic()
        
        try:
            from mycosoft_mas.core.routers.voice_orchestrator_api import (
                MYCAOrchestrator,
                VoiceOrchestratorRequest,
                get_orchestrator,
            )
            
            # Test 5.1: Get orchestrator
            orchestrator = get_orchestrator()
            assert orchestrator is not None
            self.log("  Orchestrator initialized")
            
            # Test 5.2: Intent analysis
            intent = orchestrator._analyze_intent("Check the status of all agents")
            assert intent["type"] == "query"
            assert intent["requires_tool"] == True
            self.log(f"  Intent analysis: {intent}")
            
            # Test 5.3: Dangerous action detection
            intent2 = orchestrator._analyze_intent("Delete all old logs")
            assert intent2["requires_confirmation"] == True
            self.log(f"  Dangerous action: confirmation required")
            
            # Test 5.4: Chitchat detection
            intent3 = orchestrator._analyze_intent("Hello, how are you?")
            assert intent3["type"] == "chitchat"
            self.log(f"  Chitchat detection: OK")
            
            # Test 5.5: Local response generation
            response = orchestrator._generate_local_response(
                "What's the weather like?",
                {"type": "chitchat", "requires_tool": False, "requires_confirmation": False}
            )
            assert "MYCA" in response
            self.log(f"  Local response: {response[:60]}...")
            
            # Test 5.6: Process request (without n8n)
            request = VoiceOrchestratorRequest(
                message="Hello MYCA, status check please",
                conversation_id="test_conv_123",
                session_id="test_session",
                source="test",
                modality="text",
            )
            
            # This will use fallback since n8n is not running
            response = await orchestrator.process(request)
            assert response.response_text is not None
            assert response.session_context is not None
            assert response.session_context.turn_count == 1
            self.log(f"  Process request: turn_count={response.session_context.turn_count}")
            
            duration = (time.monotonic() - start) * 1000
            self.results.append(TestResult("Orchestrator Chat", True, "All checks passed", duration))
            self.log("  PASSED")
            
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            self.results.append(TestResult("Orchestrator Chat", False, str(e), duration))
            self.log(f"  FAILED: {e}")
    
    def print_summary(self):
        """Print test summary."""
        self.log("\n" + "=" * 60)
        self.log("TEST SUMMARY")
        self.log("=" * 60)
        
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total = len(self.results)
        
        for result in self.results:
            status = "PASS" if result.passed else "FAIL"
            self.log(f"  [{status}] {result.name}: {result.message} ({result.duration_ms}ms)")
        
        self.log("-" * 60)
        self.log(f"Total: {total} | Passed: {passed} | Failed: {failed}")
        
        if failed == 0:
            self.log("ALL TESTS PASSED!")
        else:
            self.log(f"SOME TESTS FAILED: {failed}/{total}")
        
        # Save results to file
        end_time = datetime.now(timezone.utc)
        report = {
            "run_at": self.start_time.isoformat() if self.start_time else None,
            "completed_at": end_time.isoformat(),
            "total": total,
            "passed": passed,
            "failed": failed,
            "results": [r.to_dict() for r in self.results],
        }
        
        report_path = project_root / "tests" / "integration_test_results.json"
        report_path.parent.mkdir(exist_ok=True)
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        self.log(f"\nResults saved to: {report_path}")


async def main():
    """Run integration tests."""
    suite = IntegrationTestSuite()
    await suite.run_all()


if __name__ == "__main__":
    asyncio.run(main())
