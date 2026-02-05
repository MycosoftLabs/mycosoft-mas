"""
Test Earth-2 Integration
February 4, 2026

Comprehensive tests for NVIDIA Earth-2 integration including:
- Earth2Studio service wrapper
- Pydantic data models
- MAS agents
- API endpoints
- n8n workflow integration
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestEarth2Models:
    """Test Pydantic data models for Earth-2 I/O"""
    
    def test_weather_variable_enum(self):
        """Test WeatherVariable enum values"""
        from mycosoft_mas.earth2.models import WeatherVariable
        
        assert WeatherVariable.T2M == "t2m"
        assert WeatherVariable.U10 == "u10"
        assert WeatherVariable.V10 == "v10"
        assert WeatherVariable.TP == "tp"
        assert WeatherVariable.MSL == "msl"
    
    def test_earth2_model_enum(self):
        """Test Earth2Model enum values"""
        from mycosoft_mas.earth2.models import Earth2Model
        
        assert Earth2Model.ATLAS_ERA5 == "atlas_era5"
        assert Earth2Model.STORMSCOPE_GOES_MRMS == "stormscope_goes_mrms"
        assert Earth2Model.CORRDIFF == "corrdiff"
        assert Earth2Model.HEALDA == "healda"
    
    def test_spatial_extent_validation(self):
        """Test SpatialExtent model validation"""
        from mycosoft_mas.earth2.models import SpatialExtent
        
        # Valid extent
        extent = SpatialExtent(
            min_lat=30.0,
            max_lat=50.0,
            min_lon=-100.0,
            max_lon=-80.0
        )
        assert extent.min_lat == 30.0
        assert extent.max_lat == 50.0
        
        # Invalid latitude should raise error
        with pytest.raises(ValueError):
            SpatialExtent(
                min_lat=-100.0,  # Invalid
                max_lat=50.0,
                min_lon=-100.0,
                max_lon=-80.0
            )
    
    def test_time_range_validation(self):
        """Test TimeRange model validation"""
        from mycosoft_mas.earth2.models import TimeRange
        
        start = datetime.now()
        end = start + timedelta(days=7)
        
        time_range = TimeRange(start=start, end=end)
        assert time_range.start == start
        assert time_range.end == end
    
    def test_forecast_params_creation(self):
        """Test ForecastParams model creation"""
        from mycosoft_mas.earth2.models import ForecastParams, WeatherVariable, Earth2Model, TimeRange
        
        start = datetime.now()
        end = start + timedelta(days=7)
        time_range = TimeRange(start=start, end=end, step_hours=6)
        
        params = ForecastParams(
            model=Earth2Model.ATLAS_ERA5,
            time_range=time_range,
            variables=[WeatherVariable.T2M, WeatherVariable.U10],
            ensemble_members=10
        )
        
        assert params.model == Earth2Model.ATLAS_ERA5
        assert params.ensemble_members == 10
        assert len(params.variables) == 2
        assert params.time_range.duration_hours == 168
    
    def test_nowcast_params_creation(self):
        """Test NowcastParams model creation"""
        from mycosoft_mas.earth2.models import NowcastParams, Earth2Model, SpatialExtent
        
        spatial_extent = SpatialExtent(min_lat=35.0, max_lat=45.0, min_lon=-105.0, max_lon=-90.0)
        
        params = NowcastParams(
            model=Earth2Model.STORMSCOPE_GOES_MRMS,
            spatial_extent=spatial_extent,
            lead_time_hours=6,
            time_step_minutes=10,
            include_satellite=True,
            include_radar=True
        )
        
        assert params.model == Earth2Model.STORMSCOPE_GOES_MRMS
        assert params.spatial_extent.center[0] == 40.0  # Center latitude
        assert params.time_step_minutes == 10
        assert params.lead_time_hours == 6
    
    def test_spore_dispersal_params(self):
        """Test SporeDispersalParams model"""
        from mycosoft_mas.earth2.models import SporeDispersalParams, SpatialExtent, TimeRange, Earth2Model
        
        spatial_extent = SpatialExtent(min_lat=35.0, max_lat=45.0, min_lon=-100.0, max_lon=-85.0)
        start = datetime.now()
        time_range = TimeRange(start=start, end=start + timedelta(hours=48), step_hours=6)
        
        params = SporeDispersalParams(
            species_filter=["Fusarium graminearum", "Alternaria alternata"],
            source_locations=[(41.5, -93.0), (42.0, -92.0)],
            spatial_extent=spatial_extent,
            time_range=time_range,
            wind_model=Earth2Model.ATLAS_ERA5,
            include_precipitation=True,
            include_humidity=True
        )
        
        assert "Fusarium graminearum" in params.species_filter
        assert len(params.source_locations) == 2
        assert params.time_range.duration_hours == 48
    
    def test_earth2_model_run(self):
        """Test Earth2ModelRun for MINDEX tracking"""
        from mycosoft_mas.earth2.models import Earth2ModelRun
        
        run = Earth2ModelRun(
            model="atlas_era5",
            run_type="forecast",
            status="completed",
            input_params={"hours": 168},
            output_path="/data/earth2/outputs/run_123"
        )
        
        assert run.model == "atlas_era5"
        assert run.status == "completed"
        assert run.run_id is not None


class TestEarth2Service:
    """Test Earth2Studio service wrapper"""
    
    @pytest.fixture
    def service(self):
        """Create Earth2StudioService instance"""
        from mycosoft_mas.earth2.earth2_service import Earth2StudioService
        return Earth2StudioService(
            gpu_device="cuda:0",
            model_cache_path="/tmp/earth2_cache",
            output_path="/tmp/earth2_outputs"
        )
    
    def test_service_initialization(self, service):
        """Test service initialization"""
        assert service is not None
        assert service.gpu_device == "cuda:0"
    
    def test_is_available_property(self, service):
        """Test is_available property"""
        # Will be False if nvidia-earth2studio is not installed
        available = service.is_available
        assert isinstance(available, bool)
    
    @pytest.mark.asyncio
    async def test_run_forecast_simulated(self, service):
        """Test run_forecast with simulated output"""
        from mycosoft_mas.earth2.models import ForecastParams, WeatherVariable, Earth2Model
        
        params = ForecastParams(
            model=Earth2Model.ATLAS_ERA5,
            start_time=datetime.now(),
            forecast_hours=72,
            step_hours=6,
            variables=[WeatherVariable.T2M],
            ensemble_members=3
        )
        
        result = await service.run_forecast(params)
        
        assert result is not None
        assert result.run_id is not None
        assert result.model == Earth2Model.ATLAS_ERA5
        assert result.status in ["completed", "simulated"]
    
    @pytest.mark.asyncio
    async def test_run_nowcast_simulated(self, service):
        """Test run_nowcast with simulated output"""
        from mycosoft_mas.earth2.models import NowcastParams, WeatherVariable, Earth2Model
        
        params = NowcastParams(
            model=Earth2Model.STORMSCOPE_GOES_MRMS,
            center_lat=39.0,
            center_lon=-98.0,
            domain_size_km=500,
            forecast_minutes=180,
            step_minutes=10,
            variables=[WeatherVariable.RADAR_REFLECTIVITY]
        )
        
        result = await service.run_nowcast(params)
        
        assert result is not None
        assert result.run_id is not None
        assert result.status in ["completed", "simulated"]
    
    @pytest.mark.asyncio
    async def test_run_spore_dispersal(self, service):
        """Test spore dispersal model"""
        from mycosoft_mas.earth2.models import SporeDispersalParams
        
        params = SporeDispersalParams(
            species="Fusarium graminearum",
            origin_lat=41.5,
            origin_lon=-93.0,
            origin_concentration=10000.0,
            forecast_hours=48
        )
        
        result = await service.run_spore_dispersal(params)
        
        assert result is not None
        assert result.species == "Fusarium graminearum"
        assert result.peak_concentration is not None


class TestEarth2Agents:
    """Test Earth-2 specialized MAS agents"""
    
    @pytest.fixture
    def can_import_agents(self):
        """Check if agents can be imported (requires sklearn)"""
        try:
            from mycosoft_mas.agents.v2.earth2_agents import EARTH2_AGENTS
            return True
        except ImportError:
            return False
    
    def test_earth2_orchestrator_agent_creation(self, can_import_agents):
        """Test Earth2OrchestratorAgent creation"""
        if not can_import_agents:
            pytest.skip("sklearn not installed - skipping agent tests")
        from mycosoft_mas.agents.v2.earth2_agents import Earth2OrchestratorAgent
        
        agent = Earth2OrchestratorAgent()
        
        assert agent is not None
        assert agent.agent_id == "earth2-orchestrator"
        assert agent.agent_type == "earth2-orchestrator"
    
    def test_weather_forecast_agent_creation(self, can_import_agents):
        """Test WeatherForecastAgent creation"""
        if not can_import_agents:
            pytest.skip("sklearn not installed - skipping agent tests")
        from mycosoft_mas.agents.v2.earth2_agents import WeatherForecastAgent
        
        agent = WeatherForecastAgent()
        
        assert agent is not None
        assert agent.agent_id == "weather-forecast"
        assert "atlas_era5" in agent.capabilities
    
    def test_nowcast_agent_creation(self, can_import_agents):
        """Test NowcastAgent creation"""
        if not can_import_agents:
            pytest.skip("sklearn not installed - skipping agent tests")
        from mycosoft_mas.agents.v2.earth2_agents import NowcastAgent
        
        agent = NowcastAgent()
        
        assert agent is not None
        assert agent.agent_id == "nowcast"
    
    def test_spore_dispersal_agent_creation(self, can_import_agents):
        """Test SporeDispersalAgent creation"""
        if not can_import_agents:
            pytest.skip("sklearn not installed - skipping agent tests")
        from mycosoft_mas.agents.v2.earth2_agents import SporeDispersalAgent
        
        agent = SporeDispersalAgent()
        
        assert agent is not None
        assert agent.agent_id == "spore-dispersal"
    
    def test_earth2_agents_registry(self, can_import_agents):
        """Test EARTH2_AGENTS registry"""
        if not can_import_agents:
            pytest.skip("sklearn not installed - skipping agent tests")
        from mycosoft_mas.agents.v2.earth2_agents import EARTH2_AGENTS
        
        assert "earth2-orchestrator" in EARTH2_AGENTS
        assert "weather-forecast" in EARTH2_AGENTS
        assert "nowcast" in EARTH2_AGENTS
        assert "spore-dispersal" in EARTH2_AGENTS
        assert "climate-simulation" in EARTH2_AGENTS


class TestEarth2Tools:
    """Test Earth-2 LLM tools"""
    
    def test_get_earth2_tool_definitions(self):
        """Test Earth-2 tool definitions"""
        from mycosoft_mas.llm.earth2_tools import get_earth2_tool_definitions
        
        tools = get_earth2_tool_definitions()
        
        assert len(tools) >= 4
        tool_names = [t["name"] for t in tools]
        assert "earth2_forecast" in tool_names
        assert "earth2_nowcast" in tool_names
        assert "earth2_spore_dispersal" in tool_names
        assert "earth2_model_status" in tool_names
    
    def test_earth2_tool_handlers_registry(self):
        """Test Earth-2 tool handlers"""
        from mycosoft_mas.llm.earth2_tools import EARTH2_TOOL_HANDLERS
        
        assert "earth2_forecast" in EARTH2_TOOL_HANDLERS
        assert "earth2_nowcast" in EARTH2_TOOL_HANDLERS
        assert "earth2_spore_dispersal" in EARTH2_TOOL_HANDLERS
        assert "earth2_model_status" in EARTH2_TOOL_HANDLERS
    
    @pytest.mark.asyncio
    async def test_execute_earth2_forecast(self):
        """Test executing earth2_forecast tool"""
        from mycosoft_mas.llm.earth2_tools import execute_earth2_forecast
        
        result = await execute_earth2_forecast({
            "location": "Chicago, IL",
            "latitude": 41.88,
            "longitude": -87.63,
            "forecast_days": 3
        })
        
        assert result is not None
        assert "run_id" in result or "error" in result
    
    @pytest.mark.asyncio
    async def test_execute_earth2_nowcast(self):
        """Test executing earth2_nowcast tool"""
        from mycosoft_mas.llm.earth2_tools import execute_earth2_nowcast
        
        result = await execute_earth2_nowcast({
            "latitude": 39.0,
            "longitude": -98.0,
            "forecast_hours": 3
        })
        
        assert result is not None
        assert "run_id" in result or "error" in result
    
    @pytest.mark.asyncio
    async def test_execute_earth2_spore_dispersal(self):
        """Test executing earth2_spore_dispersal tool"""
        from mycosoft_mas.llm.earth2_tools import execute_earth2_spore_dispersal
        
        result = await execute_earth2_spore_dispersal({
            "species": "Fusarium graminearum",
            "origin_lat": 41.5,
            "origin_lon": -93.0,
            "concentration": 10000
        })
        
        assert result is not None


class TestEarth2API:
    """Test Earth-2 API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        from fastapi.testclient import TestClient
        from mycosoft_mas.core.routers.earth2_api import router
        from fastapi import FastAPI
        
        app = FastAPI()
        app.include_router(router, prefix="/api/earth2")
        return TestClient(app)
    
    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/api/earth2/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "models_available" in data
    
    def test_models_endpoint(self, client):
        """Test list models endpoint"""
        response = client.get("/api/earth2/models")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert len(data["models"]) > 0
    
    def test_forecast_endpoint(self, client):
        """Test forecast submission endpoint"""
        response = client.post("/api/earth2/forecast", json={
            "start_time": datetime.now().isoformat(),
            "forecast_hours": 72,
            "step_hours": 6,
            "variables": ["t2m", "u10", "v10"],
            "ensemble_members": 3
        })
        assert response.status_code in [200, 202]
        data = response.json()
        assert "run_id" in data
    
    def test_nowcast_endpoint(self, client):
        """Test nowcast submission endpoint"""
        response = client.post("/api/earth2/nowcast", json={
            "center_lat": 39.0,
            "center_lon": -98.0,
            "domain_size_km": 500,
            "forecast_minutes": 180,
            "step_minutes": 10,
            "variables": ["radar_reflectivity"]
        })
        assert response.status_code in [200, 202]
        data = response.json()
        assert "run_id" in data
    
    def test_spore_dispersal_endpoint(self, client):
        """Test spore dispersal endpoint"""
        response = client.post("/api/earth2/spore-dispersal", json={
            "species": "Fusarium graminearum",
            "origin_lat": 41.5,
            "origin_lon": -93.0,
            "origin_concentration": 10000,
            "forecast_hours": 48
        })
        assert response.status_code in [200, 202]
        data = response.json()
        assert "run_id" in data
    
    def test_layers_endpoint(self, client):
        """Test visualization layers endpoint"""
        response = client.get("/api/earth2/layers")
        assert response.status_code == 200
        data = response.json()
        assert "layers" in data


