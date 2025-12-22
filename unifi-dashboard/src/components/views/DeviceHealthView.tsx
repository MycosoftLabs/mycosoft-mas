"use client";

import { useState, useEffect } from "react";
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Activity, Cpu, HardDrive, Thermometer, Zap, AlertTriangle } from "lucide-react";

const generateMetrics = () =>
  Array.from({ length: 20 }, (_, i) => ({
    time: `${i}m`,
    cpu: Math.random() * 40 + 30,
    memory: Math.random() * 30 + 50,
    temperature: Math.random() * 15 + 50,
  }));

interface DeviceHealth {
  name: string;
  type: string;
  cpu: number;
  memory: number;
  temperature: number;
  uptime: string;
  status: "healthy" | "warning" | "critical";
}

const devices: DeviceHealth[] = [
  {
    name: "Dream Machine Pro Max",
    type: "Gateway",
    cpu: 35,
    memory: 62,
    temperature: 58,
    uptime: "2w 4d 6h",
    status: "healthy",
  },
  {
    name: "BLACK U7 Pro XGS",
    type: "Access Point",
    cpu: 22,
    memory: 48,
    temperature: 52,
    uptime: "2w 4d 6h",
    status: "healthy",
  },
  {
    name: "WHITE U7 Pro XGS",
    type: "Access Point",
    cpu: 25,
    memory: 51,
    temperature: 54,
    uptime: "2w 4d 6h",
    status: "healthy",
  },
  {
    name: "Switch Flex Mini",
    type: "Switch",
    cpu: 18,
    memory: 42,
    temperature: 48,
    uptime: "2w 4d 6h",
    status: "healthy",
  },
];

