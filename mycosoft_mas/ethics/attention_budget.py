"""
Attention Budget - Stoic Attention Management

MYCA defaults to calm mode. Actively refuses to optimize for engagement.
Tracks notification frequency, enforces cool-down, flags addictive patterns.

Constraint 9: Anti-Addiction Principle.
Created: March 3, 2026
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# Addictive pattern flags
ADDICTIVE_PATTERNS = [
    "infinite scroll",
    "urgency without substance",
    "speculative outrage",
    "dopamine loop",
    "engagement metric",
]


@dataclass
class AttentionBudget:
    """
    Stoic attention management per channel/user.
    Enforces cool-down periods and flags addictive outputs.
    """

    cool_down_seconds: float = 300.0  # 5 min between notifications per channel
    max_per_hour: int = 6
    _events: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))

    def record_output(self, channel: str, timestamp: Optional[float] = None) -> None:
        """Record an output/notification for the channel."""
        ts = timestamp or time.time()
        self._events[channel].append(ts)
        # Prune old events (keep last 24h)
        cutoff = ts - 86400
        self._events[channel] = [t for t in self._events[channel] if t > cutoff]

    def can_send(self, channel: str) -> Tuple[bool, str]:
        """
        Check if we can send to this channel without exceeding budget.
        Returns (allowed, reason).
        """
        now = time.time()
        events = self._events.get(channel, [])

        # Cool-down check
        if events:
            last = max(events)
            if now - last < self.cool_down_seconds:
                return (
                    False,
                    f"Cool-down active: {self.cool_down_seconds - (now - last):.0f}s remaining",
                )

        # Per-hour check
        recent = [t for t in events if now - t < 3600]
        if len(recent) >= self.max_per_hour:
            return False, f"Max {self.max_per_hour} per hour reached for {channel}"

        return True, "ok"

    def get_status(self, channel: str) -> Dict[str, Any]:
        """Return budget status for a channel."""
        now = time.time()
        events = self._events.get(channel, [])

        last = max(events) if events else None
        cool_down_remaining = 0.0
        if last and now - last < self.cool_down_seconds:
            cool_down_remaining = self.cool_down_seconds - (now - last)

        recent_hour = [t for t in events if now - t < 3600]
        return {
            "channel": channel,
            "outputs_last_hour": len(recent_hour),
            "max_per_hour": self.max_per_hour,
            "cool_down_remaining_seconds": cool_down_remaining,
            "can_send": cool_down_remaining <= 0 and len(recent_hour) < self.max_per_hour,
        }

    def flag_addictive_patterns(self, content: str) -> List[str]:
        """Flag content that resembles addictive design patterns."""
        content_lower = content.lower()
        flagged = []
        for p in ADDICTIVE_PATTERNS:
            if p in content_lower:
                flagged.append(p)
        return flagged
