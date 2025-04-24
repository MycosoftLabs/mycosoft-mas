"""
Visualization Agent for User Interface Cluster

This module implements a visualization agent that provides specialized visualization
capabilities for the Mycosoft Multi-Agent System, working alongside the DashboardAgent
to deliver advanced data visualization features.
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

class VisualizationType(Enum):
    """Types of visualizations"""
    LINE_CHART = auto()
    BAR_CHART = auto()
    PIE_CHART = auto()
    SCATTER_PLOT = auto()
    HEATMAP = auto()
    NETWORK_GRAPH = auto()
    TREE_MAP = auto()
    SANKEY_DIAGRAM = auto()
    FORCE_DIRECTED_GRAPH = auto()
    GEOGRAPHICAL_MAP = auto()
    TIMELINE = auto()
    CUSTOM = auto()

class DataTransformationType(Enum):
    """Types of data transformations"""
    AGGREGATE = auto()
    FILTER = auto()
    SORT = auto()
    GROUP = auto()
    PIVOT = auto()
    NORMALIZE = auto()
    CUSTOM = auto()

class ColorScheme(Enum):
    """Available color schemes"""
    DEFAULT = auto()
    MYCOLOGY = auto()
    ACCESSIBLE = auto()
    DARK = auto()
    LIGHT = auto()
    CUSTOM = auto()

@dataclass
class DataTransformation:
    """Information about a data transformation"""
    transformation_id: str
    transformation_type: DataTransformationType
    config: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True

@dataclass
class VisualizationConfig:
    """Configuration for a visualization"""
    visualization_id: str
    visualization_type: VisualizationType
    title: str
    description: Optional[str] = None
    data_source: Optional[str] = None
    transformations: List[DataTransformation] = field(default_factory=list)
    color_scheme: ColorScheme = ColorScheme.MYCOLOGY
    config: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True

class VisualizationAgent:
    """
    Agent that provides visualization capabilities for the Mycosoft MAS.
    
    This class:
    1. Creates and manages visualization configurations
    2. Transforms data for visualization
    3. Generates visualization data
    4. Coordinates with the dashboard agent
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        message_broker: MessageBroker
    ):
        """
        Initialize the visualization agent.
        
        Args:
            config: Configuration dictionary for the visualization agent
            message_broker: Message broker instance for communication
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.message_broker = message_broker
        
        # Create data directory
        self.data_dir = Path("data/user_interface/visualizations")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Visualization registry
        self.visualizations: Dict[str, VisualizationConfig] = {}
        
        # Data cache
        self.data_cache: Dict[str, Dict[str, Any]] = {}
        
        # Metrics
        self.metrics = {
            "visualizations_created": 0,
            "transformations_applied": 0,
            "data_requests": 0,
            "errors": 0
        }
        
        # Load data
        self._load_data()
    
    def _load_data(self) -> None:
        """Load visualization data from disk"""
        try:
            # Load visualizations
            visualizations_file = self.data_dir / "visualizations.json"
            if visualizations_file.exists():
                with open(visualizations_file, "r") as f:
                    visualizations_data = json.load(f)
                    
                    for visualization_data in visualizations_data:
                        transformations = []
                        for transformation_data in visualization_data.get("transformations", []):
                            transformation = DataTransformation(
                                transformation_id=transformation_data["transformation_id"],
                                transformation_type=DataTransformationType[transformation_data["transformation_type"]],
                                config=transformation_data.get("config", {}),
                                created_at=datetime.fromisoformat(transformation_data["created_at"]),
                                updated_at=datetime.fromisoformat(transformation_data["updated_at"]),
                                is_active=transformation_data.get("is_active", True)
                            )
                            transformations.append(transformation)
                        
                        visualization = VisualizationConfig(
                            visualization_id=visualization_data["visualization_id"],
                            visualization_type=VisualizationType[visualization_data["visualization_type"]],
                            title=visualization_data["title"],
                            description=visualization_data.get("description"),
                            data_source=visualization_data.get("data_source"),
                            transformations=transformations,
                            color_scheme=ColorScheme[visualization_data.get("color_scheme", "MYCOLOGY")],
                            config=visualization_data.get("config", {}),
                            created_at=datetime.fromisoformat(visualization_data["created_at"]),
                            updated_at=datetime.fromisoformat(visualization_data["updated_at"]),
                            is_active=visualization_data.get("is_active", True)
                        )
                        
                        self.visualizations[visualization.visualization_id] = visualization
            
            # Load data cache
            data_cache_file = self.data_dir / "data_cache.json"
            if data_cache_file.exists():
                with open(data_cache_file, "r") as f:
                    self.data_cache = json.load(f)
            
            # Load metrics
            metrics_file = self.data_dir / "metrics.json"
            if metrics_file.exists():
                with open(metrics_file, "r") as f:
                    self.metrics = json.load(f)
                    
        except Exception as e:
            self.logger.error(f"Error loading visualization data: {str(e)}")
    
    async def save_data(self) -> None:
        """Save visualization data to disk"""
        try:
            # Save visualizations
            visualizations_file = self.data_dir / "visualizations.json"
            visualizations_data = []
            
            for visualization in self.visualizations.values():
                transformations_data = []
                for transformation in visualization.transformations:
                    transformation_data = {
                        "transformation_id": transformation.transformation_id,
                        "transformation_type": transformation.transformation_type.name,
                        "config": transformation.config,
                        "created_at": transformation.created_at.isoformat(),
                        "updated_at": transformation.updated_at.isoformat(),
                        "is_active": transformation.is_active
                    }
                    transformations_data.append(transformation_data)
                
                visualization_data = {
                    "visualization_id": visualization.visualization_id,
                    "visualization_type": visualization.visualization_type.name,
                    "title": visualization.title,
                    "description": visualization.description,
                    "data_source": visualization.data_source,
                    "transformations": transformations_data,
                    "color_scheme": visualization.color_scheme.name,
                    "config": visualization.config,
                    "created_at": visualization.created_at.isoformat(),
                    "updated_at": visualization.updated_at.isoformat(),
                    "is_active": visualization.is_active
                }
                visualizations_data.append(visualization_data)
            
            with open(visualizations_file, "w") as f:
                json.dump(visualizations_data, f, indent=2)
            
            # Save data cache
            data_cache_file = self.data_dir / "data_cache.json"
            with open(data_cache_file, "w") as f:
                json.dump(self.data_cache, f, indent=2)
            
            # Save metrics
            metrics_file = self.data_dir / "metrics.json"
            with open(metrics_file, "w") as f:
                json.dump(self.metrics, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error saving visualization data: {str(e)}")
    
    async def start(self) -> None:
        """Start the visualization agent"""
        self.logger.info("Starting visualization agent")
        
        # Subscribe to relevant message topics
        await self.message_broker.subscribe("visualization.command", self._handle_visualization_command)
        await self.message_broker.subscribe("visualization.data", self._handle_visualization_data)
        await self.message_broker.subscribe("visualization.request", self._handle_visualization_request)
        
        # Start background tasks
        asyncio.create_task(self._periodic_save())
        
        self.logger.info("Visualization agent started")
    
    async def stop(self) -> None:
        """Stop the visualization agent"""
        self.logger.info("Stopping visualization agent")
        
        # Unsubscribe from message topics
        await self.message_broker.unsubscribe("visualization.command", self._handle_visualization_command)
        await self.message_broker.unsubscribe("visualization.data", self._handle_visualization_data)
        await self.message_broker.unsubscribe("visualization.request", self._handle_visualization_request)
        
        # Save data
        await self.save_data()
        
        self.logger.info("Visualization agent stopped")
    
    # Visualization Management Methods
    
    async def create_visualization(
        self,
        visualization_type: VisualizationType,
        title: str,
        description: Optional[str] = None,
        data_source: Optional[str] = None,
        color_scheme: ColorScheme = ColorScheme.MYCOLOGY,
        config: Dict[str, Any] = None
    ) -> str:
        """
        Create a new visualization.
        
        Args:
            visualization_type: Type of visualization
            title: Visualization title
            description: Visualization description (optional)
            data_source: Data source for the visualization (optional)
            color_scheme: Color scheme for the visualization
            config: Visualization configuration (optional)
            
        Returns:
            str: Visualization ID
        """
        visualization_id = str(uuid.uuid4())
        
        visualization = VisualizationConfig(
            visualization_id=visualization_id,
            visualization_type=visualization_type,
            title=title,
            description=description,
            data_source=data_source,
            color_scheme=color_scheme,
            config=config or {}
        )
        
        self.visualizations[visualization_id] = visualization
        self.metrics["visualizations_created"] += 1
        
        await self.save_data()
        
        return visualization_id
    
    async def update_visualization(
        self,
        visualization_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        data_source: Optional[str] = None,
        color_scheme: Optional[ColorScheme] = None,
        config: Optional[Dict[str, Any]] = None,
        is_active: Optional[bool] = None
    ) -> None:
        """
        Update a visualization.
        
        Args:
            visualization_id: Visualization ID
            title: New visualization title (optional)
            description: New visualization description (optional)
            data_source: New data source (optional)
            color_scheme: New color scheme (optional)
            config: New visualization configuration (optional)
            is_active: Whether the visualization is active (optional)
        """
        if visualization_id in self.visualizations:
            visualization = self.visualizations[visualization_id]
            
            if title is not None:
                visualization.title = title
            
            if description is not None:
                visualization.description = description
            
            if data_source is not None:
                visualization.data_source = data_source
            
            if color_scheme is not None:
                visualization.color_scheme = color_scheme
            
            if config is not None:
                visualization.config = config
            
            if is_active is not None:
                visualization.is_active = is_active
            
            visualization.updated_at = datetime.now()
            
            await self.save_data()
    
    async def delete_visualization(self, visualization_id: str) -> None:
        """
        Delete a visualization.
        
        Args:
            visualization_id: Visualization ID
        """
        if visualization_id in self.visualizations:
            # Remove the visualization
            del self.visualizations[visualization_id]
            
            # Remove from data cache
            if visualization_id in self.data_cache:
                del self.data_cache[visualization_id]
            
            await self.save_data()
    
    async def get_visualization(self, visualization_id: str) -> Optional[VisualizationConfig]:
        """
        Get visualization information.
        
        Args:
            visualization_id: Visualization ID
            
        Returns:
            Optional[VisualizationConfig]: Visualization information, or None if not found
        """
        return self.visualizations.get(visualization_id)
    
    async def get_all_visualizations(self) -> List[VisualizationConfig]:
        """
        Get all visualizations.
        
        Returns:
            List[VisualizationConfig]: List of all visualizations
        """
        return list(self.visualizations.values())
    
    # Transformation Management Methods
    
    async def add_transformation(
        self,
        visualization_id: str,
        transformation_type: DataTransformationType,
        config: Dict[str, Any] = None
    ) -> str:
        """
        Add a transformation to a visualization.
        
        Args:
            visualization_id: Visualization ID
            transformation_type: Type of transformation
            config: Transformation configuration (optional)
            
        Returns:
            str: Transformation ID
        """
        if visualization_id in self.visualizations:
            visualization = self.visualizations[visualization_id]
            
            transformation_id = str(uuid.uuid4())
            
            transformation = DataTransformation(
                transformation_id=transformation_id,
                transformation_type=transformation_type,
                config=config or {}
            )
            
            visualization.transformations.append(transformation)
            visualization.updated_at = datetime.now()
            
            await self.save_data()
            
            return transformation_id
        
        return None
    
    async def update_transformation(
        self,
        visualization_id: str,
        transformation_id: str,
        config: Optional[Dict[str, Any]] = None,
        is_active: Optional[bool] = None
    ) -> None:
        """
        Update a transformation.
        
        Args:
            visualization_id: Visualization ID
            transformation_id: Transformation ID
            config: New transformation configuration (optional)
            is_active: Whether the transformation is active (optional)
        """
        if visualization_id in self.visualizations:
            visualization = self.visualizations[visualization_id]
            
            for transformation in visualization.transformations:
                if transformation.transformation_id == transformation_id:
                    if config is not None:
                        transformation.config = config
                    
                    if is_active is not None:
                        transformation.is_active = is_active
                    
                    transformation.updated_at = datetime.now()
                    visualization.updated_at = datetime.now()
                    
                    await self.save_data()
                    break
    
    async def remove_transformation(self, visualization_id: str, transformation_id: str) -> None:
        """
        Remove a transformation from a visualization.
        
        Args:
            visualization_id: Visualization ID
            transformation_id: Transformation ID
        """
        if visualization_id in self.visualizations:
            visualization = self.visualizations[visualization_id]
            
            visualization.transformations = [
                t for t in visualization.transformations
                if t.transformation_id != transformation_id
            ]
            
            visualization.updated_at = datetime.now()
            
            await self.save_data()
    
    async def get_transformation(self, visualization_id: str, transformation_id: str) -> Optional[DataTransformation]:
        """
        Get transformation information.
        
        Args:
            visualization_id: Visualization ID
            transformation_id: Transformation ID
            
        Returns:
            Optional[DataTransformation]: Transformation information, or None if not found
        """
        if visualization_id in self.visualizations:
            visualization = self.visualizations[visualization_id]
            
            for transformation in visualization.transformations:
                if transformation.transformation_id == transformation_id:
                    return transformation
        
        return None
    
    # Data Processing Methods
    
    async def process_visualization_data(
        self,
        visualization_id: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process data for a visualization.
        
        Args:
            visualization_id: Visualization ID
            data: Raw data to process
            
        Returns:
            Dict[str, Any]: Processed data for visualization
        """
        if visualization_id in self.visualizations:
            visualization = self.visualizations[visualization_id]
            
            # Apply transformations
            processed_data = data.copy()
            
            for transformation in visualization.transformations:
                if transformation.is_active:
                    processed_data = await self._apply_transformation(
                        processed_data,
                        transformation
                    )
            
            # Format data for visualization type
            formatted_data = await self._format_data_for_visualization(
                processed_data,
                visualization
            )
            
            # Cache the processed data
            self.data_cache[visualization_id] = {
                "data": formatted_data,
                "last_update": datetime.now().isoformat()
            }
            
            return formatted_data
        
        return data
    
    async def _apply_transformation(
        self,
        data: Dict[str, Any],
        transformation: DataTransformation
    ) -> Dict[str, Any]:
        """
        Apply a transformation to data.
        
        Args:
            data: Data to transform
            transformation: Transformation to apply
            
        Returns:
            Dict[str, Any]: Transformed data
        """
        try:
            if transformation.transformation_type == DataTransformationType.AGGREGATE:
                return await self._apply_aggregation(data, transformation.config)
            
            elif transformation.transformation_type == DataTransformationType.FILTER:
                return await self._apply_filter(data, transformation.config)
            
            elif transformation.transformation_type == DataTransformationType.SORT:
                return await self._apply_sort(data, transformation.config)
            
            elif transformation.transformation_type == DataTransformationType.GROUP:
                return await self._apply_group(data, transformation.config)
            
            elif transformation.transformation_type == DataTransformationType.PIVOT:
                return await self._apply_pivot(data, transformation.config)
            
            elif transformation.transformation_type == DataTransformationType.NORMALIZE:
                return await self._apply_normalize(data, transformation.config)
            
            elif transformation.transformation_type == DataTransformationType.CUSTOM:
                return await self._apply_custom_transformation(data, transformation.config)
            
            self.metrics["transformations_applied"] += 1
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error applying transformation: {str(e)}")
            self.metrics["errors"] += 1
            return data
    
    async def _apply_aggregation(self, data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply aggregation transformation.
        
        Args:
            data: Data to aggregate
            config: Aggregation configuration
            
        Returns:
            Dict[str, Any]: Aggregated data
        """
        # Implementation depends on data structure
        # This is a placeholder for the actual implementation
        return data
    
    async def _apply_filter(self, data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply filter transformation.
        
        Args:
            data: Data to filter
            config: Filter configuration
            
        Returns:
            Dict[str, Any]: Filtered data
        """
        # Implementation depends on data structure
        # This is a placeholder for the actual implementation
        return data
    
    async def _apply_sort(self, data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply sort transformation.
        
        Args:
            data: Data to sort
            config: Sort configuration
            
        Returns:
            Dict[str, Any]: Sorted data
        """
        # Implementation depends on data structure
        # This is a placeholder for the actual implementation
        return data
    
    async def _apply_group(self, data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply group transformation.
        
        Args:
            data: Data to group
            config: Group configuration
            
        Returns:
            Dict[str, Any]: Grouped data
        """
        # Implementation depends on data structure
        # This is a placeholder for the actual implementation
        return data
    
    async def _apply_pivot(self, data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply pivot transformation.
        
        Args:
            data: Data to pivot
            config: Pivot configuration
            
        Returns:
            Dict[str, Any]: Pivoted data
        """
        # Implementation depends on data structure
        # This is a placeholder for the actual implementation
        return data
    
    async def _apply_normalize(self, data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply normalize transformation.
        
        Args:
            data: Data to normalize
            config: Normalize configuration
            
        Returns:
            Dict[str, Any]: Normalized data
        """
        # Implementation depends on data structure
        # This is a placeholder for the actual implementation
        return data
    
    async def _apply_custom_transformation(self, data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply custom transformation.
        
        Args:
            data: Data to transform
            config: Custom transformation configuration
            
        Returns:
            Dict[str, Any]: Transformed data
        """
        # Implementation depends on custom transformation
        # This is a placeholder for the actual implementation
        return data
    
    async def _format_data_for_visualization(
        self,
        data: Dict[str, Any],
        visualization: VisualizationConfig
    ) -> Dict[str, Any]:
        """
        Format data for a specific visualization type.
        
        Args:
            data: Data to format
            visualization: Visualization configuration
            
        Returns:
            Dict[str, Any]: Formatted data
        """
        try:
            if visualization.visualization_type == VisualizationType.LINE_CHART:
                return await self._format_for_line_chart(data, visualization.config)
            
            elif visualization.visualization_type == VisualizationType.BAR_CHART:
                return await self._format_for_bar_chart(data, visualization.config)
            
            elif visualization.visualization_type == VisualizationType.PIE_CHART:
                return await self._format_for_pie_chart(data, visualization.config)
            
            elif visualization.visualization_type == VisualizationType.SCATTER_PLOT:
                return await self._format_for_scatter_plot(data, visualization.config)
            
            elif visualization.visualization_type == VisualizationType.HEATMAP:
                return await self._format_for_heatmap(data, visualization.config)
            
            elif visualization.visualization_type == VisualizationType.NETWORK_GRAPH:
                return await self._format_for_network_graph(data, visualization.config)
            
            elif visualization.visualization_type == VisualizationType.TREE_MAP:
                return await self._format_for_tree_map(data, visualization.config)
            
            elif visualization.visualization_type == VisualizationType.SANKEY_DIAGRAM:
                return await self._format_for_sankey_diagram(data, visualization.config)
            
            elif visualization.visualization_type == VisualizationType.FORCE_DIRECTED_GRAPH:
                return await this._format_for_force_directed_graph(data, visualization.config)
            
            elif visualization.visualization_type == VisualizationType.GEOGRAPHICAL_MAP:
                return await this._format_for_geographical_map(data, visualization.config)
            
            elif visualization.visualization_type == VisualizationType.TIMELINE:
                return await this._format_for_timeline(data, visualization.config)
            
            elif visualization.visualization_type == VisualizationType.CUSTOM:
                return await this._format_for_custom_visualization(data, visualization.config)
            
            return data
            
        except Exception as e:
            this.logger.error(f"Error formatting data for visualization: {str(e)}")
            this.metrics["errors"] += 1
            return data
    
    async def _format_for_line_chart(self, data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format data for line chart.
        
        Args:
            data: Data to format
            config: Line chart configuration
            
        Returns:
            Dict[str, Any]: Formatted data for line chart
        """
        # Implementation depends on data structure
        # This is a placeholder for the actual implementation
        return data
    
    async def _format_for_bar_chart(self, data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format data for bar chart.
        
        Args:
            data: Data to format
            config: Bar chart configuration
            
        Returns:
            Dict[str, Any]: Formatted data for bar chart
        """
        # Implementation depends on data structure
        # This is a placeholder for the actual implementation
        return data
    
    async def _format_for_pie_chart(self, data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format data for pie chart.
        
        Args:
            data: Data to format
            config: Pie chart configuration
            
        Returns:
            Dict[str, Any]: Formatted data for pie chart
        """
        # Implementation depends on data structure
        # This is a placeholder for the actual implementation
        return data
    
    async def _format_for_scatter_plot(self, data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format data for scatter plot.
        
        Args:
            data: Data to format
            config: Scatter plot configuration
            
        Returns:
            Dict[str, Any]: Formatted data for scatter plot
        """
        # Implementation depends on data structure
        # This is a placeholder for the actual implementation
        return data
    
    async def _format_for_heatmap(self, data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format data for heatmap.
        
        Args:
            data: Data to format
            config: Heatmap configuration
            
        Returns:
            Dict[str, Any]: Formatted data for heatmap
        """
        # Implementation depends on data structure
        # This is a placeholder for the actual implementation
        return data
    
    async def _format_for_network_graph(self, data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format data for network graph.
        
        Args:
            data: Data to format
            config: Network graph configuration
            
        Returns:
            Dict[str, Any]: Formatted data for network graph
        """
        # Implementation depends on data structure
        # This is a placeholder for the actual implementation
        return data
    
    async def _format_for_tree_map(self, data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format data for tree map.
        
        Args:
            data: Data to format
            config: Tree map configuration
            
        Returns:
            Dict[str, Any]: Formatted data for tree map
        """
        # Implementation depends on data structure
        # This is a placeholder for the actual implementation
        return data
    
    async def _format_for_sankey_diagram(self, data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format data for Sankey diagram.
        
        Args:
            data: Data to format
            config: Sankey diagram configuration
            
        Returns:
            Dict[str, Any]: Formatted data for Sankey diagram
        """
        # Implementation depends on data structure
        # This is a placeholder for the actual implementation
        return data
    
    async def _format_for_force_directed_graph(self, data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format data for force-directed graph.
        
        Args:
            data: Data to format
            config: Force-directed graph configuration
            
        Returns:
            Dict[str, Any]: Formatted data for force-directed graph
        """
        # Implementation depends on data structure
        # This is a placeholder for the actual implementation
        return data
    
    async def _format_for_geographical_map(self, data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format data for geographical map.
        
        Args:
            data: Data to format
            config: Geographical map configuration
            
        Returns:
            Dict[str, Any]: Formatted data for geographical map
        """
        # Implementation depends on data structure
        # This is a placeholder for the actual implementation
        return data
    
    async def _format_for_timeline(self, data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format data for timeline.
        
        Args:
            data: Data to format
            config: Timeline configuration
            
        Returns:
            Dict[str, Any]: Formatted data for timeline
        """
        # Implementation depends on data structure
        # This is a placeholder for the actual implementation
        return data
    
    async def _format_for_custom_visualization(self, data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format data for custom visualization.
        
        Args:
            data: Data to format
            config: Custom visualization configuration
            
        Returns:
            Dict[str, Any]: Formatted data for custom visualization
        """
        # Implementation depends on custom visualization
        # This is a placeholder for the actual implementation
        return data
    
    # Message Handling Methods
    
    async def _handle_visualization_command(self, message: Dict[str, Any]) -> None:
        """
        Handle visualization command message.
        
        Args:
            message: Message containing visualization command
        """
        try:
            # Extract command and parameters
            command = message.get("content", {}).get("command")
            params = message.get("content", {}).get("params", {})
            
            if command == "create_visualization":
                await this.create_visualization(
                    visualization_type=VisualizationType[params.get("visualization_type", "LINE_CHART")],
                    title=params.get("title", "New Visualization"),
                    description=params.get("description"),
                    data_source=params.get("data_source"),
                    color_scheme=ColorScheme[params.get("color_scheme", "MYCOLOGY")],
                    config=params.get("config")
                )
            
            elif command == "update_visualization":
                visualization_id = params.get("visualization_id")
                if visualization_id:
                    await this.update_visualization(
                        visualization_id=visualization_id,
                        title=params.get("title"),
                        description=params.get("description"),
                        data_source=params.get("data_source"),
                        color_scheme=ColorScheme[params.get("color_scheme")] if params.get("color_scheme") else None,
                        config=params.get("config"),
                        is_active=params.get("is_active")
                    )
            
            elif command == "delete_visualization":
                visualization_id = params.get("visualization_id")
                if visualization_id:
                    await this.delete_visualization(visualization_id)
            
            elif command == "add_transformation":
                visualization_id = params.get("visualization_id")
                if visualization_id:
                    await this.add_transformation(
                        visualization_id=visualization_id,
                        transformation_type=DataTransformationType[params.get("transformation_type", "AGGREGATE")],
                        config=params.get("config")
                    )
            
            elif command == "update_transformation":
                visualization_id = params.get("visualization_id")
                transformation_id = params.get("transformation_id")
                if visualization_id and transformation_id:
                    await this.update_transformation(
                        visualization_id=visualization_id,
                        transformation_id=transformation_id,
                        config=params.get("config"),
                        is_active=params.get("is_active")
                    )
            
            elif command == "remove_transformation":
                visualization_id = params.get("visualization_id")
                transformation_id = params.get("transformation_id")
                if visualization_id and transformation_id:
                    await this.remove_transformation(visualization_id, transformation_id)
            
        except Exception as e:
            this.logger.error(f"Error handling visualization command: {str(e)}")
            this.metrics["errors"] += 1
    
    async def _handle_visualization_data(self, message: Dict[str, Any]) -> None:
        """
        Handle visualization data message.
        
        Args:
            message: Message containing visualization data
        """
        try:
            # Extract visualization ID and data
            visualization_id = message.get("content", {}).get("visualization_id")
            data = message.get("content", {}).get("data")
            
            if visualization_id and data:
                # Process the data
                processed_data = await this.process_visualization_data(visualization_id, data)
                
                # Send the processed data to the dashboard agent
                await this._send_processed_data(visualization_id, processed_data)
                
                this.logger.info(f"Processed data for visualization {visualization_id}")
            
        except Exception as e:
            this.logger.error(f"Error handling visualization data: {str(e)}")
            this.metrics["errors"] += 1
    
    async def _handle_visualization_request(self, message: Dict[str, Any]) -> None:
        """
        Handle visualization request message.
        
        Args:
            message: Message containing visualization request
        """
        try:
            # Extract request details
            visualization_id = message.get("content", {}).get("visualization_id")
            data_source = message.get("content", {}).get("data_source")
            
            if visualization_id:
                # Check if we have cached data
                if visualization_id in this.data_cache:
                    cached_data = this.data_cache[visualization_id]
                    
                    # Check if the data is still fresh (less than 5 minutes old)
                    last_update = datetime.fromisoformat(cached_data["last_update"])
                    if (datetime.now() - last_update).total_seconds() < 300:
                        # Send the cached data
                        await this._send_processed_data(visualization_id, cached_data["data"])
                        return
                
                # Request data from the data source
                await this._request_data(visualization_id, data_source)
                
                this.metrics["data_requests"] += 1
                this.logger.info(f"Requested data for visualization {visualization_id}")
            
        except Exception as e:
            this.logger.error(f"Error handling visualization request: {str(e)}")
            this.metrics["errors"] += 1
    
    async def _request_data(self, visualization_id: str, data_source: Optional[str] = None) -> None:
        """
        Request data for a visualization.
        
        Args:
            visualization_id: Visualization ID
            data_source: Data source (optional)
        """
        try:
            # Get visualization
            visualization = this.visualizations.get(visualization_id)
            if not visualization:
                return
            
            # Use provided data source or visualization's data source
            source = data_source or visualization.data_source
            if not source:
                return
            
            # Create a unique request ID
            request_id = str(uuid.uuid4())
            
            # Send data request message
            message = {
                "message_id": request_id,
                "message_type": MessageType.DATA_REQUEST.name,
                "priority": MessagePriority.MEDIUM.name,
                "sender": "visualization_agent",
                "recipient": source,
                "content": {
                    "visualization_id": visualization_id,
                    "visualization_type": visualization.visualization_type.name,
                    "config": visualization.config
                },
                "timestamp": datetime.now().isoformat()
            }
            
            await this.message_broker.publish("data.request", message)
            
        except Exception as e:
            this.logger.error(f"Error requesting data: {str(e)}")
            this.metrics["errors"] += 1
    
    async def _send_processed_data(self, visualization_id: str, data: Dict[str, Any]) -> None:
        """
        Send processed data to the dashboard agent.
        
        Args:
            visualization_id: Visualization ID
            data: Processed data
        """
        try:
            # Create a unique message ID
            message_id = str(uuid.uuid4())
            
            # Send data message
            message = {
                "message_id": message_id,
                "message_type": MessageType.DATA_RESPONSE.name,
                "priority": MessagePriority.MEDIUM.name,
                "sender": "visualization_agent",
                "recipient": "dashboard_agent",
                "content": {
                    "visualization_id": visualization_id,
                    "data": data
                },
                "timestamp": datetime.now().isoformat()
            }
            
            await this.message_broker.publish("dashboard.data", message)
            
        except Exception as e:
            this.logger.error(f"Error sending processed data: {str(e)}")
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