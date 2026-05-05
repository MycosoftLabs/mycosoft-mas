"""Load agents_matrix.yaml into AgentRow list."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from mycosoft_mas.agent100.constants import AGENT100_CONFIG_PATH
from mycosoft_mas.agent100.types import AgentRow, Framework


def load_agents(path: Path | None = None) -> list[AgentRow]:
    p = path or AGENT100_CONFIG_PATH
    if not p.exists():
        return []
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not raw or "agents" not in raw:
        return []
    out: list[AgentRow] = []
    for item in raw["agents"]:
        if not isinstance(item, dict):
            continue
        fid = str(item.get("id", "")).strip()
        if not fid:
            continue
        fw = str(item.get("framework", "mas_base"))
        if fw not in (
            "openclaw",
            "nemoclaw",
            "mas_base",
            "claude_api",
            "gpt_api",
            "gemini_api",
            "grok_api",
            "crewai",
            "langchain",
            "langgraph",
        ):
            fw = "mas_base"
        out.append(
            AgentRow(
                id=fid,
                archetype=str(item.get("archetype", "unknown")),
                framework=fw,  # type: ignore[arg-type]
                tier_budget_cents=int(item.get("tier_budget_cents", 20_000)),
                api_key_env=str(item.get("api_key_env", "")),
                pair_agent_id=item.get("pair_agent_id"),
                parent_agent_id=item.get("parent_agent_id"),
                meta={k: v for k, v in item.items() if k not in ("id", "archetype", "framework")},
            )
        )
    return out


def save_stub_matrix(path: Path | None = None) -> Path:
    """Write minimal 100-agent stub if file missing or agents list empty."""
    p = path or AGENT100_CONFIG_PATH
    if p.exists():
        try:
            raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            if raw.get("agents"):
                return p
        except Exception:
            pass
    p.parent.mkdir(parents=True, exist_ok=True)
    agents: list[dict[str, Any]] = []
    archetypes = [
        "defense_analyst",
        "finance_ops",
        "scientific_researcher",
        "device_field_tech",
        "data_engineer",
        "product_manager",
        "security_auditor",
        "legal_compliance",
        "customer_success",
        "executive_assistant",
        "marketing_creator",
        "sales_sdr",
        "support_tier1",
        "devops_sre",
        "ml_engineer",
        "bioinformatics",
        "gis_remote_sensing",
        "supply_chain",
        "hr_recruiter",
        "random_stress",
    ]
    for i in range(100):
        arch = archetypes[i % 20]
        fw: Framework = "openclaw" if i < 70 else "gpt_api"
        agents.append(
            {
                "id": f"agent100_{i+1:03d}",
                "archetype": arch,
                "framework": fw,
                "tier_budget_cents": 20_000,
                "api_key_env": f"AGENT100_KEY_AGENT100_{i+1:03d}",
            }
        )
    p.write_text(yaml.safe_dump({"version": 1, "agents": agents}, sort_keys=False), encoding="utf-8")
    return p
