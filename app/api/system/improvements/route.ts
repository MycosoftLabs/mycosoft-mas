import { NextResponse } from "next/server";

interface Improvement {
  id: string;
  category: "workflow" | "agent" | "system" | "performance";
  priority: "critical" | "high" | "medium" | "low";
  title: string;
  description: string;
  workflow?: string;
  node?: string;
  errorCount?: number;
  autoFixable: boolean;
  suggestedFix: string;
  efficiency: number;
  estimatedImpact: string;
  status: "pending" | "in_progress" | "fixed" | "dismissed";
  createdAt: string;
  fixedAt?: string;
}

interface SystemEfficiency {
  overall: number;
  workflows: number;
  agents: number;
  memory: number;
  network: number;
  database: number;
}

// In-memory storage for demo (would be Redis/PostgreSQL in production)
let improvementsCache: Improvement[] = [];
let efficiencyCache: SystemEfficiency = {
  overall: 92,
  workflows: 88,
  agents: 95,
  memory: 78,
  network: 96,
  database: 94,
};

export async function GET() {
  try {
    // Fetch latest data from N8n debug workflow
    let n8nData: { improvements?: Improvement[]; systemEfficiency?: number } | null = null;
    try {
      const response = await fetch("http://localhost:5678/webhook/debug/trigger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "get_report" }),
        signal: AbortSignal.timeout(5000),
      });
      if (response.ok) {
        n8nData = await response.json();
      }
    } catch {
      // N8n might not be reachable, use cached data
    }

    // Merge N8n data with cache
    if (n8nData?.improvements) {
      improvementsCache = [...n8nData.improvements, ...improvementsCache].slice(0, 100);
    }
    if (n8nData?.systemEfficiency) {
      efficiencyCache.workflows = n8nData.systemEfficiency;
      efficiencyCache.overall = Math.round(
        (efficiencyCache.workflows +
          efficiencyCache.agents +
          efficiencyCache.memory +
          efficiencyCache.network +
          efficiencyCache.database) /
          5
      );
    }

    // Add some demo improvements if cache is empty
    if (improvementsCache.length === 0) {
      improvementsCache = [
        {
          id: "imp_001",
          category: "workflow",
          priority: "medium",
          title: "Optimize MYCA: Proactive Monitor aggregation",
          description: "Add error handling to prevent failures when optional nodes don't execute",
          workflow: "MYCA: Proactive Monitor",
          node: "Aggregate Data",
          errorCount: 3,
          autoFixable: true,
          suggestedFix: "Add 'alwaysOutputData: true' to IF nodes before aggregation",
          efficiency: 85,
          estimatedImpact: "Reduce error rate by 95%",
          status: "pending",
          createdAt: new Date().toISOString(),
        },
        {
          id: "imp_002",
          category: "agent",
          priority: "low",
          title: "Improve memory cleanup in long-running agents",
          description: "Some agents accumulate memory over time without proper cleanup",
          autoFixable: false,
          suggestedFix: "Implement periodic memory garbage collection",
          efficiency: 78,
          estimatedImpact: "Free up 15% memory resources",
          status: "pending",
          createdAt: new Date(Date.now() - 3600000).toISOString(),
        },
        {
          id: "imp_003",
          category: "performance",
          priority: "high",
          title: "Cache Qdrant vector search results",
          description: "Repeated searches for same terms can be cached",
          autoFixable: true,
          suggestedFix: "Add Redis caching layer for common queries",
          efficiency: 65,
          estimatedImpact: "Reduce search latency by 80%",
          status: "in_progress",
          createdAt: new Date(Date.now() - 7200000).toISOString(),
        },
      ];
    }

    return NextResponse.json({
      success: true,
      data: {
        improvements: improvementsCache,
        efficiency: efficiencyCache,
        lastUpdated: new Date().toISOString(),
        stats: {
          total: improvementsCache.length,
          pending: improvementsCache.filter((i) => i.status === "pending").length,
          inProgress: improvementsCache.filter((i) => i.status === "in_progress").length,
          fixed: improvementsCache.filter((i) => i.status === "fixed").length,
          autoFixable: improvementsCache.filter((i) => i.autoFixable).length,
          critical: improvementsCache.filter((i) => i.priority === "critical").length,
          high: improvementsCache.filter((i) => i.priority === "high").length,
        },
      },
    });
  } catch (error) {
    console.error("Error fetching improvements:", error);
    return NextResponse.json(
      { success: false, error: "Failed to fetch improvements" },
      { status: 500 }
    );
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { action, improvementId, newStatus } = body;

    if (action === "update_status" && improvementId && newStatus) {
      const improvement = improvementsCache.find((i) => i.id === improvementId);
      if (improvement) {
        improvement.status = newStatus;
        if (newStatus === "fixed") {
          improvement.fixedAt = new Date().toISOString();
        }
        return NextResponse.json({ success: true, improvement });
      }
      return NextResponse.json({ success: false, error: "Improvement not found" }, { status: 404 });
    }

    if (action === "trigger_auto_fix" && improvementId) {
      const improvement = improvementsCache.find((i) => i.id === improvementId);
      if (improvement && improvement.autoFixable) {
        improvement.status = "in_progress";
        
        // Trigger the CodeFixAgent via orchestrator
        try {
          await fetch("http://localhost:8000/tasks/submit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              type: "auto_fix_improvement",
              priority: improvement.priority,
              data: improvement,
            }),
          });
        } catch {
          // Orchestrator might not be available
        }

        return NextResponse.json({ success: true, message: "Auto-fix triggered", improvement });
      }
      return NextResponse.json(
        { success: false, error: "Improvement not found or not auto-fixable" },
        { status: 400 }
      );
    }

    if (action === "add_improvement") {
      const newImprovement: Improvement = {
        id: `imp_${Date.now()}`,
        category: body.category || "system",
        priority: body.priority || "medium",
        title: body.title,
        description: body.description || "",
        autoFixable: body.autoFixable || false,
        suggestedFix: body.suggestedFix || "",
        efficiency: body.efficiency || 50,
        estimatedImpact: body.estimatedImpact || "Unknown",
        status: "pending",
        createdAt: new Date().toISOString(),
      };
      improvementsCache.unshift(newImprovement);
      return NextResponse.json({ success: true, improvement: newImprovement });
    }

    return NextResponse.json({ success: false, error: "Invalid action" }, { status: 400 });
  } catch (error) {
    console.error("Error processing improvement action:", error);
    return NextResponse.json(
      { success: false, error: "Failed to process action" },
      { status: 500 }
    );
  }
}

