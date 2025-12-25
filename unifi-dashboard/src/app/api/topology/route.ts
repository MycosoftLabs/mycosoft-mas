import { NextResponse } from "next/server";

const MAS_BACKEND_URL = process.env.MAS_BACKEND_URL || "http://localhost:8001";

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

export async function GET() {
  // Build a topology based on the MAS agent registry when available.
  try {
    const res = await fetch(`${MAS_BACKEND_URL}/agents/registry/n8n/registry`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
    if (res.ok) {
      const data = await res.json();
      const agents = asArray(data.agents) as any[];

      const nodes = [
        { id: "n8n", type: "service", name: "n8n Workflows", x: 50, y: 45, status: "online" },
        { id: "mas", type: "service", name: "MAS Orchestrator", x: 50, y: 25, status: "online" },
        ...agents.map((a, idx) => ({
          id: a.id,
          type: a.id === "myca" ? "orchestrator" : "agent",
          name: a.name,
          x: 15 + (idx % 6) * 14,
          y: 65 + Math.floor(idx / 6) * 10,
          status: a.active ? "online" : "idle",
          category: a.category,
        })),
      ];

      const connections = agents.map((a) => ({
        source: "mas",
        target: a.id,
        type: "control",
        active: true,
        bandwidth: 5,
      }));

      connections.push({
        source: "mas",
        target: "n8n",
        type: "control",
        active: true,
        bandwidth: 10,
      });

      return NextResponse.json({ nodes, connections });
    }
  } catch {
    // ignore
  }

  return NextResponse.json({ nodes: [], connections: [] });
}
