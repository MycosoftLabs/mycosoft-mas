"""FlyBrain plug registry (spec §2): one adapter class per Mycosoft system."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type

from mycosoft_mas.flybrain.plugs.base import FlyBrainPlug, PlugContext, StandalonePlug
from mycosoft_mas.flybrain.plugs.droid import DroidPlug
from mycosoft_mas.flybrain.plugs.earthsim import EarthSimPlug
from mycosoft_mas.flybrain.plugs.itdx import ITDXPlug, itdx_channel_rows
from mycosoft_mas.flybrain.plugs.nlm import NLMPlug, build_envelope
from mycosoft_mas.flybrain.schemas import SessionConfig

PLUG_REGISTRY: Dict[str, Type[FlyBrainPlug]] = {
    "standalone": StandalonePlug,
    "droid": DroidPlug,
    "earthsim": EarthSimPlug,
    "nlm": NLMPlug,
    "itdx": ITDXPlug,
}


class UnknownPlug(ValueError):
    """Requested plug name is not registered."""


def plug_names() -> List[str]:
    return list(PLUG_REGISTRY.keys())


def get_plug(
    name: str, config: Optional[SessionConfig] = None, settings: Any = None
) -> FlyBrainPlug:
    """Instantiate the plug ``name`` for a session ``config``."""
    key = str(name or "standalone").strip().lower()
    cls = PLUG_REGISTRY.get(key)
    if cls is None:
        raise UnknownPlug(f"unknown plug {name!r}; known: {', '.join(PLUG_REGISTRY)}")
    if config is None:
        config = SessionConfig(plug=key)  # type: ignore[arg-type]
    return cls(config, settings)


__all__ = [
    "DroidPlug",
    "EarthSimPlug",
    "FlyBrainPlug",
    "ITDXPlug",
    "NLMPlug",
    "PLUG_REGISTRY",
    "PlugContext",
    "StandalonePlug",
    "UnknownPlug",
    "build_envelope",
    "get_plug",
    "itdx_channel_rows",
    "plug_names",
]
