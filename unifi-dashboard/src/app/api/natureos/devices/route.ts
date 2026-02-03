import { NextRequest, NextResponse } from "next/server";
const MAS_URL = process.env.MAS_ORCHESTRATOR_URL || "http://192.168.0.188:8001";
export async function GET() {
  try {
    const response = await fetch(`${MAS_URL}/natureos/devices`);
    const data = response.ok ? await response.json() : { devices: [] };
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ devices: [] }, { status: 500 });
  }
}
export async function POST(request: NextRequest) {
  const body = await request.json();
  try {
    const response = await fetch(`${MAS_URL}/natureos/devices/register`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body)
    });
    return NextResponse.json(await response.json(), { status: response.status });
  } catch {
    return NextResponse.json({ error: "Failed" }, { status: 500 });
  }
}
