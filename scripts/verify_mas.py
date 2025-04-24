import subprocess
import logging
import sys
from typing import List
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_script(script_name: str) -> bool:
    """Run a Python script and return True if successful"""
    try:
        logger.info(f"Running {script_name}...")
        result = subprocess.run(
            [sys.executable, f"scripts/{script_name}"],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running {script_name}:")
        logger.error(e.stdout)
        logger.error(e.stderr)
        return False

def main():
    scripts_to_run: List[str] = [
        "check_services.py",
        "initialize_mas.py",
        "verify_monitoring.py"
    ]
    
    all_successful = True
    for script in scripts_to_run:
        if not run_script(script):
            all_successful = False
            logger.error(f"Failed to run {script}")
            break
        time.sleep(5)  # Small delay between scripts
    
    if all_successful:
        logger.info("All verification steps completed successfully!")
        logger.info("MAS is ready to use!")
        logger.info("Access points:")
        logger.info("- Orchestrator: http://localhost:8000")
        logger.info("- Grafana: http://localhost:3000")
        logger.info("- Prometheus: http://localhost:9090")
        logger.info("- AlertManager: http://localhost:9093")
    else:
        logger.error("MAS verification failed. Please check the logs above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main() 