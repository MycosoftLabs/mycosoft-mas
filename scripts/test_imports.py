"""Test importing key modules."""
import sys
import traceback

modules_to_test = [
    # Voice modules
    "mycosoft_mas.voice",
    "mycosoft_mas.voice.intent_classifier",
    "mycosoft_mas.voice.command_registry",
    "mycosoft_mas.voice.confirmation_gateway",
    "mycosoft_mas.voice.skill_registry",
    "mycosoft_mas.voice.cross_session_memory",
    "mycosoft_mas.voice.event_stream",
    "mycosoft_mas.voice.memory_summarizer",
    "mycosoft_mas.voice.full_duplex_voice",
    "mycosoft_mas.voice.personaplex_bridge",
    
    # Agent modules
    "mycosoft_mas.agents.skill_learning_agent",
    "mycosoft_mas.agents.coding_agent",
    "mycosoft_mas.agents.workflow_generator_agent",
    "mycosoft_mas.agents.corporate_agents",
    
    # Integration modules
    "mycosoft_mas.integrations.aws_integration",
    
    # Security modules
    "mycosoft_mas.security.security_integration",
    "mycosoft_mas.security.integrity_service",
    "mycosoft_mas.security.rbac",
    
    # Orchestration
    "mycosoft_mas.orchestration.langgraph_integration",
    
    # Core modules
    "mycosoft_mas.core.orchestrator",
    "mycosoft_mas.core.orchestrator_service",
    "mycosoft_mas.core.myca_workflow_orchestrator",
]

passed = 0
failed = []

for module in modules_to_test:
    try:
        __import__(module)
        print(f"[OK] {module}")
        passed += 1
    except Exception as e:
        print(f"[FAIL] {module}: {type(e).__name__}: {e}")
        failed.append((module, str(e)))

print(f"\n{'='*60}")
print(f"Results: {passed}/{len(modules_to_test)} modules imported successfully")

if failed:
    print(f"\nFailed modules ({len(failed)}):")
    for module, error in failed:
        print(f"  - {module}")
    sys.exit(1)
else:
    print("All modules import successfully!")
    sys.exit(0)
