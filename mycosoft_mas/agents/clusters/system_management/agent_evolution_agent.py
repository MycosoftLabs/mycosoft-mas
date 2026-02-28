"""
Agent Evolution Agent for Mycology BioAgent System

This agent continuously searches for improvements, new tools, and upgrades
for agents in the Mycosoft MAS. It discovers, evaluates, and recommends
upgrades to enhance the system's capabilities.
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional, Any, Set, Tuple, Union, Callable, Awaitable
from datetime import datetime, timedelta
import json
import uuid
import re
import aiohttp
import feedparser
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum, auto

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus, TaskType, TaskStatus, TaskPriority

class DiscoverySource(Enum):
    """Sources for discovering improvements"""
    GITHUB = auto()
    TWITTER = auto()
    REDDIT = auto()
    HUGGINGFACE = auto()
    PAPERS_WITH_CODE = auto()
    ARXIV = auto()
    DISCORD_IDEAS = auto()
    CODEBASE_SCAN = auto()
    CUSTOM = auto()

class ImprovementType(Enum):
    """Types of improvements"""
    CODE_UPGRADE = auto()
    NEW_LIBRARY = auto()
    NEW_TOOL = auto()
    NEW_PROTOCOL = auto()
    NEW_ALGORITHM = auto()
    NEW_MODEL = auto()
    NEW_FEATURE = auto()
    OPTIMIZATION = auto()
    BUG_FIX = auto()
    DOCUMENTATION = auto()

class EvaluationStatus(Enum):
    """Status of improvement evaluation"""
    DISCOVERED = auto()
    EVALUATING = auto()
    RECOMMENDED = auto()
    REJECTED = auto()
    IMPLEMENTED = auto()
    TESTING = auto()
    DEPLOYED = auto()
    FAILED = auto()

@dataclass
class Improvement:
    """Information about a potential improvement"""
    improvement_id: str
    name: str
    description: str
    source: DiscoverySource
    source_url: str
    improvement_type: ImprovementType
    target_agent_id: str
    relevance_score: float
    implementation_complexity: float
    potential_impact: float
    status: EvaluationStatus = EvaluationStatus.DISCOVERED
    code_snippets: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    requirements: Dict[str, Any] = field(default_factory=dict)
    implementation_steps: List[str] = field(default_factory=list)
    test_cases: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class DiscoveryTask:
    """Task for discovering improvements"""
    task_id: str
    source: DiscoverySource
    query: str
    filters: Dict[str, Any] = field(default_factory=dict)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class EvaluationResult:
    """Result of evaluating an improvement"""
    result_id: str
    improvement_id: str
    evaluator_agent_id: str
    score: float
    recommendation: str
    implementation_plan: Optional[str] = None
    estimated_effort: Optional[float] = None
    risks: List[str] = field(default_factory=list)
    benefits: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class ImplementationPlan:
    """Plan for implementing an improvement"""
    plan_id: str
    improvement_id: str
    target_agent_id: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    estimated_duration: Optional[float] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    status: str = "pending"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class IdeaEntry:
    """Entry parsed from the Ideas catalog"""
    entry_id: str
    entry_type: str
    title: str
    url: Optional[str]
    date: Optional[str]
    author: Optional[str]
    section: str
    channel: Optional[str]
    raw: str
    created_at: datetime = field(default_factory=datetime.utcnow)

class AgentEvolutionAgent(BaseAgent):
    """Agent for discovering and recommending improvements to other agents"""
    
    def __init__(self, agent_id: str, name: str = "Agent Evolution Agent", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id=agent_id, name=name, config=config or {})
        self.improvements: Dict[str, Improvement] = {}
        self.discovery_tasks: Dict[str, DiscoveryTask] = {}
        self.evaluation_results: Dict[str, EvaluationResult] = {}
        self.implementation_plans: Dict[str, ImplementationPlan] = {}
        self.agent_registry: Dict[str, Dict[str, Any]] = {}
        self.discovery_queue: asyncio.Queue = asyncio.Queue()
        self.evaluation_queue: asyncio.Queue = asyncio.Queue()
        self.implementation_queue: asyncio.Queue = asyncio.Queue()
        self._background_tasks: List[asyncio.Task] = []
        
        # Create necessary directories
        self.data_dir = Path("data/agent_evolution")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.idea_data_dir = Path("mycosoft_mas/runtime/idea_evolution")
        self.idea_data_dir.mkdir(parents=True, exist_ok=True)

        self.ideas_doc_path = Path(
            os.environ.get(
                "IDEAS_DOC_PATH",
                "docs/MYCA_Master_Ideas_Concepts_Resources.md"
            )
        )
        self.status_tracker_path = Path(
            os.environ.get(
                "IDEA_STATUS_TRACKER_PATH",
                "docs/IDEA_STATUS_TRACKER_FEB26_2026.md"
            )
        )
        
        # Initialize metrics
        self.metrics.update({
            "improvements_discovered": 0,
            "improvements_evaluated": 0,
            "improvements_implemented": 0,
            "discovery_tasks_run": 0,
            "evaluation_tasks_run": 0,
            "implementation_tasks_run": 0,
            "ideas_parsed": 0,
            "ideas_status_updated": 0,
            "codebase_findings": 0
        })
    
    async def initialize(self) -> None:
        """Initialize the agent"""
        await super().initialize()
        await self._load_data()
        await self._register_default_discovery_tasks()
        self.status = AgentStatus.RUNNING
        self.logger.info("Agent Evolution Agent initialized")

        self._background_tasks = [
            asyncio.create_task(self._process_discovery_queue()),
            asyncio.create_task(self._process_evaluation_queue()),
            asyncio.create_task(self._process_implementation_queue()),
            asyncio.create_task(self.start_evolution_loop())
        ]

    async def _initialize_services(self) -> None:
        """Initialize without external dependencies."""
        # Agent Evolution runs its own loops and file IO. Avoid external
        # dependency wiring so startup is resilient.
        return None
    
    async def stop(self) -> None:
        """Stop the agent"""
        self.status = AgentStatus.STOPPED
        self.logger.info("Stopping Agent Evolution Agent")
        await self._save_data()
        for task in self._background_tasks:
            task.cancel()
        await super().stop()
    
    async def register_agent(
        self,
        agent_id: str,
        agent_type: str,
        capabilities: List[str],
        dependencies: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register an agent in the registry"""
        self.agent_registry[agent_id] = {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "capabilities": capabilities,
            "dependencies": dependencies,
            "metadata": metadata or {},
            "registered_at": datetime.utcnow().isoformat()
        }
        await self._save_data()
    
    async def create_discovery_task(
        self,
        source: DiscoverySource,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        next_run: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new discovery task"""
        task_id = f"discovery_{uuid.uuid4().hex[:8]}"
        
        task = DiscoveryTask(
            task_id=task_id,
            source=source,
            query=query,
            filters=filters or {},
            next_run=next_run or (datetime.utcnow() + timedelta(days=3)),
            metadata=metadata or {}
        )
        
        self.discovery_tasks[task_id] = task
        await self._save_data()
        
        return task_id
    
    async def run_discovery_task(self, task_id: str) -> List[str]:
        """Run a discovery task and return improvement IDs"""
        if task_id not in self.discovery_tasks:
            self.logger.error(f"Discovery task {task_id} not found")
            return []
        
        task = self.discovery_tasks[task_id]
        task.last_run = datetime.utcnow()
        task.next_run = datetime.utcnow() + timedelta(days=3)
        task.updated_at = datetime.utcnow()
        
        self.metrics["discovery_tasks_run"] += 1
        
        # Run discovery based on source
        improvement_ids = []
        
        if task.source == DiscoverySource.GITHUB:
            improvement_ids = await self._discover_from_github(task)
        elif task.source == DiscoverySource.TWITTER:
            improvement_ids = await self._discover_from_twitter(task)
        elif task.source == DiscoverySource.REDDIT:
            improvement_ids = await self._discover_from_reddit(task)
        elif task.source == DiscoverySource.HUGGINGFACE:
            improvement_ids = await self._discover_from_huggingface(task)
        elif task.source == DiscoverySource.PAPERS_WITH_CODE:
            improvement_ids = await self._discover_from_papers_with_code(task)
        elif task.source == DiscoverySource.ARXIV:
            improvement_ids = await self._discover_from_arxiv(task)
        elif task.source == DiscoverySource.DISCORD_IDEAS:
            improvement_ids = await self._discover_from_discord_ideas(task)
        elif task.source == DiscoverySource.CODEBASE_SCAN:
            improvement_ids = await self._discover_from_codebase_scan(task)
        elif task.source == DiscoverySource.CUSTOM:
            improvement_ids = await self._discover_from_custom_source(task)
        
        await self._save_data()
        return improvement_ids
    
    async def evaluate_improvement(
        self,
        improvement_id: str,
        evaluator_agent_id: str,
        score: float,
        recommendation: str,
        implementation_plan: Optional[str] = None,
        estimated_effort: Optional[float] = None,
        risks: Optional[List[str]] = None,
        benefits: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Evaluate an improvement and return result ID"""
        if improvement_id not in self.improvements:
            self.logger.error(f"Improvement {improvement_id} not found")
            return ""
        
        result_id = f"eval_{uuid.uuid4().hex[:8]}"
        
        result = EvaluationResult(
            result_id=result_id,
            improvement_id=improvement_id,
            evaluator_agent_id=evaluator_agent_id,
            score=score,
            recommendation=recommendation,
            implementation_plan=implementation_plan,
            estimated_effort=estimated_effort,
            risks=risks or [],
            benefits=benefits or [],
            metadata=metadata or {}
        )
        
        self.evaluation_results[result_id] = result
        
        # Update improvement status
        improvement = self.improvements[improvement_id]
        improvement.status = EvaluationStatus.RECOMMENDED if score >= 0.7 else EvaluationStatus.REJECTED
        improvement.updated_at = datetime.utcnow()
        
        self.metrics["improvements_evaluated"] += 1
        await self._save_data()
        
        return result_id
    
    async def create_implementation_plan(
        self,
        improvement_id: str,
        target_agent_id: str,
        steps: List[Dict[str, Any]],
        dependencies: Optional[List[str]] = None,
        estimated_duration: Optional[float] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create an implementation plan for an improvement"""
        if improvement_id not in self.improvements:
            self.logger.error(f"Improvement {improvement_id} not found")
            return ""
        
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"
        
        plan = ImplementationPlan(
            plan_id=plan_id,
            improvement_id=improvement_id,
            target_agent_id=target_agent_id,
            steps=steps,
            dependencies=dependencies or [],
            estimated_duration=estimated_duration,
            priority=priority,
            metadata=metadata or {}
        )
        
        self.implementation_plans[plan_id] = plan
        
        # Update improvement status
        improvement = self.improvements[improvement_id]
        improvement.status = EvaluationStatus.IMPLEMENTED
        improvement.updated_at = datetime.utcnow()
        
        await self._save_data()
        
        # Add to implementation queue
        await self.implementation_queue.put(plan_id)
        
        return plan_id
    
    async def get_improvement(self, improvement_id: str) -> Optional[Improvement]:
        """Get an improvement by ID"""
        return self.improvements.get(improvement_id)
    
    async def get_discovery_task(self, task_id: str) -> Optional[DiscoveryTask]:
        """Get a discovery task by ID"""
        return self.discovery_tasks.get(task_id)
    
    async def get_evaluation_result(self, result_id: str) -> Optional[EvaluationResult]:
        """Get an evaluation result by ID"""
        return self.evaluation_results.get(result_id)
    
    async def get_implementation_plan(self, plan_id: str) -> Optional[ImplementationPlan]:
        """Get an implementation plan by ID"""
        return self.implementation_plans.get(plan_id)
    
    async def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get information about an agent"""
        return self.agent_registry.get(agent_id)
    
    async def get_recommended_improvements(
        self,
        agent_id: Optional[str] = None,
        improvement_type: Optional[ImprovementType] = None,
        limit: int = 10
    ) -> List[Improvement]:
        """Get recommended improvements"""
        recommended = []
        
        for improvement in self.improvements.values():
            if improvement.status != EvaluationStatus.RECOMMENDED:
                continue
            
            if agent_id and improvement.target_agent_id != agent_id:
                continue
            
            if improvement_type and improvement.improvement_type != improvement_type:
                continue
            
            recommended.append(improvement)
        
        # Sort by potential impact and relevance score
        recommended.sort(key=lambda x: (x.potential_impact, x.relevance_score), reverse=True)
        
        return recommended[:limit]
    
    async def _register_default_discovery_tasks(self) -> None:
        """Register default discovery tasks"""
        # GitHub tasks
        await self.create_discovery_task(
            source=DiscoverySource.GITHUB,
            query="mycology agent python",
            filters={"language": "python", "stars": ">10"},
            next_run=datetime.utcnow() + timedelta(days=1)
        )
        
        await self.create_discovery_task(
            source=DiscoverySource.GITHUB,
            query="fungi classification machine learning",
            filters={"language": "python", "stars": ">10"},
            next_run=datetime.utcnow() + timedelta(days=1)
        )
        
        # Twitter tasks
        await self.create_discovery_task(
            source=DiscoverySource.TWITTER,
            query="mycology research AI",
            filters={"from": "scientists,researchers"},
            next_run=datetime.utcnow() + timedelta(days=1)
        )
        
        # Reddit tasks
        await self.create_discovery_task(
            source=DiscoverySource.REDDIT,
            query="mycology machine learning",
            filters={"subreddit": "mycology,machinelearning,artificial"},
            next_run=datetime.utcnow() + timedelta(days=1)
        )
        
        # HuggingFace tasks
        await self.create_discovery_task(
            source=DiscoverySource.HUGGINGFACE,
            query="fungi classification",
            filters={"task": "image-classification"},
            next_run=datetime.utcnow() + timedelta(days=1)
        )
        
        # Papers with Code tasks
        await self.create_discovery_task(
            source=DiscoverySource.PAPERS_WITH_CODE,
            query="fungi classification",
            filters={"task": "image-classification"},
            next_run=datetime.utcnow() + timedelta(days=1)
        )
        
        # ArXiv tasks
        await self.create_discovery_task(
            source=DiscoverySource.ARXIV,
            query="mycology machine learning",
            filters={"category": "cs.CV,cs.LG,q-bio"},
            next_run=datetime.utcnow() + timedelta(days=1)
        )

        # Discord ideas catalog
        await self.create_discovery_task(
            source=DiscoverySource.DISCORD_IDEAS,
            query="ideas_catalog",
            filters={"source": str(self.ideas_doc_path)},
            next_run=datetime.utcnow() + timedelta(hours=12)
        )

        # Codebase scan (gaps and TODOs)
        await self.create_discovery_task(
            source=DiscoverySource.CODEBASE_SCAN,
            query="gap_report_scan",
            filters={
                "gap_report_latest": ".cursor/gap_report_latest.json",
                "gap_report_index": ".cursor/gap_report_index.json"
            },
            next_run=datetime.utcnow() + timedelta(hours=12)
        )
    
    async def _discover_from_github(self, task: DiscoveryTask) -> List[str]:
        """Discover improvements from GitHub"""
        self.logger.info(f"Discovering from GitHub: {task.query}")
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            self.logger.warning("GITHUB_TOKEN not set; skipping GitHub discovery")
            return []

        query = task.query
        language = task.filters.get("language", "python")
        per_page = int(task.filters.get("per_page", 5))
        q = f"{query} language:{language}"
        url = f"https://api.github.com/search/repositories?q={q}&sort=stars&order=desc&per_page={per_page}"

        headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
        improvement_ids: List[str] = []

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=30) as resp:
                if resp.status != 200:
                    self.logger.warning(f"GitHub discovery failed: {resp.status}")
                    return []
                payload = await resp.json()
                for item in payload.get("items", []):
                    improvement_id = await self._create_improvement(
                        name=item.get("name", "GitHub Repository"),
                        description=item.get("description") or "GitHub repository discovery",
                        source=DiscoverySource.GITHUB,
                        source_url=item.get("html_url", ""),
                        improvement_type=ImprovementType.NEW_TOOL,
                        target_agent_id=task.filters.get("target_agent_id", "system"),
                        relevance_score=0.6,
                        implementation_complexity=0.5,
                        potential_impact=0.6,
                        dependencies=[],
                        requirements={"stars": item.get("stargazers_count", 0)}
                    )
                    improvement_ids.append(improvement_id)

        return improvement_ids
    
    async def _discover_from_twitter(self, task: DiscoveryTask) -> List[str]:
        """Discover improvements from Twitter"""
        self.logger.info(f"Discovering from Twitter: {task.query}")
        self.logger.warning("Twitter discovery not configured; skipping")
        return []
    
    async def _discover_from_reddit(self, task: DiscoveryTask) -> List[str]:
        """Discover improvements from Reddit"""
        self.logger.info(f"Discovering from Reddit: {task.query}")
        self.logger.warning("Reddit discovery not configured; skipping")
        return []
    
    async def _discover_from_huggingface(self, task: DiscoveryTask) -> List[str]:
        """Discover improvements from HuggingFace"""
        self.logger.info(f"Discovering from HuggingFace: {task.query}")
        query = task.query
        per_page = int(task.filters.get("per_page", 5))
        url = f"https://huggingface.co/api/models?search={query}&limit={per_page}"
        token = os.environ.get("HUGGINGFACE_API_TOKEN")

        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        improvement_ids: List[str] = []
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=30) as resp:
                if resp.status != 200:
                    self.logger.warning(f"HuggingFace discovery failed: {resp.status}")
                    return []
                payload = await resp.json()
                for item in payload:
                    model_id = item.get("id", "")
                    improvement_id = await self._create_improvement(
                        name=model_id or "HuggingFace Model",
                        description=item.get("pipeline_tag") or "HuggingFace model discovery",
                        source=DiscoverySource.HUGGINGFACE,
                        source_url=f"https://huggingface.co/{model_id}" if model_id else "",
                        improvement_type=ImprovementType.NEW_MODEL,
                        target_agent_id=task.filters.get("target_agent_id", "system"),
                        relevance_score=0.6,
                        implementation_complexity=0.7,
                        potential_impact=0.6,
                        dependencies=[],
                        requirements={"downloads": item.get("downloads", 0)}
                    )
                    improvement_ids.append(improvement_id)

        return improvement_ids
    
    async def _discover_from_papers_with_code(self, task: DiscoveryTask) -> List[str]:
        """Discover improvements from Papers with Code"""
        self.logger.info(f"Discovering from Papers with Code: {task.query}")
        query = task.query
        per_page = int(task.filters.get("per_page", 5))
        url = f"https://paperswithcode.com/api/v1/papers/?search={query}&page_size={per_page}"

        improvement_ids: List[str] = []
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as resp:
                if resp.status != 200:
                    self.logger.warning(f"Papers with Code discovery failed: {resp.status}")
                    return []
                payload = await resp.json()
                for item in payload.get("results", []):
                    improvement_id = await self._create_improvement(
                        name=item.get("title", "Paper"),
                        description=item.get("abstract") or "Paper discovery",
                        source=DiscoverySource.PAPERS_WITH_CODE,
                        source_url=item.get("url", ""),
                        improvement_type=ImprovementType.NEW_ALGORITHM,
                        target_agent_id=task.filters.get("target_agent_id", "system"),
                        relevance_score=0.6,
                        implementation_complexity=0.7,
                        potential_impact=0.6,
                        dependencies=[],
                        requirements={}
                    )
                    improvement_ids.append(improvement_id)

        return improvement_ids
    
    async def _discover_from_arxiv(self, task: DiscoveryTask) -> List[str]:
        """Discover improvements from ArXiv"""
        self.logger.info(f"Discovering from ArXiv: {task.query}")
        query = task.query.replace(" ", "+")
        max_results = int(task.filters.get("max_results", 5))
        url = f"http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results={max_results}"

        feed = feedparser.parse(url)
        improvement_ids: List[str] = []
        for entry in feed.entries:
            improvement_id = await self._create_improvement(
                name=entry.get("title", "ArXiv Paper"),
                description=entry.get("summary", "")[:500],
                source=DiscoverySource.ARXIV,
                source_url=entry.get("link", ""),
                improvement_type=ImprovementType.NEW_ALGORITHM,
                target_agent_id=task.filters.get("target_agent_id", "system"),
                relevance_score=0.6,
                implementation_complexity=0.7,
                potential_impact=0.6,
                dependencies=[],
                requirements={}
            )
            improvement_ids.append(improvement_id)

        return improvement_ids
    
    async def _discover_from_custom_source(self, task: DiscoveryTask) -> List[str]:
        """Discover improvements from a custom source"""
        self.logger.info(f"Discovering from custom source: {task.query}")
        
        # This would be implemented based on the specific custom source
        # For now, we'll return an empty list
        
        return []

    async def _discover_from_discord_ideas(self, task: DiscoveryTask) -> List[str]:
        """Parse Ideas catalog and update idea status data"""
        self.logger.info("Parsing Discord ideas catalog")
        ideas = self._parse_ideas_document()
        if not ideas:
            return []

        ideas_payload = [idea.__dict__ for idea in ideas]
        self._write_json(self.idea_data_dir / "ideas_parsed.json", ideas_payload)
        self.metrics["ideas_parsed"] = len(ideas)

        status_overrides = self._load_status_overrides()
        ideas_status = []
        for idea in ideas:
            status = self._apply_status_overrides(idea, status_overrides)
            ideas_status.append({
                "entry_id": idea.entry_id,
                "status": status,
                "section": idea.section,
                "channel": idea.channel,
                "title": idea.title,
                "url": idea.url,
                "date": idea.date,
                "author": idea.author
            })

        self._write_json(self.idea_data_dir / "ideas_status.json", ideas_status)
        self.metrics["ideas_status_updated"] = len(ideas_status)
        return []

    async def _discover_from_codebase_scan(self, task: DiscoveryTask) -> List[str]:
        """Discover improvements from gap reports"""
        improvement_ids: List[str] = []
        gap_latest = Path(task.filters.get("gap_report_latest", ".cursor/gap_report_latest.json"))
        if not gap_latest.exists():
            self.logger.warning("Gap report not found; skipping codebase scan")
            return []

        gaps = self._read_json(gap_latest) or {}
        items = gaps.get("todos_fixmes", [])
        for item in items[:25]:
            improvement_type = ImprovementType.BUG_FIX if item.get("kind") == "BUG" else ImprovementType.DOCUMENTATION
            name = f"{item.get('kind', 'GAP')}: {item.get('file', '')}"
            description = item.get("line", "") or item.get("message", "")
            improvement_id = await self._create_improvement(
                name=name,
                description=description,
                source=DiscoverySource.CODEBASE_SCAN,
                source_url=item.get("file", ""),
                improvement_type=improvement_type,
                target_agent_id="system",
                relevance_score=0.6,
                implementation_complexity=0.4,
                potential_impact=0.6,
                dependencies=[],
                requirements={"repo": item.get("repo")}
            )
            improvement_ids.append(improvement_id)

        self.metrics["codebase_findings"] += len(improvement_ids)
        return improvement_ids

    async def start_evolution_loop(self) -> None:
        """Run discovery loop continuously"""
        while self.status == AgentStatus.RUNNING:
            try:
                now = datetime.utcnow()
                for task_id, task in self.discovery_tasks.items():
                    if task.is_active and task.next_run and task.next_run <= now:
                        await self.run_discovery_task(task_id)
                await asyncio.sleep(3600)
            except Exception as exc:
                self.logger.error(f"Evolution loop error: {exc}")
                await asyncio.sleep(60)

    def _parse_ideas_document(self) -> List[IdeaEntry]:
        """Parse the ideas document into structured entries"""
        if not self.ideas_doc_path.exists():
            self.logger.warning(f"Ideas doc not found: {self.ideas_doc_path}")
            return []

        entries: List[IdeaEntry] = []
        section = ""
        channel = None
        link_re = re.compile(r"^- \[(.+?)\]\((.+?)\)\s+`(\d{4}-\d{2}-\d{2})`\s+\*(.+?)\*")
        note_re = re.compile(r"^- `(\d{4}-\d{2}-\d{2})`\s+\*\*(.+?)\*\*:\s+(.*)")

        for line in self.ideas_doc_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("## "):
                section = line.replace("## ", "").strip()
                channel = None
                continue
            if line.startswith("### "):
                channel = line.replace("### ", "").strip()
                continue

            link_match = link_re.match(line)
            if link_match:
                title, url, date, author = link_match.groups()
                entry_id = f"idea_{uuid.uuid4().hex[:10]}"
                entries.append(IdeaEntry(
                    entry_id=entry_id,
                    entry_type="link",
                    title=title,
                    url=url,
                    date=date,
                    author=author,
                    section=section,
                    channel=channel,
                    raw=line
                ))
                continue

            note_match = note_re.match(line)
            if note_match:
                date, author, text = note_match.groups()
                entry_id = f"idea_{uuid.uuid4().hex[:10]}"
                entries.append(IdeaEntry(
                    entry_id=entry_id,
                    entry_type="note",
                    title=text,
                    url=None,
                    date=date,
                    author=author,
                    section=section,
                    channel=channel,
                    raw=line
                ))
                continue

        return entries

    def _load_status_overrides(self) -> Dict[str, str]:
        """Load status overrides from the tracker document"""
        if not self.status_tracker_path.exists():
            return {}

        overrides: Dict[str, str] = {}
        pattern = re.compile(r"^- \*\*(Implemented|Partial)\*\*:\s*(.+)")
        for line in self.status_tracker_path.read_text(encoding="utf-8").splitlines():
            match = pattern.match(line.strip())
            if match:
                status, title = match.groups()
                overrides[title.strip().lower()] = status.lower()
        return overrides

    def _apply_status_overrides(self, idea: IdeaEntry, overrides: Dict[str, str]) -> str:
        """Apply status overrides based on title keyword match"""
        title = (idea.title or "").lower()
        for key, status in overrides.items():
            if key in title:
                return status
        return "not_started"

    def _write_json(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    def _read_json(self, path: Path) -> Optional[Dict[str, Any]]:
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    
    async def _create_improvement(
        self,
        name: str,
        description: str,
        source: DiscoverySource,
        source_url: str,
        improvement_type: ImprovementType,
        target_agent_id: str,
        relevance_score: float,
        implementation_complexity: float,
        potential_impact: float,
        code_snippets: Optional[List[str]] = None,
        dependencies: Optional[List[str]] = None,
        requirements: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new improvement"""
        improvement_id = f"improvement_{uuid.uuid4().hex[:8]}"
        
        improvement = Improvement(
            improvement_id=improvement_id,
            name=name,
            description=description,
            source=source,
            source_url=source_url,
            improvement_type=improvement_type,
            target_agent_id=target_agent_id,
            relevance_score=relevance_score,
            implementation_complexity=implementation_complexity,
            potential_impact=potential_impact,
            code_snippets=code_snippets or [],
            dependencies=dependencies or [],
            requirements=requirements or {},
            metadata=metadata or {}
        )
        
        self.improvements[improvement_id] = improvement
        await self._save_data()
        
        self.metrics["improvements_discovered"] += 1
        
        # Add to evaluation queue
        await self.evaluation_queue.put(improvement_id)
        
        return improvement_id
    
    async def _load_data(self) -> None:
        """Load data from disk"""
        # Load improvements
        improvements_file = self.data_dir / "improvements.json"
        if improvements_file.exists():
            with open(improvements_file, "r") as f:
                improvements_data = json.load(f)
                
                for improvement_data in improvements_data:
                    improvement = Improvement(
                        improvement_id=improvement_data["improvement_id"],
                        name=improvement_data["name"],
                        description=improvement_data["description"],
                        source=DiscoverySource[improvement_data["source"]],
                        source_url=improvement_data["source_url"],
                        improvement_type=ImprovementType[improvement_data["improvement_type"]],
                        target_agent_id=improvement_data["target_agent_id"],
                        relevance_score=improvement_data["relevance_score"],
                        implementation_complexity=improvement_data["implementation_complexity"],
                        potential_impact=improvement_data["potential_impact"],
                        status=EvaluationStatus[improvement_data["status"]],
                        code_snippets=improvement_data.get("code_snippets", []),
                        dependencies=improvement_data.get("dependencies", []),
                        requirements=improvement_data.get("requirements", {}),
                        implementation_steps=improvement_data.get("implementation_steps", []),
                        test_cases=improvement_data.get("test_cases", []),
                        metadata=improvement_data.get("metadata", {}),
                        created_at=datetime.fromisoformat(improvement_data["created_at"]),
                        updated_at=datetime.fromisoformat(improvement_data["updated_at"])
                    )
                    
                    self.improvements[improvement.improvement_id] = improvement
        
        # Load discovery tasks
        tasks_file = self.data_dir / "discovery_tasks.json"
        if tasks_file.exists():
            with open(tasks_file, "r") as f:
                tasks_data = json.load(f)
                
                for task_data in tasks_data:
                    task = DiscoveryTask(
                        task_id=task_data["task_id"],
                        source=DiscoverySource[task_data["source"]],
                        query=task_data["query"],
                        filters=task_data.get("filters", {}),
                        last_run=datetime.fromisoformat(task_data["last_run"]) if task_data.get("last_run") else None,
                        next_run=datetime.fromisoformat(task_data["next_run"]) if task_data.get("next_run") else None,
                        is_active=task_data.get("is_active", True),
                        metadata=task_data.get("metadata", {}),
                        created_at=datetime.fromisoformat(task_data["created_at"]),
                        updated_at=datetime.fromisoformat(task_data["updated_at"])
                    )
                    
                    self.discovery_tasks[task.task_id] = task
        
        # Load evaluation results
        results_file = self.data_dir / "evaluation_results.json"
        if results_file.exists():
            with open(results_file, "r") as f:
                results_data = json.load(f)
                
                for result_data in results_data:
                    result = EvaluationResult(
                        result_id=result_data["result_id"],
                        improvement_id=result_data["improvement_id"],
                        evaluator_agent_id=result_data["evaluator_agent_id"],
                        score=result_data["score"],
                        recommendation=result_data["recommendation"],
                        implementation_plan=result_data.get("implementation_plan"),
                        estimated_effort=result_data.get("estimated_effort"),
                        risks=result_data.get("risks", []),
                        benefits=result_data.get("benefits", []),
                        metadata=result_data.get("metadata", {}),
                        created_at=datetime.fromisoformat(result_data["created_at"])
                    )
                    
                    self.evaluation_results[result.result_id] = result
        
        # Load implementation plans
        plans_file = self.data_dir / "implementation_plans.json"
        if plans_file.exists():
            with open(plans_file, "r") as f:
                plans_data = json.load(f)
                
                for plan_data in plans_data:
                    plan = ImplementationPlan(
                        plan_id=plan_data["plan_id"],
                        improvement_id=plan_data["improvement_id"],
                        target_agent_id=plan_data["target_agent_id"],
                        steps=plan_data.get("steps", []),
                        dependencies=plan_data.get("dependencies", []),
                        estimated_duration=plan_data.get("estimated_duration"),
                        priority=TaskPriority[plan_data["priority"]],
                        status=plan_data.get("status", "pending"),
                        metadata=plan_data.get("metadata", {}),
                        created_at=datetime.fromisoformat(plan_data["created_at"]),
                        updated_at=datetime.fromisoformat(plan_data["updated_at"])
                    )
                    
                    self.implementation_plans[plan.plan_id] = plan
        
        # Load agent registry
        registry_file = self.data_dir / "agent_registry.json"
        if registry_file.exists():
            with open(registry_file, "r") as f:
                self.agent_registry = json.load(f)
    
    async def _save_data(self) -> None:
        """Save data to disk"""
        # Save improvements
        improvements_file = self.data_dir / "improvements.json"
        improvements_data = []
        
        for improvement in self.improvements.values():
            improvement_data = {
                "improvement_id": improvement.improvement_id,
                "name": improvement.name,
                "description": improvement.description,
                "source": improvement.source.name,
                "source_url": improvement.source_url,
                "improvement_type": improvement.improvement_type.name,
                "target_agent_id": improvement.target_agent_id,
                "relevance_score": improvement.relevance_score,
                "implementation_complexity": improvement.implementation_complexity,
                "potential_impact": improvement.potential_impact,
                "status": improvement.status.name,
                "code_snippets": improvement.code_snippets,
                "dependencies": improvement.dependencies,
                "requirements": improvement.requirements,
                "implementation_steps": improvement.implementation_steps,
                "test_cases": improvement.test_cases,
                "metadata": improvement.metadata,
                "created_at": improvement.created_at.isoformat(),
                "updated_at": improvement.updated_at.isoformat()
            }
            improvements_data.append(improvement_data)
        
        with open(improvements_file, "w") as f:
            json.dump(improvements_data, f, indent=2)
        
        # Save discovery tasks
        tasks_file = self.data_dir / "discovery_tasks.json"
        tasks_data = []
        
        for task in self.discovery_tasks.values():
            task_data = {
                "task_id": task.task_id,
                "source": task.source.name,
                "query": task.query,
                "filters": task.filters,
                "last_run": task.last_run.isoformat() if task.last_run else None,
                "next_run": task.next_run.isoformat() if task.next_run else None,
                "is_active": task.is_active,
                "metadata": task.metadata,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat()
            }
            tasks_data.append(task_data)
        
        with open(tasks_file, "w") as f:
            json.dump(tasks_data, f, indent=2)
        
        # Save evaluation results
        results_file = self.data_dir / "evaluation_results.json"
        results_data = []
        
        for result in self.evaluation_results.values():
            result_data = {
                "result_id": result.result_id,
                "improvement_id": result.improvement_id,
                "evaluator_agent_id": result.evaluator_agent_id,
                "score": result.score,
                "recommendation": result.recommendation,
                "implementation_plan": result.implementation_plan,
                "estimated_effort": result.estimated_effort,
                "risks": result.risks,
                "benefits": result.benefits,
                "metadata": result.metadata,
                "created_at": result.created_at.isoformat()
            }
            results_data.append(result_data)
        
        with open(results_file, "w") as f:
            json.dump(results_data, f, indent=2)
        
        # Save implementation plans
        plans_file = self.data_dir / "implementation_plans.json"
        plans_data = []
        
        for plan in self.implementation_plans.values():
            plan_data = {
                "plan_id": plan.plan_id,
                "improvement_id": plan.improvement_id,
                "target_agent_id": plan.target_agent_id,
                "steps": plan.steps,
                "dependencies": plan.dependencies,
                "estimated_duration": plan.estimated_duration,
                "priority": plan.priority.name,
                "status": plan.status,
                "metadata": plan.metadata,
                "created_at": plan.created_at.isoformat(),
                "updated_at": plan.updated_at.isoformat()
            }
            plans_data.append(plan_data)
        
        with open(plans_file, "w") as f:
            json.dump(plans_data, f, indent=2)
        
        # Save agent registry
        registry_file = self.data_dir / "agent_registry.json"
        with open(registry_file, "w") as f:
            json.dump(self.agent_registry, f, indent=2)
    
    async def _process_discovery_queue(self) -> None:
        """Process the discovery queue"""
        while self.status == AgentStatus.RUNNING:
            try:
                # Check for tasks that need to be run
                now = datetime.utcnow()
                for task_id, task in self.discovery_tasks.items():
                    if task.is_active and task.next_run and task.next_run <= now:
                        # Run the task
                        await self.run_discovery_task(task_id)
                
                # Sleep for a while before checking again
                await asyncio.sleep(3600)  # Check every hour
                
            except Exception as e:
                self.logger.error(f"Error processing discovery queue: {str(e)}")
                await asyncio.sleep(60)  # Sleep for a minute before retrying
    
    async def _process_evaluation_queue(self) -> None:
        """Process the evaluation queue"""
        while self.status == AgentStatus.RUNNING:
            try:
                # Get next item to evaluate
                improvement_id = await self.evaluation_queue.get()
                
                # Evaluate the improvement
                await self._evaluate_improvement(improvement_id)
                
                # Mark task as complete
                self.evaluation_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error processing evaluation queue: {str(e)}")
                continue
    
    async def _process_implementation_queue(self) -> None:
        """Process the implementation queue"""
        while self.status == AgentStatus.RUNNING:
            try:
                # Get next plan to implement
                plan_id = await self.implementation_queue.get()
                
                # Implement the plan
                await self._implement_plan(plan_id)
                
                # Mark task as complete
                self.implementation_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error processing implementation queue: {str(e)}")
                continue
    
    async def _evaluate_improvement(self, improvement_id: str) -> None:
        """Evaluate an improvement"""
        if improvement_id not in self.improvements:
            return
        
        improvement = self.improvements[improvement_id]
        improvement.status = EvaluationStatus.EVALUATING
        improvement.updated_at = datetime.utcnow()
        
        # In a real implementation, this would involve more sophisticated evaluation
        # For now, we'll use a simple heuristic based on relevance and impact
        
        # Calculate a score based on relevance, impact, and complexity
        score = (improvement.relevance_score * 0.5 + 
                 improvement.potential_impact * 0.3 + 
                 (1 - improvement.implementation_complexity) * 0.2)
        
        # Determine recommendation
        recommendation = "Implement" if score >= 0.7 else "Reject"
        
        # Create evaluation result
        await self.evaluate_improvement(
            improvement_id=improvement_id,
            evaluator_agent_id=self.agent_id,
            score=score,
            recommendation=recommendation,
            estimated_effort=improvement.implementation_complexity,
            risks=["Integration challenges", "Performance impact"],
            benefits=["Improved functionality", "Better accuracy"]
        )
        
        self.metrics["evaluation_tasks_run"] += 1
    
    async def _implement_plan(self, plan_id: str) -> None:
        """Implement a plan"""
        if plan_id not in self.implementation_plans:
            return
        
        plan = self.implementation_plans[plan_id]
        plan.status = "in_progress"
        plan.updated_at = datetime.utcnow()
        
        # In a real implementation, this would involve actual code changes
        # For now, we'll simulate implementation
        
        # Simulate implementation steps
        for i, step in enumerate(plan.steps):
            self.logger.info(f"Implementing step {i+1}/{len(plan.steps)}: {step.get('name', 'Unknown step')}")
            await asyncio.sleep(1)  # Simulate work
        
        # Update plan status
        plan.status = "completed"
        plan.updated_at = datetime.utcnow()
        
        # Update improvement status
        improvement = self.improvements[plan.improvement_id]
        improvement.status = EvaluationStatus.DEPLOYED
        improvement.updated_at = datetime.utcnow()
        
        self.metrics["implementation_tasks_run"] += 1
        self.metrics["improvements_implemented"] += 1
        
        await self._save_data() 