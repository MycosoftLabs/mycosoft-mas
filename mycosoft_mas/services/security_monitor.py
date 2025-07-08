"""
Mycosoft MAS - Security Monitor Service

This module monitors security-related events and vulnerabilities.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import asyncio
from pathlib import Path
import json

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
        """Check for security vulnerabilities."""
        try:
            file = Path("data/security/vulnerabilities.json")
            if file.exists():
                with open(file, "r") as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"Error checking vulnerabilities: {str(e)}")
            return []
            
    async def _check_security_alerts(self) -> List[Dict[str, Any]]:
        """Check for security alerts."""
        try:
            file = Path("data/security/alerts.json")
            if file.exists():
                with open(file, "r") as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"Error checking security alerts: {str(e)}")
            return []
            
    async def _check_security_updates(self) -> List[Dict[str, Any]]:
        """Check for security updates."""
        try:
            file = Path("data/security/updates.json")
            if file.exists():
                with open(file, "r") as f:
                    return json.load(f)
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
