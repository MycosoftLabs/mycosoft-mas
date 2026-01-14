"use client";

/**
 * WiFiSense Dashboard - Radio-based presence and motion sensing
 * 
 * Displays:
 * - Zone presence status
 * - Motion activity levels
 * - RSSI signal strength heatmap
 * - Real-time event feed
 * 
 * Route: /natureos/wifisense
 */

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { 
  ArrowLeft, 
  Radio, 
  Users, 
  Activity,
  Wifi,
  WifiOff,
  RefreshCw,
  Settings,
  Eye,
  EyeOff,
  Zap,
  CircleDot,
  Loader2,
} from "lucide-react";

interface ZoneConfig {
  zone_id: string;
  name: string;
  devices: string[];
  presence_threshold: number;
  motion_sensitivity: number;
  enabled: boolean;
}

interface PresenceEvent {
  zone_id: string;
  state: "present" | "absent" | "entering" | "leaving" | "unknown";
  confidence: number;
  last_updated?: string;
}

interface MotionEvent {
  zone_id: string;
  level: "none" | "low" | "medium" | "high";
  variance: number;
  last_updated?: string;
}

interface WiFiSenseStatus {
  enabled: boolean;
  processing_mode: string;
  zones: ZoneConfig[];
  zones_count: number;
  devices_count: number;
  presence_events: PresenceEvent[];
  motion_events: MotionEvent[];
}

const PRESENCE_COLORS = {
  present: "bg-green-500",
  absent: "bg-gray-500",
  entering: "bg-yellow-500",
  leaving: "bg-orange-500",
  unknown: "bg-gray-400",
};

const MOTION_COLORS = {
  none: "bg-gray-400",
  low: "bg-blue-400",
  medium: "bg-yellow-400",
  high: "bg-red-500",
};

const PRESENCE_ICONS = {
  present: Users,
  absent: EyeOff,
  entering: Eye,
  leaving: Eye,
  unknown: CircleDot,
};

