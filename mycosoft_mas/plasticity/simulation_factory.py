"""
Plasticity Forge Phase 1 — simulation and replay infrastructure.

Provides deterministic scenarios for eval: telemetry replay, anomaly injection,
tool failures, contradictory sources, ecological counterfactuals, coding tasks,
control tasks. Produces scenario payloads and expected scoring contracts for
the real eval plane.

Created: March 14, 2026
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class ScenarioType(str, Enum):
    """Types of deterministic eval scenarios."""
    TELEMETRY_REPLAY = "telemetry_replay"
    ANOMALY_INJECTION = "anomaly_injection"
    TOOL_FAILURE = "tool_failure"
    CONTRADICTORY_SOURCE = "contradictory_source"
    ECOLOGICAL_COUNTERFACTUAL = "ecological_counterfactual"
    CODING_TASK = "coding_task"
    CONTROL_TASK = "control_task"
    MISSING_SENSOR = "missing_sensor"


@dataclass
class SimulationScenario:
    """A single scenario: type, input payload, expected scoring contract."""
    scenario_id: str
    scenario_type: str  # ScenarioType value
    name: str
    description: Optional[str] = None
    input_payload: Dict[str, Any] = field(default_factory=dict)
    expected_contract: Dict[str, Any] = field(default_factory=dict)  # e.g. min_groundedness, max_latency_ms
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    deterministic_seed: Optional[int] = None


def _hash_payload(payload: Dict[str, Any]) -> str:
    """Stable hash for deterministic replay."""
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


def make_telemetry_replay_scenario(
    telemetry_batch_id: str,
    replay_slice: Optional[Dict[str, Any]] = None,
    seed: Optional[int] = None,
) -> SimulationScenario:
    """Build a telemetry-replay scenario for deterministic eval."""
    payload = {
        "telemetry_batch_id": telemetry_batch_id,
        "replay_slice": replay_slice or {},
        "seed": seed,
    }
    sid = f"replay_{_hash_payload(payload)}"
    return SimulationScenario(
        scenario_id=sid,
        scenario_type=ScenarioType.TELEMETRY_REPLAY.value,
        name=f"Telemetry replay {telemetry_batch_id}",
        description="Replay recorded telemetry for regression and retention eval",
        input_payload=payload,
        expected_contract={"replay_complete": True, "retention_min": 0.0},
        deterministic_seed=seed,
    )


def make_anomaly_injection_scenario(
    anomaly_kind: str,
    severity: float = 0.5,
    base_payload: Optional[Dict[str, Any]] = None,
    seed: Optional[int] = None,
) -> SimulationScenario:
    """Build anomaly-injection scenario (sensor drift, outliers, missing windows)."""
    payload = {
        "anomaly_kind": anomaly_kind,
        "severity": severity,
        "base_payload": base_payload or {},
        "seed": seed,
    }
    sid = f"anomaly_{_hash_payload(payload)}"
    return SimulationScenario(
        scenario_id=sid,
        scenario_type=ScenarioType.ANOMALY_INJECTION.value,
        name=f"Anomaly {anomaly_kind} @ {severity}",
        description="Inject anomaly for robustness and calibration eval",
        input_payload=payload,
        expected_contract={"calibration_min": 0.0, "safety_ok": True},
        deterministic_seed=seed,
    )


def make_tool_failure_scenario(
    tool_id: str,
    failure_mode: str = "timeout",
    fallback_expected: bool = True,
) -> SimulationScenario:
    """Build tool-failure scenario for graceful degradation eval."""
    payload = {"tool_id": tool_id, "failure_mode": failure_mode, "fallback_expected": fallback_expected}
    sid = f"tool_fail_{_hash_payload(payload)}"
    return SimulationScenario(
        scenario_id=sid,
        scenario_type=ScenarioType.TOOL_FAILURE.value,
        name=f"Tool failure {tool_id} ({failure_mode})",
        input_payload=payload,
        expected_contract={"graceful_degrade": True, "no_cascade_failure": True},
    )


def make_contradictory_source_scenario(
    source_a: str,
    source_b: str,
    conflict_field: str,
    seed: Optional[int] = None,
) -> SimulationScenario:
    """Build contradictory-source scenario for groundedness and citation eval."""
    payload = {
        "source_a": source_a,
        "source_b": source_b,
        "conflict_field": conflict_field,
        "seed": seed,
    }
    sid = f"contra_{_hash_payload(payload)}"
    return SimulationScenario(
        scenario_id=sid,
        scenario_type=ScenarioType.CONTRADICTORY_SOURCE.value,
        name=f"Contradiction {source_a} vs {source_b}",
        description="Two sources disagree; expect grounded resolution or abstain",
        input_payload=payload,
        expected_contract={"groundedness_min": 0.0, "no_hallucination": True},
        deterministic_seed=seed,
    )


def make_ecological_counterfactual_scenario(
    counterfactual_type: str,
    world_state_snapshot: Optional[Dict[str, Any]] = None,
    seed: Optional[int] = None,
) -> SimulationScenario:
    """Build ecological counterfactual (what-if) for world-model consistency."""
    payload = {
        "counterfactual_type": counterfactual_type,
        "world_state_snapshot": world_state_snapshot or {},
        "seed": seed,
    }
    sid = f"eco_{_hash_payload(payload)}"
    return SimulationScenario(
        scenario_id=sid,
        scenario_type=ScenarioType.ECOLOGICAL_COUNTERFACTUAL.value,
        name=f"Counterfactual {counterfactual_type}",
        input_payload=payload,
        expected_contract={"consistency_min": 0.0},
        deterministic_seed=seed,
    )


def make_coding_task_scenario(
    task_id: str,
    language: str = "python",
    difficulty: str = "medium",
    spec: Optional[Dict[str, Any]] = None,
) -> SimulationScenario:
    """Build coding task scenario for capability and safety eval."""
    payload = {
        "task_id": task_id,
        "language": language,
        "difficulty": difficulty,
        "spec": spec or {},
    }
    sid = f"coding_{_hash_payload(payload)}"
    return SimulationScenario(
        scenario_id=sid,
        scenario_type=ScenarioType.CODING_TASK.value,
        name=f"Coding task {task_id}",
        input_payload=payload,
        expected_contract={"task_success_min": 0.0, "no_exec_arbitrary": True},
    )


def make_control_task_scenario(
    task_id: str,
    control_type: str,
    params: Optional[Dict[str, Any]] = None,
    seed: Optional[int] = None,
) -> SimulationScenario:
    """Build control task (e.g. setpoint, trajectory) for closed-loop eval."""
    payload = {"task_id": task_id, "control_type": control_type, "params": params or {}, "seed": seed}
    sid = f"control_{_hash_payload(payload)}"
    return SimulationScenario(
        scenario_id=sid,
        scenario_type=ScenarioType.CONTROL_TASK.value,
        name=f"Control task {task_id}",
        input_payload=payload,
        expected_contract={"stability_ok": True, "latency_p99_max_ms": 2000.0},
        deterministic_seed=seed,
    )


def make_missing_sensor_scenario(
    sensor_id: str,
    missing_window_seconds: float = 60.0,
    fallback_expected: bool = True,
) -> SimulationScenario:
    """Build missing-sensor scenario for robustness and degraded-state handling."""
    payload = {
        "sensor_id": sensor_id,
        "missing_window_seconds": missing_window_seconds,
        "fallback_expected": fallback_expected,
    }
    sid = f"missing_{_hash_payload(payload)}"
    return SimulationScenario(
        scenario_id=sid,
        scenario_type=ScenarioType.MISSING_SENSOR.value,
        name=f"Missing sensor {sensor_id}",
        input_payload=payload,
        expected_contract={"degraded_ok": True, "no_crash": True},
    )


def scenario_to_dict(scenario: SimulationScenario) -> Dict[str, Any]:
    """Serialize for registry or API."""
    return asdict(scenario)


def list_scenario_types() -> List[str]:
    """Return all scenario type values for API/docs."""
    return [t.value for t in ScenarioType]
