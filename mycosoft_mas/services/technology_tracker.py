"""
Mycosoft MAS - Technology Tracker Service

This module tracks and manages technology-related information and updates.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import asyncio
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class TechnologyTracker:
    """Service for tracking and managing technology information."""
    
    def __init__(self):
        self.technologies: Dict[str, Dict[str, Any]] = {}
        self.technology_alerts: List[Dict[str, Any]] = []
        self.technology_updates: List[Dict[str, Any]] = []
        self.last_check = datetime.now()
        
    async def check_for_updates(self) -> Dict[str, Any]:
        """Check for new technologies and updates."""
        try:
            # Check for new technologies
            new_techs = await self._check_new_technologies()
            
            # Check for technology alerts
            alerts = await self._check_technology_alerts()
            
            # Check for technology updates
            updates = await self._check_technology_updates()
            
            self.last_check = datetime.now()
            
            return {
                'new_technologies': new_techs,
                'technology_alerts': alerts,
                'technology_updates': updates,
                'last_check': self.last_check.isoformat()
            }
        except Exception as e:
            logger.error(f"Error checking technology updates: {str(e)}")
            return {
                'error': str(e),
                'last_check': self.last_check.isoformat()
            }
            
    async def _check_new_technologies(self) -> List[Dict[str, Any]]:
        """Check for new technologies."""
        try:
            file = Path("data/technology/new_technologies.json")
            if file.exists():
                with open(file, "r") as f:
                    data = json.load(f)
                return data
            return []
        except Exception as e:
            logger.error(f"Error checking for new technologies: {str(e)}")
            return []
            
    async def _check_technology_alerts(self) -> List[Dict[str, Any]]:
        """Check for technology-related alerts."""
        try:
            file = Path("data/technology/alerts.json")
            if file.exists():
                with open(file, "r") as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"Error checking technology alerts: {str(e)}")
            return []
            
    async def _check_technology_updates(self) -> List[Dict[str, Any]]:
        """Check for technology updates."""
        try:
            file = Path("data/technology/updates.json")
            if file.exists():
                with open(file, "r") as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"Error checking technology updates: {str(e)}")
            return []
            
    def register_technology(self, name: str, details: Dict[str, Any]) -> bool:
        """Register a new technology."""
        try:
            if name in self.technologies:
                logger.warning(f"Technology {name} already registered")
                return False
                
            self.technologies[name] = {
                **details,
                'registered_at': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat()
            }
            return True
        except Exception as e:
            logger.error(f"Error registering technology {name}: {str(e)}")
            return False
            
    def update_technology(self, name: str, updates: Dict[str, Any]) -> bool:
        """Update an existing technology."""
        try:
            if name not in self.technologies:
                logger.warning(f"Technology {name} not found")
                return False
                
            self.technologies[name].update(updates)
            self.technologies[name]['last_updated'] = datetime.now().isoformat()
            return True
        except Exception as e:
            logger.error(f"Error updating technology {name}: {str(e)}")
            return False
            
    def get_technology(self, name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific technology."""
        return self.technologies.get(name)
        
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the technology tracker."""
        return {
            'registered_technologies_count': len(self.technologies),
            'technology_alerts_count': len(self.technology_alerts),
            'technology_updates_count': len(self.technology_updates),
            'last_check': self.last_check.isoformat()
        }
        
    def clear_updates(self) -> None:
        """Clear all stored updates and alerts."""
        self.technology_alerts.clear()
        self.technology_updates.clear()
