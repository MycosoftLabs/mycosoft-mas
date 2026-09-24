"""ITDX / FUSARIUM demonstration plug (spec §2 ``itdx``, §11.5).

``observe()`` supplies the map slice (``plug_config.map_slice`` or the Fort
Stewart demonstration slice) as an ``itdx_slice`` observation plus any
detection frame the caller attached in ``plug_config.detections``.
``navigate()`` reuses the Earth-Sim AO planner. ``act()`` returns the four
ITDX channel rows (``pathways``, ``navigation``, ``biology``,
``information``) in the exact ``itdx_api._channel`` shape.

Honesty (spec §11.5): ``SCORED`` only for quantities computed from real
geometry this tick — path feasibility, free-cell fraction, detection and
taxon counts — and every ``note`` says what ``p`` means. Everything else
is ``NOT_SUPPLIED`` with a ``reason``.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Mapping, Optional

from mycosoft_mas.flybrain.navigation import MAX_WAYPOINTS
from mycosoft_mas.flybrain.plugs.base import FlyBrainPlug, PlugContext
from mycosoft_mas.flybrain.plugs.earthsim import (
    DEFAULT_OBSTACLE_RADIUS_M,
    PROBE_BUDGET_S,
    _num,
    default_map_slice,
    plan_across_ao,
)
from mycosoft_mas.flybrain.schemas import (
    ORIGIN_SIMULATED,
    BrainState,
    DetectionFrame,
    ITDXChannelRow,
    MotorAction,
    NavPath,
    Observation,
)

ITDX_CHANNELS_SCHEMA_VERSION = "flybrain.itdx_channels/v1"
CHANNEL_KEYS = ("pathways", "navigation", "biology", "information")
AGENT_ID = "flybrain"


def _live(brain: Optional[BrainState], extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    live: Dict[str, Any] = {"origin": ORIGIN_SIMULATED}
    if brain is not None:
        live.update({"session_id": brain.session_id, "tick": brain.step, "t_ms": brain.t_ms})
    else:
        live.update({"session_id": None, "tick": None})
    if extra:
        live.update(extra)
    return live


def itdx_channel_rows(
    map_slice: Optional[Mapping[str, Any]],
    brain: Optional[BrainState],
    action: Optional[MotorAction],
    nav: Optional[NavPath],
    detections: Optional[DetectionFrame],
) -> Dict[str, Dict[str, Any]]:
    """Four ITDX channel rows (``ITDXChannelRow.model_dump()`` dicts).

    * ``navigation`` — SCORED ``p = 1 - blocked_cells/total_cells`` only when
      ``nav.feasible``; the note says p is the free-cell fraction of the
      occupancy grid, not P(success).
    * ``pathways`` — SCORED ``p = min(1, len(waypoints)/12)`` only when feasible.
    * ``biology`` — SCORED ``p`` = fraction of detections resolved to a MINDEX
      taxon when detections exist, else NOT_SUPPLIED.
    * ``information`` — SCORED with ``sample_count`` = detection count when a
      detection frame is available, else NOT_SUPPLIED.
    """
    ao = map_slice.get("ao") if isinstance(map_slice, Mapping) else None
    place = None
    if isinstance(ao, Mapping):
        place = ao.get("name") or ao.get("place")
    extra: Dict[str, Any] = {"ao": place}
    if action is not None:
        extra["action_kind"] = action.kind
        extra["turn"] = action.turn
        extra["heading_delta_deg"] = action.heading_delta_deg

    # navigation ---------------------------------------------------------------
    if nav is not None and nav.feasible and nav.total_cells > 0:
        free = 1.0 - (nav.blocked_cells / nav.total_cells)
        free = max(0.0, min(1.0, free))
        navigation = ITDXChannelRow(
            status="SCORED",
            agent_id=AGENT_ID,
            p=free,
            note=(
                f"p = free-cell fraction of the A* occupancy grid this tick "
                f"({nav.total_cells - nav.blocked_cells}/{nav.total_cells} cells free); "
                "not P(mission success). Path feasible; FlyBrain LIF turn bias "
                f"{nav.turn_bias:+.2f}. SIMULATED."
            ),
            live=_live(
                brain,
                {
                    **extra,
                    "blocked_cells": nav.blocked_cells,
                    "total_cells": nav.total_cells,
                    "path_m": nav.cost,
                },
            ),
            capability_class="flybrain_navigation",
            sample_count=nav.total_cells,
        )
    else:
        reason = (
            "no navigation planned this tick" if nav is None else (nav.note or "path infeasible")
        )
        navigation = ITDXChannelRow(
            status="NOT_SUPPLIED",
            agent_id=AGENT_ID,
            p=None,
            note="FlyBrain did not compute a feasible path; no probability invented.",
            live=_live(brain, extra),
            reason=reason,
            capability_class="flybrain_navigation",
        )

    # pathways -----------------------------------------------------------------
    if nav is not None and nav.feasible:
        n_wp = len(nav.waypoints)
        pathways = ITDXChannelRow(
            status="SCORED",
            agent_id=AGENT_ID,
            p=min(1.0, n_wp / float(MAX_WAYPOINTS)),
            note=(
                f"p = waypoint count / {MAX_WAYPOINTS} ({n_wp} Douglas-Peucker waypoints, "
                f"{(nav.cost or 0.0):.0f} m); a path-resolution measure, not P(success). SIMULATED."
            ),
            live=_live(brain, {**extra, "n_waypoints": n_wp, "path_m": nav.cost}),
            capability_class="flybrain_pathways",
            sample_count=n_wp,
        )
    else:
        pathways = ITDXChannelRow(
            status="NOT_SUPPLIED",
            agent_id=AGENT_ID,
            p=None,
            note="No feasible path this tick; no pathway score invented.",
            live=_live(brain, extra),
            reason="no navigation planned" if nav is None else (nav.note or "path infeasible"),
            capability_class="flybrain_pathways",
        )

    # biology / information ------------------------------------------------------
    if detections is not None and detections.available:
        n_det = len(detections.detections)
        n_taxa = sum(1 for d in detections.detections if d.taxon is not None and d.taxon.matched)
        n_bio = sum(1 for d in detections.detections if d.category in ("animal", "plant", "fungus"))
        det_live = {
            **extra,
            "n_detections": n_det,
            "n_taxa_resolved": n_taxa,
            "n_biological": n_bio,
            "engine": detections.engine,
            "sahi": detections.sahi,
        }
        if n_det > 0:
            biology = ITDXChannelRow(
                status="SCORED",
                agent_id=AGENT_ID,
                p=n_taxa / n_det,
                note=(
                    f"p = fraction of detections resolved to a MINDEX taxon "
                    f"({n_taxa}/{n_det}; {n_bio} biological classes); not a presence probability."
                ),
                live=_live(brain, det_live),
                capability_class="flybrain_vision_taxon",
                sample_count=n_det,
            )
        else:
            biology = ITDXChannelRow(
                status="NOT_SUPPLIED",
                agent_id=AGENT_ID,
                p=None,
                note="Detector ran but the frame holds no detections; no biology score invented.",
                live=_live(brain, det_live),
                reason="no detections in frame",
                capability_class="flybrain_vision_taxon",
            )
        information = ITDXChannelRow(
            status="SCORED",
            agent_id=AGENT_ID,
            p=None,
            note=(
                f"sample_count = {n_det} YOLO26/SAHI detections this tick "
                f"(engine {detections.engine or 'unknown'}); counts only, no probability computed."
            ),
            live=_live(brain, det_live),
            capability_class="flybrain_vision_count",
            sample_count=n_det,
        )
    else:
        reason = (
            "no detection frame this tick"
            if detections is None
            else f"detector unavailable: {detections.note or 'no reason given'}"
        )
        biology = ITDXChannelRow(
            status="NOT_SUPPLIED",
            agent_id=AGENT_ID,
            p=None,
            note="No detections available; no biology score invented.",
            live=_live(brain, extra),
            reason=reason,
            capability_class="flybrain_vision_taxon",
        )
        information = ITDXChannelRow(
            status="NOT_SUPPLIED",
            agent_id=AGENT_ID,
            p=None,
            note="No detection frame available; no information count invented.",
            live=_live(brain, extra),
            reason=reason,
            capability_class="flybrain_vision_count",
        )

    return {
        "pathways": pathways.model_dump(),
        "navigation": navigation.model_dump(),
        "biology": biology.model_dump(),
        "information": information.model_dump(),
    }


class ITDXPlug(FlyBrainPlug):
    """FUSARIUM ITDX demonstration: map slice + detections → four channel rows."""

    name = "itdx"
    navigates = True

    def __init__(self, config=None, settings=None) -> None:
        super().__init__(config, settings)
        self.map_slice: Dict[str, Any] = {}
        self.last_nav: Optional[NavPath] = None
        self.last_channels: Dict[str, Dict[str, Any]] = {}

    def describe(self) -> Dict[str, Any]:
        base = super().describe()
        base.update(
            {
                "observe": "ITDX map slice (plug_config.map_slice or Fort Stewart demo) "
                "+ optional plug_config.detections frame",
                "act": "pathways/navigation/biology/information channel rows (itdx_api._channel shape)",
                "channels": list(CHANNEL_KEYS),
            }
        )
        return base

    def plug_map_slice(self) -> Optional[Dict[str, Any]]:
        cfg = self.config.plug_config if isinstance(self.config.plug_config, dict) else {}
        ms = cfg.get("map_slice")
        return dict(ms) if isinstance(ms, dict) else None

    async def observe(self, ctx: PlugContext) -> List[Observation]:
        notes: List[str] = []
        out: List[Observation] = []
        map_slice = self.plug_map_slice()
        if map_slice is None:
            try:
                map_slice = await asyncio.wait_for(
                    asyncio.to_thread(default_map_slice), PROBE_BUDGET_S
                )
            except Exception as exc:  # noqa: BLE001
                notes.append(f"itdx: default map slice unavailable ({type(exc).__name__}: {exc})")
        if map_slice is not None:
            self.map_slice = map_slice
            payload = {
                "ao": map_slice.get("ao") or {},
                "assets": list(map_slice.get("assets") or []),
                "devices": list(map_slice.get("devices") or []),
            }
            for key in ("focus", "heading_deg", "clock", "origin"):
                if key in map_slice:
                    payload[key] = map_slice[key]
            out.append(
                Observation(kind="itdx_slice", payload=payload, t_ms=ctx.t_ms, source="itdx")
            )
        frame = ctx.plug_config.get("detections")
        if isinstance(frame, DetectionFrame):
            frame = frame.model_dump()
        if isinstance(frame, dict):
            try:
                DetectionFrame.model_validate(frame)
                out.append(
                    Observation(kind="detections", payload=frame, t_ms=ctx.t_ms, source="itdx")
                )
            except Exception as exc:  # noqa: BLE001
                notes.append(f"itdx: plug_config.detections is not a DetectionFrame ({exc})")
        self.last_observe_notes = notes
        ctx.notes.extend(notes)
        return out

    async def navigate(
        self, ctx: PlugContext, action: MotorAction, detections: Optional[DetectionFrame]
    ) -> Optional[NavPath]:
        if not self.map_slice:
            self.last_nav = NavPath(
                feasible=False, note="no map slice observed; nothing to plan on"
            )
            return self.last_nav
        cfg = ctx.plug_config
        nav = await asyncio.to_thread(
            plan_across_ao,
            self.map_slice,
            action,
            ctx.encoded_rates_hz,
            detections,
            left_groups=ctx.atlas.input_groups("left") if ctx.atlas is not None else (),
            right_groups=ctx.atlas.input_groups("right") if ctx.atlas is not None else (),
            size_m=_num(cfg.get("grid_size_m")),
            cell_m=_num(cfg.get("cell_m")),
            obstacle_radius_m=_num(cfg.get("obstacle_radius_m")) or DEFAULT_OBSTACLE_RADIUS_M,
        )
        self.last_nav = nav
        return nav

    async def act(
        self,
        ctx: PlugContext,
        action: MotorAction,
        nav: Optional[NavPath],
        detections: Optional[DetectionFrame],
    ) -> Dict[str, Any]:
        rows = itdx_channel_rows(self.map_slice, ctx.brain, action, nav, detections)
        self.last_channels = rows
        result = {
            "mode": self.name,
            "origin": ORIGIN_SIMULATED,
            "actuated": False,
            "dry_run": ctx.dry_run,
            "schema_version": ITDX_CHANNELS_SCHEMA_VERSION,
            "channels": rows,
            "nav_feasible": bool(nav.feasible) if nav is not None else None,
            "observe_notes": list(self.last_observe_notes),
        }
        self.last_result = result
        return result


__all__ = [
    "AGENT_ID",
    "CHANNEL_KEYS",
    "ITDX_CHANNELS_SCHEMA_VERSION",
    "ITDXPlug",
    "itdx_channel_rows",
]
