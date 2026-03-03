"""
Platform Access Control for MYCA

Verifies sender identity and permissions across all communication
platforms (Discord, Slack, Email, WhatsApp, Signal).
"""

import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

AUTHORIZED_DOMAIN = "mycosoft.org"

LEADERSHIP: Dict[str, str] = {
    "morgan@mycosoft.org": "CEO",
    "rj@mycosoft.org": "COO",
    "garret@mycosoft.org": "CTO",
}

TEAM: Set[str] = set()

LEADERSHIP_PERMISSIONS = frozenset({
    "read", "write", "delete", "deploy", "modify", "bulk_update",
    "restart", "admin", "approve", "code_execute", "agent_invoke",
})

TEAM_PERMISSIONS = frozenset({
    "read", "write", "request",
})


@dataclass
class AccessLevel:
    authorized: bool
    role: str = "none"
    email: str = ""
    permissions: frozenset = frozenset()


class PlatformAccessControl:
    """Verify sender identity and enforce permissions across platforms."""

    def __init__(self):
        self._discord_whitelist: Dict[str, str] = {}
        self._phone_whitelist: Dict[str, str] = {}
        self._load_whitelists()

    def _load_whitelists(self):
        discord_wl = os.getenv("MYCA_DISCORD_WHITELIST", "")
        for entry in discord_wl.split(","):
            entry = entry.strip()
            if ":" in entry:
                uid, email = entry.split(":", 1)
                self._discord_whitelist[uid.strip()] = email.strip()

        phone_wl = os.getenv("MYCA_PHONE_WHITELIST", "")
        for entry in phone_wl.split(","):
            entry = entry.strip()
            if ":" in entry:
                phone, email = entry.split(":", 1)
                self._phone_whitelist[phone.strip()] = email.strip()

    async def verify_sender(
        self, platform: str, sender_id: str,
    ) -> AccessLevel:
        email = self._resolve_email(platform, sender_id)
        if not email:
            return AccessLevel(authorized=False, role="unknown")

        if not email.endswith(f"@{AUTHORIZED_DOMAIN}"):
            return AccessLevel(authorized=False, role="external", email=email)

        if email in LEADERSHIP:
            return AccessLevel(
                authorized=True,
                role=LEADERSHIP[email],
                email=email,
                permissions=LEADERSHIP_PERMISSIONS,
            )
        if email in TEAM:
            return AccessLevel(
                authorized=True,
                role="team",
                email=email,
                permissions=TEAM_PERMISSIONS,
            )

        return AccessLevel(
            authorized=True, role="member", email=email,
            permissions=frozenset({"read"}),
        )

    def _resolve_email(self, platform: str, sender_id: str) -> Optional[str]:
        if platform == "email":
            return sender_id
        if platform == "slack":
            if "@" in sender_id:
                return sender_id
            return None
        if platform == "discord":
            return self._discord_whitelist.get(sender_id)
        if platform in ("whatsapp", "signal"):
            return self._phone_whitelist.get(sender_id)
        return None

    async def check_permission(
        self, email: str, action: str,
    ) -> bool:
        if email in LEADERSHIP:
            return True
        if email in TEAM:
            return action in TEAM_PERMISSIONS
        return action == "read"
