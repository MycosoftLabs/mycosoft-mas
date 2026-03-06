"""
Staff registry helpers for MYCA OS.

Loads the canonical staff directory from config/org_roles.yaml and expands
environment-variable placeholders used for channel identities.

Date: 2026-03-06
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

ENV_PATTERN = re.compile(r"\$\{([^}]+)\}")


def _expand_env_placeholders(value: Any) -> Any:
    if isinstance(value, str):
        def repl(match: re.Match[str]) -> str:
            return os.getenv(match.group(1), "")
        return ENV_PATTERN.sub(repl, value)
    if isinstance(value, dict):
        return {k: _expand_env_placeholders(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env_placeholders(v) for v in value]
    return value


def _roles_path() -> Path:
    return Path(__file__).resolve().parents[3] / "config" / "org_roles.yaml"


def load_staff_directory() -> Dict[str, Dict[str, Any]]:
    path = _roles_path()
    if not path.exists():
        return {}

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    roles = data.get("roles", {})
    staff: Dict[str, Dict[str, Any]] = {}

    for person_id, info in roles.items():
        expanded = _expand_env_placeholders(info)
        channels = expanded.get("channels", {}) or {}
        platforms = [name for name, value in channels.items() if value]
        staff[person_id] = {
            "id": person_id,
            "name": expanded.get("name", person_id.title()),
            "role": ", ".join(expanded.get("titles", [])[:2]) or person_id,
            "titles": expanded.get("titles", []),
            "scopes": expanded.get("scopes", []),
            "task_types": expanded.get("task_types", []),
            "reports_to": expanded.get("reports_to"),
            "channels": channels,
            "platforms": platforms,
            "email": channels.get("email", ""),
            "priority": "high" if person_id in {"morgan", "rj", "garret"} else "normal",
            "topics": expanded.get("scopes", []),
        }
    return staff


def resolve_person_id(
    staff_directory: Dict[str, Dict[str, Any]],
    *,
    platform: Optional[str] = None,
    sender_id: Optional[str] = None,
    email: Optional[str] = None,
    fallback_name: Optional[str] = None,
) -> Optional[str]:
    email_normalized = (email or "").strip().lower()
    sender_normalized = (sender_id or "").strip()
    fallback_normalized = (fallback_name or "").strip().lower()

    for person_id, staff in staff_directory.items():
        if email_normalized and staff.get("email", "").strip().lower() == email_normalized:
            return person_id
        if platform and sender_normalized:
            channel_value = (staff.get("channels", {}) or {}).get(platform, "")
            if channel_value and channel_value == sender_normalized:
                return person_id
        if fallback_normalized and fallback_normalized in {
            person_id.lower(),
            staff.get("name", "").strip().lower(),
        }:
            return person_id
    return None
