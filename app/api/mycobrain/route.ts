import { NextRequest, NextResponse } from "next/server";

const MYCOBRAIN_SERVICE_URL = process.env.MYCOBRAIN_SERVICE_URL || "http://localhost:8003";

export async function GET(request: NextRequest) {
  try {
    const response = await fetch(`${MYCOBRAIN_SERVICE_URL}/devices`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
    });
    
    if (!response.ok) {
      // Service might not be running
      if (response.status === 500 || response.status === 503) {
        return NextResponse.json({
          devices: [],
          service_status: "offline",
          message: "MycoBrain service is not available",
          timestamp: new Date().toISOString(),
        });
      }
      throw new Error(`Failed to fetch devices: ${response.statusText}`);
    }
    
    const data = await response.json();
    
    // Transform devices to the format the frontend expects
    const devices = (data.devices || []).map((device: any) => ({
      device_id: device.device_id,
      port: device.port,
      name: "MycoBrain Gateway",
      type: "gateway",
      status: device.status || "connected",
      protocol: device.protocol || "MDP v1",
      connected_at: device.connected_at,
      firmware: device.info?.firmware,
      board: device.info?.board,
      sensors: ["BME688 x2"],
      features: ["NeoPixel", "Buzzer", "LoRa", "I2C"],
    }));
    
    return NextResponse.json({
      devices,
      count: devices.length,
      service_status: "online",
      timestamp: new Date().toISOString(),
    });
  } catch (error: any) {
    console.error("Error fetching MycoBrain devices:", error);
    
    // Check if the service is unreachable
    if (error.cause?.code === "ECONNREFUSED" || error.message.includes("fetch")) {
      return NextResponse.json({
        devices: [],
        service_status: "offline",
        message: "MycoBrain service is not running",
        timestamp: new Date().toISOString(),
      });
    }
    
    return NextResponse.json(
      { 
        error: error.message || "Failed to fetch devices",
        devices: [],
        service_status: "error",
      },
      { status: 500 }
    );
  }
}

