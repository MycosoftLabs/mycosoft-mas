"""
Packet-first PSILO overlay for MYCA2 only (Mar 17, 2026).

Between turn_packet_builder and llm_brain: DMN attenuation hints, temporary edges,
synesthesia cross-domain notes, observer/integrator summary — injected as world_model summary deltas.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Tuple

from mycosoft_mas.schemas.experience_packet import ExperiencePacket


def _overlay_from_session_state(state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not state:
        return {
            "dmn_attenuation": 0.0,
            "active_edges": [],
            "cross_domain_ratio": 0.0,
            "synesthesia_notes": [],
            "observer_summary": "",
        }
    return {
        "dmn_attenuation": float(state.get("dmn_attenuation") or 0.0),
        "active_edges": list(state.get("overlay_edges") or state.get("active_edges") or []),
        "cross_domain_ratio": float(state.get("cross_domain_ratio") or 0.0),
        "synesthesia_notes": list(state.get("synesthesia_notes") or []),
        "observer_summary": str(state.get("observer_summary") or ""),
    }


def apply_psilo_overlay(
    ep: ExperiencePacket,
    psilo_session_state: Optional[Dict[str, Any]] = None,
) -> Tuple[ExperiencePacket, Dict[str, Any]]:
    """
    Return augmented EP (shallow copy of world summary) and overlay metrics for UI/telemetry.
    """
    ov = _overlay_from_session_state(psilo_session_state)
    metrics = {
        "dmn_dominance": max(0.0, 1.0 - ov["dmn_attenuation"]),
        "cross_domain_ratio": ov["cross_domain_ratio"],
        "edge_count": len(ov["active_edges"]),
    }

    ep2 = copy.copy(ep)
    if ep2.world_state is None:
        from mycosoft_mas.schemas.experience_packet import WorldStateRef

        ep2.world_state = WorldStateRef(summary="")
    else:
        ep2.world_state = copy.copy(ep2.world_state)

    extra_parts: List[str] = []
    if ov["dmn_attenuation"] > 0:
        extra_parts.append(
            f"[PSILO DMN attenuation]: hub pressure reduced by factor ~{ov['dmn_attenuation']:.2f}"
        )
    if ov["active_edges"]:
        extra_parts.append(
            f"[PSILO overlay edges]: {len(ov['active_edges'])} active — {ov['active_edges'][:5]}"
        )
    if ov["synesthesia_notes"]:
        extra_parts.append("[PSILO synesthesia]: " + "; ".join(str(x) for x in ov["synesthesia_notes"][:4]))
    if ov["observer_summary"]:
        extra_parts.append(f"[PSILO observer/integrator]: {ov['observer_summary'][:600]}")

    base = (ep2.world_state.summary or "").strip()
    if extra_parts:
        ep2.world_state.summary = (base + "\n\n" if base else "") + "\n".join(extra_parts)

    return ep2, metrics
