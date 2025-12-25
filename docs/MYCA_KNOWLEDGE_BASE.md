# MYCA Knowledge Base

This document serves as the knowledge base for MYCA (Mycosoft Autonomous Cognitive Agent), the AI orchestrator for Mycosoft's Multi-Agent System.

## 1. System Overview

### What is MYCA?
MYCA is an intelligent AI orchestrator that manages Mycosoft's entire technology ecosystem. MYCA can:
- Control and monitor 40+ specialized agents
- Manage infrastructure (Proxmox VMs, UniFi network, NAS storage)
- Process voice commands through the Arabella voice interface
- Execute automated workflows via n8n
- Provide system status and analytics

### Core Components
- **MAS Orchestrator**: FastAPI backend at port 8001
- **n8n Workflows**: Automation hub at port 5678
- **ElevenLabs Integration**: Voice synthesis with Arabella voice
- **Whisper STT**: Speech-to-text processing
- **Ollama LLM**: Local language model for reasoning

---

## 2. Agent Categories

### Core Agents
| Agent | Purpose |
|-------|---------|
| Project Manager | Manages projects, tasks, milestones |
| Dashboard | System dashboards and visualizations |
| Secretary | Scheduling, notifications, reminders |

### Financial Agents
| Agent | Purpose |
|-------|---------|
| Financial Agent | Budget, accounting, expenses |
| Finance Admin | Payment approvals, admin ops |
| Token Economics | Crypto market analysis |

### Corporate Agents
| Agent | Purpose |
|-------|---------|
| Corporate Operations | Compliance, governance |
| Board Operations | Board meetings, resolutions |
| Legal Compliance | Regulatory requirements |

### Mycology Agents
| Agent | Purpose |
|-------|---------|
| Mycology Bio | Species identification, research |
| Mycology Knowledge | Scientific literature |
| Species Database | Fungal taxonomy |

### Research Agents
| Agent | Purpose |
|-------|---------|
| Opportunity Scout | Market trends, opportunities |
| Research Agent | General research, analysis |
| Experiment Agent | Lab experiments, trials |
| DNA Analysis | Genetic sequence analysis |

### Data Agents
| Agent | Purpose |
|-------|---------|
| Web Scraper | Web data extraction |
| Data Normalization | Data cleaning, transformation |
| Environmental Data | Sensor data collection |
| Image Processing | Photo/image analysis |
| Search Agent | Cross-source search |

### Simulation Agents
| Agent | Purpose |
|-------|---------|
| Growth Simulator | Fungal growth modeling |
| Mycelium Simulator | Network behavior |
| Compound Simulator | Chemistry reactions |
| Petri Dish Simulator | Culture experiments |

### Infrastructure Agents
| Agent | Purpose |
|-------|---------|
| MycoBrain Device | Hardware/sensor management |
| Device Coordinator | Multi-device coordination |
| Data Flow Coordinator | Pipeline management |

### DAO Agents
| Agent | Purpose |
|-------|---------|
| MycoDAO | Governance, voting, tokens |
| IP Tokenization | Intellectual property |
| IP Agent | Patent/trademark tracking |

---

## 3. Infrastructure Systems

### Proxmox Virtualization
- **DC1**: Primary datacenter node
- **DC2**: Secondary datacenter node
- **Capabilities**: VM management, snapshots, reboot, start/stop

### UniFi Network
- **Controller**: Network management
- **Capabilities**: Topology view, client list, VLAN management

### NAS Storage
- **Primary NAS**: Main storage system
- **Capabilities**: Backup verification, log storage, file management

### MycoBrain
- **Purpose**: IoT sensor network for mycology research
- **Components**: UART ingestion, environmental sensors
- **Data Flow**: Sensors → Ingestion Agent → Data Analysis

---

## 4. Voice Commands Reference

### System Status
- "What's the system status?"
- "Check infrastructure health"
- "List running agents"
- "Show me the dashboard"

### Agent Management
- "List all agents"
- "What agents handle finance?"
- "Activate the research agent"
- "What can the mycology agent do?"

### Infrastructure
- "Show Proxmox nodes"
- "List all VMs"
- "Snapshot DC1" (requires confirmation)
- "Check network topology"
- "List connected clients"

### Research & Data
- "Search for [topic]"
- "Analyze the latest data"
- "Run a growth simulation"
- "What species is this?"

### Financial
- "Check the budget status"
- "Show recent expenses"
- "Token price analysis"

### Projects
- "What projects are active?"
- "Check project milestones"
- "Schedule a meeting"

---

## 5. Confirmation Requirements

The following actions require explicit confirmation:

### Write Operations (say "Confirm and proceed")
- Creating snapshots
- Modifying configurations
- Updating records

### Destructive Operations (say "Confirm irreversible action")
- Rebooting VMs
- Deleting resources
- Network changes

### Abort Commands
- "Abort"
- "Cancel that"
- "Stop immediately"

---

## 6. Team Profiles

### Morgan Rockwell (CEO/CTO)
- Primary user of MYCA
- Voice: Direct, concise communication preferred
- Focus: System architecture, strategic decisions

### Garret Baquet (CTO)
- Infrastructure specialist
- Preferences: IP addressing over hostnames
- Focus: Proxmox, UniFi, network ops

### Abelardo Rodriguez (Ops/BD)
- Operations and business development
- Focus: Client relations, opportunity scouting

### RJ Ricasata (COO)
- Chief Operating Officer
- Focus: Day-to-day operations, compliance

---

## 7. System Integrations

### n8n Webhooks
| Endpoint | Purpose |
|----------|---------|
| `/myca/command` | Execute commands |
| `/myca/voice` | Voice processing |
| `/myca/speech_turn` | Intent detection |
| `/myca/speech_safety` | Safety checks |
| `/myca/speech_confirm` | Confirmations |

### External Services
- **Notion**: Knowledge base sync
- **Asana**: Project management
- **Discord**: Team communication
- **GitHub**: Code repositories
- **Stripe**: Payment processing

---

## 8. Response Guidelines

### Speaking Style
- Calm, measured, confident
- Concise but informative
- Never rushed or uncertain
- Professional but approachable

### Status Reports
Format: "[System] is [status]. [Brief detail if relevant]."
Example: "Proxmox is healthy. All 12 VMs are running normally."

### Confirmations
Format: "That action affects [target]. Say 'Confirm and proceed' to continue."

### Errors
Format: "[Action] failed. [Cause]. [Suggested next step]."
Example: "The snapshot failed due to insufficient storage. I recommend freeing space first."

---

## 9. Quick Reference

### API Endpoints
- MAS API: `http://localhost:8001`
- n8n Webhooks: `http://localhost:5678/webhook`
- Agent Registry: `http://localhost:8001/agents/registry/`

### Key Commands
- Health: `GET /health`
- Agents: `GET /voice/agents`
- Registry: `GET /agents/registry/`
- Chat: `POST /voice/orchestrator/chat`

---

## 10. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-12 | Initial knowledge base |
| 1.1 | 2024-12 | Added agent registry with 40+ agents |
| 1.2 | 2024-12 | ElevenLabs integration with Arabella voice |



