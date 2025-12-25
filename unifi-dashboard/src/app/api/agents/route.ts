import { NextResponse } from "next/server";

// Mock agent data - in production, this would fetch from the Python MAS backend
const agents = [
  {
    id: "myca-orchestrator",
    name: "MYCA Orchestrator",
    type: "orchestrator",
    category: "core",
    status: "online",
    experience: "Excellent",
    ip: "10.0.0.1",
    mac: "00:00:00:00:00:01",
    vendor: "Mycosoft",
    uptime: "2w 4d 4h 0m",
    downloadSpeed: 159,
    uploadSpeed: 136,
    tasksCompleted: 1247,
    tasksInProgress: 3,
    connections: ["financial-agent", "mycology-agent", "project-manager", "dashboard-agent"],
  },
  {
    id: "financial-agent",
    name: "Financial Agent",
    type: "agent",
    category: "financial",
    status: "online",
    experience: "Excellent",
    ip: "10.0.0.172",
    mac: "00:00:00:00:00:02",
    vendor: "Mycosoft",
    uptime: "8d 20m 11s",
    downloadSpeed: 49.4,
    uploadSpeed: 5.36,
    tasksCompleted: 89,
    tasksInProgress: 1,
    connections: ["myca-orchestrator", "database"],
  },
  {
    id: "mycology-agent",
    name: "Mycology Research",
    type: "agent",
    category: "mycology",
    status: "online",
    experience: "Excellent",
    ip: "10.0.0.248",
    mac: "00:00:00:00:00:03",
    vendor: "Mycosoft",
    uptime: "8d 20m 11s",
    downloadSpeed: 36.1,
    uploadSpeed: 49.4,
    tasksCompleted: 234,
    tasksInProgress: 2,
    connections: ["myca-orchestrator", "knowledge-graph"],
  },
  {
    id: "project-manager",
    name: "Project Manager",
    type: "agent",
    category: "core",
    status: "online",
    experience: "Excellent",
    ip: "10.0.0.90",
    mac: "00:00:00:00:00:04",
    vendor: "Mycosoft",
    uptime: "17d 47m 31s",
    downloadSpeed: 0,
    uploadSpeed: 0,
    tasksCompleted: 412,
    tasksInProgress: 5,
    connections: ["myca-orchestrator", "n8n-workflow"],
  },
  {
    id: "opportunity-scout",
    name: "Opportunity Scout",
    type: "agent",
    category: "research",
    status: "online",
    experience: "Good",
    ip: "10.0.0.91",
    mac: "00:00:00:00:00:05",
    vendor: "Mycosoft",
    uptime: "6d 1h 33m 28s",
    downloadSpeed: 25,
    uploadSpeed: 12,
    tasksCompleted: 78,
    tasksInProgress: 1,
    connections: ["myca-orchestrator", "external-api"],
  },
  {
    id: "marketing-agent",
    name: "Marketing Agent",
    type: "agent",
    category: "communication",
    status: "idle",
    experience: "Good",
    ip: "10.0.0.228",
    mac: "00:00:00:00:00:06",
    vendor: "Mycosoft",
    uptime: "1d 3h 37m 6s",
    downloadSpeed: 0,
    uploadSpeed: 0,
    tasksCompleted: 56,
    tasksInProgress: 0,
    connections: ["myca-orchestrator"],
  },
  {
    id: "myco-dao-agent",
    name: "MycoDAO Agent",
    type: "agent",
    category: "dao",
    status: "online",
    experience: "Excellent",
    ip: "10.0.0.105",
    mac: "00:00:00:00:00:07",
    vendor: "Mycosoft",
    uptime: "18d 3h 59m 58s",
    downloadSpeed: 32,
    uploadSpeed: 48,
    tasksCompleted: 23,
    tasksInProgress: 0,
    connections: ["myca-orchestrator", "blockchain"],
  },
  {
    id: "dashboard-agent",
    name: "Dashboard Agent",
    type: "agent",
    category: "core",
    status: "online",
    experience: "Excellent",
    ip: "10.0.0.184",
    mac: "00:00:00:00:00:08",
    vendor: "Mycosoft",
    uptime: "17d 45m 51s",
    downloadSpeed: 0,
    uploadSpeed: 24,
    tasksCompleted: 890,
    tasksInProgress: 1,
    connections: ["myca-orchestrator", "user-interface"],
  },
];

export async function GET() {
  // In production, fetch from Python backend:
  // const response = await fetch('http://localhost:8000/api/agents');
  // const data = await response.json();
  // return NextResponse.json(data);
  
  return NextResponse.json(agents);
}

export async function POST(request: Request) {
  const body = await request.json();
  
  // In production, forward to Python backend:
  // const response = await fetch('http://localhost:8000/api/agents', {
  //   method: 'POST',
  //   headers: { 'Content-Type': 'application/json' },
  //   body: JSON.stringify(body),
  // });
  // const data = await response.json();
  // return NextResponse.json(data);
  
  return NextResponse.json({ success: true, message: "Agent command received", data: body });
}
