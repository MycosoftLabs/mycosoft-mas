import requests
import json
import logging
from typing import Dict, Any
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ORCHESTRATOR_URL = "http://localhost:8000"

def initialize_security():
    """Initialize security policies and access control"""
    try:
        response = requests.post(
            f"{ORCHESTRATOR_URL}/security/initialize",
            json={
                "policies": {
                    "access_control": {
                        "default_level": "restricted",
                        "allowed_origins": ["*"]
                    },
                    "encryption": {
                        "algorithm": "AES-256",
                        "key_rotation_interval": 86400
                    }
                }
            }
        )
        response.raise_for_status()
        logger.info("Security initialization completed")
    except Exception as e:
        logger.error(f"Security initialization failed: {str(e)}")
        raise

def initialize_agents():
    """Initialize agent configurations"""
    try:
        response = requests.post(
            f"{ORCHESTRATOR_URL}/agents/initialize",
            json={
                "default_config": {
                    "max_concurrent_tasks": 5,
                    "health_check_interval": 30,
                    "resource_limits": {
                        "cpu": "1.0",
                        "memory": "1Gi"
                    }
                }
            }
        )
        response.raise_for_status()
        logger.info("Agent initialization completed")
    except Exception as e:
        logger.error(f"Agent initialization failed: {str(e)}")
        raise

def initialize_monitoring():
    """Initialize monitoring configurations"""
    try:
        response = requests.post(
            f"{ORCHESTRATOR_URL}/monitoring/initialize",
            json={
                "metrics": {
                    "collection_interval": 15,
                    "retention_period": "7d"
                },
                "alerts": {
                    "default_severity": "warning",
                    "notification_channels": ["email", "slack"]
                }
            }
        )
        response.raise_for_status()
        logger.info("Monitoring initialization completed")
    except Exception as e:
        logger.error(f"Monitoring initialization failed: {str(e)}")
        raise

def initialize_dependencies():
    """Initialize dependency management"""
    try:
        response = requests.post(
            f"{ORCHESTRATOR_URL}/dependencies/initialize",
            json={
                "default_policies": {
                    "version_constraints": ">=1.0.0",
                    "security_checks": True,
                    "auto_update": False
                }
            }
        )
        response.raise_for_status()
        logger.info("Dependency initialization completed")
    except Exception as e:
        logger.error(f"Dependency initialization failed: {str(e)}")
        raise

def main():
    logger.info("Starting MAS initialization...")
    
    # Wait for orchestrator to be ready
    max_retries = 30
    retry_interval = 5
    
    for i in range(max_retries):
        try:
            response = requests.get(f"{ORCHESTRATOR_URL}/health")
            if response.status_code == 200:
                break
        except Exception:
            if i == max_retries - 1:
                logger.error("Orchestrator not ready after maximum retries")
                raise
            logger.info(f"Waiting for orchestrator... (attempt {i+1}/{max_retries})")
            time.sleep(retry_interval)
    
    # Initialize components
    initialize_security()
    initialize_agents()
    initialize_monitoring()
    initialize_dependencies()
    
    logger.info("MAS initialization completed successfully")

if __name__ == "__main__":
    main() 