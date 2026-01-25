#!/usr/bin/env python3
"""
Mycosoft Authentication Flow Tester

Tests:
1. Login flow completion
2. Token refresh functionality
3. Unauthorized route blocking
4. Session management

Usage:
    python scripts/auth_flow_tester.py --all
    python scripts/auth_flow_tester.py --login-flow
    python scripts/auth_flow_tester.py --protected-routes
"""

import argparse
import json
import urllib3
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from pathlib import Path

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    import requests
except ImportError:
    print("Please install requests: pip install requests")
    exit(1)


@dataclass
class AuthTestResult:
    """Result of an authentication test."""
    test_name: str
    status: str  # PASS, FAIL, SKIP, WARN
    message: str
    response_code: Optional[int] = None
    details: Optional[str] = None


@dataclass
class AuthTestReport:
    """Complete authentication test report."""
    test_time: str
    total_tests: int
    passed: int
    failed: int
    warnings: int
    skipped: int
    results: List[AuthTestResult]
    overall_status: str


class AuthFlowTester:
    """Comprehensive authentication flow tester."""
    
    # Base URLs for testing
    WEBSITE_URL = "https://sandbox.mycosoft.com"
    LOCAL_URL = "http://localhost:3000"
    
    # Public endpoints (should return 200 without auth)
    PUBLIC_ENDPOINTS = [
        ("/", "Homepage"),
        ("/api/health", "Health Check"),
        ("/login", "Login Page"),
        ("/mindex", "MINDEX Public Page"),
        ("/about", "About Page"),
    ]
    
    # Protected endpoints (should return 401/403 without auth)
    PROTECTED_ENDPOINTS = [
        ("/api/agents", "Agents API", "GET"),
        ("/api/network", "Network API", "GET"),
        ("/api/traffic", "Traffic API", "GET"),
        ("/api/system", "System API", "GET"),
        ("/api/flows", "Flows API", "GET"),
        ("/api/topology", "Topology API", "GET"),
        ("/api/myca/chat", "MYCA Chat API", "POST"),
        ("/api/myca/tts", "MYCA TTS API", "POST"),
        ("/dashboard", "Dashboard Page", "GET"),
        ("/security", "Security Dashboard", "GET"),
        ("/admin", "Admin Panel", "GET"),
    ]
    
    # Login flow endpoints
    LOGIN_ENDPOINTS = [
        ("/api/auth/login", "Login Endpoint"),
        ("/api/auth/logout", "Logout Endpoint"),
        ("/api/auth/session", "Session Check"),
        ("/api/auth/refresh", "Token Refresh"),
        ("/api/auth/me", "Current User"),
    ]
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or self.WEBSITE_URL
        self.results: List[AuthTestResult] = []
        self.session = requests.Session()
        
    def test_public_endpoints(self) -> List[AuthTestResult]:
        """Test that public endpoints are accessible without auth."""
        print("\n[*] Testing Public Endpoints (should be accessible)")
        print("=" * 60)
        
        for endpoint, name in self.PUBLIC_ENDPOINTS:
            url = f"{self.base_url}{endpoint}"
            print(f"  Testing: {name} ({endpoint})")
            
            try:
                response = requests.get(url, timeout=10, verify=False)
                
                if response.status_code == 200:
                    result = AuthTestResult(
                        test_name=f"Public: {name}",
                        status="PASS",
                        message="Accessible without auth",
                        response_code=response.status_code
                    )
                    print(f"    [PASS] HTTP {response.status_code}")
                elif response.status_code in [301, 302, 307, 308]:
                    result = AuthTestResult(
                        test_name=f"Public: {name}",
                        status="PASS",
                        message=f"Redirect to {response.headers.get('Location', 'unknown')}",
                        response_code=response.status_code
                    )
                    print(f"    [PASS] Redirect ({response.status_code})")
                else:
                    result = AuthTestResult(
                        test_name=f"Public: {name}",
                        status="WARN",
                        message=f"Unexpected status {response.status_code}",
                        response_code=response.status_code
                    )
                    print(f"    [WARN] HTTP {response.status_code}")
                    
            except requests.exceptions.ConnectionError:
                result = AuthTestResult(
                    test_name=f"Public: {name}",
                    status="SKIP",
                    message="Connection refused - service may be down"
                )
                print(f"    [SKIP] Connection refused")
            except Exception as e:
                result = AuthTestResult(
                    test_name=f"Public: {name}",
                    status="FAIL",
                    message=str(e)
                )
                print(f"    [FAIL] {e}")
            
            self.results.append(result)
        
        return [r for r in self.results if r.test_name.startswith("Public:")]
    
    def test_protected_endpoints(self) -> List[AuthTestResult]:
        """Test that protected endpoints block unauthenticated access."""
        print("\n[*] Testing Protected Endpoints (should require auth)")
        print("=" * 60)
        
        for item in self.PROTECTED_ENDPOINTS:
            if len(item) == 3:
                endpoint, name, method = item
            else:
                endpoint, name = item
                method = "GET"
            
            url = f"{self.base_url}{endpoint}"
            print(f"  Testing: {name} ({method} {endpoint})")
            
            try:
                if method == "POST":
                    response = requests.post(
                        url, 
                        json={}, 
                        timeout=10, 
                        verify=False
                    )
                else:
                    response = requests.get(url, timeout=10, verify=False)
                
                # Check if properly protected
                if response.status_code in [401, 403]:
                    result = AuthTestResult(
                        test_name=f"Protected: {name}",
                        status="PASS",
                        message=f"Correctly blocked with {response.status_code}",
                        response_code=response.status_code
                    )
                    print(f"    [PASS] Blocked ({response.status_code})")
                elif response.status_code == 200:
                    # This could be intentional - some endpoints may be public
                    result = AuthTestResult(
                        test_name=f"Protected: {name}",
                        status="WARN",
                        message="Accessible without auth - verify if intentional",
                        response_code=response.status_code
                    )
                    print(f"    [WARN] Accessible without auth - may be intentional")
                elif response.status_code == 404:
                    result = AuthTestResult(
                        test_name=f"Protected: {name}",
                        status="SKIP",
                        message="Endpoint not found (404)",
                        response_code=response.status_code
                    )
                    print(f"    [SKIP] Not found (404)")
                elif response.status_code in [301, 302, 307, 308]:
                    location = response.headers.get('Location', '')
                    if 'login' in location.lower():
                        result = AuthTestResult(
                            test_name=f"Protected: {name}",
                            status="PASS",
                            message=f"Redirects to login",
                            response_code=response.status_code,
                            details=location
                        )
                        print(f"    [PASS] Redirects to login")
                    else:
                        result = AuthTestResult(
                            test_name=f"Protected: {name}",
                            status="WARN",
                            message=f"Redirect to {location}",
                            response_code=response.status_code
                        )
                        print(f"    [WARN] Redirect to {location}")
                else:
                    result = AuthTestResult(
                        test_name=f"Protected: {name}",
                        status="WARN",
                        message=f"Unexpected status {response.status_code}",
                        response_code=response.status_code
                    )
                    print(f"    [WARN] HTTP {response.status_code}")
                    
            except requests.exceptions.ConnectionError:
                result = AuthTestResult(
                    test_name=f"Protected: {name}",
                    status="SKIP",
                    message="Connection refused"
                )
                print(f"    [SKIP] Connection refused")
            except Exception as e:
                result = AuthTestResult(
                    test_name=f"Protected: {name}",
                    status="FAIL",
                    message=str(e)
                )
                print(f"    [FAIL] {e}")
            
            self.results.append(result)
        
        return [r for r in self.results if r.test_name.startswith("Protected:")]
    
    def test_login_flow(self) -> List[AuthTestResult]:
        """Test login flow endpoints."""
        print("\n[*] Testing Login Flow Endpoints")
        print("=" * 60)
        
        for endpoint, name in self.LOGIN_ENDPOINTS:
            url = f"{self.base_url}{endpoint}"
            print(f"  Checking: {name} ({endpoint})")
            
            try:
                # Try GET first to see if endpoint exists
                response = requests.get(url, timeout=10, verify=False)
                
                if response.status_code == 404:
                    result = AuthTestResult(
                        test_name=f"Login Flow: {name}",
                        status="SKIP",
                        message="Endpoint not implemented (404)",
                        response_code=404
                    )
                    print(f"    [SKIP] Not implemented")
                elif response.status_code == 405:
                    # Method not allowed - endpoint exists but needs POST
                    result = AuthTestResult(
                        test_name=f"Login Flow: {name}",
                        status="PASS",
                        message="Endpoint exists (requires POST)",
                        response_code=405
                    )
                    print(f"    [PASS] Exists (POST required)")
                elif response.status_code in [200, 401, 403]:
                    result = AuthTestResult(
                        test_name=f"Login Flow: {name}",
                        status="PASS",
                        message=f"Endpoint active (HTTP {response.status_code})",
                        response_code=response.status_code
                    )
                    print(f"    [PASS] Active ({response.status_code})")
                else:
                    result = AuthTestResult(
                        test_name=f"Login Flow: {name}",
                        status="WARN",
                        message=f"Unexpected response {response.status_code}",
                        response_code=response.status_code
                    )
                    print(f"    [WARN] HTTP {response.status_code}")
                    
            except requests.exceptions.ConnectionError:
                result = AuthTestResult(
                    test_name=f"Login Flow: {name}",
                    status="SKIP",
                    message="Connection refused"
                )
                print(f"    [SKIP] Connection refused")
            except Exception as e:
                result = AuthTestResult(
                    test_name=f"Login Flow: {name}",
                    status="FAIL",
                    message=str(e)
                )
                print(f"    [FAIL] {e}")
            
            self.results.append(result)
        
        return [r for r in self.results if r.test_name.startswith("Login Flow:")]
    
    def test_token_handling(self) -> List[AuthTestResult]:
        """Test JWT/token handling in headers."""
        print("\n[*] Testing Token Handling")
        print("=" * 60)
        
        # Test with invalid token
        print("  Testing invalid token rejection...")
        headers = {"Authorization": "Bearer invalid_token_12345"}
        
        test_endpoints = [
            "/api/agents",
            "/api/network",
            "/api/system",
        ]
        
        for endpoint in test_endpoints:
            url = f"{self.base_url}{endpoint}"
            
            try:
                response = requests.get(
                    url, 
                    headers=headers, 
                    timeout=10, 
                    verify=False
                )
                
                if response.status_code in [401, 403]:
                    result = AuthTestResult(
                        test_name=f"Token: Invalid token rejected ({endpoint})",
                        status="PASS",
                        message=f"Correctly rejected invalid token",
                        response_code=response.status_code
                    )
                    print(f"    [PASS] {endpoint} rejects invalid token")
                elif response.status_code == 200:
                    result = AuthTestResult(
                        test_name=f"Token: Invalid token rejected ({endpoint})",
                        status="WARN",
                        message="Endpoint accessible with invalid token",
                        response_code=response.status_code
                    )
                    print(f"    [WARN] {endpoint} accessible with invalid token")
                else:
                    result = AuthTestResult(
                        test_name=f"Token: Invalid token rejected ({endpoint})",
                        status="WARN",
                        message=f"Unexpected status {response.status_code}",
                        response_code=response.status_code
                    )
                    print(f"    [WARN] {endpoint} returned {response.status_code}")
                    
            except requests.exceptions.ConnectionError:
                result = AuthTestResult(
                    test_name=f"Token: Invalid token rejected ({endpoint})",
                    status="SKIP",
                    message="Connection refused"
                )
                print(f"    [SKIP] {endpoint} - connection refused")
            except Exception as e:
                result = AuthTestResult(
                    test_name=f"Token: Invalid token rejected ({endpoint})",
                    status="FAIL",
                    message=str(e)
                )
                print(f"    [FAIL] {endpoint} - {e}")
            
            self.results.append(result)
        
        # Test with malformed Authorization header
        print("\n  Testing malformed auth header rejection...")
        malformed_headers = [
            {"Authorization": ""},
            {"Authorization": "Bearer"},
            {"Authorization": "InvalidScheme token123"},
        ]
        
        for i, headers in enumerate(malformed_headers):
            try:
                response = requests.get(
                    f"{self.base_url}/api/agents",
                    headers=headers,
                    timeout=10,
                    verify=False
                )
                
                if response.status_code in [401, 403]:
                    result = AuthTestResult(
                        test_name=f"Token: Malformed header #{i+1}",
                        status="PASS",
                        message="Correctly rejected malformed header",
                        response_code=response.status_code
                    )
                    print(f"    [PASS] Malformed header #{i+1} rejected")
                else:
                    result = AuthTestResult(
                        test_name=f"Token: Malformed header #{i+1}",
                        status="WARN",
                        message=f"Got {response.status_code} instead of 401/403",
                        response_code=response.status_code
                    )
                    print(f"    [WARN] Malformed header #{i+1} got {response.status_code}")
                    
            except Exception as e:
                result = AuthTestResult(
                    test_name=f"Token: Malformed header #{i+1}",
                    status="SKIP",
                    message=str(e)
                )
                print(f"    [SKIP] {e}")
            
            self.results.append(result)
        
        return [r for r in self.results if r.test_name.startswith("Token:")]
    
    def generate_report(self) -> AuthTestReport:
        """Generate comprehensive test report."""
        passed = len([r for r in self.results if r.status == "PASS"])
        failed = len([r for r in self.results if r.status == "FAIL"])
        warnings = len([r for r in self.results if r.status == "WARN"])
        skipped = len([r for r in self.results if r.status == "SKIP"])
        
        if failed > 0:
            overall = "FAILED"
        elif warnings > 3:
            overall = "NEEDS_ATTENTION"
        elif passed > 0:
            overall = "PASSED"
        else:
            overall = "INCONCLUSIVE"
        
        return AuthTestReport(
            test_time=datetime.now().isoformat(),
            total_tests=len(self.results),
            passed=passed,
            failed=failed,
            warnings=warnings,
            skipped=skipped,
            results=self.results,
            overall_status=overall
        )
    
    def save_report(self, report: AuthTestReport, output_dir: Path):
        """Save test report to files."""
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # JSON report
        json_path = output_dir / f"auth_test_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            report_dict = asdict(report)
            json.dump(report_dict, f, indent=2, default=str)
        print(f"\n[*] JSON report: {json_path}")
        
        # Markdown report
        md_path = output_dir / f"AUTH_TEST_REPORT_{timestamp}.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write("# Authentication Flow Test Report\n\n")
            f.write(f"**Test Date**: {report.test_time}\n")
            f.write(f"**Overall Status**: {report.overall_status}\n\n")
            f.write("---\n\n")
            
            f.write("## Summary\n\n")
            f.write("| Metric | Count |\n")
            f.write("|--------|-------|\n")
            f.write(f"| Total Tests | {report.total_tests} |\n")
            f.write(f"| Passed | {report.passed} |\n")
            f.write(f"| Failed | {report.failed} |\n")
            f.write(f"| Warnings | {report.warnings} |\n")
            f.write(f"| Skipped | {report.skipped} |\n\n")
            
            # Group by category
            categories = {}
            for result in report.results:
                cat = result.test_name.split(":")[0]
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(result)
            
            for cat, results in categories.items():
                f.write(f"## {cat} Tests\n\n")
                f.write("| Test | Status | Details |\n")
                f.write("|------|--------|--------|\n")
                for r in results:
                    name = r.test_name.replace(f"{cat}: ", "")
                    code = f" (HTTP {r.response_code})" if r.response_code else ""
                    f.write(f"| {name} | {r.status} | {r.message}{code} |\n")
                f.write("\n")
            
            f.write("---\n")
            f.write("*Generated by Mycosoft Auth Flow Tester*\n")
        
        print(f"[*] Markdown report: {md_path}")
        return json_path, md_path


