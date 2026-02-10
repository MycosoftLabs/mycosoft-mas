"""
SecurityCodeReviewer - Pre-Execution Security Gate for Self-Healing MAS
Created: February 9, 2026

Reviews ALL code changes before execution:
- Scans for hardcoded secrets (API keys, passwords)
- Checks for SQL injection patterns
- Validates no protected files are modified
- Checks for dangerous patterns (rm -rf, DROP TABLE, etc.)
- Returns approve/block decision with reason
"""

import re
import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Risk level for code changes."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityCodeReviewer:
    """
    Reviews all code changes before execution for security issues.
    
    This is the security gate that ALL code modifications must pass through
    before being executed by CodingAgent or any other code modification system.
    """
    
    # Protected files that should NEVER be modified by automation
    PROTECTED_FILES: Set[str] = {
        "mycosoft_mas/core/orchestrator.py",
        "mycosoft_mas/core/orchestrator_service.py",
        "mycosoft_mas/safety/guardian_agent.py",
        "mycosoft_mas/safety/sandboxing.py",
        "mycosoft_mas/security/code_reviewer.py",  # This file!
        "mycosoft_mas/security/security_integration.py",
        ".env",
        ".env.local",
        ".env.production",
        "secrets.json",
        "credentials.json",
    }
    
    # Protected directories - require elevated approval
    PROTECTED_DIRS: Set[str] = {
        "mycosoft_mas/security/",
        "mycosoft_mas/safety/",
        "mycosoft_mas/core/",
        ".claude/",
        ".cursor/",
    }
    
    # Patterns that indicate secrets in code
    SECRET_PATTERNS = [
        (r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\'][^"\']{10,}["\']', "API key detected"),
        (r'(?i)(secret|password|passwd|pwd)\s*[=:]\s*["\'][^"\']+["\']', "Secret/password detected"),
        (r'sk-[a-zA-Z0-9]{20,}', "Anthropic API key detected"),
        (r'sk-proj-[a-zA-Z0-9]{20,}', "OpenAI API key detected"),
        (r'ghp_[a-zA-Z0-9]{36}', "GitHub token detected"),
        (r'xoxb-[0-9]{10,}-[0-9]{10,}-[a-zA-Z0-9]{24}', "Slack token detected"),
        (r'-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----', "Private key detected"),
        (r'(?i)bearer\s+[a-zA-Z0-9\-_]{20,}', "Bearer token detected"),
    ]
    
    # Dangerous patterns in code
    DANGEROUS_PATTERNS = [
        (r'rm\s+-rf\s+[/\*]', "Dangerous rm -rf command"),
        (r'DROP\s+(TABLE|DATABASE)', "DROP TABLE/DATABASE detected"),
        (r'DELETE\s+FROM\s+\w+\s*(;|$)', "Unfiltered DELETE FROM"),
        (r'TRUNCATE\s+TABLE', "TRUNCATE TABLE detected"),
        (r'exec\s*\(', "Dynamic exec() call"),
        (r'eval\s*\(', "Dynamic eval() call"),
        (r'subprocess\.call\s*\([^)]*shell\s*=\s*True', "Shell injection risk"),
        (r'os\.system\s*\(', "os.system() call - prefer subprocess"),
        (r'__import__\s*\(', "Dynamic __import__() call"),
        (r'pickle\.loads?\s*\(', "Pickle deserialization risk"),
        (r'yaml\.load\s*\([^)]*\)', "Unsafe YAML load (use safe_load)"),
    ]
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        (r'f["\'].*\{.*\}.*(?:SELECT|INSERT|UPDATE|DELETE|DROP)', "SQL injection via f-string"),
        (r'%\s*\(.*\).*(?:SELECT|INSERT|UPDATE|DELETE|DROP)', "SQL injection via % formatting"),
        (r'\.format\s*\(.*\).*(?:SELECT|INSERT|UPDATE|DELETE|DROP)', "SQL injection via .format()"),
        (r'\+\s*["\'].*(?:SELECT|INSERT|UPDATE|DELETE|DROP)', "SQL injection via concatenation"),
    ]
    
    def __init__(self):
        self.review_history: List[Dict[str, Any]] = []
        self.blocked_count = 0
        self.approved_count = 0
        self.last_review: Optional[datetime] = None
        
    async def review_code_change(
        self,
        change_request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Review a code change request before execution.
        
        Args:
            change_request: Dict containing:
                - requester_id: Who requested the change
                - change_type: Type of change (fix_bug, create_agent, etc.)
                - description: What the change does
                - target_files: List of files to modify
                - code_content: Optional - actual code to be written
                
        Returns:
            Dict with:
                - approved: bool
                - reason: str
                - risk_level: RiskLevel
                - issues: List of issues found
        """
        requester_id = change_request.get("requester_id", "unknown")
        change_type = change_request.get("change_type", "unknown")
        description = change_request.get("description", "")
        target_files = change_request.get("target_files", [])
        code_content = change_request.get("code_content") or ""
        
        logger.info(f"Reviewing code change: {change_type} from {requester_id}")
        
        issues: List[Dict[str, Any]] = []
        risk_level = RiskLevel.NONE
        
        # Check 1: Protected files
        protected_issues = self._check_protected_files(target_files)
        if protected_issues:
            issues.extend(protected_issues)
            risk_level = RiskLevel.CRITICAL
        
        # Check 2: Protected directories
        dir_issues = self._check_protected_directories(target_files)
        if dir_issues:
            issues.extend(dir_issues)
            if risk_level.value < RiskLevel.HIGH.value:
                risk_level = RiskLevel.HIGH
        
        # Check 3: Secret patterns in description or code
        secret_issues = self._scan_for_secrets(description + " " + code_content)
        if secret_issues:
            issues.extend(secret_issues)
            risk_level = RiskLevel.CRITICAL
        
        # Check 4: Dangerous patterns
        danger_issues = self._scan_for_dangerous_patterns(description + " " + code_content)
        if danger_issues:
            issues.extend(danger_issues)
            if risk_level.value < RiskLevel.HIGH.value:
                risk_level = RiskLevel.HIGH
        
        # Check 5: SQL injection patterns
        sql_issues = self._scan_for_sql_injection(code_content)
        if sql_issues:
            issues.extend(sql_issues)
            if risk_level.value < RiskLevel.HIGH.value:
                risk_level = RiskLevel.HIGH
        
        # Check 6: Validate change type is allowed
        type_issues = self._validate_change_type(change_type, requester_id)
        if type_issues:
            issues.extend(type_issues)
        
        # Determine approval
        approved = len(issues) == 0 or all(
            issue.get("severity") in ["warning", "info"] 
            for issue in issues
        )
        
        # Log the review
        review_result = {
            "approved": approved,
            "reason": issues[0]["message"] if issues else "No issues found",
            "risk_level": risk_level.value,
            "issues": issues,
            "requester_id": requester_id,
            "change_type": change_type,
            "target_files": target_files,
            "reviewed_at": datetime.now().isoformat(),
        }
        
        self.review_history.append(review_result)
        self.last_review = datetime.now()
        
        if approved:
            self.approved_count += 1
            logger.info(f"Code change APPROVED: {change_type}")
        else:
            self.blocked_count += 1
            logger.warning(f"Code change BLOCKED: {change_type} - {review_result['reason']}")
        
        return review_result
    
    def _check_protected_files(self, target_files: List[str]) -> List[Dict[str, Any]]:
        """Check if any protected files are targeted."""
        issues = []
        for file_path in target_files:
            # Normalize path
            normalized = file_path.replace("\\", "/").lstrip("./")
            
            for protected in self.PROTECTED_FILES:
                if normalized.endswith(protected) or protected in normalized:
                    issues.append({
                        "type": "protected_file",
                        "severity": "critical",
                        "message": f"Cannot modify protected file: {file_path}",
                        "file": file_path,
                    })
        return issues
    
    def _check_protected_directories(self, target_files: List[str]) -> List[Dict[str, Any]]:
        """Check if any protected directories are targeted."""
        issues = []
        for file_path in target_files:
            normalized = file_path.replace("\\", "/").lstrip("./")
            
            for protected_dir in self.PROTECTED_DIRS:
                if normalized.startswith(protected_dir):
                    issues.append({
                        "type": "protected_directory",
                        "severity": "high",
                        "message": f"Modifying protected directory requires elevated approval: {protected_dir}",
                        "file": file_path,
                        "directory": protected_dir,
                    })
        return issues
    
    def _scan_for_secrets(self, content: str) -> List[Dict[str, Any]]:
        """Scan content for hardcoded secrets."""
        issues = []
        for pattern, message in self.SECRET_PATTERNS:
            matches = re.findall(pattern, content)
            if matches:
                issues.append({
                    "type": "secret_detected",
                    "severity": "critical",
                    "message": message,
                    "pattern": pattern,
                    "matches_count": len(matches),
                })
        return issues
    
    def _scan_for_dangerous_patterns(self, content: str) -> List[Dict[str, Any]]:
        """Scan content for dangerous patterns."""
        issues = []
        for pattern, message in self.DANGEROUS_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                issues.append({
                    "type": "dangerous_pattern",
                    "severity": "high",
                    "message": message,
                    "pattern": pattern,
                })
        return issues
    
    def _scan_for_sql_injection(self, content: str) -> List[Dict[str, Any]]:
        """Scan for SQL injection vulnerabilities."""
        issues = []
        for pattern, message in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                issues.append({
                    "type": "sql_injection",
                    "severity": "high",
                    "message": message,
                    "pattern": pattern,
                })
        return issues
    
    def _validate_change_type(
        self, 
        change_type: str, 
        requester_id: str
    ) -> List[Dict[str, Any]]:
        """Validate that the change type is allowed for the requester."""
        issues = []
        
        # High-risk change types that need special handling
        high_risk_types = {
            "modify_security": "Modifying security components requires manual approval",
            "modify_orchestrator": "Modifying orchestrator requires CEO-level approval",
            "delete_agent": "Deleting agents requires explicit confirmation",
            "modify_database_schema": "Schema changes require database engineer review",
        }
        
        if change_type in high_risk_types:
            issues.append({
                "type": "high_risk_change",
                "severity": "warning",
                "message": high_risk_types[change_type],
                "change_type": change_type,
                "requester": requester_id,
            })
        
        return issues
    
    async def scan_for_vulnerabilities(
        self,
        file_paths: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Scan files for known vulnerabilities.
        
        Args:
            file_paths: List of file paths to scan
            
        Returns:
            List of vulnerabilities found
        """
        vulnerabilities = []
        
        for file_path in file_paths:
            try:
                path = Path(file_path)
                if path.exists() and path.is_file():
                    content = path.read_text(encoding='utf-8', errors='ignore')
                    
                    # Scan for secrets
                    secrets = self._scan_for_secrets(content)
                    for s in secrets:
                        s["file"] = file_path
                        vulnerabilities.append(s)
                    
                    # Scan for dangerous patterns
                    dangers = self._scan_for_dangerous_patterns(content)
                    for d in dangers:
                        d["file"] = file_path
                        vulnerabilities.append(d)
                    
                    # Scan for SQL injection
                    sqli = self._scan_for_sql_injection(content)
                    for sq in sqli:
                        sq["file"] = file_path
                        vulnerabilities.append(sq)
                        
            except Exception as e:
                logger.error(f"Error scanning {file_path}: {e}")
        
        return vulnerabilities
    
    async def check_protected_files(self, target_files: List[str]) -> bool:
        """
        Check if any target files are protected.
        
        Returns:
            True if any protected files are targeted
        """
        issues = self._check_protected_files(target_files)
        return len(issues) > 0
    
    def get_review_stats(self) -> Dict[str, Any]:
        """Get statistics about code reviews."""
        return {
            "total_reviews": len(self.review_history),
            "approved_count": self.approved_count,
            "blocked_count": self.blocked_count,
            "approval_rate": self.approved_count / max(1, len(self.review_history)),
            "last_review": self.last_review.isoformat() if self.last_review else None,
        }
    
    def get_recent_blocks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent blocked code changes."""
        blocked = [r for r in self.review_history if not r.get("approved")]
        return blocked[-limit:]


# Singleton instance
_reviewer_instance: Optional[SecurityCodeReviewer] = None


def get_security_reviewer() -> SecurityCodeReviewer:
    """Get the global SecurityCodeReviewer instance."""
    global _reviewer_instance
    if _reviewer_instance is None:
        _reviewer_instance = SecurityCodeReviewer()
    return _reviewer_instance


__all__ = [
    "SecurityCodeReviewer",
    "RiskLevel",
    "get_security_reviewer",
]
