"use client";

import { Search, ZoomIn, ZoomOut, Maximize2, Plus, Minus } from "lucide-react";

export function TopologyView() {
  const devices = [
    { name: "Proxmox VE 6 65:cc", x: 200, y: 300, type: "server", vendor: "Proxmox" },
    { name: "UNAS-Pro 12:26", x: 350, y: 300, type: "nas", vendor: "ODROID" },
    { name: "Linksys EA6350 2a:72", x: 500, y: 300, type: "router", vendor: "Linksys" },
    { name: "mycrosoft 3e:98", x: 650, y: 300, type: "desktop", vendor: "Microsoft" },
    { name: "Meross Smart Wi-Fi Roll...", x: 800, y: 300, type: "iot", vendor: "Meross" },
    { name: "MycoComp 2a:70", x: 950, y: 300, type: "laptop", vendor: "ASUS" },
    { name: "BLACK U7 Pro XGS", x: 1100, y: 300, type: "ap", vendor: "Ubiquiti" },
    { name: "84:2b:2b:46:13:e6", x: 1250, y: 300, type: "device", vendor: "Dell" },
    { name: "WHITE U7 Pro XGS", x: 1400, y: 300, type: "ap", vendor: "Ubiquiti" },
    { name: "ubuntu-cursor 11:93", x: 1550, y: 300, type: "server", vendor: "Fedora" },
  ];

  return (
    <div className="flex h-full flex-col">
      {/* Top Bar */}
      <div className="flex items-center gap-4 border-b border-gray-800 bg-[#1E293B] px-6 py-4">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            className="h-4 w-4 rounded border-gray-600 bg-gray-700"
            defaultChecked
          />
          <span>Show Internet Traffic</span>
        </label>
        <button className="ml-auto rounded-lg p-2 hover:bg-gray-700">
          <ZoomOut className="h-4 w-4" />
        </button>
        <button className="rounded-lg p-2 hover:bg-gray-700">
          <Maximize2 className="h-4 w-4" />
        </button>
        <button className="rounded-lg p-2 hover:bg-gray-700">
          <Plus className="h-4 w-4" />
        </button>
        <button className="rounded-lg p-2 hover:bg-gray-700">
          <Minus className="h-4 w-4" />
        </button>
      </div>

      {/* Main Canvas */}
      <div className="relative flex-1 bg-[#0F172A]">
        {/* Internet Node at top */}
        <div className="absolute left-1/2 top-20 -translate-x-1/2 text-center">
          <div className="mb-2 flex h-16 w-16 items-center justify-center rounded-full bg-blue-500/20">
            <svg className="h-10 w-10 text-blue-500" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
            </svg>
          </div>
          <div className="text-xs font-medium">Wyverd Fiber</div>
        </div>

        {/* Dotted line from internet to gateway */}
        <svg className="absolute left-0 top-0 h-full w-full">
          <line
            x1="50%"
            y1="120"
            x2="50%"
            y2="220"
            stroke="#3B82F6"
            strokeWidth="2"
            strokeDasharray="5,5"
          />
        </svg>

        {/* Gateway Node */}
        <div className="absolute left-1/2 top-60 -translate-x-1/2 text-center">
          <div className="mb-2 flex h-20 w-32 items-center justify-center rounded-lg bg-[#1E293B]">
            <svg className="h-12 w-20 text-gray-400" fill="currentColor" viewBox="0 0 100 40">
              <rect x="5" y="8" width="90" height="24" rx="2" fill="#374151" />
              <circle cx="85" cy="20" r="2" fill="#10B981" />
              <circle cx="80" cy="20" r="2" fill="#10B981" />
            </svg>
          </div>
          <div className="text-xs font-medium">Dream Machine Pro Max</div>
          <div className="text-xs text-cyan-500">↓ 153 Kbps</div>
          <div className="text-xs text-purple-500">↑ 136 Kbps</div>
        </div>

        {/* Horizontal line for devices */}
        <svg className="absolute left-0 top-0 h-full w-full">
          <line
            x1="10%"
            y1="400"
            x2="90%"
            y2="400"
            stroke="#3B82F6"
            strokeWidth="2"
            strokeDasharray="5,5"
          />
          <line
            x1="50%"
            y1="340"
            x2="50%"
            y2="400"
            stroke="#3B82F6"
            strokeWidth="2"
            strokeDasharray="5,5"
          />
        </svg>

        {/* Devices */}
        {devices.map((device, i) => (
          <div
            key={i}
            className="absolute text-center"
            style={{ left: `${(i + 1) * 9}%`, top: "450px" }}
          >
            <svg className="absolute left-1/2 -top-12 h-12 w-0.5 -translate-x-1/2">
              <line
                x1="1"
                y1="0"
                x2="1"
                y2="48"
                stroke="#3B82F6"
                strokeWidth="2"
                strokeDasharray="3,3"
              />
            </svg>
            <div className="mb-2 flex h-12 w-12 items-center justify-center rounded-lg bg-gray-700">
              {device.type === "ap" ? (
                <div className="h-8 w-8 rounded-full bg-white" />
              ) : device.type === "laptop" ? (
                <svg className="h-8 w-8 text-gray-400" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M20 18c1.1 0 1.99-.9 1.99-2L22 6c0-1.1-.9-2-2-2H4c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2H0v2h24v-2h-4zM4 6h16v10H4V6z" />
                </svg>
              ) : (
                <div className="h-6 w-6 rounded bg-gray-600" />
              )}
            </div>
            <div className="max-w-[80px] truncate text-[10px] font-medium">{device.name}</div>
            {i % 3 === 0 && (
              <>
                <div className="text-[9px] text-cyan-500">↓ {Math.floor(Math.random() * 50)} bps</div>
                <div className="text-[9px] text-purple-500">↑ {Math.floor(Math.random() * 30)} bps</div>
              </>
            )}
          </div>
        ))}

        {/* Bottom Controls */}
        <div className="absolute bottom-4 left-1/2 flex -translate-x-1/2 gap-2 rounded-lg bg-[#1E293B] p-2">
          <button className="rounded-lg p-2 hover:bg-gray-700">
            <ZoomIn className="h-4 w-4" />
          </button>
          <button className="rounded-lg p-2 hover:bg-gray-700">
            <ZoomOut className="h-4 w-4" />
          </button>
          <button className="rounded-lg p-2 hover:bg-gray-700">
            <Maximize2 className="h-4 w-4" />
          </button>
          <button className="rounded-lg p-2 hover:bg-gray-700">
            <Plus className="h-4 w-4 text-blue-500" />
          </button>
        </div>
      </div>
    </div>
  );
}
