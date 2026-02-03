import { NextRequest, NextResponse } from "next/server";
const MAS_URL = process.env.MAS_ORCHESTRATOR_URL || "http://192.168.0.188:8001";
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const deviceId = searchParams.get("deviceId");
  try {
    const response = await fetch(`${MAS_URL}/natureos/telemetry?device_id=${deviceId}`);
    return NextResponse.json(response.ok ? await response.json() : { telemetry: [] });
  } catch {
    return NextResponse.json({ telemetry: [] }, { status: 500 });
  }
}
export async function POST(request: NextRequest) {
  const body = await request.json();
  try {
    const response = await fetch(`${MAS_URL}/natureos/telemetry`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body)
    });
    return NextResponse.json(await response.json());
  } catch {
    return NextResponse.json({ error: "Failed" }, { status: 500 });
  }
}
