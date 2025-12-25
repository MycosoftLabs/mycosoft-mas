"use client";

import { useState } from "react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";

const timeData = Array.from({ length: 24 }, (_, i) => ({
  time: `${i}:00`,
  download: Math.random() * 100 + 50,
  upload: Math.random() * 50 + 20,
  total: Math.random() * 150 + 70,
}));

const protocolData = [
  { name: "HTTPS", value: 45, color: "#0EA5E9" },
  { name: "HTTP", value: 15, color: "#F59E0B" },
  { name: "DNS", value: 12, color: "#10B981" },
  { name: "SSH", value: 8, color: "#8B5CF6" },
  { name: "FTP", value: 5, color: "#EF4444" },
  { name: "Other", value: 15, color: "#6B7280" },
];

const applicationData = [
  { app: "Netflix", bandwidth: 85, sessions: 12, color: "#E50914" },
  { app: "YouTube", bandwidth: 72, sessions: 24, color: "#FF0000" },
  { app: "Zoom", bandwidth: 45, sessions: 3, color: "#2D8CFF" },
  { app: "Discord", bandwidth: 38, sessions: 8, color: "#5865F2" },
  { app: "Steam", bandwidth: 95, sessions: 2, color: "#1B2838" },
  { app: "Spotify", bandwidth: 28, sessions: 5, color: "#1DB954" },
];

const hourlyTraffic = Array.from({ length: 24 }, (_, i) => ({
  hour: i,
  traffic: Math.random() * 200 + 50,
}));

export function TrafficAnalysisView() {
  const [timeRange, setTimeRange] = useState("24h");
  const [viewType, setViewType] = useState("bandwidth");

  return (
    <div className="flex h-full flex-col overflow-auto bg-[#0F172A] p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="mb-2 text-2xl font-bold">Traffic Analysis</h1>
        <p className="text-sm text-gray-400">
          Detailed bandwidth, protocol, and application insights
        </p>
      </div>

      {/* Time Range Selector */}
      <div className="mb-6 flex gap-2">
        {["1h", "24h", "7d", "30d"].map((range) => (
          <button
            key={range}
            onClick={() => setTimeRange(range)}
            className={`rounded-lg px-4 py-2 text-sm font-medium ${
              timeRange === range
                ? "bg-blue-500 text-white"
                : "bg-gray-700 text-gray-300 hover:bg-gray-600"
            }`}
          >
            {range}
          </button>
        ))}
      </div>

      {/* Main Bandwidth Chart */}
      <div className="mb-6 rounded-lg bg-[#1E293B] p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Bandwidth Over Time</h2>
          <div className="flex gap-2">
            <button
              onClick={() => setViewType("bandwidth")}
              className={`rounded px-3 py-1 text-xs ${
                viewType === "bandwidth" ? "bg-blue-500" : "bg-gray-700"
              }`}
            >
              Bandwidth
            </button>
            <button
              onClick={() => setViewType("packets")}
              className={`rounded px-3 py-1 text-xs ${
                viewType === "packets" ? "bg-blue-500" : "bg-gray-700"
              }`}
            >
              Packets
            </button>
          </div>
        </div>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={timeData}>
              <defs>
                <linearGradient id="download" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#0EA5E9" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#0EA5E9" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="upload" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#F59E0B" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#F59E0B" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="time" stroke="#9CA3AF" />
              <YAxis stroke="#9CA3AF" />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1E293B",
                  border: "1px solid #374151",
                  borderRadius: "0.5rem",
                }}
              />
              <Legend />
              <Area
                type="monotone"
                dataKey="download"
                stroke="#0EA5E9"
                fill="url(#download)"
                name="Download (Mbps)"
              />
              <Area
                type="monotone"
                dataKey="upload"
                stroke="#F59E0B"
                fill="url(#upload)"
                name="Upload (Mbps)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Protocol and Application Analysis */}
      <div className="mb-6 grid grid-cols-2 gap-6">
        {/* Protocol Distribution */}
        <div className="rounded-lg bg-[#1E293B] p-6">
          <h2 className="mb-4 text-lg font-semibold">Protocol Distribution</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={protocolData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {protocolData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Top Applications */}
        <div className="rounded-lg bg-[#1E293B] p-6">
          <h2 className="mb-4 text-lg font-semibold">Top Applications</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={applicationData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="app" stroke="#9CA3AF" />
                <YAxis stroke="#9CA3AF" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1E293B",
                    border: "1px solid #374151",
                    borderRadius: "0.5rem",
                  }}
                />
                <Bar dataKey="bandwidth" fill="#0EA5E9" name="Bandwidth (Mbps)" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Hourly Traffic Heatmap */}
      <div className="mb-6 rounded-lg bg-[#1E293B] p-6">
        <h2 className="mb-4 text-lg font-semibold">24-Hour Traffic Pattern</h2>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={hourlyTraffic}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="hour" stroke="#9CA3AF" label={{ value: "Hour of Day", position: "insideBottom", offset: -5 }} />
              <YAxis stroke="#9CA3AF" label={{ value: "Traffic (Mbps)", angle: -90, position: "insideLeft" }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1E293B",
                  border: "1px solid #374151",
                  borderRadius: "0.5rem",
                }}
              />
              <Line
                type="monotone"
                dataKey="traffic"
                stroke="#10B981"
                strokeWidth={2}
                dot={{ fill: "#10B981" }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Detailed Application Table */}
      <div className="rounded-lg bg-[#1E293B] p-6">
        <h2 className="mb-4 text-lg font-semibold">Application Details</h2>
        <table className="w-full text-sm">
          <thead className="border-b border-gray-700 text-left text-xs text-gray-400">
            <tr>
              <th className="pb-3">Application</th>
              <th className="pb-3">Bandwidth</th>
              <th className="pb-3">Sessions</th>
              <th className="pb-3">Trend</th>
            </tr>
          </thead>
          <tbody>
            {applicationData.map((app, i) => (
              <tr key={i} className="border-b border-gray-800 last:border-0">
                <td className="py-3">
                  <div className="flex items-center gap-2">
                    <div
                      className="h-3 w-3 rounded"
                      style={{ backgroundColor: app.color }}
                    />
                    {app.app}
                  </div>
                </td>
                <td className="py-3 font-medium">{app.bandwidth} Mbps</td>
                <td className="py-3 text-gray-400">{app.sessions}</td>
                <td className="py-3">
                  <span className="text-green-500">↑ 12%</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
