#!/usr/bin/env python3
"""
Mycosoft Security Audit Scanner

Comprehensive security audit including:
- API authentication testing (ensure protected endpoints reject unauthenticated access)
- Leaked secrets detection in API responses
- Proxmox infrastructure scan
- UniFi network scan
- Certificate validation

Usage:
    python scripts/security_audit_scanner.py --all
    python scripts/security_audit_scanner.py --api-auth
    python scripts/security_audit_scanner.py --secrets-check
    python scripts/security_audit_scanner.py --proxmox
    python scripts/security_audit_scanner.py --unifi
"""

import argparse
import json
import re
import ssl
import socket
import urllib3
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional, Tuple
import warnings

# Disable SSL warnings for internal testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore')

try:
    import requests
except ImportError:
    print("Please install requests: pip install requests")
    exit(1)


@dataclass
class SecurityFinding:
    """Represents a security finding."""
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    category: str  # api_auth, secrets, network, certificate, etc.
    title: str
    description: str
    remediation: str
    evidence: Optional[str] = None


@dataclass
class AuditReport:
    """Complete security audit report."""
    scan_time: str
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    findings: List[SecurityFinding] = field(default_factory=list)
    api_tests: List[Dict] = field(default_factory=list)
    proxmox_status: Optional[Dict] = None
    unifi_status: Optional[Dict] = None
    overall_risk: str = "UNKNOWN"


