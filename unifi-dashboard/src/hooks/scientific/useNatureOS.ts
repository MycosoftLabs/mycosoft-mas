"use client";
import { useState, useEffect, useCallback } from "react";

interface Device {
  id: string;
  name: string;
  type: string;
  status: string;
}

interface Telemetry {
  deviceId: string;
  sensorType: string;
  value: number;
  timestamp: string;
}

interface Event {
  id: string;
  type: string;
  severity: string;
  message: string;
}

export function useNatureOS() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDevices = useCallback(async () => {
    try {
      const response = await fetch("/api/natureos/devices");
      if (response.ok) {
        const data = await response.json();
        setDevices(data.devices || []);
      }
    } catch (e) {
      setError("Failed to fetch devices");
    }
  }, []);

  const registerDevice = useCallback(async (deviceType: string, config: Record<string, unknown>) => {
    try {
      const response = await fetch("/api/natureos/devices", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ device_type: deviceType, ...config }),
      });
      if (response.ok) {
        await fetchDevices();
        return await response.json();
      }
    } catch (e) {
      setError("Failed to register device");
    }
    return null;
  }, [fetchDevices]);

  const sendCommand = useCallback(async (deviceId: string, command: string, payload: Record<string, unknown>) => {
    try {
      const response = await fetch(`/api/natureos/devices/${deviceId}/commands`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command_type: command, payload }),
      });
      return response.ok ? await response.json() : null;
    } catch (e) {
      setError("Failed to send command");
      return null;
    }
  }, []);

  const getTelemetry = useCallback(async (deviceId: string, limit = 100): Promise<Telemetry[]> => {
    try {
      const response = await fetch(`/api/natureos/telemetry?deviceId=${deviceId}&limit=${limit}`);
      if (response.ok) {
        const data = await response.json();
        return data.telemetry || [];
      }
    } catch (e) {
      setError("Failed to fetch telemetry");
    }
    return [];
  }, []);

  useEffect(() => {
    fetchDevices().finally(() => setLoading(false));
    const interval = setInterval(fetchDevices, 10000);
    return () => clearInterval(interval);
  }, [fetchDevices]);

  return {
    devices,
    events,
    loading,
    error,
    fetchDevices,
    registerDevice,
    sendCommand,
    getTelemetry,
  };
}
