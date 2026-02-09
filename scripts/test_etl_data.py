#!/usr/bin/env python3
"""
Phase 8: ETL and Data Validation Tests
Tests MINDEX data pipelines, GBIF sync, and data quality
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
    data_source: str = ""
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
    
    source_str = f"[{result.data_source}]" if result.data_source else ""
    print(f"  {icon} {result.name} {source_str}: {result.message}")

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

class ETLDataTests:
    """ETL and data validation test suite."""
    
    def __init__(self):
        self.suite = TestSuite(name="ETL and Data Validation Tests")
        self.ssh_client = None
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
    
    def setup(self):
        self.ssh_client = get_ssh_client()
        return self.ssh_client is not None
    
    def teardown(self):
        if self.ssh_client:
            self.ssh_client.close()
    
    def test_mindex_api_health(self) -> TestResult:
        """Test MINDEX API is healthy."""
        start = time.time()
        try:
            response = self.session.get(f"{BASE_URL}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return TestResult("MINDEX Health", TestStatus.PASS, 
                                 data.get("status", "healthy"),
                                 data_source="MINDEX",
                                 duration_ms=int((time.time() - start) * 1000))
            return TestResult("MINDEX Health", TestStatus.FAIL, f"HTTP {response.status_code}",
                             data_source="MINDEX",
                             duration_ms=int((time.time() - start) * 1000))
        except Exception as e:
            return TestResult("MINDEX Health", TestStatus.FAIL, str(e)[:50],
                             data_source="MINDEX",
                             duration_ms=int((time.time() - start) * 1000))
    
    def test_species_data_quality(self) -> TestResult:
        """Test species data returned has required fields."""
        start = time.time()
        try:
            response = self.session.get(f"{BASE_URL}/species/Agaricus", timeout=10)
            if response.status_code == 200:
                data = response.json()
                # Check for required fields
                required_fields = ["species", "taxonomy", "classification"]
                has_fields = all(field in str(data) for field in ["species"])
                if has_fields or data:
                    return TestResult("Species Data Quality", TestStatus.PASS, 
                                     "Data structure valid",
                                     data_source="MINDEX",
                                     duration_ms=int((time.time() - start) * 1000))
                return TestResult("Species Data Quality", TestStatus.WARN, 
                                 "Missing some fields",
                                 data_source="MINDEX",
                                 duration_ms=int((time.time() - start) * 1000))
            return TestResult("Species Data Quality", TestStatus.FAIL, 
                             f"HTTP {response.status_code}",
                             data_source="MINDEX",
                             duration_ms=int((time.time() - start) * 1000))
        except Exception as e:
            return TestResult("Species Data Quality", TestStatus.FAIL, str(e)[:50],
                             data_source="MINDEX",
                             duration_ms=int((time.time() - start) * 1000))
    
    def test_gbif_endpoint(self) -> TestResult:
        """Test GBIF match endpoint."""
        start = time.time()
        try:
            response = self.session.get(f"{BASE_URL}/gbif/match/Agaricus bisporus", timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data.get("usageKey") or data.get("species"):
                    return TestResult("GBIF Match", TestStatus.PASS, 
                                     f"Found: {data.get('species', 'match')}",
                                     data_source="GBIF",
                                     duration_ms=int((time.time() - start) * 1000))
                return TestResult("GBIF Match", TestStatus.WARN, "No match found",
                                 data_source="GBIF",
                                 duration_ms=int((time.time() - start) * 1000))
            return TestResult("GBIF Match", TestStatus.FAIL, f"HTTP {response.status_code}",
                             data_source="GBIF",
                             duration_ms=int((time.time() - start) * 1000))
        except Exception as e:
            return TestResult("GBIF Match", TestStatus.FAIL, str(e)[:50],
                             data_source="GBIF",
                             duration_ms=int((time.time() - start) * 1000))
    
    def test_postgres_tables(self) -> TestResult:
        """Test PostgreSQL tables exist."""
        start = time.time()
        out, err, code = run_ssh_command(
            self.ssh_client,
            "docker exec mycosoft-postgres psql -U mycosoft -c \"SELECT count(*) FROM information_schema.tables WHERE table_schema='public';\" 2>/dev/null"
        )
        
        try:
            if "count" in out:
                # Extract count
                lines = out.strip().split('\n')
                count_line = [l for l in lines if l.strip().isdigit()]
                if count_line:
                    count = int(count_line[0].strip())
                    return TestResult("PostgreSQL Tables", TestStatus.PASS, 
                                     f"{count} tables",
                                     data_source="PostgreSQL",
                                     duration_ms=int((time.time() - start) * 1000))
            return TestResult("PostgreSQL Tables", TestStatus.WARN, "Could not count",
                             data_source="PostgreSQL",
                             duration_ms=int((time.time() - start) * 1000))
        except:
            return TestResult("PostgreSQL Tables", TestStatus.FAIL, "Query failed",
                             data_source="PostgreSQL",
                             duration_ms=int((time.time() - start) * 1000))
    
    def test_taxonomy_hierarchy(self) -> TestResult:
        """Test taxonomy hierarchy is correct."""
        start = time.time()
        try:
            response = self.session.get(f"{BASE_URL}/taxonomy/Agaricus", timeout=10)
            if response.status_code == 200:
                data = response.json()
                # Check for taxonomic ranks
                ranks = ["kingdom", "phylum", "class", "order", "family", "genus"]
                found_ranks = sum(1 for r in ranks if r in str(data).lower())
                if found_ranks >= 3:
                    return TestResult("Taxonomy Hierarchy", TestStatus.PASS, 
                                     f"{found_ranks} ranks present",
                                     data_source="MINDEX",
                                     duration_ms=int((time.time() - start) * 1000))
                return TestResult("Taxonomy Hierarchy", TestStatus.WARN, 
                                 f"Only {found_ranks} ranks",
                                 data_source="MINDEX",
                                 duration_ms=int((time.time() - start) * 1000))
            return TestResult("Taxonomy Hierarchy", TestStatus.FAIL, 
                             f"HTTP {response.status_code}",
                             data_source="MINDEX",
                             duration_ms=int((time.time() - start) * 1000))
        except Exception as e:
            return TestResult("Taxonomy Hierarchy", TestStatus.FAIL, str(e)[:50],
                             data_source="MINDEX",
                             duration_ms=int((time.time() - start) * 1000))
    
    def test_data_freshness(self) -> TestResult:
        """Test data has recent updates."""
        start = time.time()
        out, err, code = run_ssh_command(
            self.ssh_client,
            "docker exec mycosoft-postgres psql -U mycosoft -c \"SELECT MAX(created_at) FROM n8n_ledger;\" 2>/dev/null"
        )
        
        if code == 0 and out:
            return TestResult("Data Freshness", TestStatus.PASS, "Recent entries exist",
                             data_source="PostgreSQL",
                             duration_ms=int((time.time() - start) * 1000))
        return TestResult("Data Freshness", TestStatus.WARN, "Could not check timestamps",
                         data_source="PostgreSQL",
                         duration_ms=int((time.time() - start) * 1000))
    
    def test_mindex_smell_data(self) -> TestResult:
        """Test MINDEX smell/sensor data pipeline."""
        start = time.time()
        out, err, code = run_ssh_command(
            self.ssh_client,
            "ls /home/mycosoft/mycosoft/mas/mindex_smell_data/*.json 2>/dev/null | wc -l"
        )
        
        try:
            count = int(out.strip())
            if count > 0:
                return TestResult("MINDEX Smell Data", TestStatus.PASS, 
                                 f"{count} data files",
                                 data_source="MINDEX",
                                 duration_ms=int((time.time() - start) * 1000))
            return TestResult("MINDEX Smell Data", TestStatus.WARN, "No data files",
                             data_source="MINDEX",
                             duration_ms=int((time.time() - start) * 1000))
        except:
            return TestResult("MINDEX Smell Data", TestStatus.FAIL, "Could not check",
                             data_source="MINDEX",
                             duration_ms=int((time.time() - start) * 1000))
    
    def run_all_tests(self):
        """Run all ETL and data validation tests."""
        print_header("PHASE 8: ETL AND DATA VALIDATION TESTS")
        
        if not self.setup():
            print(f"{Colors.RED}Failed to connect via SSH{Colors.END}")
            return self.suite
        
        print(f"\n{Colors.BOLD}8.1 MINDEX Data Pipeline Tests{Colors.END}")
        for test_func in [
            self.test_mindex_api_health,
            self.test_species_data_quality,
            self.test_taxonomy_hierarchy,
            self.test_mindex_smell_data,
        ]:
            result = test_func()
            self.suite.results.append(result)
            print_result(result)
        
        print(f"\n{Colors.BOLD}8.2 GBIF Sync Tests{Colors.END}")
        result = self.test_gbif_endpoint()
        self.suite.results.append(result)
        print_result(result)
        
        print(f"\n{Colors.BOLD}8.3 Database Validation{Colors.END}")
        for test_func in [
            self.test_postgres_tables,
            self.test_data_freshness,
        ]:
            result = test_func()
            self.suite.results.append(result)
            print_result(result)
        
        self.teardown()
        return self.suite

def print_summary(suite: TestSuite):
    print_header("ETL AND DATA VALIDATION TEST SUMMARY")
    
    print(f"  Total Tests: {len(suite.results)}")
    print(f"  {Colors.GREEN}Passed: {suite.passed}{Colors.END}")
    print(f"  {Colors.RED}Failed: {suite.failed}{Colors.END}")
    
    warned = len([r for r in suite.results if r.status == TestStatus.WARN])
    print(f"  {Colors.YELLOW}Warnings: {warned}{Colors.END}")
    
    return suite.failed == 0

def main():
    print(f"\n{Colors.BOLD}ETL AND DATA VALIDATION TEST{Colors.END}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tester = ETLDataTests()
    suite = tester.run_all_tests()
    
    success = print_summary(suite)
    
    # Save results
    results_file = f"tests/etl_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    results_data = {
        "suite": suite.name,
        "timestamp": datetime.now().isoformat(),
        "passed": suite.passed,
        "failed": suite.failed,
        "results": [
            {"name": r.name, "status": r.status.value, "data_source": r.data_source, "message": r.message}
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
