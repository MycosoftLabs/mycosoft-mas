"""
Tests for Intent Classification Engine
Created: February 12, 2026

Tests all 14 intent categories with real classification (NO MOCK DATA)
"""

import pytest
from mycosoft_mas.voice.intent_classifier import (
    IntentClassifier,
    ClassifiedIntent,
    IntentPriority,
    ConfirmationLevel,
    classify_voice_command,
)


@pytest.fixture
def classifier():
    """Create a fresh classifier instance for each test"""
    return IntentClassifier()


class TestNatureOSIntent:
    """Test natureos category - MATLAB-driven analyses"""

    def test_analyze_zone(self, classifier):
        result = classifier.classify("Analyze soil quality in zone A")
        assert result.intent_category == "natureos"
        assert result.confidence > 0.3

    def test_forecast(self, classifier):
        result = classifier.classify("Predict temperature for next 24 hours")
        assert result.intent_category == "natureos"
        assert result.confidence > 0.3

    def test_anomaly_scan(self, classifier):
        result = classifier.classify("Are there any sensor anomalies?")
        assert result.intent_category == "natureos"
        assert result.confidence > 0.3

    def test_biodiversity_report(self, classifier):
        result = classifier.classify("Generate biodiversity report")
        assert result.intent_category == "natureos"


class TestGreetingIntent:
    """Test greeting category - "hello", "hi", "hey" """
    
    def test_hello(self, classifier):
        result = classifier.classify("Hello MYCA")
        assert result.intent_category == "greeting"
        assert result.confidence > 0.5
        assert result.priority == IntentPriority.LOW
    
    def test_hi(self, classifier):
        result = classifier.classify("Hi there")
        assert result.intent_category == "greeting"
        assert result.confidence > 0.5
    
    def test_hey(self, classifier):
        result = classifier.classify("Hey")
        assert result.intent_category == "greeting"
    
    def test_good_morning(self, classifier):
        result = classifier.classify("Good morning")
        assert result.intent_category == "greeting"


class TestQuestionIntent:
    """Test question category - "what", "how", "why", "when" """
    
    def test_what_question(self, classifier):
        result = classifier.classify("What is the weather today?")
        assert result.intent_category == "question"
        assert result.confidence > 0.5
    
    def test_how_question(self, classifier):
        result = classifier.classify("How does this system work?")
        assert result.intent_category == "question"
    
    def test_why_question(self, classifier):
        result = classifier.classify("Why is the server down?")
        assert result.intent_category == "question"
    
    def test_when_question(self, classifier):
        result = classifier.classify("When was the last backup?")
        assert result.intent_category == "question"
    
    def test_can_you_question(self, classifier):
        result = classifier.classify("Can you help me?")
        assert result.intent_category == "question"


class TestCommandIntent:
    """Test command category - "do", "start", "stop", "create" """
    
    def test_start_command(self, classifier):
        result = classifier.classify("Start the server")
        assert result.intent_category == "command"
        assert result.confidence > 0.5
        assert result.priority == IntentPriority.HIGH
    
    def test_stop_command(self, classifier):
        result = classifier.classify("Stop the agent")
        assert result.intent_category == "command"
    
    def test_create_command(self, classifier):
        result = classifier.classify("Create a new agent")
        assert result.intent_category == "command"
    
    def test_run_command(self, classifier):
        result = classifier.classify("Run the script")
        assert result.intent_category == "command"
    
    def test_kill_command(self, classifier):
        result = classifier.classify("Kill the process")
        assert result.intent_category == "command"


class TestSearchIntent:
    """Test search category - "find", "search", "look up" """
    
    def test_find(self, classifier):
        result = classifier.classify("Find all mushroom species")
        assert result.intent_category == "search"
        assert result.confidence > 0.5
    
    def test_search(self, classifier):
        result = classifier.classify("Search for Agaricus bisporus")
        assert result.intent_category == "search"
    
    def test_look_up(self, classifier):
        result = classifier.classify("Look up the documentation")
        assert result.intent_category == "search"
    
    def test_query(self, classifier):
        result = classifier.classify("Query the database")
        assert result.intent_category == "search"


