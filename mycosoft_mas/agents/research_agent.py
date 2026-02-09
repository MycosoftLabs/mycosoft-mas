"""
Research Agent for Mycosoft MAS

This module implements the ResearchAgent class that handles research operations,
including literature review, data analysis, and knowledge synthesis.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import json
import uuid
from dataclasses import dataclass
from enum import Enum

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.messaging.message_types import Message, MessageType, MessagePriority
from mycosoft_mas.agents.enums import AgentStatus, TaskType, TaskStatus, TaskPriority

class ResearchType(Enum):
    LITERATURE_REVIEW = "literature_review"
    DATA_ANALYSIS = "data_analysis"
    EXPERIMENTAL = "experimental"
    META_ANALYSIS = "meta_analysis"
    SYSTEMATIC_REVIEW = "systematic_review"
    CASE_STUDY = "case_study"

class ResearchStatus(Enum):
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"

@dataclass
class ResearchProject:
    id: str
    title: str
    description: str
    research_type: ResearchType
    status: ResearchStatus
    start_date: datetime
    end_date: datetime
    team: List[str]
    objectives: List[str]
    methodology: Dict[str, Any]
    findings: Dict[str, Any]
    references: List[str]
    created_at: datetime
    updated_at: datetime

class ResearchAgent(BaseAgent):
    """
    Agent responsible for managing research operations.
    
    This agent handles:
    - Research project management
    - Literature review and analysis
    - Data collection and processing
    - Knowledge synthesis
    - Research collaboration
    """
    
    def __init__(self, agent_id: str, name: str, config: dict):
        """Initialize the Research Agent.
        
        Args:
            agent_id: Unique identifier for the agent
            name: Human-readable name for the agent
            config: Configuration dictionary for the agent
        """
        super().__init__(agent_id=agent_id, name=name, config=config)
        
        # Initialize research state
        self.research_projects = {}
        self.literature_reviews = {}
        self.data_sources = {}
        self.analysis_results = {}
        self.collaborations = {}
        
        # Initialize queues
        self.research_queue = asyncio.Queue()
        self.analysis_queue = asyncio.Queue()
        self.review_queue = asyncio.Queue()
        
        # Create data directory
        self.data_dir = Path("data/research")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Metrics
        self.metrics.update({
            "projects_managed": 0,
            "papers_reviewed": 0,
            "analyses_completed": 0,
            "collaborations_established": 0
        })
    
    async def initialize(self) -> bool:
        """Initialize the Research Agent."""
        try:
            await super().initialize()
            await self._load_research_data()
            await self._initialize_research_services()
            await self._start_background_tasks()
            self.logger.info(f"Research Agent {self.name} initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize Research Agent: {str(e)}")
            return False
    
    async def create_research_project(self, project_data: Dict) -> Dict:
        """Create a new research project."""
        try:
            project_id = f"proj_{uuid.uuid4().hex[:8]}"
            
            project = ResearchProject(
                id=project_id,
                title=project_data['title'],
                description=project_data['description'],
                research_type=ResearchType[project_data['type'].upper()],
                status=ResearchStatus.PLANNING,
                start_date=datetime.fromisoformat(project_data['start_date']),
                end_date=datetime.fromisoformat(project_data['end_date']),
                team=project_data.get('team', []),
                objectives=project_data.get('objectives', []),
                methodology=project_data.get('methodology', {}),
                findings={},
                references=[],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            self.research_projects[project_id] = project
            await self._save_research_project(project)
            
            return {
                "success": True,
                "project_id": project_id,
                "message": "Research project created successfully"
            }
        except Exception as e:
            self.logger.error(f"Failed to create research project: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def conduct_literature_review(self, review_data: Dict) -> Dict:
        """Conduct a literature review."""
        try:
            review_id = f"rev_{uuid.uuid4().hex[:8]}"
            
            review = {
                'id': review_id,
                'project_id': review_data['project_id'],
                'search_terms': review_data['search_terms'],
                'sources': review_data.get('sources', []),
                'inclusion_criteria': review_data.get('inclusion_criteria', {}),
                'exclusion_criteria': review_data.get('exclusion_criteria', {}),
                'papers_reviewed': [],
                'findings': {},
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            self.literature_reviews[review_id] = review
            await self._save_literature_review(review)
            
            # Add to review queue
            await self.review_queue.put({
                'review_id': review_id,
                'review_data': review_data
            })
            
            return {
                "success": True,
                "review_id": review_id,
                "message": "Literature review started"
            }
        except Exception as e:
            self.logger.error(f"Failed to start literature review: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def analyze_research_data(self, analysis_data: Dict) -> Dict:
        """Analyze research data."""
        try:
            analysis_id = f"ana_{uuid.uuid4().hex[:8]}"
            
            analysis = {
                'id': analysis_id,
                'project_id': analysis_data['project_id'],
                'data_sources': analysis_data['data_sources'],
                'analysis_type': analysis_data['analysis_type'],
                'parameters': analysis_data.get('parameters', {}),
                'results': {},
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            self.analysis_results[analysis_id] = analysis
            await self._save_analysis_result(analysis)
            
            # Add to analysis queue
            await self.analysis_queue.put({
                'analysis_id': analysis_id,
                'analysis_data': analysis_data
            })
            
            return {
                "success": True,
                "analysis_id": analysis_id,
                "message": "Data analysis started"
            }
        except Exception as e:
            self.logger.error(f"Failed to start data analysis: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def _load_research_data(self) -> None:
        """Load research data from storage."""
        try:
            # Load research projects
            projects_file = self.data_dir / "projects.json"
            if projects_file.exists():
                with open(projects_file, "r") as f:
                    projects_data = json.load(f)
                    for project_data in projects_data:
                        project = ResearchProject(
                            id=project_data["id"],
                            title=project_data["title"],
                            description=project_data["description"],
                            research_type=ResearchType[project_data["research_type"]],
                            status=ResearchStatus[project_data["status"]],
                            start_date=datetime.fromisoformat(project_data["start_date"]),
                            end_date=datetime.fromisoformat(project_data["end_date"]),
                            team=project_data["team"],
                            objectives=project_data["objectives"],
                            methodology=project_data["methodology"],
                            findings=project_data["findings"],
                            references=project_data["references"],
                            created_at=datetime.fromisoformat(project_data["created_at"]),
                            updated_at=datetime.fromisoformat(project_data["updated_at"])
                        )
                        self.research_projects[project.id] = project
            
            # Load literature reviews
            reviews_file = self.data_dir / "reviews.json"
            if reviews_file.exists():
                with open(reviews_file, "r") as f:
                    self.literature_reviews = json.load(f)
            
            # Load analysis results
            analyses_file = self.data_dir / "analyses.json"
            if analyses_file.exists():
                with open(analyses_file, "r") as f:
                    self.analysis_results = json.load(f)
            
        except Exception as e:
            self.logger.error(f"Error loading research data: {str(e)}")
            raise
    
    async def _initialize_research_services(self) -> None:
        """Initialize research services."""
        # TODO: Initialize research-specific services
        pass
    
    async def _start_background_tasks(self) -> None:
        """Start background tasks."""
        asyncio.create_task(self._process_research_queue())
        asyncio.create_task(self._process_analysis_queue())
        asyncio.create_task(self._process_review_queue())
        asyncio.create_task(self._monitor_research_projects())
    
    async def _process_research_queue(self) -> None:
        """Process the research queue."""
        while self.is_running:
            try:
                research_item = await self.research_queue.get()
                await self._handle_research_task(research_item)
                self.research_queue.task_done()
            except Exception as e:
                self.logger.error(f"Error processing research queue: {str(e)}")
                await asyncio.sleep(1)
    
    async def _process_analysis_queue(self) -> None:
        """Process the analysis queue."""
        while self.is_running:
            try:
                analysis_item = await self.analysis_queue.get()
                await self._handle_analysis_task(analysis_item)
                self.analysis_queue.task_done()
            except Exception as e:
                self.logger.error(f"Error processing analysis queue: {str(e)}")
                await asyncio.sleep(1)
    
    async def _process_review_queue(self) -> None:
        """Process the review queue."""
        while self.is_running:
            try:
                review_item = await self.review_queue.get()
                await self._handle_review_task(review_item)
                self.review_queue.task_done()
            except Exception as e:
                self.logger.error(f"Error processing review queue: {str(e)}")
                await asyncio.sleep(1)
    
    async def _monitor_research_projects(self) -> None:
        """Monitor research projects."""
        while self.is_running:
            try:
                for project in self.research_projects.values():
                    if project.status == ResearchStatus.IN_PROGRESS:
                        await self._check_project_progress(project)
                await asyncio.sleep(3600)  # Check every hour
            except Exception as e:
                self.logger.error(f"Error monitoring research projects: {str(e)}")
                await asyncio.sleep(60)
    
    async def _handle_research_task(self, task: Dict) -> None:
        """Handle a research task."""
        # TODO: Implement research task handling
        pass
    
    async def _handle_analysis_task(self, task: Dict) -> None:
        """Handle an analysis task."""
        # TODO: Implement analysis task handling
        pass
    
    async def _handle_review_task(self, task: Dict) -> None:
        """Handle a review task."""
        # TODO: Implement review task handling
        pass
    
    async def _check_project_progress(self, project: ResearchProject) -> None:
        """Check project progress and update status."""
        # TODO: Implement project progress checking
        pass
    
    async def _save_research_project(self, project: ResearchProject) -> None:
        """Save a research project."""
        try:
            projects_file = self.data_dir / "projects.json"
            projects_data = []
            
            if projects_file.exists():
                with open(projects_file, "r") as f:
                    projects_data = json.load(f)
            
            project_dict = {
                "id": project.id,
                "title": project.title,
                "description": project.description,
                "research_type": project.research_type.value,
                "status": project.status.value,
                "start_date": project.start_date.isoformat(),
                "end_date": project.end_date.isoformat(),
                "team": project.team,
                "objectives": project.objectives,
                "methodology": project.methodology,
                "findings": project.findings,
                "references": project.references,
                "created_at": project.created_at.isoformat(),
                "updated_at": project.updated_at.isoformat()
            }
            
            projects_data.append(project_dict)
            
            with open(projects_file, "w") as f:
                json.dump(projects_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error saving research project: {str(e)}")
            raise
    
    async def _save_literature_review(self, review: Dict) -> None:
        """Save a literature review."""
        try:
            reviews_file = self.data_dir / "reviews.json"
            reviews_data = []
            
            if reviews_file.exists():
                with open(reviews_file, "r") as f:
                    reviews_data = json.load(f)
            
            reviews_data.append(review)
            
            with open(reviews_file, "w") as f:
                json.dump(reviews_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error saving literature review: {str(e)}")
            raise
    
    async def _save_analysis_result(self, analysis: Dict) -> None:
        """Save an analysis result."""
        try:
            analyses_file = self.data_dir / "analyses.json"
            analyses_data = []
            
            if analyses_file.exists():
                with open(analyses_file, "r") as f:
                    analyses_data = json.load(f)
            
            analyses_data.append(analysis)
            
            with open(analyses_file, "w") as f:
                json.dump(analyses_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error saving analysis result: {str(e)}")
            raise
    
    async def _handle_error_type(self, error_type: str, error: Dict) -> Dict:
        """Handle research-specific error types."""
        try:
            error_msg = error.get('error', 'Unknown error')
            error_data = error.get('data', {})
            
            if error_type == 'project_error':
                project_id = error_data.get('project_id')
                if project_id in self.research_projects:
                    project = self.research_projects[project_id]
                    project.status = ResearchStatus.ON_HOLD
                    self.logger.warning(f"Project {project_id} put on hold due to error: {error_msg}")
                    return {"success": True, "message": f"Project {project_id} put on hold", "action_taken": "pause_project"}
            
            elif error_type == 'analysis_error':
                analysis_id = error_data.get('analysis_id')
                if analysis_id in self.analysis_results:
                    analysis = self.analysis_results[analysis_id]
                    analysis['status'] = 'failed'
                    self.logger.warning(f"Analysis {analysis_id} failed: {error_msg}")
                    return {"success": True, "message": f"Analysis {analysis_id} marked as failed", "action_taken": "mark_failed"}
            
            elif error_type == 'review_error':
                review_id = error_data.get('review_id')
                if review_id in self.literature_reviews:
                    review = self.literature_reviews[review_id]
                    review['status'] = 'failed'
                    self.logger.warning(f"Review {review_id} failed: {error_msg}")
                    return {"success": True, "message": f"Review {review_id} marked as failed", "action_taken": "mark_failed"}
            
            # Default error handling
            self.logger.error(f"Unhandled error type {error_type}: {error_msg}")
            return {"success": False, "message": f"Unhandled error type: {error_type}", "action_taken": "none"}
            
        except Exception as e:
            self.logger.error(f"Error in error handler: {str(e)}")
            return {"success": False, "message": f"Error handler failed: {str(e)}", "action_taken": "none"} 