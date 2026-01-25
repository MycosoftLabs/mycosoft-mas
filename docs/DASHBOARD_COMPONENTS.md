# MAS v2 Dashboard Components

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
