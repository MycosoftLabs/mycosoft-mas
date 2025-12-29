import { NextRequest, NextResponse } from "next/server";

const MYCOBRAIN_SERVICE_URL = process.env.MYCOBRAIN_SERVICE_URL || "http://localhost:8003";

export async function GET(request: NextRequest) {
  try {
    const response = await fetch(`${MYCOBRAIN_SERVICE_URL}/devices`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
      next: { revalidate: 5 }, // Revalidate every 5 seconds
    });

    if (!response.ok) {
      throw new Error(`MycoBrain service error: ${response.statusText}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error("Error fetching MycoBrain devices:", error);
    return NextResponse.json(
      { 
        error: error.message || "Failed to fetch devices",
        devices: [],
        count: 0,
        timestamp: new Date().toISOString()
      },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { action, port, side, baudrate } = body;

    if (action === "scan") {
      // Scan for available ports
      const response = await fetch(`${MYCOBRAIN_SERVICE_URL}/ports`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`Port scan failed: ${response.statusText}`);
      }

      const data = await response.json();
      return NextResponse.json(data);
    }

    if (action === "connect" && port) {
      // Connect to a device
      try {
        const response = await fetch(`${MYCOBRAIN_SERVICE_URL}/devices/connect/${encodeURIComponent(port)}`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            port,
            side: side || "auto",
            baudrate: baudrate || 115200,
          }),
        });

        if (!response.ok) {
          let errorDetail = `Connection failed: ${response.statusText}`;
          try {
            const errorData = await response.json();
            errorDetail = errorData.detail || errorData.error || errorData.message || errorDetail;
          } catch (e) {
            // If response is not JSON, use status text
            const text = await response.text();
            if (text) {
              errorDetail = text;
            }
          }
          
          console.error(`Connection failed to ${port}:`, errorDetail);
          return NextResponse.json(
            { 
              error: errorDetail,
              port,
              side: side || "auto",
              status_code: response.status,
            },
            { status: response.status }
          );
        }

        const data = await response.json();
        return NextResponse.json(data);
      } catch (fetchError: any) {
        console.error(`Network error connecting to ${port}:`, fetchError);
        return NextResponse.json(
          { 
            error: `Network error: ${fetchError.message || "Failed to reach MycoBrain service"}`,
            port,
            details: fetchError.message,
          },
          { status: 503 }
        );
      }
    }

    if (action === "disconnect") {
      const { device_id } = body;
      if (!device_id) {
        return NextResponse.json(
          { error: "device_id is required" },
          { status: 400 }
        );
      }

      const response = await fetch(`${MYCOBRAIN_SERVICE_URL}/devices/${device_id}/disconnect`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`Disconnect failed: ${response.statusText}`);
      }

      const data = await response.json();
      return NextResponse.json(data);
    }

    return NextResponse.json(
      { error: "Unknown action" },
      { status: 400 }
    );
  } catch (error: any) {
    console.error("Error in MycoBrain device action:", error);
    return NextResponse.json(
      { error: error.message || "Action failed" },
      { status: 500 }
    );
  }
}

