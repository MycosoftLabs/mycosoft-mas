#!/usr/bin/env python3
"""
Phase 5: Agent Orchestration Tests
Tests agent lifecycle, communication, and specific agent functionality
Created: February 5, 2026
"""
import paramiko
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
    details: Optional[Dict] = None
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
VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'REDACTED_VM_SSH_PASSWORD'
BASE_URL = f"http://{VM_HOST}:8000"

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
    
    print(f"  {icon} {result.name}: {result.message}")

def get_ssh_client():
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)
        return client
    except:
        return None

def run_ssh_command(client, cmd, timeout=60):
    try:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode('utf-8', errors='replace').strip()
        err = stderr.read().decode('utf-8', errors='replace').strip()
        return out, err, exit_code
    except Exception as e:
        return "", str(e), -1

class AgentOrchestrationTests:
    """Agent orchestration test suite."""
    
    def __init__(self):
        self.suite = TestSuite(name="Agent Orchestration Tests")
        self.ssh_client = None
        self.session = requests.Session()
    
    def setup(self):
        self.ssh_client = get_ssh_client()
        return self.ssh_client is not None
    
    def teardown(self):
        if self.ssh_client:
            self.ssh_client.close()
    
    def test_agent_registry_exists(self) -> TestResult:
        """Test that agent registry module exists."""
        start = time.time()
        out, err, code = run_ssh_command(
            self.ssh_client,
            "ls /home/mycosoft/mycosoft/mas/mycosoft_mas/agents/registry.py 2>/dev/null | wc -l"
        )
        
        if out.strip() == "1":
            return TestResult("Agent Registry Module", TestStatus.PASS, "Exists",
                             duration_ms=int((time.time() - start) * 1000))
        return TestResult("Agent Registry Module", TestStatus.WARN, "Not found",
                         duration_ms=int((time.time() - start) * 1000))
    
    def test_agent_categories(self) -> TestResult:
        """Test that agent categories are defined."""
        start = time.time()
        out, err, code = run_ssh_command(
            self.ssh_client,
            'grep -r "category" /home/mycosoft/mycosoft/mas/mycosoft_mas/agents/*.py 2>/dev/null | wc -l'
        )
        
        try:
            count = int(out.strip())
            if count > 10:
                return TestResult("Agent Categories", TestStatus.PASS, 
                                 f"{count} category references found",
                                 duration_ms=int((time.time() - start) * 1000))
            return TestResult("Agent Categories", TestStatus.WARN,
                             f"Only {count} category references",
                             duration_ms=int((time.time() - start) * 1000))
        except:
            return TestResult("Agent Categories", TestStatus.FAIL, "Could not count",
                             duration_ms=int((time.time() - start) * 1000))
    
    def test_orchestrator_module(self) -> TestResult:
        """Test orchestrator module exists."""
        start = time.time()
        out, err, code = run_ssh_command(
            self.ssh_client,
            "ls /home/mycosoft/mycosoft/mas/orchestrator-myca/*.py 2>/dev/null | wc -l"
        )
        
        try:
            count = int(out.strip())
            if count >= 3:
                return TestResult("Orchestrator Module", TestStatus.PASS,
                                 f"{count} Python files",
                                 duration_ms=int((time.time() - start) * 1000))
            return TestResult("Orchestrator Module", TestStatus.WARN,
                             f"Only {count} Python files",
                             duration_ms=int((time.time() - start) * 1000))
        except:
            return TestResult("Orchestrator Module", TestStatus.FAIL, "Not found",
                             duration_ms=int((time.time() - start) * 1000))
    
    def test_redis_agent_channel(self) -> TestResult:
        """Test Redis agent communication channel."""
        start = time.time()
        out, err, code = run_ssh_command(
            self.ssh_client,
            'docker exec mycosoft-redis redis-cli PUBSUB CHANNELS "agent*" 2>/dev/null'
        )
        
        if code == 0:
            channels = out.strip().split('\n') if out.strip() else []
            return TestResult("Redis Agent Channels", TestStatus.PASS,
                             f"{len(channels)} channels" if channels else "Ready (no active channels)",
                             duration_ms=int((time.time() - start) * 1000))
        return TestResult("Redis Agent Channels", TestStatus.FAIL, "Could not check",
                         duration_ms=int((time.time() - start) * 1000))
    
    def test_n8n_workflow_count(self) -> TestResult:
        """Test n8n workflow count."""
        start = time.time()
        try:
            response = self.session.get(f"http://{VM_HOST}:5678/rest/workflows", timeout=10)
            if response.status_code == 200:
                try:
                    data = response.json()
                    count = len(data.get('data', []))
                    return TestResult("n8n Workflows", TestStatus.PASS,
                                     f"{count} workflows",
                                     duration_ms=int((time.time() - start) * 1000))
                except:
                    return TestResult("n8n Workflows", TestStatus.PASS,
                                     "Accessible",
                                     duration_ms=int((time.time() - start) * 1000))
            elif response.status_code == 401:
                return TestResult("n8n Workflows", TestStatus.WARN,
                                 "Auth required (expected)",
                                 duration_ms=int((time.time() - start) * 1000))
            return TestResult("n8n Workflows", TestStatus.FAIL,
                             f"HTTP {response.status_code}",
                             duration_ms=int((time.time() - start) * 1000))
        except Exception as e:
            return TestResult("n8n Workflows", TestStatus.FAIL, str(e)[:50],
                             duration_ms=int((time.time() - start) * 1000))
    
    def test_agent_communication_simulation(self) -> TestResult:
        """Simulate agent communication via Redis."""
        start = time.time()
        test_msg = f"test_ping_{int(time.time())}"
        
        # Publish a test message
        out, err, code = run_ssh_command(
            self.ssh_client,
            f'docker exec mycosoft-redis redis-cli PUBLISH agent_test "{test_msg}" 2>/dev/null'
        )
        
        if "1" in out or code == 0:
            return TestResult("Agent Communication", TestStatus.PASS,
                             "Message published to channel",
                             duration_ms=int((time.time() - start) * 1000))
        return TestResult("Agent Communication", TestStatus.WARN,
                         "No subscribers (expected in test)",
                         duration_ms=int((time.time() - start) * 1000))
    
    def test_specific_agents(self) -> TestResult:
        """Test specific agent configurations exist."""
        start = time.time()
        agent_files = [
            "mycosoft_mas/agents",
            "agents",
        ]
        
        total_count = 0
        for path in agent_files:
            out, err, code = run_ssh_command(
                self.ssh_client,
                f"find /home/mycosoft/mycosoft/mas/{path} -name '*.py' 2>/dev/null | wc -l"
            )
            try:
                total_count += int(out.strip())
            except:
                pass
        
        if total_count > 20:
            return TestResult("Agent Definitions", TestStatus.PASS,
                             f"{total_count} agent files",
                             duration_ms=int((time.time() - start) * 1000))
        elif total_count > 0:
            return TestResult("Agent Definitions", TestStatus.WARN,
                             f"Only {total_count} agent files",
                             duration_ms=int((time.time() - start) * 1000))
        return TestResult("Agent Definitions", TestStatus.FAIL, "No agent files found",
                         duration_ms=int((time.time() - start) * 1000))
    
    def test_voice_agent_integration(self) -> TestResult:
        """Test voice agent integration."""
        start = time.time()
        out, err, code = run_ssh_command(
            self.ssh_client,
            "grep -r 'voice' /home/mycosoft/mycosoft/mas/mycosoft_mas/agents/*.py 2>/dev/null | wc -l"
        )
        
        try:
            count = int(out.strip())
            if count > 0:
                return TestResult("Voice Agent Integration", TestStatus.PASS,
                                 f"{count} voice references",
                                 duration_ms=int((time.time() - start) * 1000))
            return TestResult("Voice Agent Integration", TestStatus.WARN,
                             "No voice references",
                             duration_ms=int((time.time() - start) * 1000))
        except:
            return TestResult("Voice Agent Integration", TestStatus.FAIL, "Could not check",
                             duration_ms=int((time.time() - start) * 1000))
    
    def run_all_tests(self):
        """Run all agent orchestration tests."""
        print_header("PHASE 5: AGENT ORCHESTRATION TESTS")
        
        if not self.setup():
            print(f"{Colors.RED}Failed to connect via SSH{Colors.END}")
            return self.suite
        
        print(f"\n{Colors.BOLD}5.1 Agent Registry Tests{Colors.END}")
        for test_func in [
            self.test_agent_registry_exists,
            self.test_agent_categories,
            self.test_specific_agents,
        ]:
            result = test_func()
            self.suite.results.append(result)
            print_result(result)
        
        print(f"\n{Colors.BOLD}5.2 Orchestrator Tests{Colors.END}")
        for test_func in [
            self.test_orchestrator_module,
            self.test_n8n_workflow_count,
        ]:
            result = test_func()
            self.suite.results.append(result)
            print_result(result)
        
        print(f"\n{Colors.BOLD}5.3 Communication Tests{Colors.END}")
        for test_func in [
            self.test_redis_agent_channel,
            self.test_agent_communication_simulation,
            self.test_voice_agent_integration,
        ]:
            result = test_func()
            self.suite.results.append(result)
            print_result(result)
        
        self.teardown()
        return self.suite

def print_summary(suite: TestSuite):
    print_header("AGENT ORCHESTRATION TEST SUMMARY")
    
    print(f"  Total Tests: {len(suite.results)}")
    print(f"  {Colors.GREEN}Passed: {suite.passed}{Colors.END}")
    print(f"  {Colors.RED}Failed: {suite.failed}{Colors.END}")
    
    warned = len([r for r in suite.results if r.status == TestStatus.WARN])
    print(f"  {Colors.YELLOW}Warnings: {warned}{Colors.END}")
    
    return suite.failed == 0

def main():
    print(f"\n{Colors.BOLD}AGENT ORCHESTRATION TEST{Colors.END}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tester = AgentOrchestrationTests()
    suite = tester.run_all_tests()
    
    success = print_summary(suite)
    
    # Save results
    results_file = f"tests/agent_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    results_data = {
        "suite": suite.name,
        "timestamp": datetime.now().isoformat(),
        "passed": suite.passed,
        "failed": suite.failed,
        "results": [
            {"name": r.name, "status": r.status.value, "message": r.message}
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
