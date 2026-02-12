"""
SelfHealingMonitor - Automatic Issue Detection and Fix Triggering
Created: February 9, 2026

Monitors system health and triggers automatic fixes:
- Watches for failing tests
- Monitors agent errors/crashes
- Detects API endpoint failures
- Detects security vulnerabilities
- Automatically creates fix requests via CodeModificationService
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import traceback

logger = logging.getLogger(__name__)


class IssueType(str, Enum):
    """Types of issues that can be detected."""
    TEST_FAILURE = "test_failure"
    AGENT_CRASH = "agent_crash"
    AGENT_ERROR = "agent_error"
    API_FAILURE = "api_failure"
    SECURITY_VULNERABILITY = "security_vulnerability"
    HEALTH_CHECK_FAILURE = "health_check_failure"
    MEMORY_ISSUE = "memory_issue"
    PERFORMANCE_DEGRADATION = "performance_degradation"


class IssueSeverity(str, Enum):
    """Severity levels for detected issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SelfHealingMonitor:
    """
    Monitors system health and automatically triggers fixes.
    
    This service runs in the background and:
    1. Collects error reports from agents
    2. Monitors test results
    3. Watches API health endpoints
    4. Detects security vulnerabilities
    5. Automatically creates fix requests for recurring issues
    """
    
    # Threshold for auto-triggering fixes
    ERROR_THRESHOLD = 3  # Same error 3 times = auto-fix
    CHECK_INTERVAL = 60  # Check every 60 seconds
    
    def __init__(self):
        self.is_running = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        # Issue tracking
        self.detected_issues: List[Dict[str, Any]] = []
        self.error_counts: Dict[str, int] = {}  # error_signature -> count
        self.fix_requests_sent: Dict[str, str] = {}  # error_signature -> change_id
        
        # Statistics
        self.issues_detected = 0
        self.fixes_triggered = 0
        self.fixes_successful = 0
        self.last_check: Optional[datetime] = None
        
        # Custom check functions
        self._custom_checks: List[Callable] = []
        
        # Code modification service reference
        self._code_service = None
        
    async def initialize(self):
        """Initialize the monitor and connect to services."""
        try:
            from mycosoft_mas.services.code_modification_service import get_code_modification_service
            self._code_service = await get_code_modification_service()
            logger.info("SelfHealingMonitor initialized with CodeModificationService")
        except Exception as e:
            logger.error(f"Failed to initialize CodeModificationService: {e}")
    
    async def start_monitoring(self):
        """Start the background monitoring task."""
        if self.is_running:
            logger.warning("SelfHealingMonitor is already running")
            return
        
        await self.initialize()
        self.is_running = True
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info("SelfHealingMonitor started")
    
    async def stop_monitoring(self):
        """Stop the background monitoring task."""
        self.is_running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("SelfHealingMonitor stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.is_running:
            try:
                await self._run_checks()
                self.last_check = datetime.now()
                await asyncio.sleep(self.CHECK_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.CHECK_INTERVAL)
    
    async def _run_checks(self):
        """Run all health checks."""
        # Run custom checks
        for check_fn in self._custom_checks:
            try:
                await check_fn()
            except Exception as e:
                logger.error(f"Custom check failed: {e}")
        
        # Check for accumulated errors that need fixing
        await self._process_error_accumulation()
    
    async def _process_error_accumulation(self):
        """Check if any errors have accumulated past threshold."""
        for error_sig, count in list(self.error_counts.items()):
            if count >= self.ERROR_THRESHOLD:
                # Check if we already sent a fix request
                if error_sig not in self.fix_requests_sent:
                    await self._trigger_auto_fix(error_sig)
    
    async def _trigger_auto_fix(self, error_signature: str):
        """Trigger an automatic fix for accumulated errors."""
        if not self._code_service:
            logger.warning("Cannot trigger fix: CodeModificationService not available")
            return
        
        # Find the original error details
        original_issue = None
        for issue in self.detected_issues:
            if self._get_error_signature(issue) == error_signature:
                original_issue = issue
                break
        
        if not original_issue:
            logger.warning(f"Cannot find original issue for signature: {error_signature}")
            return
        
        logger.info(f"Auto-triggering fix for recurring error: {error_signature}")
        
        try:
            result = await self._code_service.request_code_change(
                requester_id="self_healing_monitor",
                change_type="fix_bug",
                description=f"Auto-fix for recurring error: {original_issue.get('message', 'Unknown error')}",
                target_files=original_issue.get("affected_files"),
                priority=8,  # High priority for auto-detected issues
                context={
                    "error_signature": error_signature,
                    "occurrence_count": self.error_counts.get(error_signature, 0),
                    "original_issue": original_issue,
                    "auto_triggered": True,
                },
            )
            
            if result.get("change_id"):
                self.fix_requests_sent[error_signature] = result["change_id"]
                self.fixes_triggered += 1
                logger.info(f"Auto-fix request submitted: {result['change_id']}")
            
        except Exception as e:
            logger.error(f"Failed to trigger auto-fix: {e}")
    
    def _get_error_signature(self, issue: Dict[str, Any]) -> str:
        """Generate a signature for an error to track duplicates."""
        message = issue.get("message", "")[:100]
        issue_type = issue.get("type", "unknown")
        source = issue.get("source", "unknown")
        return f"{issue_type}:{source}:{hash(message)}"
    
    # ==================== ISSUE HANDLERS ====================
    
    async def handle_test_failure(
        self,
        test_name: str,
        error: str,
        file_path: Optional[str] = None,
        stack_trace: Optional[str] = None,
    ):
        """
        Handle a test failure.
        
        Args:
            test_name: Name of the failing test
            error: Error message
            file_path: Path to the test file
            stack_trace: Optional stack trace
        """
        issue = {
            "type": IssueType.TEST_FAILURE.value,
            "severity": IssueSeverity.ERROR.value,
            "message": f"Test failed: {test_name} - {error}",
            "test_name": test_name,
            "source": "test_runner",
            "affected_files": [file_path] if file_path else None,
            "stack_trace": stack_trace,
            "detected_at": datetime.now().isoformat(),
        }
        
        await self._record_issue(issue)
        logger.warning(f"Test failure recorded: {test_name}")
    
    async def handle_agent_crash(
        self,
        agent_id: str,
        error: str,
        stack_trace: Optional[str] = None,
    ):
        """
        Handle an agent crash.
        
        Args:
            agent_id: ID of the crashed agent
            error: Error message
            stack_trace: Optional stack trace
        """
        issue = {
            "type": IssueType.AGENT_CRASH.value,
            "severity": IssueSeverity.CRITICAL.value,
            "message": f"Agent crashed: {agent_id} - {error}",
            "agent_id": agent_id,
            "source": agent_id,
            "stack_trace": stack_trace,
            "detected_at": datetime.now().isoformat(),
        }
        
        await self._record_issue(issue)
        logger.error(f"Agent crash recorded: {agent_id}")
        
        # Crashes are critical - trigger fix immediately
        if self._code_service:
            await self._trigger_immediate_fix(issue)
    
    async def handle_agent_error(
        self,
        agent_id: str,
        error: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        Handle an agent error (non-fatal).
        
        Args:
            agent_id: ID of the agent
            error: Error message
            context: Additional context
        """
        issue = {
            "type": IssueType.AGENT_ERROR.value,
            "severity": IssueSeverity.WARNING.value,
            "message": f"Agent error: {agent_id} - {error}",
            "agent_id": agent_id,
            "source": agent_id,
            "context": context,
            "detected_at": datetime.now().isoformat(),
        }
        
        await self._record_issue(issue)
    
    async def handle_api_failure(
        self,
        endpoint: str,
        status_code: int,
        error: str,
    ):
        """
        Handle an API endpoint failure.
        
        Args:
            endpoint: The failing endpoint
            status_code: HTTP status code
            error: Error message
        """
        issue = {
            "type": IssueType.API_FAILURE.value,
            "severity": IssueSeverity.ERROR.value if status_code >= 500 else IssueSeverity.WARNING.value,
            "message": f"API failure: {endpoint} returned {status_code} - {error}",
            "endpoint": endpoint,
            "status_code": status_code,
            "source": "api_monitor",
            "detected_at": datetime.now().isoformat(),
        }
        
        await self._record_issue(issue)
        logger.warning(f"API failure recorded: {endpoint} ({status_code})")
    
    async def handle_security_vulnerability(
        self,
        vulnerability: Dict[str, Any],
    ):
        """
        Handle a detected security vulnerability.
        
        Args:
            vulnerability: Vulnerability details from SecurityCodeReviewer
        """
        issue = {
            "type": IssueType.SECURITY_VULNERABILITY.value,
            "severity": IssueSeverity.CRITICAL.value,
            "message": f"Security vulnerability: {vulnerability.get('message', 'Unknown')}",
            "vulnerability": vulnerability,
            "source": "security_scanner",
            "affected_files": [vulnerability.get("file")] if vulnerability.get("file") else None,
            "detected_at": datetime.now().isoformat(),
        }
        
        await self._record_issue(issue)
        logger.error(f"Security vulnerability recorded: {vulnerability.get('type')}")
        
        # Security issues are critical - trigger fix immediately
        if self._code_service:
            await self._trigger_immediate_fix(issue)
    
    async def handle_health_check_failure(
        self,
        component: str,
        error: str,
    ):
        """
        Handle a health check failure.
        
        Args:
            component: The failing component
            error: Error message
        """
        issue = {
            "type": IssueType.HEALTH_CHECK_FAILURE.value,
            "severity": IssueSeverity.WARNING.value,
            "message": f"Health check failed: {component} - {error}",
            "component": component,
            "source": "health_monitor",
            "detected_at": datetime.now().isoformat(),
        }
        
        await self._record_issue(issue)
    
    async def _record_issue(self, issue: Dict[str, Any]):
        """Record an issue and update tracking."""
        self.detected_issues.append(issue)
        self.issues_detected += 1
        
        # Limit stored issues
        if len(self.detected_issues) > 1000:
            self.detected_issues = self.detected_issues[-500:]
        
        # Update error counts
        signature = self._get_error_signature(issue)
        self.error_counts[signature] = self.error_counts.get(signature, 0) + 1
    
    async def _trigger_immediate_fix(self, issue: Dict[str, Any]):
        """Trigger an immediate fix for critical issues."""
        if not self._code_service:
            return
        
        try:
            result = await self._code_service.request_code_change(
                requester_id="self_healing_monitor",
                change_type="fix_security" if issue["type"] == IssueType.SECURITY_VULNERABILITY.value else "fix_bug",
                description=f"Immediate fix required: {issue['message']}",
                target_files=issue.get("affected_files"),
                priority=10,  # Maximum priority
                context={
                    "issue": issue,
                    "immediate": True,
                    "severity": issue.get("severity"),
                },
            )
            
            if result.get("change_id"):
                signature = self._get_error_signature(issue)
                self.fix_requests_sent[signature] = result["change_id"]
                self.fixes_triggered += 1
                logger.info(f"Immediate fix request submitted: {result['change_id']}")
                
        except Exception as e:
            logger.error(f"Failed to trigger immediate fix: {e}")
    
    def add_custom_check(self, check_fn: Callable):
        """Add a custom health check function."""
        self._custom_checks.append(check_fn)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        return {
            "is_running": self.is_running,
            "issues_detected": self.issues_detected,
            "fixes_triggered": self.fixes_triggered,
            "fixes_successful": self.fixes_successful,
            "pending_fixes": len(self.fix_requests_sent),
            "unique_errors": len(self.error_counts),
            "last_check": self.last_check.isoformat() if self.last_check else None,
        }
    
    def get_recent_issues(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent issues."""
        return self.detected_issues[-limit:]
    
    def get_issues_by_type(self, issue_type: str) -> List[Dict[str, Any]]:
        """Get issues filtered by type."""
        return [i for i in self.detected_issues if i.get("type") == issue_type]
    
    def clear_error_count(self, error_signature: str):
        """Clear the error count for a signature (e.g., after fix confirmed)."""
        if error_signature in self.error_counts:
            del self.error_counts[error_signature]
        if error_signature in self.fix_requests_sent:
            del self.fix_requests_sent[error_signature]


# Singleton instance
_monitor_instance: Optional[SelfHealingMonitor] = None


async def get_self_healing_monitor() -> SelfHealingMonitor:
    """Get the global SelfHealingMonitor instance (initialized with CodeModificationService)."""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = SelfHealingMonitor()
        await _monitor_instance.initialize()
    return _monitor_instance


__all__ = [
    "SelfHealingMonitor",
    "IssueType",
    "IssueSeverity",
    "get_self_healing_monitor",
]
