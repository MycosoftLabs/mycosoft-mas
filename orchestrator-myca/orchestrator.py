import asyncio
import logging
import httpx
import time
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional
import os
from datetime import datetime
import json
from prometheus_client import Counter, Histogram, start_http_server
import redis
import psycopg2
from psycopg2.extras import RealDictCursor

from agents_config import AGENTS, TASK_TYPE_TO_AGENT

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
TASKS_PROCESSED = Counter('orchestrator_tasks_processed_total', 'Total number of tasks processed')
TASK_DURATION = Histogram('orchestrator_task_duration_seconds', 'Time spent processing tasks')
ERROR_COUNT = Counter('orchestrator_errors_total', 'Total number of errors')

# Redis client
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=int(os.getenv("REDIS_DB", 0))
)

# PostgreSQL connection
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        user=os.getenv("DB_USER", "mycosoft"),
        password=os.getenv("DB_PASSWORD", "mycosoft"),
        dbname=os.getenv("DB_NAME", "mycosoft"),
        cursor_factory=RealDictCursor
    )

app = FastAPI(title="Mycosoft Orchestrator")

class Task(BaseModel):
    task_type: str
    data: Dict[str, Any]
    priority: Optional[int] = 1
    retry_count: Optional[int] = 0

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    redis_status: str
    postgres_status: str
    agent_statuses: Dict[str, str]

async def check_agent_health(agent_id: str) -> str:
    """Check the health of a specific agent."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{AGENTS[agent_id]['endpoint']}/health")
            return "healthy" if response.status_code == 200 else "unhealthy"
    except Exception as e:
        logger.error(f"Health check failed for agent {agent_id}: {str(e)}")
        return "unhealthy"

async def get_agent_statuses() -> Dict[str, str]:
    """Get the health status of all agents."""
    tasks = [check_agent_health(agent_id) for agent_id in AGENTS.keys()]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return dict(zip(AGENTS.keys(), results))

@app.get("/health")
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    try:
        # Check Redis
        redis_status = "healthy" if redis_client.ping() else "unhealthy"
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        redis_status = "unhealthy"

    try:
        # Check PostgreSQL
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                postgres_status = "healthy"
    except Exception as e:
        logger.error(f"PostgreSQL health check failed: {str(e)}")
        postgres_status = "unhealthy"

    # Check agent statuses
    agent_statuses = await get_agent_statuses()

    return HealthResponse(
        status="healthy" if all(status == "healthy" for status in [redis_status, postgres_status] + list(agent_statuses.values())) else "degraded",
        timestamp=datetime.utcnow().isoformat(),
        redis_status=redis_status,
        postgres_status=postgres_status,
        agent_statuses=agent_statuses
    )

async def handle_task(task: Task) -> Dict[str, Any]:
    """Handle a task by routing it to the appropriate agent."""
    start_time = time.time()
    task_id = f"task_{int(start_time)}_{hash(json.dumps(task.dict()))}"

    try:
        # Get the appropriate agent for the task type
        agent_id = TASK_TYPE_TO_AGENT.get(task.task_type)
        if not agent_id:
            raise HTTPException(status_code=400, detail=f"Unknown task type: {task.task_type}")

        agent_config = AGENTS[agent_id]
        
        # Store task in Redis for tracking
        redis_client.setex(
            f"task:{task_id}",
            3600,  # 1 hour TTL
            json.dumps({
                "task_type": task.task_type,
                "agent": agent_id,
                "status": "processing",
                "start_time": start_time
            })
        )

        # Forward task to agent
        async with httpx.AsyncClient(timeout=agent_config["timeout"]) as client:
            response = await client.post(
                f"{agent_config['endpoint']}/task",
                json=task.dict()
            )
            response.raise_for_status()
            result = response.json()

        # Update task status in Redis
        redis_client.setex(
            f"task:{task_id}",
            3600,
            json.dumps({
                "task_type": task.task_type,
                "agent": agent_id,
                "status": "completed",
                "start_time": start_time,
                "end_time": time.time(),
                "result": result
            })
        )

        # Record metrics
        TASKS_PROCESSED.inc()
        TASK_DURATION.observe(time.time() - start_time)

        return result

    except httpx.HTTPError as e:
        ERROR_COUNT.inc()
        logger.error(f"HTTP error processing task {task_id}: {str(e)}")
        
        # Update task status in Redis
        redis_client.setex(
            f"task:{task_id}",
            3600,
            json.dumps({
                "task_type": task.task_type,
                "agent": agent_id,
                "status": "failed",
                "start_time": start_time,
                "end_time": time.time(),
                "error": str(e)
            })
        )

        if task.retry_count < agent_config["retry_count"]:
            # Schedule retry
            await asyncio.sleep(agent_config["retry_delay"])
            task.retry_count += 1
            return await handle_task(task)
        else:
            raise HTTPException(status_code=500, detail=f"Task failed after {task.retry_count} retries: {str(e)}")

    except Exception as e:
        ERROR_COUNT.inc()
        logger.error(f"Error processing task {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/task")
async def process_task(task: Task, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Process a task by routing it to the appropriate agent."""
    background_tasks.add_task(handle_task, task)
    return {"status": "accepted", "message": "Task is being processed"}

@app.get("/task/{task_id}")
async def get_task_status(task_id: str) -> Dict[str, Any]:
    """Get the status of a specific task."""
    task_data = redis_client.get(f"task:{task_id}")
    if not task_data:
        raise HTTPException(status_code=404, detail="Task not found")
    return json.loads(task_data)

@app.on_event("startup")
async def startup_event():
    """Initialize the orchestrator on startup."""
    # Start Prometheus metrics server
    start_http_server(8001)
    logger.info("Orchestrator started with Prometheus metrics on port 8001")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 