import { NextResponse } from "next/server";

const MAS_BACKEND_URL = process.env.MAS_BACKEND_URL || "http://localhost:8001";

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

export async function GET() {
  // Prefer real MAS registry data (used for voice routing + n8n integration).
  try {
    const res = await fetch(`${MAS_BACKEND_URL}/agents/registry/n8n/registry`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });

    if (res.ok) {
      const data = await res.json();
      const agents = asArray(data.agents).map((a: any) => ({
        id: a.id,
        name: a.name,
        type: a.id === "myca" ? "orchestrator" : "agent",
        category: a.category,
        status: a.active ? "online" : "idle",
        experience: "Excellent",
        ip: "0.0.0.0",
        mac: "00:00:00:00:00:00",
        vendor: "Mycosoft",
        uptime: "unknown",
        downloadSpeed: 0,
        uploadSpeed: 0,
        tasksCompleted: 0,
        tasksInProgress: 0,
        connections: [],
      }));

      return NextResponse.json(agents);
    }
  } catch {
    // ignore
  }

  // Fallback: empty list (UI will still render)
  return NextResponse.json([]);
}

export async function POST(request: Request) {
  const body = await request.json();

  // Forward agent commands to MAS voice router (basic wiring for now).
  try {
    const res = await fetch(`${MAS_BACKEND_URL}/agents/registry/route/voice`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ transcript: body?.message ?? body?.transcript ?? "" }),
    });
    if (res.ok) return NextResponse.json(await res.json());
  } catch {
    // ignore
  }

  return NextResponse.json({ success: true, message: "Agent command received", data: body });
}
