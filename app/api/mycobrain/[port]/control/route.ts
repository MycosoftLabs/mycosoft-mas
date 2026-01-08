import { NextRequest, NextResponse } from "next/server";

const MYCOBRAIN_SERVICE_URL = process.env.MYCOBRAIN_SERVICE_URL || "http://localhost:8003";

export async function POST(
  request: NextRequest,
  { params }: { params: { port: string } }
) {
  try {
    const body = await request.json();
    const { command, parameters } = body;
    const deviceId = params.port; // This is actually the device_id like "mycobrain-COM5"
    
    // Build the command payload with proper mapping
    const commandPayload = {
      command: {
        command_type: command,
        ...parameters,
      },
    };
    
    console.log(`[MycoBrain Control] Device: ${deviceId}, Command: ${command}, Params:`, parameters);
    
    const response = await fetch(`${MYCOBRAIN_SERVICE_URL}/devices/${deviceId}/command`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(commandPayload),
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      console.error(`[MycoBrain Control] Error:`, errorData);
      return NextResponse.json(
        { error: errorData.detail || `Command failed: ${response.statusText}` },
        { status: response.status }
      );
    }
    
    const data = await response.json();
    console.log(`[MycoBrain Control] Response:`, data);
    return NextResponse.json(data);
  } catch (error: any) {
    console.error("Error in MycoBrain control:", error);
    return NextResponse.json(
      { error: error.message || "Control command failed" },
      { status: 500 }
    );
  }
}

