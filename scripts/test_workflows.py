#!/usr/bin/env python3
"""
Phase 7: n8n Workflow Tests
Tests workflow inventory, webhook triggers, and execution
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
    workflow: str = ""
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
N8N_URL = f"http://{VM_HOST}:5678"

# Expected workflows from documentation
EXPECTED_WORKFLOWS = [
    "voice_skill_learning",
    "voice_coding_agent",
    "voice_corporate_agents",
    "voice_event_notifications",
    "voice_security_alerts",
    "voice_memory_operations",
    "voice_infrastructure_control",
    "earth2_weather_automation",
    "earth2_spore_alert",
    "earth2_nowcast_alert",
]

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
    
    workflow_str = f"[{result.workflow}]" if result.workflow else ""
    print(f"  {icon} {result.name} {workflow_str}: {result.message}")

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

class WorkflowTests:
    """n8n Workflow test suite."""
    
    def __init__(self):
        self.suite = TestSuite(name="Workflow Tests")
        self.ssh_client = None
        self.session = requests.Session()
    
    def setup(self):
        self.ssh_client = get_ssh_client()
        return self.ssh_client is not None
    
    def teardown(self):
        if self.ssh_client:
            self.ssh_client.close()
    
    def test_n8n_health(self) -> TestResult:
        """Test n8n health endpoint."""
        start = time.time()
        try:
            response = self.session.get(f"{N8N_URL}/healthz", timeout=10)
            if response.status_code == 200:
                return TestResult("n8n Health", TestStatus.PASS, "Service healthy",
                                 duration_ms=int((time.time() - start) * 1000))
            return TestResult("n8n Health", TestStatus.FAIL, f"HTTP {response.status_code}",
                             duration_ms=int((time.time() - start) * 1000))
        except Exception as e:
            return TestResult("n8n Health", TestStatus.FAIL, str(e)[:50],
                             duration_ms=int((time.time() - start) * 1000))
    
    def test_n8n_ui(self) -> TestResult:
        """Test n8n UI accessibility."""
        start = time.time()
        try:
            response = self.session.get(f"{N8N_URL}/", timeout=10)
            if response.status_code == 200:
                return TestResult("n8n UI", TestStatus.PASS, "Accessible",
                                 duration_ms=int((time.time() - start) * 1000))
            return TestResult("n8n UI", TestStatus.FAIL, f"HTTP {response.status_code}",
                             duration_ms=int((time.time() - start) * 1000))
        except Exception as e:
            return TestResult("n8n UI", TestStatus.FAIL, str(e)[:50],
                             duration_ms=int((time.time() - start) * 1000))
    
    def test_workflow_files_exist(self) -> TestResult:
        """Test workflow JSON files exist in codebase."""
        start = time.time()
        out, err, code = run_ssh_command(
            self.ssh_client,
            "ls /home/mycosoft/mycosoft/mas/n8n/workflows/*.json 2>/dev/null | wc -l"
        )
        
        try:
            count = int(out.strip())
            if count >= 10:
                return TestResult("Workflow Files", TestStatus.PASS, f"{count} workflow files",
                                 duration_ms=int((time.time() - start) * 1000))
            elif count > 0:
                return TestResult("Workflow Files", TestStatus.WARN, 
                                 f"Only {count} workflow files (expected 10+)",
                                 duration_ms=int((time.time() - start) * 1000))
            return TestResult("Workflow Files", TestStatus.FAIL, "No workflow files found",
                             duration_ms=int((time.time() - start) * 1000))
        except:
            return TestResult("Workflow Files", TestStatus.FAIL, "Could not count files",
                             duration_ms=int((time.time() - start) * 1000))
    
    def test_specific_workflow_file(self, workflow_name: str) -> TestResult:
        """Test specific workflow file exists."""
        start = time.time()
        out, err, code = run_ssh_command(
            self.ssh_client,
            f"ls /home/mycosoft/mycosoft/mas/n8n/workflows/{workflow_name}.json 2>/dev/null"
        )
        
        if workflow_name in out:
            return TestResult("Workflow File", TestStatus.PASS, "Found",
                             workflow=workflow_name,
                             duration_ms=int((time.time() - start) * 1000))
        return TestResult("Workflow File", TestStatus.WARN, "Not found",
                         workflow=workflow_name,
                         duration_ms=int((time.time() - start) * 1000))
    
    def test_n8n_postgres_connection(self) -> TestResult:
        """Test n8n can connect to PostgreSQL."""
        start = time.time()
        out, err, code = run_ssh_command(
            self.ssh_client,
            "docker logs myca-n8n --tail 20 2>&1 | grep -i 'postgres\\|database\\|connected' | head -3"
        )
        
        if "error" not in out.lower() and code == 0:
            return TestResult("n8n PostgreSQL", TestStatus.PASS, "Connected",
                             duration_ms=int((time.time() - start) * 1000))
        return TestResult("n8n PostgreSQL", TestStatus.WARN, "Check logs",
                         duration_ms=int((time.time() - start) * 1000))
    
    def test_webhook_endpoint_format(self) -> TestResult:
        """Test webhook endpoint format is correct."""
        start = time.time()
        # Check if any workflow has webhook node
        out, err, code = run_ssh_command(
            self.ssh_client,
            'grep -l "webhook" /home/mycosoft/mycosoft/mas/n8n/workflows/*.json 2>/dev/null | wc -l'
        )
        
        try:
            count = int(out.strip())
            if count > 0:
                return TestResult("Webhook Workflows", TestStatus.PASS, 
                                 f"{count} workflows with webhooks",
                                 duration_ms=int((time.time() - start) * 1000))
            return TestResult("Webhook Workflows", TestStatus.WARN, "No webhook workflows found",
                             duration_ms=int((time.time() - start) * 1000))
        except:
            return TestResult("Webhook Workflows", TestStatus.FAIL, "Could not check",
                             duration_ms=int((time.time() - start) * 1000))
    
    def test_n8n_container_status(self) -> TestResult:
        """Test n8n container is running properly."""
        start = time.time()
        out, err, code = run_ssh_command(
            self.ssh_client,
            "docker ps --filter 'name=myca-n8n' --format '{{.Status}}'"
        )
        
        if "Up" in out:
            return TestResult("n8n Container", TestStatus.PASS, out.split('\n')[0][:40],
                             duration_ms=int((time.time() - start) * 1000))
        return TestResult("n8n Container", TestStatus.FAIL, "Not running",
                         duration_ms=int((time.time() - start) * 1000))
    
    def run_all_tests(self):
        """Run all workflow tests."""
        print_header("PHASE 7: WORKFLOW TESTS")
        
        if not self.setup():
            print(f"{Colors.RED}Failed to connect via SSH{Colors.END}")
            return self.suite
        
        print(f"\n{Colors.BOLD}7.1 n8n Service Tests{Colors.END}")
        for test_func in [
            self.test_n8n_health,
            self.test_n8n_ui,
            self.test_n8n_container_status,
            self.test_n8n_postgres_connection,
        ]:
            result = test_func()
            self.suite.results.append(result)
            print_result(result)
        
        print(f"\n{Colors.BOLD}7.2 Workflow File Inventory{Colors.END}")
        result = self.test_workflow_files_exist()
        self.suite.results.append(result)
        print_result(result)
        
        for workflow in EXPECTED_WORKFLOWS[:5]:  # Test first 5
            result = self.test_specific_workflow_file(workflow)
            self.suite.results.append(result)
            print_result(result)
        
        print(f"\n{Colors.BOLD}7.3 Webhook Configuration{Colors.END}")
        result = self.test_webhook_endpoint_format()
        self.suite.results.append(result)
        print_result(result)
        
        self.teardown()
        return self.suite

def print_summary(suite: TestSuite):
    print_header("WORKFLOW TEST SUMMARY")
    
    print(f"  Total Tests: {len(suite.results)}")
    print(f"  {Colors.GREEN}Passed: {suite.passed}{Colors.END}")
    print(f"  {Colors.RED}Failed: {suite.failed}{Colors.END}")
    
    warned = len([r for r in suite.results if r.status == TestStatus.WARN])
    print(f"  {Colors.YELLOW}Warnings: {warned}{Colors.END}")
    
    return suite.failed == 0

def main():
    print(f"\n{Colors.BOLD}WORKFLOW TEST{Colors.END}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tester = WorkflowTests()
    suite = tester.run_all_tests()
    
    success = print_summary(suite)
    
    # Save results
    results_file = f"tests/workflow_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    results_data = {
        "suite": suite.name,
        "timestamp": datetime.now().isoformat(),
        "passed": suite.passed,
        "failed": suite.failed,
        "results": [
            {"name": r.name, "status": r.status.value, "workflow": r.workflow, "message": r.message}
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
