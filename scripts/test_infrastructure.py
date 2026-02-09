#!/usr/bin/env python3
"""
Phase 1: Infrastructure and Connectivity Tests
Comprehensive testing of containers, databases, and network connectivity
Created: February 5, 2026
"""
import paramiko
import requests
import json
import time
import sys
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, field, asdict
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
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def add_result(self, result: TestResult):
        self.results.append(result)
    
    @property
    def passed(self) -> int:
        return len([r for r in self.results if r.status == TestStatus.PASS])
    
    @property
    def failed(self) -> int:
        return len([r for r in self.results if r.status == TestStatus.FAIL])
    
    @property
    def warned(self) -> int:
        return len([r for r in self.results if r.status == TestStatus.WARN])

# Configuration
VM_CONFIG = {
    'sandbox': {'host': '192.168.0.187', 'user': 'mycosoft', 'password': 'REDACTED_VM_SSH_PASSWORD'},
}

EXPECTED_CONTAINERS = [
    'mycosoft-website',
    'mindex-api',
    'mycorrhizae-api',
    'myca-n8n',
    'mycosoft-postgres',
    'mycosoft-redis',
]

EXPECTED_PORTS = {
    3000: 'Website',
    8000: 'MINDEX API',
    8002: 'Mycorrhizae API',
    5678: 'n8n',
    5432: 'PostgreSQL',
    6379: 'Redis',
}

def print_header(title: str):
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{title.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}\n")

def print_result(result: TestResult):
    """Print a test result with color coding."""
    if result.status == TestStatus.PASS:
        icon = f"{Colors.GREEN}[PASS]{Colors.END}"
    elif result.status == TestStatus.FAIL:
        icon = f"{Colors.RED}[FAIL]{Colors.END}"
    elif result.status == TestStatus.WARN:
        icon = f"{Colors.YELLOW}[WARN]{Colors.END}"
    else:
        icon = f"{Colors.BLUE}[SKIP]{Colors.END}"
    
    print(f"  {icon} {result.name}: {result.message}")
    if result.details and result.status == TestStatus.FAIL:
        for key, value in result.details.items():
            print(f"       {Colors.YELLOW}{key}: {value}{Colors.END}")

def get_ssh_client(host: str, user: str, password: str) -> Optional[paramiko.SSHClient]:
    """Create SSH connection to VM."""
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=user, password=password, timeout=30)
        return client
    except Exception as e:
        return None

def run_ssh_command(client: paramiko.SSHClient, cmd: str, timeout: int = 60) -> Tuple[str, str, int]:
    """Execute SSH command and return stdout, stderr, exit_code."""
    try:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode('utf-8', errors='replace').strip()
        err = stderr.read().decode('utf-8', errors='replace').strip()
        return out, err, exit_code
    except Exception as e:
        return "", str(e), -1

