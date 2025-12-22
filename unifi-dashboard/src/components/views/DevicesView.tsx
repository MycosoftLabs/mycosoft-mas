"use client";

import { AreaChart, Area, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from "recharts";

const generateData = () => {
  const data = [];
  for (let i = 0; i < 24; i++) {
    data.push({
      time: `${i}:00`,
      traffic: Math.random() * 5,
      latency: Math.random() * 10 + 5,
    });
  }
  return data;
};

export function DevicesView() {
  const data = generateData();

  return (
    <div className="flex h-full overflow-hidden">
      {/* Left Sidebar */}
      <div className="w-64 border-r border-gray-800 bg-[#1E293B] p-4">
        <div className="mb-4 rounded-lg bg-[#0F172A] p-4">
          <svg viewBox="0 0 200 80" className="mb-3 h-20 w-full">
            <rect x="20" y="20" width="160" height="40" rx="4" fill="#374151" />
            <rect x="25" y="25" width="150" height="30" rx="2" fill="#1F2937" />
            <circle cx="165" cy="40" r="3" fill="#10B981" />
            <circle cx="175" cy="40" r="3" fill="#10B981" />
          </svg>
          <div className="text-sm font-semibold">Dream Machine Pro Max</div>
        </div>

        <div className="space-y-4 text-sm">
          <div>
            <div className="text-xs text-gray-400">Gateway IP</div>
            <div>192.168.0.1</div>
          </div>

          <div>
            <div className="text-xs text-gray-400">System Uptime</div>
            <div>2w 4d 4h 0m</div>
          </div>

          <div>
            <div className="text-xs text-gray-400">UniFi OS 4.4.6</div>
            <div className="text-xs text-gray-400">Network 10.0.162</div>
          </div>

          <div className="border-t border-gray-800 pt-4">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-xs text-gray-400">WAN1</span>
              <div className="flex items-center gap-1">
                <div className="h-2 w-2 rounded-full bg-blue-500" />
                <span className="text-xs text-blue-500">Wyverd Fiber</span>
              </div>
            </div>

            <div className="mb-2 text-xs">
              <div className="text-gray-400">WAN IP</div>
              <div>192.168.1.141</div>
            </div>

            <div className="mb-2 text-xs">
              <div className="text-gray-400">Monthly Data Usage</div>
              <div>168 GB</div>
            </div>

            <div className="text-xs">
              <div className="text-gray-400">Throughput</div>
              <div className="flex gap-2">
                <span className="text-cyan-500">↓ 0 bps</span>
                <span className="text-purple-500">↑ 0 bps</span>
              </div>
            </div>
          </div>

          <div className="flex gap-2 text-xs">
            <div className="flex items-center gap-1">
              <div className="h-3 w-3 bg-yellow-500" />
              5ms
            </div>
            <div className="flex items-center gap-1">
              <svg viewBox="0 0 16 16" className="h-3 w-3 fill-red-500">
                <circle cx="8" cy="8" r="6" />
              </svg>
              5ms
            </div>
            <div className="flex items-center gap-1">
              <svg viewBox="0 0 16 16" className="h-3 w-3 fill-orange-500">
                <path d="M8 2L2 14h12L8 2z" />
              </svg>
              5ms
            </div>
          </div>

          <button className="text-xs text-blue-500 hover:underline">ISP Speed Test</button>

          <div className="border-t border-gray-800 pt-4">
            <div className="mb-2 text-xs font-semibold">Default WiFi Speeds</div>
            <div className="space-y-2 text-xs">
              <div>
                <div className="mb-1 text-gray-400">Channel Widths (MHz)</div>
                <div className="grid grid-cols-5 gap-1">
                  <span className="text-gray-400">5 GHz</span>
                  <span>20</span>
                  <span>40</span>
                  <span>80</span>
                  <span>160</span>
                </div>
                <div className="grid grid-cols-5 gap-1">
                  <span className="text-gray-400">6 GHz</span>
                  <span>20</span>
                  <span>40</span>
                  <span>80</span>
                  <span className="text-blue-500">160</span>
                  <span>320</span>
                </div>
              </div>
            </div>
          </div>

          <button className="w-full rounded-lg bg-blue-500 px-4 py-2 text-sm font-medium">
            CyberSecure Enhanced - Activate
          </button>

          <div className="text-xs text-gray-400">
            • Up to 55K signatures updated Real-time.
            <br />• 100+ Content filters
          </div>

          <button className="text-xs text-blue-500 hover:underline">Dashboard Widgets</button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto bg-[#0F172A]">
        {/* Top Tabs */}
        <div className="border-b border-gray-800 bg-[#1E293B]">
          <div className="flex gap-6 px-6">
            <button className="border-b-2 border-blue-500 px-4 py-3 text-sm font-medium text-blue-500">
              Overview
            </button>
            <button className="px-4 py-3 text-sm text-gray-400 hover:text-white">
              WiFi
            </button>
            <button className="px-4 py-3 text-sm text-gray-400 hover:text-white">
              Flows
            </button>
            <button className="px-4 py-3 text-sm text-gray-400 hover:text-white">
              All WANs
            </button>
          </div>
        </div>

        {/* Stats */}
        <div className="border-b border-gray-800 p-6">
          <div className="mb-4 flex items-center gap-4">
            <div className="flex items-center gap-2">
              <svg viewBox="0 0 100 40" className="h-8 w-20 fill-gray-400">
                <rect x="5" y="8" width="90" height="24" rx="2" fill="#374151" />
                <circle cx="85" cy="20" r="2" fill="#10B981" />
              </svg>
              <span className="text-sm font-medium">Dream Machine Pro Max</span>
            </div>
            <div className="ml-auto flex gap-6 text-xs">
              <div className="text-center">
                <div className="text-xl font-bold text-blue-500">1</div>
                <div className="text-gray-400">WAN1</div>
              </div>
              <div className="text-center">
                <div className="text-xl font-bold text-gray-500">0</div>
                <div className="text-gray-400">WAN2</div>
              </div>
              <div className="text-center">
                <div className="text-xl font-bold text-blue-500">2</div>
                <div className="text-gray-400">LANs</div>
              </div>
              <div className="text-center">
                <div className="text-xl font-bold text-blue-500">8</div>
                <div className="text-gray-400">Ports</div>
              </div>
            </div>
          </div>

          {/* Connection Tabs */}
          <div className="mb-4 flex gap-2 text-sm">
            <button className="rounded bg-blue-500 px-3 py-1.5 font-medium">
              Internet Activity
            </button>
            <button className="rounded bg-gray-700 px-3 py-1.5">3.33 GB</button>
            <button className="flex items-center gap-2 rounded bg-gray-700 px-3 py-1.5">
              <span>Avg. Latency</span>
            </button>
            <button className="flex items-center gap-2 rounded bg-gray-700 px-3 py-1.5">
              <span>Packet Loss</span>
            </button>
            <button className="flex items-center gap-2 rounded bg-gray-700 px-3 py-1.5">
              <span>Connections</span>
            </button>
            <div className="ml-auto flex gap-2 text-xs">
              <button className="rounded bg-gray-700 px-2 py-1">1h</button>
              <button className="rounded bg-blue-500 px-2 py-1 font-medium">1D</button>
              <button className="rounded bg-gray-700 px-2 py-1">1W</button>
              <button className="rounded bg-gray-700 px-2 py-1">1M</button>
            </div>
          </div>

          {/* Chart */}
          <div className="h-64 rounded-lg bg-[#1E293B] p-4">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data}>
                <defs>
                  <linearGradient id="colorTraffic" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0EA5E9" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#0EA5E9" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="time" stroke="#6B7280" tick={{ fontSize: 10 }} />
                <YAxis stroke="#6B7280" tick={{ fontSize: 10 }} />
                <Area
                  type="monotone"
                  dataKey="traffic"
                  stroke="#0EA5E9"
                  strokeWidth={2}
                  fill="url(#colorTraffic)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Bottom Sections */}
        <div className="p-6">
          <div className="grid grid-cols-2 gap-6">
            {/* Top APs */}
            <div className="rounded-lg bg-[#1E293B] p-4">
              <div className="mb-4 text-sm font-semibold">Top APs</div>
              <div className="space-y-3 text-xs">
                {["BLACK U...", "MycoC...", "ubuntu-c...", "SSL/TLS", "STUN"].map((item, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <div className="h-8 w-8 rounded bg-gray-700" />
                    <div className="flex-1">
                      <div className="font-medium">{item}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Top Clients */}
            <div className="rounded-lg bg-[#1E293B] p-4">
              <div className="mb-4 text-sm font-semibold">Top Clients</div>
              <div className="space-y-3 text-xs">
                {["Docker", "QUIC", "Google Pl...", "Google St...", "Google D..."].map((item, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <div className="h-8 w-8 rounded-full bg-gray-700" />
                    <div className="flex-1">
                      <div className="font-medium">{item}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Top Apps */}
            <div className="rounded-lg bg-[#1E293B] p-4">
              <div className="mb-4 text-sm font-semibold">Top Apps</div>
              <div className="space-y-2 text-xs">
                {[
                  { name: "SSL/TLS", icon: "🔒" },
                  { name: "STUN", icon: "📡" },
                  { name: "Docker", icon: "🐳" },
                  { name: "QUIC", icon: "⚡" },
                  { name: "Google Play", icon: "▶" },
                ].map((item, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded bg-gray-700 text-sm">
                      {item.icon}
                    </div>
                    <div>{item.name}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Most Common Devices */}
            <div className="rounded-lg bg-[#1E293B] p-4">
              <div className="mb-4 text-sm font-semibold">Most Common Devices</div>
              <div className="grid grid-cols-4 gap-3">
                {Array(8)
                  .fill(0)
                  .map((_, i) => (
                    <div key={i} className="flex flex-col items-center gap-2 text-center">
                      <div className="h-12 w-12 rounded bg-gray-700" />
                      <div className="text-[10px] text-gray-400">Device {i + 1}</div>
                    </div>
                  ))}
              </div>
            </div>
          </div>

          {/* WiFi Stats */}
          <div className="mt-6 rounded-lg bg-[#1E293B] p-4">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex gap-8">
                <button className="text-sm font-semibold">2.4 GHz</button>
                <button className="rounded bg-blue-500 px-4 py-1.5 text-sm font-semibold">
                  5 GHz
                </button>
                <button className="text-sm text-gray-400">6 GHz</button>
              </div>
              <button className="text-xs text-blue-500 hover:underline">→</button>
            </div>

            <div className="mb-4 text-xs text-gray-400">AP Radio TX Retries</div>
            <div className="grid grid-cols-4 gap-4 text-center text-xs">
              <div className="rounded bg-[#0F172A] p-3">
                <div className="mb-1 text-2xl font-bold text-green-500">35%+</div>
                <div className="text-gray-400">Good</div>
              </div>
              <div className="rounded bg-[#0F172A] p-3">
                <div className="mb-1 text-2xl font-bold">25%</div>
                <div className="text-gray-400">Fair</div>
              </div>
              <div className="rounded bg-[#0F172A] p-3">
                <div className="mb-1 text-2xl font-bold">28%</div>
                <div className="text-gray-400">Poor</div>
              </div>
              <div className="rounded bg-[#0F172A] p-3">
                <div className="mb-1 text-2xl font-bold">18%</div>
                <div className="text-gray-400">Critical</div>
              </div>
            </div>
          </div>

          {/* WiFi Connectivity */}
          <div className="mt-6 rounded-lg bg-[#1E293B] p-4">
            <div className="mb-4 text-sm font-semibold">WiFi Connectivity</div>
            <div className="grid grid-cols-4 gap-4">
              {[
                { label: "Association", value: 2, color: "green" },
                { label: "Authentication", value: 100, color: "green" },
                { label: "DHCP", value: 100, color: "green" },
                { label: "DNS", value: 100, color: "green" },
              ].map((item, i) => (
                <div key={i} className="text-center">
                  <div className={`mb-2 text-2xl font-bold text-${item.color}-500`}>
                    {item.value}%
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-gray-700">
                    <div
                      className={`h-full bg-${item.color}-500`}
                      style={{ width: `${item.value}%` }}
                    />
                  </div>
                  <div className="mt-1 text-xs text-gray-400">{item.label}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Channel Graph */}
          <div className="mt-6 h-32 rounded-lg bg-[#1E293B]">
            <div className="flex h-full items-end justify-between p-4">
              {Array(13)
                .fill(0)
                .map((_, i) => (
                  <div
                    key={i}
                    className={`w-8 ${i === 5 || i === 6 ? "bg-green-500" : "bg-gray-700"}`}
                    style={{ height: `${Math.random() * 60 + 20}%` }}
                  />
                ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
