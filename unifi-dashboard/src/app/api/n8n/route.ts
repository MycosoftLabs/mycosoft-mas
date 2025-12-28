import { NextRequest, NextResponse } from "next/server";

const N8N_LOCAL_URL = process.env.N8N_LOCAL_URL || "http://localhost:5678";
const N8N_CLOUD_URL = process.env.N8N_CLOUD_URL || "https://mycosoft.app.n8n.cloud";
const N8N_API_KEY = process.env.N8N_API_KEY || "";

interface N8NWorkflow {
  id: string;
  name: string;
  active: boolean;
  createdAt: string;
  updatedAt: string;
  nodes?: Array<{ type: string; name: string }>;
  tags?: Array<{ id: string; name: string }>;
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

interface N8NStatus {
  local: {
    connected: boolean;
    url: string;
    workflows: N8NWorkflow[];
    executions: N8NExecution[];
    activeWorkflows: number;
    totalWorkflows: number;
  };
  cloud: {
    connected: boolean;
    url: string;
    workflows: N8NWorkflow[];
    executions: N8NExecution[];
    activeWorkflows: number;
    totalWorkflows: number;
  };
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
    // Fetch workflows
    const workflowsRes = await fetch(`${baseUrl}/api/v1/workflows`, {
      headers,
      signal: AbortSignal.timeout(5000),
    });

    if (!workflowsRes.ok) {
      console.log(`n8n at ${baseUrl} returned ${workflowsRes.status}`);
      return { connected: false, workflows: [], executions: [] };
    }

    const workflowsData = await workflowsRes.json();
    const workflows = workflowsData.data || [];

    // Fetch recent executions
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
  } catch (error) {
    console.log(`Failed to connect to n8n at ${baseUrl}:`, error);
    return { connected: false, workflows: [], executions: [] };
  }
}

export async function GET(): Promise<NextResponse<N8NStatus>> {
  // Fetch data from both local and cloud n8n instances in parallel
  const [localData, cloudData] = await Promise.all([
    fetchN8NData(N8N_LOCAL_URL),
    N8N_API_KEY ? fetchN8NData(N8N_CLOUD_URL, N8N_API_KEY) : Promise.resolve({ connected: false, workflows: [], executions: [] }),
  ]);

  const status: N8NStatus = {
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
  };

  return NextResponse.json(status);
}

// Trigger a workflow execution
export async function POST(request: NextRequest) {
  const body = await request.json();
  const { workflowId, instance = "local", data = {} } = body;

  if (!workflowId) {
    return NextResponse.json({ error: "workflowId is required" }, { status: 400 });
  }

  const baseUrl = instance === "cloud" ? N8N_CLOUD_URL : N8N_LOCAL_URL;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  
  if (instance === "cloud" && N8N_API_KEY) {
    headers["X-N8N-API-KEY"] = N8N_API_KEY;
  }

  try {
    const response = await fetch(`${baseUrl}/api/v1/workflows/${workflowId}/activate`, {
      method: "POST",
      headers,
      body: JSON.stringify(data),
      signal: AbortSignal.timeout(10000),
    });

    if (response.ok) {
      const result = await response.json();
      return NextResponse.json({ success: true, result });
    } else {
      const error = await response.text();
      return NextResponse.json({ success: false, error }, { status: response.status });
    }
  } catch (error) {
    console.error("Error triggering workflow:", error);
    return NextResponse.json({ success: false, error: "Failed to trigger workflow" }, { status: 500 });
  }
}
