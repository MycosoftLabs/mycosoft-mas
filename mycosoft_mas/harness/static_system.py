"""Canonical static answers — YAML/JSON driven, no code deploy for new rows."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)


class StaticSystem:
    """Lookup table for policies, definitions, device protocols."""

    def __init__(self, path: str | None = None) -> None:
        self._path = path
        self._entries: dict[str, str] = {}
        self.reload()

    def reload(self) -> None:
        self._entries.clear()
        p = self._path
        if not p or not os.path.isfile(p):
            logger.info("static system file missing: %s", p)
            return
        raw = Path(p).read_text(encoding="utf-8")
        data: Any
        if p.endswith(".json"):
            data = json.loads(raw)
        else:
            data = yaml.safe_load(raw)
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, str):
                    self._entries[k.strip().lower()] = v
                elif isinstance(v, dict) and "answer" in v:
                    self._entries[k.strip().lower()] = str(v["answer"])

    def lookup(self, query: str) -> Optional[str]:
        if not query.strip():
            return None
        key = query.strip().lower()
        if key in self._entries:
            return self._entries[key]
        for prefix, ans in self._entries.items():
            if key.startswith(prefix) or prefix in key:
                return ans
        return None
