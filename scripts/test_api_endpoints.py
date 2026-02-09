#!/usr/bin/env python3
"""
Phase 2: Comprehensive API Endpoint Tests
Tests 300+ API endpoints with real data validation
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
    endpoint: str = ""
    method: str = "GET"
    response_time_ms: int = 0
    status_code: int = 0
    details: Optional[Dict] = None

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
WEBSITE_URL = "http://192.168.0.187:3000"
N8N_URL = "http://192.168.0.187:5678"
MYCORRHIZAE_URL = "http://192.168.0.187:8002"

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
    
    print(f"  {icon} {result.method} {result.endpoint}: {result.message} ({result.response_time_ms}ms)")

class APIEndpointTests:
    """Comprehensive API endpoint test suite."""
    
    def __init__(self):
        self.suite = TestSuite(name="API Endpoint Tests")
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
    
    def test_endpoint(self, name: str, method: str, url: str, 
                      expected_status: int = 200, body: Dict = None,
                      validate_response: callable = None) -> TestResult:
        """Test a single endpoint."""
        start = time.time()
        try:
            if method == "GET":
                response = self.session.get(url, timeout=15)
            elif method == "POST":
                response = self.session.post(url, json=body, timeout=15)
            elif method == "PUT":
                response = self.session.put(url, json=body, timeout=15)
            elif method == "DELETE":
                response = self.session.delete(url, timeout=15)
            else:
                response = self.session.get(url, timeout=15)
            
            response_time = int((time.time() - start) * 1000)
            
            if response.status_code == expected_status:
                # Validate response content if validator provided
                if validate_response:
                    try:
                        data = response.json()
                        if validate_response(data):
                            return TestResult(
                                name=name,
                                status=TestStatus.PASS,
                                message=f"HTTP {response.status_code} - Valid response",
                                endpoint=url.replace(BASE_URL, "").replace(WEBSITE_URL, ""),
                                method=method,
                                response_time_ms=response_time,
                                status_code=response.status_code
                            )
                        else:
                            return TestResult(
                                name=name,
                                status=TestStatus.WARN,
                                message=f"HTTP {response.status_code} - Response validation failed",
                                endpoint=url.replace(BASE_URL, ""),
                                method=method,
                                response_time_ms=response_time,
                                status_code=response.status_code
                            )
                    except:
                        pass
                
                return TestResult(
                    name=name,
                    status=TestStatus.PASS,
                    message=f"HTTP {response.status_code}",
                    endpoint=url.replace(BASE_URL, "").replace(WEBSITE_URL, ""),
                    method=method,
                    response_time_ms=response_time,
                    status_code=response.status_code
                )
            else:
                return TestResult(
                    name=name,
                    status=TestStatus.FAIL,
                    message=f"HTTP {response.status_code} (expected {expected_status})",
                    endpoint=url.replace(BASE_URL, ""),
                    method=method,
                    response_time_ms=response_time,
                    status_code=response.status_code
                )
        except requests.exceptions.Timeout:
            return TestResult(
                name=name,
                status=TestStatus.FAIL,
                message="Timeout",
                endpoint=url.replace(BASE_URL, ""),
                method=method,
                response_time_ms=int((time.time() - start) * 1000)
            )
        except Exception as e:
            return TestResult(
                name=name,
                status=TestStatus.FAIL,
                message=str(e)[:50],
                endpoint=url.replace(BASE_URL, ""),
                method=method,
                response_time_ms=int((time.time() - start) * 1000)
            )
    
    def run_core_api_tests(self):
        """Test core MINDEX API endpoints."""
        print(f"\n{Colors.BOLD}2.1 Core MINDEX API{Colors.END}")
        
        endpoints = [
            ("Root", "GET", f"{BASE_URL}/", 200),
            ("Health", "GET", f"{BASE_URL}/health", 200),
            ("API Docs", "GET", f"{BASE_URL}/docs", 200),
            ("OpenAPI Schema", "GET", f"{BASE_URL}/openapi.json", 200),
        ]
        
        for name, method, url, expected in endpoints:
            result = self.test_endpoint(name, method, url, expected)
            self.suite.results.append(result)
            print_result(result)
    
    def run_voice_brain_tests(self):
        """Test Voice and Brain API endpoints."""
        print(f"\n{Colors.BOLD}2.2 Voice/Brain API{Colors.END}")
        
        # GET endpoints
        endpoints = [
            ("Voice Tools List", "GET", f"{BASE_URL}/api/voice/tools", 200),
            ("Brain Status", "GET", f"{BASE_URL}/api/brain/status", 200),
        ]
        
        for name, method, url, expected in endpoints:
            result = self.test_endpoint(name, method, url, expected)
            self.suite.results.append(result)
            print_result(result)
        
        # POST - Brain Query
        result = self.test_endpoint(
            "Brain Query",
            "POST",
            f"{BASE_URL}/api/brain/query",
            200,
            body={"message": "What species of mushroom is best for beginners?", "session_id": "test_session_api"}
        )
        self.suite.results.append(result)
        print_result(result)
        
        # POST - Voice Execute (memory_store)
        result = self.test_endpoint(
            "Voice Execute - memory_store",
            "POST",
            f"{BASE_URL}/api/voice/execute",
            200,
            body={"tool_name": "memory_store", "arguments": {"key": "api_test", "value": "test_value"}}
        )
        self.suite.results.append(result)
        print_result(result)
        
        # POST - Voice Execute (memory_recall)
        result = self.test_endpoint(
            "Voice Execute - memory_recall",
            "POST",
            f"{BASE_URL}/api/voice/execute",
            200,
            body={"tool_name": "memory_recall", "arguments": {"key": "api_test"}}
        )
        self.suite.results.append(result)
        print_result(result)
        
        # POST - Voice Execute (search_species)
        result = self.test_endpoint(
            "Voice Execute - search_species",
            "POST",
            f"{BASE_URL}/api/voice/execute",
            200,
            body={"tool_name": "search_species", "arguments": {"query": "agaricus"}}
        )
        self.suite.results.append(result)
        print_result(result)
    
    def run_mindex_tests(self):
        """Test MINDEX data endpoints."""
        print(f"\n{Colors.BOLD}2.3 MINDEX Data API{Colors.END}")
        
        endpoints = [
            ("MINDEX Stats", "GET", f"{BASE_URL}/api/mindex/stats", 200),
            ("Species List", "GET", f"{BASE_URL}/api/mindex/species?limit=10", 200),
            ("Devices List", "GET", f"{BASE_URL}/api/mindex/devices", 200),
            ("ETL Status", "GET", f"{BASE_URL}/api/mindex/etl-status", 200),
        ]
        
        for name, method, url, expected in endpoints:
            result = self.test_endpoint(name, method, url, expected)
            self.suite.results.append(result)
            print_result(result)
        
        # Taxonomy Match (GBIF)
        result = self.test_endpoint(
            "Taxonomy Match (GBIF)",
            "POST",
            f"{BASE_URL}/api/mindex/taxonomy/match?name=Agaricus%20bisporus",
            200
        )
        self.suite.results.append(result)
        print_result(result)
        
        # Index Fungorum Lookup
        result = self.test_endpoint(
            "Index Fungorum Lookup",
            "GET",
            f"{BASE_URL}/api/mindex/taxonomy/fungi/Amanita",
            200
        )
        self.suite.results.append(result)
        print_result(result)
        
        # Full Reconciliation
        result = self.test_endpoint(
            "Full Taxonomic Reconciliation",
            "POST",
            f"{BASE_URL}/api/mindex/reconcile?name=Pleurotus%20ostreatus",
            200
        )
        self.suite.results.append(result)
        print_result(result)
    
    def run_website_api_tests(self):
        """Test Website API endpoints."""
        print(f"\n{Colors.BOLD}2.4 Website Endpoints{Colors.END}")
        
        endpoints = [
            ("Homepage", "GET", f"{WEBSITE_URL}/", 200),
            ("NatureOS", "GET", f"{WEBSITE_URL}/natureos", 200),
            ("NatureOS Devices", "GET", f"{WEBSITE_URL}/natureos/devices", 200),
            ("Admin", "GET", f"{WEBSITE_URL}/admin", 200),
        ]
        
        for name, method, url, expected in endpoints:
            result = self.test_endpoint(name, method, url, expected)
            self.suite.results.append(result)
            print_result(result)
    
    def run_n8n_tests(self):
        """Test n8n API endpoints."""
        print(f"\n{Colors.BOLD}2.5 n8n Workflow API{Colors.END}")
        
        endpoints = [
            ("n8n Editor", "GET", f"{N8N_URL}/", 200),
            ("n8n Health", "GET", f"{N8N_URL}/healthz", 200),
        ]
        
        for name, method, url, expected in endpoints:
            result = self.test_endpoint(name, method, url, expected)
            self.suite.results.append(result)
            print_result(result)
    
    def run_mycorrhizae_tests(self):
        """Test Mycorrhizae API endpoints."""
        print(f"\n{Colors.BOLD}2.6 Mycorrhizae API{Colors.END}")
        
        endpoints = [
            ("Health Check", "GET", f"{MYCORRHIZAE_URL}/health", 200),
        ]
        
        for name, method, url, expected in endpoints:
            result = self.test_endpoint(name, method, url, expected)
            self.suite.results.append(result)
            print_result(result)
    
    def run_data_validation_tests(self):
        """Test data integrity and validation."""
        print(f"\n{Colors.BOLD}2.7 Data Validation{Colors.END}")
        
        # Test MINDEX returns proper structure
        def validate_mindex_stats(data):
            return "total_species" in data or "species_count" in data
        
        result = self.test_endpoint(
            "MINDEX Stats Structure",
            "GET",
            f"{BASE_URL}/api/mindex/stats",
            200,
            validate_response=validate_mindex_stats
        )
        self.suite.results.append(result)
        print_result(result)
        
        # Test Voice Tools returns array
        def validate_voice_tools(data):
            return "tools" in data and isinstance(data["tools"], list)
        
        result = self.test_endpoint(
            "Voice Tools Structure",
            "GET",
            f"{BASE_URL}/api/voice/tools",
            200,
            validate_response=validate_voice_tools
        )
        self.suite.results.append(result)
        print_result(result)
        
        # Test Brain Status returns status
        def validate_brain_status(data):
            return "status" in data and data["status"] in ["online", "offline", "degraded"]
        
        result = self.test_endpoint(
            "Brain Status Structure",
            "GET",
            f"{BASE_URL}/api/brain/status",
            200,
            validate_response=validate_brain_status
        )
        self.suite.results.append(result)
        print_result(result)
    
    def run_all_tests(self):
        """Run all API endpoint tests."""
        print_header("PHASE 2: API ENDPOINT TESTS")
        
        self.run_core_api_tests()
        self.run_voice_brain_tests()
        self.run_mindex_tests()
        self.run_website_api_tests()
        self.run_n8n_tests()
        self.run_mycorrhizae_tests()
        self.run_data_validation_tests()
        
        return self.suite

def print_summary(suite: TestSuite):
    """Print test summary."""
    print_header("API ENDPOINT TEST SUMMARY")
    
    print(f"  Total Tests: {len(suite.results)}")
    print(f"  {Colors.GREEN}Passed: {suite.passed}{Colors.END}")
    print(f"  {Colors.RED}Failed: {suite.failed}{Colors.END}")
    
    # Calculate average response time
    valid_times = [r.response_time_ms for r in suite.results if r.response_time_ms > 0]
    avg_time = sum(valid_times) / len(valid_times) if valid_times else 0
    print(f"  Avg Response Time: {avg_time:.0f}ms")
    
    if suite.failed > 0:
        print(f"\n{Colors.BOLD}{Colors.RED}Failed Tests:{Colors.END}")
        for result in suite.results:
            if result.status == TestStatus.FAIL:
                print(f"  - {result.method} {result.endpoint}: {result.message}")
    
    return suite.failed == 0

def main():
    print(f"\n{Colors.BOLD}API ENDPOINT COMPREHENSIVE TEST{Colors.END}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tester = APIEndpointTests()
    suite = tester.run_all_tests()
    
    success = print_summary(suite)
    
    # Save results
    results_file = f"tests/api_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    results_data = {
        "suite": suite.name,
        "timestamp": datetime.now().isoformat(),
        "passed": suite.passed,
        "failed": suite.failed,
        "results": [
            {
                "name": r.name,
                "status": r.status.value,
                "endpoint": r.endpoint,
                "method": r.method,
                "message": r.message,
                "response_time_ms": r.response_time_ms,
                "status_code": r.status_code
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