export function DeviceHealthView() {
  const [selectedDevice, setSelectedDevice] = useState(devices[0]);
  const [metrics, setMetrics] = useState(generateMetrics());

  useEffect(() => {
    const interval = setInterval(() => {
      setMetrics((prev) => [
        ...prev.slice(1),
        {
          time: `${prev.length}m`,
          cpu: Math.random() * 40 + 30,
          memory: Math.random() * 30 + 50,
          temperature: Math.random() * 15 + 50,
        },
      ]);
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "healthy":
        return "text-green-500";
      case "warning":
        return "text-yellow-500";
      case "critical":
        return "text-red-500";
      default:
        return "text-gray-500";
    }
  };

  const getMetricColor = (value: number, type: "cpu" | "memory" | "temperature") => {
    if (type === "temperature") {
      if (value > 70) return "text-red-500";
      if (value > 60) return "text-yellow-500";
      return "text-green-500";
    }
    if (value > 80) return "text-red-500";
    if (value > 60) return "text-yellow-500";
    return "text-green-500";
  };

  return (
    <div className="flex h-full overflow-hidden bg-[#0F172A]">
      {/* Left Panel - Device List */}
      <div className="w-80 border-r border-gray-800 bg-[#1E293B] p-4">
        <h2 className="mb-4 text-lg font-semibold">Network Devices</h2>
        <div className="space-y-2">
          {devices.map((device) => (
            <button
              key={device.name}
              onClick={() => setSelectedDevice(device)}
              className={`w-full rounded-lg border-2 p-4 text-left transition-colors ${
                selectedDevice.name === device.name
                  ? "border-blue-500 bg-gray-700"
                  : "border-gray-700 bg-gray-800 hover:bg-gray-700"
              }`}
            >
              <div className="mb-2 flex items-center justify-between">
                <span className="font-medium">{device.name}</span>
                <span
                  className={`text-xs ${getStatusColor(device.status)}`}
                >
                  {device.status}
                </span>
              </div>
              <div className="mb-2 text-xs text-gray-400">{device.type}</div>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div>
                  <div className="text-gray-500">CPU</div>
                  <div className={getMetricColor(device.cpu, "cpu")}>
                    {device.cpu}%
                  </div>
                </div>
                <div>
                  <div className="text-gray-500">MEM</div>
                  <div className={getMetricColor(device.memory, "memory")}>
                    {device.memory}%
                  </div>
                </div>
                <div>
                  <div className="text-gray-500">TEMP</div>
                  <div className={getMetricColor(device.temperature, "temperature")}>
                    {device.temperature}°C
                  </div>
                </div>
              </div>
            </button>
          ))}
        </div>

        {/* System Alerts */}
        <div className="mt-6 rounded-lg bg-yellow-500/10 p-4">
          <div className="mb-2 flex items-center gap-2 text-yellow-500">
            <AlertTriangle className="h-4 w-4" />
            <span className="text-sm font-semibold">System Alerts</span>
          </div>
          <div className="text-xs text-gray-400">
            No critical alerts at this time
          </div>
        </div>
      </div>

      {/* Right Panel - Detailed Metrics */}
      <div className="flex-1 overflow-auto p-6">
        <div className="mb-6">
          <h1 className="mb-2 text-2xl font-bold">{selectedDevice.name}</h1>
          <div className="flex items-center gap-4 text-sm text-gray-400">
            <span>{selectedDevice.type}</span>
            <span>•</span>
            <span>Uptime: {selectedDevice.uptime}</span>
            <span>•</span>
            <span className={getStatusColor(selectedDevice.status)}>
              {selectedDevice.status.toUpperCase()}
            </span>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="mb-6 grid grid-cols-4 gap-4">
          <div className="rounded-lg bg-[#1E293B] p-4">
            <div className="mb-2 flex items-center gap-2 text-blue-500">
              <Cpu className="h-5 w-5" />
              <span className="text-sm font-medium">CPU Usage</span>
            </div>
            <div className="text-3xl font-bold">{selectedDevice.cpu}%</div>
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-gray-700">
              <div
                className="h-full bg-blue-500 transition-all"
                style={{ width: `${selectedDevice.cpu}%` }}
              />
            </div>
          </div>

          <div className="rounded-lg bg-[#1E293B] p-4">
            <div className="mb-2 flex items-center gap-2 text-purple-500">
              <HardDrive className="h-5 w-5" />
              <span className="text-sm font-medium">Memory</span>
            </div>
            <div className="text-3xl font-bold">{selectedDevice.memory}%</div>
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-gray-700">
              <div
                className="h-full bg-purple-500 transition-all"
                style={{ width: `${selectedDevice.memory}%` }}
              />
            </div>
          </div>

          <div className="rounded-lg bg-[#1E293B] p-4">
            <div className="mb-2 flex items-center gap-2 text-orange-500">
              <Thermometer className="h-5 w-5" />
              <span className="text-sm font-medium">Temperature</span>
            </div>
            <div className="text-3xl font-bold">{selectedDevice.temperature}°C</div>
            <div className="mt-2 text-xs text-gray-400">
              Max: 85°C • Normal: 40-65°C
            </div>
          </div>

          <div className="rounded-lg bg-[#1E293B] p-4">
            <div className="mb-2 flex items-center gap-2 text-green-500">
              <Zap className="h-5 w-5" />
              <span className="text-sm font-medium">Power</span>
            </div>
            <div className="text-3xl font-bold">12.5W</div>
            <div className="mt-2 text-xs text-gray-400">
              PoE+ • 802.3at
            </div>
          </div>
        </div>

        {/* CPU Usage Chart */}
        <div className="mb-6 rounded-lg bg-[#1E293B] p-6">
          <h2 className="mb-4 text-lg font-semibold">CPU Usage (Last 20min)</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={metrics}>
                <defs>
                  <linearGradient id="cpuGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="time" stroke="#9CA3AF" />
                <YAxis stroke="#9CA3AF" domain={[0, 100]} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1E293B",
                    border: "1px solid #374151",
                    borderRadius: "0.5rem",
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="cpu"
                  stroke="#3B82F6"
                  fill="url(#cpuGradient)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Memory Usage Chart */}
        <div className="mb-6 rounded-lg bg-[#1E293B] p-6">
          <h2 className="mb-4 text-lg font-semibold">Memory Usage (Last 20min)</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={metrics}>
                <defs>
                  <linearGradient id="memoryGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#8B5CF6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#8B5CF6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="time" stroke="#9CA3AF" />
                <YAxis stroke="#9CA3AF" domain={[0, 100]} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1E293B",
                    border: "1px solid #374151",
                    borderRadius: "0.5rem",
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="memory"
                  stroke="#8B5CF6"
                  fill="url(#memoryGradient)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Temperature Chart */}
        <div className="rounded-lg bg-[#1E293B] p-6">
          <h2 className="mb-4 text-lg font-semibold">Temperature (Last 20min)</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={metrics}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="time" stroke="#9CA3AF" />
                <YAxis stroke="#9CA3AF" domain={[30, 80]} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1E293B",
                    border: "1px solid #374151",
                    borderRadius: "0.5rem",
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="temperature"
                  stroke="#F59E0B"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
