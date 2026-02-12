# Autonomous Cursor System

**Created:** February 12, 2026  
**Status:** Implemented  
**Location:** `mycosoft_mas/mcp/`, `mycosoft_mas/services/`, `scripts/`

## Overview

The Autonomous Cursor System enables Cursor IDE to operate with significantly enhanced intelligence, self-improvement, and automation capabilities. It provides:

1. **MCP Servers** - Direct integration with Cursor via Model Context Protocol
2. **Auto-Learning** - Pattern detection, skill generation, agent creation
3. **Autonomous Operations** - Self-triggering tasks, deployment monitoring
4. **Continuous Improvement** - Daily self-improvement cycles

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CURSOR IDE                               │
├─────────────────────────────────────────────────────────────────┤
│  MCP Servers (.mcp.json)                                        │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│  │ mycosoft-    │ │ mycosoft-    │ │ mycosoft-    │            │
│  │ memory       │ │ tasks        │ │ orchestrator │            │
│  └──────────────┘ └──────────────┘ └──────────────┘            │
│  ┌──────────────┐                                               │
│  │ mycosoft-    │                                               │
│  │ registry     │                                               │
│  └──────────────┘                                               │
├─────────────────────────────────────────────────────────────────┤
│  Auto-Learning Scripts                                          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│  │ pattern_     │ │ skill_       │ │ agent_       │            │
│  │ scanner.py   │ │ generator.py │ │ factory.py   │            │
│  └──────────────┘ └──────────────┘ └──────────────┘            │
├─────────────────────────────────────────────────────────────────┤
│  Background Services                                            │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│  │ learning_    │ │ deployment_  │ │ autonomous_  │            │
│  │ feedback.py  │ │ feedback.py  │ │ scheduler.py │            │
│  └──────────────┘ └──────────────┘ └──────────────┘            │
├─────────────────────────────────────────────────────────────────┤
│  Orchestration                                                  │
│  ┌──────────────────────────────────────────────────┐          │
│  │ continuous_improvement.py                        │          │
│  │ (daily self-improvement loop)                    │          │
│  └──────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### Phase 1: MCP Infrastructure

#### Memory MCP (`mycosoft-memory`)
- **Location:** `mycosoft_mas/memory/mcp_memory_server.py`
- **Tools:** `memory_write`, `memory_read`, `memory_search`, `memory_list`
- **Purpose:** Persistent memory across Cursor sessions

#### Task Management MCP (`mycosoft-tasks`)
- **Location:** `mycosoft_mas/mcp/task_management_server.py`
- **Tools:**
  - `task_create` - Create new tasks with priority, assignment, due dates
  - `task_list` - List tasks by status, assignee, project
  - `task_update` - Update task status and details
  - `task_assign` - Assign task to agent or developer
  - `plan_get` - Get plan details from `.cursor/plans/`
  - `gap_scan` - Scan for TODOs, FIXMEs, and incomplete implementations

#### Orchestrator MCP (`mycosoft-orchestrator`)
- **Location:** `mycosoft_mas/mcp/orchestrator_server.py`
- **Tools:**
  - `agent_list` - List all MAS agents with capabilities
  - `agent_invoke` - Invoke a specific agent with parameters
  - `agent_status` - Get agent execution status
  - `system_health` - Check MAS, MINDEX, and website health
  - `workflow_trigger` - Trigger n8n workflows

#### Registry MCP (`mycosoft-registry`)
- **Location:** `mycosoft_mas/mcp/registry_server.py`
- **Tools:**
  - `registry_add_agent` - Register new MAS agents
  - `registry_add_api` - Register new API endpoints
  - `registry_add_skill` - Register new Cursor skills
  - `registry_sync` - Synchronize all registries
  - `docs_index` - Index documentation file
  - `docs_manifest` - Rebuild docs manifest

### Phase 2: Auto-Learning

#### Pattern Scanner
- **Location:** `scripts/pattern_scanner.py`
- **Purpose:** Detect repeated code patterns across repos
- **Detects:**
  - Function patterns (similar signatures, docstrings)
  - Class patterns (base classes, methods)
  - File structure patterns (similar directories)
  - Import patterns (common dependencies)
  - API route patterns (endpoints, methods)
  - Agent/skill definition patterns

#### Skill Generator
- **Location:** `scripts/skill_generator.py`
- **Purpose:** Auto-generate SKILL.md files from patterns
- **Features:**
  - Template-based generation
  - Step inference from code patterns
  - File path detection
  - Input/output schema generation

#### Agent Factory
- **Location:** `scripts/agent_factory.py`
- **Purpose:** Auto-create MAS agents and Cursor agents
- **Creates:**
  - Python agent files (`mycosoft_mas/agents/`)
  - Cursor agent definitions (`.cursor/agents/`)
  - Updates `__init__.py` and registries
  - Basic test templates

#### Learning Feedback Service
- **Location:** `mycosoft_mas/services/learning_feedback.py`
- **Purpose:** Track and learn from task outcomes
- **Features:**
  - Outcome recording (success/failure)
  - Performance analysis per agent
  - Approach pattern detection
  - Improvement suggestions

### Phase 3: Autonomous Operations

#### Autonomous Scheduler
- **Location:** `scripts/autonomous_scheduler.py`
- **Purpose:** Self-triggering task execution
- **Triggers:**
  - File system changes (via watchdog)
  - Time intervals (hourly, daily)
