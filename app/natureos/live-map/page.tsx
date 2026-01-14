"use client";

/**
 * Live Device Map - deck.gl visualization for device fleet tracking
 * 
 * Features:
 * - Real-time device positions
 * - GPS trail animation with TripsLayer
 * - Time scrubber with playback
 * - Alert timeline visualization
 * 
 * Route: /natureos/live-map
 */

import { useState, useEffect, useCallback, useMemo } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { ArrowLeft, Layers, RefreshCw, Radio, MapPin } from "lucide-react";
import { TimeScrubber } from "@/components/maps/TimeScrubber";
import { useDeviceLayers, DEVICE_COLORS } from "@/components/maps/DeviceTrips";

// Dynamically import DeckGL to avoid SSR issues
const DeckGL = dynamic(() => import("@deck.gl/react").then((mod) => mod.DeckGL), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full bg-gray-900">
      <div className="text-cyan-400 animate-pulse">Loading map...</div>
    </div>
  ),
});

const MapComponent = dynamic(
  () => import("react-map-gl/mapbox").then((mod) => mod.Map),
  { ssr: false }
);

// Initial view state
const INITIAL_VIEW = {
  longitude: -117.16,
  latitude: 32.72,
  zoom: 11,
  pitch: 45,
  bearing: 0,
};

// Mock device data - replace with real API
interface Device {
  device_id: string;
  device_type: "mycobrain" | "sporebase" | "alarm";
  position: [number, number];
  status: "online" | "offline" | "degraded";
  timestamp: number;
}

interface Track {
  device_id: string;
  device_type: string;
  path: Array<[number, number, number]>;
  color: [number, number, number];
}

interface Alert {
  id: string;
  timestamp: number;
  level: "info" | "warning" | "critical";
  message: string;
  device_id?: string;
}

// Generate mock data
function generateMockData(timeOffset: number) {
  const now = Date.now() / 1000;
  const baseTime = now - 3600; // Last hour

  const devices: Device[] = [
    {
      device_id: "myco-001",
      device_type: "mycobrain",
      position: [-117.16 + Math.sin(timeOffset * 0.01) * 0.02, 32.72 + Math.cos(timeOffset * 0.01) * 0.01],
      status: "online",
      timestamp: now,
    },
    {
      device_id: "myco-002",
      device_type: "mycobrain",
      position: [-117.14, 32.73],
      status: "online",
      timestamp: now,
    },
    {
      device_id: "spore-001",
      device_type: "sporebase",
      position: [-117.18 + Math.cos(timeOffset * 0.008) * 0.015, 32.71 + Math.sin(timeOffset * 0.008) * 0.01],
      status: "online",
      timestamp: now,
    },
    {
      device_id: "spore-002",
      device_type: "sporebase",
      position: [-117.15, 32.74],
      status: "degraded",
      timestamp: now - 120,
    },
    {
      device_id: "alarm-001",
      device_type: "alarm",
      position: [-117.17, 32.70],
      status: "offline",
      timestamp: now - 600,
    },
  ];

  // Generate historical paths
  const tracks: Track[] = [
    {
      device_id: "myco-001",
      device_type: "mycobrain",
      path: Array.from({ length: 100 }, (_, i) => {
        const t = baseTime + (i / 100) * 3600;
        return [
          -117.16 + Math.sin(i * 0.05) * 0.02,
          32.72 + Math.cos(i * 0.05) * 0.01,
          t,
        ] as [number, number, number];
      }),
      color: DEVICE_COLORS.mycobrain,
    },
    {
      device_id: "spore-001",
      device_type: "sporebase",
      path: Array.from({ length: 80 }, (_, i) => {
        const t = baseTime + (i / 80) * 3600;
        return [
          -117.18 + Math.cos(i * 0.04) * 0.015,
          32.71 + Math.sin(i * 0.04) * 0.01,
          t,
        ] as [number, number, number];
      }),
      color: DEVICE_COLORS.sporebase,
    },
  ];

  const alerts: Alert[] = [
    { id: "1", timestamp: baseTime + 600, level: "info", message: "Device myco-001 connected", device_id: "myco-001" },
    { id: "2", timestamp: baseTime + 1200, level: "warning", message: "High temperature detected", device_id: "spore-001" },
    { id: "3", timestamp: baseTime + 2400, level: "critical", message: "Device alarm-001 offline", device_id: "alarm-001" },
    { id: "4", timestamp: baseTime + 3000, level: "info", message: "VOC spike recorded", device_id: "myco-002" },
  ];

  return { devices, tracks, alerts };
}

