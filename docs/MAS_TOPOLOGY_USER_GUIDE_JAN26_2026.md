# MAS Topology Command Center - User Guide
## Date: January 26, 2026

---

## Overview

The MAS Topology Command Center is Morgan's primary interface for controlling MYCA and the 247+ AI agents that operate Mycosoft. This guide covers every feature, button, and interaction available in the dashboard.

---

## Accessing the Dashboard

- **URL**: `http://localhost:3010/natureos/mas/topology` (dev) or `https://sandbox.mycosoft.com/natureos/mas/topology` (production)
- **Version**: v2.2
- **Recommended**: Use Chrome/Edge for best WebGL performance

---

## Interface Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  [Back]                                    [Fullscreen]         │
├────────────┬────────────────────────────────────┬───────────────┤
│            │                                    │               │
│  LEFT      │        3D TOPOLOGY VIEW           │    RIGHT      │
│  PANEL     │        (247 Agent Nodes)          │    PANEL      │
│            │                                    │               │
├────────────┴────────────────────────────────────┴───────────────┤
│  [Connect] [Path] [Spawn] [Timeline] [Command] [Legend] [Health]│
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Ask MYCA...                                              │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Top Bar

### Stats Display
- **237/247**: Active agents / Total agents
- **8126/s**: Messages per second throughput
- **23ms**: Average latency
- **96%**: Overall system health score

### Buttons
- **Back to NatureOS**: Return to NatureOS dashboard
- **Enter Fullscreen**: Toggle fullscreen mode for focused work

---

## Left Panel - Filtering & Display

### Search
- Type in the "Filter nodes..." field to search for specific agents by name

### Categories
Click category buttons to filter the 3D view:
- **core** (11 agents): Memory, Task Router, Scheduler, Logger
- **financial** (12 agents): Accounting, Budgeting, Tax, Investment
- **mycology** (25 agents): Species DB, Growth Analytics, Spore Tracker
- **research** (15 agents): Literature Scanner, Patent Analyzer
- **dao** (40 agents): Governance, Voting, Proposals
- **communication** (10 agents): Email, Slack, Notifications
- **data** (30 agents): ETL, Analytics, Search, Archive
- **infrastructure** (18 agents): Proxmox, Docker, Network
- **simulation** (12 agents): Earth Sim, Digital Twin
- **security** (8 agents): Threat Hunter, Incident Response
- **integration** (20 agents): OpenAI, GitHub, Notion, Zapier
- **device** (18 agents): MycoBrain, Sensors, LoRa
- **chemistry** (8 agents): Compound Analysis, Reactions
- **nlm** (20 agents): Smell Classifier, Model Training

### Security Status
- Shows "No active incidents" or lists current security alerts
- Click to view detailed incident information

### Display Toggles
- **Labels**: Show/hide agent name labels
- **Connections**: Show/hide connection lines
- **Inactive**: Show/hide offline agents

---

## Right Panel - System Health

### Metrics
- **CPU**: Current CPU utilization percentage
- **Memory**: Current memory usage percentage
- **Health**: Overall system health score

### Status Indicators
- **System**: Green = healthy, Yellow = warning, Red = critical
- **Agents**: Agent pool status
- **Network**: Network connectivity status
- **Load**: System load status

### Category Breakdown
Shows active/total agents per category (e.g., "core 11/11", "financial 10/12")

---

## Bottom Control Bar

### Tool Buttons

#### Connect
- Click to enter connection mode
- Click any node to start a connection
- Click a second node to complete the connection
- Creates a new data flow between agents

#### Path
Opens the **Path Tracer** panel:
- Select source and target nodes
- Click "Trace Path" to visualize the communication route
- Shows hop count and latency between agents

#### Spawn
Opens the **Spawn Agent** panel:
- **Suggested** tab: Shows detected capability gaps with spawn recommendations
- **Custom** tab: Manually configure a new agent
- View orchestrator output for spawn operations

#### Timeline
Opens historical playback (planned feature):
- Scrub through past system states
- Analyze historical performance

#### Command
Opens **MYCA Command Center**:
- **Health Check**: Run system health diagnostics
- **Restart All**: Restart all agents (use with caution)
- **Sync Memory**: Force memory synchronization across agents
- **Clear Queue**: Clear pending task queue
- Includes Command Terminal for direct commands
- System Activity Stream shows real-time logs

#### Legend
Displays the **Connection Legend**:
- Connection types (data, command, event)
- Packet types with color coding
- Line styles and their meanings

#### Health
Opens **Connection Health** panel:
- Shows connectivity score percentage
- Lists connected, partial, and disconnected agents
- Identifies critical issues (missing orchestrator paths)
- **Auto-Fix Connections** button to repair gaps automatically

---

## Ask MYCA Natural Language Query

Type natural language questions in the bottom input field:

### Example Queries
- "Show all offline agents"
- "Agents with high CPU"
- "Financial agents"
- "Show path from MYCA to MINDEX"
- "Spawn security agent"
- "Core agents"
- "Agents connected to database"

### Query Results
- Matching agents are highlighted in the 3D view
- Results count is displayed
- Click a result to focus on that node

---

## 3D Visualization Interaction

### Navigation
- **Left-click drag**: Rotate the view
- **Right-click drag**: Pan the view
- **Scroll wheel**: Zoom in/out
- **Double-click node**: Focus on that agent

### Node Selection
Click any node to see:
- Agent name and description
- Current status (active/busy/idle/offline/error)
- Key metrics (tasks, uptime, connections)
- Action buttons (Start/Stop/Restart/Query/Backup)

### Node Colors
- **Green**: Active and healthy
- **Blue**: Busy processing
- **Yellow**: Idle/standby
- **Gray**: Offline/planned
- **Red**: Error state

---

## Common Workflows

### 1. Check System Health
1. View the stats bar (237/247, 96%)
2. Open the Health panel
3. Review disconnected agents
4. Click "Auto-Fix" if issues found

### 2. Trace Data Flow
1. Click "Path" button
2. Select source agent (e.g., "MYCA")
3. Select target agent (e.g., "PostgreSQL")
4. Click "Trace Path"
5. Review the path visualization

### 3. Deploy New Agent
1. Click "Spawn" button
2. Review suggested gaps
3. Click "Spawn" next to a recommended agent
4. Or switch to "Custom" tab for manual config
5. Monitor orchestrator output

### 4. Issue Commands
1. Click "Command" button
2. Use quick actions (Health Check, etc.)
3. Or type custom command in terminal
4. View results in activity stream

---

## Troubleshooting

### "POLL" Mode
- Indicates WebSocket is unavailable
- System falls back to polling for updates
- Data may be slightly delayed

### Agent Shows Offline
1. Check if MAS orchestrator is running
2. Review the agent's container status
3. Use Command Center to restart

### No Connection Data
1. Verify Supabase connectivity
2. Check MAS API at 192.168.0.188:8001
3. Review browser console for errors

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Escape | Close active modal |
| F | Toggle fullscreen |
| R | Refresh data |

---

*Guide prepared for Morgan Rockwell, CEO/SuperAdmin*
*Version: 1.0*
*Last Updated: January 26, 2026*
