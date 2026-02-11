#!/usr/bin/env python3
"""
Voice-Earth2-Map Pipeline E2E Tests - February 5, 2026

Comprehensive tests for the integrated voice command system:
- Earth2 voice commands (weather forecasts, model control)
- Map voice commands (navigation, zoom, layers)
- Context injection and management
- VRAM management for shared GPU
- Frontend command generation

Run with: python -m pytest tests/test_voice_earth2_map_pipeline_feb05_2026.py -v
Or standalone: python tests/test_voice_earth2_map_pipeline_feb05_2026.py
"""

import asyncio
import sys
import os
import pytest
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Test results tracking
test_results: List[Dict[str, Any]] = []


def log_test(name: str, passed: bool, details: str = ""):
    """Log a test result."""
    status = "[PASS]" if passed else "[FAIL]"
    print(f"  {status} {name}")
    if details and not passed:
        print(f"         {details}")
    test_results.append({
        "name": name,
        "passed": passed,
        "details": details,
        "timestamp": datetime.utcnow().isoformat()
    })


def section(title: str):
    """Print a section header."""
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


# =============================================================================
# Test: Earth2 Voice Handler
# =============================================================================

def test_earth2_voice_handler():
    """Test Earth2 voice command parsing and handling."""
    section("Earth2 Voice Handler Tests")
    
    try:
        from scripts.earth2_voice_handler import (
            Earth2VoiceHandler,
            Earth2Intent,
            is_earth2_command,
        )
        log_test("Import earth2_voice_handler", True)
    except ImportError as e:
        log_test("Import earth2_voice_handler", False, str(e))
        return
    
    handler = Earth2VoiceHandler()
    
    # Test forecast detection
    test_cases = [
        ("show me a 24 hour forecast", Earth2Intent.FORECAST),
        ("what's the weather going to be tomorrow", Earth2Intent.FORECAST),
        ("run a nowcast", Earth2Intent.NOWCAST),
        ("load the pangu model", Earth2Intent.LOAD_MODEL),
        ("show wind layer", Earth2Intent.SHOW_LAYER),
        ("hide precipitation overlay", Earth2Intent.HIDE_LAYER),
        ("explain this storm", Earth2Intent.EXPLAIN),
        ("what's the GPU status", Earth2Intent.GPU_STATUS),
        ("random unrelated text", Earth2Intent.UNKNOWN),
    ]
    
    for text, expected_intent in test_cases:
        cmd = handler.parse_command(text)
        passed = cmd.intent == expected_intent
        log_test(
            f"Parse: '{text[:30]}...' -> {expected_intent.value}",
            passed,
            f"Got {cmd.intent.value}" if not passed else ""
        )
    
    # Test is_earth2_command function
    log_test(
        "is_earth2_command('show forecast')",
        is_earth2_command("show forecast") == True
    )
    log_test(
        "is_earth2_command('hello world')",
        is_earth2_command("hello world") == False
    )
    
    # Test command execution (without actual API calls)
    async def run_execute():
        cmd = handler.parse_command("show me a 6 hour forecast")
        result = await handler.execute_command(cmd)
        return result
    
    try:
        # Create new event loop for this test since asyncio.run() was used earlier
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(run_execute())
        finally:
            loop.close()
        
        passed = isinstance(result, dict) and "action" in result
        log_test(
            "Execute forecast command returns dict",
            passed,
            "" if passed else f"Got: {result}"
        )
    except Exception as e:
        import traceback
        log_test(
            "Execute forecast command returns dict",
            False,
            f"Exception: {type(e).__name__}: {e}"
        )


# =============================================================================
# Test: Map Voice Handler
# =============================================================================