class InfrastructureTests:
    """Infrastructure and connectivity test suite."""
    
    def __init__(self):
        self.suite = TestSuite(name="Infrastructure Tests")
        self.ssh_client: Optional[paramiko.SSHClient] = None
        self.vm_host = VM_CONFIG['sandbox']['host']
    
    def connect_ssh(self) -> bool:
        """Establish SSH connection."""
        config = VM_CONFIG['sandbox']
        self.ssh_client = get_ssh_client(config['host'], config['user'], config['password'])
        return self.ssh_client is not None
    
    def test_ssh_connectivity(self) -> TestResult:
        """Test SSH connection to Sandbox VM."""
        start = time.time()
        if self.connect_ssh():
            return TestResult(
                name="SSH Connectivity",
                status=TestStatus.PASS,
                message=f"Connected to {self.vm_host}",
                duration_ms=int((time.time() - start) * 1000)
            )
        return TestResult(
            name="SSH Connectivity",
            status=TestStatus.FAIL,
            message=f"Failed to connect to {self.vm_host}",
            duration_ms=int((time.time() - start) * 1000)
        )
    
    def test_container_running(self, container_name: str) -> TestResult:
        """Test if a container is running."""
        start = time.time()
        out, err, code = run_ssh_command(
            self.ssh_client,
            f"docker ps --filter 'name={container_name}' --format '{{{{.Status}}}}'"
        )
        
        if out and "Up" in out:
            return TestResult(
                name=f"Container: {container_name}",
                status=TestStatus.PASS,
                message=out.split('\n')[0][:50],
                duration_ms=int((time.time() - start) * 1000)
            )
        return TestResult(
            name=f"Container: {container_name}",
            status=TestStatus.FAIL,
            message="Not running or not found",
            details={"stderr": err[:100] if err else "Container not found"},
            duration_ms=int((time.time() - start) * 1000)
        )
    
    def test_container_logs_errors(self, container_name: str) -> TestResult:
        """Check container logs for errors."""
        start = time.time()
        out, err, code = run_ssh_command(
            self.ssh_client,
            f"docker logs {container_name} --tail 50 2>&1 | grep -i 'error\\|exception\\|fatal' | wc -l"
        )
        
        try:
            error_count = int(out.strip()) if out.strip().isdigit() else 0
        except:
            error_count = 0
        
        if error_count == 0:
            return TestResult(
                name=f"Logs: {container_name}",
                status=TestStatus.PASS,
                message="No errors in last 50 lines",
                duration_ms=int((time.time() - start) * 1000)
            )
        elif error_count < 5:
            return TestResult(
                name=f"Logs: {container_name}",
                status=TestStatus.WARN,
                message=f"{error_count} errors in last 50 lines",
                duration_ms=int((time.time() - start) * 1000)
            )
        return TestResult(
            name=f"Logs: {container_name}",
            status=TestStatus.FAIL,
            message=f"{error_count} errors in last 50 lines",
            duration_ms=int((time.time() - start) * 1000)
        )
    
    def test_port_listening(self, port: int, service_name: str) -> TestResult:
        """Test if a port is listening."""
        start = time.time()
        out, err, code = run_ssh_command(
            self.ssh_client,
            f"ss -tlnp | grep ':{port} ' | head -1"
        )
        
        if out:
            return TestResult(
                name=f"Port {port} ({service_name})",
                status=TestStatus.PASS,
                message="Listening",
                duration_ms=int((time.time() - start) * 1000)
            )
        return TestResult(
            name=f"Port {port} ({service_name})",
            status=TestStatus.FAIL,
            message="Not listening",
            duration_ms=int((time.time() - start) * 1000)
        )
    
    def test_http_endpoint(self, name: str, url: str, expected_status: int = 200) -> TestResult:
        """Test HTTP endpoint availability."""
        start = time.time()
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == expected_status:
                return TestResult(
                    name=name,
                    status=TestStatus.PASS,
                    message=f"HTTP {response.status_code}",
                    duration_ms=int((time.time() - start) * 1000)
                )
            return TestResult(
                name=name,
                status=TestStatus.WARN,
                message=f"HTTP {response.status_code} (expected {expected_status})",
                duration_ms=int((time.time() - start) * 1000)
            )
        except requests.exceptions.Timeout:
            return TestResult(
                name=name,
                status=TestStatus.FAIL,
                message="Timeout",
                duration_ms=int((time.time() - start) * 1000)
            )
        except Exception as e:
            return TestResult(
                name=name,
                status=TestStatus.FAIL,
                message=str(e)[:50],
                duration_ms=int((time.time() - start) * 1000)
            )
    
    def test_postgres_connectivity(self) -> TestResult:
        """Test PostgreSQL database connectivity."""
        start = time.time()
        out, err, code = run_ssh_command(
            self.ssh_client,
            'docker exec mycosoft-postgres psql -U mycosoft -c "SELECT 1 as health_check;" 2>/dev/null'
        )
        
        if "1" in out and code == 0:
            return TestResult(
                name="PostgreSQL Connectivity",
                status=TestStatus.PASS,
                message="Query successful",
                duration_ms=int((time.time() - start) * 1000)
            )
        return TestResult(
            name="PostgreSQL Connectivity",
            status=TestStatus.FAIL,
            message="Query failed",
            details={"error": err[:100] if err else "Unknown error"},
            duration_ms=int((time.time() - start) * 1000)
        )
    
    def test_postgres_databases(self) -> TestResult:
        """Test PostgreSQL databases exist."""
        start = time.time()
        out, err, code = run_ssh_command(
            self.ssh_client,
            'docker exec mycosoft-postgres psql -U mycosoft -c "\\l" 2>/dev/null | grep -E "mycosoft|n8n"'
        )
        
        expected_dbs = ['mycosoft', 'n8n']
        found_dbs = [db for db in expected_dbs if db in out]
        
        if len(found_dbs) == len(expected_dbs):
            return TestResult(
                name="PostgreSQL Databases",
                status=TestStatus.PASS,
                message=f"Found: {', '.join(found_dbs)}",
                duration_ms=int((time.time() - start) * 1000)
            )
        return TestResult(
            name="PostgreSQL Databases",
            status=TestStatus.WARN,
            message=f"Found {len(found_dbs)}/{len(expected_dbs)} databases",
            details={"found": found_dbs, "expected": expected_dbs},
            duration_ms=int((time.time() - start) * 1000)
        )
    
    def test_redis_connectivity(self) -> TestResult:
        """Test Redis connectivity."""
        start = time.time()
        out, err, code = run_ssh_command(
            self.ssh_client,
            'docker exec mycosoft-redis redis-cli PING 2>/dev/null'
        )
        
        if "PONG" in out:
            return TestResult(
                name="Redis Connectivity",
                status=TestStatus.PASS,
                message="PONG received",
                duration_ms=int((time.time() - start) * 1000)
            )
        return TestResult(
            name="Redis Connectivity",
            status=TestStatus.FAIL,
            message="No PONG received",
            duration_ms=int((time.time() - start) * 1000)
        )
    
    def test_redis_keyspace(self) -> TestResult:
        """Test Redis keyspace status."""
        start = time.time()
        out, err, code = run_ssh_command(
            self.ssh_client,
            'docker exec mycosoft-redis redis-cli INFO keyspace 2>/dev/null'
        )
        
        if "db0" in out:
            return TestResult(
                name="Redis Keyspace",
                status=TestStatus.PASS,
                message="Has data",
                duration_ms=int((time.time() - start) * 1000)
            )
        return TestResult(
            name="Redis Keyspace",
            status=TestStatus.WARN,
            message="Empty keyspace (no sessions stored)",
            duration_ms=int((time.time() - start) * 1000)
        )
    
    def test_disk_space(self) -> TestResult:
        """Test available disk space."""
        start = time.time()
        out, err, code = run_ssh_command(
            self.ssh_client,
            "df -h / | tail -1 | awk '{print $5}'"
        )
        
        try:
            usage = int(out.strip().replace('%', ''))
            if usage < 80:
                return TestResult(
                    name="Disk Space",
                    status=TestStatus.PASS,
                    message=f"{usage}% used",
                    duration_ms=int((time.time() - start) * 1000)
                )
            elif usage < 90:
                return TestResult(
                    name="Disk Space",
                    status=TestStatus.WARN,
                    message=f"{usage}% used (getting full)",
                    duration_ms=int((time.time() - start) * 1000)
                )
            return TestResult(
                name="Disk Space",
                status=TestStatus.FAIL,
                message=f"{usage}% used (critical)",
                duration_ms=int((time.time() - start) * 1000)
            )
        except:
            return TestResult(
                name="Disk Space",
                status=TestStatus.FAIL,
                message="Could not determine",
                duration_ms=int((time.time() - start) * 1000)
            )
    
    def test_memory_usage(self) -> TestResult:
        """Test memory usage."""
        start = time.time()
        out, err, code = run_ssh_command(
            self.ssh_client,
            "free -m | grep Mem | awk '{printf \"%.0f\", $3/$2*100}'"
        )
        
        try:
            usage = int(out.strip())
            if usage < 80:
                return TestResult(
                    name="Memory Usage",
                    status=TestStatus.PASS,
                    message=f"{usage}% used",
                    duration_ms=int((time.time() - start) * 1000)
                )
            elif usage < 90:
                return TestResult(
                    name="Memory Usage",
                    status=TestStatus.WARN,
                    message=f"{usage}% used (high)",
                    duration_ms=int((time.time() - start) * 1000)
                )
            return TestResult(
                name="Memory Usage",
                status=TestStatus.FAIL,
                message=f"{usage}% used (critical)",
                duration_ms=int((time.time() - start) * 1000)
            )
        except:
            return TestResult(
                name="Memory Usage",
                status=TestStatus.FAIL,
                message="Could not determine",
                duration_ms=int((time.time() - start) * 1000)
            )
    
    def test_nas_mount(self) -> TestResult:
        """Test NAS volume mount for media assets."""
        start = time.time()
        out, err, code = run_ssh_command(
            self.ssh_client,
            "ls -la /opt/mycosoft/media/website/assets 2>/dev/null | head -5"
        )
        
        if out and "total" in out.lower():
            return TestResult(
                name="NAS Media Mount",
                status=TestStatus.PASS,
                message="Mounted and accessible",
                duration_ms=int((time.time() - start) * 1000)
            )
        return TestResult(
            name="NAS Media Mount",
            status=TestStatus.WARN,
            message="Not mounted or empty",
            duration_ms=int((time.time() - start) * 1000)
        )
    
    def test_git_repo_status(self) -> TestResult:
        """Test git repository status."""
        start = time.time()
        out, err, code = run_ssh_command(
            self.ssh_client,
            "cd /home/mycosoft/mycosoft/mas && git log --oneline -1"
        )
        
        if out:
            return TestResult(
                name="Git Repository",
                status=TestStatus.PASS,
                message=out[:50],
                duration_ms=int((time.time() - start) * 1000)
            )
        return TestResult(
            name="Git Repository",
            status=TestStatus.FAIL,
            message="Could not get git status",
            duration_ms=int((time.time() - start) * 1000)
        )
    
    def run_all_tests(self) -> TestSuite:
        """Run all infrastructure tests."""
        self.suite.start_time = datetime.now()
        
        print_header("PHASE 1: INFRASTRUCTURE TESTS")
        
        # 1. SSH Connectivity
        print(f"\n{Colors.BOLD}1.1 Connectivity Tests{Colors.END}")
        result = self.test_ssh_connectivity()
        self.suite.add_result(result)
        print_result(result)
        
        if result.status == TestStatus.FAIL:
            print(f"\n{Colors.RED}Cannot continue without SSH connection.{Colors.END}")
            self.suite.end_time = datetime.now()
            return self.suite
        
        # 2. Container Health
        print(f"\n{Colors.BOLD}1.2 Container Health{Colors.END}")
        for container in EXPECTED_CONTAINERS:
            result = self.test_container_running(container)
            self.suite.add_result(result)
            print_result(result)
        
        # 3. Container Logs
        print(f"\n{Colors.BOLD}1.3 Container Logs (Error Check){Colors.END}")
        for container in EXPECTED_CONTAINERS:
            result = self.test_container_logs_errors(container)
            self.suite.add_result(result)
            print_result(result)
        
        # 4. Port Checks
        print(f"\n{Colors.BOLD}1.4 Port Availability{Colors.END}")
        for port, service in EXPECTED_PORTS.items():
            result = self.test_port_listening(port, service)
            self.suite.add_result(result)
            print_result(result)
        
        # 5. HTTP Endpoints
        print(f"\n{Colors.BOLD}1.5 HTTP Endpoints{Colors.END}")
        endpoints = [
            ("Website Homepage", f"http://{self.vm_host}:3000"),
            ("NatureOS", f"http://{self.vm_host}:3000/natureos"),
            ("MINDEX API", f"http://{self.vm_host}:8000"),
            ("MINDEX Docs", f"http://{self.vm_host}:8000/docs"),
            ("Mycorrhizae Health", f"http://{self.vm_host}:8002/health"),
            ("n8n Editor", f"http://{self.vm_host}:5678"),
            ("Voice Tools", f"http://{self.vm_host}:8000/api/voice/tools"),
            ("Brain Status", f"http://{self.vm_host}:8000/api/brain/status"),
        ]
        for name, url in endpoints:
            result = self.test_http_endpoint(name, url)
            self.suite.add_result(result)
            print_result(result)
        
        # 6. Database Tests
        print(f"\n{Colors.BOLD}1.6 Database Connectivity{Colors.END}")
        for test_func in [
            self.test_postgres_connectivity,
            self.test_postgres_databases,
            self.test_redis_connectivity,
            self.test_redis_keyspace,
        ]:
            result = test_func()
            self.suite.add_result(result)
            print_result(result)
        
        # 7. System Resources
        print(f"\n{Colors.BOLD}1.7 System Resources{Colors.END}")
        for test_func in [
            self.test_disk_space,
            self.test_memory_usage,
            self.test_nas_mount,
            self.test_git_repo_status,
        ]:
            result = test_func()
            self.suite.add_result(result)
            print_result(result)
        
        # Close SSH
        if self.ssh_client:
            self.ssh_client.close()
        
        self.suite.end_time = datetime.now()
        return self.suite

