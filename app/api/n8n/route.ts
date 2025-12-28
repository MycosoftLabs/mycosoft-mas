import { NextResponse } from "next/server";

const N8N_LOCAL_URL = process.env.N8N_LOCAL_URL || "http://localhost:5678";
const N8N_CLOUD_URL = process.env.N8N_CLOUD_URL || "https://mycosoft.app.n8n.cloud";
const N8N_API_KEY = process.env.N8N_API_KEY || "";

interface N8NWorkflow {
  id: string;
  name: string;
  active: boolean;
  createdAt: string;
  updatedAt: string;
}

interface N8NExecution {
  id: string;
  finished: boolean;
  mode: string;
  startedAt: string;
  stoppedAt?: string;
  workflowId: string;
  status: string;
}

async function fetchN8NData(baseUrl: string, apiKey?: string): Promise<{
  connected: boolean;
  workflows: N8NWorkflow[];
  executions: N8NExecution[];
}> {
  const headers: Record<string, string> = {
    "Accept": "application/json",
  };
  
  if (apiKey) {
    headers["X-N8N-API-KEY"] = apiKey;
  }

  try {
    // First check if n8n is reachable at all
    const healthCheck = await fetch(`${baseUrl}/healthz`, {
      signal: AbortSignal.timeout(3000),
    }).catch(() => null);
    
    if (!healthCheck || !healthCheck.ok) {
      // Try the base URL as fallback
      const baseCheck = await fetch(`${baseUrl}/`, {
        signal: AbortSignal.timeout(3000),
      }).catch(() => null);
      
      if (!baseCheck) {
        return { connected: false, workflows: [], executions: [] };
      }
    }
    
    // n8n is reachable - try to get workflows
    const workflowsRes = await fetch(`${baseUrl}/api/v1/workflows`, {
      headers,
      signal: AbortSignal.timeout(5000),
    });

    if (!workflowsRes.ok) {
      // n8n is running but requires auth - still mark as connected
      return { 
        connected: true, 
        workflows: [
          { id: "auth_required", name: "n8n is running (open n8n UI for details)", active: true, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() }
        ], 
        executions: [] 
      };
    }

    const workflowsData = await workflowsRes.json();
    const workflows = workflowsData.data || [];

    let executions: N8NExecution[] = [];
    try {
      const executionsRes = await fetch(`${baseUrl}/api/v1/executions?limit=10`, {
        headers,
        signal: AbortSignal.timeout(5000),
      });
      
      if (executionsRes.ok) {
        const executionsData = await executionsRes.json();
        executions = executionsData.data || [];
      }
    } catch {
      // Executions endpoint might not be available
    }

    return { connected: true, workflows, executions };
  } catch {
    return { connected: false, workflows: [], executions: [] };
  }
}

export async function GET() {
  const [localData, cloudData] = await Promise.all([
    fetchN8NData(N8N_LOCAL_URL),
    N8N_API_KEY ? fetchN8NData(N8N_CLOUD_URL, N8N_API_KEY) : Promise.resolve({ connected: false, workflows: [], executions: [] }),
  ]);

  return NextResponse.json({
    local: {
      connected: localData.connected,
      url: N8N_LOCAL_URL,
      workflows: localData.workflows,
      executions: localData.executions,
      activeWorkflows: localData.workflows.filter((w) => w.active).length,
      totalWorkflows: localData.workflows.length,
    },
    cloud: {
      connected: cloudData.connected,
      url: N8N_CLOUD_URL,
      workflows: cloudData.workflows,
      executions: cloudData.executions,
      activeWorkflows: cloudData.workflows.filter((w) => w.active).length,
      totalWorkflows: cloudData.workflows.length,
    },
  });
}