def test_map_voice_handler():
    """Test map voice command parsing and handling."""
    section("Map Voice Handler Tests")
    
    try:
        from scripts.map_voice_handler import (
            MapVoiceHandler,
            MapIntent,
            is_map_command,
            process_map_voice,
        )
        log_test("Import map_voice_handler", True)
    except ImportError as e:
        log_test("Import map_voice_handler", False, str(e))
        return
    
    handler = MapVoiceHandler()
    
    # Test navigation commands
    test_cases = [
        ("go to tokyo", MapIntent.NAVIGATE),
        ("fly to new york", MapIntent.NAVIGATE),
        ("zoom in", MapIntent.ZOOM),
        ("zoom out a lot", MapIntent.ZOOM),
        ("zoom to level 10", MapIntent.ZOOM),
        ("pan left", MapIntent.PAN),
        ("move north", MapIntent.PAN),
        ("show satellite layer", MapIntent.LAYER),
        ("hide weather overlay", MapIntent.LAYER),
        ("reset the view", MapIntent.RESET),
        ("show only seismic events", MapIntent.CREP_FILTER),
        ("clear all filters", MapIntent.CREP_FILTER),
        ("tell me about this volcano", MapIntent.CREP_ENTITY),
        ("what's happening here", MapIntent.WHAT_HERE),
    ]
    
    for text, expected_intent in test_cases:
        cmd = handler.parse_command(text)
        passed = cmd.intent == expected_intent
        log_test(
            f"Parse: '{text[:30]}...' -> {expected_intent.value}",
            passed,
            f"Got {cmd.intent.value}" if not passed else ""
        )
    
    # Test known location resolution
    cmd = handler.parse_command("go to tokyo")
    log_test(
        "Known location 'tokyo' has coordinates",
        cmd.coordinates is not None and abs(cmd.coordinates[0] - 35.6762) < 0.1
    )
    
    # Test frontend command generation
    result = process_map_voice("zoom in")
    log_test(
        "process_map_voice returns frontend_command",
        "frontend_command" in result and result["frontend_command"]["type"] == "zoomBy"
    )
    
    result = process_map_voice("go to london")
    log_test(
        "Navigate command has flyTo type",
        result.get("frontend_command", {}).get("type") == "flyTo"
    )


# =============================================================================
# Test: Voice Command Router
# =============================================================================

def test_voice_command_router():
    """Test unified voice command routing."""
    section("Voice Command Router Tests")
    
    try:
        from scripts.voice_command_router import (
            VoiceCommandRouter,
            VoiceDomain,
            classify_intent_quick,
        )
        log_test("Import voice_command_router", True)
    except ImportError as e:
        log_test("Import voice_command_router", False, str(e))
        return
    
    router = VoiceCommandRouter()
    
    # Test domain detection
    test_cases = [
        ("show me a weather forecast", VoiceDomain.EARTH2),
        ("load the fcn model", VoiceDomain.EARTH2),
        ("zoom in on the map", VoiceDomain.MAP),
        ("go to tokyo", VoiceDomain.MAP),
        ("show seismic events", VoiceDomain.CREP),
        ("what's the status", VoiceDomain.SYSTEM),
    ]
    
    for text, expected_domain in test_cases:
        domain = router.detect_domain(text)
        passed = domain == expected_domain
        log_test(
            f"Domain: '{text[:30]}...' -> {expected_domain.value}",
            passed,
            f"Got {domain.value}" if not passed else ""
        )
    
    # Test quick classification
    intent = classify_intent_quick("show me the weather forecast")
    log_test(
        "classify_intent_quick returns string",
        isinstance(intent, str) and intent in ["earth2", "map", "crep", "system", "general", "unknown"]
    )


# =============================================================================
# Test: Context Injector
# =============================================================================

def test_context_injector():
    """Test context injection system."""
    section("Context Injector Tests")
    
    try:
        from scripts.context_injector import (
            ContextInjector,
            get_context_injector,
            get_llm_context,
        )
        log_test("Import context_injector", True)
    except ImportError as e:
        log_test("Import context_injector", False, str(e))
        return
    
    injector = ContextInjector()
    
    # Test map context update
    injector.update_map_context(
        center=(-74.0060, 40.7128),
        zoom=10.0,
        bearing=45.0,
    )
    log_test(
        "Update map context",
        injector.map_viewport is not None and injector.map_viewport.zoom == 10.0
    )
    
    # Test CREP context
    injector.update_crep_layers(["satellites", "vessels", "seismic"])
    log_test(
        "Update CREP layers",
        len(injector.crep_context.active_layers) == 3
    )
    
    # Test Earth2 context
    injector.update_earth2_context(
        active_model="fcn",
        loaded_models=["fcn", "pangu"],
        gpu_memory_used_gb=5.5,
    )
    log_test(
        "Update Earth2 context",
        injector.earth2_context.active_model == "fcn"
    )
    
    # Test context dictionary
    ctx = injector.get_context_dict()
    log_test(
        "get_context_dict returns dict",
        isinstance(ctx, dict) and "map" in ctx and "earth2" in ctx
    )
    
    # Test LLM context generation
    llm_ctx = injector.build_context_for_llm()
    log_test(
        "build_context_for_llm returns string",
        isinstance(llm_ctx, str) and "zoom" in llm_ctx.lower()
    )
    
    # Test command recording
    injector.record_command(
        domain="earth2",
        action="forecast",
        success=True,
        raw_text="show me a 24 hour forecast"
    )
    log_test(
        "record_command updates conversation context",
        injector.conversation_context.last_command_domain == "earth2"
    )


