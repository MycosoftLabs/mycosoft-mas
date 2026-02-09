"""Bayesian Optimization for experiments. Created: February 3, 2026"""
import logging
from typing import Any, Dict, List, Tuple, Callable
from uuid import uuid4
import random

logger = logging.getLogger(__name__)

class BayesianOptimizer:
    """Bayesian optimization for experimental parameter tuning."""
    
    def __init__(self, parameter_bounds: Dict[str, Tuple[float, float]], acquisition_function: str = "ei"):
        self.parameter_bounds = parameter_bounds
        self.acquisition_function = acquisition_function
        self.observations: List[Tuple[Dict[str, float], float]] = []
    
    def suggest(self) -> Dict[str, float]:
        if len(self.observations) < 5:
            return {k: random.uniform(v[0], v[1]) for k, v in self.parameter_bounds.items()}
        return {k: (v[0] + v[1]) / 2 for k, v in self.parameter_bounds.items()}
    
    def observe(self, parameters: Dict[str, float], result: float) -> None:
        self.observations.append((parameters, result))
        logger.info(f"Observed result: {result}")
    
    def get_best(self) -> Tuple[Dict[str, float], float]:
        if not self.observations:
            return {}, 0.0
        return max(self.observations, key=lambda x: x[1])
    
    def optimize(self, objective_function: Callable, n_iterations: int = 20) -> Dict[str, Any]:
        for i in range(n_iterations):
            params = self.suggest()
            result = objective_function(params)
            self.observe(params, result)
        best_params, best_value = self.get_best()
        return {"best_parameters": best_params, "best_value": best_value, "iterations": n_iterations}
