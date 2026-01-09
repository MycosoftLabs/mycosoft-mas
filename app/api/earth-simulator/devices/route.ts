import { NextRequest, NextResponse } from "next/server";

/**
 * Device Locations API
 * 
 * Returns MycoBrain device locations and telemetry for map display.
 */

export async function GET(request: NextRequest) {
  try {
    // Fetch devices from MycoBrain service
    const mycobrainUrl = process.env.MYCOBRAIN_SERVICE_URL || "http://localhost:8003";
    
    let devices: any[] = [];
    try {
      const response = await fetch(`${mycobrainUrl}/devices`);
      if (response.ok) {
        const data = await response.json();
        devices = (data.devices || []).map((device: any) => ({
          id: device.device_id || device.id,
          name: device.name || device.device_id,
          port: device.port,
          status: device.status,
          location: device.location || null, // { lat, lon } if available
          lastSeen: device.last_seen || device.lastSeen,
          telemetry: device.telemetry || null,
        }));
      }
    } catch (error) {
      console.error("Error fetching MycoBrain devices:", error);
    }

    return NextResponse.json({
      success: true,
      devices,
      count: devices.length,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Devices API error:", error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}
