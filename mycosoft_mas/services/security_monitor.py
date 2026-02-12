"""
Mycosoft MAS - Security Monitor Service

This module monitors security-related events and vulnerabilities.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import asyncio
from pathlib import Path

logger = logging.getLogger(__name__)

class SecurityMonitor:
    """Service for monitoring security events and vulnerabilities."""
    
    def __init__(self):
        self.security_alerts: List[Dict[str, Any]] = []
        self.vulnerabilities: List[Dict[str, Any]] = []
        self.security_updates: List[Dict[str, Any]] = []
        self.last_check = datetime.now()
        
    async def check_security(self) -> Dict[str, Any]:
        """Check for security issues, vulnerabilities, and updates."""
        try:
            # Check for vulnerabilities
            vulns = await self._check_vulnerabilities()
            
            # Check for security alerts
            alerts = await self._check_security_alerts()
            
            # Check for security updates
            updates = await self._check_security_updates()
            
            self.last_check = datetime.now()
            
            return {
                'vulnerabilities': vulns,
                'security_alerts': alerts,
                'security_updates': updates,
                'last_check': self.last_check.isoformat()
            }
        except Exception as e:
            logger.error(f"Error checking security: {str(e)}")
            return {
                'error': str(e),
                'last_check': self.last_check.isoformat()
            }
            
    async def _check_vulnerabilities(self) -> List[Dict[str, Any]]:
        """
        Check for security vulnerabilities using VulnerabilityScanner.
        
        Performs:
        - Code pattern scanning (OWASP Top 10)
        - Secret detection
        - Dependency CVE scanning
        
        Returns:
            List of vulnerability findings with severity, location, and remediation info
        """
        try:
            from mycosoft_mas.security.vulnerability_scanner import get_vulnerability_scanner
            
            # Get the scanner instance
            scanner = await get_vulnerability_scanner()
            
            # Scan the MAS codebase
            mas_root = Path(__file__).parent.parent.parent
            scan_results = await scanner.full_scan(str(mas_root))
            
            # Extract critical and high severity vulnerabilities
            vulnerabilities = []
            
            # Add critical vulnerabilities
            for vuln in scan_results.get("critical_vulnerabilities", []):
                vulnerabilities.append({
                    "severity": "critical",
                    "category": vuln.get("category"),
                    "message": vuln.get("message"),
                    "file": vuln.get("file"),
                    "line": vuln.get("line"),
                    "detected_at": vuln.get("detected_at"),
                    "remediation": self._get_remediation_advice(vuln)
                })
            
            # Add high severity vulnerabilities
            for vuln in scan_results.get("high_vulnerabilities", []):
                vulnerabilities.append({
                    "severity": "high",
                    "category": vuln.get("category"),
                    "message": vuln.get("message"),
                    "file": vuln.get("file"),
                    "line": vuln.get("line"),
                    "detected_at": vuln.get("detected_at"),
                    "remediation": self._get_remediation_advice(vuln)
                })
            
            # Store for status reporting
            self.vulnerabilities = vulnerabilities
            
            # Log summary
            logger.info(
                f"Vulnerability scan complete: {scan_results['total_vulnerabilities']} total, "
                f"{len(scan_results['critical_vulnerabilities'])} critical, "
                f"{len(scan_results['high_vulnerabilities'])} high"
            )
            
            return vulnerabilities
            
        except Exception as e:
            logger.error(f"Error checking vulnerabilities: {str(e)}")
            return []
    
    def _get_remediation_advice(self, vuln: Dict[str, Any]) -> str:
        """
        Provide remediation advice based on vulnerability type.
        
        Args:
            vuln: Vulnerability details
            
        Returns:
            Human-readable remediation advice
        """
        category = vuln.get("category", "")
        message = vuln.get("message", "")
        
        # Secret detection
        if "API key" in message or "token" in message.lower() or "password" in message.lower():
            return "Remove hardcoded secret and use environment variables or secret manager"
        
        # OWASP A01 - Broken Access Control
        if "Endpoint without auth check" in message:
            return "Add authentication decorator (@require_auth) to endpoint"
        
        # OWASP A02 - Cryptographic Failures
        if "MD5" in message or "SHA1" in message:
            return "Use SHA256 or bcrypt for password hashing"
        if "base64" in message:
            return "Replace base64 with proper encryption (AES-GCM, Fernet)"
        if "random.random" in message:
            return "Use secrets.token_bytes() or secrets.token_hex() for secure random"
        
        # OWASP A03 - Injection
        if "SQL injection" in message:
            return "Use parameterized queries with placeholders (?)"
        if "Command injection" in message:
            return "Avoid shell=True, use subprocess with list arguments"
        if "eval" in message or "exec" in message:
            return "Remove eval/exec or use ast.literal_eval for safe evaluation"
        
        # OWASP A04 - Insecure Design
        if "Missing security implementation" in message:
            return "Implement the security feature immediately - no placeholders in production"
        
        # OWASP A05 - Security Misconfiguration
        if "Debug mode" in message:
            return "Set DEBUG=False in production environments"
        if "CORS allows all origins" in message:
            return "Restrict CORS to specific trusted domains"
        if "SSL verification disabled" in message:
            return "Remove verify=False and use proper CA certificates"
        
        # OWASP A07 - Auth Failures
        if "JWT verification disabled" in message:
            return "Enable JWT signature verification"
        
        # OWASP A08 - Software Integrity
        if "pickle" in message:
            return "Use JSON for serialization or sign pickle data"
        if "yaml.load" in message:
            return "Use yaml.safe_load() instead of yaml.load()"
        
        # CVE in dependencies
        if category == "cve" and vuln.get("fix_version"):
            return f"Update to version {vuln['fix_version']} or later"
        
        # Default
        return "Review code and apply security best practices"
            
    async def _check_security_alerts(self) -> List[Dict[str, Any]]:
        """Check for security alerts."""
        try:
            # TODO: Implement actual alert checking logic
            return []
        except Exception as e:
            logger.error(f"Error checking security alerts: {str(e)}")
            return []
            
    async def _check_security_updates(self) -> List[Dict[str, Any]]:
        """Check for security updates."""
        try:
            # TODO: Implement actual update checking logic
            return []
        except Exception as e:
            logger.error(f"Error checking security updates: {str(e)}")
            return []
            
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the security monitor."""
        return {
            'security_alerts_count': len(self.security_alerts),
            'vulnerabilities_count': len(self.vulnerabilities),
            'security_updates_count': len(self.security_updates),
            'last_check': self.last_check.isoformat()
        }
        
    def clear_alerts(self) -> None:
        """Clear all stored alerts and updates."""
        self.security_alerts.clear()
        self.vulnerabilities.clear()
        self.security_updates.clear() 