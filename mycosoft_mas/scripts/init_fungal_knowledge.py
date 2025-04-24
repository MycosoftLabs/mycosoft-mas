import asyncio
import json
import logging
import os
from pathlib import Path

from mycosoft_mas.agents.mycology_bio_agent import MycologyBioAgent
from mycosoft_mas.plugins.fungal_knowledge_graph import FungalKnowledgeGraph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def initialize_fungal_knowledge(config_path: str) -> None:
    """Initialize the fungal knowledge graph with the given configuration."""
    try:
        # Load configuration
        with open(config_path) as f:
            config = json.load(f)
        
        # Create necessary directories
        data_dir = Path(config["data_dir"])
        output_dir = Path(config["output_dir"])
        data_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize the fungal knowledge graph
        graph = FungalKnowledgeGraph(config)
        await graph.initialize()
        
        # Initialize the bio agent
        agent = MycologyBioAgent(config)
        await agent.initialize()
        
        logger.info("Fungal knowledge graph initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize fungal knowledge graph: {e}")
        raise

if __name__ == "__main__":
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "fungal_knowledge_config.json")
    asyncio.run(initialize_fungal_knowledge(config_path)) 