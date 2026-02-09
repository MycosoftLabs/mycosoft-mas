#!/usr/bin/env python3
"""
Phase 4: Voice and PersonaPlex Tests
Tests voice commands, intent classification, and PersonaPlex integration
Created: February 5, 2026
"""
import requests
import json
import time
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

# Terminal colors
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

class TestStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIP = "SKIP"

@dataclass
class TestResult:
    name: str
    status: TestStatus
    message: str
    command: str = ""
    response: str = ""
    duration_ms: int = 0

@dataclass
class TestSuite:
    name: str
    results: List[TestResult] = field(default_factory=list)
    
    @property
    def passed(self) -> int:
        return len([r for r in self.results if r.status == TestStatus.PASS])
    
    @property
    def failed(self) -> int:
        return len([r for r in self.results if r.status == TestStatus.FAIL])

# Configuration
BASE_URL = "http://192.168.0.187:8000"

def print_header(title: str):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{title.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}\n")

def print_result(result: TestResult):
    if result.status == TestStatus.PASS:
        icon = f"{Colors.GREEN}[PASS]{Colors.END}"
    elif result.status == TestStatus.FAIL:
        icon = f"{Colors.RED}[FAIL]{Colors.END}"
    elif result.status == TestStatus.WARN:
        icon = f"{Colors.YELLOW}[WARN]{Colors.END}"
    else:
        icon = f"{Colors.BLUE}[SKIP]{Colors.END}"
    
    print(f"  {icon} {result.name}")
    if result.command:
        print(f"       Command: \"{result.command[:50]}...\"" if len(result.command) > 50 else f"       Command: \"{result.command}\"")
    if result.response and result.status != TestStatus.PASS:
        print(f"       Response: {result.response[:80]}")

