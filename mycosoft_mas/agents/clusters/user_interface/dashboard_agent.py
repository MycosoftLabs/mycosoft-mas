"""
Dashboard Agent for User Interface Cluster

This module implements a dashboard agent that manages the main dashboard for the
Mycosoft Multi-Agent System, providing visualization and interaction capabilities
for users to monitor and control the system.
"""

import asyncio
import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple, Union, Callable, Awaitable
from pathlib import Path
from enum import Enum, auto
from dataclasses import dataclass, field

from ...messaging.message_types import MessageType, MessagePriority
from ...messaging.message_broker import MessageBroker

class DashboardComponentType(Enum):
    """Types of dashboard components"""
    CHART = auto()
    TABLE = auto()
    METRIC = auto()
    ALERT = auto()
    CONTROL = auto()
    MAP = auto()
    TIMELINE = auto()
    CUSTOM = auto()

class DashboardLayoutType(Enum):
    """Types of dashboard layouts"""
    GRID = auto()
    FLEXIBLE = auto()
    CUSTOM = auto()

class DashboardTheme(Enum):
    """Available dashboard themes"""
    LIGHT = auto()
    DARK = auto()
    MYCOLOGY = auto()
    CUSTOM = auto()

@dataclass
class DashboardComponent:
    """Information about a dashboard component"""
    component_id: str
    component_type: DashboardComponentType
    title: str
    description: Optional[str] = None
    position: Dict[str, int] = field(default_factory=lambda: {"x": 0, "y": 0, "width": 1, "height": 1})
    data_source: Optional[str] = None
    refresh_interval: Optional[int] = None  # in seconds
    config: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True

@dataclass
class Dashboard:
    """Information about a dashboard"""
    dashboard_id: str
    name: str
    description: Optional[str] = None
    layout_type: DashboardLayoutType = DashboardLayoutType.GRID
    theme: DashboardTheme = DashboardTheme.MYCOLOGY
    components: List[DashboardComponent] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    is_default: bool = False
    owner: Optional[str] = None
    permissions: Dict[str, List[str]] = field(default_factory=lambda: {"view": [], "edit": []})

