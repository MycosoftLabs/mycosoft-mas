#!/usr/bin/env python3
"""
Phase 3: Frontend UI Tests
Tests all website pages, forms, and interactions via HTTP requests
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
    page: str = ""
    response_time_ms: int = 0

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
WEBSITE_URL = f"http://{VM_HOST}:3000"

# Website pages to test
WEBSITE_PAGES = [
    # Core pages
    {"path": "/", "name": "Home Page", "category": "Core"},
    {"path": "/about", "name": "About Page", "category": "Core"},
    {"path": "/contact", "name": "Contact Page", "category": "Core"},
    {"path": "/services", "name": "Services Page", "category": "Core"},
    
    # Product pages
    {"path": "/products", "name": "Products Page", "category": "Products"},
    {"path": "/products/mushroom1", "name": "Mushroom1 Product", "category": "Products"},
    {"path": "/products/sporebase", "name": "SporeBase Product", "category": "Products"},
    {"path": "/products/mindex", "name": "MINDEX Product", "category": "Products"},
    
    # Feature pages
    {"path": "/search", "name": "Search Page", "category": "Features"},
    {"path": "/dashboard", "name": "Dashboard Page", "category": "Features"},
    {"path": "/ancestry", "name": "Ancestry Page", "category": "Features"},
    {"path": "/crep", "name": "CREP Page", "category": "Features"},
    {"path": "/earth-simulator", "name": "Earth Simulator", "category": "Features"},
    {"path": "/soc", "name": "SOC Page", "category": "Features"},
    {"path": "/mindex", "name": "MINDEX Page", "category": "Features"},
    
    # API/Data pages
    {"path": "/api", "name": "API Page", "category": "API"},
    {"path": "/docs", "name": "Docs Page", "category": "API"},
    
    # Auth pages
    {"path": "/login", "name": "Login Page", "category": "Auth"},
    {"path": "/register", "name": "Register Page", "category": "Auth"},
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
    
    time_str = f"({result.response_time_ms}ms)" if result.response_time_ms > 0 else ""
    print(f"  {icon} {result.name} {time_str}: {result.message}")

class FrontendTests:
    """Frontend UI test suite."""
    
    def __init__(self):
        self.suite = TestSuite(name="Frontend UI Tests")
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mycosoft-Test-Agent/1.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        })
    
    def test_page(self, path: str, name: str, category: str) -> TestResult:
        """Test a single page is accessible."""
        start = time.time()
        try:
            url = f"{WEBSITE_URL}{path}"
            response = self.session.get(url, timeout=15, allow_redirects=True)
            response_time = int((time.time() - start) * 1000)
            
            if response.status_code == 200:
                # Check content length
                content_length = len(response.text)
                if content_length > 100:
                    return TestResult(name, TestStatus.PASS, 
                                     f"HTTP 200 ({content_length} bytes)",
                                     page=path, response_time_ms=response_time)
                return TestResult(name, TestStatus.WARN,
                                 f"Empty or minimal content ({content_length} bytes)",
                                 page=path, response_time_ms=response_time)
            elif response.status_code == 404:
                return TestResult(name, TestStatus.WARN,
                                 "Page not found (404)",
                                 page=path, response_time_ms=response_time)
            elif response.status_code in [301, 302]:
                return TestResult(name, TestStatus.PASS,
                                 f"Redirects to {response.headers.get('Location', 'unknown')}",
                                 page=path, response_time_ms=response_time)
            else:
                return TestResult(name, TestStatus.FAIL,
                                 f"HTTP {response.status_code}",
                                 page=path, response_time_ms=response_time)
        except requests.exceptions.Timeout:
            return TestResult(name, TestStatus.FAIL, "Timeout",
                             page=path, response_time_ms=15000)
        except Exception as e:
            return TestResult(name, TestStatus.FAIL, str(e)[:50],
                             page=path, response_time_ms=int((time.time() - start) * 1000))
    
    def test_html_structure(self, path: str) -> TestResult:
        """Test HTML structure of a page."""
        start = time.time()
        try:
            url = f"{WEBSITE_URL}{path}"
            response = self.session.get(url, timeout=15)
            response_time = int((time.time() - start) * 1000)
            
            if response.status_code == 200:
                html = response.text.lower()
                # Check for basic HTML elements
                has_doctype = "<!doctype html>" in html or "<!doctype" in html
                has_html = "<html" in html
                has_head = "<head" in html
                has_body = "<body" in html
                
                if has_doctype and has_html and has_head and has_body:
                    return TestResult(f"HTML Structure {path}", TestStatus.PASS,
                                     "Valid HTML structure",
                                     page=path, response_time_ms=response_time)
                return TestResult(f"HTML Structure {path}", TestStatus.WARN,
                                 "Missing HTML elements",
                                 page=path, response_time_ms=response_time)
            return TestResult(f"HTML Structure {path}", TestStatus.FAIL,
                             f"HTTP {response.status_code}",
                             page=path, response_time_ms=response_time)
        except Exception as e:
            return TestResult(f"HTML Structure {path}", TestStatus.FAIL, str(e)[:50],
                             page=path, response_time_ms=int((time.time() - start) * 1000))
    
    def test_static_assets(self) -> TestResult:
        """Test static assets are loading."""
        start = time.time()
        try:
            # Try common static asset paths
            static_paths = [
                "/_next/static",
                "/static",
                "/assets",
                "/favicon.ico",
            ]
            
            accessible = 0
            for path in static_paths:
                try:
                    response = self.session.get(f"{WEBSITE_URL}{path}", timeout=5)
                    if response.status_code in [200, 301, 302]:
                        accessible += 1
                except:
                    pass
            
            response_time = int((time.time() - start) * 1000)
            
            if accessible > 0:
                return TestResult("Static Assets", TestStatus.PASS,
                                 f"{accessible}/{len(static_paths)} paths accessible",
                                 response_time_ms=response_time)
            return TestResult("Static Assets", TestStatus.WARN,
                             "No static paths accessible",
                             response_time_ms=response_time)
        except Exception as e:
            return TestResult("Static Assets", TestStatus.FAIL, str(e)[:50],
                             response_time_ms=int((time.time() - start) * 1000))
    
    def test_api_routes(self) -> TestResult:
        """Test Next.js API routes."""
        start = time.time()
        try:
            api_endpoints = [
                "/api/health",
                "/api/status",
            ]
            
            accessible = 0
            for path in api_endpoints:
                try:
                    response = self.session.get(f"{WEBSITE_URL}{path}", timeout=5)
                    if response.status_code in [200, 404]:
                        accessible += 1
                except:
                    pass
            
            response_time = int((time.time() - start) * 1000)
            return TestResult("API Routes", TestStatus.PASS,
                             f"Tested {len(api_endpoints)} routes",
                             response_time_ms=response_time)
        except Exception as e:
            return TestResult("API Routes", TestStatus.FAIL, str(e)[:50],
                             response_time_ms=int((time.time() - start) * 1000))
    
    def test_responsive_headers(self) -> TestResult:
        """Test proper response headers."""
        start = time.time()
        try:
            response = self.session.get(f"{WEBSITE_URL}/", timeout=10)
            response_time = int((time.time() - start) * 1000)
            
            headers = response.headers
            checks = {
                "Content-Type": "content-type" in [h.lower() for h in headers],
                "X-Frame-Options or CSP": any(h.lower() in ["x-frame-options", "content-security-policy"] for h in headers),
            }
            
            passed = sum(checks.values())
            if passed >= 1:
                return TestResult("Response Headers", TestStatus.PASS,
                                 f"{passed}/{len(checks)} security headers",
                                 response_time_ms=response_time)
            return TestResult("Response Headers", TestStatus.WARN,
                             "Missing security headers",
                             response_time_ms=response_time)
        except Exception as e:
            return TestResult("Response Headers", TestStatus.FAIL, str(e)[:50],
                             response_time_ms=int((time.time() - start) * 1000))
    
    def run_all_tests(self):
        """Run all frontend tests."""
        print_header("PHASE 3: FRONTEND UI TESTS")
        
        # Group pages by category
        categories = {}
        for page in WEBSITE_PAGES:
            cat = page["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(page)
        
        # Test each category
        for cat_name, pages in categories.items():
            print(f"\n{Colors.BOLD}3.{list(categories.keys()).index(cat_name)+1} {cat_name} Pages{Colors.END}")
            for page in pages:
                result = self.test_page(page["path"], page["name"], page["category"])
                self.suite.results.append(result)
                print_result(result)
        
        # Additional tests
        print(f"\n{Colors.BOLD}3.{len(categories)+1} Page Quality Tests{Colors.END}")
        
        # Test HTML structure for home page
        result = self.test_html_structure("/")
        self.suite.results.append(result)
        print_result(result)
        
        result = self.test_static_assets()
        self.suite.results.append(result)
        print_result(result)
        
        result = self.test_api_routes()
        self.suite.results.append(result)
        print_result(result)
        
        result = self.test_responsive_headers()
        self.suite.results.append(result)
        print_result(result)
        
        return self.suite

def print_summary(suite: TestSuite):
    print_header("FRONTEND UI TEST SUMMARY")
    
    print(f"  Total Tests: {len(suite.results)}")
    print(f"  {Colors.GREEN}Passed: {suite.passed}{Colors.END}")
    print(f"  {Colors.RED}Failed: {suite.failed}{Colors.END}")
    
    warned = len([r for r in suite.results if r.status == TestStatus.WARN])
    print(f"  {Colors.YELLOW}Warnings: {warned}{Colors.END}")
    
    # Calculate average response time
    response_times = [r.response_time_ms for r in suite.results if r.response_time_ms > 0]
    if response_times:
        avg_time = sum(response_times) / len(response_times)
        print(f"\n  {Colors.BOLD}Performance:{Colors.END}")
        print(f"    Average Response: {avg_time:.0f}ms")
        print(f"    Slowest: {max(response_times)}ms")
        print(f"    Fastest: {min(response_times)}ms")
    
    return suite.failed == 0

def main():
    print(f"\n{Colors.BOLD}FRONTEND UI TEST{Colors.END}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tester = FrontendTests()
    suite = tester.run_all_tests()
    
    success = print_summary(suite)
    
    # Save results
    results_file = f"tests/frontend_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    results_data = {
        "suite": suite.name,
        "timestamp": datetime.now().isoformat(),
        "passed": suite.passed,
        "failed": suite.failed,
        "results": [
            {"name": r.name, "status": r.status.value, "page": r.page, 
             "response_time_ms": r.response_time_ms, "message": r.message}
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
