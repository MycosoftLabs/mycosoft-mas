"use client";

import {
  LayoutDashboard,
  Network,
  Radio,
  Users,
  HardDrive,
  Activity,
  FileText,
  Settings,
  Wifi,
} from "lucide-react";

export function Sidebar() {
  const navItems = [
    { icon: LayoutDashboard, active: true },
    { icon: Network, active: false },
    { icon: Radio, active: false },
    { icon: Users, active: false },
    { icon: HardDrive, active: false },
    { icon: Wifi, active: false },
    { icon: Activity, active: false },
    { icon: FileText, active: false },
    { icon: Settings, active: false },
  ];

  return (
    <div className="flex w-72 flex-col border-r border-gray-800 bg-[#1E293B]">
      {/* Top Navigation Icons */}
      <div className="flex items-center gap-2 border-b border-gray-800 p-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#0F172A]">
          <svg viewBox="0 0 24 24" className="h-6 w-6 fill-white">
            <path d="M12 2L2 7v10c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-10-5z" />
          </svg>
        </div>
        <div className="flex-1 text-xs text-gray-400">8:36 PM EDT</div>
      </div>

      {/* Device Image */}
      <div className="border-b border-gray-800 p-6">
        <div className="mb-4 rounded-lg bg-[#0F172A] p-4">
          <svg viewBox="0 0 200 80" className="h-20 w-full">
            <rect x="20" y="20" width="160" height="40" rx="4" fill="#374151" />
            <rect x="25" y="25" width="150" height="30" rx="2" fill="#1F2937" />
            <circle cx="165" cy="40" r="3" fill="#10B981" />
            <circle cx="175" cy="40" r="3" fill="#10B981" />
            <rect x="30" y="32" width="80" height="2" fill="#4B5563" />
            <rect x="30" y="38" width="60" height="2" fill="#4B5563" />
            <rect x="30" y="44" width="70" height="2" fill="#4B5563" />
          </svg>
        </div>

        <div className="space-y-2">
          <div className="font-semibold">Keval UDM-SE</div>
          <div className="text-xs text-gray-400">UniFi OS 3.2.12</div>
          <div className="flex gap-2">
            <button className="text-xs text-blue-500 hover:underline">
              View Release Notes
            </button>
            <span className="text-xs text-gray-400">|</span>
            <button className="text-xs text-blue-500 hover:underline">
              Submit Support Ticket
            </button>
          </div>
        </div>
      </div>

      {/* System Info */}
      <div className="flex-1 overflow-auto p-6">
        <div className="space-y-4">
          <div>
            <div className="text-xs text-gray-400">WAN IP (Port 10)</div>
            <div className="text-sm">192.168.1.1</div>
          </div>

          <div>
            <div className="text-xs text-gray-400">Gateway IP</div>
            <div className="text-sm">10.0.0.1</div>
          </div>

          <div>
            <div className="text-xs text-gray-400">System Uptime</div>
            <div className="text-sm">2w 3d 15h 21m</div>
          </div>

          <div className="border-t border-gray-800 pt-4">
            <div className="mb-2 flex items-center justify-between">
              <div className="text-xs text-gray-400">Internet</div>
              <div className="flex items-center gap-1">
                <div className="h-2 w-2 rounded-full bg-blue-500" />
                <div className="text-xs text-blue-500">Spectrum</div>
              </div>
            </div>
            <div className="mb-2">
              <div className="text-xs text-gray-400">Uptime</div>
              <div className="text-sm text-green-500">100%</div>
            </div>
            <div className="mb-2">
              <div className="text-xs text-gray-400">Activity</div>
              <div className="flex items-center gap-2 text-sm">
                <span className="text-cyan-500">↓ 1,901 Mbps</span>
                <span className="text-purple-500">↑ 1,211 Mbps</span>
              </div>
            </div>
            <div className="flex gap-2 text-xs">
              <div className="flex items-center gap-1">
                <div className="h-3 w-3 bg-yellow-500" />
                49 ms
              </div>
              <div className="flex items-center gap-1">
                <svg viewBox="0 0 16 16" className="h-3 w-3 fill-red-500">
                  <circle cx="8" cy="8" r="6" />
                </svg>
                26 ms
              </div>
              <div className="flex items-center gap-1">
                <svg viewBox="0 0 16 16" className="h-3 w-3 fill-orange-500">
                  <path d="M8 2L2 14h12L8 2z" />
                </svg>
                49 ms
              </div>
            </div>
          </div>

          <div className="border-t border-gray-800 pt-4">
            <div className="mb-2 text-xs font-semibold">Internet Health</div>
            <div className="mb-1 flex items-center justify-between text-xs">
              <span className="text-gray-400">-12h</span>
              <span className="text-gray-400">Now</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-gray-700">
              <div className="h-full bg-green-500" style={{ width: "100%" }} />
            </div>
            <div className="mt-2 flex items-center justify-between">
              <button className="text-xs text-blue-500 hover:underline">See All</button>
            </div>
          </div>

          <div className="border-t border-gray-800 pt-4">
            <div className="mb-2 text-xs font-semibold">Speed Test</div>
            <div className="text-xs text-gray-400">Runs Daily at 07:00 AM</div>
            <div className="mt-2">
              <button className="text-xs text-blue-500 hover:underline">Run Now</button>
            </div>
            <div className="mt-3 space-y-1">
              <div className="text-xs text-gray-400">Last Speed Test</div>
              <div className="text-xs">Sep 21, 7:00 AM</div>
              <div className="flex gap-2 text-sm">
                <span className="text-cyan-500">1,672 Mbps</span>
                <span className="text-purple-500">1,40.0 Mbps</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Icons */}
      <div className="border-t border-gray-800 p-4">
        <div className="flex flex-col gap-2">
          {navItems.map((item, i) => (
            <button
              key={i}
              className={`flex h-10 w-10 items-center justify-center rounded-lg transition-colors ${
                item.active
                  ? "bg-blue-500 text-white"
                  : "text-gray-400 hover:bg-gray-700 hover:text-white"
              }`}
            >
              <item.icon className="h-5 w-5" />
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
