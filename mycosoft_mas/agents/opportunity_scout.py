"""
OpportunityScout Agent

This agent continuously monitors DoD opportunity sources for relevant solicitations.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import aiohttp
import yaml
from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.messaging.message_broker import MessageBroker

class OpportunityScout(BaseAgent):
    """Agent responsible for monitoring DoD opportunity sources."""
    
    def __init__(self, agent_id: str, name: str, config: Dict):
        """
        Initialize the OpportunityScout agent.
        
        Args:
            agent_id: Unique identifier for the agent
            name: Display name for the agent
            config: Agent configuration dictionary
        """
        super().__init__(agent_id=agent_id, name=name, config=config)
        self.logger = logging.getLogger(__name__)
        self.data_dir = Path(config.get("output", {}).get("location", "data/opportunities"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Load keywords
        self.primary_keywords = config.get("keywords", {}).get("primary", [])
        self.secondary_keywords = config.get("keywords", {}).get("secondary", [])
        
        # Initialize message broker
        self.message_broker = MessageBroker({})
    
    async def initialize(self) -> None:
        """Initialize the agent."""
        await super().initialize()
        self.logger.info("OpportunityScout agent initialized")
    
    async def process(self) -> None:
        """Main processing loop for the agent."""
        while self.status.value == "running":
            try:
                # Scan each data source
                for source in self.config.get("data_sources", []):
                    await self.scan_source(source)
                
                # Sleep until next scheduled run
                await asyncio.sleep(3600)  # 1 hour
            except Exception as e:
                self.logger.error(f"Error in OpportunityScout process: {str(e)}")
                await self.error_logging_service.log_error(
                    "opportunity_scout_error",
                    {"error": str(e)}
                )
    
    async def scan_source(self, source: Dict) -> None:
        """
        Scan a specific opportunity source.
        
        Args:
            source: Source configuration dictionary
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(source["url"]) as response:
                    if response.status == 200:
                        data = await response.json()
                        opportunities = self.filter_opportunities(data)
                        if opportunities:
                            await self.process_opportunities(opportunities, source["name"])
                    else:
                        self.logger.warning(f"Failed to fetch from {source['name']}: {response.status}")
        except Exception as e:
            self.logger.error(f"Error scanning source {source['name']}: {str(e)}")
    
    def filter_opportunities(self, data: Dict) -> List[Dict]:
        """
        Filter opportunities based on keywords.
        
        Args:
            data: Raw opportunity data
            
        Returns:
            List of filtered opportunities
        """
        filtered = []
        for opp in data.get("opportunities", []):
            text = f"{opp.get('title', '')} {opp.get('description', '')}".lower()
            
            # Check primary keywords
            primary_matches = sum(1 for kw in self.primary_keywords if kw.lower() in text)
            
            # Check secondary keywords
            secondary_matches = sum(1 for kw in self.secondary_keywords if kw.lower() in text)
            
            if primary_matches >= 2 or (primary_matches >= 1 and secondary_matches >= 2):
                filtered.append(opp)
        
        return filtered
    
    async def process_opportunities(self, opportunities: List[Dict], source: str) -> None:
        """
        Process and store filtered opportunities.
        
        Args:
            opportunities: List of filtered opportunities
            source: Source name
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.data_dir / f"{source}_{timestamp}.json"
        
        # Save opportunities to file
        with open(output_file, "w") as f:
            json.dump(opportunities, f, indent=2)
        
        # Notify via Slack for high-priority opportunities
        for opp in opportunities:
            if self.is_high_priority(opp):
                await self.message_broker.send_message(
                    "slack",
                    {
                        "channel": self.config["notifications"]["slack"]["channel"],
                        "text": f"New high-priority opportunity: {opp.get('title')}\n{opp.get('url')}"
                    }
                )
    
    def is_high_priority(self, opportunity: Dict) -> bool:
        """
        Determine if an opportunity is high priority.
        
        Args:
            opportunity: Opportunity data
            
        Returns:
            True if high priority, False otherwise
        """
        # Check for key indicators of high priority
        text = f"{opportunity.get('title', '')} {opportunity.get('description', '')}".lower()
        primary_matches = sum(1 for kw in self.primary_keywords if kw.lower() in text)
        return primary_matches >= 3
    
    async def shutdown(self) -> None:
        """Shutdown the agent."""
        await super().shutdown()
        self.logger.info("OpportunityScout agent shut down") 