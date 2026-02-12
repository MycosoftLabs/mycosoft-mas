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
import os

# External API clients
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

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
    
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming tasks and route to appropriate handlers.
        
        Args:
            task: Task dictionary containing type and parameters
            
        Returns:
            Dict with task processing results
        """
        try:
            task_type = task.get("type", "").lower()
            
            # Route to appropriate handler
            if task_type == "research" or task_type == "literature_search":
                return await self.handle_research(task)
            elif task_type == "analysis" or task_type == "data_analysis":
                return await self.handle_analysis(task)
            elif task_type == "review" or task_type == "peer_review":
                return await self.handle_review(task)
            elif task_type == "progress" or task_type == "project_progress":
                return await self.handle_project_progress(task)
            elif task_type == "create_project":
                return await self.create_research_project(task.get("data", {}))
            elif task_type == "literature_review":
                return await self.conduct_literature_review(task.get("data", {}))
            elif task_type == "analyze_data":
                return await self.analyze_research_data(task.get("data", {}))
            else:
                self.logger.warning(f"Unknown task type: {task_type}")
                return {
                    "success": False,
                    "message": f"Unknown task type: {task_type}",
                    "supported_types": [
                        "research", "literature_search",
                        "analysis", "data_analysis",
                        "review", "peer_review",
                        "progress", "project_progress",
                        "create_project", "literature_review", "analyze_data"
                    ]
                }
        except Exception as e:
            self.logger.error(f"Error processing task: {str(e)}")
            return {
                "success": False,
                "message": f"Task processing error: {str(e)}"
            }
    
    async def handle_research(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle research database queries (PubMed, arXiv, Google Scholar).
        
        Connects to academic databases to search for papers and retrieve metadata.
        Returns empty results if APIs are unavailable.
        
        Args:
            task: Task containing search parameters (query, source, filters)
            
        Returns:
            Dict with search results or empty list if unavailable
        """
        try:
            query = task.get("query", "")
            source = task.get("source", "pubmed").lower()
            max_results = task.get("max_results", 10)
            
            if not query:
                return {
                    "success": False,
                    "message": "No search query provided",
                    "results": []
                }
            
            results = []
            
            # PubMed/NCBI search
            if source == "pubmed":
                results = await self._search_pubmed(query, max_results)
            
            # arXiv search
            elif source == "arxiv":
                results = await self._search_arxiv(query, max_results)
            
            # Google Scholar (requires external service)
            elif source == "scholar":
                results = await self._search_scholar(query, max_results)
            
            # Semantic Scholar API
            elif source == "semantic_scholar":
                results = await self._search_semantic_scholar(query, max_results)
            
            else:
                return {
                    "success": False,
                    "message": f"Unknown source: {source}",
                    "supported_sources": ["pubmed", "arxiv", "scholar", "semantic_scholar"],
                    "results": []
                }
            
            return {
                "success": True,
                "source": source,
                "query": query,
                "count": len(results),
                "results": results
            }
            
        except Exception as e:
            self.logger.error(f"Research handler error: {str(e)}")
            return {
                "success": False,
                "message": f"Research error: {str(e)}",
                "results": []
            }
    
    async def handle_analysis(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle data analysis tasks using pandas and numpy.
        
        Performs statistical analysis, data transformations, and visualizations.
        Returns error if pandas/numpy unavailable.
        
        Args:
            task: Task containing data and analysis parameters
            
        Returns:
            Dict with analysis results or error
        """
        try:
            if not PANDAS_AVAILABLE:
                return {
                    "success": False,
                    "message": "pandas/numpy not available - install with: pip install pandas numpy",
                    "results": {}
                }
            
            analysis_type = task.get("analysis_type", "").lower()
            data_source = task.get("data_source")
            parameters = task.get("parameters", {})
            
            if not data_source:
                return {
                    "success": False,
                    "message": "No data source provided",
                    "results": {}
                }
            
            # Load data
            df = await self._load_analysis_data(data_source)
            if df is None or df.empty:
                return {
                    "success": False,
                    "message": "Failed to load data or empty dataset",
                    "results": {}
                }
            
            results = {}
            
            # Descriptive statistics
            if analysis_type == "descriptive" or analysis_type == "summary":
                results = self._analyze_descriptive(df, parameters)
            
            # Correlation analysis
            elif analysis_type == "correlation":
                results = self._analyze_correlation(df, parameters)
            
            # Time series analysis
            elif analysis_type == "timeseries":
                results = self._analyze_timeseries(df, parameters)
            
            # Distribution analysis
            elif analysis_type == "distribution":
                results = self._analyze_distribution(df, parameters)
            
            # Custom analysis
            elif analysis_type == "custom":
                results = await self._analyze_custom(df, parameters)
            
            else:
                return {
                    "success": False,
                    "message": f"Unknown analysis type: {analysis_type}",
                    "supported_types": ["descriptive", "correlation", "timeseries", "distribution", "custom"],
                    "results": {}
                }
            
            return {
                "success": True,
                "analysis_type": analysis_type,
                "data_shape": df.shape,
                "results": results
            }
            
        except Exception as e:
            self.logger.error(f"Analysis handler error: {str(e)}")
            return {
                "success": False,
                "message": f"Analysis error: {str(e)}",
                "results": {}
            }
    
    async def handle_review(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle peer review tasks.
        
        Connects to peer review platforms or internal review system.
        Returns empty results if services unavailable.
        
        Args:
            task: Task containing review parameters
            
        Returns:
            Dict with review status or empty if unavailable
        """
        try:
            review_type = task.get("review_type", "").lower()
            target_id = task.get("target_id")  # paper_id, project_id, etc.
            reviewer_id = task.get("reviewer_id")
            
            if not target_id:
                return {
                    "success": False,
                    "message": "No target specified for review",
                    "review_data": {}
                }
            
            # Check for internal review system connection (MAS Memory/MINDEX)
            review_data = await self._get_internal_review(target_id)
            
            # If internal review unavailable, check external services
            if not review_data:
                if review_type == "pubpeer":
                    review_data = await self._get_pubpeer_comments(target_id)
                elif review_type == "crossref":
                    review_data = await self._get_crossref_review(target_id)
                elif review_type == "mas":
                    review_data = await self._get_mas_review_status(target_id)
            
            if review_data:
                return {
                    "success": True,
                    "target_id": target_id,
                    "review_type": review_type,
                    "review_data": review_data
                }
            else:
                return {
                    "success": True,
                    "message": "No review data available",
                    "target_id": target_id,
                    "review_data": {}
                }
            
        except Exception as e:
            self.logger.error(f"Review handler error: {str(e)}")
            return {
                "success": False,
                "message": f"Review error: {str(e)}",
                "review_data": {}
            }
    
    async def handle_project_progress(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle project progress tracking.
        
        Queries project management data from MAS or external PM tools.
        Returns empty results if unavailable.
        
        Args:
            task: Task containing project_id and query parameters
            
        Returns:
            Dict with progress data or empty if unavailable
        """
        try:
            project_id = task.get("project_id")
            
            if not project_id:
                # Return all projects summary
                projects_summary = []
                for proj_id, proj in self.research_projects.items():
                    projects_summary.append({
                        "id": proj_id,
                        "title": proj.title,
                        "status": proj.status.value,
                        "progress": self._calculate_project_progress(proj),
                        "updated_at": proj.updated_at.isoformat()
                    })
                
                return {
                    "success": True,
                    "total_projects": len(projects_summary),
                    "projects": projects_summary
                }
            
            # Get specific project
            if project_id not in self.research_projects:
                # Try to get from MAS or external PM system
                external_data = await self._get_external_project_data(project_id)
                if external_data:
                    return {
                        "success": True,
                        "project_id": project_id,
                        "source": "external",
                        "progress_data": external_data
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Project {project_id} not found",
                        "progress_data": {}
                    }
            
            project = self.research_projects[project_id]
            progress_data = {
                "id": project.id,
                "title": project.title,
                "description": project.description,
                "status": project.status.value,
                "research_type": project.research_type.value,
                "start_date": project.start_date.isoformat(),
                "end_date": project.end_date.isoformat(),
                "team": project.team,
                "objectives": project.objectives,
                "objectives_completed": self._count_completed_objectives(project),
                "total_objectives": len(project.objectives),
                "progress_percentage": self._calculate_project_progress(project),
                "days_elapsed": (datetime.now() - project.start_date).days,
                "days_remaining": (project.end_date - datetime.now()).days,
                "findings_count": len(project.findings) if project.findings else 0,
                "references_count": len(project.references),
                "updated_at": project.updated_at.isoformat()
            }
            
            return {
                "success": True,
                "project_id": project_id,
                "source": "internal",
                "progress_data": progress_data
            }
            
        except Exception as e:
            self.logger.error(f"Project progress handler error: {str(e)}")
            return {
                "success": False,
                "message": f"Progress tracking error: {str(e)}",
                "progress_data": {}
            }
    
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
    
    # ==================== Research Database Methods ====================
    
    async def _search_pubmed(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search PubMed/NCBI database using E-utilities API.
        
        Returns empty list if API unavailable or error occurs.
        """
        if not AIOHTTP_AVAILABLE:
            self.logger.warning("aiohttp not available - cannot search PubMed")
            return []
        
        try:
            base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
            
            # Search for paper IDs
            search_url = f"{base_url}esearch.fcgi"
            search_params = {
                "db": "pubmed",
                "term": query,
                "retmax": max_results,
                "retmode": "json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, params=search_params) as response:
                    if response.status != 200:
                        self.logger.warning(f"PubMed search failed: {response.status}")
                        return []
                    
                    search_data = await response.json()
                    id_list = search_data.get("esearchresult", {}).get("idlist", [])
                    
                    if not id_list:
                        return []
                    
                    # Fetch details for each paper
                    fetch_url = f"{base_url}esummary.fcgi"
                    fetch_params = {
                        "db": "pubmed",
                        "id": ",".join(id_list),
                        "retmode": "json"
                    }
                    
                    async with session.get(fetch_url, params=fetch_params) as fetch_response:
                        if fetch_response.status != 200:
                            return []
                        
                        fetch_data = await fetch_response.json()
                        results = []
                        
                        for pmid in id_list:
                            paper_data = fetch_data.get("result", {}).get(pmid, {})
                            if paper_data:
                                results.append({
                                    "id": pmid,
                                    "title": paper_data.get("title", ""),
                                    "authors": [author.get("name", "") for author in paper_data.get("authors", [])],
                                    "journal": paper_data.get("fulljournalname", ""),
                                    "pubdate": paper_data.get("pubdate", ""),
                                    "doi": paper_data.get("elocationid", ""),
                                    "source": "pubmed"
                                })
                        
                        return results
        except Exception as e:
            self.logger.error(f"PubMed search error: {str(e)}")
            return []
    
    async def _search_arxiv(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search arXiv database using arXiv API.
        
        Returns empty list if API unavailable or error occurs.
        """
        if not AIOHTTP_AVAILABLE:
            self.logger.warning("aiohttp not available - cannot search arXiv")
            return []
        
        try:
            base_url = "http://export.arxiv.org/api/query"
            params = {
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": max_results
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(base_url, params=params) as response:
                    if response.status != 200:
                        self.logger.warning(f"arXiv search failed: {response.status}")
                        return []
                    
                    # Parse XML response
                    import xml.etree.ElementTree as ET
                    xml_data = await response.text()
                    root = ET.fromstring(xml_data)
                    
                    results = []
                    namespace = {'atom': 'http://www.w3.org/2005/Atom'}
                    
                    for entry in root.findall('atom:entry', namespace):
                        title = entry.find('atom:title', namespace)
                        published = entry.find('atom:published', namespace)
                        authors = entry.findall('atom:author', namespace)
                        
                        results.append({
                            "id": entry.find('atom:id', namespace).text if entry.find('atom:id', namespace) is not None else "",
                            "title": title.text.strip() if title is not None else "",
                            "authors": [author.find('atom:name', namespace).text for author in authors if author.find('atom:name', namespace) is not None],
                            "published": published.text if published is not None else "",
                            "source": "arxiv"
                        })
                    
                    return results
        except Exception as e:
            self.logger.error(f"arXiv search error: {str(e)}")
            return []
    
    async def _search_scholar(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search Google Scholar (requires external service/API key).
        
        Returns empty list as direct Scholar API requires authentication.
        """
        self.logger.warning("Google Scholar search requires SerpAPI or similar service - not implemented")
        return []
    
    async def _search_semantic_scholar(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search Semantic Scholar API.
        
        Returns empty list if API unavailable or error occurs.
        """
        if not AIOHTTP_AVAILABLE:
            self.logger.warning("aiohttp not available - cannot search Semantic Scholar")
            return []
        
        try:
            base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
            params = {
                "query": query,
                "limit": max_results,
                "fields": "paperId,title,authors,year,citationCount,abstract"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(base_url, params=params) as response:
                    if response.status != 200:
                        self.logger.warning(f"Semantic Scholar search failed: {response.status}")
                        return []
                    
                    data = await response.json()
                    results = []
                    
                    for paper in data.get("data", []):
                        results.append({
                            "id": paper.get("paperId", ""),
                            "title": paper.get("title", ""),
                            "authors": [author.get("name", "") for author in paper.get("authors", [])],
                            "year": paper.get("year", ""),
                            "citations": paper.get("citationCount", 0),
                            "abstract": paper.get("abstract", ""),
                            "source": "semantic_scholar"
                        })
                    
                    return results
        except Exception as e:
            self.logger.error(f"Semantic Scholar search error: {str(e)}")
            return []
    
    # ==================== Data Analysis Methods ====================
    
    async def _load_analysis_data(self, data_source: Union[str, Dict]) -> Optional[pd.DataFrame]:
        """Load data for analysis from various sources."""
        if not PANDAS_AVAILABLE:
            return None
        
        try:
            # File path
            if isinstance(data_source, str):
                if data_source.endswith('.csv'):
                    return pd.read_csv(data_source)
                elif data_source.endswith('.json'):
                    return pd.read_json(data_source)
                elif data_source.endswith('.xlsx') or data_source.endswith('.xls'):
                    return pd.read_excel(data_source)
                else:
                    self.logger.warning(f"Unsupported file format: {data_source}")
                    return None
            
            # Dictionary data
            elif isinstance(data_source, dict):
                return pd.DataFrame(data_source)
            
            else:
                return None
        except Exception as e:
            self.logger.error(f"Error loading analysis data: {str(e)}")
            return None
    
    def _analyze_descriptive(self, df: pd.DataFrame, parameters: Dict) -> Dict:
        """Perform descriptive statistical analysis."""
        try:
            columns = parameters.get("columns", df.select_dtypes(include=[np.number]).columns.tolist())
            
            results = {
                "summary": df[columns].describe().to_dict(),
                "missing_values": df[columns].isnull().sum().to_dict(),
                "data_types": df[columns].dtypes.astype(str).to_dict(),
                "unique_counts": {col: df[col].nunique() for col in columns}
            }
            
            return results
        except Exception as e:
            self.logger.error(f"Descriptive analysis error: {str(e)}")
            return {"error": str(e)}
    
    def _analyze_correlation(self, df: pd.DataFrame, parameters: Dict) -> Dict:
        """Perform correlation analysis."""
        try:
            method = parameters.get("method", "pearson")
            columns = parameters.get("columns", df.select_dtypes(include=[np.number]).columns.tolist())
            
            corr_matrix = df[columns].corr(method=method)
            
            results = {
                "method": method,
                "correlation_matrix": corr_matrix.to_dict(),
                "strong_correlations": []
            }
            
            # Find strong correlations (>0.7 or <-0.7)
            for i in range(len(corr_matrix.columns)):
                for j in range(i+1, len(corr_matrix.columns)):
                    corr_value = corr_matrix.iloc[i, j]
                    if abs(corr_value) > 0.7:
                        results["strong_correlations"].append({
                            "var1": corr_matrix.columns[i],
                            "var2": corr_matrix.columns[j],
                            "correlation": float(corr_value)
                        })
            
            return results
        except Exception as e:
            self.logger.error(f"Correlation analysis error: {str(e)}")
            return {"error": str(e)}
    
    def _analyze_timeseries(self, df: pd.DataFrame, parameters: Dict) -> Dict:
        """Perform time series analysis."""
        try:
            time_column = parameters.get("time_column")
            value_column = parameters.get("value_column")
            
            if not time_column or not value_column:
                return {"error": "time_column and value_column required for timeseries analysis"}
            
            # Convert to datetime if not already
            if not pd.api.types.is_datetime64_any_dtype(df[time_column]):
                df[time_column] = pd.to_datetime(df[time_column])
            
            df_sorted = df.sort_values(time_column)
            
            results = {
                "start_date": str(df_sorted[time_column].min()),
                "end_date": str(df_sorted[time_column].max()),
                "num_points": len(df_sorted),
                "mean": float(df_sorted[value_column].mean()),
                "std": float(df_sorted[value_column].std()),
                "trend": "increasing" if df_sorted[value_column].iloc[-1] > df_sorted[value_column].iloc[0] else "decreasing"
            }
            
            return results
        except Exception as e:
            self.logger.error(f"Timeseries analysis error: {str(e)}")
            return {"error": str(e)}
    
    def _analyze_distribution(self, df: pd.DataFrame, parameters: Dict) -> Dict:
        """Perform distribution analysis."""
        try:
            column = parameters.get("column")
            if not column or column not in df.columns:
                return {"error": f"Column {column} not found"}
            
            data = df[column].dropna()
            
            results = {
                "column": column,
                "count": int(len(data)),
                "mean": float(data.mean()),
                "median": float(data.median()),
                "std": float(data.std()),
                "min": float(data.min()),
                "max": float(data.max()),
                "quartiles": {
                    "q1": float(data.quantile(0.25)),
                    "q2": float(data.quantile(0.50)),
                    "q3": float(data.quantile(0.75))
                },
                "skewness": float(data.skew()),
                "kurtosis": float(data.kurtosis())
            }
            
            return results
        except Exception as e:
            self.logger.error(f"Distribution analysis error: {str(e)}")
            return {"error": str(e)}
    
    async def _analyze_custom(self, df: pd.DataFrame, parameters: Dict) -> Dict:
        """Perform custom analysis based on parameters."""
        try:
            operation = parameters.get("operation", "")
            
            if operation == "group_by":
                group_col = parameters.get("group_column")
                agg_col = parameters.get("agg_column")
                agg_func = parameters.get("agg_function", "mean")
                
                if group_col and agg_col:
                    result = df.groupby(group_col)[agg_col].agg(agg_func)
                    return {"operation": "group_by", "results": result.to_dict()}
            
            elif operation == "pivot":
                index = parameters.get("index")
                columns = parameters.get("columns")
                values = parameters.get("values")
                
                if index and columns and values:
                    result = df.pivot_table(index=index, columns=columns, values=values)
                    return {"operation": "pivot", "results": result.to_dict()}
            
            return {"error": f"Unknown custom operation: {operation}"}
        except Exception as e:
            self.logger.error(f"Custom analysis error: {str(e)}")
            return {"error": str(e)}
    
    # ==================== Review Methods ====================
    
    async def _get_internal_review(self, target_id: str) -> Optional[Dict]:
        """Get internal review data from MAS memory/MINDEX."""
        try:
            # Check local literature reviews
            for review_id, review in self.literature_reviews.items():
                if review.get("project_id") == target_id:
                    return {
                        "review_id": review_id,
                        "status": review.get("status", "unknown"),
                        "findings": review.get("findings", {}),
                        "papers_reviewed": len(review.get("papers_reviewed", [])),
                        "updated_at": review.get("updated_at")
                    }
            
            # Could query MINDEX API here for reviews
            return None
        except Exception as e:
            self.logger.error(f"Internal review query error: {str(e)}")
            return None
    
    async def _get_pubpeer_comments(self, paper_id: str) -> Optional[Dict]:
        """Get PubPeer comments for a paper (requires API access)."""
        self.logger.warning("PubPeer API integration not implemented")
        return None
    
    async def _get_crossref_review(self, doi: str) -> Optional[Dict]:
        """Get Crossref review metadata."""
        if not AIOHTTP_AVAILABLE:
            return None
        
        try:
            url = f"https://api.crossref.org/works/{doi}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        message = data.get("message", {})
                        return {
                            "doi": doi,
                            "title": message.get("title", [""])[0],
                            "published": message.get("published", {}),
                            "references_count": message.get("references-count", 0),
                            "is_referenced_by_count": message.get("is-referenced-by-count", 0)
                        }
            return None
        except Exception as e:
            self.logger.error(f"Crossref query error: {str(e)}")
            return None
    
    async def _get_mas_review_status(self, target_id: str) -> Optional[Dict]:
        """Get review status from MAS orchestrator."""
        try:
            mas_url = os.getenv("MAS_API_URL", "http://192.168.0.188:8001")
            if not AIOHTTP_AVAILABLE:
                return None
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{mas_url}/api/research/review/{target_id}") as response:
                    if response.status == 200:
                        return await response.json()
            return None
        except Exception as e:
            self.logger.error(f"MAS review query error: {str(e)}")
            return None
    
    # ==================== Project Progress Methods ====================
    
    def _calculate_project_progress(self, project: ResearchProject) -> float:
        """Calculate project progress percentage."""
        try:
            total_points = 100
            progress = 0
            
            # Status-based progress
            if project.status == ResearchStatus.COMPLETED:
                return 100.0
            elif project.status == ResearchStatus.PLANNING:
                progress = 10
            elif project.status == ResearchStatus.IN_PROGRESS:
                progress = 30
            
            # Objectives completion
            if project.objectives:
                completed = self._count_completed_objectives(project)
                progress += (completed / len(project.objectives)) * 40
            
            # Findings contribution
            if project.findings:
                progress += min(20, len(project.findings) * 5)
            
            # References contribution
            if project.references:
                progress += min(10, len(project.references))
            
            return min(100.0, progress)
        except Exception as e:
            self.logger.error(f"Progress calculation error: {str(e)}")
            return 0.0
    
    def _count_completed_objectives(self, project: ResearchProject) -> int:
        """Count completed objectives (would check objective status in real implementation)."""
        # Simplified: check if findings exist for objectives
        if not project.objectives or not project.findings:
            return 0
        
        # In real implementation, objectives would have status tracking
        # For now, estimate based on findings
        return min(len(project.objectives), len(project.findings))
    
    async def _get_external_project_data(self, project_id: str) -> Optional[Dict]:
        """Get project data from external PM tools (Jira, GitHub Projects, etc.)."""
        try:
            # Try MAS API first
            mas_url = os.getenv("MAS_API_URL", "http://192.168.0.188:8001")
            if AIOHTTP_AVAILABLE:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{mas_url}/api/projects/{project_id}") as response:
                        if response.status == 200:
                            return await response.json()
            
            # Could add GitHub Projects API, Jira API, etc. here
            return None
        except Exception as e:
            self.logger.error(f"External project data query error: {str(e)}")
            return None
    
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
        # NOTE: Pending implementation - Future services to initialize:
        # 1. Connection to academic paper databases (PubMed, arXiv, Semantic Scholar)
        # 2. Citation management system integration
        # 3. Research collaboration platform connectors
        # Currently operates with local file storage only
        self.logger.info("Research services initialized (local mode)")
    
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
        try:
            task_type = task.get("type", "general")
            project_id = task.get("project_id")
            
            self.logger.info(f"Processing research task: {task_type} for project {project_id}")
            
            # Update project status if exists
            if project_id and project_id in self.research_projects:
                project = self.research_projects[project_id]
                project.status = ResearchStatus.IN_PROGRESS
                project.updated_at = datetime.now()
                await self._save_research_project(project)
            
            self.metrics["projects_managed"] += 1
            self.logger.info(f"Research task {task_type} completed for project {project_id}")
            
        except Exception as e:
            self.logger.error(f"Error handling research task: {str(e)}")
    
    async def _handle_analysis_task(self, task: Dict) -> None:
        """Handle an analysis task."""
        try:
            analysis_id = task.get("analysis_id")
            analysis_data = task.get("analysis_data", {})
            
            self.logger.info(f"Processing analysis task: {analysis_id}")
            
            if analysis_id and analysis_id in self.analysis_results:
                analysis = self.analysis_results[analysis_id]
                analysis["status"] = "completed"
                analysis["updated_at"] = datetime.now().isoformat()
                analysis["results"] = {
                    "completed": True,
                    "analysis_type": analysis_data.get("analysis_type", "unknown"),
                    "timestamp": datetime.now().isoformat()
                }
                await self._save_analysis_result(analysis)
            
            self.metrics["analyses_completed"] += 1
            self.logger.info(f"Analysis task {analysis_id} completed")
            
        except Exception as e:
            self.logger.error(f"Error handling analysis task: {str(e)}")
    
    async def _handle_review_task(self, task: Dict) -> None:
        """Handle a review task."""
        try:
            review_id = task.get("review_id")
            review_data = task.get("review_data", {})
            
            self.logger.info(f"Processing review task: {review_id}")
            
            if review_id and review_id in self.literature_reviews:
                review = self.literature_reviews[review_id]
                review["status"] = "completed"
                review["updated_at"] = datetime.now().isoformat()
                review["findings"] = {
                    "search_terms": review_data.get("search_terms", []),
                    "papers_found": 0,  # Would be populated by actual search
                    "timestamp": datetime.now().isoformat()
                }
                await self._save_literature_review(review)
            
            self.metrics["papers_reviewed"] += 1
            self.logger.info(f"Review task {review_id} completed")
            
        except Exception as e:
            self.logger.error(f"Error handling review task: {str(e)}")
    
    async def _check_project_progress(self, project: ResearchProject) -> None:
        """Check project progress and update status."""
        try:
            now = datetime.now()
            
            # Check if project is past end date
            if now > project.end_date and project.status == ResearchStatus.IN_PROGRESS:
                self.logger.warning(f"Project {project.id} is past deadline")
                # Keep status as in_progress but log for review
            
            # Check if project has findings (indicates completion)
            if project.findings and len(project.findings) > 0:
                project.status = ResearchStatus.COMPLETED
                project.updated_at = now
                await self._save_research_project(project)
                self.logger.info(f"Project {project.id} marked as completed")
            
        except Exception as e:
            self.logger.error(f"Error checking project progress for {project.id}: {str(e)}")
    
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