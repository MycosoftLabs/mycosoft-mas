import { NextRequest, NextResponse } from "next/server";

const MYCOBRAIN_SERVICE_URL = process.env.MYCOBRAIN_SERVICE_URL || "http://localhost:8003";

export async function GET(
  request: NextRequest,
  { params }: { params: { port: string } }
) {
  try {
    const deviceId = params.port;
    
    // Get telemetry data from the backend service
    const response = await fetch(`${MYCOBRAIN_SERVICE_URL}/devices/${deviceId}/telemetry`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });
    
    if (!response.ok) {
      // Return empty sensors if device not connected
      if (response.status === 400 || response.status === 404) {
        return NextResponse.json({
          sensors: [],
          timestamp: new Date().toISOString(),
        });
      }
      throw new Error(`Failed to fetch telemetry: ${response.statusText}`);
    }
    
    const data = await response.json();
    
    // Transform telemetry data to sensor format the frontend expects
    const sensors = [];
    
    if (data.telemetry?.bme1) {
      sensors.push({
        id: "bme688-1",
        name: "BME688 Sensor 1",
        type: "environmental",
        address: "0x77",
        status: "active",
        readings: {
          temperature: data.telemetry.bme1.temperature,
          humidity: data.telemetry.bme1.humidity,
          pressure: data.telemetry.bme1.pressure,
          gas_resistance: data.telemetry.bme1.gas_resistance,
          iaq: data.telemetry.bme1.iaq,
        },
        last_reading: data.timestamp,
      });
    }
    
    if (data.telemetry?.bme2) {
      sensors.push({
        id: "bme688-2",
        name: "BME688 Sensor 2",
        type: "environmental",
        address: "0x76",
        status: "active",
        readings: {
          temperature: data.telemetry.bme2.temperature,
          humidity: data.telemetry.bme2.humidity,
          pressure: data.telemetry.bme2.pressure,
          gas_resistance: data.telemetry.bme2.gas_resistance,
          iaq: data.telemetry.bme2.iaq,
        },
        last_reading: data.timestamp,
      });
    }
    
    return NextResponse.json({
      sensors,
      raw: data.telemetry?.raw,
      timestamp: data.timestamp,
    });
  } catch (error: any) {
    console.error("Error fetching sensors:", error);
    return NextResponse.json(
      { 
        error: error.message || "Failed to fetch sensors",
        sensors: [],
      },
      { status: 500 }
    );
  }
}

