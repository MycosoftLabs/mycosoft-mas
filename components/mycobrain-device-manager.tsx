"use client";

import { useState, useEffect } from "react";
import {
  Cpu,
  RefreshCw,
  Power,
  PowerOff,
  Wifi,
  WifiOff,
  Thermometer,
  Droplets,
  Gauge,
  Activity,
  Settings,
  Play,
  Square,
  Zap,
  Volume2,
  VolumeX,
} from "lucide-react";

interface MycoBrainDevice {
  device_id: string;
  port: string;
  side: "side-a" | "side-b" | "unknown";
  status: string;
  connected_at?: string;
  mac_address?: string;
  firmware_version?: string;
  i2c_sensors?: number[];
}

interface Telemetry {
  device_id: string;
  side: string;
  timestamp: string;
  telemetry: {
    temperature?: number;
    humidity?: number;
    pressure?: number;
    gas_resistance?: number;
    ai1_voltage?: number;
    ai2_voltage?: number;
    ai3_voltage?: number;
    ai4_voltage?: number;
    mosfet_states?: boolean[];
    i2c_addresses?: number[];
    firmware_version?: string;
    uptime_seconds?: number;
  };
}

interface SerialPort {
  port: string;
  description: string;
  vid?: string;
  pid?: string;
  is_esp32?: boolean;
  is_mycobrain?: boolean;
}

