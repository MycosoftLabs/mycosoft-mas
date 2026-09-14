"""Nature Learning Model / FormSpace coupling plug (spec §2 ``nlm``, §11.4).

``observe()`` reports the scientific NLM probe (``model_loaded``, reason)
as an ``nlm`` observation — the encoder turns an unloaded model into *no
drive* and an ``UNQUALIFIED`` note. ``act()`` packs the population rates
of this tick into a ``formspace.observation/v1`` envelope
(``origin="SYNTHETIC"`` — the FormSpace word for non-measured input) and
pushes it through the process-wide :class:`CausalObservationPipeline`
with ``cutoff = available_at``. It also computes an anomaly score of the
current rate vector against the session's running mean/std (``None``
until five ticks have been seen).

This plug never emits a probability and never claims a forecast.
"""

from __future__ import annotations

import asyncio
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional

from mycosoft_mas.flybrain.plugs.base import FlyBrainPlug, PlugContext
from mycosoft_mas.flybrain.schemas import (
    ORIGIN_SIMULATED,
    DetectionFrame,
    MotorAction,
    NavPath,
    Observation,
)

CHART_ID = "flybrain.population_rates"
CHART_VERSION = "v1"
SOURCE_ID = "flybrain"
ANOMALY_MIN_TICKS = 5
PROBE_BUDGET_S = 3.0


def root_evidence_id(session_id: str, tick: int) -> str:
    return f"flybrain:{session_id}:{int(tick)}"


def build_envelope(
    session_id: str,
    tick: int,
    rates: Mapping[str, Any],
    *,
    t_ms: Optional[float] = None,
    now: Optional[datetime] = None,
    extra_provenance: Optional[Dict[str, Any]] = None,
) -> Any:
    """``formspace.observation/v1`` envelope of population rates (Hz per group).

    ``origin="SYNTHETIC"`` per the FormSpace contract; ``provenance.origin``
    carries the module's own ``SIMULATED`` label. ``root_evidence_id`` is
    ``flybrain:<session>:<tick>`` so the pipeline flags a replayed tick as a
    duplicate reading (M06).
    """
    from mycosoft_mas.nlm.formspace.contracts import ObservationEnvelope

    stamp = now or datetime.now(timezone.utc)
    values: Dict[str, float] = {}
    for key, value in (rates or {}).items():
        if isinstance(value, bool):
            continue
        try:
            f = float(value)
        except (TypeError, ValueError):
            continue
        if math.isnan(f) or math.isinf(f):
            continue
        values[str(key)] = f
    provenance: Dict[str, Any] = {
        "origin": ORIGIN_SIMULATED,
        "connectome": "flywire-783",
        "model": "shiu2024-lif",
        "session_id": session_id,
        "tick": int(tick),
    }
    if t_ms is not None:
        provenance["t_ms"] = float(t_ms)
    if extra_provenance:
        provenance.update(extra_provenance)
    return ObservationEnvelope(
        subject_id=session_id,
        source_id=SOURCE_ID,
        root_evidence_id=root_evidence_id(session_id, tick),
        event_time=stamp,
        received_at=stamp,
        available_at=stamp,
        chart_id=CHART_ID,
        chart_version=CHART_VERSION,
        values=values,
        units={k: "Hz" for k in values},
        observed_mask={k: True for k in values},
        quality={"n_groups": len(values), "simulated": True},
        origin="SYNTHETIC",
        provenance=provenance,
    )


class RateAnomalyTracker:
    """Welford running mean/variance per group; z-score RMS of a new vector.

    ``score`` is ``None`` until ``min_ticks`` vectors have been observed.
    Returns the diagnostic dict *before* folding the vector in.
    """

    def __init__(self, min_ticks: int = ANOMALY_MIN_TICKS) -> None:
        self.min_ticks = int(min_ticks)
        self.n = 0
        self._mean: Dict[str, float] = {}
        self._m2: Dict[str, float] = {}

    def evaluate(self, rates: Mapping[str, Any]) -> Dict[str, Any]:
        vec: Dict[str, float] = {}
        for k, v in (rates or {}).items():
            if isinstance(v, bool):
                continue
            try:
                f = float(v)
            except (TypeError, ValueError):
                continue
            if not (math.isnan(f) or math.isinf(f)):
                vec[str(k)] = f
        result: Dict[str, Any]
        if self.n < self.min_ticks:
            result = {
                "score": None,
                "n_history": self.n,
                "min_ticks": self.min_ticks,
                "method": "zscore_rms",
                "per_group": {},
                "note": (
                    f"anomaly score needs {self.min_ticks} ticks of history; "
                    f"{self.n} seen — no score invented"
                ),
            }
        else:
            per_group: Dict[str, float] = {}
            for k, x in vec.items():
                if k not in self._mean:
                    continue
                var = self._m2[k] / max(self.n - 1, 1)
                std = math.sqrt(var) if var > 0 else 0.0
                per_group[k] = (x - self._mean[k]) / std if std > 0 else 0.0
            if per_group:
                score = math.sqrt(sum(z * z for z in per_group.values()) / len(per_group))
            else:
                score = None
            worst = max(per_group.items(), key=lambda kv: abs(kv[1]))[0] if per_group else None
            result = {
                "score": score,
                "n_history": self.n,
                "min_ticks": self.min_ticks,
                "method": "zscore_rms",
                "per_group": per_group,
                "max_abs_z_group": worst,
                "note": (
                    "RMS z-score of this tick's group rates against the session running "
                    "mean/std; a session-relative novelty measure, not a probability"
                ),
            }
        # fold in
        self.n += 1
        for k, x in vec.items():
            mean = self._mean.get(k, 0.0)
            m2 = self._m2.get(k, 0.0)
            count_k = self.n
            delta = x - mean
            mean += delta / count_k
            m2 += delta * (x - mean)
            self._mean[k] = mean
            self._m2[k] = m2
        return result

    def state(self) -> Dict[str, Any]:
        return {"n": self.n, "groups": len(self._mean), "min_ticks": self.min_ticks}


