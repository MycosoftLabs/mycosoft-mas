import { NextRequest, NextResponse } from "next/server";
import * as fs from "fs";
import * as path from "path";

interface SearchResult {
  type: "agent" | "service" | "database" | "workflow" | "integration";
  name: string;
  subtitle: string;
  id: string;
  status?: string;
  category?: string;
}

// Get agents from registry
async function getAgents(): Promise<SearchResult[]> {
  const results: SearchResult[] = [];
  
  // Try to load from registry.json
  try {
    const registryPath = path.join(process.cwd(), "..", "mycosoft_mas", "agents", "registry.json");
    if (fs.existsSync(registryPath)) {
      const content = fs.readFileSync(registryPath, "utf-8");
      const registry = JSON.parse(content);
      for (const agent of registry.agents || []) {
        results.push({
          type: "agent",
          name: agent.display_name || agent.name,
          subtitle: `${agent.category || "core"} • ${agent.agent_id}`,
          id: agent.agent_id,
          status: "active",
          category: agent.category,
        });
      }
    }
  } catch (e) {
    console.error("Error loading agent registry:", e);
  }
  
  // Add core agents that are always present
  const coreAgents = [
    { id: "myca", name: "MYCA Orchestrator", category: "core" },
    { id: "financial_agent", name: "Financial Agent", category: "financial" },
    { id: "mycology_bio", name: "Mycology Bio Agent", category: "mycology" },
    { id: "mycology_knowledge", name: "Mycology Knowledge Agent", category: "mycology" },
    { id: "research_agent", name: "Research Agent", category: "research" },
    { id: "project_manager", name: "Project Manager Agent", category: "core" },
    { id: "dashboard_agent", name: "Dashboard Agent", category: "core" },
    { id: "opportunity_scout", name: "Opportunity Scout", category: "research" },
    { id: "marketing_agent", name: "Marketing Agent", category: "communication" },
    { id: "myco_dao", name: "MycoDAO Agent", category: "dao" },
    { id: "secretary_agent", name: "Secretary Agent", category: "core" },
  ];
  
  for (const agent of coreAgents) {
    if (!results.find(r => r.id === agent.id)) {
      results.push({
        type: "agent",
        name: agent.name,
        subtitle: `${agent.category} • ${agent.id}`,
        id: agent.id,
        status: "active",
        category: agent.category,
      });
    }
  }
  
  return results;
}

// Get services/integrations
async function getServices(): Promise<SearchResult[]> {
  return [
    { type: "service", name: "n8n Workflows", subtitle: "Local: localhost:5678", id: "n8n-local", status: "active" },
    { type: "service", name: "n8n Cloud", subtitle: "mycosoft.app.n8n.cloud", id: "n8n-cloud", status: "active" },
    { type: "service", name: "ElevenLabs TTS", subtitle: "Voice Synthesis", id: "elevenlabs", status: "active" },
    { type: "service", name: "OpenAI API", subtitle: "AI/LLM Services", id: "openai", status: "active" },
    { type: "integration", name: "UniFi Controller", subtitle: "Network Management", id: "unifi", status: "active" },
    { type: "integration", name: "Docker", subtitle: "Container Runtime", id: "docker", status: "active" },
  ];
}

// Get databases
async function getDatabases(): Promise<SearchResult[]> {
  return [
    { type: "database", name: "SQLite (MINDEX)", subtitle: "Local Knowledge Store", id: "sqlite-mindex", status: "active" },
    { type: "database", name: "ChromaDB", subtitle: "Vector Store", id: "chromadb", status: "active" },
    { type: "database", name: "Voice Feedback DB", subtitle: "Speech Data", id: "voice-feedback", status: "active" },
    { type: "database", name: "Agent Registry", subtitle: "Agent Configuration", id: "agent-registry", status: "active" },
  ];
}

// Get workflows from n8n
async function getWorkflows(): Promise<SearchResult[]> {
  const results: SearchResult[] = [];
  
  try {
    const res = await fetch("http://localhost:5678/api/v1/workflows", {
      headers: { "Accept": "application/json" },
      signal: AbortSignal.timeout(3000),
    });
    
    if (res.ok) {
      const data = await res.json();
      for (const workflow of data.data || []) {
        results.push({
          type: "workflow",
          name: workflow.name,
          subtitle: workflow.active ? "Active" : "Inactive",
          id: workflow.id,
          status: workflow.active ? "active" : "inactive",
        });
      }
    }
  } catch {
    // n8n not available, add placeholder
    results.push({
      type: "workflow",
      name: "MYCA Voice Chat",
      subtitle: "Voice Processing",
      id: "myca-voice",
      status: "unknown",
    });
  }
  
  return results;
}

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const query = searchParams.get("q")?.toLowerCase() || "";
  const type = searchParams.get("type"); // Optional filter by type
  
  // Gather all searchable items
  const [agents, services, databases, workflows] = await Promise.all([
    getAgents(),
    getServices(),
    getDatabases(),
    getWorkflows(),
  ]);
  
  let allResults = [...agents, ...services, ...databases, ...workflows];
  
  // Filter by type if specified
  if (type) {
    allResults = allResults.filter(r => r.type === type);
  }
  
  // Filter by query
  if (query) {
    allResults = allResults.filter(r => 
      r.name.toLowerCase().includes(query) ||
      r.subtitle.toLowerCase().includes(query) ||
      r.id.toLowerCase().includes(query) ||
      (r.category && r.category.toLowerCase().includes(query))
    );
  }
  
  // Sort by relevance (exact matches first, then by type priority)
  allResults.sort((a, b) => {
    const aExact = a.name.toLowerCase() === query ? 1 : 0;
    const bExact = b.name.toLowerCase() === query ? 1 : 0;
    if (aExact !== bExact) return bExact - aExact;
    
    // Type priority: agents > workflows > services > databases
    const typePriority: Record<string, number> = { agent: 4, workflow: 3, service: 2, integration: 1, database: 0 };
    return (typePriority[b.type] || 0) - (typePriority[a.type] || 0);
  });
  
  return NextResponse.json({
    results: allResults.slice(0, 20), // Limit to 20 results
    total: allResults.length,
    query,
  });
}
