"""
MYCA Harness — Nemotron (via unified backend selection), PersonaPlex bridge,
policy YAML (STATIC), MINDEX unified search-in-LLM, turbo-quant placeholder,
intention brain, execution logging, and optional NLM.

The FastAPI router mounts by default on the MAS app unless ``HARNESS_API_DISABLED=1``
or legacy ``HARNESS_API_ENABLED=false``. ``POST /voice/brain/chat`` can use the harness
when ``use_harness: true`` or ``BRAIN_CHAT_USE_HARNESS=1``. See :class:`HarnessEngine`.
"""

from mycosoft_mas.harness.config import HarnessConfig
from mycosoft_mas.harness.engine import HarnessEngine
from mycosoft_mas.harness.models import HarnessPacket, HarnessResult, RouteType

__all__ = [
    "HarnessConfig",
    "HarnessEngine",
    "HarnessPacket",
    "HarnessResult",
    "RouteType",
]