export function MycoBrainDeviceManager() {
  const [devices, setDevices] = useState<MycoBrainDevice[]>([]);
  const [ports, setPorts] = useState<SerialPort[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<string | null>(null);
  const [telemetry, setTelemetry] = useState<Record<string, Telemetry>>({});
  const [loading, setLoading] = useState(false);
  const [connecting, setConnecting] = useState<Record<string, boolean>>({});

  const fetchDevices = async () => {
    try {
      const res = await fetch("/api/mycobrain/devices");
      if (res.ok) {
        const data = await res.json();
        setDevices(data.devices || []);
      }
    } catch (error) {
      console.error("Error fetching devices:", error);
    }
  };

  const fetchPorts = async () => {
    try {
      const res = await fetch("/api/mycobrain/ports");
      if (res.ok) {
        const data = await res.json();
        setPorts(data.ports || []);
      }
    } catch (error) {
      console.error("Error fetching ports:", error);
    }
  };

  const fetchTelemetry = async (deviceId: string) => {
    try {
      const res = await fetch(`/api/mycobrain/telemetry?device_id=${encodeURIComponent(deviceId)}`);
      if (res.ok) {
        const data = await res.json();
        if (data.status === "ok" && data.telemetry) {
          setTelemetry((prev) => ({
            ...prev,
            [deviceId]: data,
          }));
        }
      }
    } catch (error) {
      console.error("Error fetching telemetry:", error);
    }
  };

  const connectDevice = async (port: string, side: "side-a" | "side-b" = "side-a") => {
    setConnecting((prev) => ({ ...prev, [port]: true }));
    try {
      const res = await fetch("/api/mycobrain/devices", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "connect",
          port,
          side,
          baudrate: 115200,
        }),
      });

      const data = await res.json();

      if (res.ok) {
        await fetchDevices();
        if (data.device_id) {
          setSelectedDevice(data.device_id);
          // Start polling telemetry
          const interval = setInterval(() => {
            fetchTelemetry(data.device_id);
          }, 2000);
          // Store interval ID for cleanup (would need ref in real implementation)
        }
      } else {
        // Detailed error message
        const errorMsg = data.error || data.detail || data.message || `Connection failed (${res.status})`;
        const fullError = `Failed to connect to ${port}:\n${errorMsg}${data.details ? `\n\nDetails: ${data.details}` : ""}`;
        console.error("Connection error:", fullError, data);
        alert(fullError);
      }
    } catch (error: any) {
      const errorMsg = error.message || "Unknown error occurred";
      const fullError = `Connection error to ${port}:\n${errorMsg}\n\nPossible causes:\n- Device not connected\n- Port in use by another application\n- MycoBrain service not running\n- Invalid port name`;
      console.error("Connection error:", error);
      alert(fullError);
    } finally {
      setConnecting((prev) => ({ ...prev, [port]: false }));
    }
  };

  const disconnectDevice = async (deviceId: string) => {
    try {
      const res = await fetch("/api/mycobrain/devices", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "disconnect",
          device_id: deviceId,
        }),
      });

      if (res.ok) {
        await fetchDevices();
        setTelemetry((prev) => {
          const next = { ...prev };
          delete next[deviceId];
          return next;
        });
        if (selectedDevice === deviceId) {
          setSelectedDevice(null);
        }
      }
    } catch (error: any) {
      alert(`Disconnect error: ${error.message}`);
    }
  };

  const sendCommand = async (
    deviceId: string,
    command: string,
    parameters: Record<string, any> = {}
  ) => {
    try {
      const res = await fetch("/api/mycobrain/command", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          device_id: deviceId,
          command,
          parameters,
          // Default to JSON for broad firmware compatibility; the route auto-falls-back anyway.
          use_mdp: false,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        if (data.status === "sent") {
          // Refresh telemetry after command
          setTimeout(() => fetchTelemetry(deviceId), 500);
        }
      } else {
        const error = await res.json();
        alert(`Command failed: ${error.error || error.detail}`);
      }
    } catch (error: any) {
      alert(`Command error: ${error.message}`);
    }
  };

  useEffect(() => {
    fetchDevices();
    fetchPorts();
  }, []);

  // Separate effect for polling - avoids dependency issues
  useEffect(() => {
    const interval = setInterval(() => {
      fetchDevices();
    }, 5000);
    
    return () => clearInterval(interval);
  }, []);

  // Poll telemetry for connected devices
  useEffect(() => {
    const interval = setInterval(() => {
      devices.forEach((d) => {
        if (d.status === "connected") {
          fetchTelemetry(d.device_id);
        }
      });
    }, 5000);
    
    return () => clearInterval(interval);
  }, [devices]);

  const currentTelemetry = selectedDevice ? telemetry[selectedDevice] : null;
  const tel = currentTelemetry?.telemetry;

  return (
    <div className="space-y-6">
      {/* Device List */}
      <div className="rounded-xl bg-gray-800/50 border border-gray-700/50 overflow-hidden">
        <div className="p-4 border-b border-gray-700/50 flex items-center justify-between">
          <h2 className="text-lg font-semibold">MycoBrain Devices</h2>
          <div className="flex gap-2">
            <button
              onClick={fetchPorts}
              className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
              title="Scan Ports"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            </button>
            <button
              onClick={fetchDevices}
              className="px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg text-sm font-medium"
            >
              Refresh
            </button>
          </div>
        </div>

        <div className="divide-y divide-gray-700/50">
          {devices.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              No devices connected. Scan and connect to available ports below.
            </div>
          ) : (
            devices.map((device) => (
              <div
                key={device.device_id}
                className={`p-4 hover:bg-gray-800/50 transition-colors cursor-pointer ${
                  selectedDevice === device.device_id ? "bg-purple-500/10" : ""
                }`}
                onClick={() => setSelectedDevice(device.device_id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div
                      className={`p-3 rounded-lg ${
                        device.status === "connected"
                          ? "bg-green-500/20"
                          : "bg-gray-700/50"
                      }`}
                    >
                      <Cpu
                        className={`w-6 h-6 ${
                          device.status === "connected" ? "text-green-400" : "text-gray-500"
                        }`}
                      />
                    </div>
                    <div>
                      <div className="font-medium">{device.device_id}</div>
                      <div className="text-sm text-gray-500">
                        {device.port} • {device.side.toUpperCase()}
                        {device.mac_address && ` • ${device.mac_address}`}
                      </div>
                      {device.i2c_sensors && device.i2c_sensors.length > 0 && (
                        <div className="text-xs text-cyan-400 mt-1">
                          I2C Sensors: {device.i2c_sensors.map((a) => `0x${a.toString(16)}`).join(", ")}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div
                      className={`px-3 py-1 rounded-full text-xs ${
                        device.status === "connected"
                          ? "bg-green-500/20 text-green-400"
                          : "bg-gray-700 text-gray-400"
                      }`}
                    >
                      {device.status}
                    </div>
                    {device.status === "connected" && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          disconnectDevice(device.device_id);
                        }}
                        className="px-3 py-1 bg-red-600 hover:bg-red-700 rounded-lg text-sm"
                      >
                        Disconnect
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Available Ports */}
      <div className="rounded-xl bg-gray-800/50 border border-gray-700/50 overflow-hidden">
        <div className="p-4 border-b border-gray-700/50">
          <h2 className="text-lg font-semibold">Available Serial Ports</h2>
        </div>
        <div className="divide-y divide-gray-700/50">
          {ports.length === 0 ? (
            <div className="p-8 text-center text-gray-500">No serial ports found</div>
          ) : (
            ports.map((port) => {
              const isConnected = devices.some((d) => d.port === port.port && d.status === "connected");
              return (
                <div key={port.port} className="p-4 flex items-center justify-between">
                  <div>
                    <div className="font-medium">{port.port}</div>
                    <div className="text-sm text-gray-500">{port.description}</div>
                    {port.vid && port.pid && (
                      <div className="text-xs text-gray-600 font-mono">
                        VID: {port.vid} PID: {port.pid}
                      </div>
                    )}
                  </div>
                  <div className="flex gap-2">
                    {!isConnected ? (
                      <>
                        <button
                          onClick={() => connectDevice(port.port, "side-a")}
                          disabled={connecting[port.port]}
                          className="px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm disabled:opacity-50"
                        >
                          {connecting[port.port] ? "Connecting..." : "Connect Side-A"}
                        </button>
                        <button
                          onClick={() => connectDevice(port.port, "side-b")}
                          disabled={connecting[port.port]}
                          className="px-3 py-1 bg-purple-600 hover:bg-purple-700 rounded-lg text-sm disabled:opacity-50"
                        >
                          {connecting[port.port] ? "Connecting..." : "Connect Side-B"}
                        </button>
                      </>
                    ) : (
                      <span className="px-3 py-1 bg-green-500/20 text-green-400 rounded-lg text-sm">
                        Connected
                      </span>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Device Controls & Telemetry */}
      {selectedDevice && currentTelemetry && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Telemetry */}
          <div className="rounded-xl bg-gray-800/50 border border-gray-700/50 p-6">
            <h3 className="text-lg font-semibold mb-4">Telemetry</h3>
            <div className="space-y-4">
              {tel?.temperature !== undefined && (
                <div className="flex items-center gap-3">
                  <Thermometer className="w-5 h-5 text-red-400" />
                  <div className="flex-1">
                    <div className="text-sm text-gray-400">Temperature</div>
                    <div className="text-xl font-bold">{tel.temperature.toFixed(2)}°C</div>
                  </div>
                </div>
              )}
              {tel?.humidity !== undefined && (
                <div className="flex items-center gap-3">
                  <Droplets className="w-5 h-5 text-blue-400" />
                  <div className="flex-1">
                    <div className="text-sm text-gray-400">Humidity</div>
                    <div className="text-xl font-bold">{tel.humidity.toFixed(2)}%</div>
                  </div>
                </div>
              )}
              {tel?.pressure !== undefined && (
                <div className="flex items-center gap-3">
                  <Gauge className="w-5 h-5 text-green-400" />
                  <div className="flex-1">
                    <div className="text-sm text-gray-400">Pressure</div>
                    <div className="text-xl font-bold">{tel.pressure.toFixed(2)} hPa</div>
                  </div>
                </div>
              )}
              {tel?.gas_resistance !== undefined && (
                <div className="flex items-center gap-3">
                  <Activity className="w-5 h-5 text-yellow-400" />
                  <div className="flex-1">
                    <div className="text-sm text-gray-400">Gas Resistance</div>
                    <div className="text-xl font-bold">{tel.gas_resistance.toFixed(0)} Ω</div>
                  </div>
                </div>
              )}
              {tel?.i2c_addresses && tel.i2c_addresses.length > 0 && (
                <div className="mt-4 pt-4 border-t border-gray-700/50">
                  <div className="text-sm text-gray-400 mb-2">I2C Sensors Detected</div>
                  <div className="flex flex-wrap gap-2">
                    {tel.i2c_addresses.map((addr, i) => (
                      <span
                        key={i}
                        className="px-2 py-1 bg-cyan-500/20 text-cyan-400 rounded text-xs font-mono"
                      >
                        0x{addr.toString(16).toUpperCase()}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Controls */}
          <div className="rounded-xl bg-gray-800/50 border border-gray-700/50 p-6">
            <h3 className="text-lg font-semibold mb-4">Device Controls</h3>
            <div className="space-y-4">
              {/* NeoPixel LED Control */}
              <div>
                <div className="text-sm text-gray-400 mb-2">RGB LED Control</div>
                <div className="flex gap-2 flex-wrap">
                  <button
                    onClick={() =>
                      sendCommand(selectedDevice, "set_neopixel", {
                        led_index: 0,
                        r: 255,
                        g: 0,
                        b: 0,
                      })
                    }
                    className="px-3 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-sm"
                  >
                    Red
                  </button>
                  <button
                    onClick={() =>
                      sendCommand(selectedDevice, "set_neopixel", {
                        led_index: 0,
                        r: 0,
                        g: 255,
                        b: 0,
                      })
                    }
                    className="px-3 py-2 bg-green-600 hover:bg-green-700 rounded-lg text-sm"
                  >
                    Green
                  </button>
                  <button
                    onClick={() =>
                      sendCommand(selectedDevice, "set_neopixel", {
                        led_index: 0,
                        r: 0,
                        g: 0,
                        b: 255,
                      })
                    }
                    className="px-3 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm"
                  >
                    Blue
                  </button>
                  <button
                    onClick={() =>
                      sendCommand(selectedDevice, "set_neopixel", {
                        led_index: 0,
                        r: 255,
                        g: 0,
                        b: 255,
                      })
                    }
                    className="px-3 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg text-sm"
                  >
                    Purple
                  </button>
                </div>
                <button
                  onClick={() => sendCommand(selectedDevice, "set_neopixel", { all_off: true })}
                  className="mt-2 px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm w-full"
                >
                  All Off
                </button>
              </div>

              {/* Buzzer Control */}
              <div>
                <div className="text-sm text-gray-400 mb-2">Buzzer</div>
                <div className="flex gap-2">
                  <button
                    onClick={() => sendCommand(selectedDevice, "set_buzzer", { frequency: 1000, duration: 200 })}
                    className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 rounded-lg text-sm flex items-center gap-2"
                  >
                    <Volume2 className="w-4 h-4" />
                    Beep
                  </button>
                  <button
                    onClick={() => sendCommand(selectedDevice, "set_buzzer", { off: true })}
                    className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm flex items-center gap-2"
                  >
                    <VolumeX className="w-4 h-4" />
                    Off
                  </button>
                </div>
              </div>

              {/* MOSFET Control */}
              <div>
                <div className="text-sm text-gray-400 mb-2">MOSFET Outputs</div>
                <div className="grid grid-cols-2 gap-2">
                  {[0, 1, 2, 3].map((mosfet) => {
                    const isOn = tel?.mosfet_states?.[mosfet] || false;
                    return (
                      <button
                        key={mosfet}
                        onClick={() =>
                          sendCommand(selectedDevice, "set_mosfet", {
                            mosfet_index: mosfet,
                            state: !isOn,
                          })
                        }
                        className={`px-3 py-2 rounded-lg text-sm flex items-center justify-center gap-2 ${
                          isOn
                            ? "bg-green-600 hover:bg-green-700"
                            : "bg-gray-700 hover:bg-gray-600"
                        }`}
                      >
                        {isOn ? <Power className="w-4 h-4" /> : <PowerOff className="w-4 h-4" />}
                        MOSFET {mosfet}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* I2C Scan */}
              <div>
                <button
                  onClick={() => sendCommand(selectedDevice, "i2c_scan", {})}
                  className="w-full px-4 py-2 bg-cyan-600 hover:bg-cyan-700 rounded-lg text-sm"
                >
                  Scan I2C Bus
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

