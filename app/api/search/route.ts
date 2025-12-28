import { NextRequest, NextResponse } from "next/server";

interface SearchResult {
  type: "agent" | "service" | "database" | "workflow" | "integration";
  name: string;
  subtitle: string;
  id: string;
  status?: string;
  category?: string;
}

const coreAgents = [
  { id: "myca", name: "MYCA Orchestrator", category: "core" },
  { id: "financial_agent", name: "Financial Agent", category: "financial" },
  { id: "mycology_bio", name: "Mycology Bio Agent", category: "mycology" },
  { id: "research_agent", name: "Research Agent", category: "research" },
  { id: "project_manager", name: "Project Manager Agent", category: "core" },
  { id: "dashboard_agent", name: "Dashboard Agent", category: "core" },
];

const services = [
  { type: "service" as const, name: "n8n Workflows", subtitle: "Local: localhost:5678", id: "n8n-local", status: "active" },
  { type: "service" as const, name: "n8n Cloud", subtitle: "mycosoft.app.n8n.cloud", id: "n8n-cloud", status: "active" },
  { type: "service" as const, name: "ElevenLabs TTS", subtitle: "Voice Synthesis", id: "elevenlabs", status: "active" },
  { type: "integration" as const, name: "UniFi Controller", subtitle: "Network Management", id: "unifi", status: "active" },
];

const databases = [
  { type: "database" as const, name: "SQLite (MINDEX)", subtitle: "Local Knowledge Store", id: "sqlite-mindex", status: "active" },
  { type: "database" as const, name: "ChromaDB", subtitle: "Vector Store", id: "chromadb", status: "active" },
];

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const query = searchParams.get("q")?.toLowerCase() || "";
  
  const agentResults: SearchResult[] = coreAgents.map((agent) => ({
    type: "agent",
    name: agent.name,
    subtitle: `${agent.category} • ${agent.id}`,
    id: agent.id,
    status: "active",
    category: agent.category,
  }));
  
  let allResults: SearchResult[] = [...agentResults, ...services, ...databases];
  
  if (query) {
    allResults = allResults.filter(r => 
      r.name.toLowerCase().includes(query) ||
      r.subtitle.toLowerCase().includes(query) ||
      r.id.toLowerCase().includes(query)
    );
  }
  
  return NextResponse.json({
    results: allResults.slice(0, 20),
    total: allResults.length,
    query,
  });
}
