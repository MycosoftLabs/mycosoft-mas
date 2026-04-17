"""
MYCA Harness — Nemotron (via unified backend selection), PersonaPlex bridge,
policy YAML (STATIC), MINDEX unified search-in-LLM, turbo-quant placeholder,
intention brain, execution logging, and optional NLM.

Wire the FastAPI router when ``HARNESS_API_ENABLED`` is set; see :meth:`HarnessEngine`.
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