class DashboardAgent:
    """
    Agent that manages dashboards for the Mycosoft MAS.
    
    This class:
    1. Creates and manages dashboard layouts and components
    2. Handles data visualization and updates
    3. Manages user interactions and permissions
    4. Coordinates with other agents for data and control
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        message_broker: MessageBroker
    ):
        """
        Initialize the dashboard agent.
        
        Args:
            config: Configuration dictionary for the dashboard agent
            message_broker: Message broker instance for communication
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.message_broker = message_broker
        
        # Create data directory
        self.data_dir = Path("data/user_interface/dashboards")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Dashboard registry
        self.dashboards: Dict[str, Dashboard] = {}
        self.active_dashboard_id: Optional[str] = None
        
        # Component data cache
        self.component_data: Dict[str, Dict[str, Any]] = {}
        
        # Metrics
        self.metrics = {
            "dashboards_created": 0,
            "components_created": 0,
            "data_updates": 0,
            "user_interactions": 0,
            "errors": 0
        }
        
        # Load data
        self._load_data()
    
    def _load_data(self) -> None:
        """Load dashboard data from disk"""
        try:
            # Load dashboards
            dashboards_file = self.data_dir / "dashboards.json"
            if dashboards_file.exists():
                with open(dashboards_file, "r") as f:
                    dashboards_data = json.load(f)
                    
                    for dashboard_data in dashboards_data:
                        components = []
                        for component_data in dashboard_data.get("components", []):
                            component = DashboardComponent(
                                component_id=component_data["component_id"],
                                component_type=DashboardComponentType[component_data["component_type"]],
                                title=component_data["title"],
                                description=component_data.get("description"),
                                position=component_data.get("position", {"x": 0, "y": 0, "width": 1, "height": 1}),
                                data_source=component_data.get("data_source"),
                                refresh_interval=component_data.get("refresh_interval"),
                                config=component_data.get("config", {}),
                                created_at=datetime.fromisoformat(component_data["created_at"]),
                                updated_at=datetime.fromisoformat(component_data["updated_at"]),
                                is_active=component_data.get("is_active", True)
                            )
                            components.append(component)
                        
                        dashboard = Dashboard(
                            dashboard_id=dashboard_data["dashboard_id"],
                            name=dashboard_data["name"],
                            description=dashboard_data.get("description"),
                            layout_type=DashboardLayoutType[dashboard_data["layout_type"]],
                            theme=DashboardTheme[dashboard_data["theme"]],
                            components=components,
                            created_at=datetime.fromisoformat(dashboard_data["created_at"]),
                            updated_at=datetime.fromisoformat(dashboard_data["updated_at"]),
                            is_active=dashboard_data.get("is_active", True),
                            is_default=dashboard_data.get("is_default", False),
                            owner=dashboard_data.get("owner"),
                            permissions=dashboard_data.get("permissions", {"view": [], "edit": []})
                        )
                        
                        self.dashboards[dashboard.dashboard_id] = dashboard
                        
                        # Set active dashboard if it's the default
                        if dashboard.is_default:
                            self.active_dashboard_id = dashboard.dashboard_id
            
            # Load component data
            component_data_file = self.data_dir / "component_data.json"
            if component_data_file.exists():
                with open(component_data_file, "r") as f:
                    self.component_data = json.load(f)
            
            # Load metrics
            metrics_file = self.data_dir / "metrics.json"
            if metrics_file.exists():
                with open(metrics_file, "r") as f:
                    self.metrics = json.load(f)
                    
        except Exception as e:
            self.logger.error(f"Error loading dashboard data: {str(e)}")
    
    async def save_data(self) -> None:
        """Save dashboard data to disk"""
        try:
            # Save dashboards
            dashboards_file = self.data_dir / "dashboards.json"
            dashboards_data = []
            
            for dashboard in self.dashboards.values():
                components_data = []
                for component in dashboard.components:
                    component_data = {
                        "component_id": component.component_id,
                        "component_type": component.component_type.name,
                        "title": component.title,
                        "description": component.description,
                        "position": component.position,
                        "data_source": component.data_source,
                        "refresh_interval": component.refresh_interval,
                        "config": component.config,
                        "created_at": component.created_at.isoformat(),
                        "updated_at": component.updated_at.isoformat(),
                        "is_active": component.is_active
                    }
                    components_data.append(component_data)
                
                dashboard_data = {
                    "dashboard_id": dashboard.dashboard_id,
                    "name": dashboard.name,
                    "description": dashboard.description,
                    "layout_type": dashboard.layout_type.name,
                    "theme": dashboard.theme.name,
                    "components": components_data,
                    "created_at": dashboard.created_at.isoformat(),
                    "updated_at": dashboard.updated_at.isoformat(),
                    "is_active": dashboard.is_active,
                    "is_default": dashboard.is_default,
                    "owner": dashboard.owner,
                    "permissions": dashboard.permissions
                }
                dashboards_data.append(dashboard_data)
            
            with open(dashboards_file, "w") as f:
                json.dump(dashboards_data, f, indent=2)
            
            # Save component data
            component_data_file = self.data_dir / "component_data.json"
            with open(component_data_file, "w") as f:
                json.dump(self.component_data, f, indent=2)
            
            # Save metrics
            metrics_file = self.data_dir / "metrics.json"
            with open(metrics_file, "w") as f:
                json.dump(self.metrics, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error saving dashboard data: {str(e)}")
    
    async def start(self) -> None:
        """Start the dashboard agent"""
        self.logger.info("Starting dashboard agent")
        
        # Subscribe to relevant message topics
        await self.message_broker.subscribe("dashboard.command", self._handle_dashboard_command)
        await self.message_broker.subscribe("dashboard.data", self._handle_dashboard_data)
        await self.message_broker.subscribe("dashboard.interaction", self._handle_dashboard_interaction)
        
        # Start background tasks
        asyncio.create_task(self._update_component_data())
        asyncio.create_task(self._periodic_save())
        
        self.logger.info("Dashboard agent started")
    
    async def stop(self) -> None:
        """Stop the dashboard agent"""
        self.logger.info("Stopping dashboard agent")
        
        # Unsubscribe from message topics
        await self.message_broker.unsubscribe("dashboard.command", self._handle_dashboard_command)
        await self.message_broker.unsubscribe("dashboard.data", self._handle_dashboard_data)
        await self.message_broker.unsubscribe("dashboard.interaction", self._handle_dashboard_interaction)
        
        # Save data
        await self.save_data()
        
        self.logger.info("Dashboard agent stopped")
    
    # Dashboard Management Methods
    
    async def create_dashboard(
        self,
        name: str,
        description: Optional[str] = None,
        layout_type: DashboardLayoutType = DashboardLayoutType.GRID,
        theme: DashboardTheme = DashboardTheme.MYCOLOGY,
        is_default: bool = False,
        owner: Optional[str] = None,
        permissions: Dict[str, List[str]] = None
    ) -> str:
        """
        Create a new dashboard.
        
        Args:
            name: Dashboard name
            description: Dashboard description (optional)
            layout_type: Dashboard layout type
            theme: Dashboard theme
            is_default: Whether this is the default dashboard
            owner: Dashboard owner (optional)
            permissions: Dashboard permissions (optional)
            
        Returns:
            str: Dashboard ID
        """
        dashboard_id = str(uuid.uuid4())
        
        # If this is the default dashboard, unset any existing default
        if is_default:
            for dashboard in self.dashboards.values():
                if dashboard.is_default:
                    dashboard.is_default = False
        
        dashboard = Dashboard(
            dashboard_id=dashboard_id,
            name=name,
            description=description,
            layout_type=layout_type,
            theme=theme,
            is_default=is_default,
            owner=owner,
            permissions=permissions or {"view": [], "edit": []}
        )
        
        self.dashboards[dashboard_id] = dashboard
        self.metrics["dashboards_created"] += 1
        
        # Set as active dashboard if it's the default
        if is_default:
            self.active_dashboard_id = dashboard_id
        
        await self.save_data()
        
        return dashboard_id
    
    async def update_dashboard(
        self,
        dashboard_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        layout_type: Optional[DashboardLayoutType] = None,
        theme: Optional[DashboardTheme] = None,
        is_default: Optional[bool] = None,
        owner: Optional[str] = None,
        permissions: Optional[Dict[str, List[str]]] = None
    ) -> None:
        """
        Update a dashboard.
        
        Args:
            dashboard_id: Dashboard ID
            name: New dashboard name (optional)
            description: New dashboard description (optional)
            layout_type: New dashboard layout type (optional)
            theme: New dashboard theme (optional)
            is_default: Whether this is the default dashboard (optional)
            owner: New dashboard owner (optional)
            permissions: New dashboard permissions (optional)
        """
        if dashboard_id in self.dashboards:
            dashboard = self.dashboards[dashboard_id]
            
            if name is not None:
                dashboard.name = name
            
            if description is not None:
                dashboard.description = description
            
            if layout_type is not None:
                dashboard.layout_type = layout_type
            
            if theme is not None:
                dashboard.theme = theme
            
            if is_default is not None:
                # If setting as default, unset any existing default
                if is_default:
                    for d in self.dashboards.values():
                        if d.is_default and d.dashboard_id != dashboard_id:
                            d.is_default = False
                            self.active_dashboard_id = dashboard_id
                
                dashboard.is_default = is_default
            
            if owner is not None:
                dashboard.owner = owner
            
            if permissions is not None:
                dashboard.permissions = permissions
            
            dashboard.updated_at = datetime.now()
            
            await self.save_data()
    
    async def delete_dashboard(self, dashboard_id: str) -> None:
        """
        Delete a dashboard.
        
        Args:
            dashboard_id: Dashboard ID
        """
        if dashboard_id in self.dashboards:
            dashboard = self.dashboards[dashboard_id]
            
            # If this was the active dashboard, set another as active
            if self.active_dashboard_id == dashboard_id:
                # Try to find another dashboard
                for d_id, d in self.dashboards.items():
                    if d_id != dashboard_id:
                        self.active_dashboard_id = d_id
                        break
                    else:
                        self.active_dashboard_id = None
            
            # Remove the dashboard
            del self.dashboards[dashboard_id]
            
            await self.save_data()
    
    async def get_dashboard(self, dashboard_id: str) -> Optional[Dashboard]:
        """
        Get dashboard information.
        
        Args:
            dashboard_id: Dashboard ID
            
        Returns:
            Optional[Dashboard]: Dashboard information, or None if not found
        """
        return self.dashboards.get(dashboard_id)
    
    async def get_all_dashboards(self) -> List[Dashboard]:
        """
        Get all dashboards.
        
        Returns:
            List[Dashboard]: List of all dashboards
        """
        return list(self.dashboards.values())
    
    async def get_active_dashboard(self) -> Optional[Dashboard]:
        """
        Get the active dashboard.
        
        Returns:
            Optional[Dashboard]: Active dashboard, or None if none is active
        """
        if self.active_dashboard_id:
            return self.dashboards.get(self.active_dashboard_id)
        return None
    
    async def set_active_dashboard(self, dashboard_id: str) -> None:
        """
        Set the active dashboard.
        
        Args:
            dashboard_id: Dashboard ID
        """
        if dashboard_id in self.dashboards:
            self.active_dashboard_id = dashboard_id
            await self.save_data()
    
    # Component Management Methods
    
    async def add_component(
        self,
        dashboard_id: str,
        component_type: DashboardComponentType,
        title: str,
        description: Optional[str] = None,
        position: Dict[str, int] = None,
        data_source: Optional[str] = None,
        refresh_interval: Optional[int] = None,
        config: Dict[str, Any] = None
    ) -> str:
        """
        Add a component to a dashboard.
        
        Args:
            dashboard_id: Dashboard ID
            component_type: Component type
            title: Component title
            description: Component description (optional)
            position: Component position (optional)
            data_source: Component data source (optional)
            refresh_interval: Component refresh interval (optional)
            config: Component configuration (optional)
            
        Returns:
            str: Component ID
        """
        if dashboard_id in self.dashboards:
            dashboard = self.dashboards[dashboard_id]
            
            component_id = str(uuid.uuid4())
            
            component = DashboardComponent(
                component_id=component_id,
                component_type=component_type,
                title=title,
                description=description,
                position=position or {"x": 0, "y": 0, "width": 1, "height": 1},
                data_source=data_source,
                refresh_interval=refresh_interval,
                config=config or {}
            )
            
            dashboard.components.append(component)
            dashboard.updated_at = datetime.now()
            
            self.metrics["components_created"] += 1
            
            await self.save_data()
            
            return component_id
        
        return None
    
    async def update_component(
        self,
        dashboard_id: str,
        component_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        position: Optional[Dict[str, int]] = None,
        data_source: Optional[str] = None,
        refresh_interval: Optional[int] = None,
        config: Optional[Dict[str, Any]] = None,
        is_active: Optional[bool] = None
    ) -> None:
        """
        Update a component.
        
        Args:
            dashboard_id: Dashboard ID
            component_id: Component ID
            title: New component title (optional)
            description: New component description (optional)
            position: New component position (optional)
            data_source: New component data source (optional)
            refresh_interval: New component refresh interval (optional)
            config: New component configuration (optional)
            is_active: Whether the component is active (optional)
        """
        if dashboard_id in self.dashboards:
            dashboard = self.dashboards[dashboard_id]
            
            for component in dashboard.components:
                if component.component_id == component_id:
                    if title is not None:
                        component.title = title
                    
                    if description is not None:
                        component.description = description
                    
                    if position is not None:
                        component.position = position
                    
                    if data_source is not None:
                        component.data_source = data_source
                    
                    if refresh_interval is not None:
                        component.refresh_interval = refresh_interval
                    
                    if config is not None:
                        component.config = config
                    
                    if is_active is not None:
                        component.is_active = is_active
                    
                    component.updated_at = datetime.now()
                    dashboard.updated_at = datetime.now()
                    
                    await self.save_data()
                    break
    
    async def remove_component(self, dashboard_id: str, component_id: str) -> None:
        """
        Remove a component from a dashboard.
        
        Args:
            dashboard_id: Dashboard ID
            component_id: Component ID
        """
        if dashboard_id in self.dashboards:
            dashboard = self.dashboards[dashboard_id]
            
            dashboard.components = [
                c for c in dashboard.components
                if c.component_id != component_id
            ]
            
            dashboard.updated_at = datetime.now()
            
            await self.save_data()
    
    async def get_component(self, dashboard_id: str, component_id: str) -> Optional[DashboardComponent]:
        """
        Get component information.
        
        Args:
            dashboard_id: Dashboard ID
            component_id: Component ID
            
        Returns:
            Optional[DashboardComponent]: Component information, or None if not found
        """
        if dashboard_id in self.dashboards:
            dashboard = self.dashboards[dashboard_id]
            
            for component in dashboard.components:
                if component.component_id == component_id:
                    return component
        
        return None
    
    async def get_component_data(self, component_id: str) -> Optional[Dict[str, Any]]:
        """
        Get component data.
        
        Args:
            component_id: Component ID
            
        Returns:
            Optional[Dict[str, Any]]: Component data, or None if not found
        """
        return self.component_data.get(component_id)
    
    # Data Update Methods
    
    async def _update_component_data(self) -> None:
        """Update component data based on refresh intervals"""
        while True:
            try:
                now = datetime.now()
                
                # Check each dashboard
                for dashboard in self.dashboards.values():
                    # Check each component
                    for component in dashboard.components:
                        # Skip inactive components
                        if not component.is_active:
                            continue
                        
                        # Skip components without data sources or refresh intervals
                        if not component.data_source or not component.refresh_interval:
                            continue
                        
                        # Check if it's time to refresh
                        last_update = self.component_data.get(component.component_id, {}).get("last_update")
                        if last_update:
                            last_update = datetime.fromisoformat(last_update)
                            if (now - last_update).total_seconds() < component.refresh_interval:
                                continue
                        
                        # Request data update
                        await self._request_component_data(component)
                
                await asyncio.sleep(1)  # Check every second
            except Exception as e:
                self.logger.error(f"Error updating component data: {str(e)}")
                await asyncio.sleep(60)
    
    async def _request_component_data(self, component: DashboardComponent) -> None:
        """
        Request data for a component.
        
        Args:
            component: Component to request data for
        """
        try:
            # Create a unique request ID
            request_id = str(uuid.uuid4())
            
            # Send data request message
            message = {
                "message_id": request_id,
                "message_type": MessageType.DATA_REQUEST.name,
                "priority": MessagePriority.MEDIUM.name,
                "sender": "dashboard_agent",
                "recipient": component.data_source,
                "content": {
                    "component_id": component.component_id,
                    "component_type": component.component_type.name,
                    "config": component.config
                },
                "timestamp": datetime.now().isoformat()
            }
            
            await this.message_broker.publish("data.request", message)
            
            self.logger.info(f"Requested data for component {component.component_id} from {component.data_source}")
            
        except Exception as e:
            self.logger.error(f"Error requesting component data: {str(e)}")
            this.metrics["errors"] += 1
    
    async def _handle_dashboard_data(self, message: Dict[str, Any]) -> None:
        """
        Handle dashboard data message.
        
        Args:
            message: Message containing dashboard data
        """
        try:
            # Extract component ID and data
            component_id = message.get("content", {}).get("component_id")
            data = message.get("content", {}).get("data")
            
            if component_id and data:
                # Update component data
                self.component_data[component_id] = {
                    "data": data,
                    "last_update": datetime.now().isoformat()
                }
                
                self.metrics["data_updates"] += 1
                
                # Save data
                await this.save_data()
                
                self.logger.info(f"Updated data for component {component_id}")
            
        except Exception as e:
            self.logger.error(f"Error handling dashboard data: {str(e)}")
            this.metrics["errors"] += 1
    
    async def _handle_dashboard_command(self, message: Dict[str, Any]) -> None:
        """
        Handle dashboard command message.
        
        Args:
            message: Message containing dashboard command
        """
        try:
            # Extract command and parameters
            command = message.get("content", {}).get("command")
            params = message.get("content", {}).get("params", {})
            
            if command == "create_dashboard":
                await this.create_dashboard(
                    name=params.get("name", "New Dashboard"),
                    description=params.get("description"),
                    layout_type=DashboardLayoutType[params.get("layout_type", "GRID")],
                    theme=DashboardTheme[params.get("theme", "MYCOLOGY")],
                    is_default=params.get("is_default", False),
                    owner=params.get("owner"),
                    permissions=params.get("permissions")
                )
            
            elif command == "update_dashboard":
                dashboard_id = params.get("dashboard_id")
                if dashboard_id:
                    await this.update_dashboard(
                        dashboard_id=dashboard_id,
                        name=params.get("name"),
                        description=params.get("description"),
                        layout_type=DashboardLayoutType[params.get("layout_type")] if params.get("layout_type") else None,
                        theme=DashboardTheme[params.get("theme")] if params.get("theme") else None,
                        is_default=params.get("is_default"),
                        owner=params.get("owner"),
                        permissions=params.get("permissions")
                    )
            
            elif command == "delete_dashboard":
                dashboard_id = params.get("dashboard_id")
                if dashboard_id:
                    await this.delete_dashboard(dashboard_id)
            
            elif command == "add_component":
                dashboard_id = params.get("dashboard_id")
                if dashboard_id:
                    await this.add_component(
                        dashboard_id=dashboard_id,
                        component_type=DashboardComponentType[params.get("component_type", "CHART")],
                        title=params.get("title", "New Component"),
                        description=params.get("description"),
                        position=params.get("position"),
                        data_source=params.get("data_source"),
                        refresh_interval=params.get("refresh_interval"),
                        config=params.get("config")
                    )
            
            elif command == "update_component":
                dashboard_id = params.get("dashboard_id")
                component_id = params.get("component_id")
                if dashboard_id and component_id:
                    await this.update_component(
                        dashboard_id=dashboard_id,
                        component_id=component_id,
                        title=params.get("title"),
                        description=params.get("description"),
                        position=params.get("position"),
                        data_source=params.get("data_source"),
                        refresh_interval=params.get("refresh_interval"),
                        config=params.get("config"),
                        is_active=params.get("is_active")
                    )
            
            elif command == "remove_component":
                dashboard_id = params.get("dashboard_id")
                component_id = params.get("component_id")
                if dashboard_id and component_id:
                    await this.remove_component(dashboard_id, component_id)
            
            elif command == "set_active_dashboard":
                dashboard_id = params.get("dashboard_id")
                if dashboard_id:
                    await this.set_active_dashboard(dashboard_id)
            
        except Exception as e:
            this.logger.error(f"Error handling dashboard command: {str(e)}")
            this.metrics["errors"] += 1
    
    async def _handle_dashboard_interaction(self, message: Dict[str, Any]) -> None:
        """
        Handle dashboard interaction message.
        
        Args:
            message: Message containing dashboard interaction
        """
        try:
            # Extract interaction details
            interaction_type = message.get("content", {}).get("type")
            component_id = message.get("content", {}).get("component_id")
            data = message.get("content", {}).get("data")
            
            if interaction_type and component_id:
                # Update metrics
                this.metrics["user_interactions"] += 1
                
                # Handle different interaction types
                if interaction_type == "click":
                    # Handle component click
                    await this._handle_component_click(component_id, data)
                
                elif interaction_type == "input":
                    # Handle component input
                    await this._handle_component_input(component_id, data)
                
                elif interaction_type == "drag":
                    # Handle component drag
                    await this._handle_component_drag(component_id, data)
                
                self.logger.info(f"Handled {interaction_type} interaction for component {component_id}")
            
        except Exception as e:
            this.logger.error(f"Error handling dashboard interaction: {str(e)}")
            this.metrics["errors"] += 1
    
    async def _handle_component_click(self, component_id: str, data: Dict[str, Any]) -> None:
        """
        Handle component click interaction.
        
        Args:
            component_id: Component ID
            data: Click data
        """
        # Find the component
        for dashboard in this.dashboards.values():
            for component in dashboard.components:
                if component.component_id == component_id:
                    # Handle based on component type
                    if component.component_type == DashboardComponentType.CONTROL:
                        # Send control command
                        await this._send_control_command(component, data)
                    
                    elif component.component_type == DashboardComponentType.CHART:
                        # Handle chart click (e.g., drill down)
                        await this._handle_chart_click(component, data)
                    
                    break
    
    async def _handle_component_input(self, component_id: str, data: Dict[str, Any]) -> None:
        """
        Handle component input interaction.
        
        Args:
            component_id: Component ID
            data: Input data
        """
        # Find the component
        for dashboard in this.dashboards.values():
            for component in dashboard.components:
                if component.component_id == component_id:
                    # Handle based on component type
                    if component.component_type == DashboardComponentType.CONTROL:
                        # Send control command
                        await this._send_control_command(component, data)
                    
                    break
    
    async def _handle_component_drag(self, component_id: str, data: Dict[str, Any]) -> None:
        """
        Handle component drag interaction.
        
        Args:
            component_id: Component ID
            data: Drag data
        """
        # Find the component
        for dashboard in this.dashboards.values():
            for component in dashboard.components:
                if component.component_id == component_id:
                    # Update component position
                    if "position" in data:
                        await this.update_component(
                            dashboard_id=dashboard.dashboard_id,
                            component_id=component_id,
                            position=data["position"]
                        )
                    break
    
    async def _send_control_command(self, component: DashboardComponent, data: Dict[str, Any]) -> None:
        """
        Send control command based on component configuration.
        
        Args:
            component: Component that triggered the command
            data: Command data
        """
        try:
            # Get command target from component config
            command_target = component.config.get("command_target")
            command_type = component.config.get("command_type")
            
            if command_target and command_type:
                # Create command message
                message = {
                    "message_id": str(uuid.uuid4()),
                    "message_type": MessageType.COMMAND.name,
                    "priority": MessagePriority.MEDIUM.name,
                    "sender": "dashboard_agent",
                    "recipient": command_target,
                    "content": {
                        "command": command_type,
                        "params": data
                    },
                    "timestamp": datetime.now().isoformat()
                }
                
                # Publish command message
                await this.message_broker.publish(f"{command_target}.command", message)
                
                this.logger.info(f"Sent command {command_type} to {command_target}")
            
        except Exception as e:
            this.logger.error(f"Error sending control command: {str(e)}")
            this.metrics["errors"] += 1
    
    async def _handle_chart_click(self, component: DashboardComponent, data: Dict[str, Any]) -> None:
        """
        Handle chart click interaction.
        
        Args:
            component: Chart component
            data: Click data
        """
        try:
            # Get chart configuration
            chart_type = component.config.get("chart_type")
            drill_down = component.config.get("drill_down", False)
            
            if drill_down and "series" in data and "point" in data:
                # Create drill-down request
                series = data["series"]
                point = data["point"]
                
                # Create drill-down component
                dashboard_id = None
                for d_id, d in this.dashboards.items():
                    for c in d.components:
                        if c.component_id == component.component_id:
                            dashboard_id = d_id
                            break
                    if dashboard_id:
                        break
                
                if dashboard_id:
                    # Create drill-down component
                    await this.add_component(
                        dashboard_id=dashboard_id,
                        component_type=DashboardComponentType.CHART,
                        title=f"{component.title} - {series} - {point}",
                        description=f"Drill-down view for {series} - {point}",
                        position={"x": 0, "y": 0, "width": 2, "height": 2},
                        data_source=component.data_source,
                        refresh_interval=component.refresh_interval,
                        config={
                            "chart_type": chart_type,
                            "drill_down": False,
                            "parent_component_id": component.component_id,
                            "series": series,
                            "point": point
                        }
                    )
            
        except Exception as e:
            this.logger.error(f"Error handling chart click: {str(e)}")
            this.metrics["errors"] += 1
    
    # Background Tasks
    
    async def _periodic_save(self) -> None:
        """Periodically save data to disk"""
        while True:
            try:
                await asyncio.sleep(300)  # Save every 5 minutes
                await this.save_data()
            except Exception as e:
                this.logger.error(f"Error in periodic save: {str(e)}")
                await asyncio.sleep(60) 