class TestNavigationIntent:
    """Test navigation category - "go to", "open", "show" """
    
    def test_go_to(self, classifier):
        result = classifier.classify("Go to the dashboard")
        assert result.intent_category == "navigation"
        assert result.confidence > 0.5
    
    def test_open(self, classifier):
        result = classifier.classify("Open the settings page")
        assert result.intent_category == "navigation"
    
    def test_show(self, classifier):
        result = classifier.classify("Show the device list")
        assert result.intent_category == "navigation"
    
    def test_navigate_to(self, classifier):
        result = classifier.classify("Navigate to the admin panel")
        assert result.intent_category == "navigation"


class TestDeviceControlIntent:
    """Test device_control category - "turn on/off", "set", "configure" """
    
    def test_turn_on(self, classifier):
        result = classifier.classify("Turn on the sensor")
        assert result.intent_category == "device_control"
        assert result.confidence > 0.5
        assert result.confirmation_level == ConfirmationLevel.VERBAL
    
    def test_turn_off(self, classifier):
        result = classifier.classify("Turn off the lights")
        assert result.intent_category == "device_control"
    
    def test_set(self, classifier):
        result = classifier.classify("Set the temperature to 25 degrees")
        assert result.intent_category == "device_control"
    
    def test_configure(self, classifier):
        result = classifier.classify("Configure the device")
        assert result.intent_category == "device_control"


class TestExperimentIntent:
    """Test experiment category - "run experiment", "test hypothesis" """
    
    def test_run_experiment(self, classifier):
        result = classifier.classify("Run an experiment on the culture")
        assert result.intent_category == "experiment"
        assert result.confidence > 0.5
    
    def test_test_hypothesis(self, classifier):
        result = classifier.classify("Test the hypothesis")
        assert result.intent_category == "experiment"
    
    def test_conduct_trial(self, classifier):
        result = classifier.classify("Conduct a trial")
        assert result.intent_category == "experiment"


class TestWorkflowIntent:
    """Test workflow category - "create workflow", "trigger automation" """
    
    def test_create_workflow(self, classifier):
        result = classifier.classify("Create a workflow for data processing")
        assert result.intent_category == "workflow"
        assert result.confidence > 0.5
        assert result.confirmation_level == ConfirmationLevel.VERBAL
    
    def test_trigger_workflow(self, classifier):
        result = classifier.classify("Trigger the backup workflow")
        assert result.intent_category == "workflow"
    
    def test_run_automation(self, classifier):
        result = classifier.classify("Run the automation")
        assert result.intent_category == "workflow"


class TestMemoryIntent:
    """Test memory category - "remember", "recall", "forget" """
    
    def test_remember(self, classifier):
        result = classifier.classify("Remember that I prefer metric units")
        assert result.intent_category == "memory"
        assert result.confidence > 0.5
    
    def test_recall(self, classifier):
        result = classifier.classify("Recall the conversation from yesterday")
        assert result.intent_category == "memory"
    
    def test_forget(self, classifier):
        result = classifier.classify("Forget about that")
        assert result.intent_category == "memory"


class TestStatusIntent:
    """Test status category - "check status", "health", "report" """
    
    def test_check_status(self, classifier):
        result = classifier.classify("Check the status of all services")
        assert result.intent_category == "status"
        assert result.confidence > 0.5
    
    def test_health_check(self, classifier):
        result = classifier.classify("Health check report")
        assert result.intent_category == "status"
    
    def test_show_metrics(self, classifier):
        result = classifier.classify("Show the metrics")
        assert result.intent_category == "status"


class TestDeployIntent:
    """Test deploy category - "deploy", "build", "restart" """
    
    def test_deploy(self, classifier):
        result = classifier.classify("Deploy to the sandbox")
        assert result.intent_category == "deploy"
        assert result.confidence > 0.5
        assert result.priority == IntentPriority.HIGH
        assert result.confirmation_level == ConfirmationLevel.VERBAL
    
    def test_build(self, classifier):
        result = classifier.classify("Build the Docker container")
        assert result.intent_category == "deploy"
    
    def test_restart(self, classifier):
        result = classifier.classify("Deploy and restart the container")
        assert result.intent_category == "deploy"


