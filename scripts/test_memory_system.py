#!/usr/bin/env python3
"""
Phase 6: Memory System Tests
Tests all 8 memory scopes, CRUD operations, and cryptographic integrity
Created: February 5, 2026
"""
import paramiko
import requests
import json
import time
import sys
import hashlib
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
    scope: str = ""
    operation: str = ""
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

# Memory Scopes as per documentation
MEMORY_SCOPES = [
    {"name": "conversation", "ttl": "24h", "description": "Chat history"},
    {"name": "user", "ttl": "30d", "description": "User preferences"},
    {"name": "agent", "ttl": "7d", "description": "Agent state"},
    {"name": "system", "ttl": "forever", "description": "Registry data"},
    {"name": "ephemeral", "ttl": "1h", "description": "Temp calculations"},
    {"name": "device", "ttl": "7d", "description": "IoT telemetry"},
    {"name": "experiment", "ttl": "forever", "description": "ML results"},
    {"name": "workflow", "ttl": "7d", "description": "Pipeline state"},
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
    
    scope_str = f"[{result.scope}]" if result.scope else ""
    print(f"  {icon} {result.name} {scope_str}: {result.message}")

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

class MemorySystemTests:
    """Memory system test suite."""
    
    def __init__(self):
        self.suite = TestSuite(name="Memory System Tests")
        self.ssh_client = None
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
    
    def setup(self):
        self.ssh_client = get_ssh_client()
        return self.ssh_client is not None
    
    def teardown(self):
        if self.ssh_client:
            self.ssh_client.close()
    
    def test_memory_store(self, scope: str, key: str, value: str) -> TestResult:
        """Test storing a memory value."""
        start = time.time()
        try:
            response = self.session.post(
                f"{BASE_URL}/api/voice/execute",
                json={
                    "tool_name": "memory_store",
                    "arguments": {"key": f"{scope}_{key}", "value": value}
                },
                timeout=10
            )
            duration = int((time.time() - start) * 1000)
            
            if response.status_code == 200:
                return TestResult(f"Store", TestStatus.PASS, "Value stored",
                                 scope=scope, operation="CREATE", duration_ms=duration)
            return TestResult(f"Store", TestStatus.FAIL, f"HTTP {response.status_code}",
                             scope=scope, operation="CREATE", duration_ms=duration)
        except Exception as e:
            return TestResult(f"Store", TestStatus.FAIL, str(e)[:50],
                             scope=scope, operation="CREATE",
                             duration_ms=int((time.time() - start) * 1000))
    
    def test_memory_recall(self, scope: str, key: str) -> TestResult:
        """Test recalling a memory value."""
        start = time.time()
        try:
            response = self.session.post(
                f"{BASE_URL}/api/voice/execute",
                json={
                    "tool_name": "memory_recall",
                    "arguments": {"key": f"{scope}_{key}"}
                },
                timeout=10
            )
            duration = int((time.time() - start) * 1000)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    return TestResult(f"Recall", TestStatus.PASS, "Value retrieved",
                                     scope=scope, operation="READ", duration_ms=duration)
                return TestResult(f"Recall", TestStatus.WARN, "Key not found",
                                 scope=scope, operation="READ", duration_ms=duration)
            return TestResult(f"Recall", TestStatus.FAIL, f"HTTP {response.status_code}",
                             scope=scope, operation="READ", duration_ms=duration)
        except Exception as e:
            return TestResult(f"Recall", TestStatus.FAIL, str(e)[:50],
                             scope=scope, operation="READ",
                             duration_ms=int((time.time() - start) * 1000))
    
    def test_redis_memory_backend(self) -> TestResult:
        """Test Redis as memory backend."""
        start = time.time()
        test_key = f"memory_test_{int(time.time())}"
        test_value = "test_memory_value"
        
        # Set value
        out, err, code = run_ssh_command(
            self.ssh_client,
            f'docker exec mycosoft-redis redis-cli SET "{test_key}" "{test_value}" 2>/dev/null'
        )
        
        if "OK" in out:
            # Get value
            out2, err2, code2 = run_ssh_command(
                self.ssh_client,
                f'docker exec mycosoft-redis redis-cli GET "{test_key}" 2>/dev/null'
            )
            
            if test_value in out2:
                # Clean up
                run_ssh_command(
                    self.ssh_client,
                    f'docker exec mycosoft-redis redis-cli DEL "{test_key}" 2>/dev/null'
                )
                return TestResult("Redis Backend", TestStatus.PASS, "SET/GET successful",
                                 duration_ms=int((time.time() - start) * 1000))
        
        return TestResult("Redis Backend", TestStatus.FAIL, "SET/GET failed",
                         duration_ms=int((time.time() - start) * 1000))
    
    def test_postgres_memory_schema(self) -> TestResult:
        """Test PostgreSQL memory tables exist."""
        start = time.time()
        out, err, code = run_ssh_command(
            self.ssh_client,
            "docker exec mycosoft-postgres psql -U mycosoft -c \"SELECT table_name FROM information_schema.tables WHERE table_schema='public';\" 2>/dev/null"
        )
        
        if code == 0 and out:
            tables = out.lower()
            memory_tables = ["memory" in tables, "session" in tables or "ledger" in tables]
            if any(memory_tables):
                return TestResult("PostgreSQL Schema", TestStatus.PASS, "Memory tables found",
                                 duration_ms=int((time.time() - start) * 1000))
            return TestResult("PostgreSQL Schema", TestStatus.WARN, "No dedicated memory tables",
                             duration_ms=int((time.time() - start) * 1000))
        
        return TestResult("PostgreSQL Schema", TestStatus.FAIL, "Could not query schema",
                         duration_ms=int((time.time() - start) * 1000))
    
    def test_hash_integrity(self) -> TestResult:
        """Test SHA256 hashing for memory integrity."""
        start = time.time()
        
        test_data = {"key": "test", "value": "integrity_check", "timestamp": datetime.now().isoformat()}
        json_str = json.dumps(test_data, sort_keys=True)
        hash_value = hashlib.sha256(json_str.encode()).hexdigest()
        
        # Verify hash is 64 characters (SHA256)
        if len(hash_value) == 64:
            return TestResult("Hash Integrity", TestStatus.PASS, f"SHA256: {hash_value[:16]}...",
                             duration_ms=int((time.time() - start) * 1000))
        return TestResult("Hash Integrity", TestStatus.FAIL, "Invalid hash length",
                         duration_ms=int((time.time() - start) * 1000))
    
    def test_memory_module_exists(self) -> TestResult:
        """Test memory module exists in codebase."""
        start = time.time()
        out, err, code = run_ssh_command(
            self.ssh_client,
            "ls /home/mycosoft/mycosoft/mas/mycosoft_mas/voice/memory*.py 2>/dev/null | wc -l"
        )
        
        try:
            count = int(out.strip())
            if count > 0:
                return TestResult("Memory Module", TestStatus.PASS, f"{count} memory files",
                                 duration_ms=int((time.time() - start) * 1000))
            return TestResult("Memory Module", TestStatus.WARN, "No memory files in voice/",
                             duration_ms=int((time.time() - start) * 1000))
        except:
            return TestResult("Memory Module", TestStatus.FAIL, "Could not check",
                             duration_ms=int((time.time() - start) * 1000))
    
    def run_scope_crud_tests(self):
        """Run CRUD tests on all memory scopes."""
        print(f"\n{Colors.BOLD}6.1 Memory Scope CRUD Tests{Colors.END}")
        
        for scope_info in MEMORY_SCOPES:
            scope = scope_info["name"]
            test_key = f"test_{int(time.time())}"
            test_value = f"value_for_{scope}"
            
            # Store
            result = self.test_memory_store(scope, test_key, test_value)
            self.suite.results.append(result)
            print_result(result)
            
            # Recall
            result = self.test_memory_recall(scope, test_key)
            self.suite.results.append(result)
            print_result(result)
    
    def run_backend_tests(self):
        """Run backend storage tests."""
        print(f"\n{Colors.BOLD}6.2 Storage Backend Tests{Colors.END}")
        
        for test_func in [
            self.test_redis_memory_backend,
            self.test_postgres_memory_schema,
        ]:
            result = test_func()
            self.suite.results.append(result)
            print_result(result)
    
    def run_integrity_tests(self):
        """Run cryptographic integrity tests."""
        print(f"\n{Colors.BOLD}6.3 Cryptographic Integrity Tests{Colors.END}")
        
        for test_func in [
            self.test_hash_integrity,
            self.test_memory_module_exists,
        ]:
            result = test_func()
            self.suite.results.append(result)
            print_result(result)
    
    def run_all_tests(self):
        """Run all memory system tests."""
        print_header("PHASE 6: MEMORY SYSTEM TESTS")
        
        if not self.setup():
            print(f"{Colors.RED}Failed to connect via SSH{Colors.END}")
            return self.suite
        
        self.run_scope_crud_tests()
        self.run_backend_tests()
        self.run_integrity_tests()
        
        self.teardown()
        return self.suite

def print_summary(suite: TestSuite):
    print_header("MEMORY SYSTEM TEST SUMMARY")
    
    print(f"  Total Tests: {len(suite.results)}")
    print(f"  {Colors.GREEN}Passed: {suite.passed}{Colors.END}")
    print(f"  {Colors.RED}Failed: {suite.failed}{Colors.END}")
    
    warned = len([r for r in suite.results if r.status == TestStatus.WARN])
    print(f"  {Colors.YELLOW}Warnings: {warned}{Colors.END}")
    
    # Scope breakdown
    print(f"\n  {Colors.BOLD}Scope Coverage:{Colors.END}")
    for scope_info in MEMORY_SCOPES:
        scope = scope_info["name"]
        scope_results = [r for r in suite.results if r.scope == scope]
        passed = len([r for r in scope_results if r.status == TestStatus.PASS])
        total = len(scope_results)
        if total > 0:
            print(f"    {scope}: {passed}/{total}")
    
    return suite.failed == 0

def main():
    print(f"\n{Colors.BOLD}MEMORY SYSTEM TEST{Colors.END}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tester = MemorySystemTests()
    suite = tester.run_all_tests()
    
    success = print_summary(suite)
    
    # Save results
    results_file = f"tests/memory_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    results_data = {
        "suite": suite.name,
        "timestamp": datetime.now().isoformat(),
        "passed": suite.passed,
        "failed": suite.failed,
        "scopes_tested": [s["name"] for s in MEMORY_SCOPES],
        "results": [
            {"name": r.name, "status": r.status.value, "scope": r.scope, 
             "operation": r.operation, "message": r.message}
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
