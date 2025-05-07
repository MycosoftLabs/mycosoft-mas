from datetime import datetime, timedelta
import asyncio
import logging
from typing import Dict, List, Optional, Union
from .base_agent import BaseAgent
import networkx as nx
from dataclasses import dataclass
from enum import Enum
import json

class ProjectStatus(Enum):
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class TaskPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class Task:
    id: str
    name: str
    description: str
    priority: TaskPriority
    assignee: str
    due_date: datetime
    dependencies: List[str]
    status: str
    progress: float
    created_at: datetime
    updated_at: datetime

class ProjectManagerAgent(BaseAgent):
    def __init__(self, agent_id: str, name: str, config: dict):
        super().__init__(agent_id=agent_id, name=name, config=config)
        self.projects = {}
        self.tasks = {}
        self.resource_pool = {}
        self.project_dependencies = nx.DiGraph()
        self.task_dependencies = nx.DiGraph()
        self.metrics = {
            'project_health': {},
            'resource_utilization': {},
            'deadline_compliance': {},
            'budget_tracking': {}
        }
        self.notification_queue = asyncio.Queue()
        
    async def initialize(self, integration_service):
        """Initialize the project manager agent with configurations and data."""
        await super().initialize(integration_service)
        await self._load_project_data()
        await self._load_resource_data()
        await self._start_background_tasks()
        self.logger.info(f"Project Manager Agent {self.name} initialized successfully")

    async def create_project(self, project_data: Dict) -> Dict:
        """Create a new project with specified parameters."""
        try:
            project_id = project_data.get('id', f"proj_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            
            if project_id in self.projects:
                return {"success": False, "message": "Project ID already exists"}
                
            project = {
                'id': project_id,
                'name': project_data['name'],
                'description': project_data['description'],
                'start_date': datetime.fromisoformat(project_data['start_date']),
                'end_date': datetime.fromisoformat(project_data['end_date']),
                'status': ProjectStatus.PLANNING,
                'owner': project_data['owner'],
                'team': project_data.get('team', []),
                'budget': project_data.get('budget', 0),
                'tasks': [],
                'dependencies': project_data.get('dependencies', []),
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            # Add project dependencies to graph
            self.project_dependencies.add_node(project_id)
            for dep in project['dependencies']:
                if dep in self.projects:
                    self.project_dependencies.add_edge(dep, project_id)
            
            self.projects[project_id] = project
            await self._update_project_metrics(project_id)
            
            return {
                "success": True,
                "project_id": project_id,
                "message": "Project created successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create project: {str(e)}")
            return {"success": False, "message": str(e)}

    async def create_task(self, project_id: str, task_data: Dict) -> Dict:
        """Create a new task within a project."""
        try:
            if project_id not in self.projects:
                return {"success": False, "message": "Project not found"}
                
            task_id = task_data.get('id', f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            
            if task_id in self.tasks:
                return {"success": False, "message": "Task ID already exists"}
                
            task = Task(
                id=task_id,
                name=task_data['name'],
                description=task_data['description'],
                priority=TaskPriority[task_data['priority'].upper()],
                assignee=task_data['assignee'],
                due_date=datetime.fromisoformat(task_data['due_date']),
                dependencies=task_data.get('dependencies', []),
                status='pending',
                progress=0.0,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Add task dependencies to graph
            self.task_dependencies.add_node(task_id)
            for dep in task.dependencies:
                if dep in self.tasks:
                    self.task_dependencies.add_edge(dep, task_id)
            
            self.tasks[task_id] = task
            self.projects[project_id]['tasks'].append(task_id)
            
            # Notify assignee
            await self.notification_queue.put({
                'type': 'task_assigned',
                'task_id': task_id,
                'assignee': task.assignee,
                'project_id': project_id
            })
            
            return {
                "success": True,
                "task_id": task_id,
                "message": "Task created successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create task: {str(e)}")
            return {"success": False, "message": str(e)}

    async def update_task_status(self, task_id: str, status: str, progress: float) -> Dict:
        """Update task status and progress."""
        try:
            if task_id not in self.tasks:
                return {"success": False, "message": "Task not found"}
                
            task = self.tasks[task_id]
            old_status = task.status
            task.status = status
            task.progress = progress
            task.updated_at = datetime.now()
            
            # Check if this update affects dependent tasks
            dependent_tasks = list(self.task_dependencies.successors(task_id))
            if dependent_tasks:
                await self.notification_queue.put({
                    'type': 'task_dependency_update',
                    'task_id': task_id,
                    'dependent_tasks': dependent_tasks,
                    'status': status
                })
            
            # Update project metrics
            for project_id, project in self.projects.items():
                if task_id in project['tasks']:
                    await self._update_project_metrics(project_id)
                    break
            
            return {
                "success": True,
                "message": f"Task status updated from {old_status} to {status}"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to update task status: {str(e)}")
            return {"success": False, "message": str(e)}

    async def assign_resources(self, project_id: str, resources: Dict[str, List[str]]) -> Dict:
        """Assign resources to a project."""
        try:
            if project_id not in self.projects:
                return {"success": False, "message": "Project not found"}
                
            project = self.projects[project_id]
            
            # Validate resource availability
            for resource_type, resource_ids in resources.items():
                for resource_id in resource_ids:
                    if not await self._check_resource_availability(resource_id, project['start_date'], project['end_date']):
                        return {
                            "success": False,
                            "message": f"Resource {resource_id} not available for the specified period"
                        }
            
            # Assign resources
            project['resources'] = resources
            await self._update_resource_utilization()
            
            return {
                "success": True,
                "message": "Resources assigned successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to assign resources: {str(e)}")
            return {"success": False, "message": str(e)}

    async def generate_project_report(self, project_id: str) -> Dict:
        """Generate a comprehensive project report."""
        try:
            if project_id not in self.projects:
                return {"success": False, "message": "Project not found"}
                
            project = self.projects[project_id]
            tasks = [self.tasks[task_id] for task_id in project['tasks']]
            
            report = {
                'project_overview': {
                    'name': project['name'],
                    'status': project['status'].value,
                    'progress': sum(t.progress for t in tasks) / len(tasks) if tasks else 0,
                    'start_date': project['start_date'].isoformat(),
                    'end_date': project['end_date'].isoformat(),
                    'days_remaining': (project['end_date'] - datetime.now()).days
                },
                'tasks_summary': {
                    'total': len(tasks),
                    'completed': len([t for t in tasks if t.status == 'completed']),
                    'in_progress': len([t for t in tasks if t.status == 'in_progress']),
                    'pending': len([t for t in tasks if t.status == 'pending'])
                },
                'resource_utilization': self.metrics['resource_utilization'].get(project_id, {}),
                'budget_tracking': self.metrics['budget_tracking'].get(project_id, {}),
                'risks_and_issues': await self._analyze_project_risks(project_id),
                'recommendations': await self._generate_recommendations(project_id)
            }
            
            return {
                "success": True,
                "report": report
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate project report: {str(e)}")
            return {"success": False, "message": str(e)}

    async def _start_background_tasks(self):
        """Start background tasks for monitoring and maintenance."""
        asyncio.create_task(self._monitor_project_health())
        asyncio.create_task(self._process_notifications())
        asyncio.create_task(self._update_metrics())

    async def _monitor_project_health(self):
        """Monitor project health and trigger alerts if needed."""
        while True:
            for project_id, project in self.projects.items():
                health_score = await self._calculate_project_health(project_id)
                if health_score < 0.6:  # Alert threshold
                    await self.notification_queue.put({
                        'type': 'project_health_alert',
                        'project_id': project_id,
                        'health_score': health_score,
                        'timestamp': datetime.now()
                    })
            await asyncio.sleep(3600)  # Check every hour

    async def _process_notifications(self):
        """Process notifications in the queue."""
        while True:
            notification = await self.notification_queue.get()
            await self._handle_notification(notification)
            self.notification_queue.task_done()

    async def _update_metrics(self):
        """Update project and resource metrics."""
        while True:
            for project_id in self.projects:
                await self._update_project_metrics(project_id)
            await self._update_resource_utilization()
            await asyncio.sleep(900)  # Update every 15 minutes

    async def _calculate_project_health(self, project_id: str) -> float:
        """Calculate project health score based on various metrics."""
        # Implementation for calculating project health
        pass

    async def _analyze_project_risks(self, project_id: str) -> List[Dict]:
        """Analyze and identify project risks."""
        # Implementation for risk analysis
        pass

    async def _generate_recommendations(self, project_id: str) -> List[Dict]:
        """Generate recommendations for project improvement."""
        # TODO: Implement recommendation generation logic
        pass

    async def _handle_error_type(self, error: Dict) -> Dict:
        """Handle specific error types for project management."""
        try:
            error_type = error.get('type', 'unknown')
            error_data = error.get('data', {})
            
            if error_type == 'project_error':
                project_id = error_data.get('project_id')
                if project_id in self.projects:
                    # Put project on hold and notify team
                    self.projects[project_id]['status'] = ProjectStatus.ON_HOLD
                    await self.notification_queue.put({
                        'type': 'project_on_hold',
                        'project_id': project_id,
                        'reason': error_data.get('message', 'Unknown error')
                    })
                    return {
                        'success': True,
                        'action': 'project_put_on_hold',
                        'project_id': project_id
                    }
                    
            elif error_type == 'task_error':
                task_id = error_data.get('task_id')
                if task_id in self.tasks:
                    # Reassign task and update dependencies
                    task = self.tasks[task_id]
                    old_assignee = task.assignee
                    # Find new assignee from resource pool
                    new_assignee = next((r for r in self.resource_pool if r != old_assignee), None)
                    if new_assignee:
                        task.assignee = new_assignee
                        await self.notification_queue.put({
                            'type': 'task_reassigned',
                            'task_id': task_id,
                            'old_assignee': old_assignee,
                            'new_assignee': new_assignee
                        })
                        return {
                            'success': True,
                            'action': 'task_reassigned',
                            'task_id': task_id
                        }
                        
            elif error_type == 'dependency_error':
                # Handle circular dependencies or broken dependency chains
                project_id = error_data.get('project_id')
                task_id = error_data.get('task_id')
                if project_id in self.projects and task_id in self.tasks:
                    # Remove problematic dependencies
                    if task_id in self.task_dependencies:
                        self.task_dependencies.remove_node(task_id)
                    if project_id in self.project_dependencies:
                        self.project_dependencies.remove_node(project_id)
                    return {
                        'success': True,
                        'action': 'dependencies_cleared',
                        'project_id': project_id,
                        'task_id': task_id
                    }
                    
            elif error_type == 'resource_error':
                # Handle resource allocation issues
                resource_id = error_data.get('resource_id')
                if resource_id in self.resource_pool:
                    # Mark resource as unavailable
                    self.resource_pool[resource_id]['available'] = False
                    await self.notification_queue.put({
                        'type': 'resource_unavailable',
                        'resource_id': resource_id
                    })
                    return {
                        'success': True,
                        'action': 'resource_marked_unavailable',
                        'resource_id': resource_id
                    }
                    
            elif error_type == 'health_check_error':
                # Put all active projects on hold during system issues
                affected_projects = []
                for project_id, project in self.projects.items():
                    if project['status'] == ProjectStatus.IN_PROGRESS:
                        project['status'] = ProjectStatus.ON_HOLD
                        affected_projects.append(project_id)
                
                if affected_projects:
                    await self.notification_queue.put({
                        'type': 'system_maintenance',
                        'affected_projects': affected_projects
                    })
                    return {
                        'success': True,
                        'action': 'projects_put_on_hold',
                        'affected_projects': affected_projects
                    }
            
            # Default case for unhandled error types
            self.logger.warning(f"Unhandled error type: {error_type}")
            return {
                'success': False,
                'action': 'error_not_handled',
                'error_type': error_type
            }
            
        except Exception as e:
            self.logger.error(f"Error handling failed: {str(e)}")
            return {
                'success': False,
                'action': 'error_handling_failed',
                'error': str(e)
            }

    async def _find_alternative_resource(self, project_id: str, resource_id: str) -> Optional[str]:
        """Find an alternative resource for a project when the original becomes unavailable."""
        try:
            if project_id not in self.projects:
                return None
                
            project = self.projects[project_id]
            resource_type = self.resource_pool[resource_id].get('type')
            
            # Find available resources of the same type
            available_resources = [
                r_id for r_id, r_data in self.resource_pool.items()
                if r_data.get('type') == resource_type and r_data.get('status') == 'available'
            ]
            
            if available_resources:
                new_resource_id = available_resources[0]
                # Update project resources
                if 'resources' in project:
                    project['resources'] = [
                        new_resource_id if r == resource_id else r
                        for r in project['resources']
                    ]
                self.logger.info(f"Found alternative resource {new_resource_id} for {resource_id}")
                return new_resource_id
                
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to find alternative resource: {str(e)}")
            return None 