- **Tasks:**
  - Linting on Python file changes
  - Tests on test file changes
  - Docs build on markdown changes
  - Registry sync on agent/skill changes
  - Pattern scan (daily)
  - Skill generation (daily)

#### Deployment Feedback Service
- **Location:** `mycosoft_mas/services/deployment_feedback.py`
- **Purpose:** Monitor and learn from deployments
- **Features:**
  - Deployment tracking
  - Health endpoint monitoring
  - Success/failure analysis
  - Auto-rollback recommendations
  - Optimization suggestions

#### Continuous Improvement Loop
- **Location:** `scripts/continuous_improvement.py`
- **Purpose:** Daily self-improvement orchestration
- **Cycle:**
  1. Gap scan (TODOs, FIXMEs, stubs)
  2. Pattern scan (code patterns)
  3. Skill generation (from patterns)
  4. Registry sync
  5. Learning analysis
  6. Self-optimization
  7. Report generation

## Usage

### Starting the System

```bash
# Show system status
python scripts/start_autonomous_cursor.py --status

# Run improvement loop once
python scripts/start_autonomous_cursor.py --improvement

# Start scheduler daemon
python scripts/start_autonomous_cursor.py --scheduler

# Start everything
python scripts/start_autonomous_cursor.py --all
```

### Using MCP Tools in Cursor

The MCP servers are automatically available in Cursor. Use them via the tool calling interface:

```
# Create a task
Use tool: mycosoft-tasks.task_create
  title: "Implement authentication"
  priority: "high"
  agent: "backend-dev"

# Check system health
Use tool: mycosoft-orchestrator.system_health

# Register new skill
Use tool: mycosoft-registry.registry_add_skill
  skill_id: "my-new-skill"
  description: "Does something useful"
```

### Manual Script Usage

```bash
# Run pattern scanner
python scripts/pattern_scanner.py

# Generate skills from patterns
python scripts/skill_generator.py

# Create agent from spec
python scripts/agent_factory.py --name "NewAgent" --capabilities "data processing"
```

## Configuration

### .mcp.json

MCP servers are configured in `.mcp.json`:

```json
{
  "mcpServers": {
    "mycosoft-memory": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "mycosoft_mas.memory.mcp_memory_server"],
      "env": { "MINDEX_DATABASE_URL": "${MINDEX_DATABASE_URL}" }
    },
    "mycosoft-tasks": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "mycosoft_mas.mcp.task_management_server"],
      "env": { "CURSOR_PLANS_DIR": "C:/Users/admin2/.cursor/plans" }
    },
    "mycosoft-orchestrator": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "mycosoft_mas.mcp.orchestrator_server"],
      "env": {
        "MAS_API_URL": "http://192.168.0.188:8001",
        "MINDEX_API_URL": "http://192.168.0.189:8000",
        "N8N_URL": "http://192.168.0.188:5678"
      }
    },
    "mycosoft-registry": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "mycosoft_mas.mcp.registry_server"],
      "env": { "WORKSPACE_ROOT": "..." }
    }
  }
}
```

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `MINDEX_DATABASE_URL` | PostgreSQL connection for memory |
| `CURSOR_PLANS_DIR` | Directory for Cursor plans |
| `MAS_API_URL` | MAS orchestrator API URL |
| `MINDEX_API_URL` | MINDEX API URL |
| `N8N_URL` | n8n workflow URL |
| `WORKSPACE_ROOT` | Workspace root for registry operations |

## Data Files

All data is stored in `data/`:

| File | Purpose |
|------|---------|
| `learning_feedback.json` | Task outcome history |
| `deployment_feedback.json` | Deployment history |
| `autonomous_cursor.log` | System logs |
| `improvement_report.json` | Latest improvement report |
| `gap_report.json` | Latest gap scan results |
| `pattern_report.json` | Latest pattern scan results |

## Integration with myca-autonomous-operator

The `myca-autonomous-operator` agent (`.cursor/agents/myca-autonomous-operator.md`) is updated to use all these systems:

1. **MCP Tools** - Direct access to all MCP servers
2. **Auto-Learning Scripts** - Can run pattern scanner, skill generator, agent factory
3. **Services** - Can use learning and deployment services
4. **Self-Improvement Workflow** - Follows the continuous improvement process

## Safety Considerations

1. **Protected Files** - Agent factory won't modify protected files (orchestrator, security)
2. **Validation** - All generated code is validated before writing
3. **Backup** - Registries are backed up before modification
4. **Rollback** - Deployment service can recommend rollbacks
5. **Learning Limits** - Self-optimization has bounds on threshold changes

## Future Enhancements

1. **Phase 6: Self-Evolving Agents** - Agents that modify their own capabilities
2. **Phase 7: Cross-Repo Learning** - Learning patterns from external repos
3. **Phase 8: Natural Language Skills** - Generate skills from natural language descriptions
4. **Phase 9: Proactive Bug Detection** - Predict and prevent bugs before they occur

## Related Documentation

- `docs/MYCA_CODING_SYSTEM_FEB09_2026.md` - MYCA coding system overview
- `docs/SYSTEM_REGISTRY_FEB04_2026.md` - System registry
- `docs/API_CATALOG_FEB04_2026.md` - API catalog
- `docs/MASTER_DOCUMENT_INDEX.md` - Document index
