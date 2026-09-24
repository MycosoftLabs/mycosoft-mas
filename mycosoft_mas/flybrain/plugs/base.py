"""FlyBrain plug protocol (spec §2): the adapter between the runtime and one
Mycosoft system.

A plug has three duties per tick:

* ``observe(ctx)`` — collect what its system sees **in-process** (device
  telemetry, a map slice, an NLM probe, camera detections) and return them
  as :class:`Observation` objects for the encoders. Nothing is invented: a
  source that is unreachable produces a note, not a payload.
* ``navigate(ctx, action, detections)`` — plugs that navigate (``navigates``
  is True) turn the decoded :class:`MotorAction` into a :class:`NavPath`.
* ``act(ctx, action, nav, detections)`` — hand the decoded action to the
  system. Every plug in this module is advisory except ``droid``, whose
  actuation is triple-gated (spec §11.3); all of them return a plain dict
  that the runtime stores in ``TickResult.plug_result``.

Plugs never make HTTP calls back into MAS (spec §11.6). Heavy or optional
imports live inside the methods that need them so this module is safe to
import under ``MAS_LIGHT_IMPORT=1``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from mycosoft_mas.flybrain.config import FlyBrainSettings
from mycosoft_mas.flybrain.schemas import (
    ORIGIN_SIMULATED,
    BrainState,
    DetectionFrame,
    MotorAction,
    NavPath,
    Observation,
    SessionConfig,
)


@dataclass
class PlugContext:
    """Everything a plug may need for one ``observe``/``act`` call.

    ``get_detector`` returns the process-wide :class:`FlyBrainDetector`
    (it never raises; the detector itself reports unavailability).
    ``engine_snapshot`` is ``FlyBrainEngine.snapshot()`` of the session
    engine, ``brain`` the :class:`BrainState` decoded this tick (``None``
    during ``observe``), ``encoded_rates_hz`` the drive applied this tick.
    """

    session_id: str
    config: SessionConfig
    settings: FlyBrainSettings
    atlas: Any  # mycosoft_mas.flybrain.atlas.Atlas
    tick: int = 0
    t_ms: float = 0.0
    engine_snapshot: Dict[str, Any] = field(default_factory=dict)
    get_detector: Callable[[], Any] = lambda: None
    brain: Optional[BrainState] = None
    encoded_rates_hz: Dict[str, float] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)

    @property
    def plug_config(self) -> Dict[str, Any]:
        cfg = self.config.plug_config
        return cfg if isinstance(cfg, dict) else {}

    @property
    def dry_run(self) -> bool:
        return bool(self.config.dry_run)

    @property
    def device_id(self) -> Optional[str]:
        return self.config.device_id

    def note(self, text: str) -> None:
        if text:
            self.notes.append(text)


class FlyBrainPlug:
    """Base plug: API-supplied observations only, advisory action, no actuation."""

    name: str = "standalone"
    navigates: bool = False
    actuates: bool = False

    def __init__(
        self, config: Optional[SessionConfig] = None, settings: Optional[FlyBrainSettings] = None
    ) -> None:
        self.config: SessionConfig = config or SessionConfig(plug=self.name)  # type: ignore[arg-type]
        self.settings = settings
        self.last_observe_notes: List[str] = []
        self.last_result: Dict[str, Any] = {}
        self.closed = False

    # -- description --------------------------------------------------------

    def describe(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "navigates": self.navigates,
            "actuates": self.actuates,
            "dry_run": bool(self.config.dry_run),
            "origin": ORIGIN_SIMULATED,
            "observe": "API-supplied observations only",
            "act": "returns the decoded action; no actuation",
        }

    # -- per-tick hooks -----------------------------------------------------

    async def observe(self, ctx: PlugContext) -> List[Observation]:  # noqa: ARG002
        self.last_observe_notes = []
        return []

    async def navigate(
        self, ctx: PlugContext, action: MotorAction, detections: Optional[DetectionFrame]
    ) -> Optional[NavPath]:  # noqa: ARG002
        return None

    async def act(
        self,
        ctx: PlugContext,
        action: MotorAction,
        nav: Optional[NavPath],
        detections: Optional[DetectionFrame],
    ) -> Dict[str, Any]:
        result = {
            "mode": self.name,
            "origin": ORIGIN_SIMULATED,
            "actuated": False,
            "dry_run": ctx.dry_run,
            "action_kind": action.kind,
            "heading_delta_deg": action.heading_delta_deg,
            "throttle_pct": action.throttle_pct,
            "nav_feasible": bool(nav.feasible) if nav is not None else None,
            "n_detections": len(detections.detections) if detections is not None else None,
            "note": "standalone plug: action returned to the caller; nothing actuated",
        }
        self.last_result = result
        return result

    async def close(self) -> None:
        self.closed = True


class StandalonePlug(FlyBrainPlug):
    """Spec §2 ``standalone``: observations come only from the API."""

    name = "standalone"


__all__ = ["FlyBrainPlug", "PlugContext", "StandalonePlug"]
