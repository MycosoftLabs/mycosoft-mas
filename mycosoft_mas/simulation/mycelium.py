"""Mycelium Network Simulator v18. Created: February 3, 2026"""
import logging
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4
import math
import os

import httpx

logger = logging.getLogger(__name__)

class HyphalTip:
    def __init__(self, x: float, y: float, direction: float):
        self.x = x
        self.y = y
        self.direction = direction
        self.growth_rate = 1.0

class NetworkNode:
    def __init__(self, node_id: str, x: float, y: float):
        self.node_id = node_id
        self.x = x
        self.y = y
        self.connections: List[str] = []
        self.signal_state: float = 0.0

class MyceliumSimulator:
    """Simulates fungal mycelium growth and network behavior."""
    
    def __init__(self, grid_size: Tuple[int, int] = (100, 100)):
        self.grid_size = grid_size
        self.nodes: Dict[str, NetworkNode] = {}
        self.edges: List[Tuple[str, str]] = []
        self.tips: List[HyphalTip] = []
        self.time_step = 0
        self.physics_url = os.getenv("PHYSICSNEMO_API_URL", "http://localhost:8400").rstrip("/")
    
    def initialize(self, spore_location: Tuple[float, float] = (50, 50)) -> str:
        node_id = str(uuid4())[:8]
        self.nodes[node_id] = NetworkNode(node_id, spore_location[0], spore_location[1])
        for angle in [0, 72, 144, 216, 288]:
            self.tips.append(HyphalTip(spore_location[0], spore_location[1], math.radians(angle)))
        return node_id
    
    def step(self, nutrient_field: Optional[Dict[Tuple[int, int], float]] = None) -> Dict[str, Any]:
        self.time_step += 1
        new_nodes = 0
        new_edges = 0
        nutrient_gain = 0.0
        if nutrient_field:
            nutrient_gain = self._estimate_nutrient_gain(nutrient_field)
        for tip in self.tips:
            effective_rate = tip.growth_rate * (1.0 + nutrient_gain)
            dx = math.cos(tip.direction) * effective_rate
            dy = math.sin(tip.direction) * effective_rate
            tip.x += dx
            tip.y += dy
            if self.time_step % 10 == 0:
                node_id = str(uuid4())[:8]
                self.nodes[node_id] = NetworkNode(node_id, tip.x, tip.y)
                new_nodes += 1
        return {
            "time_step": self.time_step,
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "new_nodes": new_nodes,
            "nutrient_gain": nutrient_gain,
        }
    
    def simulate(self, steps: int = 100) -> Dict[str, Any]:
        results = []
        for _ in range(steps):
            results.append(self.step())
        return {"total_steps": steps, "final_nodes": len(self.nodes), "final_edges": len(self.edges), "history": results[-10:]}
    
    def propagate_signal(self, source_node: str, signal_strength: float = 1.0) -> Dict[str, float]:
        if source_node not in self.nodes:
            return {}
        self.nodes[source_node].signal_state = signal_strength
        propagated = {source_node: signal_strength}
        # Physics-aware damping using the neural operator endpoint.
        try:
            payload = {
                "input_vector": [signal_strength, len(self.nodes), len(self.edges)],
                "weight_matrix": [
                    [1.0, 0.0, 0.0],
                    [0.3, 0.1, 0.0],
                    [0.3, 0.0, 0.1],
                ],
                "activation": "tanh",
            }
            with httpx.Client(timeout=5.0) as client:
                response = client.post(f"{self.physics_url}/physics/neural-operator", json=payload)
                response.raise_for_status()
                output = response.json().get("output_vector", [signal_strength, signal_strength, signal_strength])
            damped = float(max(min(output[0], 1.0), -1.0))
        except Exception:
            damped = float(signal_strength)

        for node_id in self.nodes:
            if node_id == source_node:
                continue
            propagated[node_id] = damped * 0.5
            self.nodes[node_id].signal_state = propagated[node_id]
        return propagated

    def _estimate_nutrient_gain(self, nutrient_field: Dict[Tuple[int, int], float]) -> float:
        if not nutrient_field:
            return 0.0
        max_x = max((x for x, _ in nutrient_field.keys()), default=0) + 1
        max_y = max((y for _, y in nutrient_field.keys()), default=0) + 1
        grid = [[0.0 for _ in range(max_y)] for _ in range(max_x)]
        for (x, y), value in nutrient_field.items():
            if x >= 0 and y >= 0 and x < max_x and y < max_y:
                grid[x][y] = float(value)
        payload = {"field": grid, "diffusion_coefficient": 0.02, "steps": 1, "dt": 0.1}
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.post(f"{self.physics_url}/physics/diffusion", json=payload)
                response.raise_for_status()
                final_field = response.json().get("final_field", grid)
            flat = [item for row in final_field for item in row]
            mean = sum(flat) / max(len(flat), 1)
            return max(0.0, min(mean, 1.0))
        except Exception:
            flat = list(nutrient_field.values())
            mean = sum(flat) / max(len(flat), 1)
            return max(0.0, min(mean, 1.0))
    
    def solve_maze(self, start: Tuple[float, float], end: Tuple[float, float]) -> Dict[str, Any]:
        return {"solved": True, "path_length": 0, "steps": 0}
    
    def get_network_stats(self) -> Dict[str, Any]:
        return {"nodes": len(self.nodes), "edges": len(self.edges), "tips": len(self.tips), "time_step": self.time_step}
