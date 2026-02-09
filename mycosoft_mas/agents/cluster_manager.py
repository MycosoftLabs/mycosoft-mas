"""
Mycosoft MAS - Cluster Manager

This module manages agent clusters and their interactions.
"""

from typing import Dict, List, Any, Optional
import logging
import asyncio
from datetime import datetime

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

class ClusterManager:
    """Manages agent clusters and their interactions."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.clusters: Dict[str, List[BaseAgent]] = {}
        self.cluster_metrics: Dict[str, Dict[str, Any]] = {}
        self.last_check = datetime.now()
        
    async def start(self) -> None:
        """Start the cluster manager."""
        try:
            logger.info("Starting cluster manager")
            # Initialize cluster metrics
            for cluster_id in self.config.get('clusters', []):
                self.clusters[cluster_id] = []
                self.cluster_metrics[cluster_id] = {
                    'agent_count': 0,
                    'last_activity': datetime.now().isoformat(),
                    'status': 'active'
                }
        except Exception as e:
            logger.error(f"Error starting cluster manager: {str(e)}")
            raise
            
    async def stop(self) -> None:
        """Stop the cluster manager."""
        try:
            logger.info("Stopping cluster manager")
            # Clean up clusters
            self.clusters.clear()
            self.cluster_metrics.clear()
        except Exception as e:
            logger.error(f"Error stopping cluster manager: {str(e)}")
            raise
            
    async def create_cluster(self, cluster_id: str) -> bool:
        """Create a new agent cluster."""
        try:
            if cluster_id in self.clusters:
                logger.warning(f"Cluster {cluster_id} already exists")
                return False
                
            self.clusters[cluster_id] = []
            self.cluster_metrics[cluster_id] = {
                'agent_count': 0,
                'last_activity': datetime.now().isoformat(),
                'status': 'active'
            }
            return True
        except Exception as e:
            logger.error(f"Error creating cluster {cluster_id}: {str(e)}")
            return False
            
    async def delete_cluster(self, cluster_id: str) -> bool:
        """Delete an existing cluster."""
        try:
            if cluster_id not in self.clusters:
                logger.warning(f"Cluster {cluster_id} not found")
                return False
                
            # Remove all agents from the cluster
            for agent in self.clusters[cluster_id]:
                await agent.stop()
                
            del self.clusters[cluster_id]
            del self.cluster_metrics[cluster_id]
            return True
        except Exception as e:
            logger.error(f"Error deleting cluster {cluster_id}: {str(e)}")
            return False
            
    async def add_agent_to_cluster(self, agent: BaseAgent, cluster_id: str) -> bool:
        """Add an agent to a cluster."""
        try:
            if cluster_id not in self.clusters:
                logger.warning(f"Cluster {cluster_id} not found")
                return False
                
            if agent in self.clusters[cluster_id]:
                logger.warning(f"Agent {agent.agent_id} already in cluster {cluster_id}")
                return False
                
            self.clusters[cluster_id].append(agent)
            self.cluster_metrics[cluster_id]['agent_count'] += 1
            self.cluster_metrics[cluster_id]['last_activity'] = datetime.now().isoformat()
            return True
        except Exception as e:
            logger.error(f"Error adding agent to cluster {cluster_id}: {str(e)}")
            return False
            
    async def remove_agent_from_cluster(self, agent: BaseAgent, cluster_id: str) -> bool:
        """Remove an agent from a cluster."""
        try:
            if cluster_id not in self.clusters:
                logger.warning(f"Cluster {cluster_id} not found")
                return False
                
            if agent not in self.clusters[cluster_id]:
                logger.warning(f"Agent {agent.agent_id} not in cluster {cluster_id}")
                return False
                
            self.clusters[cluster_id].remove(agent)
            self.cluster_metrics[cluster_id]['agent_count'] -= 1
            self.cluster_metrics[cluster_id]['last_activity'] = datetime.now().isoformat()
            return True
        except Exception as e:
            logger.error(f"Error removing agent from cluster {cluster_id}: {str(e)}")
            return False
            
    def get_cluster_status(self, cluster_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a specific cluster."""
        if cluster_id not in self.clusters:
            return None
            
        return {
            'cluster_id': cluster_id,
            'agent_count': len(self.clusters[cluster_id]),
            'agents': [agent.agent_id for agent in self.clusters[cluster_id]],
            'metrics': self.cluster_metrics[cluster_id]
        }
        
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the cluster manager."""
        return {
            'clusters': {
                cluster_id: {
                    'agent_count': len(agents),
                    'metrics': self.cluster_metrics[cluster_id]
                }
                for cluster_id, agents in self.clusters.items()
            },
            'last_check': self.last_check.isoformat()
        } 