export default function WiFiSensePage() {
  const [status, setStatus] = useState<WiFiSenseStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [eventLog, setEventLog] = useState<Array<{
    id: string;
    type: string;
    zone: string;
    message: string;
    time: string;
  }>>([]);

  const fetchStatus = useCallback(async () => {
    try {
      const response = await fetch("/api/mindex/wifisense");
      if (response.ok) {
        const data = await response.json();
        setStatus(data);
        setError(null);
        
        // Add new events to log
        if (data.presence_events) {
          data.presence_events.forEach((event: PresenceEvent) => {
            if (event.state !== "unknown") {
              addEvent("presence", event.zone_id, 
                `${event.state} (${Math.round(event.confidence * 100)}% confidence)`);
            }
          });
        }
        if (data.motion_events) {
          data.motion_events.forEach((event: MotionEvent) => {
            if (event.level !== "none") {
              addEvent("motion", event.zone_id, 
                `${event.level} motion detected`);
            }
          });
        }
      } else {
        setError("Failed to fetch status");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Connection error");
    } finally {
      setLoading(false);
    }
  }, []);

  const addEvent = (type: string, zone: string, message: string) => {
    const id = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    setEventLog((prev) => [
      { id, type, zone, message, time: new Date().toLocaleTimeString() },
      ...prev.slice(0, 49), // Keep last 50 events
    ]);
  };

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchStatus]);

  const toggleEnabled = async () => {
    const newEnabled = !status?.enabled;
    await fetch("/api/mindex/wifisense", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "set_enabled", enabled: newEnabled }),
    });
    fetchStatus();
  };

  const getPresenceForZone = (zoneId: string): PresenceEvent => {
    return status?.presence_events.find((p) => p.zone_id === zoneId) || {
      zone_id: zoneId,
      state: "unknown",
      confidence: 0,
    };
  };

  const getMotionForZone = (zoneId: string): MotionEvent | undefined => {
    return status?.motion_events.find((m) => m.zone_id === zoneId);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-white">
      {/* Header */}
      <header className="border-b border-gray-700/50 bg-gray-900/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/natureos"
              className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-cyan-500/20">
                <Radio className="w-6 h-6 text-cyan-400" />
              </div>
              <div>
                <h1 className="text-xl font-bold">WiFiSense</h1>
                <p className="text-xs text-gray-400">
                  Radio-based Presence & Motion Detection
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors ${
                autoRefresh
                  ? "bg-cyan-500/20 border-cyan-500/40 text-cyan-400"
                  : "bg-gray-800 border-gray-700 text-gray-400"
              }`}
            >
              <RefreshCw className={`w-4 h-4 ${autoRefresh ? "animate-spin-slow" : ""}`} />
              <span className="text-sm">{autoRefresh ? "Live" : "Paused"}</span>
            </button>
            <button
              onClick={fetchStatus}
              className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
            >
              <RefreshCw className="w-5 h-5" />
            </button>
            <button
              onClick={toggleEnabled}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg ${
                status?.enabled
                  ? "bg-green-500/20 text-green-400 border border-green-500/40"
                  : "bg-gray-700 text-gray-400 border border-gray-600"
              }`}
            >
              {status?.enabled ? (
                <>
                  <Wifi className="w-4 h-4" />
                  <span className="text-sm">Enabled</span>
                </>
              ) : (
                <>
                  <WifiOff className="w-4 h-4" />
                  <span className="text-sm">Disabled</span>
                </>
              )}
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
        {error && (
          <div className="mb-6 p-4 rounded-lg bg-red-500/20 border border-red-500/40 text-red-400">
            {error}
          </div>
        )}

        {/* Stats Row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="p-4 rounded-xl bg-gray-800/50 border border-gray-700/50">
            <div className="flex items-center gap-2 mb-2">
              <Radio className="w-4 h-4 text-cyan-400" />
              <span className="text-sm text-gray-400">Zones</span>
            </div>
            <div className="text-2xl font-bold">{status?.zones_count || 0}</div>
          </div>
          <div className="p-4 rounded-xl bg-gray-800/50 border border-gray-700/50">
            <div className="flex items-center gap-2 mb-2">
              <Wifi className="w-4 h-4 text-cyan-400" />
              <span className="text-sm text-gray-400">Devices</span>
            </div>
            <div className="text-2xl font-bold">{status?.devices_count || 0}</div>
          </div>
          <div className="p-4 rounded-xl bg-gray-800/50 border border-gray-700/50">
            <div className="flex items-center gap-2 mb-2">
              <Users className="w-4 h-4 text-green-400" />
              <span className="text-sm text-gray-400">Present</span>
            </div>
            <div className="text-2xl font-bold text-green-400">
              {status?.presence_events.filter((p) => p.state === "present").length || 0}
            </div>
          </div>
          <div className="p-4 rounded-xl bg-gray-800/50 border border-gray-700/50">
            <div className="flex items-center gap-2 mb-2">
              <Activity className="w-4 h-4 text-yellow-400" />
              <span className="text-sm text-gray-400">Motion</span>
            </div>
            <div className="text-2xl font-bold text-yellow-400">
              {status?.motion_events.filter((m) => m.level !== "none").length || 0}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Zones Grid */}
          <div className="lg:col-span-2">
            <div className="rounded-xl bg-gray-800/50 border border-gray-700/50 overflow-hidden">
              <div className="p-4 border-b border-gray-700/50">
                <h2 className="font-semibold flex items-center gap-2">
                  <Radio className="w-5 h-5 text-cyan-400" />
                  Sensing Zones
                </h2>
              </div>
              <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                {status?.zones.map((zone) => {
                  const presence = getPresenceForZone(zone.zone_id);
                  const motion = getMotionForZone(zone.zone_id);
                  const PresenceIcon = PRESENCE_ICONS[presence.state as keyof typeof PRESENCE_ICONS] || CircleDot;

                  return (
                    <div
                      key={zone.zone_id}
                      className={`p-4 rounded-lg bg-gray-900/50 border transition-all ${
                        zone.enabled
                          ? "border-gray-700/50 hover:border-cyan-500/30"
                          : "border-gray-700/30 opacity-50"
                      }`}
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <h3 className="font-medium">{zone.name}</h3>
                          <p className="text-xs text-gray-500">{zone.zone_id}</p>
                        </div>
                        <div
                          className={`px-2 py-1 rounded text-xs font-medium ${
                            PRESENCE_COLORS[presence.state as keyof typeof PRESENCE_COLORS]
                          }`}
                        >
                          {presence.state}
                        </div>
                      </div>

                      <div className="flex items-center gap-4 mb-3">
                        <div className="flex items-center gap-2">
                          <PresenceIcon className="w-5 h-5" />
                          <span className="text-sm">
                            {Math.round(presence.confidence * 100)}%
                          </span>
                        </div>
                        {motion && motion.level !== "none" && (
                          <div className="flex items-center gap-2">
                            <Zap
                              className={`w-4 h-4 ${
                                motion.level === "high"
                                  ? "text-red-400"
                                  : motion.level === "medium"
                                  ? "text-yellow-400"
                                  : "text-blue-400"
                              }`}
                            />
                            <span className="text-sm capitalize">{motion.level}</span>
                          </div>
                        )}
                      </div>

                      <div className="flex items-center gap-2 text-xs text-gray-500">
                        <Wifi className="w-3 h-3" />
                        <span>{zone.devices.length} devices</span>
                        <span className="mx-1">•</span>
                        <span>Threshold: {zone.presence_threshold} dBm</span>
                      </div>
                    </div>
                  );
                })}

                {(!status?.zones || status.zones.length === 0) && (
                  <div className="col-span-2 text-center py-8 text-gray-500">
                    <Radio className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>No sensing zones configured</p>
                    <p className="text-sm mt-1">Add zones to start WiFi sensing</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Event Log */}
          <div className="lg:col-span-1">
            <div className="rounded-xl bg-gray-800/50 border border-gray-700/50 overflow-hidden h-full">
              <div className="p-4 border-b border-gray-700/50">
                <h2 className="font-semibold flex items-center gap-2">
                  <Activity className="w-5 h-5 text-cyan-400" />
                  Event Log
                </h2>
              </div>
              <div className="p-2 max-h-96 overflow-y-auto">
                {eventLog.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <Activity className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">Waiting for events...</p>
                  </div>
                ) : (
                  <div className="space-y-1">
                    {eventLog.map((event) => (
                      <div
                        key={event.id}
                        className="p-2 rounded bg-gray-900/30 text-xs"
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span
                            className={`px-1.5 py-0.5 rounded ${
                              event.type === "presence"
                                ? "bg-green-500/20 text-green-400"
                                : "bg-yellow-500/20 text-yellow-400"
                            }`}
                          >
                            {event.type}
                          </span>
                          <span className="text-gray-500">{event.time}</span>
                        </div>
                        <div className="text-gray-300">{event.zone}</div>
                        <div className="text-gray-500">{event.message}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Mode Info */}
        <div className="mt-6 p-4 rounded-xl bg-gray-800/30 border border-gray-700/30">
          <div className="flex items-center gap-3">
            <Settings className="w-5 h-5 text-gray-500" />
            <div>
              <div className="text-sm font-medium">
                Processing Mode: {status?.processing_mode || "phase0"}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                Phase 0: RSSI-based presence detection | 
                Phase 1: CSI amplitude motion detection | 
                Phase 2: CSI phase pose estimation
              </div>
            </div>
          </div>
        </div>
      </main>

      <style jsx>{`
        @keyframes spin-slow {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .animate-spin-slow {
          animation: spin-slow 3s linear infinite;
        }
      `}</style>
    </div>
  );
}
