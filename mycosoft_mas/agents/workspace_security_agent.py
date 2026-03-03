"""
MYCA Workspace Security Agent — Monitors VM 191 for unauthorized access.

Security features:
  - SSH login monitoring (detects non-MYCA logins)
  - Token isolation verification (MYCA's tokens are unique, not shared)
  - Git identity enforcement (commits as myca@mycosoft.org)
  - Audit logging of all security events
  - Alert escalation to Morgan for anomalies

Runs on: 192.168.0.191 (MYCA VM)
Created: March 3, 2026
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from mycosoft_mas.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class WorkspaceSecurityAgent(BaseAgent):
    """Security monitoring for MYCA's workspace VM."""

    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        super().__init__(agent_id=agent_id, name=name, config=config)
        self.capabilities = [
            "ssh_monitoring",
            "token_audit",
            "git_identity_enforcement",
            "intrusion_detection",
            "security_alerts",
        ]
        self._security_events: List[Dict] = []
        self._known_users = {"mycosoft"}  # Only MYCA's service account
        self._alert_count = 0

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        task_type = task.get("type", "")
        handlers = {
            "check_ssh_logins": self._handle_check_ssh,
            "audit_tokens": self._handle_audit_tokens,
            "verify_git_identity": self._handle_verify_git,
            "security_status": self._handle_security_status,
            "check_all": self._handle_check_all,
        }
        handler = handlers.get(task_type)
        if not handler:
            return {
                "status": "error",
                "error": f"Unknown security task: {task_type}",
                "available": list(handlers.keys()),
            }
        return await handler(task)

    # ------------------------------------------------------------------
    # SSH Login Monitoring
    # ------------------------------------------------------------------

    async def _handle_check_ssh(self, task: Dict) -> Dict:
        """
        Check for SSH logins on VM 191.
        Reads /var/log/auth.log for login events.
        Alerts on any login that isn't the mycosoft service account.
        """
        alerts = []

        # Read auth log entries (last 100 lines)
        auth_log = self._read_auth_log()

        for entry in auth_log:
            if "Accepted" in entry:
                # Parse username from: "Accepted password for mycosoft from ..."
                parts = entry.split()
                try:
                    user_idx = parts.index("for") + 1
                    username = parts[user_idx]
                    ip_idx = parts.index("from") + 1
                    source_ip = parts[ip_idx]

                    if username not in self._known_users:
                        alert = {
                            "type": "unauthorized_ssh_login",
                            "username": username,
                            "source_ip": source_ip,
                            "raw": entry.strip(),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "severity": "high",
                        }
                        alerts.append(alert)
                        self._security_events.append(alert)
                        self._alert_count += 1
                except (ValueError, IndexError):
                    pass

        if alerts:
            await self._escalate_alert(
                f"SECURITY: {len(alerts)} unauthorized SSH login(s) detected on VM 191",
                alerts,
            )

        return {
            "status": "success",
            "alerts": alerts,
            "total_entries_checked": len(auth_log),
            "unauthorized_logins": len(alerts),
        }

    # ------------------------------------------------------------------
    # Token Audit
    # ------------------------------------------------------------------

    async def _handle_audit_tokens(self, task: Dict) -> Dict:
        """
        Verify that MYCA's tokens are unique and not shared with other services.
        Check environment variables and credential files.
        """
        issues = []

        # Check that critical env vars are set and unique
        critical_tokens = [
            "DISCORD_BOT_TOKEN",
            "SLACK_BOT_TOKEN",
            "ASANA_PAT",
            "GOOGLE_SERVICE_ACCOUNT_KEY",
        ]

        for token_name in critical_tokens:
            value = os.getenv(token_name, "")
            if not value:
                issues.append({
                    "type": "missing_token",
                    "token": token_name,
                    "severity": "medium",
                })
            elif len(value) < 20:
                issues.append({
                    "type": "suspicious_token_length",
                    "token": token_name,
                    "length": len(value),
                    "severity": "medium",
                })

        # Check credential files
        cred_dir = "/opt/myca/credentials"
        if os.path.isdir(cred_dir):
            for root, dirs, files in os.walk(cred_dir):
                for f in files:
                    path = os.path.join(root, f)
                    try:
                        stat = os.stat(path)
                        # Check permissions — should be 600 (owner-only)
                        mode = oct(stat.st_mode)[-3:]
                        if mode != "600":
                            issues.append({
                                "type": "insecure_permissions",
                                "file": path,
                                "mode": mode,
                                "expected": "600",
                                "severity": "high",
                            })
                    except Exception:
                        pass

        return {
            "status": "success",
            "issues": issues,
            "tokens_checked": len(critical_tokens),
            "credential_dir_exists": os.path.isdir(cred_dir),
        }

    # ------------------------------------------------------------------
    # Git Identity
    # ------------------------------------------------------------------

    async def _handle_verify_git(self, task: Dict) -> Dict:
        """
        Verify that git is configured with MYCA's identity.
        Expected: MYCA <myca@mycosoft.org>
        """
        import subprocess

        issues = []
        git_config = {}

        try:
            name = subprocess.check_output(
                ["git", "config", "--global", "user.name"],
                text=True, timeout=5,
            ).strip()
            git_config["user.name"] = name
            if name != "MYCA":
                issues.append({
                    "type": "wrong_git_name",
                    "current": name,
                    "expected": "MYCA",
                })
        except Exception:
            issues.append({"type": "git_name_not_set"})

        try:
            email = subprocess.check_output(
                ["git", "config", "--global", "user.email"],
                text=True, timeout=5,
            ).strip()
            git_config["user.email"] = email
            if email != "myca@mycosoft.org":
                issues.append({
                    "type": "wrong_git_email",
                    "current": email,
                    "expected": "myca@mycosoft.org",
                })
        except Exception:
            issues.append({"type": "git_email_not_set"})

        return {
            "status": "success",
            "git_config": git_config,
            "issues": issues,
            "identity_correct": len(issues) == 0,
        }

    # ------------------------------------------------------------------
    # Security Status
    # ------------------------------------------------------------------

    async def _handle_security_status(self, task: Dict) -> Dict:
        """Return overall security status."""
        return {
            "status": "success",
            "security": {
                "total_alerts": self._alert_count,
                "recent_events": self._security_events[-20:],
                "known_users": list(self._known_users),
                "vm": "192.168.0.191",
            },
        }

    # ------------------------------------------------------------------
    # Check All
    # ------------------------------------------------------------------

    async def _handle_check_all(self, task: Dict) -> Dict:
        """Run all security checks."""
        ssh_result = await self._handle_check_ssh(task)
        token_result = await self._handle_audit_tokens(task)
        git_result = await self._handle_verify_git(task)

        total_issues = (
            len(ssh_result.get("alerts", []))
            + len(token_result.get("issues", []))
            + len(git_result.get("issues", []))
        )

        return {
            "status": "success",
            "overall": "clean" if total_issues == 0 else f"{total_issues} issues found",
            "ssh": ssh_result,
            "tokens": token_result,
            "git_identity": git_result,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_auth_log(self) -> List[str]:
        """Read recent auth.log entries."""
        log_path = "/var/log/auth.log"
        if not os.path.exists(log_path):
            # Try journalctl as fallback
            import subprocess
            try:
                output = subprocess.check_output(
                    ["journalctl", "-u", "ssh", "--no-pager", "-n", "100"],
                    text=True, timeout=5,
                )
                return output.strip().split("\n")
            except Exception:
                return []

        try:
            with open(log_path) as f:
                lines = f.readlines()
            return lines[-100:]
        except PermissionError:
            logger.warning("Cannot read %s — need root or adm group", log_path)
            return []

    async def _escalate_alert(self, message: str, details: List[Dict]):
        """Send security alert to Morgan."""
        try:
            # Log to memory
            await self.remember(
                key=f"security_alert_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                value={
                    "message": message,
                    "details": details[:5],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        except Exception as e:
            logger.debug("Failed to log security alert: %s", e)

        # Try Discord webhook
        webhook_url = os.getenv("DISCORD_MYCA_WEBHOOK", "")
        if webhook_url:
            import httpx
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    await client.post(
                        webhook_url,
                        json={"content": f"**SECURITY ALERT**\n{message}"},
                    )
            except Exception:
                pass