export default function LiveMapPage() {
  const [mounted, setMounted] = useState(false);
  const [viewState, setViewState] = useState(INITIAL_VIEW);
  const [showTrails, setShowTrails] = useState(true);
  const [selectedDevice, setSelectedDevice] = useState<string | null>(null);
  
  // Time control state
  const now = useMemo(() => Date.now() / 1000, []);
  const [currentTime, setCurrentTime] = useState(now);
  const startTime = now - 3600; // Last hour
  const endTime = now;

  // Mock data - replace with real API
  const { devices, tracks, alerts } = useMemo(
    () => generateMockData(currentTime - startTime),
    [currentTime, startTime]
  );

  // Get device layers from hook
  const deviceLayers = useDeviceLayers({
    devices,
    tracks,
    currentTime,
    trailLength: 180,
    showTrails,
  });

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleTimeChange = useCallback((time: number) => {
    setCurrentTime(time);
  }, []);

  const handleAlertClick = useCallback((alert: Alert) => {
    if (alert.device_id) {
      setSelectedDevice(alert.device_id);
      // Find device position and pan to it
      const device = devices.find((d) => d.device_id === alert.device_id);
      if (device) {
        setViewState((prev) => ({
          ...prev,
          longitude: device.position[0],
          latitude: device.position[1],
          zoom: 14,
        }));
      }
    }
    // Jump to alert time
    setCurrentTime(alert.timestamp);
  }, [devices]);

  const handleRefresh = useCallback(() => {
    setCurrentTime(Date.now() / 1000);
  }, []);

  if (!mounted) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-cyan-400 animate-pulse">Initializing...</div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-screen bg-gray-900 overflow-hidden">
      {/* Header */}
      <div className="absolute top-0 left-0 right-0 z-20 p-4 flex items-center justify-between bg-gradient-to-b from-black/60 to-transparent">
        <div className="flex items-center gap-4">
          <Link
            href="/natureos"
            className="p-2 rounded-lg bg-black/40 backdrop-blur-sm border border-white/10 hover:border-white/20 transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-white" />
          </Link>
          <div>
            <h1 className="text-lg font-semibold text-white flex items-center gap-2">
              <Radio className="w-5 h-5 text-cyan-400" />
              Live Device Map
            </h1>
            <p className="text-xs text-gray-400">Real-time fleet tracking</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowTrails(!showTrails)}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors ${
              showTrails
                ? "bg-cyan-500/20 border-cyan-500/40 text-cyan-400"
                : "bg-black/40 border-white/10 text-gray-400"
            }`}
          >
            <Layers className="w-4 h-4" />
            <span className="text-sm">Trails</span>
          </button>
          <button
            onClick={handleRefresh}
            className="p-2 rounded-lg bg-black/40 backdrop-blur-sm border border-white/10 hover:border-white/20 transition-colors"
            title="Jump to now"
          >
            <RefreshCw className="w-5 h-5 text-white" />
          </button>
        </div>
      </div>

      {/* Device Legend */}
      <div className="absolute top-20 right-4 z-10 p-3 rounded-lg bg-black/60 backdrop-blur-sm border border-white/10">
        <div className="text-xs font-medium text-gray-400 mb-2">Devices</div>
        <div className="space-y-2">
          {Object.entries(DEVICE_COLORS).map(([type, color]) => (
            <div key={type} className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: `rgb(${color.join(",")})` }}
              />
              <span className="text-xs text-gray-300 capitalize">{type}</span>
            </div>
          ))}
        </div>
        <div className="mt-3 pt-2 border-t border-white/10">
          <div className="text-xs font-medium text-gray-400 mb-2">Status</div>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-green-400" />
              <span className="text-xs text-gray-300">Online</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-yellow-400" />
              <span className="text-xs text-gray-300">Degraded</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-red-400" />
              <span className="text-xs text-gray-300">Offline</span>
            </div>
          </div>
        </div>
      </div>

      {/* Selected Device Info */}
      {selectedDevice && (
        <div className="absolute top-20 left-4 z-10 p-4 rounded-lg bg-black/60 backdrop-blur-sm border border-cyan-500/30 max-w-xs">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <MapPin className="w-4 h-4 text-cyan-400" />
              <span className="text-sm font-medium text-white">{selectedDevice}</span>
            </div>
            <button
              onClick={() => setSelectedDevice(null)}
              className="text-gray-400 hover:text-white text-xs"
            >
              ✕
            </button>
          </div>
          {(() => {
            const device = devices.find((d) => d.device_id === selectedDevice);
            if (!device) return null;
            return (
              <div className="space-y-1 text-xs text-gray-300">
                <div>Type: <span className="capitalize">{device.device_type}</span></div>
                <div>Status: <span className="capitalize">{device.status}</span></div>
                <div>Position: {device.position[1].toFixed(4)}, {device.position[0].toFixed(4)}</div>
              </div>
            );
          })()}
        </div>
      )}

      {/* Map */}
      <DeckGL
        viewState={viewState}
        onViewStateChange={({ viewState: newViewState }) => setViewState(newViewState as typeof INITIAL_VIEW)}
        controller={true}
        layers={deviceLayers}
        onClick={(info) => {
          if (info.object && "device_id" in info.object) {
            setSelectedDevice((info.object as Device).device_id);
          }
        }}
        getTooltip={({ object }) => {
          if (object && "device_id" in object) {
            const d = object as Device;
            return {
              html: `<div style="padding: 8px; font-family: monospace;">
                <strong>${d.device_id}</strong><br/>
                Type: ${d.device_type}<br/>
                Status: ${d.status}
              </div>`,
              style: {
                backgroundColor: "rgba(0, 0, 0, 0.8)",
                color: "white",
                borderRadius: "8px",
              },
            };
          }
          return null;
        }}
      >
        <MapComponent
          mapboxAccessToken={process.env.NEXT_PUBLIC_MAPBOX_TOKEN}
          mapStyle="mapbox://styles/mapbox/dark-v11"
          attributionControl={false}
        />
      </DeckGL>

      {/* Time Scrubber */}
      <TimeScrubber
        startTime={startTime}
        endTime={endTime}
        currentTime={currentTime}
        onTimeChange={handleTimeChange}
        alerts={alerts}
        onAlertClick={handleAlertClick}
      />
    </div>
  );
}
