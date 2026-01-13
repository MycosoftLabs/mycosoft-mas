/**
 * MycoBrain Device Registration API
 * Handles device registration, telemetry ingestion, and status updates
 */

import { NextRequest, NextResponse } from "next/server";
import { headers } from "next/headers";

// Device registration payload
interface DeviceRegistration {
  device_id: string;
  firmware_version: string;
  hardware_version?: string;
  mac_address?: string;
  site_id?: string;
  location?: {
    name: string;
    latitude?: number;
    longitude?: number;
  };
  capabilities?: string[];
  sensors?: {
    type: string;
    model: string;
    address?: string;
  }[];
}

// Telemetry payload
interface TelemetryData {
  device_id: string;
  timestamp: string;
  readings: {
    temperature?: number;
    humidity?: number;
    pressure?: number;
    gas_resistance?: number;
    iaq?: number;
    co2_equivalent?: number;
    voc_equivalent?: number;
    [key: string]: number | undefined;
  };
  status?: {
    uptime_seconds: number;
    free_heap: number;
    wifi_rssi?: number;
  };
}

// In-memory device registry (replace with database in production)
const devices = new Map<string, DeviceRegistration & { 
  registered_at: string; 
  last_seen: string;
  online: boolean;
}>();

/**
 * POST /api/devices/register
 * Register a new MycoBrain device or update existing
 */
export async function POST(request: NextRequest) {
  try {
    const body: DeviceRegistration = await request.json();
    
    // Validate required fields
    if (!body.device_id || !body.firmware_version) {
      return NextResponse.json(
        { error: "Missing required fields: device_id, firmware_version" },
        { status: 400 }
      );
    }
    
    // Get client IP
    const headersList = headers();
    const clientIP = headersList.get("x-forwarded-for") || 
                     headersList.get("x-real-ip") || 
                     "unknown";
    
    const now = new Date().toISOString();
    const existingDevice = devices.get(body.device_id);
    
    if (existingDevice) {
      // Update existing device
      devices.set(body.device_id, {
        ...existingDevice,
        ...body,
        last_seen: now,
        online: true,
      });
      
      console.log(`[MycoBrain] Device updated: ${body.device_id} from ${clientIP}`);
      
      return NextResponse.json({
        status: "updated",
        device_id: body.device_id,
        message: "Device registration updated",
        server_time: now,
      });
    }
    
    // Register new device
    devices.set(body.device_id, {
      ...body,
      registered_at: now,
      last_seen: now,
      online: true,
    });
    
    console.log(`[MycoBrain] New device registered: ${body.device_id} from ${clientIP}`);
    
    return NextResponse.json({
      status: "registered",
      device_id: body.device_id,
      message: "Device registered successfully",
      server_time: now,
      config: {
        telemetry_interval_ms: 60000, // 1 minute
        heartbeat_interval_ms: 30000, // 30 seconds
      },
    });
    
  } catch (error) {
    console.error("[MycoBrain] Registration error:", error);
    return NextResponse.json(
      { error: "Failed to register device" },
      { status: 500 }
    );
  }
}

/**
 * GET /api/devices/register
 * List all registered devices
 */
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const siteId = searchParams.get("site_id");
  const onlineOnly = searchParams.get("online") === "true";
  
  let deviceList = Array.from(devices.values());
  
  // Filter by site
  if (siteId) {
    deviceList = deviceList.filter(d => d.site_id === siteId);
  }
  
  // Filter by online status
  if (onlineOnly) {
    deviceList = deviceList.filter(d => d.online);
  }
  
  // Mark devices offline if not seen in 5 minutes
  const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString();
  deviceList = deviceList.map(d => ({
    ...d,
    online: d.last_seen > fiveMinutesAgo,
  }));
  
  return NextResponse.json({
    count: deviceList.length,
    devices: deviceList,
  });
}
