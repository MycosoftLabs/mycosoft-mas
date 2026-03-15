"""
Plasticity Forge Phase 1 — mutation engine, fitness, promotion, simulation, compression, security.

Mutation engine v0 applies narrow operators only. Fitness policy enforces hard gates
and Pareto ranking. Simulation factory provides deterministic eval scenarios.
Compression lane defines edge recipes and Jetson acceptance. Security sandbox
enforces no prod secrets and approval tiers.
"""

from mycosoft_mas.plasticity.compression_lane import (
    check_edge_acceptance,
    default_edge_gate,
    list_recipe_types,
)
from mycosoft_mas.plasticity.fitness_policy import (
    evaluate_fitness,
    fitness_profile_to_dict,
    passes_hard_gates,
    pareto_rank,
)
from mycosoft_mas.plasticity.mutation_engine import (
    ALLOWED_OPERATORS,
    apply_mutations,
    validate_operator_params,
)
from mycosoft_mas.plasticity.security_governance_sandbox import (
    run_sandbox_check,
    sandbox_check_required,
)
from mycosoft_mas.plasticity.simulation_factory import (
    list_scenario_types,
    scenario_to_dict,
)

__all__ = [
    "ALLOWED_OPERATORS",
    "apply_mutations",
    "validate_operator_params",
    "evaluate_fitness",
    "passes_hard_gates",
    "pareto_rank",
    "fitness_profile_to_dict",
    "list_scenario_types",
    "scenario_to_dict",
    "check_edge_acceptance",
    "default_edge_gate",
    "list_recipe_types",
    "run_sandbox_check",
    "sandbox_check_required",
]
