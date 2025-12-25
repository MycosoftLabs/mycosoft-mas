"use client";

import { Search } from "lucide-react";

const flows = [
  {
    source: "MycoComp 2a:70",
    destination: "status-ui-com-8473b888e-9b16-47b1-96fe-...",
    service: "HTTPS",
    risk: "low",
    dir: "↑",
    in: "Default",
    out: "Internet 1",
    action: "Allow",
    datetime: "Dec 16, 5:43:51.792 PM",
  },
  {
    source: "MycoComp 2a:70",
    destination: "optimizationguide.googleapis.com",
    service: "HTTPS",
    risk: "low",
    dir: "↑",
    in: "Default",
    out: "Internet 1",
    action: "Allow",
    datetime: "Dec 16, 5:43:51.523 PM",
  },
  {
    source: "MycoComp 2a:70",
    destination: "cloudaccess.svc.ui.com (99.84.41.14)",
    service: "HTTPS",
    risk: "low",
    dir: "↑",
    in: "Default",
    out: "Internet 1",
    action: "Allow",
    datetime: "Dec 16, 5:43:51.392 PM",
  },
];

export function FlowsView() {
  return (
    <div className="flex h-full flex-col">
      {/* Top Bar */}
      <div className="flex items-center gap-4 border-b border-gray-800 bg-[#1E293B] px-6 py-4">
        <button className="flex items-center gap-2 rounded-lg bg-blue-500 px-4 py-2 text-sm font-medium">
          Flows
        </button>
        <button className="flex items-center gap-2 rounded-lg px-4 py-2 text-sm text-gray-400 hover:bg-gray-700">
          CyberSecure Enhanced
          <span className="rounded bg-blue-500 px-2 py-0.5 text-xs">Activate</span>
        </button>
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search"
            className="w-full rounded-lg bg-[#0F172A] py-2 pl-10 pr-4 text-sm text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar */}
        <div className="w-64 border-r border-gray-800 bg-[#1E293B] p-4">
          <div className="mb-6">
            <div className="mb-2 text-xs font-semibold text-gray-400">Risk</div>
            <div className="space-y-2">
              {[
                { label: "Low", count: 50896, color: "green" },
                { label: "Suspicious", count: 0, color: "yellow" },
                { label: "Concerning", count: 0, color: "red" },
              ].map((item) => (
                <label key={item.label} className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded border-gray-600 bg-gray-700"
                  />
                  <div className={`h-2 w-2 rounded-full bg-${item.color}-500`} />
                  <span className="flex-1 text-sm">{item.label}</span>
                  <span className="text-xs text-gray-400">{item.count}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="mb-6">
            <div className="mb-2 text-xs font-semibold text-gray-400">Direction</div>
            <div className="flex gap-2">
              <button className="rounded-lg bg-gray-700 p-2">↓</button>
              <button className="rounded-lg bg-gray-700 p-2">↑</button>
              <button className="rounded-lg bg-gray-700 p-2">↔</button>
            </div>
          </div>

          <div className="mb-6">
            <button className="w-full rounded-lg bg-[#0F172A] px-3 py-2 text-left text-sm">
              Source
            </button>
          </div>

          <div className="mb-6">
            <button className="w-full rounded-lg bg-[#0F172A] px-3 py-2 text-left text-sm">
              Source Zone
            </button>
          </div>

          <div className="mb-6">
            <button className="w-full rounded-lg bg-[#0F172A] px-3 py-2 text-left text-sm">
              Source Network
            </button>
          </div>

          <div className="space-y-2">
            <button className="text-xs text-blue-500 hover:underline">Clear Filters</button>
            <button className="text-xs text-blue-500 hover:underline">Download</button>
            <button className="text-xs text-blue-500 hover:underline">Customize Columns</button>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex flex-1 flex-col overflow-hidden">
          {/* Summary Stats */}
          <div className="border-b border-gray-800 bg-[#1E293B] p-4">
            <div className="mb-4 text-sm font-semibold">Flow Summary</div>
            <div className="grid grid-cols-4 gap-4 text-sm">
              <div>
                <div className="text-xs text-gray-400">Total</div>
                <div className="text-xl font-bold">50,896</div>
              </div>
              <div>
                <div className="text-xs text-red-400">Low</div>
                <div className="text-xl font-bold">50,896 (100%)</div>
              </div>
              <div>
                <div className="text-xs text-gray-400">Suspicious</div>
                <div className="text-xl font-bold">0 (0%)</div>
              </div>
              <div>
                <div className="text-xs text-gray-400">Concerning</div>
                <div className="text-xl font-bold">0 (0%)</div>
              </div>
            </div>
          </div>

          {/* Top Sections */}
          <div className="border-b border-gray-800 bg-[#1E293B] p-4">
            <div className="grid grid-cols-3 gap-4">
              <div>
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-xs font-semibold">Top Destinations</span>
                  <button className="text-xs text-blue-500 hover:underline">See More</button>
                </div>
                <div className="space-y-1 text-xs">
                  <div className="flex justify-between">
                    <span className="truncate">optimizationguide-pa.googleapis.com</span>
                    <span className="text-gray-400">4,688</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="truncate">1.0.0.1</span>
                    <span className="text-gray-400">4,318</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="truncate">dns.google</span>
                    <span className="text-gray-400">4,300</span>
                  </div>
                </div>
              </div>

              <div>
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-xs font-semibold">Top Clients</span>
                  <button className="text-xs text-blue-500 hover:underline">See More</button>
                </div>
                <div className="space-y-1 text-xs">
                  <div className="flex justify-between">
                    <span>MycoComp 2a:70</span>
                    <span className="text-gray-400">36,776</span>
                  </div>
                  <div className="flex justify-between">
                    <span>UNAS-Pro 12:26</span>
                    <span className="text-gray-400">1,534</span>
                  </div>
                  <div className="flex justify-between">
                    <span>ubuntu-cursor 11:93</span>
                    <span className="text-gray-400">645</span>
                  </div>
                </div>
              </div>

              <div>
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-xs font-semibold">Top Apps</span>
                  <button className="text-xs text-blue-500 hover:underline">See More</button>
                </div>
                <div className="space-y-1 text-xs">
                  <div className="flex justify-between">
                    <span>SSL/TLS</span>
                    <span className="text-gray-400">3.18 GB</span>
                  </div>
                  <div className="flex justify-between">
                    <span>STUN</span>
                    <span className="text-gray-400">1.15 GB</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Docker</span>
                    <span className="text-gray-400">188 MB</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Flows Table */}
          <div className="flex-1 overflow-auto">
            <table className="w-full text-left text-xs">
              <thead className="sticky top-0 bg-[#1E293B] text-gray-400">
                <tr>
                  <th className="px-4 py-3">Source</th>
                  <th className="px-4 py-3">Destination</th>
                  <th className="px-4 py-3">Service</th>
                  <th className="px-4 py-3">Risk</th>
                  <th className="px-4 py-3">Dir.</th>
                  <th className="px-4 py-3">In</th>
                  <th className="px-4 py-3">Out</th>
                  <th className="px-4 py-3">Action</th>
                  <th className="px-4 py-3">Date / Time</th>
                </tr>
              </thead>
              <tbody>
                {flows.map((flow, i) => (
                  <tr key={i} className="border-b border-gray-800 hover:bg-[#1E293B]">
                    <td className="px-4 py-3">{flow.source}</td>
                    <td className="max-w-xs truncate px-4 py-3">{flow.destination}</td>
                    <td className="px-4 py-3">{flow.service}</td>
                    <td className="px-4 py-3">
                      <div className="h-2 w-2 rounded-full bg-green-500" />
                    </td>
                    <td className="px-4 py-3">{flow.dir}</td>
                    <td className="px-4 py-3">{flow.in}</td>
                    <td className="px-4 py-3">{flow.out}</td>
                    <td className="px-4 py-3">{flow.action}</td>
                    <td className="px-4 py-3 text-gray-400">{flow.datetime}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="border-t border-gray-800 bg-[#1E293B] p-4">
            <div className="flex items-center justify-between text-xs">
              <div>1-100 of 10000+ Flows</div>
              <div className="flex gap-2">
                <button className="rounded bg-gray-700 px-3 py-1">Previous</button>
                <button className="rounded bg-gray-700 px-3 py-1">Next</button>
                <select className="rounded bg-gray-700 px-3 py-1">
                  <option>100</option>
                  <option>500</option>
                  <option>1000</option>
                </select>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
