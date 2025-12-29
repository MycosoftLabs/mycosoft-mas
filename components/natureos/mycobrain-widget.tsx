"use client";

import { useState, useEffect, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Activity } from "lucide-react";

interface MycoBrainDevice {
  device_id: string;
  firmware_version?: string;
  status?: string;
  last_seen?: string;
  i2c_addresses?: string[];
  analog_labels?: Record<string, string>;
  mosfet_labels?: Record<string, string>;
  purpose?: string;
}

interface MycoBrainTelemetry {
  seq: number;
  serial: string;
  fw_version: string;
  ts: number;
  side_a?: {
    ai_volts?: Record<string, number>;
    bme688?: {
      temperature: number;
      humidity: number;
      pressure: number;
      gas_resistance: number;
    };
    i2c_devices?: string[];
    mosfet_states?: Record<string, boolean>;
    uptime_ms?: number;
  };
  side_b?: {
    rssi?: number;
    snr?: number;
    tx_count?: number;
    rx_count?: number;
    ack_count?: number;
    retry_count?: number;
  };
}

export function MycoBrainWidget() {
  const [devices, setDevices] = useState<MycoBrainDevice[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [telemetry, setTelemetry] = useState<MycoBrainTelemetry | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchDevices() {
      try {
        setLoading(true);
        const res = await fetch("/api/mycobrain/devices");
        if (!res.ok) throw new Error(`devices: ${res.status}`);
        const list = await res.json();
        setDevices(Array.isArray(list) ? list : []);
        if (!selected && list?.length) {
          setSelected(list[0].device_id || list[0].id || "");
        }
      } catch (e: any) {
        setError(e?.message ?? "Failed to load devices");
      } finally {
        setLoading(false);
      }
    }
    fetchDevices();
  }, []);

  useEffect(() => {
    if (!selected) return;
    
    async function fetchTelemetry() {
      try {
        const since = new Date(Date.now() - 60 * 60 * 1000).toISOString();
        const res = await fetch(
          `/api/mycobrain/telemetry?device_id=${encodeURIComponent(selected)}&startTime=${encodeURIComponent(since)}`
        );
        if (!res.ok) throw new Error(`telemetry: ${res.status}`);
        const rows: MycoBrainTelemetry[] = await res.json();
        setTelemetry(rows?.[0] ?? null);
      } catch (e: any) {
        console.error("Failed to load telemetry:", e);
      }
    }
    
    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 10000); // Refresh every 10 seconds
    return () => clearInterval(interval);
  }, [selected]);

  const currentDevice = useMemo(
    () => devices.find((d) => d.device_id === selected || d.id === selected) ?? null,
    [devices, selected]
  );

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <div className="text-center">
            <Activity className="w-8 h-8 animate-pulse mx-auto mb-4 text-green-500" />
            <p className="text-sm text-gray-500">Loading MycoBrain devices...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <Activity className="w-5 h-5" />
          MycoBrain
        </CardTitle>
        {devices.length > 0 && (
          <Select value={selected} onValueChange={setSelected}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Select device" />
            </SelectTrigger>
            <SelectContent>
              {devices.map((d) => (
                <SelectItem key={d.device_id || d.id} value={d.device_id || d.id || ""}>
                  {d.device_id || d.id}
                  {d.purpose ? ` — ${d.purpose}` : ""}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </CardHeader>

      <CardContent className="space-y-4">
        {error && (
          <div className="text-sm text-red-600 bg-red-50 p-3 rounded-lg">{error}</div>
        )}

        {!currentDevice ? (
          <div className="text-sm text-gray-600 text-center py-8">
            {devices.length === 0
              ? "No MycoBrain devices registered."
              : "Select a device to view telemetry"}
          </div>
        ) : (
          <>
            {/* Device Info */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-gray-50 rounded-lg p-3">
                <div className="text-xs text-gray-500">Firmware</div>
                <div className="font-semibold">{currentDevice.firmware_version || "—"}</div>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <div className="text-xs text-gray-500">Status</div>
                <div className="font-semibold">
                  <Badge variant={currentDevice.status === "online" ? "default" : "secondary"}>
                    {currentDevice.status || "—"}
                  </Badge>
                </div>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <div className="text-xs text-gray-500">I²C Devices</div>
                <div className="font-semibold">
                  {(currentDevice.i2c_addresses?.length ?? 0).toString()}
                </div>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <div className="text-xs text-gray-500">Last seen</div>
                <div className="font-semibold text-sm">
                  {currentDevice.last_seen
                    ? new Date(currentDevice.last_seen).toLocaleString()
                    : "—"}
                </div>
              </div>
            </div>

            {/* BME688 Sensor Data */}
            {telemetry?.side_a?.bme688 && (
              <div>
                <h4 className="text-sm font-medium mb-2">BME688 Environmental Sensor</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-blue-50 rounded-lg p-3">
                    <div className="text-xs text-gray-500">Temperature</div>
                    <div className="font-semibold">
                      {telemetry.side_a.bme688.temperature.toFixed(1)}°C
                    </div>
                  </div>
                  <div className="bg-blue-50 rounded-lg p-3">
                    <div className="text-xs text-gray-500">Humidity</div>
                    <div className="font-semibold">
                      {telemetry.side_a.bme688.humidity.toFixed(1)}%
                    </div>
                  </div>
                  <div className="bg-blue-50 rounded-lg p-3">
                    <div className="text-xs text-gray-500">Pressure</div>
                    <div className="font-semibold">
                      {telemetry.side_a.bme688.pressure.toFixed(1)} hPa
                    </div>
                  </div>
                  <div className="bg-blue-50 rounded-lg p-3">
                    <div className="text-xs text-gray-500">Gas Resistance</div>
                    <div className="font-semibold">
                      {Math.round(telemetry.side_a.bme688.gas_resistance).toLocaleString()} Ω
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Radio Data */}
            {telemetry?.side_b && (
              <div>
                <h4 className="text-sm font-medium mb-2">Radio Communication</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-purple-50 rounded-lg p-3">
                    <div className="text-xs text-gray-500">RSSI</div>
                    <div className="font-semibold">{telemetry.side_b.rssi ?? "—"}</div>
                  </div>
                  <div className="bg-purple-50 rounded-lg p-3">
                    <div className="text-xs text-gray-500">SNR</div>
                    <div className="font-semibold">{telemetry.side_b.snr ?? "—"}</div>
                  </div>
                  <div className="bg-purple-50 rounded-lg p-3">
                    <div className="text-xs text-gray-500">TX/RX</div>
                    <div className="font-semibold">
                      {telemetry.side_b.tx_count ?? 0}/{telemetry.side_b.rx_count ?? 0}
                    </div>
                  </div>
                  <div className="bg-purple-50 rounded-lg p-3">
                    <div className="text-xs text-gray-500">Retries</div>
                    <div className="font-semibold">{telemetry.side_b.retry_count ?? 0}</div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

