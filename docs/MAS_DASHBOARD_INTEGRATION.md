# MAS Dashboard Integration

## Overview

The MAS Dashboard has been integrated into the MYCA system, providing a UniFi-style network topology visualization for the Multi-Agent System. The dashboard displays agents, orchestrators, operators, databases, programs, and users, showing their connections and interactions.

## Features

### Topology View
- **Interactive Network Map**: Visual representation of all MAS entities
- **Entity Types**:
  - **Orchestrator**: Central coordination hub (blue)
  - **Agents**: Specialized worker agents (purple)
  - **Operators**: System operators (green)
  - **Databases**: Data storage systems (cyan)
  - **Programs**: External programs/services (orange)
  - **Users**: System users (yellow)

### Connection Types
- Agent to Orchestrator
- Agent to Agent
- Agent to Operator
- Agent to Program
- Agent to Database
- User to Orchestrator
- Operator to Database

### Interactive Features
- **Drag and Drop**: Reposition entities on the canvas
- **Zoom Controls**: Zoom in/out and reset view
- **Entity Details**: Click on entities to view detailed information
- **Real-time Updates**: Auto-refreshes every 5 seconds
- **Connection Visualization**: Animated connection lines showing relationships

## File Structure

```
components/
├── mas-dashboard.tsx          # Main dashboard component
├── mas-topology-view.tsx       # Topology visualization component
├── mas-sidebar.tsx             # Left sidebar with system info
├── mas-navigation.tsx          # Navigation bar component
├── mas-search-bar.tsx          # Search functionality
└── mas-entity-modal.tsx        # Entity details modal

app/
├── api/
│   └── mas/
│       └── topology/
│           └── route.ts        # API endpoint for topology data
└── myca/
    └── dashboard/
        └── page.tsx            # Dashboard page route
```

## API Integration

### Topology Endpoint
**GET** `/api/mas/topology`

Returns:
```json
{
  "entities": [
    {
      "id": "orchestrator-1",
      "name": "MYCA Orchestrator",
      "type": "orchestrator",
      "status": "active",
      "x": 400,
      "y": 100,
      "connections": ["agent-1", "agent-2"],
      "metadata": {
        "ip": "192.168.0.1",
        "uptime": "2w 4d 4h",
        "tasksCompleted": 1247,
        "tasksInProgress": 3,
        "downloadSpeed": 159,
        "uploadSpeed": 136,
        "experience": "Excellent"
      }
    }
  ],
  "connections": [
    {
      "from": "orchestrator-1",
      "to": "agent-1",
      "type": "agent-to-orchestrator",
      "status": "active"
    }
  ]
}
```

## Accessing the Dashboard

The dashboard is accessible at:
- **Route**: `/myca/dashboard`
- **Component**: `MASDashboard`

## Integration with MAS Backend

Currently, the dashboard uses mock data. To integrate with the actual MAS backend:

1. **Update API Route** (`app/api/mas/topology/route.ts`):
   ```typescript
   const response = await fetch('http://localhost:8000/api/agents');
   const agents = await response.json();
   
   // Transform MAS agent data to topology entities
   const entities = transformAgentsToEntities(agents);
   ```

2. **Connect to MAS API Endpoints**:
   - `/api/agents` - Get all agents
   - `/api/orchestrator/status` - Get orchestrator status
   - `/api/topology` - Get connection topology (if available)

## Customization

### Adding New Entity Types
1. Update `MASEntity` type in `mas-topology-view.tsx`
2. Add icon rendering in `getEntityIcon()` function
3. Add color scheme in `getEntityColor()` function
4. Update legend component

### Styling
The dashboard uses Tailwind CSS with a dark theme matching UniFi's design:
- Background: `#0F172A` (slate-900)
- Cards: `#1E293B` (slate-800)
- Borders: `gray-800`
- Accent: `blue-500`

## Future Enhancements

- [ ] Real-time WebSocket updates
- [ ] Filter entities by type/status
- [ ] Search functionality
- [ ] Export topology as image
- [ ] Historical topology snapshots
- [ ] Performance metrics overlay
- [ ] Alert/notification system
- [ ] Entity grouping/clustering

## Dependencies

- `next`: 16.0.10
- `react`: 19.2.3
- `lucide-react`: ^0.561.0 (for icons)
- `tailwindcss`: ^3.4.19 (for styling)

## Notes

- The topology view uses SVG for connection lines
- Entities are positioned using absolute positioning
- Auto-layout is applied only when entities don't have explicit positions
- The dashboard is fully responsive and works on different screen sizes
