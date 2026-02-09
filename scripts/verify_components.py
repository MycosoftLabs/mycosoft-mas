#!/usr/bin/env python3
"""Verify all voice/Earth2/map components are working."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=== Final Component Verification ===")
print()

tests = []

try:
    from scripts.earth2_voice_handler import Earth2VoiceHandler, process_earth2_voice, is_earth2_command
    tests.append(("earth2_voice_handler", True))
except Exception as e:
    tests.append(("earth2_voice_handler", False, str(e)))

try:
    from scripts.map_voice_handler import MapVoiceHandler, process_map_voice, is_map_command
    tests.append(("map_voice_handler", True))
except Exception as e:
    tests.append(("map_voice_handler", False, str(e)))

try:
    from scripts.voice_command_router import VoiceCommandRouter, route_voice_command, classify_intent_quick
    tests.append(("voice_command_router", True))
except Exception as e:
    tests.append(("voice_command_router", False, str(e)))

try:
    from scripts.context_injector import ContextInjector, get_context_injector, get_llm_context
    tests.append(("context_injector", True))
except Exception as e:
    tests.append(("context_injector", False, str(e)))

try:
    from scripts.vram_manager import VRAMManager, get_vram_manager, get_memory_status
    tests.append(("vram_manager", True))
except Exception as e:
    tests.append(("vram_manager", False, str(e)))

print("Module Imports:")
for test in tests:
    name = test[0]
    passed = test[1]
    status = "[OK]" if passed else "[FAIL]"
    print(f"  {status} {name}")
    if not passed and len(test) > 2:
        print(f"       Error: {test[2]}")

print()
print("=== Functionality Tests ===")
print()

# Earth2 parsing
handler = Earth2VoiceHandler()
cmd = handler.parse_command("show me a 24 hour forecast")
print(f"  Earth2 Parse: intent={cmd.intent.value}")
assert cmd.intent.value == "earth2_forecast", "Earth2 forecast parsing failed"

# Map parsing
map_handler = MapVoiceHandler()
cmd2 = map_handler.parse_command("zoom in on the map")
print(f"  Map Parse: intent={cmd2.intent.value}")
assert cmd2.intent.value == "map_zoom", "Map zoom parsing failed"

# Router classification
router = VoiceCommandRouter()
domain = router.detect_domain("show me a weather forecast")
print(f"  Router Domain: {domain.value}")
assert domain.value == "earth2", "Router classification failed"

# Context
injector = get_context_injector()
injector.update_map_context(center=(-74.0, 40.7), zoom=10)
ctx = injector.get_context_dict()
print(f"  Context: has_map={'map' in ctx}")
assert "map" in ctx, "Context missing map"

# VRAM
status = get_memory_status()
print(f"  VRAM: gpu_available={status.get('available', True)}")

print()
print("=" * 50)
print("  ALL COMPONENTS VERIFIED SUCCESSFULLY")
print("=" * 50)
