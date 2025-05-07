import requests
import logging
import time
from typing import Dict, List
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROMETHEUS_URL = "http://localhost:9090"
GRAFANA_URL = "http://localhost:3000"
ALERTMANAGER_URL = "http://localhost:9093"

def verify_prometheus():
    """Verify Prometheus is collecting metrics"""
    try:
        # Check Prometheus health
        response = requests.get(f"{PROMETHEUS_URL}/-/healthy")
        response.raise_for_status()
        
        # Check if targets are up
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/targets")
        data = response.json()
        
        active_targets = [t for t in data['data']['activeTargets'] if t['health'] == 'up']
        logger.info(f"Prometheus is monitoring {len(active_targets)} targets")
        
        # Check for MAS-specific metrics
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/query?query=mas_service_health")
        data = response.json()
        if data['data']['result']:
            logger.info("MAS metrics are being collected")
        else:
            logger.warning("No MAS metrics found in Prometheus")
            
    except Exception as e:
        logger.error(f"Prometheus verification failed: {str(e)}")
        raise

def verify_grafana():
    """Verify Grafana is properly configured"""
    try:
        # Check Grafana health
        response = requests.get(f"{GRAFANA_URL}/api/health")
        response.raise_for_status()
        
        # Check datasources
        response = requests.get(
            f"{GRAFANA_URL}/api/datasources",
            auth=('admin', 'admin')
        )
        data = response.json()
        
        prometheus_ds = [ds for ds in data if ds['type'] == 'prometheus']
        if prometheus_ds:
            logger.info("Prometheus datasource is configured in Grafana")
        else:
            logger.warning("Prometheus datasource not found in Grafana")
            
        # Check dashboards
        response = requests.get(
            f"{GRAFANA_URL}/api/search",
            auth=('admin', 'admin')
        )
        data = response.json()
        
        mas_dashboards = [d for d in data if 'mas' in d['title'].lower()]
        if mas_dashboards:
            logger.info(f"Found {len(mas_dashboards)} MAS dashboards")
        else:
            logger.warning("No MAS dashboards found")
            
    except Exception as e:
        logger.error(f"Grafana verification failed: {str(e)}")
        raise

def verify_alertmanager():
    """Verify AlertManager is properly configured"""
    try:
        # Check AlertManager health
        response = requests.get(f"{ALERTMANAGER_URL}/-/healthy")
        response.raise_for_status()
        
        # Check configuration
        response = requests.get(f"{ALERTMANAGER_URL}/api/v2/status")
        data = response.json()
        
        if data['config']['route']:
            logger.info("AlertManager routing is configured")
        else:
            logger.warning("AlertManager routing not configured")
            
    except Exception as e:
        logger.error(f"AlertManager verification failed: {str(e)}")
        raise

def main():
    logger.info("Starting monitoring verification...")
    
    verify_prometheus()
    verify_grafana()
    verify_alertmanager()
    
    logger.info("Monitoring verification completed successfully")

if __name__ == "__main__":
    main() 