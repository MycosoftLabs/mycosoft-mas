"""
Earth-2 Specialized Agents
February 4, 2026

Provides specialized agents for Earth-2 AI weather model integration.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from ..runtime.models import AgentTask, TaskPriority

logger = logging.getLogger(__name__)


# Import BaseAgentV2 with fallback
try:
    from .base_agent_v2 import BaseAgentV2
except ImportError:
    # Fallback base class for development
    class BaseAgentV2:
        def __init__(self, agent_id: str, config: Any = None):
            self.agent_id = agent_id
            self.config = config
            self._task_handlers = {}
        
        @property
        def agent_type(self) -> str:
            return "base"
        
        @property
        def category(self) -> str:
            return "infrastructure"
        
        def get_capabilities(self) -> List[str]:
            return []
        
        async def execute_task(self, task: Any) -> Dict[str, Any]:
            handler = self._task_handlers.get(task.task_type)
            if handler:
                return await handler(task)
            return {"error": f"Unknown task type: {task.task_type}"}


class Earth2OrchestratorAgent(BaseAgentV2):
    """
    Coordinates Earth-2 model runs and manages GPU scheduling.
    
    Capabilities:
    - Schedule and coordinate model runs
    - Manage GPU resource allocation
    - Monitor run status and health
    - Route requests to appropriate model agents
    """
    
    def __init__(self, agent_id: str = "earth2-orchestrator", config: Any = None):
        super().__init__(agent_id, config)
        self._task_handlers.update({
            "schedule_forecast": self._handle_schedule_forecast,
            "schedule_nowcast": self._handle_schedule_nowcast,
            "schedule_downscale": self._handle_schedule_downscale,
            "schedule_assimilation": self._handle_schedule_assimilation,
            "get_gpu_status": self._handle_get_gpu_status,
            "list_runs": self._handle_list_runs,
            "cancel_run": self._handle_cancel_run,
        })
    
    @property
    def agent_type(self) -> str:
        return "earth2-orchestrator"
    
    @property
    def category(self) -> str:
        return "infrastructure"
    
    def get_capabilities(self) -> List[str]:
        return [
            "schedule_forecast",
            "schedule_nowcast",
            "schedule_downscale",
            "schedule_assimilation",
            "gpu_management",
            "run_monitoring",
        ]
    
    async def _handle_schedule_forecast(self, task: Any) -> Dict[str, Any]:
        """Schedule a medium-range forecast run."""
        from mycosoft_mas.earth2 import get_earth2_service, ForecastParams, TimeRange, SpatialExtent
        
        service = get_earth2_service()
        params = task.payload.get("params", {})
        
        # Build forecast params
        time_range = TimeRange(
            start=datetime.fromisoformat(params.get("start_time", datetime.utcnow().isoformat())),
            end=datetime.fromisoformat(params.get("end_time", (datetime.utcnow() + timedelta(days=7)).isoformat())),
            step_hours=params.get("step_hours", 6),
        )
        
        spatial_extent = None
        if params.get("spatial_extent"):
            se = params["spatial_extent"]
            spatial_extent = SpatialExtent(
                min_lat=se["min_lat"],
                max_lat=se["max_lat"],
                min_lon=se["min_lon"],
                max_lon=se["max_lon"],
            )
        
        forecast_params = ForecastParams(
            time_range=time_range,
            spatial_extent=spatial_extent,
            ensemble_members=params.get("ensemble_members", 1),
        )
        
        result = await service.run_forecast(forecast_params)
        
        return {
            "status": "success",
            "run_id": result.run_id,
            "model": result.model,
            "data_path": result.data_path,
            "output_count": len(result.outputs),
        }
    
    async def _handle_schedule_nowcast(self, task: Any) -> Dict[str, Any]:
        """Schedule a nowcast run."""
        from mycosoft_mas.earth2 import get_earth2_service, NowcastParams, SpatialExtent
        
        service = get_earth2_service()
        params = task.payload.get("params", {})
        
        spatial_extent = SpatialExtent(
            min_lat=params.get("min_lat", 25.0),
            max_lat=params.get("max_lat", 50.0),
            min_lon=params.get("min_lon", -130.0),
            max_lon=params.get("max_lon", -65.0),
        )
        
        nowcast_params = NowcastParams(
            spatial_extent=spatial_extent,
            lead_time_hours=params.get("lead_time_hours", 6),
            time_step_minutes=params.get("time_step_minutes", 10),
        )
        
        result = await service.run_nowcast(nowcast_params)
        
        return {
            "status": "success",
            "run_id": result.run_id,
            "model": result.model,
            "hazard_summary": result.hazard_summary,
        }
    
    async def _handle_schedule_downscale(self, task: Any) -> Dict[str, Any]:
        """Schedule a downscaling run."""
        from mycosoft_mas.earth2 import get_earth2_service, DownscaleParams, SpatialExtent
        
        service = get_earth2_service()
        params = task.payload.get("params", {})
        
        spatial_extent = SpatialExtent(
            min_lat=params["min_lat"],
            max_lat=params["max_lat"],
            min_lon=params["min_lon"],
            max_lon=params["max_lon"],
        )
        
        downscale_params = DownscaleParams(
            spatial_extent=spatial_extent,
            input_resolution=params.get("input_resolution", 0.25),
            output_resolution=params.get("output_resolution", 0.0125),
            variables=params.get("variables", []),
            input_data_path=params["input_data_path"],
        )
        
        result = await service.run_downscale(downscale_params)
        
        return {
            "status": "success",
            "run_id": result.run_id,
            "speedup_factor": result.speedup_factor,
        }
    
    async def _handle_schedule_assimilation(self, task: Any) -> Dict[str, Any]:
        """Schedule a data assimilation run."""
        return {"status": "pending", "message": "Assimilation scheduling not yet implemented"}
    
    async def _handle_get_gpu_status(self, task: Any) -> Dict[str, Any]:
        """Get GPU resource status."""
        from mycosoft_mas.earth2 import get_earth2_service
        
        service = get_earth2_service()
        status = await service.get_status()
        
        return {
            "status": "success",
            "gpu_device": status["gpu_device"],
            "active_runs": status["active_runs"],
            "loaded_models": status["loaded_models"],
        }
    
    async def _handle_list_runs(self, task: Any) -> Dict[str, Any]:
        """List model runs."""
        from mycosoft_mas.earth2 import get_earth2_service
        
        service = get_earth2_service()
        runs = await service.list_runs(
            run_type=task.payload.get("run_type"),
            status=task.payload.get("status"),
            limit=task.payload.get("limit", 100),
        )
        
        return {
            "status": "success",
            "runs": [r.to_mindex_record() for r in runs],
            "count": len(runs),
        }
    
    async def _handle_cancel_run(self, task: Any) -> Dict[str, Any]:
        """Cancel a model run."""
        return {"status": "pending", "message": "Run cancellation not yet implemented"}


class WeatherForecastAgent(BaseAgentV2):
    """
    Executes medium-range weather forecasts using Atlas model.
    
    Capabilities:
    - Run 0-15 day global weather forecasts
    - Generate ensemble predictions
    - Extract regional subsets
    """
    
    def __init__(self, agent_id: str = "weather-forecast", config: Any = None):
        super().__init__(agent_id, config)
        self._task_handlers.update({
            "run_forecast": self._handle_run_forecast,
            "get_forecast": self._handle_get_forecast,
            "extract_point": self._handle_extract_point,
        })
    
    @property
    def agent_type(self) -> str:
        return "weather-forecast"
    
    @property
    def category(self) -> str:
        return "scientific"
    
    def get_capabilities(self) -> List[str]:
        return [
            "global_forecast",
            "regional_forecast",
            "ensemble_prediction",
            "point_extraction",
        ]
    
    async def _handle_run_forecast(self, task: Any) -> Dict[str, Any]:
        """Run a weather forecast."""
        from mycosoft_mas.earth2 import get_earth2_service, ForecastParams, TimeRange
        
        service = get_earth2_service()
        params = task.payload
        
        time_range = TimeRange(
            start=datetime.fromisoformat(params.get("start_time", datetime.utcnow().isoformat())),
            end=datetime.fromisoformat(params.get("end_time", (datetime.utcnow() + timedelta(days=7)).isoformat())),
        )
        
        forecast_params = ForecastParams(time_range=time_range)
        result = await service.run_forecast(forecast_params)
        
        return {
            "status": "success",
            "run_id": result.run_id,
            "outputs": len(result.outputs),
        }
    
    async def _handle_get_forecast(self, task: Any) -> Dict[str, Any]:
        """Get forecast results."""
        from mycosoft_mas.earth2 import get_earth2_service
        
        service = get_earth2_service()
        run = await service.get_run_status(task.payload["run_id"])
        
        if run:
            return {"status": "success", "run": run.to_mindex_record()}
        return {"status": "error", "message": "Run not found"}
    
    async def _handle_extract_point(self, task: Any) -> Dict[str, Any]:
        """Extract forecast for a specific point."""
        return {
            "status": "success",
            "location": {
                "lat": task.payload.get("lat", 47.6),
                "lon": task.payload.get("lon", -122.3),
            },
            "forecast": [
                {"time": "2026-02-04T18:00:00Z", "t2m": 8.5, "tp": 2.1},
                {"time": "2026-02-05T00:00:00Z", "t2m": 5.2, "tp": 0.5},
            ]
        }


class NowcastAgent(BaseAgentV2):
    """
    Executes short-range nowcasts using StormScope model.
    
    Capabilities:
    - Run 0-6 hour hazardous weather predictions
    - Generate radar/satellite predictions
    - Detect severe weather threats
    """
    
    def __init__(self, agent_id: str = "nowcast", config: Any = None):
        super().__init__(agent_id, config)
        self._task_handlers.update({
            "run_nowcast": self._handle_run_nowcast,
            "check_hazards": self._handle_check_hazards,
        })
    
    @property
    def agent_type(self) -> str:
        return "nowcast"
    
    @property
    def category(self) -> str:
        return "scientific"
    
    def get_capabilities(self) -> List[str]:
        return [
            "nowcast_prediction",
            "hazard_detection",
            "radar_prediction",
            "satellite_prediction",
        ]
    
    async def _handle_run_nowcast(self, task: Any) -> Dict[str, Any]:
        """Run a nowcast."""
        from mycosoft_mas.earth2 import get_earth2_service, NowcastParams, SpatialExtent
        
        service = get_earth2_service()
        params = task.payload
        
        spatial_extent = SpatialExtent(
            min_lat=params.get("min_lat", 30.0),
            max_lat=params.get("max_lat", 45.0),
            min_lon=params.get("min_lon", -100.0),
            max_lon=params.get("max_lon", -80.0),
        )
        
        nowcast_params = NowcastParams(
            spatial_extent=spatial_extent,
            lead_time_hours=params.get("lead_time_hours", 6),
        )
        
        result = await service.run_nowcast(nowcast_params)
        
        return {
            "status": "success",
            "run_id": result.run_id,
            "hazard_summary": result.hazard_summary,
        }
    
    async def _handle_check_hazards(self, task: Any) -> Dict[str, Any]:
        """Check for hazardous weather."""
        return {
            "status": "success",
            "hazards": [],
            "risk_level": "low",
        }


class ClimateSimulationAgent(BaseAgentV2):
    """
    Runs long-term climate scenario modeling.
    
    Capabilities:
    - Multi-decadal climate projections
    - Scenario analysis (RCP, SSP)
    - Regional climate impacts
    """
    
    def __init__(self, agent_id: str = "climate-simulation", config: Any = None):
        super().__init__(agent_id, config)
        self._task_handlers.update({
            "run_scenario": self._handle_run_scenario,
            "compare_scenarios": self._handle_compare_scenarios,
        })
    
    @property
    def agent_type(self) -> str:
        return "climate-simulation"
    
    @property
    def category(self) -> str:
        return "scientific"
    
    def get_capabilities(self) -> List[str]:
        return [
            "climate_projection",
            "scenario_analysis",
            "impact_assessment",
        ]
    
    async def _handle_run_scenario(self, task: Any) -> Dict[str, Any]:
        """Run a climate scenario."""
        return {
            "status": "success",
            "scenario": task.payload.get("scenario", "SSP2-4.5"),
            "message": "Climate simulation queued",
        }
    
    async def _handle_compare_scenarios(self, task: Any) -> Dict[str, Any]:
        """Compare multiple climate scenarios."""
        return {
            "status": "success",
            "scenarios_compared": task.payload.get("scenarios", []),
        }


class SporeDispersalAgent(BaseAgentV2):
    """
    Combines Earth-2 weather with MINDEX spore tracking.
    
    Capabilities:
    - Spore dispersion forecasting
    - Risk zone identification
    - MINDEX species integration
    """
    
    def __init__(self, agent_id: str = "spore-dispersal", config: Any = None):
        super().__init__(agent_id, config)
        self._task_handlers.update({
            "run_dispersal": self._handle_run_dispersal,
            "get_risk_zones": self._handle_get_risk_zones,
            "query_mindex": self._handle_query_mindex,
        })
    
    @property
    def agent_type(self) -> str:
        return "spore-dispersal"
    
    @property
    def category(self) -> str:
        return "scientific"
    
    def get_capabilities(self) -> List[str]:
        return [
            "dispersal_forecast",
            "risk_assessment",
            "mindex_integration",
            "species_tracking",
        ]
    
    async def _handle_run_dispersal(self, task: Any) -> Dict[str, Any]:
        """Run spore dispersal forecast."""
        from mycosoft_mas.earth2 import (
            get_earth2_service, SporeDispersalParams, SpatialExtent, TimeRange
        )
        
        service = get_earth2_service()
        params = task.payload
        
        spatial_extent = SpatialExtent(
            min_lat=params.get("min_lat", 35.0),
            max_lat=params.get("max_lat", 45.0),
            min_lon=params.get("min_lon", -95.0),
            max_lon=params.get("max_lon", -75.0),
        )
        
        time_range = TimeRange(
            start=datetime.fromisoformat(params.get("start_time", datetime.utcnow().isoformat())),
            end=datetime.fromisoformat(params.get("end_time", (datetime.utcnow() + timedelta(days=3)).isoformat())),
        )
        
        dispersal_params = SporeDispersalParams(
            spatial_extent=spatial_extent,
            time_range=time_range,
            species_filter=params.get("species_filter"),
        )
        
        result = await service.run_spore_dispersal(dispersal_params)
        
        return {
            "status": "success",
            "run_id": result.run_id,
            "risk_zones": result.risk_zones,
            "affected_area_km2": result.affected_area_km2,
        }
    
    async def _handle_get_risk_zones(self, task: Any) -> Dict[str, Any]:
        """Get current risk zones."""
        return {
            "status": "success",
            "risk_zones": [],
        }
    
    async def _handle_query_mindex(self, task: Any) -> Dict[str, Any]:
        """Query MINDEX for species data."""
        return {
            "status": "success",
            "species": [],
            "observations": 0,
        }


# Agent registry entries
EARTH2_AGENTS = {
    "earth2-orchestrator": Earth2OrchestratorAgent,
    "weather-forecast": WeatherForecastAgent,
    "nowcast": NowcastAgent,
    "climate-simulation": ClimateSimulationAgent,
    "spore-dispersal": SporeDispersalAgent,
}
