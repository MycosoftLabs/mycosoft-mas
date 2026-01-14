"use client";

/**
 * DeviceTrips - deck.gl TripsLayer for device movement visualization
 * Displays GPS trails and device tracks with time animation
 */

import { useMemo } from "react";
import { TripsLayer } from "@deck.gl/geo-layers";
import { ScatterplotLayer, PathLayer } from "@deck.gl/layers";

interface DevicePoint {
  device_id: string;
  device_type: "mycobrain" | "sporebase" | "alarm";
  position: [number, number]; // [lng, lat]
  status: "online" | "offline" | "degraded";
  timestamp: number;
}

interface DeviceTrack {
  device_id: string;
  device_type: string;
  path: Array<[number, number, number]>; // [lng, lat, timestamp]
  color: [number, number, number];
}

interface DeviceTripsProps {
  devices: DevicePoint[];
  tracks: DeviceTrack[];
  currentTime: number;
  trailLength?: number;
  showTrails?: boolean;
}

// Color mapping for device types
const DEVICE_COLORS: Record<string, [number, number, number]> = {
  mycobrain: [0, 212, 255],    // cyan
  sporebase: [127, 255, 204],  // mint
  alarm: [255, 107, 157],      // pink
};

// Status colors
const STATUS_COLORS: Record<string, [number, number, number, number]> = {
  online: [0, 255, 136, 200],    // green
  offline: [255, 68, 102, 200],  // red
  degraded: [255, 173, 20, 200], // yellow
};

export function useDeviceLayers({
  devices,
  tracks,
  currentTime,
  trailLength = 180,
  showTrails = true,
}: DeviceTripsProps) {
  const layers = useMemo(() => {
    const result = [];

    // Trips layer for animated trails
    if (showTrails && tracks.length > 0) {
      result.push(
        new TripsLayer({
          id: "device-trips",
          data: tracks,
          getPath: (d: DeviceTrack) => d.path.map((p) => [p[0], p[1]]),
          getTimestamps: (d: DeviceTrack) => d.path.map((p) => p[2]),
          getColor: (d: DeviceTrack) => d.color || DEVICE_COLORS[d.device_type] || [100, 100, 100],
          widthUnits: "pixels",
          getWidth: 3,
          trailLength,
          currentTime,
          capRounded: true,
          jointRounded: true,
          opacity: 0.8,
        })
      );
    }

    // Breadcrumb path layer (static full history)
    if (tracks.length > 0) {
      result.push(
        new PathLayer({
          id: "device-paths",
          data: tracks,
          getPath: (d: DeviceTrack) => d.path.map((p) => [p[0], p[1]]),
          getColor: (d: DeviceTrack) => {
            const color = d.color || DEVICE_COLORS[d.device_type] || [100, 100, 100];
            return [...color, 60]; // Low opacity for background
          },
          widthUnits: "pixels",
          getWidth: 1,
          opacity: 0.3,
        })
      );
    }

    // Current device positions
    if (devices.length > 0) {
      result.push(
        new ScatterplotLayer({
          id: "device-positions",
          data: devices,
          getPosition: (d: DevicePoint) => d.position,
          getRadius: 8,
          radiusUnits: "pixels",
          getFillColor: (d: DevicePoint) => STATUS_COLORS[d.status] || STATUS_COLORS.offline,
          getLineColor: (d: DevicePoint) => DEVICE_COLORS[d.device_type] || [100, 100, 100],
          lineWidthUnits: "pixels",
          getLineWidth: 2,
          stroked: true,
          filled: true,
          pickable: true,
        })
      );

      // Outer ring for online devices (pulse effect simulation)
      result.push(
        new ScatterplotLayer({
          id: "device-rings",
          data: devices.filter((d) => d.status === "online"),
          getPosition: (d: DevicePoint) => d.position,
          getRadius: 16,
          radiusUnits: "pixels",
          getFillColor: [0, 0, 0, 0],
          getLineColor: (d: DevicePoint) => [...DEVICE_COLORS[d.device_type] || [100, 100, 100], 100],
          lineWidthUnits: "pixels",
          getLineWidth: 1,
          stroked: true,
          filled: false,
        })
      );
    }

    return result;
  }, [devices, tracks, currentTime, trailLength, showTrails]);

  return layers;
}

export { DEVICE_COLORS, STATUS_COLORS };
