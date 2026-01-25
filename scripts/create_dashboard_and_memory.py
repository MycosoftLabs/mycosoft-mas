#!/usr/bin/env python3
"""
Create MAS v2 Dashboard and Memory System Files

This script creates:
1. Real-time agent monitoring dashboard components
2. Memory systems (Redis short-term, MINDEX/Qdrant long-term)
3. MINDEX database schema additions
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent


def create_memory_manager():
    """Create unified memory manager"""
    content = '''"""
MAS v2 Memory Manager

Unified memory system for agents with:
- Short-term memory (Redis) - Conversation context, task state
- Long-term memory (MINDEX/PostgreSQL) - Activity logs, decision history
- Vector memory (Qdrant) - Knowledge embeddings
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

import redis.asyncio as redis
import aiohttp

from mycosoft_mas.runtime import AgentMessage


logger = logging.getLogger("MemoryManager")


class ShortTermMemory:
    """
    Redis-based short-term memory.
    
    Stores:
    - Conversation context (last N messages)
    - Current task state
    - Agent configuration
    - Temporary data
    """
    
    def __init__(self, agent_id: str, redis_url: Optional[str] = None):
        self.agent_id = agent_id
        self.redis_url = redis_url or os.environ.get("REDIS_URL", "redis://redis:6379/0")
        self.redis: Optional[redis.Redis] = None
        self.prefix = f"mas:memory:{agent_id}"
        self.default_ttl = 3600  # 1 hour
    
    async def connect(self):
        """Connect to Redis"""
        self.redis = redis.from_url(self.redis_url, decode_responses=True)
        await self.redis.ping()
        logger.info(f"Short-term memory connected for {self.agent_id}")
    
    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set a value in memory"""
        full_key = f"{self.prefix}:{key}"
        serialized = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
        await self.redis.set(full_key, serialized, ex=ttl or self.default_ttl)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from memory"""
        full_key = f"{self.prefix}:{key}"
        value = await self.redis.get(full_key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None
    
    async def delete(self, key: str):
        """Delete a value from memory"""
        full_key = f"{self.prefix}:{key}"
        await self.redis.delete(full_key)
    
    async def add_to_conversation(self, message: Dict[str, Any]):
        """Add a message to conversation history"""
        conv_key = f"{self.prefix}:conversation"
        await self.redis.rpush(conv_key, json.dumps(message))
        await self.redis.ltrim(conv_key, -10, -1)  # Keep last 10 messages
        await self.redis.expire(conv_key, self.default_ttl)
    
    async def get_conversation(self) -> List[Dict[str, Any]]:
        """Get conversation history"""
        conv_key = f"{self.prefix}:conversation"
        messages = await self.redis.lrange(conv_key, 0, -1)
        return [json.loads(m) for m in messages]
    
    async def set_task_state(self, task_id: str, state: Dict[str, Any]):
        """Set current task state"""
        await self.set(f"task:{task_id}", state)
    
    async def get_task_state(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get current task state"""
        return await self.get(f"task:{task_id}")


class LongTermMemory:
    """
    MINDEX-based long-term memory.
    
    Stores:
    - Agent activity logs
    - Decision history
    - Performance metrics
    - Permanent knowledge
    """
    
    def __init__(self, agent_id: str, mindex_url: Optional[str] = None):
        self.agent_id = agent_id
        self.mindex_url = mindex_url or os.environ.get("MINDEX_URL", "http://mindex:8000")
    
    async def log_activity(
        self,
        action_type: str,
        input_summary: str,
        output_summary: Optional[str] = None,
        success: bool = True,
        duration_ms: int = 0,
        related_agents: Optional[List[str]] = None,
    ):
        """Log an activity to MINDEX"""
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(
                    f"{self.mindex_url}/api/agent_logs",
                    json={
                        "agent_id": self.agent_id,
                        "action_type": action_type,
                        "input_summary": input_summary[:500],
                        "output_summary": output_summary[:500] if output_summary else None,
                        "success": success,
                        "duration_ms": duration_ms,
                        "related_agents": related_agents or [],
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to log activity to MINDEX: {e}")
    
    async def log_decision(
        self,
        decision_type: str,
        context: Dict[str, Any],
        decision: str,
        reasoning: str,
    ):
        """Log a decision for future reference"""
        await self.log_activity(
            action_type=f"decision:{decision_type}",
            input_summary=json.dumps(context)[:500],
            output_summary=f"{decision}: {reasoning}"[:500],
            success=True,
        )
    
    async def get_activity_history(
        self,
        limit: int = 100,
        action_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get activity history from MINDEX"""
        try:
            params = {"agent_id": self.agent_id, "limit": limit}
            if action_type:
                params["action_type"] = action_type
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.mindex_url}/api/agent_logs",
                    params=params
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            logger.warning(f"Failed to get activity history: {e}")
        
        return []
    
    async def store_knowledge(self, key: str, value: Dict[str, Any]):
        """Store permanent knowledge"""
        # This would use a dedicated knowledge table
        await self.log_activity(
            action_type="knowledge:store",
            input_summary=f"key={key}",
            output_summary=json.dumps(value)[:500],
            success=True,
        )
    
    async def query_knowledge(self, query: str) -> List[Dict[str, Any]]:
        """Query stored knowledge"""
        # This would perform a semantic search
        return []


class VectorMemory:
    """
    Qdrant-based vector memory for semantic search.
    
    Stores:
    - Document embeddings
    - Conversation embeddings
    - Knowledge graph embeddings
    """
    
    def __init__(self, agent_id: str, qdrant_url: Optional[str] = None):
        self.agent_id = agent_id
        self.qdrant_url = qdrant_url or os.environ.get("QDRANT_URL", "http://qdrant:6333")
        self.collection_name = f"agent_{agent_id.replace('-', '_')}"
    
    async def ensure_collection(self):
        """Ensure collection exists"""
        try:
            async with aiohttp.ClientSession() as session:
                # Check if collection exists
                async with session.get(
                    f"{self.qdrant_url}/collections/{self.collection_name}"
                ) as resp:
                    if resp.status == 404:
                        # Create collection
                        await session.put(
                            f"{self.qdrant_url}/collections/{self.collection_name}",
                            json={
                                "vectors": {
                                    "size": 1536,  # OpenAI embedding size
                                    "distance": "Cosine",
                                }
                            }
                        )
                        logger.info(f"Created Qdrant collection: {self.collection_name}")
        except Exception as e:
            logger.warning(f"Failed to ensure Qdrant collection: {e}")
    
    async def store_embedding(
        self,
        embedding: List[float],
        payload: Dict[str, Any],
        point_id: Optional[str] = None,
    ):
        """Store an embedding"""
        point_id = point_id or str(uuid4())
        
        try:
            async with aiohttp.ClientSession() as session:
                await session.put(
                    f"{self.qdrant_url}/collections/{self.collection_name}/points",
                    json={
                        "points": [{
                            "id": point_id,
                            "vector": embedding,
                            "payload": payload,
                        }]
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to store embedding: {e}")
    
    async def search(
        self,
        query_embedding: List[float],
        limit: int = 5,
        filter_conditions: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar embeddings"""
        try:
            body = {
                "vector": query_embedding,
                "limit": limit,
                "with_payload": True,
            }
            if filter_conditions:
                body["filter"] = filter_conditions
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.qdrant_url}/collections/{self.collection_name}/points/search",
                    json=body
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result.get("result", [])
        except Exception as e:
            logger.warning(f"Failed to search embeddings: {e}")
        
        return []


class UnifiedMemoryManager:
    """
    Unified interface for all memory systems.
    
    Provides a single API for:
    - Short-term memory operations
    - Long-term memory storage
    - Semantic search
    """
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.short_term = ShortTermMemory(agent_id)
        self.long_term = LongTermMemory(agent_id)
        self.vector = VectorMemory(agent_id)
        self._connected = False
    
    async def connect(self):
        """Connect to all memory systems"""
        await self.short_term.connect()
        await self.vector.ensure_collection()
        self._connected = True
        logger.info(f"Memory manager connected for {self.agent_id}")
    
    async def close(self):
        """Close all connections"""
        await self.short_term.close()
        self._connected = False
    
    async def remember(
        self,
        key: str,
        value: Any,
        duration: str = "short",  # short, long, permanent
    ):
        """Store a memory"""
        if duration == "short":
            await self.short_term.set(key, value)
        elif duration == "long":
            await self.short_term.set(key, value, ttl=86400)  # 24 hours
        else:  # permanent
            await self.long_term.store_knowledge(key, {"value": value})
    
    async def recall(self, key: str) -> Optional[Any]:
        """Recall a memory"""
        # Try short-term first
        value = await self.short_term.get(key)
        if value:
            return value
        
        # Then try long-term
        history = await self.long_term.get_activity_history(
            limit=1,
            action_type=f"knowledge:store"
        )
        for item in history:
            if f"key={key}" in item.get("input_summary", ""):
                return item.get("output_summary")
        
        return None
    
    async def log(self, action: str, data: Dict[str, Any], success: bool = True):
        """Log an action"""
        await self.long_term.log_activity(
            action_type=action,
            input_summary=json.dumps(data)[:500],
            success=success,
        )
    
    async def add_to_context(self, message: Dict[str, Any]):
        """Add message to conversation context"""
        await self.short_term.add_to_conversation(message)
    
    async def get_context(self) -> List[Dict[str, Any]]:
        """Get conversation context"""
        return await self.short_term.get_conversation()
'''
    runtime_dir = BASE_DIR / "mycosoft_mas" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / "memory_manager.py").write_text(content)
    print("Created mycosoft_mas/runtime/memory_manager.py")


def create_mindex_schema():
    """Create MINDEX database schema for agent logging"""
    content = '''-- MAS v2 MINDEX Schema Additions
-- Agent activity logging and snapshot storage

-- Agent activity logs table
CREATE TABLE IF NOT EXISTS agent_logs (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(100) NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    action_type VARCHAR(100) NOT NULL,
    input_summary TEXT,
    output_summary TEXT,
    success BOOLEAN DEFAULT TRUE,
    duration_ms INTEGER DEFAULT 0,
    resources_used JSONB DEFAULT '{}',
    related_agents TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}'
);

-- Index for fast agent lookups
CREATE INDEX IF NOT EXISTS idx_agent_logs_agent_id ON agent_logs(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_logs_timestamp ON agent_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_agent_logs_action_type ON agent_logs(action_type);
CREATE INDEX IF NOT EXISTS idx_agent_logs_agent_timestamp ON agent_logs(agent_id, timestamp DESC);

-- Agent state snapshots table
CREATE TABLE IF NOT EXISTS agent_snapshots (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(100) NOT NULL,
    snapshot_time TIMESTAMPTZ DEFAULT NOW(),
    state JSONB NOT NULL,
    config JSONB NOT NULL,
    pending_tasks JSONB DEFAULT '[]',
    memory_state JSONB DEFAULT '{}',
    reason VARCHAR(255) DEFAULT 'manual'
);

-- Index for snapshot lookups
CREATE INDEX IF NOT EXISTS idx_agent_snapshots_agent_id ON agent_snapshots(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_snapshots_time ON agent_snapshots(snapshot_time DESC);

-- Agent metrics table for performance tracking
CREATE TABLE IF NOT EXISTS agent_metrics (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(100) NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    cpu_percent FLOAT DEFAULT 0,
    memory_mb INTEGER DEFAULT 0,
    tasks_completed INTEGER DEFAULT 0,
    tasks_failed INTEGER DEFAULT 0,
    avg_task_duration_ms FLOAT DEFAULT 0,
    messages_sent INTEGER DEFAULT 0,
    messages_received INTEGER DEFAULT 0,
    uptime_seconds INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0
);

-- Index for metrics
CREATE INDEX IF NOT EXISTS idx_agent_metrics_agent_id ON agent_metrics(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_metrics_timestamp ON agent_metrics(timestamp DESC);

-- Agent communication logs
CREATE TABLE IF NOT EXISTS agent_messages (
    id SERIAL PRIMARY KEY,
    message_id UUID NOT NULL,
    from_agent VARCHAR(100) NOT NULL,
    to_agent VARCHAR(100) NOT NULL,
    message_type VARCHAR(50) NOT NULL,
    payload JSONB DEFAULT '{}',
    priority INTEGER DEFAULT 5,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    correlation_id UUID,
    acknowledged BOOLEAN DEFAULT FALSE,
    ack_time TIMESTAMPTZ
);

-- Index for message lookups
CREATE INDEX IF NOT EXISTS idx_agent_messages_from ON agent_messages(from_agent);
CREATE INDEX IF NOT EXISTS idx_agent_messages_to ON agent_messages(to_agent);
CREATE INDEX IF NOT EXISTS idx_agent_messages_timestamp ON agent_messages(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_agent_messages_correlation ON agent_messages(correlation_id);

-- Agent knowledge store
CREATE TABLE IF NOT EXISTS agent_knowledge (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(100) NOT NULL,
    key VARCHAR(255) NOT NULL,
    value JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    UNIQUE(agent_id, key)
);

-- Index for knowledge lookups
CREATE INDEX IF NOT EXISTS idx_agent_knowledge_agent_id ON agent_knowledge(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_knowledge_key ON agent_knowledge(key);

-- Function to clean up old logs (run periodically)
CREATE OR REPLACE FUNCTION cleanup_old_agent_logs(days_to_keep INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM agent_logs 
    WHERE timestamp < NOW() - (days_to_keep || ' days')::INTERVAL;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to clean up old metrics (run periodically)
CREATE OR REPLACE FUNCTION cleanup_old_agent_metrics(days_to_keep INTEGER DEFAULT 7)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM agent_metrics 
    WHERE timestamp < NOW() - (days_to_keep || ' days')::INTERVAL;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- View for agent activity summary
CREATE OR REPLACE VIEW agent_activity_summary AS
SELECT 
    agent_id,
    COUNT(*) as total_actions,
    COUNT(*) FILTER (WHERE success = TRUE) as successful_actions,
    COUNT(*) FILTER (WHERE success = FALSE) as failed_actions,
    AVG(duration_ms) as avg_duration_ms,
    MAX(timestamp) as last_activity,
    MIN(timestamp) as first_activity
FROM agent_logs
GROUP BY agent_id;

-- View for recent agent errors
CREATE OR REPLACE VIEW recent_agent_errors AS
SELECT 
    agent_id,
    action_type,
    input_summary,
    output_summary,
    timestamp
FROM agent_logs
WHERE success = FALSE
ORDER BY timestamp DESC
LIMIT 100;

-- Grant permissions (adjust as needed)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON agent_logs TO mas_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON agent_snapshots TO mas_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON agent_metrics TO mas_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON agent_messages TO mas_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON agent_knowledge TO mas_user;
'''
    migrations_dir = BASE_DIR / "migrations"
    migrations_dir.mkdir(exist_ok=True)
    (migrations_dir / "003_agent_logging.sql").write_text(content)
    print("Created migrations/003_agent_logging.sql")


def create_dashboard_api():
    """Create dashboard API endpoints"""
    content = '''"""
MAS v2 Dashboard API

FastAPI routes for the real-time agent monitoring dashboard.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import StreamingResponse

from mycosoft_mas.runtime import (
    AgentPool,
    AgentState,
    AgentStatus,
    MessageBroker,
)


logger = logging.getLogger("DashboardAPI")
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: Dict[str, Any]):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


# Global references (set during app startup)
agent_pool: Optional[AgentPool] = None
message_broker: Optional[MessageBroker] = None


def set_agent_pool(pool: AgentPool):
    global agent_pool
    agent_pool = pool


def set_message_broker(broker: MessageBroker):
    global message_broker
    message_broker = broker


@router.get("/agents")
async def get_all_agents():
    """Get all agents with their current status"""
    if not agent_pool:
        return {"agents": [], "error": "Agent pool not initialized"}
    
    agents = await agent_pool.get_all_agents()
    return {
        "agents": [a.to_dict() for a in agents],
        "total": len(agents),
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/agents/{agent_id}")
async def get_agent_details(agent_id: str):
    """Get detailed information about a specific agent"""
    if not agent_pool:
        raise HTTPException(status_code=503, detail="Agent pool not initialized")
    
    agent = await agent_pool.get_agent_state(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return agent.to_dict()


@router.get("/agents/{agent_id}/logs")
async def get_agent_logs(agent_id: str, limit: int = 100):
    """Get recent logs for an agent"""
    # Would query MINDEX for logs
    return {
        "agent_id": agent_id,
        "logs": [],
        "limit": limit,
    }


@router.get("/stats")
async def get_pool_stats():
    """Get agent pool statistics"""
    if not agent_pool:
        return {"error": "Agent pool not initialized"}
    
    stats = await agent_pool.get_pool_stats()
    return {
        "stats": stats,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/topology")
async def get_topology():
    """Get agent topology for visualization"""
    if not agent_pool:
        return {"nodes": [], "edges": []}
    
    agents = await agent_pool.get_all_agents()
    
    # Build topology nodes
    nodes = [
        {
            "id": "orchestrator",
            "type": "orchestrator",
            "label": "MYCA Orchestrator",
            "status": "active",
        }
    ]
    
    for agent in agents:
        nodes.append({
            "id": agent.agent_id,
            "type": "agent",
            "label": agent.agent_id,
            "status": agent.status.value,
        })
    
    # Build edges (all agents connect to orchestrator)
    edges = [
        {"from": "orchestrator", "to": agent.agent_id}
        for agent in agents
    ]
    
    return {
        "nodes": nodes,
        "edges": edges,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    
    try:
        # Send initial state
        if agent_pool:
            agents = await agent_pool.get_all_agents()
            await websocket.send_json({
                "type": "initial_state",
                "agents": [a.to_dict() for a in agents],
            })
        
        # Keep connection alive and handle messages
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=30.0
                )
                
                # Handle client messages
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                elif data.get("type") == "subscribe":
                    agent_id = data.get("agent_id")
                    # Subscribe to specific agent updates
                    
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({"type": "heartbeat"})
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.get("/stream")
async def stream_updates():
    """Server-Sent Events endpoint for log streaming"""
    
    async def event_generator():
        while True:
            if agent_pool:
                agents = await agent_pool.get_all_agents()
                data = {
                    "type": "agent_update",
                    "agents": [a.to_dict() for a in agents],
                    "timestamp": datetime.utcnow().isoformat(),
                }
                yield f"data: {json.dumps(data)}\\n\\n"
            
            await asyncio.sleep(5)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


# Background task to broadcast updates
async def broadcast_updates():
    """Broadcast agent updates to all connected WebSocket clients"""
    while True:
        try:
            if agent_pool and manager.active_connections:
                agents = await agent_pool.get_all_agents()
                await manager.broadcast({
                    "type": "agent_update",
                    "agents": [a.to_dict() for a in agents],
                    "timestamp": datetime.utcnow().isoformat(),
                })
        except Exception as e:
            logger.error(f"Broadcast error: {e}")
        
        await asyncio.sleep(5)
'''
    core_dir = BASE_DIR / "mycosoft_mas" / "core"
    core_dir.mkdir(parents=True, exist_ok=True)
    (core_dir / "dashboard_api.py").write_text(content)
    print("Created mycosoft_mas/core/dashboard_api.py")


def create_dashboard_components():
    """Create placeholder for dashboard React components documentation"""
    content = '''# MAS v2 Dashboard Components

## Overview

The MYCA Dashboard provides real-time monitoring of all MAS agents.

## Required Components

### AgentGrid
- Grid view of all agents with status indicators
- Color-coded by status (green=active, yellow=busy, red=error)
- Click to view agent details

### AgentCard
- Individual agent status card
- Shows: ID, type, status, tasks completed/failed
- Mini-chart for recent activity

### AgentTerminal
- Real-time log viewer for individual agents
- Supports filtering and search
- Auto-scroll with pause option

### AgentTopology
- D3.js network graph
- Shows orchestrator at center
- Agents as nodes, connections as edges
- Message flow animation

### TaskQueue
- List of pending, active, completed tasks
- Filter by agent, status, priority
- Real-time updates

### MessageFlow
- Visualization of agent-to-agent messages
- Timeline view with message details
- Filter by agent pair

### ResourceMonitor
- CPU/Memory usage per agent
- Historical charts
- Alerts for threshold breaches

### AlertCenter
- Critical issues requiring attention
- Sortable by severity
- Action buttons for common operations

## API Endpoints

- GET /api/dashboard/agents - List all agents
- GET /api/dashboard/agents/{id} - Agent details
- GET /api/dashboard/agents/{id}/logs - Agent logs
- GET /api/dashboard/stats - Pool statistics
- GET /api/dashboard/topology - Graph data
- WS /api/dashboard/ws - Real-time WebSocket
- GET /api/dashboard/stream - SSE log stream

## WebSocket Message Types

### From Server
- initial_state: Full agent list on connect
- agent_update: Periodic agent status updates
- agent_event: Single agent event (start/stop/error)
- task_event: Task status change
- message_event: Agent-to-agent message

### From Client
- ping: Keep-alive
- subscribe: Subscribe to agent updates
- unsubscribe: Unsubscribe from agent

## Implementation Notes

Dashboard should be built at:
- website/app/myca/dashboard/page.tsx
- website/app/myca/agents/page.tsx
- website/app/myca/agents/[id]/page.tsx
- website/components/agents/

Use:
- React Query for data fetching
- Zustand for state management
- D3.js for topology visualization
- Tailwind CSS for styling
- shadcn/ui for UI components
'''
    docs_dir = BASE_DIR / "docs"
    docs_dir.mkdir(exist_ok=True)
    (docs_dir / "DASHBOARD_COMPONENTS.md").write_text(content)
    print("Created docs/DASHBOARD_COMPONENTS.md")


def main():
    """Create dashboard and memory system files"""
    print("Creating MAS v2 Dashboard and Memory System...")
    print(f"Base directory: {BASE_DIR}")
    print()
    
    create_memory_manager()
    create_mindex_schema()
    create_dashboard_api()
    create_dashboard_components()
    
    print()
    print("All dashboard and memory system files created!")


if __name__ == "__main__":
    main()