def probe_nlm() -> Dict[str, Any]:
    """Scientific NLM probe (in-process); never raises."""
    try:
        from mycosoft_mas.nlm.formspace.scientific_loader import probe_scientific_nlm

        probe = probe_scientific_nlm()
        return {
            "model_loaded": bool(probe.model_loaded),
            "reason": str(probe.reason or ""),
            "model_dir": probe.model_dir,
            "schema": probe.schema,
            "is_legacy_reference": bool(probe.is_legacy_reference),
            "notes": list(probe.notes or []),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "model_loaded": False,
            "reason": f"probe failed: {type(exc).__name__}: {exc}",
            "model_dir": None,
            "schema": None,
            "is_legacy_reference": False,
            "notes": [],
        }


class NLMPlug(FlyBrainPlug):
    """FormSpace coupling: rates → observation envelopes; no probabilities."""

    name = "nlm"

    def __init__(self, config=None, settings=None) -> None:
        super().__init__(config, settings)
        self.anomaly = RateAnomalyTracker()
        self.last_probe: Dict[str, Any] = {}
        self.last_envelope_id: Optional[str] = None
        self.n_envelopes = 0

    def describe(self) -> Dict[str, Any]:
        base = super().describe()
        base.update(
            {
                "observe": "scientific NLM probe (model_loaded, reason) + optional "
                "plug_config.predict {text, confidence, metadata}",
                "act": "formspace.observation/v1 envelope of group rates → "
                "CausalObservationPipeline; z-score anomaly after 5 ticks",
                "chart_id": CHART_ID,
                "chart_version": CHART_VERSION,
                "emits_probability": False,
            }
        )
        return base

    async def observe(self, ctx: PlugContext) -> List[Observation]:
        notes: List[str] = []
        try:
            probe = await asyncio.wait_for(asyncio.to_thread(probe_nlm), PROBE_BUDGET_S)
        except Exception as exc:  # noqa: BLE001
            probe = {"model_loaded": False, "reason": f"probe timeout/failure: {exc}"}
        self.last_probe = probe
        payload: Dict[str, Any] = {
            "model_loaded": bool(probe.get("model_loaded")),
            "reason": probe.get("reason", ""),
        }
        predict = ctx.plug_config.get("predict")
        if isinstance(predict, Mapping):
            for key in ("prediction", "text", "confidence", "metadata"):
                if key in predict:
                    payload[key] = predict[key]
        if not payload["model_loaded"]:
            notes.append(f"nlm: UNQUALIFIED — scientific NLM not loaded ({payload['reason']})")
        self.last_observe_notes = notes
        ctx.notes.extend(notes)
        return [Observation(kind="nlm", payload=payload, t_ms=ctx.t_ms, source="nlm")]

    async def act(
        self,
        ctx: PlugContext,
        action: MotorAction,
        nav: Optional[NavPath],
        detections: Optional[DetectionFrame],
    ) -> Dict[str, Any]:
        rates = ctx.brain.rates_hz if ctx.brain is not None else ctx.encoded_rates_hz
        envelope = build_envelope(ctx.session_id, ctx.tick, rates, t_ms=ctx.t_ms)
        try:
            from mycosoft_mas.nlm.formspace.observation_pipeline import get_observation_pipeline

            pipeline_result = get_observation_pipeline().process(
                envelope, cutoff=envelope.available_at
            )
        except Exception as exc:  # noqa: BLE001
            pipeline_result = {
                "status": "pipeline_unavailable",
                "consumed": False,
                "error": f"{type(exc).__name__}: {exc}",
            }
        anomaly = self.anomaly.evaluate(rates)
        self.last_envelope_id = envelope.observation_id
        self.n_envelopes += 1
        model_loaded = bool(self.last_probe.get("model_loaded"))
        result = {
            "mode": self.name,
            "origin": ORIGIN_SIMULATED,
            "actuated": False,
            "dry_run": ctx.dry_run,
            "pipeline_result": pipeline_result,
            "envelope_id": envelope.observation_id,
            "root_evidence_id": envelope.root_evidence_id,
            "envelope": envelope.model_dump(mode="json"),
            "nlm_qualification": "QUALIFIED" if model_loaded else "UNQUALIFIED",
            "nlm_probe": self.last_probe,
            "anomaly": anomaly,
            "forecast": {
                "support_status": "UNSUPPORTED",
                "note": "FlyBrain never emits a forecast probability; the scientific NLM "
                "must be loaded and run its own Stage-B filter.",
            },
            "n_envelopes": self.n_envelopes,
        }
        self.last_result = result
        return result


__all__ = [
    "ANOMALY_MIN_TICKS",
    "CHART_ID",
    "CHART_VERSION",
    "NLMPlug",
    "RateAnomalyTracker",
    "build_envelope",
    "probe_nlm",
    "root_evidence_id",
]
