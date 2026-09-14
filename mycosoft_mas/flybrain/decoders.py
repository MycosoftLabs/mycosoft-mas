"""FlyBrain decoders — population rates → MotorAction / class label (spec §7).

``LocomotionDecoder`` turns the mean firing rates of the atlas readout
groups (``sensorimotor.readouts`` in ``config/flybrain_atlas.yaml``) into a
``MotorAction``. ``PopulationClassifier`` is a nearest-centroid classifier
over rate vectors whose centroids are learned **only** from labelled ticks
of the current session; with no labels it returns ``None``, never a guess.

Pure Python; safe to import under ``MAS_LIGHT_IMPORT=1``.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Optional, Tuple

from mycosoft_mas.flybrain.schemas import MotorAction

LOCOMOTION_FORMULA = (
    "turn=0 if (right+left)<min_turn_hz else (right-left)/(right+left+eps); "
    "forward=clip(fwd/fwd_ref,0,1); "
    "heading_delta_deg=turn*max_turn_deg; throttle_pct=forward*100; "
    "confidence=1-exp(-spike_count_window/200); "
    "kind='locomotion' if forward>0.05 or |turn|>0.05 else 'none'"
)


def _as_float(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def _readout_groups(readouts: Any, channel: str) -> List[str]:
    mapping: Any = readouts
    if isinstance(mapping, Mapping) and "readouts" in mapping and channel not in mapping:
        mapping = mapping.get("readouts")
    if isinstance(mapping, Mapping) and "sensorimotor" in mapping and channel not in mapping:
        mapping = mapping.get("sensorimotor", {}).get("readouts")
    groups = mapping.get(channel) if isinstance(mapping, Mapping) else None
    if isinstance(groups, str):
        groups = [groups]
    if not isinstance(groups, (list, tuple)):
        return []
    return [str(g) for g in groups if isinstance(g, str) and g]


class LocomotionDecoder:
    """Rates of the forward / turn_left / turn_right readouts → ``MotorAction``.

    ``readouts`` is the ``sensorimotor.readouts`` mapping of the atlas
    (``{forward: [...], turn_left: [...], turn_right: [...], feeding: [...]}``);
    the whole ``sensorimotor`` block or the whole atlas dict is also accepted.

    ``min_turn_hz`` gates the turn ratio: when the summed left+right readout
    rate is below it (default 5 Hz — a few spikes per neuron per window) the
    turn is 0. Without the gate a single stray spike in one readout group
    (e.g. 0.3 Hz vs 0.0 Hz) would saturate ``turn`` to ±1 and emit a full
    ``max_turn_deg`` heading change whose sign is set by noise.
    """

    def __init__(
        self,
        readouts: Any,
        fwd_ref_hz: float = 50.0,
        max_turn_deg: float = 30.0,
        eps_hz: float = 1e-3,
        min_turn_hz: float = 5.0,
        activity_threshold: float = 0.05,
        confidence_spikes: float = 200.0,
    ) -> None:
        self.readouts = readouts
        self.fwd_ref_hz = float(fwd_ref_hz) if fwd_ref_hz and fwd_ref_hz > 0 else 50.0
        self.max_turn_deg = float(max_turn_deg)
        self.eps_hz = max(float(eps_hz), 1e-9)
        self.min_turn_hz = max(float(min_turn_hz), 0.0)
        self.activity_threshold = float(activity_threshold)
        self.confidence_spikes = max(float(confidence_spikes), 1e-9)
        self.forward_groups = _readout_groups(readouts, "forward")
        self.left_groups = _readout_groups(readouts, "turn_left")
        self.right_groups = _readout_groups(readouts, "turn_right")
        self.feeding_groups = _readout_groups(readouts, "feeding")

    @staticmethod
    def _mean_rate(
        rates_hz: Mapping[str, Any], groups: List[str]
    ) -> Tuple[float, List[str], List[str]]:
        """Mean rate over the groups present in ``rates_hz``; lists used and missing groups."""
        used: List[str] = []
        missing: List[str] = []
        total = 0.0
        for g in groups:
            value = _as_float(rates_hz.get(g)) if isinstance(rates_hz, Mapping) else None
            if value is None:
                missing.append(g)
                continue
            total += max(value, 0.0)
            used.append(g)
        return (total / len(used) if used else 0.0), used, missing

    def decode(self, rates_hz: Mapping[str, Any], spike_count_window: int) -> MotorAction:
        rates = rates_hz if isinstance(rates_hz, Mapping) else {}
        fwd, fwd_used, fwd_missing = self._mean_rate(rates, self.forward_groups)
        left, left_used, left_missing = self._mean_rate(rates, self.left_groups)
        right, right_used, right_missing = self._mean_rate(rates, self.right_groups)
        feeding, feeding_used, _ = self._mean_rate(rates, self.feeding_groups)

        turn_drive = right + left
        turn_gated = turn_drive < self.min_turn_hz
        turn = 0.0 if turn_gated else (right - left) / (turn_drive + self.eps_hz)
        turn = max(-1.0, min(1.0, turn))
        forward = max(0.0, min(1.0, fwd / self.fwd_ref_hz))
        heading_delta = turn * self.max_turn_deg
        throttle = forward * 100.0
        spikes = max(int(spike_count_window or 0), 0)
        confidence = 1.0 - math.exp(-spikes / self.confidence_spikes)
        confidence = max(0.0, min(1.0, confidence))
        active = forward > self.activity_threshold or abs(turn) > self.activity_threshold
        kind = "locomotion" if active else "none"

        notes: List[str] = []
        if spikes == 0:
            notes.append("brain silent in window: confidence 0")
        missing = fwd_missing + left_missing + right_missing
        if missing:
            notes.append(f"readout groups without rates: {', '.join(missing)}")
        if not (fwd_used or left_used or right_used):
            notes.append("no readout rates available; no action")
        elif turn_gated and turn_drive > 0.0:
            notes.append(
                f"turn readouts below min_turn_hz ({turn_drive:.2f} < {self.min_turn_hz:g} Hz); "
                "turn gated to 0"
            )
        if kind == "none" and not notes:
            notes.append("readouts quiet; no action")

        evidence: Dict[str, Any] = {
            "formula": "locomotion_v1",
            "formula_text": LOCOMOTION_FORMULA,
            "forward_hz": fwd,
            "left_hz": left,
            "right_hz": right,
            "feeding_hz": feeding,
            "fwd_ref_hz": self.fwd_ref_hz,
            "max_turn_deg": self.max_turn_deg,
            "eps_hz": self.eps_hz,
            "min_turn_hz": self.min_turn_hz,
            "turn_gated": turn_gated,
            "spike_count_window": spikes,
            "readouts": {
                "forward": fwd_used,
                "turn_left": left_used,
                "turn_right": right_used,
                "feeding": feeding_used,
            },
            "missing_groups": missing,
            "origin": "SIMULATED",
        }
        return MotorAction(
            kind=kind,
            forward=forward,
            turn=turn,
            heading_delta_deg=heading_delta,
            throttle_pct=throttle,
            target_bearing_deg=None,
            confidence=confidence,
            evidence=evidence,
            note="; ".join(notes),
        )


class PopulationClassifier:
    """Nearest-centroid classifier over atlas-group rate vectors.

    Centroids are running means of the labelled rate vectors seen in this
    session via ``observe(rates, label)``. ``predict`` returns ``None`` until
    at least one labelled centroid exists, and also when the query shares no
    keys with any centroid.
    """

    def __init__(self) -> None:
        self._sums: Dict[str, Dict[str, float]] = {}
        self._counts: Dict[str, int] = {}
        self._unlabelled = 0

    @staticmethod
    def _clean(rates_vector: Any) -> Dict[str, float]:
        if not isinstance(rates_vector, Mapping):
            return {}
        out: Dict[str, float] = {}
        for k, v in rates_vector.items():
            value = _as_float(v)
            if value is not None:
                out[str(k)] = value
        return out

    def observe(self, rates_vector: Any, label: Optional[str]) -> None:
        vec = self._clean(rates_vector)
        name = str(label).strip() if label is not None else ""
        if not name:
            self._unlabelled += 1
            return
        if not vec:
            return
        sums = self._sums.setdefault(name, {})
        for k, v in vec.items():
            sums[k] = sums.get(k, 0.0) + v
        self._counts[name] = self._counts.get(name, 0) + 1

    def centroids(self) -> Dict[str, Dict[str, float]]:
        return {
            label: {k: v / self._counts[label] for k, v in sums.items()}
            for label, sums in self._sums.items()
            if self._counts.get(label)
        }

    def predict(self, rates_vector: Any) -> Optional[Dict[str, Any]]:
        vec = self._clean(rates_vector)
        cents = self.centroids()
        if not cents or not vec:
            return None
        scored: List[Tuple[float, str, int]] = []
        for label, centroid in cents.items():
            shared = [k for k in vec if k in centroid]
            if not shared:
                continue
            dist = math.sqrt(sum((vec[k] - centroid[k]) ** 2 for k in shared) / len(shared))
            scored.append((dist, label, len(shared)))
        if not scored:
            return None
        scored.sort(key=lambda s: (s[0], s[1]))
        best_dist, best_label, shared_n = scored[0]
        second = scored[1][0] if len(scored) > 1 else None
        margin = (second - best_dist) if second is not None else None
        return {
            "label": best_label,
            "distance_hz": best_dist,
            "margin_hz": margin,
            "second_label": scored[1][1] if len(scored) > 1 else None,
            "shared_keys": shared_n,
            "n_centroids": len(cents),
            "n_examples": self._counts.get(best_label, 0),
            "method": "nearest_centroid_rms_hz",
            "origin": "SIMULATED",
            "note": (
                "session-learned centroids only; distance is RMS Hz over shared groups, "
                "not a probability"
            ),
        }

    def state(self) -> Dict[str, Any]:
        cents = self.centroids()
        return {
            "labels": {
                label: {"count": self._counts.get(label, 0), "centroid": centroid}
                for label, centroid in cents.items()
            },
            "n_labels": len(cents),
            "n_labelled": sum(self._counts.values()),
            "n_unlabelled": self._unlabelled,
            "ready": bool(cents),
        }


__all__ = ["LOCOMOTION_FORMULA", "LocomotionDecoder", "PopulationClassifier"]
