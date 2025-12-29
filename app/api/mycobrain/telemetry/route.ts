import { NextRequest, NextResponse } from "next/server";

const MYCOBRAIN_SERVICE_URL = process.env.MYCOBRAIN_SERVICE_URL || "http://localhost:8003";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const deviceId = searchParams.get("device_id");

    if (!deviceId) {
      return NextResponse.json(
        { error: "device_id is required" },
        { status: 400 }
      );
    }

    const response = await fetch(`${MYCOBRAIN_SERVICE_URL}/devices/${deviceId}/telemetry`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
      next: { revalidate: 2 }, // Revalidate every 2 seconds for telemetry
    });

    if (!response.ok) {
      throw new Error(`Telemetry fetch failed: ${response.statusText}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error("Error fetching MycoBrain telemetry:", error);
    return NextResponse.json(
      { 
        error: error.message || "Failed to fetch telemetry",
        status: "error",
        telemetry: null
      },
      { status: 500 }
    );
  }
}

