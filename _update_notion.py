"""
Update Notion Workspace with Memory System Documentation
Requires NOTION_API_KEY and NOTION_DATABASE_ID environment variables

This script creates/updates the following pages:
1. Memory System - Full memory architecture documentation
2. Infrastructure - Proxmox, NAS, and backup schedules
3. MYCA Awareness - System monitoring and change detection
4. API Catalog - All available APIs and endpoints
"""

import asyncio
import os
import sys
from datetime import datetime

# Add the project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mycosoft_mas.integrations.notion_client import NotionClient


# Page content definitions
PAGES = {
    "Memory System": {
        "icon": "🧠",
        "content": """# MYCA Memory System - February 5, 2026

## Overview
The MYCA Memory System provides a comprehensive, multi-layered memory architecture for the Mycosoft Multi-Agent System.

## Six-Layer Architecture

### 1. Ephemeral Memory (30 min)
- Transient working data during active processing
- In-memory only storage
- Current calculation context, temporary variables

### 2. Session Memory (24 hours)
- Conversation context within a session
- Voice session turns, user preferences
- In-memory with persistence on session end

### 3. Working Memory (7 days)
- Short-term task-related information
- Active project context, recent decisions
- PostgreSQL backed

### 4. Semantic Memory (Permanent)
- Factual knowledge and learned patterns
- Entity relationships, skill knowledge
- PostgreSQL + Knowledge Graph

### 5. Episodic Memory (1 year+)
- Event-based autobiographical memories
- Task completions, significant interactions
- PostgreSQL with indexing

### 6. System Memory (Permanent)
- Configuration and system state
- Registry snapshots, health history
- PostgreSQL + File backups

## Key Components
- myca_memory.py - Core 6-layer implementation
- personaplex_memory.py - Voice session persistence
- n8n_memory.py - Workflow execution history
- mem0_adapter.py - Mem0-compatible adapter
- mcp_memory_server.py - MCP server for Claude
- persistent_graph.py - Knowledge graph with multi-hop reasoning

## Database Migrations
- 013_unified_memory.sql - Core memory tables
- 014_voice_sessions.sql - Voice session tracking
- 015_workflow_memory.sql - Workflow patterns
- 016_graph_persistence.sql - Knowledge graph

## Integration Bridges
- TypeScript: memory_bridge.ts
- C#: memory_bridge.cs
- C++: memory_bridge.hpp (ESP32 compatible)
""",
    },
    "Infrastructure": {
        "icon": "🏗️",
        "content": """# Mycosoft Infrastructure - February 5, 2026

## VM Inventory
| VM ID | Name | IP | Purpose |
|-------|------|-----|---------|
| 188 | MAS Containers | 192.168.0.188 | Multi-Agent System |
| 103 | Website Sandbox | 192.168.0.187 | mycosoft.com hosting |
| 189 | MINDEX VM | 192.168.0.189 | PostgreSQL + ETL |

## Proxmox Backup Schedule

### Daily Snapshots (2:00 AM)
- All VMs with 7-day retention
- Auto-cleanup of old snapshots

### Weekly Snapshots (Sunday 3:00 AM)
- All VMs with 4-week retention
- Full system state capture

### Monthly Snapshots (1st of month)
- All VMs with 12-month retention
- Long-term disaster recovery

### MINDEX Database Backup (4:00 AM)
- PostgreSQL pg_dump via SSH
- SCP transfer to Proxmox host
- Synchronized with VM snapshots

## NAS Organization
Mount: //192.168.0.105/mycosoft.com -> /mnt/mycosoft-nas

### Directory Structure
- dev/ - Development resources
  - builds/ - Build artifacts
  - configs/ - Configuration files
  - logs/ - Development logs
- mindex/ - MINDEX data
  - smell-samples/ - Olfactory sensor data
  - analysis-results/ - ML analysis outputs
  - sensor-calibration/ - Calibration data
- archives/ - Long-term storage
  - agent-snapshots/ - Agent state backups
  - etl-outputs/ - ETL job results
  - historical-data/ - Time-series archives
- media/ - Website assets
- shared/ - Cross-system resources

## Cryptographic Integrity
- SHA256 hashing for all files
- HMAC-SHA256 signatures with ledger recording
- Merkle root computation for data verification
- Dual-write to PostgreSQL and file-based ledgers
""",
    },
    "MYCA Awareness": {
        "icon": "👁️",
        "content": """# MYCA System Awareness - February 5, 2026

## Overview
MYCA maintains continuous awareness of the entire Mycosoft ecosystem through system monitoring, change detection, and automatic recovery.

## Components

### 1. System Monitor (system_monitor.py)
Tracks all registered systems with health checks:
- HTTP health endpoints
- TCP connectivity
- Container status
- Database connections
- Device heartbeats

### 2. Change Detector (change_detector.py)
Detects ecosystem changes:
- Code deployments (Git commits)
- Registry updates (systems, agents, devices)
- API changes (endpoints, schemas)
- Service health transitions
- Configuration updates

### 3. Orchestrator (orchestrator.py)
Enhanced with:
- Service health polling (60s intervals)
- Automatic failover to backups
- Circuit breaker pattern
- Retry with exponential backoff
- Recovery state restoration

## Registry Integration
- System Registry: 12+ registered systems
- Agent Registry: 96+ registered agents
- Device Registry: 22+ MycoBrain devices
- API Catalog: All endpoints indexed

## Awareness Events
The system emits events for:
- health_change: Service status transitions
- deployment: New code deployments
- registry_update: System/agent/device changes
- api_change: Endpoint modifications
- performance_anomaly: Metric deviations

## Continuous Monitoring
```python
monitor = await get_system_monitor()
await monitor.start_monitoring(interval_seconds=60)
```

## Recovery Protocol
1. Detect service failure
2. Log failure event
3. Attempt restart (3 retries)
4. If persistent, trigger failover
5. Notify via event stream
6. Restore from last known good state
""",
    },
    "API Catalog": {
        "icon": "📚",
        "content": """# Mycosoft API Catalog - February 5, 2026

## Core APIs

### MAS API (Port 8000)
- /api/v1/agents - Agent management
- /api/v1/memory - Memory operations
- /api/v1/registry - System/agent/device registry
- /api/v1/graph - Knowledge graph queries
- /api/v1/brain - MYCA brain interface

### Voice API (Port 8001)
- /api/voice/tts - Text-to-speech
- /api/voice/stt - Speech-to-text
- /api/voice/session - Session management

### MINDEX API (Port 8080)
- /api/mindex/smell - Olfactory data
- /api/mindex/analysis - ML analysis
- /api/mindex/sensor - Sensor management

### Website API (Port 3000)
- /api/products - Product catalog
- /api/devices - Device information
- /api/contact - Contact forms

## Integration APIs

### n8n Workflows (Port 5678)
- Webhook endpoints for automation
- Workflow execution triggers
- Event subscriptions

### PersonaPlex (Port 8765)
- WebSocket voice streaming
- Real-time conversation
- Context management

### Grafana (Port 3001)
- Dashboard embedding
- Metrics queries
- Alert management

### Prometheus (Port 9090)
- Metric scraping
- Alert rules
- Service discovery

## Authentication
- JWT tokens for user authentication
- API keys for service-to-service
- mTLS for internal services

## Rate Limits
- Public APIs: 100 req/min
- Authenticated: 1000 req/min
- Internal: Unlimited
""",
    },
}


