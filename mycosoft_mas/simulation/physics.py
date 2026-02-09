"""Physics simulation module backed by PhysicsNeMo local service."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
from uuid import uuid4
import os

import httpx
import numpy as np


class PhysicsSimulator:
    """General physics simulations for NatureOS and MAS simulators."""

    def __init__(
        self,
        domain_size: Tuple[int, int, int] = (100, 100, 100),
        service_url: str | None = None,
        timeout_seconds: float = 60.0,
    ) -> None:
        self.domain_size = domain_size
        self.service_url = (service_url or os.getenv("PHYSICSNEMO_API_URL", "http://localhost:8400")).rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(f"{self.service_url}{path}", json=payload)
            response.raise_for_status()
            return response.json()

    def _dict_field_to_grid(self, values: Dict[Tuple[int, int], float]) -> List[List[float]]:
        max_x = max((coord[0] for coord in values.keys()), default=0) + 1
        max_y = max((coord[1] for coord in values.keys()), default=0) + 1
        grid = np.zeros((max_x, max_y), dtype=np.float32)
        for (x, y), val in values.items():
            if x >= 0 and y >= 0:
                grid[x, y] = float(val)
        return grid.tolist()

    @staticmethod
    def _laplacian(field: np.ndarray) -> np.ndarray:
        padded = np.pad(field, pad_width=1, mode="edge")
        center = padded[1:-1, 1:-1]
        left = padded[1:-1, 0:-2]
        right = padded[1:-1, 2:]
        up = padded[0:-2, 1:-1]
        down = padded[2:, 1:-1]
        return left + right + up + down - 4.0 * center

    async def simulate_diffusion(
        self,
        initial_concentration: Dict[Tuple[int, int], float],
        diffusion_coefficient: float,
        time_steps: int = 100,
    ) -> Dict[str, Any]:
        simulation_id = str(uuid4())
        field = self._dict_field_to_grid(initial_concentration)
        payload = {
            "field": field,
            "diffusion_coefficient": diffusion_coefficient,
            "steps": max(1, min(200, int(time_steps))),
            "dt": 0.1,
        }
        try:
            result = await self._post("/physics/diffusion", payload)
            return {"simulation_id": simulation_id, **result}
        except Exception:
            arr = np.array(field, dtype=np.float32)
            for _ in range(payload["steps"]):
                arr = arr + (diffusion_coefficient * payload["dt"]) * self._laplacian(arr)
            return {
                "simulation_id": simulation_id,
                "status": "completed_cpu_fallback",
                "final_field": arr.tolist(),
                "diffusion_coefficient": diffusion_coefficient,
                "time_steps": payload["steps"],
            }

    async def simulate_electrical_network(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        sources: Dict[str, float],
    ) -> Dict[str, Any]:
        node_ids = [str(n.get("id")) for n in nodes]
        edge_count = max(len(edges), 1)
        source_vector = [float(sources.get(node_id, 0.0)) for node_id in node_ids]
        weights = []
        for idx, _ in enumerate(node_ids):
            row = [0.0] * len(node_ids)
            row[idx] = 1.0 + (edge_count / max(len(node_ids), 1))
            weights.append(row)

        payload = {"input_vector": source_vector, "weight_matrix": weights, "activation": "tanh"}
        try:
            result = await self._post("/physics/neural-operator", payload)
            voltages = {
                node_id: result["output_vector"][i]
                for i, node_id in enumerate(node_ids)
            }
        except Exception:
            # Ohmic fallback solved as diagonal network.
            voltages = {
                node_id: source_vector[i] / max(weights[i][i], 1e-6)
                for i, node_id in enumerate(node_ids)
            }

        currents: Dict[str, float] = {}
        for edge in edges:
            src = str(edge.get("source"))
            dst = str(edge.get("target"))
            resistance = float(edge.get("resistance", 1.0))
            if src in voltages and dst in voltages:
                currents[f"{src}->{dst}"] = (voltages[src] - voltages[dst]) / max(resistance, 1e-6)

        power = sum((amp ** 2) for amp in currents.values())
        return {"voltages": voltages, "currents": currents, "power_dissipated": power}

    async def simulate_heat_transfer(
        self,
        geometry: Dict[str, Any],
        boundary_conditions: Dict[str, float],
        time_seconds: float,
    ) -> Dict[str, Any]:
        simulation_id = str(uuid4())
        width = int(geometry.get("width", 32))
        height = int(geometry.get("height", 32))
        initial = float(boundary_conditions.get("ambient", 20.0))
        field = np.full((height, width), initial, dtype=np.float32)
        if "top" in boundary_conditions:
            field[0, :] = float(boundary_conditions["top"])
        if "bottom" in boundary_conditions:
            field[-1, :] = float(boundary_conditions["bottom"])
        if "left" in boundary_conditions:
            field[:, 0] = float(boundary_conditions["left"])
        if "right" in boundary_conditions:
            field[:, -1] = float(boundary_conditions["right"])

        payload = {
            "temperature_field": field.tolist(),
            "thermal_diffusivity": float(geometry.get("thermal_diffusivity", 0.01)),
            "dt": float(min(0.2, max(0.01, time_seconds / 100.0))),
            "steps": int(max(1, min(200, round(time_seconds)))),
        }
        try:
            result = await self._post("/physics/heat-transfer", payload)
            return {"simulation_id": simulation_id, "steady_state": False, **result}
        except Exception:
            arr = np.array(payload["temperature_field"], dtype=np.float32)
            for _ in range(payload["steps"]):
                arr = arr + (payload["thermal_diffusivity"] * payload["dt"]) * self._laplacian(arr)
            return {
                "simulation_id": simulation_id,
                "temperature_field": arr.tolist(),
                "steady_state": False,
                "max_temperature": float(arr.max()),
            }

    async def simulate_fluid_flow(
        self,
        geometry: Dict[str, Any],
        inlet_velocity: float,
        viscosity: float,
    ) -> Dict[str, Any]:
        simulation_id = str(uuid4())
        width = int(geometry.get("width", 32))
        height = int(geometry.get("height", 32))
        u = np.zeros((height, width), dtype=np.float32)
        v = np.zeros((height, width), dtype=np.float32)
        u[:, 0] = float(inlet_velocity)

        payload = {
            "velocity_u": u.tolist(),
            "velocity_v": v.tolist(),
            "viscosity": float(viscosity),
            "dt": 0.05,
            "steps": int(max(5, min(200, geometry.get("steps", 30)))),
        }
        try:
            result = await self._post("/physics/fluid-flow", payload)
            return {
                "simulation_id": simulation_id,
                "velocity_field": result.get("velocity_u", []),
                "pressure_field": result.get("pressure_field", []),
                "reynolds_number": result.get("reynolds_number_proxy", 0.0),
            }
        except Exception:
            for _ in range(payload["steps"]):
                u = u + (viscosity * payload["dt"]) * self._laplacian(u)
                v = v + (viscosity * payload["dt"]) * self._laplacian(v)
            pressure = -(u + v)
            reynolds = float(np.mean(np.sqrt(u * u + v * v)) / max(viscosity, 1e-6))
            return {
                "simulation_id": simulation_id,
                "velocity_field": u.tolist(),
                "pressure_field": pressure.tolist(),
                "reynolds_number": reynolds,
            }

    async def simulate_reaction_diffusion(
        self,
        concentrations: Dict[str, float],
        rate_constants: Dict[str, float],
        steps: int = 30,
    ) -> Dict[str, Any]:
        payload = {"concentrations": concentrations, "rate_constants": rate_constants, "steps": int(max(1, min(1000, steps)))}
        try:
            return await self._post("/physics/reaction", payload)
        except Exception:
            local = {k: max(0.0, float(v)) for k, v in concentrations.items()}
            history = {k: [v] for k, v in local.items()}
            dt = 0.1
            for _ in range(payload["steps"]):
                for key in list(local.keys()):
                    decay = rate_constants.get(f"{key}_decay", 0.0) * local[key]
                    growth = rate_constants.get(f"{key}_growth", 0.0)
                    local[key] = max(0.0, local[key] + (growth - decay) * dt)
                    history[key].append(local[key])
            return {"status": "completed_cpu_fallback", "final_concentrations": local, "history": history}

    async def simulate_growth_physics(self, nutrient_field: Dict[Tuple[int, int], float], diffusion_coefficient: float) -> Dict[str, Any]:
        return await self.simulate_diffusion(nutrient_field, diffusion_coefficient=diffusion_coefficient, time_steps=20)
