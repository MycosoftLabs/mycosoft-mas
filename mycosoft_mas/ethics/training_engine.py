"""
MYCA Ethics Training Engine

Loads and runs training scenarios from YAML files. Feeds scenario prompts
to sandboxed MYCA instances and collects responses for grading.

Created: March 4, 2026
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from mycosoft_mas.ethics.sandbox_manager import SandboxChatError, get_sandbox_manager

logger = logging.getLogger(__name__)

SCENARIOS_DIR = Path(__file__).parent / "scenarios"

# Learning method categories (plan)
SCENARIO_CATEGORIES = ("memorization", "trial_and_error", "experience", "reading", "game")


@dataclass
class TrainingScenario:
    """A single ethics training scenario."""

    scenario_id: str
    title: str
    description: str
    category: str  # memorization, trial_and_error, experience, reading, game
    vessel_level: List[str]  # which developmental stages it targets
    prompt_sequence: List[str]  # ordered prompts/situations
    rubric: Dict[str, Any]  # grading criteria
    expected_behaviors: List[str] = field(default_factory=list)
    max_rounds: int = 10


@dataclass
class ScenarioRunResult:
    """Result of running a scenario on a sandbox session."""

    session_id: str
    scenario_id: str
    prompts_sent: List[str]
    responses: List[Dict[str, str]]  # [{"prompt":..., "response":...}, ...]
    completed: bool
    error: Optional[str] = None
    error_code: Optional[str] = None


class TrainingEngine:
    """
    Loads scenarios from YAML and runs them against sandbox sessions.
    """

    def __init__(self, scenarios_dir: Optional[Path] = None):
        self._scenarios_dir = scenarios_dir or SCENARIOS_DIR
        self._scenarios: Dict[str, TrainingScenario] = {}
        self._load_scenarios()

    def _load_scenarios(self) -> None:
        """Load all YAML/JSON scenario files from the scenarios directory."""
        self._scenarios.clear()
        if not self._scenarios_dir.exists():
            logger.warning(f"Scenarios dir not found: {self._scenarios_dir}")
            return

        try:
            import yaml
        except ImportError:
            logger.warning("PyYAML not installed; scenario loading disabled")
            return

        for path in self._scenarios_dir.glob("*.yaml"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if not data:
                    continue
                scenario = self._parse_scenario(data, path.stem)
                if scenario:
                    self._scenarios[scenario.scenario_id] = scenario
                    logger.info(f"Loaded scenario: {scenario.scenario_id}")
            except Exception as e:
                logger.warning(f"Failed to load scenario {path}: {e}")

        for path in self._scenarios_dir.glob("*.yml"):
            if path.stem + ".yaml" in [p.name for p in self._scenarios_dir.glob("*.yaml")]:
                continue  # skip if .yaml version exists
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if not data:
                    continue
                scenario = self._parse_scenario(data, path.stem)
                if scenario:
                    self._scenarios[scenario.scenario_id] = scenario
            except Exception as e:
                logger.warning(f"Failed to load scenario {path}: {e}")

    def _parse_scenario(self, data: Dict[str, Any], default_id: str) -> Optional[TrainingScenario]:
        """Parse a scenario dict from YAML into TrainingScenario."""
        scenario_id = data.get("scenario_id") or data.get("id") or default_id
        title = data.get("title", scenario_id)
        description = data.get("description", "")
        category = data.get("category", "experience")
        vessel_level = data.get("vessel_level") or data.get("vessel_levels") or []
        if isinstance(vessel_level, str):
            vessel_level = [vessel_level]

        prompt_sequence = data.get("prompt_sequence") or data.get("prompts") or []
        if isinstance(prompt_sequence, str):
            prompt_sequence = [prompt_sequence]

        rubric = data.get("rubric") or {}
        expected_behaviors = data.get("expected_behaviors") or []
        max_rounds = int(data.get("max_rounds", 10))

        return TrainingScenario(
            scenario_id=scenario_id,
            title=title,
            description=description,
            category=category,
            vessel_level=vessel_level,
            prompt_sequence=prompt_sequence,
            rubric=rubric,
            expected_behaviors=expected_behaviors,
            max_rounds=max_rounds,
        )

    def load_scenarios(self) -> Dict[str, TrainingScenario]:
        """Reload scenarios from disk and return them."""
        self._load_scenarios()
        return dict(self._scenarios)

    def get_scenario(self, scenario_id: str) -> Optional[TrainingScenario]:
        """Get a scenario by id."""
        return self._scenarios.get(scenario_id)

    def list_scenarios(self) -> List[TrainingScenario]:
        """List all loaded scenarios."""
        return list(self._scenarios.values())

    async def run_scenario(self, session_id: str, scenario_id: str) -> ScenarioRunResult:
        """
        Run a scenario on a sandbox session.
        Feeds each prompt in the sequence to the sandbox MYCA and collects responses.
        """
        manager = get_sandbox_manager()
        session = manager.get_session(session_id)
        if not session:
            return ScenarioRunResult(
                session_id=session_id,
                scenario_id=scenario_id,
                prompts_sent=[],
                responses=[],
                completed=False,
                error="Session not found",
                error_code="session_not_found",
            )

        scenario = self._scenarios.get(scenario_id)
        if not scenario:
            return ScenarioRunResult(
                session_id=session_id,
                scenario_id=scenario_id,
                prompts_sent=[],
                responses=[],
                completed=False,
                error="Scenario not found",
                error_code="scenario_not_found",
            )

        # Check vessel compatibility
        vessel_val = session.vessel_stage.value
        if scenario.vessel_level and vessel_val not in scenario.vessel_level:
            logger.info(
                f"Session vessel {vessel_val} not in scenario targets {scenario.vessel_level}; running anyway"
            )

        prompts_sent: List[str] = []
        responses: List[Dict[str, str]] = []
        max_rounds = min(scenario.max_rounds, len(scenario.prompt_sequence) or 1)

        try:
            for i, prompt in enumerate(scenario.prompt_sequence[:max_rounds]):
                prompts_sent.append(prompt)
                response_text = await manager.chat(session_id, prompt)
                responses.append({"prompt": prompt, "response": response_text})
        except SandboxChatError as e:
            logger.warning(f"Scenario run sandbox chat error: {e.code}: {e}")
            return ScenarioRunResult(
                session_id=session_id,
                scenario_id=scenario_id,
                prompts_sent=prompts_sent,
                responses=responses,
                completed=False,
                error=str(e),
                error_code=e.code,
            )
        except Exception as e:
            logger.warning(f"Scenario run error: {e}")
            return ScenarioRunResult(
                session_id=session_id,
                scenario_id=scenario_id,
                prompts_sent=prompts_sent,
                responses=responses,
                completed=False,
                error=str(e),
                error_code="scenario_run_error",
            )

        return ScenarioRunResult(
            session_id=session_id,
            scenario_id=scenario_id,
            prompts_sent=prompts_sent,
            responses=responses,
            completed=True,
        )


_training_engine: Optional[TrainingEngine] = None


def get_training_engine() -> TrainingEngine:
    """Return the global TrainingEngine instance."""
    global _training_engine
    if _training_engine is None:
        _training_engine = TrainingEngine()
    return _training_engine
