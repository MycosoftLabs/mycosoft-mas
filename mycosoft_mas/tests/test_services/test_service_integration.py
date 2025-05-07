import pytest
import asyncio
from mycosoft_mas.services import EvolutionMonitor, SecurityMonitor, TechnologyTracker
from mycosoft_mas.services.exceptions import ServiceIntegrationError

class TestServiceIntegration:
    @pytest.fixture
    async def services(self):
        evolution = EvolutionMonitor()
        security = SecurityMonitor()
        tracker = TechnologyTracker()
        yield evolution, security, tracker
        await evolution.clear_updates()
        await security.clear_alerts()
        await tracker.clear_updates()

    @pytest.mark.asyncio
    async def test_evolution_security_integration(self, services):
        evolution, security, _ = services
        
        # Check for updates
        evolution_updates = await evolution.check_for_updates()
        
        # Verify security implications
        security_issues = await security.check_security()
        
        # Check if any evolution updates have security implications
        if evolution_updates["new_technologies"]:
            for tech in evolution_updates["new_technologies"]:
                assert "security_implications" in tech
                if tech["security_implications"]:
                    assert any(
                        vuln["package"] == tech["name"]
                        for vuln in security_issues["vulnerabilities"]
                    )

    @pytest.mark.asyncio
    async def test_security_technology_integration(self, services):
        _, security, tracker = services
        
        # Check for security issues
        security_issues = await security.check_security()
        
        # Register affected technologies
        if security_issues["vulnerabilities"]:
            for vuln in security_issues["vulnerabilities"]:
                await tracker.register_technology(
                    name=vuln["package"],
                    version=vuln["version"],
                    description=f"Technology with security vulnerability: {vuln['description']}",
                    status="vulnerable"
                )
                
                # Verify technology status
                tech_info = await tracker.get_technology(vuln["package"])
                assert tech_info["status"] == "vulnerable"

    @pytest.mark.asyncio
    async def test_evolution_technology_integration(self, services):
        evolution, _, tracker = services
        
        # Check for new technologies
        evolution_updates = await evolution.check_for_updates()
        
        # Register new technologies
        if evolution_updates["new_technologies"]:
            for tech in evolution_updates["new_technologies"]:
                await tracker.register_technology(
                    name=tech["name"],
                    version=tech["version"],
                    description=tech["description"],
                    status="new"
                )
                
                # Verify technology registration
                tech_info = await tracker.get_technology(tech["name"])
                assert tech_info["status"] == "new"
                assert tech_info["version"] == tech["version"]

    @pytest.mark.asyncio
    async def test_service_status_synchronization(self, services):
        evolution, security, tracker = services
        
        # Get initial status
        evolution_status = evolution.get_status()
        security_status = security.get_status()
        tracker_status = tracker.get_status()
        
        # Perform operations
        await evolution.check_for_updates()
        await security.check_security()
        await tracker.check_new_technologies()
        
        # Verify status updates
        assert evolution.get_status()["last_check"] != evolution_status["last_check"]
        assert security.get_status()["last_check"] != security_status["last_check"]
        assert tracker.get_status()["last_check"] != tracker_status["last_check"]

    @pytest.mark.asyncio
    async def test_concurrent_service_operations(self, services):
        evolution, security, tracker = services
        
        # Perform concurrent operations
        tasks = [
            evolution.check_for_updates(),
            security.check_security(),
            tracker.check_new_technologies()
        ]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        assert all(isinstance(r, dict) for r in results)

    @pytest.mark.asyncio
    async def test_service_error_propagation(self, services):
        evolution, security, tracker = services
        
        # Simulate errors in services
        evolution.check_interval = -1
        security.check_interval = -1
        tracker.update_interval = -1
        
        with pytest.raises(ServiceIntegrationError):
            await asyncio.gather(
                evolution.check_for_updates(),
                security.check_security(),
                tracker.check_new_technologies()
            )

    @pytest.mark.asyncio
    async def test_service_configuration_synchronization(self, services):
        evolution, security, tracker = services
        
        # Update configurations
        evolution.alert_threshold = "high"
        security.severity_threshold = "critical"
        tracker.tracking_level = "detailed"
        
        # Verify configuration updates
        assert evolution.alert_threshold == "high"
        assert security.severity_threshold == "critical"
        assert tracker.tracking_level == "detailed"

    @pytest.mark.asyncio
    async def test_service_data_consistency(self, services):
        evolution, security, tracker = services
        
        # Register a technology
        await tracker.register_technology(
            name="test-tech",
            version="1.0.0",
            description="Test technology"
        )
        
        # Check for updates and security
        evolution_updates = await evolution.check_for_updates()
        security_issues = await security.check_security()
        
        # Verify data consistency
        tech_info = await tracker.get_technology("test-tech")
        assert tech_info["name"] == "test-tech"
        assert tech_info["version"] == "1.0.0"
        
        # Check if technology appears in evolution updates
        assert any(
            tech["name"] == "test-tech"
            for tech in evolution_updates["new_technologies"]
        )
        
        # Check if technology appears in security issues
        assert any(
            vuln["package"] == "test-tech"
            for vuln in security_issues["vulnerabilities"]
        )

    @pytest.mark.asyncio
    async def test_service_cleanup_coordination(self, services):
        evolution, security, tracker = services
        
        # Perform operations
        await evolution.check_for_updates()
        await security.check_security()
        await tracker.check_new_technologies()
        
        # Clear all updates
        await evolution.clear_updates()
        await security.clear_alerts()
        await tracker.clear_updates()
        
        # Verify cleanup
        assert evolution.get_status()["updates_found"] == 0
        assert security.get_status()["vulnerabilities_found"] == 0
        assert tracker.get_status()["technologies_registered"] == 0

    @pytest.mark.asyncio
    async def test_service_metrics_aggregation(self, services):
        evolution, security, tracker = services
        
        # Get individual service metrics
        evolution_metrics = evolution.get_status()
        security_metrics = security.get_status()
        tracker_metrics = tracker.get_status()
        
        # Verify metrics structure
        assert "processing_time" in evolution_metrics
        assert "processing_time" in security_metrics
        assert "processing_time" in tracker_metrics
        
        # Verify metrics values
        assert evolution_metrics["processing_time"] >= 0
        assert security_metrics["processing_time"] >= 0
        assert tracker_metrics["processing_time"] >= 0 