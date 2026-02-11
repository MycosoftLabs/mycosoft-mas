#!/usr/bin/env python3
"""
Test MYCA Full Orchestrator Integration

Tests all 8 integration points:
1. Intent classification for all 6 intent types
2. Agent routing (delegate to Lab Agent)
3. MINDEX RAG (query about fungi species)
4. Tool execution (list tools)
5. N8N integration (trigger workflow)
6. System status queries (ask about agent status)
7. CREP awareness (ask about current flights/satellites)
8. Earth2 awareness (ask about weather predictions)

Created: Feb 11, 2026
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TestResult:
    """Result of a test case."""
    def __init__(self, name: str, passed: bool, message: str, details: Any = None):
        self.name = name
        self.passed = passed
        self.message = message
        self.details = details
    
    def __repr__(self):
        status = "[PASS]" if self.passed else "[FAIL]"
        return f"{status}: {self.name} - {self.message}"


async def test_intent_classification():
    """Test 1: Intent classification for all 6 types."""
    from mycosoft_mas.consciousness.intent_engine import get_intent_engine, IntentType
    
    results = []
    engine = get_intent_engine()
    
    test_cases = [
        ("Ask the lab agent to run an experiment", IntentType.AGENT_TASK),
        ("Execute the backup tool", IntentType.TOOL_CALL),
        ("Tell me about Amanita muscaria", IntentType.KNOWLEDGE_QUERY),
        ("Hello, how are you?", IntentType.GENERAL_CHAT),
        ("Trigger the backup workflow", IntentType.SYSTEM_COMMAND),
        ("What's the status of our agents?", IntentType.STATUS_QUERY),
    ]
    
    for message, expected_intent in test_cases:
        try:
            result = await engine.classify(message)
            passed = result.intent_type == expected_intent
            results.append(TestResult(
                name=f"Intent: {expected_intent.value}",
                passed=passed,
                message=f"'{message[:30]}...' -> {result.intent_type.value} (confidence: {result.confidence:.2f})",
                details={"expected": expected_intent.value, "got": result.intent_type.value}
            ))
        except Exception as e:
            results.append(TestResult(
                name=f"Intent: {expected_intent.value}",
                passed=False,
                message=f"Error: {e}"
            ))
    
    return results


async def test_unified_router():
    """Test 2: Unified Router - general routing."""
    from mycosoft_mas.consciousness.unified_router import get_unified_router
    
    results = []
    router = get_unified_router()
    
    test_messages = [
        "Are you alive and conscious?",
        "What is your name?",
        "How are you feeling today?",
    ]
    
    for message in test_messages:
        try:
            response_parts = []
            async for chunk in router.route(message):
                response_parts.append(chunk)
            
            response = "".join(response_parts)
            passed = len(response) > 10 and ("MYCA" in response or "conscious" in response or "I am" in response)
            
            results.append(TestResult(
                name=f"Route: '{message[:25]}...'",
                passed=passed,
                message=f"Got response ({len(response)} chars)",
                details={"response_preview": response[:100]}
            ))
        except Exception as e:
            results.append(TestResult(
                name=f"Route: '{message[:25]}...'",
                passed=False,
                message=f"Error: {e}"
            ))
    
    return results


async def test_agent_routing():
    """Test 3: Agent task delegation."""
    from mycosoft_mas.consciousness.unified_router import get_unified_router
    
    router = get_unified_router()
    
    try:
        response_parts = []
        async for chunk in router.route("Ask the lab agent to analyze the latest samples"):
            response_parts.append(chunk)
        
        response = "".join(response_parts)
        passed = len(response) > 10
        
        return [TestResult(
            name="Agent Delegation",
            passed=passed,
            message=f"Response: {response[:100]}...",
            details={"full_response": response}
        )]
    except Exception as e:
        return [TestResult(
            name="Agent Delegation",
            passed=False,
            message=f"Error: {e}"
        )]


async def test_mindex_rag():
    """Test 4: MINDEX RAG / Knowledge queries."""
    from mycosoft_mas.consciousness.unified_router import get_unified_router
    
    router = get_unified_router()
    
    try:
        response_parts = []
        async for chunk in router.route("Tell me about Amanita muscaria and its properties"):
            response_parts.append(chunk)
        
        response = "".join(response_parts)
        passed = len(response) > 20
        
        return [TestResult(
            name="MINDEX RAG Query",
            passed=passed,
            message=f"Knowledge response ({len(response)} chars)",
            details={"response_preview": response[:150]}
        )]
    except Exception as e:
        return [TestResult(
            name="MINDEX RAG Query",
            passed=False,
            message=f"Error: {e}"
        )]


async def test_tool_execution():
    """Test 5: Tool listing/execution."""
    from mycosoft_mas.consciousness.unified_router import get_unified_router
    
    router = get_unified_router()
    
    try:
        response_parts = []
        async for chunk in router.route("List available tools"):
            response_parts.append(chunk)
        
        response = "".join(response_parts)
        passed = len(response) > 10
        
        return [TestResult(
            name="Tool Listing",
            passed=passed,
            message=f"Tools response: {response[:100]}...",
            details={"response": response}
        )]
    except Exception as e:
        return [TestResult(
            name="Tool Listing",
            passed=False,
            message=f"Error: {e}"
        )]


async def test_system_status():
    """Test 6: System status queries."""
    from mycosoft_mas.consciousness.unified_router import get_unified_router
    
    router = get_unified_router()
    
    try:
        response_parts = []
        async for chunk in router.route("What's the status of our system?"):
            response_parts.append(chunk)
        
        response = "".join(response_parts)
        passed = len(response) > 20 and any(word in response.lower() for word in ["status", "system", "active", "operational", "consciousness"])
        
        return [TestResult(
            name="System Status Query",
            passed=passed,
            message=f"Status response: {response[:100]}...",
            details={"response": response}
        )]
    except Exception as e:
        return [TestResult(
            name="System Status Query",
            passed=False,
            message=f"Error: {e}"
        )]


async def test_crep_awareness():
    """Test 7: CREP awareness (flights, satellites)."""
    from mycosoft_mas.consciousness.unified_router import get_unified_router
    
    router = get_unified_router()
    
    try:
        response_parts = []
        async for chunk in router.route("How many flights are we tracking right now?"):
            response_parts.append(chunk)
        
        response = "".join(response_parts)
        passed = len(response) > 10
        
        return [TestResult(
            name="CREP Awareness",
            passed=passed,
            message=f"CREP response: {response[:100]}...",
            details={"response": response}
        )]
    except Exception as e:
        return [TestResult(
            name="CREP Awareness",
            passed=False,
            message=f"Error: {e}"
        )]


async def test_earth2_awareness():
    """Test 8: Earth2 predictions awareness."""
    from mycosoft_mas.consciousness.unified_router import get_unified_router
    
    router = get_unified_router()
    
    try:
        response_parts = []
        async for chunk in router.route("What's the weather prediction for today?"):
            response_parts.append(chunk)
        
        response = "".join(response_parts)
        passed = len(response) > 10
        
        return [TestResult(
            name="Earth2 Awareness",
            passed=passed,
            message=f"Earth2 response: {response[:100]}...",
            details={"response": response}
        )]
    except Exception as e:
        return [TestResult(
            name="Earth2 Awareness",
            passed=False,
            message=f"Error: {e}"
        )]


async def test_consciousness_awareness():
    """Bonus: Test MYCA consciousness awareness."""
    from mycosoft_mas.consciousness.unified_router import get_unified_router
    
    router = get_unified_router()
    results = []
    
    consciousness_questions = [
        "Are you alive?",
        "Are you well?",
        "Are you working?",
    ]
    
    for question in consciousness_questions:
        try:
            response_parts = []
            async for chunk in router.route(question):
                response_parts.append(chunk)
            
            response = "".join(response_parts)
            
            # Check for affirmative responses
            passed = any(word in response.lower() for word in ["yes", "i am", "myca", "conscious", "active", "aware"])
            
            results.append(TestResult(
                name=f"Consciousness: '{question}'",
                passed=passed,
                message=f"Response: {response[:80]}...",
                details={"full_response": response}
            ))
        except Exception as e:
            results.append(TestResult(
                name=f"Consciousness: '{question}'",
                passed=False,
                message=f"Error: {e}"
            ))
    
    return results


async def run_all_tests():
    """Run all integration tests."""
    print("=" * 60)
    print("MYCA FULL ORCHESTRATOR INTEGRATION TESTS")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)
    print()
    
    all_results = []
    
    # Test 1: Intent Classification
    print("Test 1: Intent Classification")
    print("-" * 40)
    results = await test_intent_classification()
    all_results.extend(results)
    for r in results:
        print(f"  {r}")
    print()
    
    # Test 2: Unified Router
    print("Test 2: Unified Router")
    print("-" * 40)
    results = await test_unified_router()
    all_results.extend(results)
    for r in results:
        print(f"  {r}")
    print()
    
    # Test 3: Agent Routing
    print("Test 3: Agent Task Delegation")
    print("-" * 40)
    results = await test_agent_routing()
    all_results.extend(results)
    for r in results:
        print(f"  {r}")
    print()
    
    # Test 4: MINDEX RAG
    print("Test 4: MINDEX RAG / Knowledge Query")
    print("-" * 40)
    results = await test_mindex_rag()
    all_results.extend(results)
    for r in results:
        print(f"  {r}")
    print()
    
    # Test 5: Tool Execution
    print("Test 5: Tool Listing")
    print("-" * 40)
    results = await test_tool_execution()
    all_results.extend(results)
    for r in results:
        print(f"  {r}")
    print()
    
    # Test 6: System Status
    print("Test 6: System Status Query")
    print("-" * 40)
    results = await test_system_status()
    all_results.extend(results)
    for r in results:
        print(f"  {r}")
    print()
    
    # Test 7: CREP Awareness
    print("Test 7: CREP Awareness")
    print("-" * 40)
    results = await test_crep_awareness()
    all_results.extend(results)
    for r in results:
        print(f"  {r}")
    print()
    
    # Test 8: Earth2 Awareness
    print("Test 8: Earth2 Awareness")
    print("-" * 40)
    results = await test_earth2_awareness()
    all_results.extend(results)
    for r in results:
        print(f"  {r}")
    print()
    
    # Bonus: Consciousness Awareness
    print("Bonus: MYCA Consciousness Awareness")
    print("-" * 40)
    results = await test_consciousness_awareness()
    all_results.extend(results)
    for r in results:
        print(f"  {r}")
    print()
    
    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for r in all_results if r.passed)
    failed = sum(1 for r in all_results if not r.passed)
    total = len(all_results)
    
    print(f"  Total:  {total}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Rate:   {(passed/total*100):.1f}%")
    print()
    
    if failed > 0:
        print("Failed Tests:")
        for r in all_results:
            if not r.passed:
                print(f"  - {r.name}: {r.message}")
    
    print()
    print(f"Completed: {datetime.now().isoformat()}")
    
    return passed, failed


if __name__ == "__main__":
    passed, failed = asyncio.run(run_all_tests())
    sys.exit(0 if failed == 0 else 1)
