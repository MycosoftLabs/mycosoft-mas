"""ITDX Task 8 — seven-role COA review bound to live MAS agents.

Kit roles (ITDX_Weka_Demo_Kit itdx/app/itdx/algorithms.py,
DETERMINISTIC_SEVEN_ROLE_REVIEW): State summarizer, COA proposer,
Alternative planner, Skeptical critic, Evidence verifier, AVANI guardian,
Human handoff.

No invented LLM personas. Each role maps to an existing agent_id and
calls process_task (or the live AvaniGovernor). Errors are returned as
errors — never a fabricated PASS.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from mycosoft_mas.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

SCHEMA_VERSION = "itdx-task8/v1"
SITUATION_SCHEMA_VERSION = "itdx.situation_assessment/v1"

# Canonical kit role labels — do not rename.
ROLE_STATE_SUMMARIZER = "State summarizer"
ROLE_COA_PROPOSER = "COA proposer"
ROLE_ALTERNATIVE_PLANNER = "Alternative planner"
ROLE_SKEPTICAL_CRITIC = "Skeptical critic"
ROLE_EVIDENCE_VERIFIER = "Evidence verifier"
ROLE_AVANI_GUARDIAN = "AVANI guardian"
ROLE_HUMAN_HANDOFF = "Human handoff"

DEFAULT_COA_SPECS: Tuple[Tuple[str, str, int, int, str], ...] = (
    ("observe", "Continue observation", 0, 15, "analyst"),
    ("request_sample", "Request independent corroboration", 20, 20, "sampling_team"),
    ("restore_link", "Restore the evidence connection", 50, 30, "network_operator"),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _role_row(
    *,
    role_id: str,
    label: str,
    agent_id: str,
    verdict: str,
    bound: bool,
    note: str = "",
    process_result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    gate = verdict if verdict in {"DENY", "PAUSE", "PASS", "REVIEW"} else "UNQUALIFIED"
    return {
        "id": role_id,
        "label": label,
        "name": label,
        "agent_id": agent_id,
        "verdict": gate,
        "gate": gate,
        "bound": bound,
        "ok": bound and error is None,
        "live": bound,
        "note": note,
        "error": error,
        "process_result": process_result,
    }


def avani_to_task8_gate(
    *,
    approved: Optional[bool],
    has_evidence: bool,
    envelope_complete: bool,
    hard_veto: bool = False,
) -> str:
    """Kit order: DENY → PAUSE → PASS → REVIEW."""
    if hard_veto or approved is False:
        return "DENY"
    if not has_evidence:
        return "PAUSE"
    if approved is True and envelope_complete:
        return "PASS"
    return "REVIEW"


def aggregate_avani_gate(role_verdicts: List[str], option_gates: List[str]) -> str:
    combined = [v for v in role_verdicts + option_gates if v]
    if any(v == "DENY" for v in combined):
        return "DENY"
    if all(v == "PAUSE" for v in combined) or (
        "PAUSE" in combined and not any(v == "PASS" for v in combined)
    ):
        if not any(v == "REVIEW" for v in combined) and not any(v == "PASS" for v in combined):
            return "PAUSE"
    if any(v == "PASS" for v in option_gates) and not any(v == "DENY" for v in combined):
        if all(v in {"PASS", "REVIEW"} for v in option_gates):
            return "PASS" if all(v == "PASS" for v in option_gates) else "REVIEW"
    return "REVIEW"


def borda_rank(options: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Borda on PASS options only. Preference, not P(success)."""
    passing = [o for o in options if o.get("formspace_gate") == "PASS"]
    m = len(passing)
    if m == 0:
        return []
    ranked = sorted(
        passing,
        key=lambda o: (-float(o.get("score") or 0), o.get("id") or ""),
    )
    out: List[Dict[str, Any]] = []
    for i, option in enumerate(ranked):
        out.append(
            {
                "id": option["id"],
                "title": option.get("title"),
                "borda_points": m - 1 - i,
                "rank": i + 1,
            }
        )
    return out


