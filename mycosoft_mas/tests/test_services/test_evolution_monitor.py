import pytest
import asyncio
from datetime import datetime
from mycosoft_mas.services.evolution_monitor import EvolutionMonitor
from mycosoft_mas.services.exceptions import EvolutionMonitorError

class TestEvolutionMonitor:
    @pytest.fixture
    async def monitor(self):
        monitor = EvolutionMonitor()
        yield monitor
        await monitor.clear_updates()

    @pytest.mark.asyncio
    async def test_check_for_updates(self, monitor):
        updates = await monitor.check_for_updates()
        assert isinstance(updates, dict)
        assert "new_technologies" in updates
        assert "evolution_alerts" in updates
        assert "system_updates" in updates

    @pytest.mark.asyncio
    async def test_new_technology_detection(self, monitor):
        # Simulate new technology detection
        updates = await monitor.check_for_updates()
        assert isinstance(updates["new_technologies"], list)
        
        # Verify technology structure
        if updates["new_technologies"]:
            tech = updates["new_technologies"][0]
            assert "name" in tech
            assert "version" in tech
            assert "description" in tech
            assert "impact" in tech

    @pytest.mark.asyncio
    async def test_evolution_alerts(self, monitor):
        # Simulate evolution alerts
        updates = await monitor.check_for_updates()
        assert isinstance(updates["evolution_alerts"], list)
        
        # Verify alert structure
        if updates["evolution_alerts"]:
            alert = updates["evolution_alerts"][0]
            assert "type" in alert
            assert "message" in alert
            assert "severity" in alert

    @pytest.mark.asyncio
    async def test_system_updates(self, monitor):
        # Simulate system updates
        updates = await monitor.check_for_updates()
        assert isinstance(updates["system_updates"], list)
        
        # Verify update structure
        if updates["system_updates"]:
            update = updates["system_updates"][0]
            assert "type" in update
            assert "details" in update
            assert "priority" in update

    @pytest.mark.asyncio
    async def test_get_status(self, monitor):
        status = monitor.get_status()
        assert isinstance(status, dict)
        assert "last_check" in status
        assert "updates_found" in status
        assert "alerts_generated" in status
        assert "processing_time" in status
        assert "error_count" in status

    @pytest.mark.asyncio
    async def test_clear_updates(self, monitor):
        # First check for updates
        await monitor.check_for_updates()
        
        # Clear updates
        await monitor.clear_updates()
        
        # Verify updates are cleared
        status = monitor.get_status()
        assert status["updates_found"] == 0
        assert status["alerts_generated"] == 0

    @pytest.mark.asyncio
    async def test_error_handling(self, monitor):
        # Test error handling for invalid check interval
        with pytest.raises(EvolutionMonitorError):
            monitor.check_interval = -1
            await monitor.check_for_updates()

    @pytest.mark.asyncio
    async def test_concurrent_checks(self, monitor):
        # Test concurrent update checks
        tasks = [
            monitor.check_for_updates() for _ in range(5)
        ]
        results = await asyncio.gather(*tasks)
        assert len(results) == 5
        assert all(isinstance(r, dict) for r in results)

    @pytest.mark.asyncio
    async def test_alert_thresholds(self, monitor):
        # Test different alert thresholds
        monitor.alert_threshold = "low"
        updates = await monitor.check_for_updates()
        assert isinstance(updates["evolution_alerts"], list)

        monitor.alert_threshold = "high"
        updates = await monitor.check_for_updates()
        assert isinstance(updates["evolution_alerts"], list)

    @pytest.mark.asyncio
    async def test_technology_sources(self, monitor):
        # Test technology source configuration
        monitor.technology_sources = ["pypi", "npm"]
        updates = await monitor.check_for_updates()
        assert isinstance(updates["new_technologies"], list)

    @pytest.mark.asyncio
    async def test_update_processing(self, monitor):
        # Test update processing time
        start_time = datetime.now()
        await monitor.check_for_updates()
        end_time = datetime.now()
        
        status = monitor.get_status()
        assert status["processing_time"] >= 0
        assert (end_time - start_time).total_seconds() >= status["processing_time"]

    @pytest.mark.asyncio
    async def test_error_counting(self, monitor):
        # Test error counting
        initial_errors = monitor.get_status()["error_count"]
        
        # Simulate an error
        monitor.check_interval = -1
        try:
            await monitor.check_for_updates()
        except EvolutionMonitorError:
            pass
            
        assert monitor.get_status()["error_count"] == initial_errors + 1 