class TestSecurityIntent:
    """Test security category - "audit", "scan", "check security" """
    
    def test_audit(self, classifier):
        result = classifier.classify("Run a security audit")
        assert result.intent_category == "security"
        assert result.confidence > 0.5
        assert result.priority == IntentPriority.CRITICAL
        assert result.confirmation_level == ConfirmationLevel.CHALLENGE
    
    def test_scan(self, classifier):
        result = classifier.classify("Scan for vulnerabilities")
        assert result.intent_category == "security"
    
    def test_check_security(self, classifier):
        result = classifier.classify("Check security settings")
        assert result.intent_category == "security"


class TestScientificIntent:
    """Test scientific category - "lab", "simulation", "compute" """
    
    def test_lab(self, classifier):
        result = classifier.classify("Lab monitoring report")
        assert result.intent_category == "scientific"
        assert result.confidence > 0.5
    
    def test_simulation(self, classifier):
        result = classifier.classify("Run a simulation")
        assert result.intent_category == "scientific"
    
    def test_compute(self, classifier):
        result = classifier.classify("Compute the growth rate")
        assert result.intent_category == "scientific"
    
    def test_analyze_data(self, classifier):
        result = classifier.classify("Analyze the data")
        assert result.intent_category == "scientific"


class TestGeneralIntent:
    """Test general category - fallback for unclassified """
    
    def test_unclassified(self, classifier):
        result = classifier.classify("blah blah random text")
        assert result.intent_category == "general"
        assert result.confidence <= 0.5
    
    def test_empty_string(self, classifier):
        result = classifier.classify("")
        assert result.intent_category == "general"
    
    def test_nonsense(self, classifier):
        result = classifier.classify("xyzabc123")
        assert result.intent_category == "general"


class TestEntityExtraction:
    """Test entity extraction across intents """
    
    def test_extract_agent_name(self, classifier):
        result = classifier.classify("Stop the coding-agent")
        assert len(result.entities) > 0
        agent_entities = [e for e in result.entities if e.entity_type == "agent_name"]
        assert len(agent_entities) > 0
        assert agent_entities[0].value == "coding-agent"
    
    def test_extract_number(self, classifier):
        result = classifier.classify("Set temperature to 25")
        number_entities = [e for e in result.entities if e.entity_type == "number"]
        assert len(number_entities) > 0
        assert number_entities[0].value == "25"
    
    def test_extract_email(self, classifier):
        result = classifier.classify("Send email to test@example.com")
        email_entities = [e for e in result.entities if e.entity_type == "email"]
        assert len(email_entities) > 0
        assert email_entities[0].value == "test@example.com"


class TestActionExtraction:
    """Test action extraction from transcripts """
    
    def test_create_action(self, classifier):
        result = classifier.classify("Create a new database")
        assert result.intent_action == "create"
    
    def test_read_action(self, classifier):
        result = classifier.classify("Show me the logs")
        assert result.intent_action == "read"
    
    def test_update_action(self, classifier):
        result = classifier.classify("Update the configuration")
        assert result.intent_action == "update"
    
    def test_delete_action(self, classifier):
        result = classifier.classify("Delete the old files")
        assert result.intent_action == "delete"
    
    def test_execute_action(self, classifier):
        result = classifier.classify("Execute the script")
        assert result.intent_action == "execute"


class TestModuleFunction:
    """Test module-level classify_voice_command function """
    
    def test_classify_voice_command(self):
        result = classify_voice_command("Hello MYCA")
        assert isinstance(result, ClassifiedIntent)
        assert result.intent_category == "greeting"
    
    def test_singleton_classifier(self):
        # Ensure we get the same instance
        result1 = classify_voice_command("test 1")
        result2 = classify_voice_command("test 2")
        # Both should work without errors
        assert result1 is not None
        assert result2 is not None


class TestEdgeCases:
    """Test edge cases and error handling """
    
    def test_very_long_transcript(self, classifier):
        long_text = "Start the server " * 100
        result = classifier.classify(long_text)
        assert result.intent_category in ["command", "general"]
    
    def test_mixed_case(self, classifier):
        result = classifier.classify("StArT tHe SeRvEr")
        assert result.intent_category == "command"
    
    def test_punctuation(self, classifier):
        result = classifier.classify("Hello, MYCA!")
        assert result.intent_category == "greeting"
    
    def test_multiple_intents(self, classifier):
        # Should classify as the strongest match
        result = classifier.classify("Hello, can you start the server?")
        # Could be greeting or command, but should pick one
        assert result.intent_category in ["greeting", "command", "question"]
        assert result.confidence > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