# =============================================================================
# Test: VRAM Manager
# =============================================================================

def test_vram_manager():
    """Test VRAM management system."""
    section("VRAM Manager Tests")
    
    try:
        from scripts.vram_manager import (
            VRAMManager,
            VRAMBudget,
            ModelPriority,
            get_vram_manager,
            EARTH2_MODEL_VRAM,
        )
        log_test("Import vram_manager", True)
    except ImportError as e:
        log_test("Import vram_manager", False, str(e))
        return
    
    # Test with custom budget for testing
    budget = VRAMBudget(
        total_gb=32.0,
        personaplex_reserved_gb=24.0,
        max_earth2_gb=6.0,
    )
    manager = VRAMManager(budget=budget)
    
    # Test memory status
    status = manager.get_memory_status()
    log_test(
        "get_memory_status returns dict",
        isinstance(status, dict) and "total_gb" in status
    )
    
    # Test model VRAM estimates
    log_test(
        "EARTH2_MODEL_VRAM has fcn",
        "fcn" in EARTH2_MODEL_VRAM and EARTH2_MODEL_VRAM["fcn"] > 0
    )
    
    # Test can_load_model check
    result = manager.can_load_model("fcn")
    log_test(
        "can_load_model returns dict with can_load key",
        isinstance(result, dict) and "can_load" in result
    )
    
    # Test loaded models list
    models = manager.get_loaded_models()
    log_test(
        "get_loaded_models returns list",
        isinstance(models, list)
    )
    
    # Test status summary
    summary = manager.get_status_summary()
    log_test(
        "get_status_summary returns complete dict",
        isinstance(summary, dict) and "memory" in summary and "loaded_models" in summary
    )


# =============================================================================
# Test: Async Voice Routing
# =============================================================================

@pytest.mark.asyncio
async def test_async_voice_routing():
    """Test async voice command routing."""
    section("Async Voice Routing Tests")
    
    try:
        from scripts.voice_command_router import route_voice_command
        log_test("Import async route_voice_command", True)
    except ImportError as e:
        log_test("Import async route_voice_command", False, str(e))
        return
    
    # Test routing a forecast command
    result = await route_voice_command("show me a 24 hour weather forecast")
    log_test(
        "Route forecast command",
        result.get("domain") == "earth2" and result.get("success") == True
    )
    
    # Test routing a map command
    result = await route_voice_command("zoom in on the map")
    log_test(
        "Route map command",
        result.get("domain") == "map" and "frontend_command" in result
    )
    
    # Test routing unknown command (should need LLM)
    result = await route_voice_command("tell me a joke about weather")
    log_test(
        "Unknown command needs LLM response",
        result.get("needs_llm_response") == True
    )


# =============================================================================
# Main
# =============================================================================

def run_all_tests():
    """Run all tests and generate report."""
    print()
    print("=" * 70)
    print("  VOICE-EARTH2-MAP PIPELINE E2E TESTS")
    print(f"  February 5, 2026 - {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 70)
    
    # Run sync tests
    test_earth2_voice_handler()
    test_map_voice_handler()
    test_voice_command_router()
    test_context_injector()
    test_vram_manager()
    
    # Run async tests
    asyncio.run(test_async_voice_routing())
    
    # Summary
    section("Test Summary")
    passed = sum(1 for t in test_results if t["passed"])
    failed = sum(1 for t in test_results if not t["passed"])
    total = len(test_results)
    
    print(f"  Passed: {passed}/{total}")
    print(f"  Failed: {failed}/{total}")
    print(f"  Success Rate: {(passed/total*100):.1f}%")
    print()
    
    if failed > 0:
        print("  Failed Tests:")
        for t in test_results:
            if not t["passed"]:
                print(f"    - {t['name']}")
                if t["details"]:
                    print(f"      {t['details']}")
        print()
    
    # Write results to file
    report_path = PROJECT_ROOT / "tests" / f"voice_pipeline_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        import json
        with open(report_path, "w") as f:
            json.dump({
                "timestamp": datetime.utcnow().isoformat(),
                "total": total,
                "passed": passed,
                "failed": failed,
                "success_rate": passed / total if total > 0 else 0,
                "tests": test_results,
            }, f, indent=2)
        print(f"  Results saved to: {report_path.name}")
    except Exception as e:
        print(f"  Could not save results: {e}")
    
    print()
    print("=" * 70)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
