from datetime import datetime, timedelta
import asyncio
import logging
from typing import Dict, List, Optional, Union, Any
from .base_agent import BaseAgent
from dataclasses import dataclass
from enum import Enum
import json
import numpy as np
import pandas as pd
from pathlib import Path
import uuid
import os
import re
from collections import defaultdict

class ExperimentStatus(Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ExperimentType(Enum):
    GROWTH = "growth"
    NUTRIENT = "nutrient"
    ENVIRONMENTAL = "environmental"
    GENETIC = "genetic"
    TOXICITY = "toxicity"
    BIOACTIVE = "bioactive"
    COMMUNICATION = "communication"
    CUSTOM = "custom"

class DataType(Enum):
    NUMERICAL = "numerical"
    CATEGORICAL = "categorical"
    IMAGE = "image"
    SEQUENCE = "sequence"
    TEXT = "text"
    SENSOR = "sensor"
    COMPOUND = "compound"

@dataclass
class Experiment:
    id: str
    name: str
    description: str
    experiment_type: ExperimentType
    status: ExperimentStatus
    start_date: datetime
    end_date: Optional[datetime]
    hypothesis: str
    methodology: str
    variables: Dict[str, Any]
    control_parameters: Dict[str, Any]
    samples: List[str]
    data_collection_points: List[Dict[str, Any]]
    results: Dict[str, Any]
    conclusions: Optional[str]
    created_at: datetime
    updated_at: datetime

class ExperimentAgent(BaseAgent):
    def __init__(self, agent_id: str, name: str, config: dict):
        super().__init__(agent_id, name, config)
        self.experiments = {}
        self.samples = {}
        self.data_storage = {}
        self.protocols = {}
        self.equipment = {}
        self.research_notes = {}
        self.notification_queue = asyncio.Queue()
        self.data_processing_queue = asyncio.Queue()
        self.data_directory = Path(config.get('data_directory', 'data/experiments'))
        self.data_directory.mkdir(parents=True, exist_ok=True)
        
    async def initialize(self):
        """Initialize the experiment agent with configurations and data."""
        await super().initialize()
        await self._load_experiment_data()
        await self._load_protocols()
        await self._load_equipment()
        await self._start_background_tasks()
        self.logger.info(f"Experiment Agent {self.name} initialized successfully")

    async def create_experiment(self, experiment_data: Dict) -> Dict:
        """Create a new scientific experiment."""
        try:
            experiment_id = experiment_data.get('id', f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            
            if experiment_id in self.experiments:
                return {"success": False, "message": "Experiment ID already exists"}
                
            experiment = Experiment(
                id=experiment_id,
                name=experiment_data['name'],
                description=experiment_data['description'],
                experiment_type=ExperimentType[experiment_data['type'].upper()],
                status=ExperimentStatus.PLANNED,
                start_date=datetime.fromisoformat(experiment_data['start_date']),
                end_date=datetime.fromisoformat(experiment_data['end_date']) if 'end_date' in experiment_data else None,
                hypothesis=experiment_data['hypothesis'],
                methodology=experiment_data['methodology'],
                variables=experiment_data.get('variables', {}),
                control_parameters=experiment_data.get('control_parameters', {}),
                samples=experiment_data.get('samples', []),
                data_collection_points=experiment_data.get('data_collection_points', []),
                results={},
                conclusions=None,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Validate experiment parameters
            validation_result = await self._validate_experiment(experiment)
            if not validation_result['success']:
                return validation_result
            
            # Create experiment directory
            experiment_dir = self.data_directory / experiment_id
            experiment_dir.mkdir(exist_ok=True)
            
            # Create subdirectories for different data types
            for data_type in DataType:
                (experiment_dir / data_type.value).mkdir(exist_ok=True)
            
            # Save experiment metadata
            with open(experiment_dir / 'metadata.json', 'w') as f:
                json.dump(self._experiment_to_dict(experiment), f, default=str)
            
            self.experiments[experiment_id] = experiment
            
            # Notify relevant team members
            await self.notification_queue.put({
                'type': 'experiment_created',
                'experiment_id': experiment_id,
                'experiment_name': experiment.name,
                'timestamp': datetime.now()
            })
            
            return {
                "success": True,
                "experiment_id": experiment_id,
                "message": "Experiment created successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create experiment: {str(e)}")
            return {"success": False, "message": str(e)}

    async def start_experiment(self, experiment_id: str) -> Dict:
        """Start a planned experiment."""
        try:
            if experiment_id not in self.experiments:
                return {"success": False, "message": "Experiment not found"}
                
            experiment = self.experiments[experiment_id]
            
            if experiment.status != ExperimentStatus.PLANNED:
                return {"success": False, "message": f"Experiment is already {experiment.status.value}"}
            
            # Check if all required resources are available
            resource_check = await self._check_resource_availability(experiment)
            if not resource_check['success']:
                return resource_check
            
            # Update experiment status
            experiment.status = ExperimentStatus.IN_PROGRESS
            experiment.updated_at = datetime.now()
            
            # Save updated metadata
            experiment_dir = self.data_directory / experiment_id
            with open(experiment_dir / 'metadata.json', 'w') as f:
                json.dump(self._experiment_to_dict(experiment), f, default=str)
            
            # Initialize data collection
            await self._initialize_data_collection(experiment)
            
            # Notify team members
            await self.notification_queue.put({
                'type': 'experiment_started',
                'experiment_id': experiment_id,
                'experiment_name': experiment.name,
                'timestamp': datetime.now()
            })
            
            return {
                "success": True,
                "message": f"Experiment {experiment.name} started successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to start experiment: {str(e)}")
            return {"success": False, "message": str(e)}

    async def record_data_point(self, experiment_id: str, data_point: Dict) -> Dict:
        """Record a data point for an experiment."""
        try:
            if experiment_id not in self.experiments:
                return {"success": False, "message": "Experiment not found"}
                
            experiment = self.experiments[experiment_id]
            
            if experiment.status != ExperimentStatus.IN_PROGRESS:
                return {"success": False, "message": f"Cannot record data for experiment in {experiment.status.value} status"}
            
            # Validate data point
            validation_result = await self._validate_data_point(data_point, experiment)
            if not validation_result['success']:
                return validation_result
            
            # Generate unique ID for data point
            data_point_id = f"dp_{uuid.uuid4().hex[:8]}"
            data_point['id'] = data_point_id
            data_point['timestamp'] = datetime.now().isoformat()
            
            # Save data point based on its type
            data_type = DataType[data_point['type'].upper()]
            experiment_dir = self.data_directory / experiment_id / data_type.value
            
            # Save data point
            data_file = experiment_dir / f"{data_point_id}.json"
            with open(data_file, 'w') as f:
                json.dump(data_point, f)
            
            # Add to experiment results
            if data_type.value not in experiment.results:
                experiment.results[data_type.value] = []
            experiment.results[data_type.value].append(data_point_id)
            
            # Update experiment metadata
            experiment.updated_at = datetime.now()
            with open(self.data_directory / experiment_id / 'metadata.json', 'w') as f:
                json.dump(self._experiment_to_dict(experiment), f, default=str)
            
            # Queue for processing
            await self.data_processing_queue.put({
                'experiment_id': experiment_id,
                'data_point_id': data_point_id,
                'data_type': data_type.value
            })
            
            return {
                "success": True,
                "data_point_id": data_point_id,
                "message": "Data point recorded successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to record data point: {str(e)}")
            return {"success": False, "message": str(e)}

    async def analyze_experiment_data(self, experiment_id: str, analysis_type: str = 'comprehensive') -> Dict:
        """Analyze experiment data and generate insights."""
        try:
            if experiment_id not in self.experiments:
                return {"success": False, "message": "Experiment not found"}
                
            experiment = self.experiments[experiment_id]
            
            # Load all data points
            data_points = await self._load_experiment_data_points(experiment_id)
            
            # Perform analysis based on type
            if analysis_type == 'comprehensive':
                analysis_results = await self._perform_comprehensive_analysis(experiment, data_points)
            elif analysis_type == 'statistical':
                analysis_results = await self._perform_statistical_analysis(experiment, data_points)
            elif analysis_type == 'visualization':
                analysis_results = await self._generate_visualizations(experiment, data_points)
            else:
                return {"success": False, "message": f"Unknown analysis type: {analysis_type}"}
            
            # Save analysis results
            analysis_dir = self.data_directory / experiment_id / 'analysis'
            analysis_dir.mkdir(exist_ok=True)
            
            analysis_file = analysis_dir / f"{analysis_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(analysis_file, 'w') as f:
                json.dump(analysis_results, f)
            
            return {
                "success": True,
                "analysis_type": analysis_type,
                "results": analysis_results,
                "message": f"{analysis_type.capitalize()} analysis completed successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze experiment data: {str(e)}")
            return {"success": False, "message": str(e)}

    async def complete_experiment(self, experiment_id: str, conclusions: str) -> Dict:
        """Complete an experiment and record conclusions."""
        try:
            if experiment_id not in self.experiments:
                return {"success": False, "message": "Experiment not found"}
                
            experiment = self.experiments[experiment_id]
            
            if experiment.status != ExperimentStatus.IN_PROGRESS:
                return {"success": False, "message": f"Cannot complete experiment in {experiment.status.value} status"}
            
            # Update experiment status
            experiment.status = ExperimentStatus.COMPLETED
            experiment.end_date = datetime.now()
            experiment.conclusions = conclusions
            experiment.updated_at = datetime.now()
            
            # Save updated metadata
            experiment_dir = self.data_directory / experiment_id
            with open(experiment_dir / 'metadata.json', 'w') as f:
                json.dump(self._experiment_to_dict(experiment), f, default=str)
            
            # Generate final report
            report = await self._generate_experiment_report(experiment)
            
            # Save report
            report_file = experiment_dir / 'final_report.json'
            with open(report_file, 'w') as f:
                json.dump(report, f)
            
            # Notify team members
            await self.notification_queue.put({
                'type': 'experiment_completed',
                'experiment_id': experiment_id,
                'experiment_name': experiment.name,
                'timestamp': datetime.now()
            })
            
            return {
                "success": True,
                "message": f"Experiment {experiment.name} completed successfully",
                "report_summary": report.get('summary', {})
            }
            
        except Exception as e:
            self.logger.error(f"Failed to complete experiment: {str(e)}")
            return {"success": False, "message": str(e)}

    async def create_research_note(self, note_data: Dict) -> Dict:
        """Create a research note related to experiments or findings."""
        try:
            note_id = note_data.get('id', f"note_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            
            note = {
                'id': note_id,
                'title': note_data['title'],
                'content': note_data['content'],
                'tags': note_data.get('tags', []),
                'related_experiments': note_data.get('related_experiments', []),
                'author': note_data.get('author', 'system'),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # Validate related experiments
            for exp_id in note['related_experiments']:
                if exp_id not in self.experiments:
                    return {"success": False, "message": f"Related experiment {exp_id} not found"}
            
            # Save note
            notes_dir = self.data_directory / 'research_notes'
            notes_dir.mkdir(exist_ok=True)
            
            note_file = notes_dir / f"{note_id}.json"
            with open(note_file, 'w') as f:
                json.dump(note, f)
            
            self.research_notes[note_id] = note
            
            return {
                "success": True,
                "note_id": note_id,
                "message": "Research note created successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create research note: {str(e)}")
            return {"success": False, "message": str(e)}

    async def _start_background_tasks(self):
        """Start background tasks for monitoring and maintenance."""
        asyncio.create_task(self._monitor_experiments())
        asyncio.create_task(self._process_data_queue())
        asyncio.create_task(self._process_notifications())
        asyncio.create_task(self._backup_experiment_data())

    async def _monitor_experiments(self):
        """Monitor active experiments and check for issues."""
        while True:
            for experiment_id, experiment in self.experiments.items():
                if experiment.status == ExperimentStatus.IN_PROGRESS:
                    # Check for data collection issues
                    issues = await self._check_data_collection_issues(experiment)
                    if issues:
                        await self.notification_queue.put({
                            'type': 'experiment_issue',
                            'experiment_id': experiment_id,
                            'issues': issues,
                            'timestamp': datetime.now()
                        })
                    
                    # Check for equipment issues
                    equipment_issues = await self._check_equipment_status(experiment)
                    if equipment_issues:
                        await self.notification_queue.put({
                            'type': 'equipment_issue',
                            'experiment_id': experiment_id,
                            'issues': equipment_issues,
                            'timestamp': datetime.now()
                        })
            
            await asyncio.sleep(300)  # Check every 5 minutes

    async def _process_data_queue(self):
        """Process data points in the queue."""
        while True:
            data_item = await self.data_processing_queue.get()
            try:
                await this._process_data_point(
                    data_item['experiment_id'],
                    data_item['data_point_id'],
                    data_item['data_type']
                )
            except Exception as e:
                self.logger.error(f"Failed to process data point: {str(e)}")
            finally:
                this.data_processing_queue.task_done()

    async def _process_notifications(self):
        """Process notifications in the queue."""
        while True:
            notification = await self.notification_queue.get()
            await this._handle_notification(notification)
            self.notification_queue.task_done()

    async def _backup_experiment_data(self):
        """Periodically backup experiment data."""
        while True:
            try:
                # Implementation for data backup
                await asyncio.sleep(86400)  # Backup once per day
            except Exception as e:
                self.logger.error(f"Failed to backup experiment data: {str(e)}")
                await asyncio.sleep(3600)  # Retry after an hour

    def _experiment_to_dict(self, experiment: Experiment) -> Dict:
        """Convert an Experiment object to a dictionary."""
        return {
            'id': experiment.id,
            'name': experiment.name,
            'description': experiment.description,
            'experiment_type': experiment.experiment_type.value,
            'status': experiment.status.value,
            'start_date': experiment.start_date.isoformat(),
            'end_date': experiment.end_date.isoformat() if experiment.end_date else None,
            'hypothesis': experiment.hypothesis,
            'methodology': experiment.methodology,
            'variables': experiment.variables,
            'control_parameters': experiment.control_parameters,
            'samples': experiment.samples,
            'data_collection_points': experiment.data_collection_points,
            'results': experiment.results,
            'conclusions': experiment.conclusions,
            'created_at': experiment.created_at.isoformat(),
            'updated_at': experiment.updated_at.isoformat()
        }

    async def _handle_error_type(self, error_type: str, error: Dict) -> Dict:
        """
        Handle experiment-specific error types.
        
        Args:
            error_type: Type of error to handle
            error: Error data dictionary
            
        Returns:
            Dict: Result of error handling
        """
        try:
            error_msg = error.get('error', 'Unknown error')
            error_data = error.get('data', {})
            
            if error_type == 'experiment_error':
                experiment_id = error_data.get('experiment_id')
                if experiment_id in self.experiments:
                    experiment = self.experiments[experiment_id]
                    # If experiment is in progress, pause it
                    if experiment.status == ExperimentStatus.IN_PROGRESS:
                        experiment.status = ExperimentStatus.PAUSED
                        experiment.updated_at = datetime.now()
                        # Save updated metadata
                        experiment_dir = self.data_directory / experiment_id
                        with open(experiment_dir / 'metadata.json', 'w') as f:
                            json.dump(self._experiment_to_dict(experiment), f, default=str)
                        # Notify team
                        asyncio.create_task(self.notification_queue.put({
                            'type': 'experiment_paused',
                            'experiment_id': experiment_id,
                            'error': error_msg,
                            'timestamp': datetime.now()
                        }))
                        self.logger.warning(f"Experiment {experiment_id} paused due to error: {error_msg}")
                        return {"success": True, "message": f"Experiment {experiment_id} paused", "action_taken": "pause_experiment"}
            
            elif error_type == 'data_collection_error':
                experiment_id = error_data.get('experiment_id')
                data_point_id = error_data.get('data_point_id')
                if experiment_id in self.experiments:
                    # Mark data point as invalid and schedule retry
                    if data_point_id:
                        asyncio.create_task(self.data_processing_queue.put({
                            'type': 'retry_data_collection',
                            'experiment_id': experiment_id,
                            'data_point_id': data_point_id,
                            'timestamp': datetime.now()
                        }))
                    self.logger.warning(f"Data collection error for experiment {experiment_id}, point {data_point_id}: {error_msg}")
                    return {"success": True, "message": "Data collection retry scheduled", "action_taken": "retry_collection"}
            
            elif error_type == 'equipment_error':
                equipment_id = error_data.get('equipment_id')
                if equipment_id in self.equipment:
                    # Mark equipment as malfunctioning
                    self.equipment[equipment_id]['status'] = 'malfunctioning'
                    self.equipment[equipment_id]['last_error'] = error_msg
                    self.equipment[equipment_id]['error_timestamp'] = datetime.now()
                    # Check affected experiments
                    affected_experiments = []
                    for exp_id, exp in self.experiments.items():
                        if equipment_id in exp.variables.get('equipment', []):
                            affected_experiments.append(exp_id)
                    if affected_experiments:
                        for exp_id in affected_experiments:
                            asyncio.create_task(self._handle_error_type('experiment_error', {
                                'error': f"Equipment {equipment_id} malfunction",
                                'data': {'experiment_id': exp_id}
                            }))
                    self.logger.warning(f"Equipment {equipment_id} marked as malfunctioning: {error_msg}")
                    return {"success": True, "message": f"Equipment {equipment_id} marked as malfunctioning", "action_taken": "mark_equipment_error"}
            
            elif error_type == 'analysis_error':
                experiment_id = error_data.get('experiment_id')
                analysis_type = error_data.get('analysis_type')
                if experiment_id in self.experiments:
                    # Mark analysis as failed and use fallback method if available
                    experiment = self.experiments[experiment_id]
                    if 'analysis_results' in experiment.results:
                        experiment.results['analysis_results'][analysis_type] = {
                            'status': 'failed',
                            'error': error_msg,
                            'timestamp': datetime.now()
                        }
                    # Try fallback analysis method
                    if analysis_type != 'basic':
                        asyncio.create_task(self.analyze_experiment_data(experiment_id, 'basic'))
                    self.logger.warning(f"Analysis error for experiment {experiment_id}, type {analysis_type}: {error_msg}")
                    return {"success": True, "message": "Fallback analysis scheduled", "action_taken": "use_fallback_analysis"}
            
            # Handle health check errors
            elif error_type == 'health_check_error':
                service = error_data.get('service', 'unknown')
                self.logger.error(f"Health check failed for {service}: {error_msg}")
                # Backup data for active experiments
                active_experiments = [
                    exp_id for exp_id, exp in self.experiments.items()
                    if exp.status == ExperimentStatus.IN_PROGRESS
                ]
                if active_experiments:
                    asyncio.create_task(self._backup_experiment_data())
                return {"success": True, "message": "Experiment data backup initiated", "action_taken": "backup_data"}
            
            # Default error handling
            self.logger.error(f"Unhandled error type {error_type}: {error_msg}")
            return {"success": False, "message": f"Unhandled error type: {error_type}", "action_taken": "none"}
            
        except Exception as e:
            self.logger.error(f"Error in error handler: {str(e)}")
            return {"success": False, "message": f"Error handler failed: {str(e)}", "action_taken": "none"} 