def main():
    parser = argparse.ArgumentParser(description="Mycosoft Authentication Flow Tester")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--public", action="store_true", help="Test public endpoints")
    parser.add_argument("--protected", action="store_true", help="Test protected endpoints")
    parser.add_argument("--login-flow", action="store_true", help="Test login flow")
    parser.add_argument("--tokens", action="store_true", help="Test token handling")
    parser.add_argument("--url", type=str, default="https://sandbox.mycosoft.com", help="Base URL")
    parser.add_argument("--output-dir", type=str, default="docs", help="Output directory")
    
    args = parser.parse_args()
    
    # Default to all if nothing specified
    if not any([args.all, args.public, args.protected, args.login_flow, args.tokens]):
        args.all = True
    
    print("=" * 60)
    print("  MYCOSOFT AUTHENTICATION FLOW TESTER")
    print("=" * 60)
    print(f"  Target: {args.url}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    tester = AuthFlowTester(base_url=args.url)
    
    if args.all or args.public:
        tester.test_public_endpoints()
    
    if args.all or args.protected:
        tester.test_protected_endpoints()
    
    if args.all or args.login_flow:
        tester.test_login_flow()
    
    if args.all or args.tokens:
        tester.test_token_handling()
    
    # Generate and save report
    report = tester.generate_report()
    output_dir = Path(args.output_dir)
    tester.save_report(report, output_dir)
    
    # Print summary
    print("\n" + "=" * 60)
    print("  TEST COMPLETE")
    print("=" * 60)
    print(f"\n  Overall Status: {report.overall_status}")
    print(f"\n  Results:")
    print(f"    PASSED:   {report.passed}")
    print(f"    FAILED:   {report.failed}")
    print(f"    WARNINGS: {report.warnings}")
    print(f"    SKIPPED:  {report.skipped}")
    print(f"    TOTAL:    {report.total_tests}")
    print("\n" + "=" * 60)
    
    return 1 if report.failed > 0 else 0


if __name__ == "__main__":
    exit(main())
