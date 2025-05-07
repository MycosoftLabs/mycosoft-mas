import pytest
import os
import yaml
from mycosoft_mas.config import settings

class TestConfig:
    @pytest.fixture
    def config_path(self):
        return os.path.join(os.path.dirname(__file__), "..", "config", "config.yaml")

    def test_config_file_exists(self, config_path):
        assert os.path.exists(config_path), "Configuration file does not exist"

    def test_config_file_format(self, config_path):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            assert isinstance(config, dict), "Configuration is not a valid YAML dictionary"

    def test_required_sections(self, config_path):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            required_sections = [
                "services",
                "security",
                "monitoring",
                "agents",
                "integrations",
                "dependencies"
            ]
            for section in required_sections:
                assert section in config, f"Missing required section: {section}"

    def test_services_config(self, config_path):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            services = config.get("services", {})
            
            # Check evolution monitor config
            assert "evolution_monitor" in services
            evolution = services["evolution_monitor"]
            assert "check_interval" in evolution
            assert "alert_threshold" in evolution
            assert "technology_sources" in evolution
            
            # Check security monitor config
            assert "security_monitor" in services
            security = services["security_monitor"]
            assert "check_interval" in security
            assert "vulnerability_scanners" in security
            assert "alert_channels" in security
            
            # Check technology tracker config
            assert "technology_tracker" in services
            tracker = services["technology_tracker"]
            assert "update_interval" in tracker
            assert "tracking_level" in tracker
            assert "storage" in tracker

    def test_security_config(self, config_path):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            security = config.get("security", {})
            
            assert "authentication" in security
            assert "authorization" in security
            assert "encryption" in security
            assert "access_control" in security

    def test_monitoring_config(self, config_path):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            monitoring = config.get("monitoring", {})
            
            assert "metrics" in monitoring
            assert "alerts" in monitoring
            assert "dashboard" in monitoring

    def test_agents_config(self, config_path):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            agents = config.get("agents", {})
            
            assert "base_agent" in agents
            assert "specialized_agents" in agents
            assert "agent_manager" in agents

    def test_integrations_config(self, config_path):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            integrations = config.get("integrations", {})
            
            assert "external_systems" in integrations
            assert "internal_systems" in integrations
            assert "api_endpoints" in integrations

    def test_dependencies_config(self, config_path):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            dependencies = config.get("dependencies", {})
            
            assert "packages" in dependencies
            assert "versions" in dependencies
            assert "constraints" in dependencies

    def test_settings_module(self):
        assert hasattr(settings, "SERVICES")
        assert hasattr(settings, "SECURITY")
        assert hasattr(settings, "MONITORING")
        assert hasattr(settings, "AGENTS")
        assert hasattr(settings, "INTEGRATIONS")
        assert hasattr(settings, "DEPENDENCIES")

    def test_settings_values(self):
        # Check service settings
        assert isinstance(settings.SERVICES, dict)
        assert "evolution_monitor" in settings.SERVICES
        assert "security_monitor" in settings.SERVICES
        assert "technology_tracker" in settings.SERVICES
        
        # Check security settings
        assert isinstance(settings.SECURITY, dict)
        assert "authentication" in settings.SECURITY
        assert "authorization" in settings.SECURITY
        
        # Check monitoring settings
        assert isinstance(settings.MONITORING, dict)
        assert "metrics" in settings.MONITORING
        assert "alerts" in settings.MONITORING
        
        # Check agent settings
        assert isinstance(settings.AGENTS, dict)
        assert "base_agent" in settings.AGENTS
        assert "specialized_agents" in settings.AGENTS
        
        # Check integration settings
        assert isinstance(settings.INTEGRATIONS, dict)
        assert "external_systems" in settings.INTEGRATIONS
        assert "internal_systems" in settings.INTEGRATIONS
        
        # Check dependency settings
        assert isinstance(settings.DEPENDENCIES, dict)
        assert "packages" in settings.DEPENDENCIES
        assert "versions" in settings.DEPENDENCIES 