def mapped_role_probes() -> List[Dict[str, Any]]:
    """Honest mapped-role index. Templates are not bound."""
    return [
        {
            "kit_role": ROLE_STATE_SUMMARIZER,
            "agent_id": "grounding-agent",
            "module": "mycosoft_mas/agents/v2/grounding_agent.py",
        },
        {
            "kit_role": ROLE_COA_PROPOSER,
            "agent_id": "intention-agent",
            "module": "mycosoft_mas/agents/v2/intention_agent.py",
        },
        {
            "kit_role": ROLE_ALTERNATIVE_PLANNER,
            "agent_id": "planner-agent",
            "module": "mycosoft_mas/agents/v2/planner_agent.py",
        },
        {
            "kit_role": ROLE_SKEPTICAL_CRITIC,
            "agent_id": "reflection-agent",
            "module": "mycosoft_mas/agents/v2/reflection_agent.py",
        },
        {
            "kit_role": ROLE_EVIDENCE_VERIFIER,
            "agent_id": "grounding-agent",
            "module": "mycosoft_mas/agents/v2/grounding_agent.py",
        },
        {
            "kit_role": ROLE_AVANI_GUARDIAN,
            "agent_id": "avani-governor",
            "module": "mycosoft_mas/avani/governor/governor.py",
        },
        {
            "kit_role": ROLE_HUMAN_HANDOFF,
            "agent_id": "secretary",
            "module": "not_invoked",
            "bound": False,
            "note": "SecretaryAgent is not invoked. Human handoff stays unbound.",
        },
    ]


def _role_process_ok(row: Dict[str, Any]) -> bool:
    if not row.get("bound") or row.get("error"):
        return False
    process_result = row.get("process_result")
    if isinstance(process_result, dict) and process_result.get("status") == "error":
        return False
    return True


def qualify_seven_roles(roles: List[Dict[str, Any]]) -> str:
    """BOUND only if all seven process_task rows succeed with no error."""
    if len(roles) < 7:
        return "UNQUALIFIED"
    oks = [_role_process_ok(row) for row in roles]
    if all(oks):
        return "BOUND"
    if any(oks):
        return "DEGRADED"
    return "UNQUALIFIED"


def _slice_evidence(map_slice: Dict[str, Any]) -> List[Dict[str, Any]]:
    assets = map_slice.get("assets") or map_slice.get("units") or []
    if not isinstance(assets, list):
        return []
    refs = []
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        refs.append(
            {
                "id": asset.get("id"),
                "label": asset.get("label") or asset.get("name"),
                "lat": asset.get("lat"),
                "lon": asset.get("lon") or asset.get("lng"),
                "type": asset.get("type"),
            }
        )
    return refs


def _constraints(map_slice: Dict[str, Any]) -> Dict[str, Any]:
    supplied = map_slice.get("constraints") if isinstance(map_slice.get("constraints"), dict) else {}
    return {
        "goal": supplied.get("goal")
        or map_slice.get("goal")
        or "Review the declared AO and preserve evidence. Advisory only.",
        "max_cost": float(supplied.get("max_cost", 100.0)),
        "max_duration_minutes": float(supplied.get("max_duration_minutes", 60)),
        "available_resources": list(
            supplied.get("available_resources")
            or ["analyst", "sampling_team", "network_operator"]
        ),
        "allowed_actions": list(
            supplied.get("allowed_actions") or ["observe", "request_sample", "restore_link"]
        ),
        "human_authority": supplied.get("human_authority") or "Analyst review only",
    }


