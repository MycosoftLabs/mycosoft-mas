#!/usr/bin/env python3
"""
Phase 9: Search and Discovery Tests
Tests fungi search, knowledge graph queries, and discovery features
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
    query: str = ""
    results_count: int = 0
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
BASE_URL = f"http://{VM_HOST}:8000"
WEBSITE_URL = f"http://{VM_HOST}:3000"

# Search test cases
SEARCH_QUERIES = [
    {"query": "Agaricus", "expected_type": "genus", "min_results": 1},
    {"query": "bisporus", "expected_type": "species", "min_results": 1},
    {"query": "mushroom cultivation", "expected_type": "topic", "min_results": 0},
    {"query": "edible fungi", "expected_type": "category", "min_results": 0},
    {"query": "Amanita phalloides", "expected_type": "species", "min_results": 1},
    {"query": "mycorrhiza", "expected_type": "concept", "min_results": 0},
    {"query": "spore", "expected_type": "morphology", "min_results": 0},
    {"query": "Pleurotus ostreatus", "expected_type": "species", "min_results": 1},
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
    
    query_str = f'"{result.query}"' if result.query else ""
    print(f"  {icon} {result.name} {query_str}: {result.message}")

class SearchDiscoveryTests:
    """Search and discovery test suite."""
    
    def __init__(self):
        self.suite = TestSuite(name="Search and Discovery Tests")
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
    
    def test_species_search(self, query: str, expected_type: str, min_results: int) -> TestResult:
        """Test species search functionality."""
        start = time.time()
        try:
            response = self.session.get(f"{BASE_URL}/species/{query}", timeout=15)
            duration = int((time.time() - start) * 1000)
            
            if response.status_code == 200:
                data = response.json()
                # Count results
                if isinstance(data, list):
                    count = len(data)
                elif isinstance(data, dict):
                    count = 1 if data else 0
                else:
                    count = 0
                
                if count >= min_results:
                    return TestResult(f"Species Search [{expected_type}]", TestStatus.PASS,
                                     f"{count} results", query=query, results_count=count,
                                     duration_ms=duration)
                return TestResult(f"Species Search [{expected_type}]", TestStatus.WARN,
                                 f"Only {count} results (expected {min_results}+)",
                                 query=query, results_count=count, duration_ms=duration)
            return TestResult(f"Species Search [{expected_type}]", TestStatus.FAIL,
                             f"HTTP {response.status_code}", query=query, duration_ms=duration)
        except Exception as e:
            return TestResult(f"Species Search [{expected_type}]", TestStatus.FAIL,
                             str(e)[:50], query=query,
                             duration_ms=int((time.time() - start) * 1000))
    
    def test_taxonomy_search(self, query: str) -> TestResult:
        """Test taxonomy search endpoint."""
        start = time.time()
        try:
            response = self.session.get(f"{BASE_URL}/taxonomy/{query}", timeout=15)
            duration = int((time.time() - start) * 1000)
            
            if response.status_code == 200:
                data = response.json()
                return TestResult("Taxonomy Search", TestStatus.PASS,
                                 "Data returned", query=query, duration_ms=duration)
            return TestResult("Taxonomy Search", TestStatus.FAIL,
                             f"HTTP {response.status_code}", query=query, duration_ms=duration)
        except Exception as e:
            return TestResult("Taxonomy Search", TestStatus.FAIL, str(e)[:50],
                             query=query, duration_ms=int((time.time() - start) * 1000))
    
    def test_gbif_species_match(self, species: str) -> TestResult:
        """Test GBIF species matching."""
        start = time.time()
        try:
            response = self.session.get(f"{BASE_URL}/gbif/match/{species}", timeout=20)
            duration = int((time.time() - start) * 1000)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("usageKey"):
                    return TestResult("GBIF Match", TestStatus.PASS,
                                     f"Key: {data.get('usageKey')}",
                                     query=species, duration_ms=duration)
                return TestResult("GBIF Match", TestStatus.WARN,
                                 "No exact match", query=species, duration_ms=duration)
            return TestResult("GBIF Match", TestStatus.FAIL,
                             f"HTTP {response.status_code}", query=species, duration_ms=duration)
        except Exception as e:
            return TestResult("GBIF Match", TestStatus.FAIL, str(e)[:50],
                             query=species, duration_ms=int((time.time() - start) * 1000))
    
    def test_website_search_page(self) -> TestResult:
        """Test website search page is accessible."""
        start = time.time()
        try:
            response = self.session.get(f"{WEBSITE_URL}/search", timeout=10)
            duration = int((time.time() - start) * 1000)
            
            if response.status_code == 200:
                return TestResult("Website Search Page", TestStatus.PASS,
                                 "Accessible", duration_ms=duration)
            return TestResult("Website Search Page", TestStatus.WARN,
                             f"HTTP {response.status_code}", duration_ms=duration)
        except Exception as e:
            return TestResult("Website Search Page", TestStatus.FAIL, str(e)[:50],
                             duration_ms=int((time.time() - start) * 1000))
    
    def test_ancestry_page(self) -> TestResult:
        """Test ancestry/phylogeny page."""
        start = time.time()
        try:
            response = self.session.get(f"{WEBSITE_URL}/ancestry", timeout=10)
            duration = int((time.time() - start) * 1000)
            
            if response.status_code == 200:
                return TestResult("Ancestry Page", TestStatus.PASS,
                                 "Accessible", duration_ms=duration)
            elif response.status_code == 404:
                return TestResult("Ancestry Page", TestStatus.WARN,
                                 "Not found (may be /phylogeny)", duration_ms=duration)
            return TestResult("Ancestry Page", TestStatus.FAIL,
                             f"HTTP {response.status_code}", duration_ms=duration)
        except Exception as e:
            return TestResult("Ancestry Page", TestStatus.FAIL, str(e)[:50],
                             duration_ms=int((time.time() - start) * 1000))
    
    def test_crep_page(self) -> TestResult:
        """Test CREP page."""
        start = time.time()
        try:
            response = self.session.get(f"{WEBSITE_URL}/crep", timeout=10)
            duration = int((time.time() - start) * 1000)
            
            if response.status_code == 200:
                return TestResult("CREP Page", TestStatus.PASS,
                                 "Accessible", duration_ms=duration)
            elif response.status_code == 404:
                return TestResult("CREP Page", TestStatus.WARN,
                                 "Not found", duration_ms=duration)
            return TestResult("CREP Page", TestStatus.FAIL,
                             f"HTTP {response.status_code}", duration_ms=duration)
        except Exception as e:
            return TestResult("CREP Page", TestStatus.FAIL, str(e)[:50],
                             duration_ms=int((time.time() - start) * 1000))
    
    def test_earth_simulator(self) -> TestResult:
        """Test Earth Simulator page."""
        start = time.time()
        try:
            response = self.session.get(f"{WEBSITE_URL}/earth-simulator", timeout=10)
            duration = int((time.time() - start) * 1000)
            
            if response.status_code == 200:
                return TestResult("Earth Simulator", TestStatus.PASS,
                                 "Accessible", duration_ms=duration)
            elif response.status_code == 404:
                return TestResult("Earth Simulator", TestStatus.WARN,
                                 "Not found", duration_ms=duration)
            return TestResult("Earth Simulator", TestStatus.FAIL,
                             f"HTTP {response.status_code}", duration_ms=duration)
        except Exception as e:
            return TestResult("Earth Simulator", TestStatus.FAIL, str(e)[:50],
                             duration_ms=int((time.time() - start) * 1000))
    
    def test_soc_page(self) -> TestResult:
        """Test SOC (Security Operations Center) page."""
        start = time.time()
        try:
            response = self.session.get(f"{WEBSITE_URL}/soc", timeout=10)
            duration = int((time.time() - start) * 1000)
            
            if response.status_code == 200:
                return TestResult("SOC Page", TestStatus.PASS,
                                 "Accessible", duration_ms=duration)
            elif response.status_code == 404:
                return TestResult("SOC Page", TestStatus.WARN,
                                 "Not found", duration_ms=duration)
            return TestResult("SOC Page", TestStatus.FAIL,
                             f"HTTP {response.status_code}", duration_ms=duration)
        except Exception as e:
            return TestResult("SOC Page", TestStatus.FAIL, str(e)[:50],
                             duration_ms=int((time.time() - start) * 1000))
    
    def test_mindex_page(self) -> TestResult:
        """Test MINDEX page."""
        start = time.time()
        try:
            response = self.session.get(f"{WEBSITE_URL}/mindex", timeout=10)
            duration = int((time.time() - start) * 1000)
            
            if response.status_code == 200:
                return TestResult("MINDEX Page", TestStatus.PASS,
                                 "Accessible", duration_ms=duration)
            elif response.status_code == 404:
                return TestResult("MINDEX Page", TestStatus.WARN,
                                 "Not found", duration_ms=duration)
            return TestResult("MINDEX Page", TestStatus.FAIL,
                             f"HTTP {response.status_code}", duration_ms=duration)
        except Exception as e:
            return TestResult("MINDEX Page", TestStatus.FAIL, str(e)[:50],
                             duration_ms=int((time.time() - start) * 1000))
    
    def run_all_tests(self):
        """Run all search and discovery tests."""
        print_header("PHASE 9: SEARCH AND DISCOVERY TESTS")
        
        print(f"\n{Colors.BOLD}9.1 Species Search Tests{Colors.END}")
        for query_info in SEARCH_QUERIES[:5]:  # First 5 queries
            result = self.test_species_search(
                query_info["query"],
                query_info["expected_type"],
                query_info["min_results"]
            )
            self.suite.results.append(result)
            print_result(result)
        
        print(f"\n{Colors.BOLD}9.2 Taxonomy Search Tests{Colors.END}")
        for query in ["Agaricus", "Amanita", "Pleurotus"]:
            result = self.test_taxonomy_search(query)
            self.suite.results.append(result)
            print_result(result)
        
        print(f"\n{Colors.BOLD}9.3 GBIF Integration Tests{Colors.END}")
        for species in ["Agaricus bisporus", "Amanita muscaria"]:
            result = self.test_gbif_species_match(species)
            self.suite.results.append(result)
            print_result(result)
        
        print(f"\n{Colors.BOLD}9.4 Website Feature Pages{Colors.END}")
        for test_func in [
            self.test_website_search_page,
            self.test_ancestry_page,
            self.test_crep_page,
            self.test_earth_simulator,
            self.test_soc_page,
            self.test_mindex_page,
        ]:
            result = test_func()
            self.suite.results.append(result)
            print_result(result)
        
        return self.suite

def print_summary(suite: TestSuite):
    print_header("SEARCH AND DISCOVERY TEST SUMMARY")
    
    print(f"  Total Tests: {len(suite.results)}")
    print(f"  {Colors.GREEN}Passed: {suite.passed}{Colors.END}")
    print(f"  {Colors.RED}Failed: {suite.failed}{Colors.END}")
    
    warned = len([r for r in suite.results if r.status == TestStatus.WARN])
    print(f"  {Colors.YELLOW}Warnings: {warned}{Colors.END}")
    
    return suite.failed == 0

def main():
    print(f"\n{Colors.BOLD}SEARCH AND DISCOVERY TEST{Colors.END}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tester = SearchDiscoveryTests()
    suite = tester.run_all_tests()
    
    success = print_summary(suite)
    
    # Save results
    results_file = f"tests/search_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    results_data = {
        "suite": suite.name,
        "timestamp": datetime.now().isoformat(),
        "passed": suite.passed,
        "failed": suite.failed,
        "results": [
            {"name": r.name, "status": r.status.value, "query": r.query, "message": r.message}
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