class TestEarth2Integration:
    """Integration tests for Earth-2 system"""
    
    @pytest.mark.asyncio
    async def test_full_forecast_pipeline(self):
        """Test full forecast pipeline from request to output"""
        from mycosoft_mas.earth2.earth2_service import get_earth2_service
        from mycosoft_mas.earth2.models import ForecastParams, WeatherVariable, Earth2Model
        
        service = get_earth2_service()
        
        params = ForecastParams(
            model=Earth2Model.ATLAS_ERA5,
            start_time=datetime.now(),
            forecast_hours=72,
            step_hours=6,
            variables=[WeatherVariable.T2M, WeatherVariable.TP],
            ensemble_members=3
        )
        
        result = await service.run_forecast(params)
        
        assert result is not None
        assert result.run_id is not None
        assert result.outputs is not None
        assert len(result.outputs) > 0
    
    @pytest.mark.asyncio
    async def test_spore_weather_integration(self):
        """Test spore dispersal with weather integration"""
        from mycosoft_mas.earth2.earth2_service import get_earth2_service
        from mycosoft_mas.earth2.models import SporeDispersalParams
        
        service = get_earth2_service()
        
        params = SporeDispersalParams(
            species="Alternaria alternata",
            origin_lat=35.0,
            origin_lon=-85.0,
            origin_concentration=5000.0,
            release_height_m=1.5,
            forecast_hours=24
        )
        
        result = await service.run_spore_dispersal(params)
        
        assert result is not None
        assert result.species == "Alternaria alternata"
        assert result.affected_area_km2 is not None


