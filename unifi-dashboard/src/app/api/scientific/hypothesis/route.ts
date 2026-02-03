import { NextRequest, NextResponse } from "next/server";
const MAS_URL = process.env.MAS_ORCHESTRATOR_URL || "http://192.168.0.188:8001";
export async function GET() {
  try {
    const response = await fetch(`${MAS_URL}/scientific/hypotheses`);
    return NextResponse.json(response.ok ? await response.json() : { hypotheses: [] });
  } catch {
    return NextResponse.json({ hypotheses: [] }, { status: 500 });
  }
}
export async function POST(request: NextRequest) {
  const body = await request.json();
  try {
    const response = await fetch(`${MAS_URL}/scientific/hypotheses`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body)
    });
    return NextResponse.json(await response.json());
  } catch {
    return NextResponse.json({ error: "Failed" }, { status: 500 });
  }
}
