import { NextResponse } from "next/server";

// Mock topology data - in production, this would fetch from the Python MAS backend
const topology = {
  nodes: [
    { id: "internet", type: "internet", name: "Wyyerd Fiber", x: 50, y: 5, status: "online" },
    { id: "myca-orchestrator", type: "orchestrator", name: "MYCA Orchestrator", x: 50, y: 25, status: "online" },
    { id: "database", type: "database", name: "PostgreSQL", x: 20, y: 50, status: "online" },
    { id: "redis", type: "cache", name: "Redis Cache", x: 35, y: 50, status: "online" },
    { id: "n8n-workflow", type: "service", name: "n8n Workflows", x: 50, y: 50, status: "online" },
    { id: "knowledge-graph", type: "database", name: "Knowledge Graph", x: 65, y: 50, status: "online" },
    { id: "external-api", type: "external", name: "External APIs", x: 80, y: 50, status: "online" },
    { id: "user-interface", type: "user", name: "User Interface", x: 10, y: 75, status: "online" },
    { id: "human-operator", type: "person", name: "Human Operator", x: 25, y: 75, status: "online" },
    { id: "blockchain", type: "external", name: "Blockchain", x: 90, y: 50, status: "online" },
    // Agent nodes
    { id: "financial-agent", type: "agent", name: "Financial Agent", x: 15, y: 65, status: "online", category: "financial" },
    { id: "mycology-agent", type: "agent", name: "Mycology Research", x: 30, y: 70, status: "online", category: "mycology" },
    { id: "project-manager", type: "agent", name: "Project Manager", x: 45, y: 72, status: "online", category: "core" },
    { id: "opportunity-scout", type: "agent", name: "Opportunity Scout", x: 55, y: 72, status: "online", category: "research" },
    { id: "marketing-agent", type: "agent", name: "Marketing Agent", x: 70, y: 70, status: "idle", category: "communication" },
    { id: "myco-dao-agent", type: "agent", name: "MycoDAO Agent", x: 85, y: 65, status: "online", category: "dao" },
    { id: "dashboard-agent", type: "agent", name: "Dashboard Agent", x: 40, y: 80, status: "online", category: "core" },
  ],
  connections: [
    // Internet to Orchestrator
    { source: "internet", target: "myca-orchestrator", type: "data", active: true, bandwidth: 1000 },
    
    // Orchestrator to Infrastructure
    { source: "myca-orchestrator", target: "database", type: "data", active: true, bandwidth: 500 },
    { source: "myca-orchestrator", target: "redis", type: "data", active: true, bandwidth: 200 },
    { source: "myca-orchestrator", target: "n8n-workflow", type: "control", active: true, bandwidth: 100 },
    { source: "myca-orchestrator", target: "knowledge-graph", type: "data", active: true, bandwidth: 150 },
    { source: "myca-orchestrator", target: "external-api", type: "data", active: true, bandwidth: 300 },
    
    // Orchestrator to Agents
    { source: "myca-orchestrator", target: "financial-agent", type: "control", active: true, bandwidth: 55 },
    { source: "myca-orchestrator", target: "mycology-agent", type: "control", active: true, bandwidth: 85 },
    { source: "myca-orchestrator", target: "project-manager", type: "control", active: true, bandwidth: 0 },
    { source: "myca-orchestrator", target: "opportunity-scout", type: "control", active: true, bandwidth: 37 },
    { source: "myca-orchestrator", target: "marketing-agent", type: "control", active: false, bandwidth: 0 },
    { source: "myca-orchestrator", target: "myco-dao-agent", type: "control", active: true, bandwidth: 80 },
    { source: "myca-orchestrator", target: "dashboard-agent", type: "control", active: true, bandwidth: 24 },
    
    // Agent to Infrastructure connections
    { source: "financial-agent", target: "database", type: "data", active: true, bandwidth: 50 },
    { source: "mycology-agent", target: "knowledge-graph", type: "data", active: true, bandwidth: 40 },
    { source: "project-manager", target: "n8n-workflow", type: "control", active: true, bandwidth: 30 },
    { source: "opportunity-scout", target: "external-api", type: "data", active: true, bandwidth: 25 },
    { source: "myco-dao-agent", target: "blockchain", type: "transaction", active: true, bandwidth: 20 },
    
    // User interactions
    { source: "dashboard-agent", target: "user-interface", type: "ui", active: true, bandwidth: 50 },
    { source: "user-interface", target: "human-operator", type: "interaction", active: true, bandwidth: 10 },
    { source: "human-operator", target: "myca-orchestrator", type: "command", active: true, bandwidth: 5 },
    
    // Agent to Agent communications
    { source: "financial-agent", target: "project-manager", type: "message", active: true, bandwidth: 10 },
    { source: "mycology-agent", target: "opportunity-scout", type: "message", active: true, bandwidth: 15 },
  ],
};

export async function GET() {
  // In production, fetch from Python backend:
  // const response = await fetch('http://localhost:8000/api/topology');
  // const data = await response.json();
  // return NextResponse.json(data);
  
  return NextResponse.json(topology);
}
