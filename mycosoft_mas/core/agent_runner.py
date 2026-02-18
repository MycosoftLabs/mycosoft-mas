"""
MYCA 24/7 Agent Runner
Continuous agent operation with work compilation into knowledge bases.

This module runs agents continuously in cycles, compiling their work into:
- Workloads database
- Wisdom/insights storage
- Knowledge base updates
- NAS-backed persistent storage for live monitoring
"""

import asyncio
import logging
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import aiofiles
import httpx

logger = logging.getLogger(__name__)

# Storage paths - use NAS if available
NAS_BASE_PATH = os.getenv("NAS_STORAGE_PATH", "/mnt/nas/mycosoft/mas")
LOCAL_BASE_PATH = os.getenv("LOCAL_STORAGE_PATH", "./data/agent_work")

# Determine storage path
STORAGE_PATH = Path(NAS_BASE_PATH if os.path.exists(NAS_BASE_PATH) else LOCAL_BASE_PATH)


@dataclass
class WorkCycle:
    """Represents a single agent work cycle."""
    cycle_id: str
    agent_id: str
    agent_name: str
    started_at: str
    completed_at: Optional[str] = None
    status: str = "running"
    tasks_processed: int = 0
    insights_generated: int = 0
    knowledge_added: int = 0
    errors: List[str] = None
    summary: str = ""

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


@dataclass
class AgentInsight:
    """An insight discovered by an agent."""
    insight_id: str
    agent_id: str
    agent_name: str
    category: str
    title: str
    description: str
    confidence: float
    timestamp: str
    data: Dict[str, Any] = None
    actionable: bool = False
    priority: str = "normal"  # low, normal, high, critical

    def __post_init__(self):
        if self.data is None:
            self.data = {}


@dataclass
class AdminNotification:
    """Notification to be sent to Morgan (super admin)."""
    notification_id: str
    timestamp: str
    type: str  # task_complete, insight, error, news, discovery
    title: str
    message: str
    agent: str
    priority: str = "normal"  # low, normal, high, critical
    requires_action: bool = False
    data: Dict[str, Any] = None

    def __post_init__(self):
        if self.data is None:
            self.data = {}


