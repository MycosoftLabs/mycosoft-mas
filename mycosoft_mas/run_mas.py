"""
Mycosoft MAS Runner

This module serves as the entry point for running the Mycosoft Multi-Agent System.
"""

import asyncio
import logging
from pathlib import Path
import yaml

from mycosoft_mas.core.myca_main import MycosoftMAS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/mas.log')
    ]
)
logger = logging.getLogger(__name__)

async def main():
    """Main entry point for the MAS application."""
    try:
        # Load configuration
        config_path = Path("config.yaml")
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found at {config_path}")
        
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        # Initialize MAS
        mas = MycosoftMAS(config)
        await mas.initialize()
        
        # Start the application
        logger.info("Mycosoft MAS is running")
        await mas.start()
        
    except Exception as e:
        logger.error(f"Error starting Mycosoft MAS: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 