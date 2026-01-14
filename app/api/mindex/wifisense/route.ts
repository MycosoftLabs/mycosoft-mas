import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

// MINDEX API URL for WiFiSense module
const MINDEX_API_URL = process.env.MINDEX_API_URL || "http://localhost:8000";

/**
 * WiFiSense API Route
 * 
 * Provides WiFi CSI-based sensing capabilities:
 * - Phase 0: RSSI-based presence detection
 * - Phase 1: CSI amplitude variance for motion detection
 * - Phase 2: CSI phase for pose estimation (future)
 * 
 * Routes:
 * GET /api/mindex/wifisense - Get system status and all zones
 * GET /api/mindex/wifisense?zone=<id> - Get specific zone status
 * POST /api/mindex/wifisense - Submit CSI reading or configure zones
 */

interface CSIReading {
  device_id: string;
  timestamp?: string;
  rssi: number;
  csi_amplitude?: number[];
  csi_phase?: number[];
  mac_tx?: string;
  mac_rx?: string;
  channel?: number;
}

interface ZoneConfig {
  zone_id: string;
  name: string;
  devices: string[];
  presence_threshold?: number;
  motion_sensitivity?: number;
  enabled?: boolean;
}

interface WiFiSenseState {
  enabled: boolean;
  zones: Record<string, ZoneConfig>;
  readings: Record<string, { rssi: number; timestamp: string }[]>;
  presence: Record<string, { state: string; confidence: number; last_updated: string }>;
  motion: Record<string, { level: string; variance: number; last_updated: string }>;
}

// In-memory state (replace with Redis/DB in production)
const state: WiFiSenseState = {
  enabled: true,
  zones: {
    "main-lab": {
      zone_id: "main-lab",
      name: "Main Laboratory",
      devices: ["myco-001", "myco-002"],
      presence_threshold: -70,
      motion_sensitivity: 0.5,
      enabled: true,
    },
    "grow-room-1": {
      zone_id: "grow-room-1",
      name: "Grow Room 1",
      devices: ["spore-001"],
      presence_threshold: -75,
      motion_sensitivity: 0.7,
      enabled: true,
    },
  },
  readings: {},
  presence: {},
  motion: {},
};

/**
 * GET handler - Get status or zone information
 */
export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const zoneId = searchParams.get("zone");

  // Try MINDEX backend first
  try {
    const url = zoneId
      ? `${MINDEX_API_URL}/api/mindex/wifisense/zone/${zoneId}`
      : `${MINDEX_API_URL}/api/mindex/wifisense/status`;

    const response = await fetch(url, {
      signal: AbortSignal.timeout(3000),
      headers: { Accept: "application/json" },
    });

    if (response.ok) {
      const data = await response.json();
      return NextResponse.json(data);
    }
  } catch {
    // Fall through to local state
  }

  // Return local state
  if (zoneId) {
    const zone = state.zones[zoneId];
    if (!zone) {
      return NextResponse.json({ error: "Zone not found" }, { status: 404 });
    }

    return NextResponse.json({
      zone,
      presence: state.presence[zoneId] || { state: "unknown", confidence: 0 },
      motion: state.motion[zoneId] || { level: "none", variance: 0 },
      readings_count: state.readings[zoneId]?.length || 0,
    });
  }

  // Return full status
  return NextResponse.json({
    enabled: state.enabled,
    processing_mode: "phase0",
    zones: Object.values(state.zones),
    zones_count: Object.keys(state.zones).length,
    active_zones: Object.entries(state.zones).filter(([_, z]) => z.enabled).length,
    devices_count: new Set(Object.values(state.zones).flatMap((z) => z.devices)).size,
    presence_events: Object.entries(state.presence).map(([zone, p]) => ({
      zone_id: zone,
      ...p,
    })),
    motion_events: Object.entries(state.motion)
      .filter(([_, m]) => m.level !== "none")
      .map(([zone, m]) => ({ zone_id: zone, ...m })),
  });
}