def create_text_block(content: str) -> dict:
    """Create a Notion text block from content."""
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": content[:2000]}}]
        },
    }


def create_heading_block(text: str, level: int = 2) -> dict:
    """Create a Notion heading block."""
    heading_type = f"heading_{level}"
    return {
        "object": "block",
        "type": heading_type,
        heading_type: {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def markdown_to_blocks(markdown: str) -> list:
    """Convert markdown content to Notion blocks."""
    blocks = []
    lines = markdown.strip().split("\n")
    current_paragraph = []

    for line in lines:
        stripped = line.strip()

        # Headings
        if stripped.startswith("### "):
            if current_paragraph:
                blocks.append(
                    create_text_block("\n".join(current_paragraph))
                )
                current_paragraph = []
            blocks.append(create_heading_block(stripped[4:], 3))

        elif stripped.startswith("## "):
            if current_paragraph:
                blocks.append(
                    create_text_block("\n".join(current_paragraph))
                )
                current_paragraph = []
            blocks.append(create_heading_block(stripped[3:], 2))

        elif stripped.startswith("# "):
            if current_paragraph:
                blocks.append(
                    create_text_block("\n".join(current_paragraph))
                )
                current_paragraph = []
            blocks.append(create_heading_block(stripped[2:], 1))

        elif stripped.startswith("```"):
            # Code blocks - simplified handling
            if current_paragraph:
                blocks.append(
                    create_text_block("\n".join(current_paragraph))
                )
                current_paragraph = []

        elif stripped == "":
            if current_paragraph:
                blocks.append(
                    create_text_block("\n".join(current_paragraph))
                )
                current_paragraph = []

        else:
            current_paragraph.append(line)

    # Remaining content
    if current_paragraph:
        blocks.append(create_text_block("\n".join(current_paragraph)))

    return blocks[:100]  # Notion limit


async def update_notion_workspace():
    """Update Notion workspace with memory system documentation."""
    # Check for API key
    api_key = os.getenv("NOTION_API_KEY")
    database_id = os.getenv("NOTION_DATABASE_ID")

    if not api_key:
        print("ERROR: NOTION_API_KEY environment variable not set")
        print("\nTo set up Notion integration:")
        print("1. Go to https://www.notion.so/my-integrations")
        print("2. Create a new integration")
        print("3. Copy the API key")
        print("4. Set NOTION_API_KEY=<your-key>")
        print("5. Add the integration to your workspace")
        print("6. Set NOTION_DATABASE_ID=<database-id>")
        return False

    if not database_id:
        print("WARNING: NOTION_DATABASE_ID not set, will create standalone pages")

    print(f"Connecting to Notion API...")
    print(f"Timestamp: {datetime.now().isoformat()}")

    async with NotionClient() as client:
        # Health check
        health = await client.health_check()
        if health["status"] != "ok":
            print(f"ERROR: Notion API health check failed: {health.get('error')}")
            return False

        print(f"Notion API connected successfully\n")

        # Create/update pages
        for page_name, page_data in PAGES.items():
            print(f"Processing: {page_name}...")

            try:
                # Search for existing page
                search_results = await client.search(
                    query=page_name,
                    filter_properties={"property": "object", "value": "page"},
                )

                existing_page = None
                for result in search_results.get("results", []):
                    title_prop = result.get("properties", {}).get("title", {})
                    if title_prop:
                        titles = title_prop.get("title", [])
                        if titles and titles[0].get("plain_text") == page_name:
                            existing_page = result
                            break

                if existing_page:
                    # Update existing page
                    page_id = existing_page["id"]
                    print(f"  Found existing page: {page_id}")

                    # Append new content
                    blocks = markdown_to_blocks(page_data["content"])
                    if blocks:
                        await client.append_blocks(page_id, blocks[:50])
                        print(f"  Updated with {len(blocks)} blocks")

                elif database_id:
                    # Create new page in database
                    properties = {
                        "Name": {
                            "title": [{"text": {"content": page_name}}]
                        }
                    }

                    blocks = markdown_to_blocks(page_data["content"])
                    page = await client.create_page(
                        database_id=database_id,
                        properties=properties,
                        children=blocks[:50],
                    )
                    print(f"  Created page: {page['id']}")

                else:
                    print(f"  Skipped (no database_id and page not found)")

            except Exception as e:
                print(f"  ERROR: {e}")

        print("\n" + "=" * 50)
        print("Notion workspace update complete!")
        print("=" * 50)

        return True


async def main():
    """Main entry point."""
    print("=" * 50)
    print("MYCA Memory System - Notion Workspace Update")
    print(f"Date: February 5, 2026")
    print("=" * 50 + "\n")

    success = await update_notion_workspace()

    if success:
        print("\nPages created/updated:")
        for page_name in PAGES.keys():
            print(f"  - {page_name}")
    else:
        print("\nNotion update failed. See errors above.")

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
