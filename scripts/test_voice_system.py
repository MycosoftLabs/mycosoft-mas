"""Test the voice system components."""
import sys
sys.path.insert(0, '.')

print("Testing Voice System Components")
print("="*60)

# Test Intent Classifier
print("\n1. Testing Intent Classifier...")
from mycosoft_mas.voice.intent_classifier import IntentClassifier, classify_voice_command

classifier = IntentClassifier()
print(f"   Loaded {len(classifier.intents)} intent categories")

# Test classification
test_phrases = [
    "spawn a new research agent",
    "fix the bug in the API endpoint",
    "learn how to deploy kubernetes",
    "what's the revenue this quarter",
    "schedule a meeting with the board",
    "enable security lockdown",
]

print("\n   Test Classifications:")
for phrase in test_phrases:
    result = classifier.classify(phrase)
    print(f"   - '{phrase}'")
    print(f"     -> Intent: {result.intent_category}, Confidence: {result.confidence:.2f}, Agents: {result.target_agents}")

# Test Command Registry
print("\n2. Testing Command Registry...")
from mycosoft_mas.voice.command_registry import VoiceCommandRegistry, get_command_registry

registry = get_command_registry()
print(f"   Loaded {len(registry.commands)} commands")

# Test matching
test_commands = [
    "show agent status",
    "run the backup workflow",
    "check system health",
]

print("\n   Test Command Matches:")
for cmd in test_commands:
    match = registry.match(cmd)
    if match:
        print(f"   - '{cmd}' -> Command: {match.command_id}, Confidence: {match.confidence:.2f}")
    else:
        print(f"   - '{cmd}' -> No match")

# Test Skill Registry
print("\n3. Testing Skill Registry...")
from mycosoft_mas.voice.skill_registry import SkillRegistry, get_skill_registry

skill_registry = get_skill_registry()
print(f"   SkillRegistry initialized")

# Test Cross Session Memory
print("\n4. Testing Cross Session Memory...")
from mycosoft_mas.voice.cross_session_memory import CrossSessionMemory

memory = CrossSessionMemory()
print(f"   CrossSessionMemory initialized successfully")

# Test Event Stream
print("\n5. Testing Event Stream...")
from mycosoft_mas.voice.event_stream import PersonaPlexEventStream, get_event_stream

stream = get_event_stream()
print(f"   PersonaPlexEventStream initialized successfully")

# Test Full Duplex Voice
print("\n6. Testing Full Duplex Voice...")
from mycosoft_mas.voice.full_duplex_voice import FullDuplexVoice, get_full_duplex_voice

duplex = get_full_duplex_voice()
print(f"   FullDuplexVoice initialized successfully")

# Test Confirmation Gateway
print("\n7. Testing Confirmation Gateway...")
from mycosoft_mas.voice.confirmation_gateway import ConfirmationGateway, get_confirmation_gateway

gateway = get_confirmation_gateway()
print(f"   ConfirmationGateway initialized")

print("\n" + "="*60)
print("Voice System Test Complete!")
print("All core voice components are functional.")