/**
 * POST handler - Submit readings or configure zones
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Configure zone
    if (body.action === "configure_zone" && body.zone) {
      const zone = body.zone as ZoneConfig;
      state.zones[zone.zone_id] = {
        ...state.zones[zone.zone_id],
        ...zone,
      };
      return NextResponse.json({ ok: true, zone: state.zones[zone.zone_id] });
    }

    // Remove zone
    if (body.action === "remove_zone" && body.zone_id) {
      delete state.zones[body.zone_id];
      delete state.presence[body.zone_id];
      delete state.motion[body.zone_id];
      delete state.readings[body.zone_id];
      return NextResponse.json({ ok: true });
    }

    // Enable/disable
    if (body.action === "set_enabled") {
      state.enabled = !!body.enabled;
      return NextResponse.json({ ok: true, enabled: state.enabled });
    }

    // Process CSI reading
    if (body.reading || body.device_id) {
      const reading: CSIReading = body.reading || body;

      if (!state.enabled) {
        return NextResponse.json({ ok: false, error: "WiFiSense disabled" });
      }

      const events = processReading(reading);
      return NextResponse.json({
        ok: true,
        device_id: reading.device_id,
        rssi: reading.rssi,
        events,
      });
    }

    return NextResponse.json({ error: "Invalid request" }, { status: 400 });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    );
  }
}

/**
 * Process a CSI/RSSI reading and detect presence/motion
 * Simplified Phase 0 implementation in TypeScript
 */
function processReading(reading: CSIReading): Array<Record<string, unknown>> {
  const events: Array<Record<string, unknown>> = [];
  const now = new Date().toISOString();

  // Find zones for this device
  for (const [zoneId, zone] of Object.entries(state.zones)) {
    if (!zone.enabled || !zone.devices.includes(reading.device_id)) {
      continue;
    }

    // Store reading
    if (!state.readings[zoneId]) {
      state.readings[zoneId] = [];
    }
    state.readings[zoneId].push({ rssi: reading.rssi, timestamp: now });

    // Keep only last 100 readings
    if (state.readings[zoneId].length > 100) {
      state.readings[zoneId] = state.readings[zoneId].slice(-100);
    }

    const readings = state.readings[zoneId];
    if (readings.length < 5) continue;

    // Calculate statistics
    const rssiValues = readings.map((r) => r.rssi);
    const mean = rssiValues.reduce((a, b) => a + b, 0) / rssiValues.length;
    const variance =
      rssiValues.reduce((sum, r) => sum + Math.pow(r - mean, 2), 0) /
      rssiValues.length;

    // Presence detection
    const threshold = zone.presence_threshold || -70;
    const oldState = state.presence[zoneId]?.state || "unknown";
    const newState = mean > threshold ? "present" : "absent";

    if (newState !== oldState) {
      const confidence = Math.min(1, 0.5 + Math.abs(mean - threshold) / 20);
      state.presence[zoneId] = {
        state: newState,
        confidence,
        last_updated: now,
      };
      events.push({
        type: "presence",
        zone_id: zoneId,
        state: newState,
        confidence,
        rssi_avg: mean,
      });
    }

    // Motion detection based on variance
    const sensitivity = zone.motion_sensitivity || 0.5;
    const baseThreshold = 2.0;
    const motionThreshold = baseThreshold / (sensitivity + 0.1);

    let motionLevel = "none";
    if (variance > motionThreshold * 4) motionLevel = "high";
    else if (variance > motionThreshold * 2) motionLevel = "medium";
    else if (variance > motionThreshold) motionLevel = "low";

    if (motionLevel !== "none") {
      const lastMotion = state.motion[zoneId]?.last_updated;
      const timeSinceLastMotion = lastMotion
        ? (Date.now() - new Date(lastMotion).getTime()) / 1000
        : Infinity;

      // Rate limit to 1 event per 5 seconds
      if (timeSinceLastMotion > 5) {
        state.motion[zoneId] = {
          level: motionLevel,
          variance,
          last_updated: now,
        };
        events.push({
          type: "motion",
          zone_id: zoneId,
          level: motionLevel,
          variance,
        });
      }
    }
  }

  return events;
}