def print_summary(suite: TestSuite):
    """Print test summary."""
    print_header("INFRASTRUCTURE TEST SUMMARY")
    
    duration = (suite.end_time - suite.start_time).total_seconds() if suite.end_time and suite.start_time else 0
    
    print(f"  Total Tests: {len(suite.results)}")
    print(f"  {Colors.GREEN}Passed: {suite.passed}{Colors.END}")
    print(f"  {Colors.RED}Failed: {suite.failed}{Colors.END}")
    print(f"  {Colors.YELLOW}Warnings: {suite.warned}{Colors.END}")
    print(f"  Duration: {duration:.2f}s")
    
    if suite.failed > 0:
        print(f"\n{Colors.BOLD}{Colors.RED}Failed Tests:{Colors.END}")
        for result in suite.results:
            if result.status == TestStatus.FAIL:
                print(f"  - {result.name}: {result.message}")
    
    return suite.failed == 0

def main():
    """Main entry point."""
    print(f"\n{Colors.BOLD}MYCOSOFT COMPREHENSIVE SYSTEM TEST{Colors.END}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tester = InfrastructureTests()
    suite = tester.run_all_tests()
    
    success = print_summary(suite)
    
    # Save results to JSON
    results_file = f"tests/infra_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    results_data = {
        "suite": suite.name,
        "start_time": suite.start_time.isoformat() if suite.start_time else None,
        "end_time": suite.end_time.isoformat() if suite.end_time else None,
        "passed": suite.passed,
        "failed": suite.failed,
        "warned": suite.warned,
        "results": [
            {
                "name": r.name,
                "status": r.status.value,
                "message": r.message,
                "details": r.details,
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