class SecurityAuditScanner:
    """Comprehensive security audit scanner."""
    
    # Known endpoints that SHOULD require authentication
    PROTECTED_ENDPOINTS = {
        # MycoBrain control endpoints (should be protected)
        "mycobrain_connect": {
            "url": "http://localhost:8003/devices/connect/COM7",
            "method": "POST",
            "should_reject_unauth": True,
            "description": "MycoBrain device connect"
        },
        "mycobrain_disconnect": {
            "url": "http://localhost:8003/devices/disconnect/COM7",
            "method": "POST",
            "should_reject_unauth": True,
            "description": "MycoBrain device disconnect"
        },
        "mycobrain_command": {
            "url": "http://localhost:8003/devices/COM7/command",
            "method": "POST",
            "should_reject_unauth": True,
            "description": "MycoBrain send command"
        },
        # Security API endpoints
        "security_block_ip": {
            "url": "http://localhost:3000/api/security",
            "method": "POST",
            "body": {"action": "block_ip", "ip": "192.0.2.1"},
            "should_reject_unauth": True,
            "description": "Security IP blocking"
        },
    }
    
    # Endpoints that are intentionally public
    PUBLIC_ENDPOINTS = {
        "website_home": {
            "url": "https://sandbox.mycosoft.com",
            "method": "GET",
            "expected_status": [200],
            "description": "Website homepage"
        },
        "mindex_health": {
            "url": "http://192.168.0.187:8000/health",
            "method": "GET",
            "expected_status": [200],
            "description": "MINDEX health check"
        },
        "mycobrain_health": {
            "url": "http://localhost:8003/health",
            "method": "GET",
            "expected_status": [200],
            "description": "MycoBrain health (public read)"
        },
        "mycobrain_devices": {
            "url": "http://localhost:8003/devices",
            "method": "GET",
            "expected_status": [200],
            "description": "MycoBrain devices list (public read)"
        },
    }
    
    # Patterns that indicate leaked secrets in responses
    SECRET_PATTERNS = [
        (r'sk-[a-zA-Z0-9]{48}', 'OpenAI API Key'),
        (r'sk-ant-[a-zA-Z0-9\-]{40,}', 'Anthropic API Key'),
        (r'eyJ[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+', 'JWT Token (may be intentional)'),
        (r'AKIA[0-9A-Z]{16}', 'AWS Access Key ID'),
        (r'ghp_[a-zA-Z0-9]{36}', 'GitHub Personal Access Token'),
        (r'gho_[a-zA-Z0-9]{36}', 'GitHub OAuth Token'),
        (r'glpat-[a-zA-Z0-9\-]{20}', 'GitLab Personal Access Token'),
        (r'xox[baprs]-[a-zA-Z0-9\-]+', 'Slack Token'),
        (r'sk_live_[a-zA-Z0-9]{24,}', 'Stripe Live Key'),
        (r'pk_live_[a-zA-Z0-9]{24,}', 'Stripe Publishable Key'),
        (r'sq0atp-[a-zA-Z0-9\-_]{22}', 'Square Access Token'),
        (r'AIza[0-9A-Za-z\-_]{35}', 'Google API Key'),
        (r'[a-z0-9]{32}', 'Potential 32-char secret (check context)'),
        (r'password["\s:=]+["\']?[^"\'>\s]{8,}', 'Potential password in response'),
        (r'secret["\s:=]+["\']?[^"\'>\s]{8,}', 'Potential secret in response'),
        (r'api[_-]?key["\s:=]+["\']?[^"\'>\s]{16,}', 'Potential API key in response'),
    ]
    
    # Proxmox API configuration
    PROXMOX_CONFIG = {
        "host": "192.168.0.202",
        "port": 8006,
        "token": "root@pam!cursor_agent=bc1c9dc7-6fca-4e89-8a1d-557a9d117a3e"
    }
    
    # UniFi API configuration
    UNIFI_CONFIG = {
        "host": "192.168.0.1",
        "port": 443,
        "username": "cursor_agent",
        "password": "Mushroom1!2020",
    }
    
    def __init__(self):
        self.findings: List[SecurityFinding] = []
        self.api_tests: List[Dict] = []
        
    def test_api_authentication(self) -> List[Dict]:
        """Test that protected endpoints reject unauthenticated access."""
        print("\n[*] Testing API Authentication (Protected Endpoints)")
        print("=" * 60)
        
        results = []
        
        for name, config in self.PROTECTED_ENDPOINTS.items():
            print(f"  Testing: {config['description']}...")
            
            try:
                if config['method'] == 'POST':
                    body = config.get('body', {})
                    response = requests.post(
                        config['url'],
                        json=body,
                        timeout=5,
                        verify=False
                    )
                else:
                    response = requests.get(
                        config['url'],
                        timeout=5,
                        verify=False
                    )
                
                status = response.status_code
                
                # Check if it properly rejects unauthenticated access
                if config['should_reject_unauth']:
                    if status in [401, 403]:
                        result = {
                            "endpoint": name,
                            "url": config['url'],
                            "status": "PASS",
                            "message": f"Correctly rejected with {status}",
                            "response_code": status
                        }
                        print(f"    [PASS] Correctly rejected ({status})")
                    else:
                        result = {
                            "endpoint": name,
                            "url": config['url'],
                            "status": "FAIL",
                            "message": f"Should reject unauthenticated but got {status}",
                            "response_code": status
                        }
                        print(f"    [FAIL] Got {status} - should be 401/403")
                        
                        self.findings.append(SecurityFinding(
                            severity="HIGH",
                            category="api_auth",
                            title=f"Unprotected Endpoint: {name}",
                            description=f"{config['description']} accepts unauthenticated requests (got {status})",
                            remediation="Add authentication middleware to this endpoint",
                            evidence=f"URL: {config['url']}, Response: {status}"
                        ))
                else:
                    result = {
                        "endpoint": name,
                        "url": config['url'],
                        "status": "INFO",
                        "message": f"Public endpoint returned {status}",
                        "response_code": status
                    }
                    
            except requests.exceptions.ConnectionError:
                result = {
                    "endpoint": name,
                    "url": config['url'],
                    "status": "SKIP",
                    "message": "Service not reachable",
                    "response_code": None
                }
                print(f"    [SKIP] Service not reachable")
            except Exception as e:
                result = {
                    "endpoint": name,
                    "url": config['url'],
                    "status": "ERROR",
                    "message": str(e),
                    "response_code": None
                }
                print(f"    [ERROR] {e}")
            
            results.append(result)
        
        self.api_tests = results
        return results
    
    def check_for_leaked_secrets(self, endpoints: List[str] = None) -> List[SecurityFinding]:
        """Check API responses for leaked secrets."""
        print("\n[*] Checking for Leaked Secrets in API Responses")
        print("=" * 60)
        
        if endpoints is None:
            endpoints = [
                "https://sandbox.mycosoft.com/api/health",
                "http://localhost:3000/api/health",
                "http://localhost:8003/health",
                "http://localhost:8003/devices",
            ]
        
        for url in endpoints:
            print(f"  Checking: {url}")
            
            try:
                response = requests.get(url, timeout=10, verify=False)
                content = response.text
                
                # Check for secret patterns
                for pattern, secret_type in self.SECRET_PATTERNS:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        # Filter out false positives for common patterns
                        if '32-char' in secret_type and len(matches) > 5:
                            continue  # Too many matches, likely false positives
                        
                        self.findings.append(SecurityFinding(
                            severity="CRITICAL" if "API Key" in secret_type else "HIGH",
                            category="secrets",
                            title=f"Potential {secret_type} Leak",
                            description=f"Found potential {secret_type} in API response from {url}",
                            remediation="Remove secrets from API responses, use environment variables",
                            evidence=f"Pattern matched: {pattern[:30]}... (matches redacted)"
                        ))
                        print(f"    [ALERT] Potential {secret_type} found!")
                        
                print(f"    [OK] No obvious secrets detected")
                        
            except requests.exceptions.ConnectionError:
                print(f"    [SKIP] Not reachable")
            except Exception as e:
                print(f"    [ERROR] {e}")
        
        return [f for f in self.findings if f.category == "secrets"]
    
    def scan_proxmox(self) -> Optional[Dict]:
        """Scan Proxmox infrastructure via API."""
        print("\n[*] Scanning Proxmox Infrastructure")
        print("=" * 60)
        
        base_url = f"https://{self.PROXMOX_CONFIG['host']}:{self.PROXMOX_CONFIG['port']}/api2/json"
        headers = {
            "Authorization": f"PVEAPIToken={self.PROXMOX_CONFIG['token']}"
        }
        
        result = {
            "status": "unknown",
            "nodes": [],
            "vms": [],
            "security_issues": []
        }
        
        try:
            # Get nodes
            print("  Fetching nodes...")
            response = requests.get(
                f"{base_url}/nodes",
                headers=headers,
                verify=False,
                timeout=10
            )
            
            if response.status_code == 200:
                nodes_data = response.json().get("data", [])
                result["nodes"] = nodes_data
                print(f"    Found {len(nodes_data)} node(s)")
                
                # Get VMs for each node
                for node in nodes_data:
                    node_name = node.get("node", "unknown")
                    print(f"  Scanning VMs on {node_name}...")
                    
                    vm_response = requests.get(
                        f"{base_url}/nodes/{node_name}/qemu",
                        headers=headers,
                        verify=False,
                        timeout=10
                    )
                    
                    if vm_response.status_code == 200:
                        vms = vm_response.json().get("data", [])
                        for vm in vms:
                            vm["node"] = node_name
                            result["vms"].append(vm)
                            
                            # Check VM security
                            vm_name = vm.get("name", "unknown")
                            vm_status = vm.get("status", "unknown")
                            
                            print(f"    VM {vm.get('vmid')}: {vm_name} ({vm_status})")
                            
                            # Security checks
                            if vm_status == "running":
                                # Check if VM has QEMU agent
                                if not vm.get("agent"):
                                    result["security_issues"].append({
                                        "vm": vm_name,
                                        "issue": "QEMU agent not detected",
                                        "severity": "LOW"
                                    })
                
                result["status"] = "success"
                print(f"\n  Total VMs: {len(result['vms'])}")
                print(f"  Security Issues: {len(result['security_issues'])}")
                
            else:
                result["status"] = "error"
                result["error"] = f"HTTP {response.status_code}"
                print(f"    [ERROR] HTTP {response.status_code}")
                
                self.findings.append(SecurityFinding(
                    severity="MEDIUM",
                    category="infrastructure",
                    title="Proxmox API Access Issue",
                    description=f"Could not access Proxmox API: HTTP {response.status_code}",
                    remediation="Check Proxmox API token permissions"
                ))
                
        except requests.exceptions.ConnectionError:
            result["status"] = "unreachable"
            print("    [ERROR] Proxmox not reachable")
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            print(f"    [ERROR] {e}")
        
        return result
    
    def scan_unifi(self) -> Optional[Dict]:
        """Scan UniFi network infrastructure."""
        print("\n[*] Scanning UniFi Network Infrastructure")
        print("=" * 60)
        
        result = {
            "status": "unknown",
            "devices": [],
            "clients": [],
            "security_issues": []
        }
        
        unifi_url = f"https://{self.UNIFI_CONFIG['host']}"
        
        try:
            # Check if credentials are configured
            if self.UNIFI_CONFIG.get('username') and self.UNIFI_CONFIG.get('password'):
                print(f"  Authenticating to UniFi at {unifi_url}...")
                
                # Login to UniFi
                login_response = requests.post(
                    f"{unifi_url}/api/auth/login",
                    json={
                        "username": self.UNIFI_CONFIG['username'],
                        "password": self.UNIFI_CONFIG['password']
                    },
                    verify=False,
                    timeout=10
                )
                
                if login_response.status_code == 200:
                    print("    [OK] UniFi authentication successful")
                    result["status"] = "authenticated"
                    cookies = login_response.cookies
                    
                    # Get devices
                    print("  Fetching network devices...")
                    devices_response = requests.get(
                        f"{unifi_url}/proxy/network/api/s/default/stat/device",
                        cookies=cookies,
                        verify=False,
                        timeout=10
                    )
                    
                    if devices_response.status_code == 200:
                        devices_data = devices_response.json().get("data", [])
                        result["devices"] = devices_data
                        print(f"    Found {len(devices_data)} network device(s)")
                        
                        for device in devices_data:
                            device_name = device.get("name", device.get("model", "Unknown"))
                            device_type = device.get("type", "unknown")
                            device_state = device.get("state", 0)
                            state_text = "online" if device_state == 1 else "offline"
                            print(f"      - {device_name} ({device_type}): {state_text}")
                            
                            # Security checks on devices
                            if device.get("upgradable"):
                                result["security_issues"].append({
                                    "device": device_name,
                                    "issue": "Firmware update available",
                                    "severity": "MEDIUM"
                                })
                    
                    # Get clients
                    print("  Fetching connected clients...")
                    clients_response = requests.get(
                        f"{unifi_url}/proxy/network/api/s/default/stat/sta",
                        cookies=cookies,
                        verify=False,
                        timeout=10
                    )
                    
                    if clients_response.status_code == 200:
                        clients_data = clients_response.json().get("data", [])
                        result["clients"] = clients_data
                        print(f"    Found {len(clients_data)} connected client(s)")
                    
                    print(f"\n  Security Issues: {len(result['security_issues'])}")
                    
                else:
                    print(f"    [FAIL] Authentication failed: HTTP {login_response.status_code}")
                    result["status"] = "auth_failed"
                    self.findings.append(SecurityFinding(
                        severity="MEDIUM",
                        category="network",
                        title="UniFi Authentication Failed",
                        description=f"Could not authenticate to UniFi controller: HTTP {login_response.status_code}",
                        remediation="Verify UniFi API credentials"
                    ))
            else:
                # No credentials - just check reachability
                print(f"  Checking UniFi at {unifi_url}...")
                response = requests.get(unifi_url, timeout=5, verify=False)
                
                if response.status_code == 200:
                    print("    [OK] UniFi controller reachable")
                    print("    [INFO] Configure credentials for full scan")
                    result["status"] = "reachable"
                else:
                    result["status"] = "error"
                    print(f"    [WARN] Got HTTP {response.status_code}")
                    
        except requests.exceptions.SSLError:
            print("    [OK] UniFi reachable (SSL cert issue - normal for self-signed)")
            result["status"] = "reachable_ssl_warning"
        except requests.exceptions.ConnectionError:
            print("    [ERROR] UniFi controller not reachable")
            result["status"] = "unreachable"
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            print(f"    [ERROR] {e}")
        
        return result
    
    def check_ssl_certificates(self, hosts: List[str] = None) -> List[SecurityFinding]:
        """Check SSL certificate validity for hosts."""
        print("\n[*] Checking SSL Certificates")
        print("=" * 60)
        
        if hosts is None:
            hosts = [
                ("sandbox.mycosoft.com", 443),
                ("mycosoft.com", 443),
            ]
        
        for host_info in hosts:
            if isinstance(host_info, tuple):
                hostname, port = host_info
            else:
                hostname = host_info
                port = 443
            
            print(f"  Checking: {hostname}:{port}")
            
            try:
                context = ssl.create_default_context()
                with socket.create_connection((hostname, port), timeout=5) as sock:
                    with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                        cert = ssock.getpeercert()
                        
                        # Check expiration
                        not_after = cert.get('notAfter', '')
                        if not_after:
                            # Parse SSL date format
                            from datetime import datetime
                            try:
                                exp_date = datetime.strptime(not_after, '%b %d %H:%M:%S %Y %Z')
                                days_until_expiry = (exp_date - datetime.now()).days
                                
                                if days_until_expiry < 0:
                                    print(f"    [CRITICAL] Certificate EXPIRED!")
                                    self.findings.append(SecurityFinding(
                                        severity="CRITICAL",
                                        category="certificate",
                                        title=f"Expired SSL Certificate: {hostname}",
                                        description="SSL certificate has expired",
                                        remediation="Renew SSL certificate immediately"
                                    ))
                                elif days_until_expiry < 30:
                                    print(f"    [WARN] Expires in {days_until_expiry} days")
                                    self.findings.append(SecurityFinding(
                                        severity="MEDIUM",
                                        category="certificate",
                                        title=f"SSL Certificate Expiring Soon: {hostname}",
                                        description=f"Certificate expires in {days_until_expiry} days",
                                        remediation="Plan certificate renewal"
                                    ))
                                else:
                                    print(f"    [OK] Valid for {days_until_expiry} days")
                            except ValueError:
                                print(f"    [WARN] Could not parse expiry date")
                        
            except ssl.SSLCertVerificationError as e:
                print(f"    [WARN] Certificate verification failed: {e}")
            except socket.timeout:
                print(f"    [SKIP] Connection timeout")
            except Exception as e:
                print(f"    [ERROR] {e}")
        
        return [f for f in self.findings if f.category == "certificate"]
    
    def generate_report(self) -> AuditReport:
        """Generate comprehensive audit report."""
        critical = len([f for f in self.findings if f.severity == "CRITICAL"])
        high = len([f for f in self.findings if f.severity == "HIGH"])
        medium = len([f for f in self.findings if f.severity == "MEDIUM"])
        low = len([f for f in self.findings if f.severity == "LOW"])
        
        if critical > 0:
            risk = "CRITICAL"
        elif high > 0:
            risk = "HIGH"
        elif medium > 0:
            risk = "MEDIUM"
        elif low > 0:
            risk = "LOW"
        else:
            risk = "HEALTHY"
        
        return AuditReport(
            scan_time=datetime.now().isoformat(),
            total_findings=len(self.findings),
            critical_count=critical,
            high_count=high,
            medium_count=medium,
            low_count=low,
            findings=self.findings,
            api_tests=self.api_tests,
            overall_risk=risk
        )
    
    def save_report(self, report: AuditReport, output_dir: Path):
        """Save audit report to files."""
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save JSON report
        json_path = output_dir / f"security_audit_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            report_dict = asdict(report)
            report_dict["findings"] = [asdict(f) for f in report.findings]
            json.dump(report_dict, f, indent=2, default=str)
        print(f"\n[*] JSON report saved: {json_path}")
        
        # Save Markdown report
        md_path = output_dir / f"SECURITY_AUDIT_{timestamp}.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write("# Mycosoft Security Audit Report\n\n")
            f.write(f"**Scan Date**: {report.scan_time}\n")
            f.write(f"**Overall Risk**: {report.overall_risk}\n\n")
            f.write("---\n\n")
            
            f.write("## Summary\n\n")
            f.write(f"| Severity | Count |\n")
            f.write(f"|----------|-------|\n")
            f.write(f"| CRITICAL | {report.critical_count} |\n")
            f.write(f"| HIGH | {report.high_count} |\n")
            f.write(f"| MEDIUM | {report.medium_count} |\n")
            f.write(f"| LOW | {report.low_count} |\n")
            f.write(f"| **TOTAL** | **{report.total_findings}** |\n\n")
            
            # API Auth Tests
            if report.api_tests:
                f.write("## API Authentication Tests\n\n")
                f.write("| Endpoint | Status | Details |\n")
                f.write("|----------|--------|--------|\n")
                for test in report.api_tests:
                    f.write(f"| {test['endpoint']} | {test['status']} | {test['message']} |\n")
                f.write("\n")
            
            # Findings
            if report.findings:
                f.write("## Security Findings\n\n")
                for finding in report.findings:
                    f.write(f"### [{finding.severity}] {finding.title}\n\n")
                    f.write(f"**Category**: {finding.category}\n\n")
                    f.write(f"**Description**: {finding.description}\n\n")
                    f.write(f"**Remediation**: {finding.remediation}\n\n")
                    if finding.evidence:
                        f.write(f"**Evidence**: `{finding.evidence}`\n\n")
                    f.write("---\n\n")
            
            f.write("*Report generated by Mycosoft Security Audit Scanner*\n")
        
        print(f"[*] Markdown report saved: {md_path}")
        
        return json_path, md_path