async def _call_process(
    agent: Any, task: Dict[str, Any]
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        result = await agent.process_task(task)
        if not isinstance(result, dict):
            return {"raw": str(result)}, None
        if result.get("status") == "error":
            err = result.get("error") or result.get("result", {}).get("error")
            return result, str(err) if err else "process_task returned status=error"
        return result, None
    except Exception as exc:
        logger.warning("process_task failed on %s: %s", getattr(agent, "agent_id", type(agent)), exc)
        return None, str(exc)


async def _evaluate_avani(option: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        from mycosoft_mas.avani.agents.avani_agent import AvaniAgent

        agent = AvaniAgent(agent_id="avani-governor", name="Avani", config={})
        result, err = await _call_process(
            agent,
            {
                "type": "evaluate_proposal",
                "source_agent": "itdx-task8",
                "action_type": option.get("action_type") or "observe",
                "description": (
                    f"{option.get('title')}: advisory only. Synthetic environmental "
                    "envelope. No actuator. No physical command."
                ),
                "risk_tier": "low",
                "ecological_impact": 0.05 if option.get("action_type") == "observe" else 0.12,
                "reversibility": 1.0,
                "metadata": {
                    "task": "8",
                    "option_id": option.get("id"),
                    "origin": "SYNTHETIC_EXERCISE",
                    "execution": "ADVISORY_ONLY",
                },
            },
        )
        if result and result.get("status") == "success" and isinstance(result.get("decision"), dict):
            return result["decision"], None
        if err:
            return await _evaluate_avani_governor(option, fallback_error=err)
        return result, err
    except Exception as exc:
        return await _evaluate_avani_governor(option, fallback_error=str(exc))


async def _evaluate_avani_governor(
    option: Dict[str, Any], fallback_error: str
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        from mycosoft_mas.avani.governor.governor import AvaniGovernor, Proposal, RiskTier

        gov = AvaniGovernor()
        decision = await gov.evaluate_proposal(
            Proposal(
                source_agent="itdx-task8",
                action_type=str(option.get("action_type") or "observe"),
                description=(
                    f"{option.get('title')}: advisory only. Synthetic environmental "
                    "envelope. No actuator."
                ),
                risk_tier=RiskTier.LOW,
                ecological_impact=0.05 if option.get("action_type") == "observe" else 0.12,
                reversibility=1.0,
                metadata={"task": "8", "option_id": option.get("id")},
            )
        )
        payload = decision.to_dict()
        payload["fallback"] = "AvaniGovernor.evaluate_proposal"
        payload["agent_process_error"] = fallback_error
        return payload, None
    except Exception as exc:
        return None, f"{fallback_error}; governor fallback failed: {exc}"


class ITDXTask8Agent(BaseAgent):
    """Seven-role Task 8 reviewer. Calls existing MAS agents; no mock PASS."""

    def __init__(
        self,
        agent_id: str = "itdx-task8",
        name: str = "ITDX Task 8",
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(agent_id=agent_id, name=name, config=config or {})
        self.capabilities = [
            "task8_review",
            "situation_assessment",
            "coa_propose",
            "avani_gate",
        ]

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        task_type = task.get("type") or "task8_review"
        if task_type in {"task8_review", "task8", "coa_review"}:
            return await self.run_task8(task.get("map_slice") or task)
        if task_type == "situation_assessment":
            return {
                "status": "error",
                "error": "situation_assessment is served by POST /api/itdx/situation-assessment",
            }
        return {"status": "error", "error": f"Unknown task type: {task_type}"}

    async def run_task8(self, map_slice: Dict[str, Any]) -> Dict[str, Any]:
        evidence = _slice_evidence(map_slice)
        constraints = _constraints(map_slice)
        has_evidence = bool(evidence)
        ao = map_slice.get("ao") if isinstance(map_slice.get("ao"), dict) else {}
        clock = map_slice.get("clock") or _utc_now()
        summary_text = (
            f"{len(evidence)} declared assets in AO "
            f"{ao.get('name') or ao.get('place') or 'UNSPECIFIED'} at {clock}."
        )

        roles: List[Dict[str, Any]] = []

        # 1. State summarizer → GroundingAgent
        grounding_result, grounding_err = await self._ground(summary_text, map_slice)
        roles.append(
            _role_row(
                role_id="state_summarizer",
                label=ROLE_STATE_SUMMARIZER,
                agent_id="grounding-agent",
                verdict="PAUSE" if not has_evidence else "REVIEW",
                bound=grounding_err is None,
                note=summary_text,
                process_result=grounding_result,
                error=grounding_err,
            )
        )

        # 2. COA proposer → IntentionAgent + kit templates
        intention_result, intention_err = await self._intention(constraints["goal"])
        options = self._build_options(constraints, evidence)
        roles.append(
            _role_row(
                role_id="coa_proposer",
                label=ROLE_COA_PROPOSER,
                agent_id="intention-agent",
                verdict="REVIEW" if options else "PAUSE",
                bound=intention_err is None
                and intention_result is not None
                and intention_result.get("status") != "error",
                note=f"Created {len(options)} template proposals. Templates alone are not bound.",
                process_result=intention_result,
                error=intention_err,
            )
        )

        # 3. Alternative planner → PlannerAgent
        planner_result, planner_err = await self._plan(constraints["goal"], options)
        distinct = len({o["action_type"] for o in options})
        roles.append(
            _role_row(
                role_id="alternative_planner",
                label=ROLE_ALTERNATIVE_PLANNER,
                agent_id="planner-agent",
                verdict="REVIEW" if distinct >= 2 else "PAUSE",
                bound=planner_err is None,
                note=f"{distinct} distinct action types.",
                process_result=planner_result,
                error=planner_err,
            )
        )

        # 4–6. Critic, verifier, AVANI — evaluate each option through Avani
        critic_notes: List[str] = []
        for option in options:
            decision, avani_err = await _evaluate_avani(option)
            option["native_avani"] = decision
            option["avani_error"] = avani_err
            approved = None if decision is None else bool(decision.get("approved"))
            hard = bool(decision and decision.get("red_line_violations"))
            checks = option.get("checks") or {}
            envelope_complete = all(checks.values()) if checks else False
            option["formspace_gate"] = avani_to_task8_gate(
                approved=approved,
                has_evidence=has_evidence,
                envelope_complete=envelope_complete,
                hard_veto=hard,
            )
            option["gate"] = option["formspace_gate"]
            option["mas_approved"] = approved
            option["mas_reason"] = (
                (decision or {}).get("reason") if decision else avani_err
            )
            if avani_err:
                critic_notes.append(f"{option['id']}: {avani_err}")
            failed = [k for k, v in checks.items() if not v]
            if failed:
                critic_notes.append(f"{option['id']} failed {failed}")

        reflection_result, reflection_err = await self._reflect(options)
        roles.append(
            _role_row(
                role_id="skeptical_critic",
                label=ROLE_SKEPTICAL_CRITIC,
                agent_id="reflection-agent",
                verdict="REVIEW",
                bound=reflection_err is None,
                note="; ".join(critic_notes) or "Preserved failed checks; agreement is not evidence.",
                process_result=reflection_result,
                error=reflection_err,
            )
        )

        unresolved = [e for e in evidence if e.get("id") is None]
        roles.append(
            _role_row(
                role_id="evidence_verifier",
                label=ROLE_EVIDENCE_VERIFIER,
                agent_id="grounding-agent",
                verdict="PAUSE" if not has_evidence else ("REVIEW" if unresolved else "PASS"),
                bound=grounding_err is None,
                note=(
                    f"{len(evidence)} slice asset refs. "
                    "IDs resolve to the submitted map slice only — not SME entailment."
                ),
                process_result={"evidence_refs": evidence, "unresolved": unresolved},
                error=grounding_err,
            )
        )

        avani_errors = [o.get("avani_error") for o in options if o.get("avani_error")]
        option_gates = [str(o.get("formspace_gate")) for o in options]
        roles.append(
            _role_row(
                role_id="avani_guardian",
                label=ROLE_AVANI_GUARDIAN,
                agent_id="avani-governor",
                verdict=aggregate_avani_gate([], option_gates),
                bound=bool(options)
                and not avani_errors
                and all(o.get("native_avani") for o in options),
                note="; ".join(f"{o['id']}: {o.get('formspace_gate')}" for o in options),
                process_result={"options": [{"id": o["id"], "avani": o.get("native_avani")} for o in options]},
                error="; ".join(str(e) for e in avani_errors) if avani_errors else None,
            )
        )

        # 7. Human handoff — no actuation. SecretaryAgent needs Google creds; do not fake it.
        roles.append(
            _role_row(
                role_id="human_handoff",
                label=ROLE_HUMAN_HANDOFF,
                agent_id="secretary",
                verdict="REVIEW",
                bound=False,
                note=(
                    "No actuation. SecretaryAgent (registry id=secretary) is not invoked. "
                    "Review options; GATE/VETO cannot be selected. execution=ADVISORY_ONLY."
                ),
                process_result={"intended_agent_id": "secretary", "execution": "ADVISORY_ONLY"},
                error="secretary_not_invoked",
            )
        )

        avani_gate = aggregate_avani_gate([r["verdict"] for r in roles], option_gates)
        ranking = borda_rank(options)
        return {
            "status": "success",
            "schema": SCHEMA_VERSION,
            "schema_version": SCHEMA_VERSION,
            "agent_id": self.agent_id,
            "role": "task8_review",
            "source": "mas",
            "mode": "DETERMINISTIC_SEVEN_ROLE_REVIEW",
            "origin": map_slice.get("origin") or "SYNTHETIC_EXERCISE",
            "execution": "ADVISORY_ONLY",
            "synthetic": True,
            "live_cop": False,
            "clock": clock,
            "ao": ao,
            "roles": roles,
            "options": options,
            "borda": ranking,
            "rank_semantics": "Preference only; never probability of success",
            "avani_gate": avani_gate,
            "seven_role": {
                "qualification": qualify_seven_roles(roles),
                "role_count": sum(1 for r in roles if _role_process_ok(r)),
                "source": "mas",
            },
        }

    async def _ground(
        self, content: str, map_slice: Dict[str, Any]
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            from mycosoft_mas.agents.v2.grounding_agent import GroundingAgent

            agent = GroundingAgent("grounding-agent", "Grounding Agent", {})
            return await _call_process(
                agent,
                {
                    "type": "ground_input",
                    "content": content,
                    "source": "itdx-task8",
                    "context": {"ao": map_slice.get("ao"), "clock": map_slice.get("clock")},
                },
            )
        except Exception as exc:
            return None, str(exc)

    async def _intention(self, goal: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            from mycosoft_mas.agents.v2.intention_agent import IntentionAgent

            agent = IntentionAgent("intention-agent", "Intention Agent", {})
            return await _call_process(
                agent,
                {"type": "plan_candidates", "directive": goal, "content": goal},
            )
        except Exception as exc:
            return None, str(exc)

    async def _plan(
        self, goal: str, options: List[Dict[str, Any]]
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            from mycosoft_mas.agents.v2.planner_agent import PlannerAgent

            agent = PlannerAgent("planner-agent", "Planner Agent", {})
            return await _call_process(
                agent,
                {
                    "type": "plan",
                    "goal": goal,
                    "candidates": [o["id"] for o in options],
                },
            )
        except Exception as exc:
            return None, str(exc)

    async def _reflect(
        self, options: List[Dict[str, Any]]
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            from mycosoft_mas.agents.v2.reflection_agent import ReflectionAgent

            agent = ReflectionAgent("reflection-agent", "Reflection Agent", {})
            prediction = ",".join(o.get("action_type", "") for o in options)
            actual = "advisory_only_no_actuation"
            return await _call_process(
                agent,
                {"type": "analyze_outcome", "prediction": prediction, "actual": actual},
            )
        except Exception as exc:
            return None, str(exc)

    def _build_options(
        self, constraints: Dict[str, Any], evidence: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        options: List[Dict[str, Any]] = []
        refs = [e.get("id") for e in evidence if e.get("id")]
        for i, (kind, title, cost, duration, resource) in enumerate(DEFAULT_COA_SPECS):
            checks = {
                "goal_present": bool(constraints.get("goal")),
                "fresh_evidence": bool(evidence),
                "within_cost": cost <= constraints["max_cost"],
                "within_duration": duration <= constraints["max_duration_minutes"],
                "resource_available": resource in constraints["available_resources"],
                "action_allowed": kind in constraints["allowed_actions"],
            }
            options.append(
                {
                    "id": f"coa-{i + 1}",
                    "title": title,
                    "action_type": kind,
                    "cost": cost,
                    "duration_minutes": duration,
                    "resource": resource,
                    "checks": checks,
                    "evidence_refs": refs,
                    "score": round(80.0 - cost * 0.2 - duration * 0.3, 3),
                    "envelope": {
                        "identity": kind,
                        "scope": "Synthetic/recorded environmental monitoring only",
                        "magnitude": "One advisory option",
                        "duration_minutes": duration,
                        "stop_conditions": ["Evidence is invalidated", "Analyst stops review"],
                        "rollback": "Withdraw recommendation; preserve the evidence record",
                        "authority": constraints.get("human_authority"),
                    },
                    "execution": "ADVISORY_ONLY",
                }
            )
        return options
