"""
Dashboard Agent for Mycosoft MAS

This module implements the DashboardAgent class that manages the system dashboard
and metrics visualization.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.messaging.message_types import Message, MessageType, MessagePriority

class DashboardAgent(BaseAgent):
    """
    Agent responsible for managing the system dashboard and metrics visualization.
    
    This agent:
    - Collects metrics from other agents
    - Generates visualizations
    - Updates dashboard widgets
    - Manages dashboard layouts
    """
    
    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        """
        Initialize the Dashboard Agent.
        
        Args:
            agent_id: Unique identifier for the agent
            name: Display name for the agent
            config: Configuration dictionary
        """
        super().__init__(agent_id=agent_id, name=name, config=config)
        
        # Initialize metrics
        self.metrics = {
            "widgets_updated": 0,
            "metrics_collected": 0,
            "visualizations_generated": 0,
            "errors_encountered": 0
        }
        
        # Initialize dashboard data
        self.dashboard_data = {
            "widgets": {},
            "layouts": {},
            "metrics": {},
            "visualizations": {}
        }
    
    async def handle_message(self, message: Message) -> None:
        """
        Handle incoming messages.
        
        Args:
            message: Message to handle
        """
        try:
            if message.type == MessageType.DASHBOARD:
                await self._handle_dashboard_message(message)
            elif message.type == MessageType.METRIC:
                await self._handle_metric_message(message)
            else:
                self.logger.warning(f"Unhandled message type: {message.type}")
        except Exception as e:
            self.logger.error(f"Error handling message: {str(e)}")
            self.metrics["errors_encountered"] += 1
            raise
    
    async def _handle_dashboard_message(self, message: Message) -> None:
        """
        Handle dashboard-related messages.
        
        Args:
            message: Dashboard message to handle
        """
        action = message.data.get("action")
        
        if action == "update_widget":
            await self._handle_update_widget(message)
        elif action == "update_layout":
            await self._handle_update_layout(message)
        elif action == "get_dashboard":
            await self._handle_get_dashboard(message)
        else:
            self.logger.warning(f"Unhandled dashboard action: {action}")
    
    async def _handle_metric_message(self, message: Message) -> None:
        """
        Handle metric-related messages.
        
        Args:
            message: Metric message to handle
        """
        action = message.data.get("action")
        
        if action == "update_metric":
            await self._handle_update_metric(message)
        elif action == "get_metrics":
            await self._handle_get_metrics(message)
        else:
            self.logger.warning(f"Unhandled metric action: {action}")
    
    async def _handle_update_widget(self, message: Message) -> None:
        """
        Handle widget update request.
        
        Args:
            message: Message containing widget update request
        """
        try:
            widget_id = message.data.get("widget_id")
            widget_data = message.data.get("widget_data")
            
            self.dashboard_data["widgets"][widget_id] = widget_data
            self.metrics["widgets_updated"] += 1
            
            await self.send_message(
                Message(
                    type=MessageType.DASHBOARD,
                    priority=MessagePriority.NORMAL,
                    data={
                        "action": "widget_updated",
                        "widget_id": widget_id
                    }
                )
            )
        except Exception as e:
            self.logger.error(f"Error updating widget: {str(e)}")
            raise
    
    async def _handle_update_layout(self, message: Message) -> None:
        """
        Handle layout update request.
        
        Args:
            message: Message containing layout update request
        """
        try:
            layout_id = message.data.get("layout_id")
            layout_data = message.data.get("layout_data")
            
            self.dashboard_data["layouts"][layout_id] = layout_data
            
            await self.send_message(
                Message(
                    type=MessageType.DASHBOARD,
                    priority=MessagePriority.NORMAL,
                    data={
                        "action": "layout_updated",
                        "layout_id": layout_id
                    }
                )
            )
        except Exception as e:
            self.logger.error(f"Error updating layout: {str(e)}")
            raise
    
    async def _handle_get_dashboard(self, message: Message) -> None:
        """
        Handle get dashboard request.
        
        Args:
            message: Message containing dashboard request
        """
        try:
            await self.send_message(
                Message(
                    type=MessageType.DASHBOARD,
                    priority=MessagePriority.NORMAL,
                    data={
                        "action": "dashboard_data",
                        "dashboard_data": self.dashboard_data
                    }
                )
            )
        except Exception as e:
            self.logger.error(f"Error getting dashboard: {str(e)}")
            raise
    
    async def _handle_update_metric(self, message: Message) -> None:
        """
        Handle metric update request.
        
        Args:
            message: Message containing metric update request
        """
        try:
            metric_id = message.data.get("metric_id")
            metric_data = message.data.get("metric_data")
            
            self.dashboard_data["metrics"][metric_id] = metric_data
            self.metrics["metrics_collected"] += 1
            
            # Generate visualization if needed
            if message.data.get("generate_visualization"):
                visualization = await self._generate_visualization(metric_id, metric_data)
                self.dashboard_data["visualizations"][metric_id] = visualization
                self.metrics["visualizations_generated"] += 1
            
            await self.send_message(
                Message(
                    type=MessageType.DASHBOARD,
                    priority=MessagePriority.NORMAL,
                    data={
                        "action": "metric_updated",
                        "metric_id": metric_id
                    }
                )
            )
        except Exception as e:
            self.logger.error(f"Error updating metric: {str(e)}")
            raise
    
    async def _handle_get_metrics(self, message: Message) -> None:
        """
        Handle get metrics request.
        
        Args:
            message: Message containing metrics request
        """
        try:
            metric_ids = message.data.get("metric_ids", [])
            
            if metric_ids:
                metrics = {
                    metric_id: self.dashboard_data["metrics"].get(metric_id)
                    for metric_id in metric_ids
                }
            else:
                metrics = self.dashboard_data["metrics"]
            
            await self.send_message(
                Message(
                    type=MessageType.DASHBOARD,
                    priority=MessagePriority.NORMAL,
                    data={
                        "action": "metrics_data",
                        "metrics": metrics
                    }
                )
            )
        except Exception as e:
            self.logger.error(f"Error getting metrics: {str(e)}")
            raise
    
    async def _generate_visualization(self, metric_id: str, metric_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate visualization for metric data.
        
        Args:
            metric_id: ID of the metric
            metric_data: Metric data to visualize
            
        Returns:
            Visualization data
        """
        try:
            # Implementation depends on visualization library
            # For now, return placeholder data
            return {
                "type": "line_chart",
                "data": metric_data,
                "options": {
                    "title": f"Metric {metric_id}",
                    "x_axis": "time",
                    "y_axis": "value"
                }
            }
        except Exception as e:
            self.logger.error(f"Error generating visualization: {str(e)}")
            raise 