def main():
    parser = argparse.ArgumentParser(description="Mycosoft Security Audit Scanner")
    parser.add_argument("--all", action="store_true", help="Run all security checks")
    parser.add_argument("--api-auth", action="store_true", help="Test API authentication")
    parser.add_argument("--secrets-check", action="store_true", help="Check for leaked secrets")
    parser.add_argument("--proxmox", action="store_true", help="Scan Proxmox infrastructure")
    parser.add_argument("--unifi", action="store_true", help="Scan UniFi network")
    parser.add_argument("--ssl", action="store_true", help="Check SSL certificates")
    parser.add_argument("--output-dir", type=str, default="docs", help="Output directory for reports")
    
    args = parser.parse_args()
    
    # Default to all if nothing specified
    if not any([args.all, args.api_auth, args.secrets_check, args.proxmox, args.unifi, args.ssl]):
        args.all = True
    
    print("=" * 60)
    print("  MYCOSOFT SECURITY AUDIT SCANNER")
    print("=" * 60)
    print(f"  Scan Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    scanner = SecurityAuditScanner()
    
    if args.all or args.api_auth:
        scanner.test_api_authentication()
    
    if args.all or args.secrets_check:
        scanner.check_for_leaked_secrets()
    
    if args.all or args.ssl:
        scanner.check_ssl_certificates()
    
    if args.all or args.proxmox:
        proxmox_result = scanner.scan_proxmox()
    
    if args.all or args.unifi:
        unifi_result = scanner.scan_unifi()
    
    # Generate and save report
    report = scanner.generate_report()
    output_dir = Path(args.output_dir)
    json_path, md_path = scanner.save_report(report, output_dir)
    
    # Print summary
    print("\n" + "=" * 60)
    print("  AUDIT COMPLETE")
    print("=" * 60)
    print(f"\n  Overall Risk Level: {report.overall_risk}")
    print(f"\n  Findings Summary:")
    print(f"    CRITICAL: {report.critical_count}")
    print(f"    HIGH:     {report.high_count}")
    print(f"    MEDIUM:   {report.medium_count}")
    print(f"    LOW:      {report.low_count}")
    print(f"    TOTAL:    {report.total_findings}")
    print("\n" + "=" * 60)
    
    # Return non-zero if critical issues found
    if report.critical_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    exit(main())
