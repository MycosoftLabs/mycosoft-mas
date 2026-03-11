"""
Voice v9 persona schema - March 2, 2026.

PersonaState for persona lock and identity consistency.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class PersonaState(BaseModel):
    """MYCA persona state for voice output validation."""
    session_id: str
    persona_locked: bool = True
    rewrite_count: int = 0  # Times text was rewritten for persona
    last_rewrite_reason: Optional[str] = None
    drift_detected: bool = False
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)
