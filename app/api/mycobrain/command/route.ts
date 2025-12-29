import { NextRequest, NextResponse } from "next/server";

const MYCOBRAIN_SERVICE_URL = process.env.MYCOBRAIN_SERVICE_URL || "http://localhost:8003";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { device_id, command, parameters, use_mdp = true } = body;

    if (!device_id || !command) {
      return NextResponse.json(
        { error: "device_id and command are required" },
        { status: 400 }
      );
    }

    // Build command payload
    const commandPayload = {
      command: {
        command_type: command,
        ...parameters,
      },
      use_mdp: use_mdp,
    };

    const response = await fetch(`${MYCOBRAIN_SERVICE_URL}/devices/${device_id}/command`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(commandPayload),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `Command failed: ${response.statusText}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error("Error sending MycoBrain command:", error);
    return NextResponse.json(
      { 
        error: error.message || "Command failed",
        status: "error"
      },
      { status: 500 }
    );
  }
}

