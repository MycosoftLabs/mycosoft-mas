# MYCA Dashboard - UniFi-Style Multi-Agent System Visualization

A beautiful, real-time dashboard for visualizing and managing the MYCA Multi-Agent System, inspired by Ubiquiti's UniFi Network application.

![MYCA Dashboard](./screenshot.png)

## Features

### 🗺️ Agent Topology Map
- Real-time visualization of agent connections and interactions
- Drag-and-drop node positioning
- Visual representation of:
  - Agent-to-Agent communication
  - Agent-to-Person interactions
  - Agent-to-Program/Service connections
  - User-to-Orchestrator commands
  - Person-to-Database queries
- Animated data flow indicators
- Connection status and bandwidth visualization

### 📊 Dashboard Overview
- System health status at a glance
- Active agent count and status
- Task throughput metrics
- Network latency monitoring
- Category-based agent grouping

### 🔄 Agent Flows
- Real-time communication flow tracking
- Service/protocol identification
- Risk level assessment
- Traffic direction indicators
- Action logging (Allow/Block)

### 🎛️ Agent Management
- Detailed agent information panel
- Task status monitoring
- Performance metrics (download/upload speeds)
- Experience ratings
- Command interface

## Architecture

```
unifi-dashboard/
├── src/
│   ├── app/
│   │   ├── api/              # API routes for agent data
│   │   │   ├── agents/
│   │   │   ├── flows/
│   │   │   └── topology/
│   │   ├── layout.tsx        # Root layout with theme provider
│   │   └── page.tsx          # Main dashboard entry
│   ├── components/
│   │   ├── views/
│   │   │   ├── AgentTopologyView.tsx   # Main topology visualization
│   │   │   ├── ClientsView.tsx
│   │   │   ├── FlowsView.tsx
│   │   │   └── ...
│   │   ├── Dashboard.tsx     # Main dashboard component
│   │   ├── Navigation.tsx    # Side navigation
│   │   └── Sidebar.tsx       # System info sidebar
│   ├── lib/
│   │   ├── data-service.ts   # Real-time data service
│   │   ├── theme-provider.tsx
│   │   └── utils.ts
│   └── types/
│       └── index.ts          # TypeScript interfaces
├── package.json
└── tailwind.config.ts
```

## Quick Start

### Prerequisites
- Node.js 18+ or Bun
- The main MAS system running (optional, for real data)

### Installation

```bash
cd unifi-dashboard
bun install  # or npm install
```

### Development

```bash
bun dev  # or npm run dev
```

The dashboard will be available at `http://localhost:3000`

### Production Build

```bash
bun run build
bun run start
```

## Integration with MAS Backend

The dashboard is designed to work with the MYCA Multi-Agent System backend. By default, it uses mock data for demonstration. To connect to the real backend:

1. Set the API URL environment variable:
   ```bash
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

2. Ensure the MAS backend exposes the following endpoints:
   - `GET /api/agents` - List all agents
   - `GET /api/topology` - Get topology nodes and connections
   - `GET /api/flows` - Get communication flows
   - `POST /api/agents/:id/command` - Send commands to agents

## Node Types

| Type | Description | Icon |
|------|-------------|------|
| `orchestrator` | MYCA central orchestrator | Brain |
| `agent` | Individual AI agents | CPU |
| `person` | Human operators | User |
| `database` | Data stores (PostgreSQL, etc.) | Database |
| `service` | External services (n8n, etc.) | Server |
| `external` | External APIs and services | External Link |
| `internet` | Internet connection | Globe |
| `cache` | Cache systems (Redis) | Cache |
| `user` | User interface | Monitor |

## Connection Types

| Type | Color | Description |
|------|-------|-------------|
| `data` | Blue | Data transfer |
| `control` | Purple | Control signals |
| `command` | Green | User commands |
| `interaction` | Yellow | Human interactions |
| `transaction` | Pink | Blockchain transactions |
| `message` | Teal | Inter-agent messages |
| `ui` | Cyan | UI updates |

## Keyboard Shortcuts

- `+` / `-` - Zoom in/out
- `R` - Reset view
- `L` - Toggle labels
- `T` - Toggle traffic animation

## Customization

### Adding New Agent Types

1. Update `src/types/index.ts` with new type definitions
2. Add corresponding icons in `AgentTopologyView.tsx`
3. Update the legend component

### Theming

The dashboard supports dark and light themes. Customize colors in:
- `tailwind.config.ts` - Tailwind color palette
- `src/app/globals.css` - CSS variables

## Tech Stack

- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: Radix UI primitives
- **Charts**: Recharts
- **Animations**: CSS animations + SVG
- **State**: React hooks + custom data service

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details.

---

Part of the [MYCA Multi-Agent System](https://github.com/mycosoft/mycosoft-mas)
