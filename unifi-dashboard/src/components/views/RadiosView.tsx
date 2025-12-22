"use client";

import { AreaChart, Area, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from "recharts";

const generateAirtimeData = () => {
  const data = [];
  for (let i = 0; i < 24; i++) {
    data.push({
      time: `${i}:00`,
      "2.4GHz-75": Math.random() * 20 + 70,
      "2.4GHz-58": Math.random() * 20 + 50,
      "2.4GHz-25": Math.random() * 20 + 20,
      "5GHz-75": Math.random() * 20 + 70,
      "5GHz-58": Math.random() * 20 + 50,
      "5GHz-25": Math.random() * 20 + 20,
      "6GHz-75": Math.random() * 20 + 70,
      "6GHz-58": Math.random() * 20 + 50,
      "6GHz-25": Math.random() * 20 + 20,
    });
  }
  return data;
};

export function RadiosView() {
  const data = generateAirtimeData();

  return (
    <div className="flex h-full flex-col">
      {/* Top Bar */}
      <div className="flex items-center gap-4 border-b border-gray-800 bg-[#1E293B] px-6 py-4">
        <button className="flex items-center gap-2 rounded-lg bg-blue-500 px-4 py-2 text-sm font-medium">
          <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
            <path d="M3 13h2v-2H3v2zm0 4h2v-2H3v2zm0-8h2V7H3v2zm4 4h14v-2H7v2zm0 4h14v-2H7v2zM7 7v2h14V7H7z" />
          </svg>
          AirView
        </button>
        <button className="rounded-lg px-4 py-2 text-sm text-gray-400 hover:bg-gray-700">
          RF Scan
        </button>
        <button className="rounded-lg px-4 py-2 text-sm text-gray-400 hover:bg-gray-700">
          Speed Test
        </button>
        <button className="rounded-lg px-4 py-2 text-sm text-gray-400 hover:bg-gray-700">
          Airtime
        </button>
        <div className="ml-auto flex items-center gap-2 text-sm">
          <span className="text-gray-400">← Airtime</span>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar */}
        <div className="w-64 border-r border-gray-800 bg-[#1E293B] p-4">
          <div className="mb-6">
            <div className="mb-2 text-sm font-semibold">View By</div>
            <div className="space-y-2">
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="viewBy"
                  defaultChecked
                  className="h-4 w-4 border-gray-600 bg-gray-700 text-blue-500"
                />
                <span className="text-sm">Access Points</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="viewBy"
                  className="h-4 w-4 border-gray-600 bg-gray-700 text-blue-500"
                />
                <span className="text-sm">Clients</span>
              </label>
            </div>
          </div>

          <div className="mb-6">
            <button className="flex w-full items-center justify-between rounded-lg bg-[#0F172A] px-3 py-2 text-sm">
              <span>All APs (2)</span>
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          </div>

          <div className="mb-6 flex gap-2 text-xs">
            <button className="rounded bg-gray-700 px-3 py-1.5">30m</button>
            <button className="rounded bg-gray-700 px-3 py-1.5">1h</button>
            <button className="rounded bg-blue-500 px-3 py-1.5 font-medium">1D</button>
            <button className="rounded bg-gray-700 px-3 py-1.5">1W</button>
            <button className="rounded bg-gray-700 px-3 py-1.5">1M</button>
          </div>

          <div className="mb-6">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-sm font-semibold">Graph Filters</span>
            </div>
            <div className="space-y-3">
              <label className="flex items-center justify-between">
                <span className="text-sm">AP Density</span>
                <input
                  type="checkbox"
                  defaultChecked
                  className="h-4 w-4 rounded border-gray-600 bg-blue-500"
                />
              </label>
              <label className="flex items-center justify-between">
                <span className="text-sm">Connectivity</span>
                <input
                  type="checkbox"
                  defaultChecked
                  className="h-4 w-4 rounded border-gray-600 bg-blue-500"
                />
              </label>
              <label className="flex items-center justify-between">
                <span className="text-sm">Connectivity Logs</span>
                <input
                  type="checkbox"
                  defaultChecked
                  className="h-4 w-4 rounded border-gray-600 bg-blue-500"
                />
              </label>
              <label className="flex items-center justify-between">
                <span className="text-sm">Usage</span>
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-gray-600 bg-gray-700"
                />
              </label>
            </div>
          </div>

          <button className="text-sm text-blue-500 hover:underline">Clear Filters</button>
        </div>

        {/* Main Content */}
        <div className="flex-1 overflow-auto bg-[#0F172A] p-6">
          {/* Airtime Charts */}
          <div className="mb-6">
            <div className="mb-4 text-sm font-semibold">2.4 GHz</div>
            <div className="h-48 rounded-lg bg-[#1E293B] p-4">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="time" stroke="#6B7280" tick={{ fontSize: 10 }} />
                  <YAxis stroke="#6B7280" tick={{ fontSize: 10 }} />
                  <Area
                    type="monotone"
                    dataKey="2.4GHz-75"
                    stackId="1"
                    stroke="#10B981"
                    fill="#10B981"
                    fillOpacity={0.6}
                  />
                  <Area
                    type="monotone"
                    dataKey="2.4GHz-58"
                    stackId="1"
                    stroke="#F59E0B"
                    fill="#F59E0B"
                    fillOpacity={0.6}
                  />
                  <Area
                    type="monotone"
                    dataKey="2.4GHz-25"
                    stackId="1"
                    stroke="#EF4444"
                    fill="#EF4444"
                    fillOpacity={0.6}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-2 flex justify-between text-xs text-gray-400">
              <span>75%</span>
              <span>58%</span>
              <span>25%</span>
              <span>0%</span>
            </div>
          </div>

          <div className="mb-6">
            <div className="mb-4 text-sm font-semibold">5 GHz</div>
            <div className="h-48 rounded-lg bg-[#1E293B] p-4">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="time" stroke="#6B7280" tick={{ fontSize: 10 }} />
                  <YAxis stroke="#6B7280" tick={{ fontSize: 10 }} />
                  <Area
                    type="monotone"
                    dataKey="5GHz-75"
                    stackId="1"
                    stroke="#10B981"
                    fill="#10B981"
                    fillOpacity={0.6}
                  />
                  <Area
                    type="monotone"
                    dataKey="5GHz-58"
                    stackId="1"
                    stroke="#F59E0B"
                    fill="#F59E0B"
                    fillOpacity={0.6}
                  />
                  <Area
                    type="monotone"
                    dataKey="5GHz-25"
                    stackId="1"
                    stroke="#EF4444"
                    fill="#EF4444"
                    fillOpacity={0.6}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="mb-6">
            <div className="mb-4 text-sm font-semibold">6 GHz</div>
            <div className="h-48 rounded-lg bg-[#1E293B] p-4">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="time" stroke="#6B7280" tick={{ fontSize: 10 }} />
                  <YAxis stroke="#6B7280" tick={{ fontSize: 10 }} />
                  <Area
                    type="monotone"
                    dataKey="6GHz-75"
                    stackId="1"
                    stroke="#10B981"
                    fill="#10B981"
                    fillOpacity={0.6}
                  />
                  <Area
                    type="monotone"
                    dataKey="6GHz-58"
                    stackId="1"
                    stroke="#F59E0B"
                    fill="#F59E0B"
                    fillOpacity={0.6}
                  />
                  <Area
                    type="monotone"
                    dataKey="6GHz-25"
                    stackId="1"
                    stroke="#EF4444"
                    fill="#EF4444"
                    fillOpacity={0.6}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* AP Density Section */}
          <div className="mb-6">
            <div className="mb-4 text-sm font-semibold">AP Density</div>
            <div className="mb-2 flex items-center gap-2 text-sm">
              <div className="h-2 w-2 rounded-full bg-green-500" />
              <span className="text-green-500">AP Density is Good</span>
            </div>
            <div className="h-32 rounded-lg bg-[#1E293B] p-4">
              <div className="flex h-full items-end justify-between">
                <div className="relative h-12 w-12 rounded-full bg-white" />
                <div className="relative h-20 w-12 rounded-full bg-green-500" />
              </div>
            </div>
          </div>

          {/* Connectivity Section */}
          <div className="mb-6">
            <div className="mb-4 text-sm font-semibold">Connectivity (Last 24h)</div>
            <div className="grid grid-cols-5 gap-4">
              {[
                { label: "Initial WiFi Connections (0)", value: 0 },
                { label: "All APs (2)", value: 2 },
                { label: "Dream Machine Pro Max", value: 0 },
                { label: "Internet", value: 0 },
                { label: "Server", value: 0 },
              ].map((item, i) => (
                <div key={i} className="rounded-lg bg-[#1E293B] p-4 text-center">
                  <div className="mb-2">
                    <svg className="mx-auto h-12 w-12 text-gray-500" fill="currentColor" viewBox="0 0 24 24">
                      <circle cx="12" cy="12" r="8" />
                    </svg>
                  </div>
                  <div className="text-xs text-gray-400">{item.label}</div>
                  <div className="mt-2 text-xs">Association {item.value}%</div>
                  <div className="text-xs">Authentication {item.value}%</div>
                  <div className="text-xs">DHCP {item.value}%</div>
                  <div className="text-xs">DNS {item.value}%</div>
                  <div className="text-xs">Success {item.value}%</div>
                </div>
              ))}
            </div>
          </div>

          {/* Latency */}
          <div className="grid grid-cols-5 gap-4 text-center text-xs text-gray-400">
            <div>Latency: 0 ms</div>
            <div>Latency: 0 ms</div>
            <div>Latency: 0 ms</div>
            <div>Latency: 0 ms</div>
            <div>Total Latency: 0 ms</div>
          </div>
        </div>
      </div>
    </div>
  );
}
