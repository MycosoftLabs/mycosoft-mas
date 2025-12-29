import { NextRequest, NextResponse } from "next/server";

const MYCOBRAIN_SERVICE_URL = process.env.MYCOBRAIN_SERVICE_URL || "http://localhost:8003";

export async function POST(
  request: NextRequest,
  { params }: { params: { port: string } }
) {
  try {
    const body = await request.json();
    const { command, parameters } = body;
    
    // Find device by port
    const devicesResponse = await fetch(`${MYCOBRAIN_SERVICE_URL}/devices`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });
    
    if (!devicesResponse.ok) {
      throw new Error("Failed to fetch devices");
    }
    
    const devicesData = await devicesResponse.json();
    const device = devicesData.devices?.find((d: any) => d.port === params.port);
    
    if (!device) {
      return NextResponse.json(
        { error: `No device found on port ${params.port}` },
        { status: 404 }
      );
    }
    
    // Forward command to the correct endpoint
    // Map common command names to device commands
    const commandMap: Record<string, string> = {
      "set_neopixel": "neopixel",
      "neopixel": "neopixel",
      "buzzer": "buzzer",
      "play_buzzer": "buzzer",
      "i2c_scan": "i2c_scan",
      "get_sensors": "i2c_scan",
    };
    
    const deviceCommand = commandMap[command] || command;
    
    const commandPayload = {
      command: {
        cmd: deviceCommand,
        ...parameters,
      },
      use_mdp: false, // Start with JSON, device may not support MDP yet
    };
    
    const response = await fetch(`${MYCOBRAIN_SERVICE_URL}/devices/${device.device_id}/command`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(commandPayload),
    });
    
    if (!response.ok) {
      const error = await response.json();
      return NextResponse.json(
        { error: error.detail || `Command failed: ${response.statusText}` },
        { status: response.status }
      );
    }
    
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error("Error in MycoBrain control:", error);
    return NextResponse.json(
      { error: error.message || "Control command failed" },
      { status: 500 }
    );
  }
}