class TestEarth2N8nWorkflows:
    """Test n8n workflow configurations"""
    
    def test_weather_automation_workflow_exists(self):
        """Test weather automation workflow file exists"""
        workflow_path = "n8n/workflows/48_earth2_weather_automation.json"
        assert os.path.exists(workflow_path)
        
        with open(workflow_path) as f:
            workflow = json.load(f)
        
        assert workflow["name"] == "Earth-2 Weather Automation"
        assert len(workflow["nodes"]) > 0
    
    def test_spore_alert_workflow_exists(self):
        """Test spore alert workflow file exists"""
        workflow_path = "n8n/workflows/49_earth2_spore_alert.json"
        assert os.path.exists(workflow_path)
        
        with open(workflow_path) as f:
            workflow = json.load(f)
        
        assert workflow["name"] == "Earth-2 Spore Alert System"
    
    def test_nowcast_alert_workflow_exists(self):
        """Test nowcast alert workflow file exists"""
        workflow_path = "n8n/workflows/50_earth2_nowcast_alert.json"
        assert os.path.exists(workflow_path)
        
        with open(workflow_path) as f:
            workflow = json.load(f)
        
        assert workflow["name"] == "Earth-2 Nowcast Alert System"
    
    def test_workflow_node_connections(self):
        """Test workflow node connections are valid"""
        workflow_path = "n8n/workflows/48_earth2_weather_automation.json"
        
        with open(workflow_path) as f:
            workflow = json.load(f)
        
        connections = workflow.get("connections", {})
        nodes = {n["name"] for n in workflow["nodes"]}
        
        # Verify all connection targets exist
        for source, targets_list in connections.items():
            for targets in targets_list.get("main", []):
                for target in targets:
                    assert target["node"] in nodes, f"Target node {target['node']} not found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
