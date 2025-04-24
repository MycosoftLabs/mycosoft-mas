import pytest
import asyncio
from datetime import datetime
from mycosoft_mas.services.security_monitor import SecurityMonitor
from mycosoft_mas.services.exceptions import SecurityMonitorError

class TestSecurityMonitor:
    @pytest.fixture
    async def monitor(self):
        monitor = SecurityMonitor()
        yield monitor
        await monitor.clear_alerts()

    @pytest.mark.asyncio
    async def test_check_security(self, monitor):
        issues = await monitor.check_security()
        assert isinstance(issues, dict)
        assert "vulnerabilities" in issues
        assert "security_alerts" in issues
        assert "security_updates" in issues

    @pytest.mark.asyncio
    async def test_vulnerability_detection(self, monitor):
        # Simulate vulnerability detection
        issues = await monitor.check_security()
        assert isinstance(issues["vulnerabilities"], list)
        
        # Verify vulnerability structure
        if issues["vulnerabilities"]:
            vuln = issues["vulnerabilities"][0]
            assert "package" in vuln
            assert "version" in vuln
            assert "severity" in vuln
            assert "description" in vuln

    @pytest.mark.asyncio
    async def test_security_alerts(self, monitor):
        # Simulate security alerts
        issues = await monitor.check_security()
        assert isinstance(issues["security_alerts"], list)
        
        # Verify alert structure
        if issues["security_alerts"]:
            alert = issues["security_alerts"][0]
            assert "type" in alert
            assert "message" in alert
            assert "severity" in alert

    @pytest.mark.asyncio
    async def test_security_updates(self, monitor):
        # Simulate security updates
        issues = await monitor.check_security()
        assert isinstance(issues["security_updates"], list)
        
        # Verify update structure
        if issues["security_updates"]:
            update = issues["security_updates"][0]
            assert "package" in update
            assert "version" in update
            assert "description" in update

    @pytest.mark.asyncio
    async def test_get_status(self, monitor):
        status = monitor.get_status()
        assert isinstance(status, dict)
        assert "last_check" in status
        assert "vulnerabilities_found" in status
        assert "alerts_generated" in status
        assert "updates_available" in status
        assert "processing_time" in status
        assert "error_count" in status

    @pytest.mark.asyncio
    async def test_clear_alerts(self, monitor):
        # First check for security issues
        await monitor.check_security()
        
        # Clear alerts
        await monitor.clear_alerts()
        
        # Verify alerts are cleared
        status = monitor.get_status()
        assert status["vulnerabilities_found"] == 0
        assert status["alerts_generated"] == 0
        assert status["updates_available"] == 0

    @pytest.mark.asyncio
    async def test_error_handling(self, monitor):
        # Test error handling for invalid check interval
        with pytest.raises(SecurityMonitorError):
            monitor.check_interval = -1
            await monitor.check_security()

    @pytest.mark.asyncio
    async def test_concurrent_checks(self, monitor):
        # Test concurrent security checks
        tasks = [
            monitor.check_security() for _ in range(5)
        ]
        results = await asyncio.gather(*tasks)
        assert len(results) == 5
        assert all(isinstance(r, dict) for r in results)

    @pytest.mark.asyncio
    async def test_severity_levels(self, monitor):
        # Test different severity levels
        monitor.severity_threshold = "low"
        issues = await monitor.check_security()
        assert isinstance(issues["vulnerabilities"], list)

        monitor.severity_threshold = "high"
        issues = await monitor.check_security()
        assert isinstance(issues["vulnerabilities"], list)

    @pytest.mark.asyncio
    async def test_vulnerability_scanners(self, monitor):
        # Test vulnerability scanner configuration
        monitor.vulnerability_scanners = ["snyk", "owasp"]
        issues = await monitor.check_security()
        assert isinstance(issues["vulnerabilities"], list)

    @pytest.mark.asyncio
    async def test_alert_channels(self, monitor):
        # Test alert channel configuration
        monitor.alert_channels = ["email", "slack"]
        issues = await monitor.check_security()
        assert isinstance(issues["security_alerts"], list)

    @pytest.mark.asyncio
    async def test_check_processing(self, monitor):
        # Test check processing time
        start_time = datetime.now()
        await monitor.check_security()
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
            await monitor.check_security()
        except SecurityMonitorError:
            pass
            
        assert monitor.get_status()["error_count"] == initial_errors + 1

    @pytest.mark.asyncio
    async def test_security_policies(self, monitor):
        # Test security policy configuration
        monitor.security_policies = {
            "max_severity": "critical",
            "auto_update": True,
            "notify_on_critical": True
        }
        issues = await monitor.check_security()
        assert isinstance(issues, dict)

    @pytest.mark.asyncio
    async def test_update_handling(self, monitor):
        # Test security update handling
        issues = await monitor.check_security()
        if issues["security_updates"]:
            update = issues["security_updates"][0]
            assert isinstance(update, dict)
            assert "package" in update
            assert "version" in update
            assert "description" in update 