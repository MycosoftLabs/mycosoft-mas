"use client";

import { Search, ChevronRight, Wifi, Network as NetworkIcon, Globe, Shield } from "lucide-react";

export function SettingsView() {
  return (
    <div className="flex h-full flex-col">
      {/* Top Bar */}
      <div className="border-b border-gray-800 bg-[#1E293B] px-6 py-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search Settings"
            className="w-full rounded-lg bg-[#0F172A] py-2 pl-10 pr-4 text-sm text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar */}
        <div className="w-64 border-r border-gray-800 bg-[#1E293B] p-4">
          <div className="space-y-2">
            <button className="flex w-full items-center gap-3 rounded-lg bg-blue-500 px-3 py-2 text-sm font-medium">
              <NetworkIcon className="h-4 w-4" />
              Overview
            </button>
            <button className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-gray-400 hover:bg-gray-700">
              <Wifi className="h-4 w-4" />
              WiFi
            </button>
            <button className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-gray-400 hover:bg-gray-700">
              <NetworkIcon className="h-4 w-4" />
              Networks
            </button>
            <button className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-gray-400 hover:bg-gray-700">
              <Globe className="h-4 w-4" />
              Internet
            </button>
            <button className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-gray-400 hover:bg-gray-700">
              <Shield className="h-4 w-4" />
              VPN
            </button>
          </div>

          <div className="mt-8 space-y-2">
            <div className="text-xs font-semibold text-gray-400">UDM Pro Max</div>
            <button className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-gray-400 hover:bg-gray-700">
              Control Plane
            </button>
            <button className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-gray-400 hover:bg-gray-700">
              Identity
            </button>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 overflow-auto bg-[#0F172A] p-6">
          {/* WiFi Section */}
          <div className="mb-4 rounded-lg bg-[#1E293B]">
            <button className="flex w-full items-center justify-between p-4 hover:bg-gray-700/50">
              <div className="flex items-center gap-3">
                <Wifi className="h-5 w-5 text-blue-500" />
                <span className="font-semibold">WiFi</span>
              </div>
              <ChevronRight className="h-5 w-5 text-gray-400" />
            </button>
            <div className="border-t border-gray-800 p-4">
              <table className="w-full text-sm">
                <thead className="text-left text-xs text-gray-400">
                  <tr>
                    <th className="pb-3">Name</th>
                    <th className="pb-3">Network</th>
                    <th className="pb-3">Broadcasting APs</th>
                    <th className="pb-3">WiFi Band</th>
                    <th className="pb-3">Clients</th>
                    <th className="pb-3">Security</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td className="py-3">
                      <div className="flex items-center gap-2">
                        <div className="h-2 w-2 rounded-full bg-green-500" />
                        Myca
                      </div>
                    </td>
                    <td className="py-3">Native Network</td>
                    <td className="py-3">All APs</td>
                    <td className="py-3">2.4 GHz 5 GHz</td>
                    <td className="py-3">-</td>
                    <td className="py-3">WPA2</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* Networks Section */}
          <div className="mb-4 rounded-lg bg-[#1E293B]">
            <button className="flex w-full items-center justify-between p-4 hover:bg-gray-700/50">
              <div className="flex items-center gap-3">
                <NetworkIcon className="h-5 w-5 text-blue-500" />
                <span className="font-semibold">Networks</span>
                <button className="ml-4 text-xs text-blue-500 hover:underline">DHCP Manager</button>
              </div>
              <ChevronRight className="h-5 w-5 text-gray-400" />
            </button>
            <div className="border-t border-gray-800 p-4">
              <table className="w-full text-sm">
                <thead className="text-left text-xs text-gray-400">
                  <tr>
                    <th className="pb-3">Name</th>
                    <th className="pb-3">Router</th>
                    <th className="pb-3">Subnet</th>
                    <th className="pb-3">IPv6 Subnet</th>
                    <th className="pb-3">DHCP</th>
                    <th className="pb-3">IP Leases</th>
                    <th className="pb-3">Available</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td className="py-3">
                      <div className="flex items-center gap-2">
                        <div className="h-2 w-2 rounded-full bg-green-500" />
                        Default
                      </div>
                    </td>
                    <td className="py-3">Dream Machine Pro Max</td>
                    <td className="py-3">192.168.8.0/24</td>
                    <td className="py-3">-</td>
                    <td className="py-3">Server</td>
                    <td className="py-3 text-blue-500">10/249</td>
                    <td className="py-3">238</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* Internet Section */}
          <div className="mb-4 rounded-lg bg-[#1E293B]">
            <button className="flex w-full items-center justify-between p-4 hover:bg-gray-700/50">
              <div className="flex items-center gap-3">
                <Globe className="h-5 w-5 text-blue-500" />
                <span className="font-semibold">Internet</span>
              </div>
              <ChevronRight className="h-5 w-5 text-gray-400" />
            </button>
            <div className="border-t border-gray-800 p-4">
              <table className="w-full text-sm">
                <thead className="text-left text-xs text-gray-400">
                  <tr>
                    <th className="pb-3">Name</th>
                    <th className="pb-3">Interface</th>
                    <th className="pb-3">ISP</th>
                    <th className="pb-3">IPv4 Address</th>
                    <th className="pb-3">IPv6 Address</th>
                    <th className="pb-3">Port</th>
                    <th className="pb-3">Uptime</th>
                    <th className="pb-3">Peak Util.</th>
                    <th className="pb-3">Latency</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td className="py-3">
                      <div className="flex items-center gap-2">
                        <div className="h-2 w-2 rounded-full bg-green-500" />
                        Internet 1
                      </div>
                    </td>
                    <td className="py-3">WAN1</td>
                    <td className="py-3 flex items-center gap-2">
                      <svg className="h-4 w-4 text-blue-500" fill="currentColor" viewBox="0 0 24 24">
                        <circle cx="12" cy="12" r="8" />
                      </svg>
                      Wyverd Fiber
                    </td>
                    <td className="py-3">192.168.1.141</td>
                    <td className="py-3">-</td>
                    <td className="py-3">9</td>
                    <td className="py-3">100%</td>
                    <td className="py-3">
                      <span className="text-cyan-500">↓ 0%</span>{" "}
                      <span className="text-purple-500">↑ 0%</span>
                    </td>
                    <td className="py-3">5 ms</td>
                  </tr>
                  <tr className="opacity-50">
                    <td className="py-3">
                      <div className="flex items-center gap-2">
                        <div className="h-2 w-2 rounded-full bg-gray-500" />
                        Internet 2
                      </div>
                    </td>
                    <td className="py-3">WAN2</td>
                    <td className="py-3">-</td>
                    <td className="py-3">-</td>
                    <td className="py-3">-</td>
                    <td className="py-3">10</td>
                    <td className="py-3">0%</td>
                    <td className="py-3">-</td>
                    <td className="py-3">-</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* VPN Server */}
          <div className="mb-4 rounded-lg bg-[#1E293B]">
            <button className="flex w-full items-center justify-between p-4 hover:bg-gray-700/50">
              <div className="flex items-center gap-3">
                <Shield className="h-5 w-5 text-blue-500" />
                <span className="font-semibold">VPN Server</span>
              </div>
              <ChevronRight className="h-5 w-5 text-gray-400" />
            </button>
          </div>

          {/* Additional Sections */}
          {[
            "Site-to-Site VPN",
            "VPN Client",
            "Port Forwarding",
            "Policy-Based Routing",
            "Content Filter",
          ].map((section, i) => (
            <div key={i} className="mb-4 rounded-lg bg-[#1E293B]">
              <button className="flex w-full items-center justify-between p-4 hover:bg-gray-700/50">
                <div className="flex items-center gap-3">
                  <div className="h-5 w-5 rounded bg-blue-500/20" />
                  <span className="font-semibold">{section}</span>
                </div>
                <ChevronRight className="h-5 w-5 text-gray-400" />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