class AgentCycleRunner:
    """
    Runs agents continuously in cycles, 24/7 operation.
    
    Features:
    - Continuous agent cycling
    - Work compilation into databases
    - Knowledge base updates
    - NAS-backed storage for monitoring
    - Admin notifications for Morgan
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.running = False
        self.cycles: Dict[str, WorkCycle] = {}
        self.insights: List[AgentInsight] = []
        self.notifications: List[AdminNotification] = []
        self._agents = []
        self._cycle_interval = self.config.get("cycle_interval", 300)  # 5 minutes default
        self._notification_queue: asyncio.Queue = asyncio.Queue()
        
        # Ensure storage directories exist
        self._ensure_storage()

    def _ensure_storage(self):
        """Ensure storage directories exist."""
        dirs = [
            STORAGE_PATH / "cycles",
            STORAGE_PATH / "insights",
            STORAGE_PATH / "notifications",
            STORAGE_PATH / "knowledge",
            STORAGE_PATH / "workloads",
            STORAGE_PATH / "wisdom",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
        logger.info(f"Agent storage initialized at: {STORAGE_PATH}")

    async def start(self, agents: List[Any] = None):
        """Start the continuous agent runner."""
        if self.running:
            logger.warning("Agent runner already running")
            return

        self.running = True
        self._agents = agents or []
        
        logger.info(f"Starting 24/7 Agent Runner with {len(self._agents)} agents")
        
        # Start background tasks
        asyncio.create_task(self._notification_worker())
        asyncio.create_task(self._run_cycles())
        
        # Notify admin of startup
        await self.notify_admin(
            type="system",
            title="MYCA System Online",
            message=f"24/7 Agent Runner started with {len(self._agents)} agents. All systems operational.",
            agent="MYCA",
            priority="high"
        )

    async def stop(self):
        """Stop the agent runner."""
        self.running = False
        logger.info("Stopping 24/7 Agent Runner")
        
        await self.notify_admin(
            type="system",
            title="MYCA System Shutdown",
            message="24/7 Agent Runner shutting down.",
            agent="MYCA",
            priority="critical"
        )

    async def _run_cycles(self):
        """Main cycle loop - runs agents continuously."""
        while self.running:
            cycle_start = datetime.now()
            
            for agent in self._agents:
                if not self.running:
                    break
                    
                try:
                    await self._run_agent_cycle(agent)
                except Exception as e:
                    logger.error(f"Error in agent cycle {agent.__class__.__name__}: {e}")
                    await self.notify_admin(
                        type="error",
                        title=f"Agent Error: {agent.__class__.__name__}",
                        message=str(e),
                        agent=agent.__class__.__name__,
                        priority="high"
                    )

            # Wait for next cycle
            elapsed = (datetime.now() - cycle_start).total_seconds()
            wait_time = max(0, self._cycle_interval - elapsed)
            if wait_time > 0 and self.running:
                await asyncio.sleep(wait_time)

    async def _run_agent_cycle(self, agent) -> WorkCycle:
        """Run a single cycle for an agent."""
        agent_name = agent.__class__.__name__
        cycle_id = f"{agent_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        cycle = WorkCycle(
            cycle_id=cycle_id,
            agent_id=getattr(agent, 'agent_id', 'unknown'),
            agent_name=agent_name,
            started_at=datetime.now().isoformat(),
        )
        self.cycles[cycle_id] = cycle

        logger.info(f"Starting cycle {cycle_id}")

        try:
            # Check if agent has a cycle method
            if hasattr(agent, 'run_cycle'):
                result = await agent.run_cycle()
                cycle.tasks_processed = result.get('tasks_processed', 0)
                cycle.insights_generated = result.get('insights_generated', 0)
                cycle.knowledge_added = result.get('knowledge_added', 0)
                cycle.summary = result.get('summary', 'Cycle completed')
                
                # Process any insights
                if result.get('insights'):
                    for insight_data in result['insights']:
                        insight = AgentInsight(
                            insight_id=f"insight_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.insights)}",
                            agent_id=cycle.agent_id,
                            agent_name=agent_name,
                            timestamp=datetime.now().isoformat(),
                            **insight_data
                        )
                        self.insights.append(insight)
                        await self._save_insight(insight)
                        
                        # Notify admin of high priority insights
                        if insight.priority in ['high', 'critical']:
                            await self.notify_admin(
                                type="insight",
                                title=insight.title,
                                message=insight.description,
                                agent=agent_name,
                                priority=insight.priority,
                                data=insight.data
                            )
            
            elif hasattr(agent, 'process_tasks'):
                # Legacy task processing
                await agent.process_tasks()
                cycle.tasks_processed = 1
                cycle.summary = "Legacy task processing completed"
            
            else:
                # Agent has no cycle/task method
                cycle.summary = "Agent idle - no work method defined"

            cycle.status = "completed"
            
        except Exception as e:
            cycle.status = "error"
            cycle.errors.append(str(e))
            cycle.summary = f"Error: {str(e)}"
            logger.error(f"Cycle {cycle_id} failed: {e}")

        cycle.completed_at = datetime.now().isoformat()
        
        # Save cycle to storage
        await self._save_cycle(cycle)
        
        return cycle

    async def _save_cycle(self, cycle: WorkCycle):
        """Save work cycle to NAS/local storage."""
        filepath = STORAGE_PATH / "cycles" / f"{cycle.cycle_id}.json"
        async with aiofiles.open(filepath, 'w') as f:
            await f.write(json.dumps(asdict(cycle), indent=2))

    async def _save_insight(self, insight: AgentInsight):
        """Save insight to storage."""
        filepath = STORAGE_PATH / "insights" / f"{insight.insight_id}.json"
        async with aiofiles.open(filepath, 'w') as f:
            await f.write(json.dumps(asdict(insight), indent=2))

    async def notify_admin(
        self,
        type: str,
        title: str,
        message: str,
        agent: str,
        priority: str = "normal",
        requires_action: bool = False,
        data: Dict[str, Any] = None
    ):
        """Queue a notification for Morgan (super admin)."""
        notification = AdminNotification(
            notification_id=f"notif_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.notifications)}",
            timestamp=datetime.now().isoformat(),
            type=type,
            title=title,
            message=message,
            agent=agent,
            priority=priority,
            requires_action=requires_action,
            data=data or {}
        )
        self.notifications.append(notification)
        await self._notification_queue.put(notification)

    async def _notification_worker(self):
        """Process notifications and send to admin."""
        while self.running:
            try:
                notification = await asyncio.wait_for(
                    self._notification_queue.get(),
                    timeout=10
                )
                
                # Save to storage
                filepath = STORAGE_PATH / "notifications" / f"{notification.notification_id}.json"
                async with aiofiles.open(filepath, 'w') as f:
                    await f.write(json.dumps(asdict(notification), indent=2))
                
                # Log for monitoring
                logger.info(f"[ADMIN NOTIFICATION] {notification.priority.upper()}: {notification.title}")
                
                # Send via webhook if configured
                await self._send_notification_webhook(notification)
                
                # Future: Add email, SMS, push notifications here
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Notification worker error: {e}")

    async def _send_notification_webhook(self, notification: AdminNotification) -> None:
        """Send notification via webhook to configured endpoints."""
        webhook_urls = os.getenv("NOTIFICATION_WEBHOOK_URLS", "").split(",")
        webhook_urls = [url.strip() for url in webhook_urls if url.strip()]
        
        if not webhook_urls:
            logger.debug("No webhook URLs configured for notifications")
            return
        
        payload = {
            "id": notification.notification_id,
            "priority": notification.priority,
            "category": notification.category,
            "title": notification.title,
            "message": notification.message,
            "timestamp": notification.timestamp,
            "source_agent": notification.source_agent,
            "metadata": notification.metadata,
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for webhook_url in webhook_urls:
                try:
                    response = await client.post(
                        webhook_url,
                        json=payload,
                        headers={"Content-Type": "application/json"}
                    )
                    if response.status_code in (200, 201, 202, 204):
                        logger.info(f"Notification webhook delivered to {webhook_url}")
                    else:
                        logger.warning(f"Webhook returned {response.status_code}: {webhook_url}")
                except Exception as e:
                    logger.error(f"Failed to send webhook to {webhook_url}: {e}")

    async def get_status(self) -> Dict[str, Any]:
        """Get current runner status."""
        return {
            "running": self.running,
            "agents": len(self._agents),
            "total_cycles": len(self.cycles),
            "total_insights": len(self.insights),
            "total_notifications": len(self.notifications),
            "storage_path": str(STORAGE_PATH),
            "cycle_interval": self._cycle_interval,
            "recent_cycles": [
                asdict(c) for c in list(self.cycles.values())[-10:]
            ],
            "recent_insights": [
                asdict(i) for i in self.insights[-10:]
            ],
            "recent_notifications": [
                asdict(n) for n in self.notifications[-10:]
            ],
        }

    async def compile_wisdom(self) -> Dict[str, Any]:
        """
        Compile accumulated insights into wisdom/knowledge.
        This creates a summary of all agent learnings.
        """
        wisdom = {
            "compiled_at": datetime.now().isoformat(),
            "total_insights": len(self.insights),
            "by_agent": {},
            "by_category": {},
            "actionable_items": [],
            "key_discoveries": [],
        }

        for insight in self.insights:
            # Group by agent
            if insight.agent_name not in wisdom["by_agent"]:
                wisdom["by_agent"][insight.agent_name] = []
            wisdom["by_agent"][insight.agent_name].append({
                "title": insight.title,
                "description": insight.description,
                "timestamp": insight.timestamp,
            })

            # Group by category
            if insight.category not in wisdom["by_category"]:
                wisdom["by_category"][insight.category] = []
            wisdom["by_category"][insight.category].append(insight.title)

            # Track actionable items
            if insight.actionable:
                wisdom["actionable_items"].append({
                    "title": insight.title,
                    "agent": insight.agent_name,
                    "priority": insight.priority,
                })

            # Track high-confidence discoveries
            if insight.confidence > 0.8:
                wisdom["key_discoveries"].append({
                    "title": insight.title,
                    "description": insight.description,
                    "confidence": insight.confidence,
                })

        # Save wisdom to storage
        filepath = STORAGE_PATH / "wisdom" / f"wisdom_{datetime.now().strftime('%Y%m%d')}.json"
        async with aiofiles.open(filepath, 'w') as f:
            await f.write(json.dumps(wisdom, indent=2))

        return wisdom


# Singleton instance
_runner: Optional[AgentCycleRunner] = None


def get_agent_runner() -> AgentCycleRunner:
    """Get the global agent runner singleton."""
    global _runner
    if _runner is None:
        _runner = AgentCycleRunner()
    return _runner


async def start_24_7_operation(agents: List[Any] = None):
    """Start 24/7 agent operation."""
    runner = get_agent_runner()
    await runner.start(agents)
    return runner