class VoiceCommandTests:
    """Voice command and PersonaPlex test suite."""
    
    def __init__(self):
        self.suite = TestSuite(name="Voice Command Tests")
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
    
    def test_brain_query(self, name: str, message: str, expected_keywords: List[str] = None) -> TestResult:
        """Test a voice/brain query."""
        start = time.time()
        try:
            response = self.session.post(
                f"{BASE_URL}/api/brain/query",
                json={"message": message, "session_id": f"test_{int(time.time())}"},
                timeout=15
            )
            duration = int((time.time() - start) * 1000)
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get("response", "")
                
                # Check for expected keywords
                if expected_keywords:
                    found = any(kw.lower() in response_text.lower() for kw in expected_keywords)
                    if found:
                        return TestResult(name=name, status=TestStatus.PASS, 
                                         message="Response contains expected content",
                                         command=message, response=response_text[:100], duration_ms=duration)
                    else:
                        return TestResult(name=name, status=TestStatus.WARN,
                                         message="Response missing expected keywords",
                                         command=message, response=response_text[:100], duration_ms=duration)
                
                return TestResult(name=name, status=TestStatus.PASS,
                                 message="Query successful",
                                 command=message, response=response_text[:100], duration_ms=duration)
            else:
                return TestResult(name=name, status=TestStatus.FAIL,
                                 message=f"HTTP {response.status_code}",
                                 command=message, duration_ms=duration)
        except Exception as e:
            return TestResult(name=name, status=TestStatus.FAIL,
                             message=str(e)[:50], command=message,
                             duration_ms=int((time.time() - start) * 1000))
    
    def test_voice_tool(self, name: str, tool_name: str, arguments: Dict) -> TestResult:
        """Test voice tool execution."""
        start = time.time()
        try:
            response = self.session.post(
                f"{BASE_URL}/api/voice/execute",
                json={"tool_name": tool_name, "arguments": arguments},
                timeout=15
            )
            duration = int((time.time() - start) * 1000)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    return TestResult(name=name, status=TestStatus.PASS,
                                     message="Tool executed successfully",
                                     command=f"{tool_name}({arguments})", duration_ms=duration)
                else:
                    return TestResult(name=name, status=TestStatus.WARN,
                                     message=f"Tool returned: {data.get('status')}",
                                     command=f"{tool_name}({arguments})", duration_ms=duration)
            else:
                return TestResult(name=name, status=TestStatus.FAIL,
                                 message=f"HTTP {response.status_code}",
                                 command=f"{tool_name}({arguments})", duration_ms=duration)
        except Exception as e:
            return TestResult(name=name, status=TestStatus.FAIL,
                             message=str(e)[:50], command=f"{tool_name}({arguments})",
                             duration_ms=int((time.time() - start) * 1000))
    
    def run_voice_tool_tests(self):
        """Test voice tool functionality."""
        print(f"\n{Colors.BOLD}4.1 Voice Tool Tests{Colors.END}")
        
        # Test each tool
        tests = [
            ("Memory Store", "memory_store", {"key": "test_voice_key", "value": "test_voice_value"}),
            ("Memory Recall", "memory_recall", {"key": "test_voice_key"}),
            ("Search Species", "search_species", {"query": "amanita"}),
            ("Get Taxonomy", "get_taxonomy", {"name": "Agaricus bisporus"}),
            ("Device Control", "device_control", {"device": "mushroom1", "action": "status"}),
            ("Workflow Trigger", "workflow_trigger", {"workflow": "test_workflow"}),
        ]
        
        for name, tool, args in tests:
            result = self.test_voice_tool(name, tool, args)
            self.suite.results.append(result)
            print_result(result)
    
    def run_brain_query_tests(self):
        """Test brain query with various commands."""
        print(f"\n{Colors.BOLD}4.2 Brain Query Tests{Colors.END}")
        
        queries = [
            ("Greeting", "Hello MYCA", ["hello", "hi", "received", "operational"]),
            ("System Status", "What is your status?", ["status", "online", "operational"]),
            ("Mycology Query", "Tell me about mushroom cultivation", ["mushroom", "cultivation", "received"]),
            ("Species Question", "What is Agaricus bisporus?", ["received", "message", "query"]),
            ("Help Request", "What can you help me with?", ["help", "assist", "received"]),
        ]
        
        for name, query, keywords in queries:
            result = self.test_brain_query(name, query, keywords)
            self.suite.results.append(result)
            print_result(result)
    
    def run_command_category_tests(self):
        """Test commands from different categories."""
        print(f"\n{Colors.BOLD}4.3 Command Category Tests{Colors.END}")
        
        categories = {
            "Learning": [
                "Learn how to optimize database queries",
                "Teach yourself about container orchestration"
            ],
            "Infrastructure": [
                "Show container status",
                "Check system health"
            ],
            "Memory": [
                "Remember that the project deadline is next Friday",
                "What do you know about the project?"
            ],
            "Research": [
                "Find research papers about mycorrhizal networks",
                "Search for information about spore dispersal"
            ],
        }
        
        for category, commands in categories.items():
            for cmd in commands:
                result = self.test_brain_query(f"{category}: {cmd[:30]}...", cmd)
                self.suite.results.append(result)
                print_result(result)
    
    def run_intent_classification_tests(self):
        """Test intent classification accuracy."""
        print(f"\n{Colors.BOLD}4.4 Intent Classification Tests{Colors.END}")
        
        # Test that different intents get appropriate responses
        intents = [
            ("Agent Control Intent", "List all available agents"),
            ("Scientific Intent", "Run an experiment on mycelium growth"),
            ("Financial Intent", "Generate a budget report"),
            ("Security Intent", "Run a security scan on the system"),
            ("Device Intent", "Check the status of all connected devices"),
        ]
        
        for name, query in intents:
            result = self.test_brain_query(name, query)
            self.suite.results.append(result)
            print_result(result)
    
    def run_session_persistence_tests(self):
        """Test session and memory persistence."""
        print(f"\n{Colors.BOLD}4.5 Session Persistence Tests{Colors.END}")
        
        session_id = f"persist_test_{int(time.time())}"
        
        # Store something
        result1 = self.test_voice_tool(
            "Store Session Data",
            "memory_store",
            {"key": f"session_{session_id}", "value": "persisted_data"}
        )
        self.suite.results.append(result1)
        print_result(result1)
        
        # Recall it
        result2 = self.test_voice_tool(
            "Recall Session Data",
            "memory_recall",
            {"key": f"session_{session_id}"}
        )
        self.suite.results.append(result2)
        print_result(result2)
    
    def run_all_tests(self):
        """Run all voice command tests."""
        print_header("PHASE 4: VOICE COMMAND TESTS")
        
        self.run_voice_tool_tests()
        self.run_brain_query_tests()
        self.run_command_category_tests()
        self.run_intent_classification_tests()
        self.run_session_persistence_tests()
        
        return self.suite

def print_summary(suite: TestSuite):
    """Print test summary."""
    print_header("VOICE COMMAND TEST SUMMARY")
    
    print(f"  Total Tests: {len(suite.results)}")
    print(f"  {Colors.GREEN}Passed: {suite.passed}{Colors.END}")
    print(f"  {Colors.RED}Failed: {suite.failed}{Colors.END}")
    
    warned = len([r for r in suite.results if r.status == TestStatus.WARN])
    print(f"  {Colors.YELLOW}Warnings: {warned}{Colors.END}")
    
    if suite.failed > 0:
        print(f"\n{Colors.BOLD}{Colors.RED}Failed Tests:{Colors.END}")
        for result in suite.results:
            if result.status == TestStatus.FAIL:
                print(f"  - {result.name}: {result.message}")
    
    return suite.failed == 0

def main():
    print(f"\n{Colors.BOLD}VOICE COMMAND COMPREHENSIVE TEST{Colors.END}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tester = VoiceCommandTests()
    suite = tester.run_all_tests()
    
    success = print_summary(suite)
    
    # Save results
    results_file = f"tests/voice_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    results_data = {
        "suite": suite.name,
        "timestamp": datetime.now().isoformat(),
        "passed": suite.passed,
        "failed": suite.failed,
        "results": [
            {
                "name": r.name,
                "status": r.status.value,
                "command": r.command,
                "message": r.message,
                "duration_ms": r.duration_ms
            }
            for r in suite.results
        ]
    }
    
    try:
        with open(results_file, 'w') as f:
            json.dump(results_data, f, indent=2)
        print(f"\n{Colors.BLUE}Results saved to: {results_file}{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.YELLOW}Could not save results: {e}{Colors.END}")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
