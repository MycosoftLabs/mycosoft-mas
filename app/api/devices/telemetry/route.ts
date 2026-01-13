/**
 * MycoBrain Telemetry Ingestion API
 * Receives sensor data from MycoBrain devices
 */

import { NextRequest, NextResponse } from "next/server";

// Telemetry data structure
interface TelemetryPayload {
  device_id: string;
  timestamp?: string;
  readings: {
    temperature?: number;
    humidity?: number;
    pressure?: number;
    gas_resistance?: number;
    iaq?: number;
    iaq_accuracy?: number;
    co2_equivalent?: number;
    voc_equivalent?: number;
    static_iaq?: number;
    breath_voc?: number;
  };
  sensor?: string;
  status?: {
    uptime_seconds?: number;
    free_heap?: number;
    wifi_rssi?: number;
    cpu_temp?: number;
  };
}

// In-memory telemetry buffer (replace with time-series DB in production)
const telemetryBuffer: TelemetryPayload[] = [];
const MAX_BUFFER_SIZE = 10000;

/**
 * POST /api/devices/telemetry
 * Receive telemetry data from MycoBrain devices
 */
export async function POST(request: NextRequest) {
  try {
    const body: TelemetryPayload = await request.json();
    
    // Validate required fields
    if (!body.device_id) {
      return NextResponse.json(
        { error: "Missing required field: device_id" },
        { status: 400 }
      );
    }
    
    // Add server timestamp if not provided
    const telemetry: TelemetryPayload = {
      ...body,
      timestamp: body.timestamp || new Date().toISOString(),
    };
    
    // Add to buffer (FIFO)
    telemetryBuffer.push(telemetry);
    if (telemetryBuffer.length > MAX_BUFFER_SIZE) {
      telemetryBuffer.shift();
    }
    
    // Log for debugging
    const readings = body.readings;
    console.log(
      `[Telemetry] ${body.device_id}: ` +
      `T=${readings.temperature?.toFixed(1)}°C ` +
      `H=${readings.humidity?.toFixed(1)}% ` +
      `IAQ=${readings.iaq || 'N/A'}`
    );
    
    return NextResponse.json({
      status: "received",
      device_id: body.device_id,
      timestamp: telemetry.timestamp,
    });
    
  } catch (error) {
    console.error("[Telemetry] Ingestion error:", error);
    return NextResponse.json(
      { error: "Failed to process telemetry" },
      { status: 500 }
    );
  }
}

/**
 * GET /api/devices/telemetry
 * Query telemetry data
 */
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const deviceId = searchParams.get("device_id");
  const limit = parseInt(searchParams.get("limit") || "100");
  const since = searchParams.get("since"); // ISO timestamp
  
  let data = [...telemetryBuffer];
  
  // Filter by device
  if (deviceId) {
    data = data.filter(t => t.device_id === deviceId);
  }
  
  // Filter by time
  if (since) {
    data = data.filter(t => t.timestamp && t.timestamp > since);
  }
  
  // Sort by timestamp descending and limit
  data = data
    .sort((a, b) => (b.timestamp || "").localeCompare(a.timestamp || ""))
    .slice(0, limit);
  
  // Calculate aggregates if single device
  let aggregates = null;
  if (deviceId && data.length > 0) {
    const temps = data.map(t => t.readings.temperature).filter(Boolean) as number[];
    const humids = data.map(t => t.readings.humidity).filter(Boolean) as number[];
    const iaqs = data.map(t => t.readings.iaq).filter(Boolean) as number[];
    
    aggregates = {
      temperature: {
        min: Math.min(...temps),
        max: Math.max(...temps),
        avg: temps.reduce((a, b) => a + b, 0) / temps.length,
      },
      humidity: {
        min: Math.min(...humids),
        max: Math.max(...humids),
        avg: humids.reduce((a, b) => a + b, 0) / humids.length,
      },
      iaq: iaqs.length > 0 ? {
        min: Math.min(...iaqs),
        max: Math.max(...iaqs),
        avg: iaqs.reduce((a, b) => a + b, 0) / iaqs.length,
      } : null,
    };
  }
  
  return NextResponse.json({
    count: data.length,
    device_id: deviceId,
    aggregates,
    data,
  });
}
