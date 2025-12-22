// ============== DEVICE & NETWORK TYPES ==============

export interface Device {
  name: string;
  type: string;
  ip: string;
  mac: string;
  vendor: string;
  uptime: string;
  experience: string;
}

export interface NetworkStats {
  download: number;
  upload: number;
  latency: number;
  clients?: number;
  timestamp?: number;
}

export interface TrafficData {
  total: number;
  services: Array<{
    name: string;
    value: number;
  }>;
}

// ============== AGENT TYPES ==============

export type AgentStatus = "online" | "offline" | "idle" | "error" | "active";
export type AgentCategory = "core" | "financial" | "mycology" | "research" | "communication" | "dao" | "integration";
export type NodeType = "orchestrator" | "agent" | "person" | "database" | "service" | "external" | "user" | "internet" | "cache" | "program";
export type ConnectionType = "data" | "control" | "command" | "ui" | "interaction" | "transaction" | "message";
export type RiskLevel = "Low" | "Medium" | "High";
export type FlowDirection = "in" | "out" | "both";

export interface Agent {
  id: string;
  name: string;
  type: string;
  category: AgentCategory;
  status: AgentStatus;
  experience: string;
  ip: string;
  mac: string;
  vendor: string;
  uptime: string;
  downloadSpeed: number;
  uploadSpeed: number;
  tasksCompleted: number;
  tasksInProgress: number;
  connections: string[];
  lastActivity?: string;
  capabilities?: string[];
  currentTask?: string;
}

// ============== TOPOLOGY TYPES ==============

export interface TopologyNode {
  id: string;
  type: NodeType;
  name: string;
  x: number; // percentage position
  y: number; // percentage position
  status: AgentStatus | "online" | "offline";
  category?: AgentCategory;
  icon?: string;
  description?: string;
  metadata?: Record<string, unknown>;
}

export interface TopologyConnection {
  source: string;
  target: string;
  type: ConnectionType;
  active: boolean;
  bandwidth?: number;
  latency?: number;
  label?: string;
  bidirectional?: boolean;
}

export interface TopologyData {
  nodes: TopologyNode[];
  connections: TopologyConnection[];
}

// ============== FLOW TYPES ==============

export interface Flow {
  id: string;
  source: string;
  destination: string;
  service: string;
  risk: RiskLevel;
  direction: FlowDirection;
  inBytes: string;
  outBytes: string;
  action: "Allow" | "Block";
  timestamp: string;
  protocol?: string;
  port?: number;
}

// ============== INTERACTION TYPES ==============

export type InteractionType = 
  | "agent-to-agent"
  | "agent-to-person"
  | "agent-to-program"
  | "person-to-database"
  | "user-to-orchestrator"
  | "orchestrator-to-agent";

export interface Interaction {
  id: string;
  type: InteractionType;
  source: string;
  target: string;
  timestamp: string;
  data?: unknown;
  status: "pending" | "active" | "completed" | "failed";
  duration?: number;
}

// ============== TASK TYPES ==============

export interface Task {
  id: string;
  title: string;
  description?: string;
  assignedTo: string;
  status: "pending" | "in_progress" | "completed" | "failed";
  priority: "low" | "medium" | "high" | "critical";
  createdAt: string;
  updatedAt?: string;
  completedAt?: string;
  result?: unknown;
}

// ============== METRICS TYPES ==============

export interface SystemMetrics {
  cpuUsage: number;
  memoryUsage: number;
  diskUsage: number;
  networkIO: {
    bytesIn: number;
    bytesOut: number;
  };
  activeAgents: number;
  totalAgents: number;
  tasksPerHour: number;
  uptime: number;
}

export interface AgentMetrics {
  agentId: string;
  tasksCompleted: number;
  tasksInProgress: number;
  averageResponseTime: number;
  errorRate: number;
  lastHealthCheck: string;
  resourceUsage: {
    cpu: number;
    memory: number;
  };
}

// ============== NOTIFICATION TYPES ==============

export interface Notification {
  id: string;
  type: "info" | "warning" | "error" | "success";
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  source?: string;
  actionUrl?: string;
}

// ============== DASHBOARD TYPES ==============

export interface DashboardWidget {
  id: string;
  type: string;
  title: string;
  position: { x: number; y: number; w: number; h: number };
  config?: Record<string, unknown>;
}

export interface DashboardLayout {
  id: string;
  name: string;
  widgets: DashboardWidget[];
  isDefault?: boolean;
}

// ============== VIEW PROPS ==============

export interface ViewProps {
  onDeviceClick?: (device: Device) => void;
  onAgentClick?: (agent: Agent) => void;
  onNodeClick?: (node: TopologyNode) => void;
}
