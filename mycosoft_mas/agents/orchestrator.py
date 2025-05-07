from __future__ import annotations

"""High-level MAS orchestrator.
Spawns CrewAI agents and registers MCP tools.
Run with `python -m mycosoft_mas.agents.orchestrator`.
"""

import os
from crewai import Agent, Crew
from agentcards import MCPToolRegistry  # type: ignore

# URL of the MCP registry (fastapi_mcp will expose /mcp locally)
MCP_REGISTRY_URL = os.getenv("MCP_REGISTRY_URL", "http://localhost:8000/mcp")

registry = MCPToolRegistry(MCP_REGISTRY_URL)

lab_agent = Agent(
    name="LabAgent",
    system_instruction="Operate field devices via MCP tools only.",
    tools=registry.tools_for("mycosoft.lab_ops"),
)

dev_agent = Agent(
    name="DevAgent",
    system_instruction="Maintain CI, run unit-tests and open PRs.",
    tools=registry.tools_for("dev"),
)

crew = Crew(manager_llm="o3-mini", agents=[lab_agent, dev_agent])


def main() -> None:  # pragma: no cover
    """Entry-point: start the orchestrator loop."""
    task = os.getenv("MAS_TASK", "Initial system bootstrap")
    crew.run(task)


if __name__ == "__main__":
    main() 