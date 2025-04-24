import pytest
import asyncio
from datetime import datetime
from mycosoft_mas.services.technology_tracker import TechnologyTracker
from mycosoft_mas.services.exceptions import TechnologyTrackerError

class TestTechnologyTracker:
    @pytest.fixture
    async def tracker(self):
        tracker = TechnologyTracker()
        yield tracker
        await tracker.clear_updates()

    @pytest.mark.asyncio
    async def test_register_technology(self, tracker):
        # Register a new technology
        await tracker.register_technology(
            name="test-tech",
            version="1.0.0",
            description="Test technology",
            capabilities=["test1", "test2"]
        )
        
        # Verify registration
        tech_info = await tracker.get_technology("test-tech")
        assert tech_info["name"] == "test-tech"
        assert tech_info["version"] == "1.0.0"
        assert tech_info["description"] == "Test technology"
        assert tech_info["capabilities"] == ["test1", "test2"]

    @pytest.mark.asyncio
    async def test_update_technology(self, tracker):
        # First register a technology
        await tracker.register_technology(
            name="test-tech",
            version="1.0.0",
            description="Test technology"
        )
        
        # Update the technology
        await tracker.update_technology(
            name="test-tech",
            version="2.0.0",
            description="Updated technology"
        )
        
        # Verify update
        tech_info = await tracker.get_technology("test-tech")
        assert tech_info["version"] == "2.0.0"
        assert tech_info["description"] == "Updated technology"

    @pytest.mark.asyncio
    async def test_get_technology(self, tracker):
        # Register a technology
        await tracker.register_technology(
            name="test-tech",
            version="1.0.0",
            description="Test technology"
        )
        
        # Get technology information
        tech_info = await tracker.get_technology("test-tech")
        assert isinstance(tech_info, dict)
        assert "name" in tech_info
        assert "version" in tech_info
        assert "description" in tech_info
        assert "status" in tech_info

    @pytest.mark.asyncio
    async def test_check_new_technologies(self, tracker):
        # Check for new technologies
        new_techs = await tracker.check_new_technologies()
        assert isinstance(new_techs, list)
        
        # Verify technology structure
        if new_techs:
            tech = new_techs[0]
            assert "name" in tech
            assert "version" in tech
            assert "description" in tech

    @pytest.mark.asyncio
    async def test_check_technology_alerts(self, tracker):
        # Check for technology alerts
        alerts = await tracker.check_technology_alerts()
        assert isinstance(alerts, list)
        
        # Verify alert structure
        if alerts:
            alert = alerts[0]
            assert "type" in alert
            assert "message" in alert
            assert "severity" in alert

    @pytest.mark.asyncio
    async def test_get_status(self, tracker):
        status = tracker.get_status()
        assert isinstance(status, dict)
        assert "last_check" in status
        assert "technologies_registered" in status
        assert "alerts_generated" in status
        assert "processing_time" in status
        assert "error_count" in status

    @pytest.mark.asyncio
    async def test_clear_updates(self, tracker):
        # First register a technology
        await tracker.register_technology(
            name="test-tech",
            version="1.0.0",
            description="Test technology"
        )
        
        # Clear updates
        await tracker.clear_updates()
        
        # Verify updates are cleared
        status = tracker.get_status()
        assert status["alerts_generated"] == 0

    @pytest.mark.asyncio
    async def test_error_handling(self, tracker):
        # Test error handling for invalid technology name
        with pytest.raises(TechnologyTrackerError):
            await tracker.register_technology(
                name="",
                version="1.0.0",
                description="Test technology"
            )

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, tracker):
        # Test concurrent technology operations
        tasks = [
            tracker.register_technology(
                name=f"test-tech-{i}",
                version="1.0.0",
                description=f"Test technology {i}"
            ) for i in range(5)
        ]
        results = await asyncio.gather(*tasks)
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_technology_dependencies(self, tracker):
        # Test technology with dependencies
        await tracker.register_technology(
            name="test-tech",
            version="1.0.0",
            description="Test technology",
            dependencies=["dep1", "dep2"]
        )
        
        tech_info = await tracker.get_technology("test-tech")
        assert "dependencies" in tech_info
        assert tech_info["dependencies"] == ["dep1", "dep2"]

    @pytest.mark.asyncio
    async def test_technology_capabilities(self, tracker):
        # Test technology capabilities
        await tracker.register_technology(
            name="test-tech",
            version="1.0.0",
            description="Test technology",
            capabilities=["cap1", "cap2"]
        )
        
        tech_info = await tracker.get_technology("test-tech")
        assert "capabilities" in tech_info
        assert tech_info["capabilities"] == ["cap1", "cap2"]

    @pytest.mark.asyncio
    async def test_technology_status(self, tracker):
        # Test technology status
        await tracker.register_technology(
            name="test-tech",
            version="1.0.0",
            description="Test technology",
            status="active"
        )
        
        tech_info = await tracker.get_technology("test-tech")
        assert "status" in tech_info
        assert tech_info["status"] == "active"

    @pytest.mark.asyncio
    async def test_technology_metadata(self, tracker):
        # Test technology metadata
        metadata = {
            "author": "Test Author",
            "license": "MIT",
            "repository": "https://github.com/test/tech"
        }
        
        await tracker.register_technology(
            name="test-tech",
            version="1.0.0",
            description="Test technology",
            metadata=metadata
        )
        
        tech_info = await tracker.get_technology("test-tech")
        assert "metadata" in tech_info
        assert tech_info["metadata"] == metadata

    @pytest.mark.asyncio
    async def test_technology_versioning(self, tracker):
        # Test technology versioning
        await tracker.register_technology(
            name="test-tech",
            version="1.0.0",
            description="Test technology"
        )
        
        # Update version
        await tracker.update_technology(
            name="test-tech",
            version="2.0.0"
        )
        
        tech_info = await tracker.get_technology("test-tech")
        assert tech_info["version"] == "2.0.0"

    @pytest.mark.asyncio
    async def test_technology_compatibility(self, tracker):
        # Test technology compatibility
        await tracker.register_technology(
            name="test-tech",
            version="1.0.0",
            description="Test technology",
            compatibility={
                "python": ">=3.8",
                "os": ["linux", "windows"]
            }
        )
        
        tech_info = await tracker.get_technology("test-tech")
        assert "compatibility" in tech_info
        assert "python" in tech_info["compatibility"]
        assert "os" in tech_info["compatibility"] 