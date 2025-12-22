"use client";

import { useState, useRef } from "react";
import { Search, ZoomIn, ZoomOut, Maximize2, Plus, Minus } from "lucide-react";

interface Device {
  id: string;
  name: string;
  x: number;
  y: number;
  type: string;
  vendor: string;
  status: "online" | "offline";
}

export function InteractiveTopologyView() {
  const [devices, setDevices] = useState<Device[]>([
    {
      id: "1",
      name: "Proxmox VE 6 65:cc",
      x: 100,
      y: 400,
      type: "server",
      vendor: "Proxmox",
      status: "online",
    },
    {
      id: "2",
      name: "UNAS-Pro 12:26",
      x: 250,
      y: 400,
      type: "nas",
      vendor: "ODROID",
      status: "online",
    },
    {
      id: "3",
      name: "Linksys EA6350",
      x: 400,
      y: 400,
      type: "router",
      vendor: "Linksys",
      status: "online",
    },
    {
      id: "4",
      name: "mycrosoft 3e:98",
      x: 550,
      y: 400,
      type: "desktop",
      vendor: "Microsoft",
      status: "online",
    },
    {
      id: "5",
      name: "MycoComp 2a:70",
      x: 700,
      y: 400,
      type: "laptop",
      vendor: "ASUS",
      status: "online",
    },
    {
      id: "6",
      name: "BLACK U7 Pro XGS",
      x: 850,
      y: 400,
      type: "ap",
      vendor: "Ubiquiti",
      status: "online",
    },
  ]);

  const [dragging, setDragging] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [selectedDevice, setSelectedDevice] = useState<string | null>(null);
  const canvasRef = useRef<HTMLDivElement>(null);

  const handleMouseDown = (e: React.MouseEvent, deviceId: string) => {
    e.preventDefault();
    const device = devices.find((d) => d.id === deviceId);
    if (!device) return;

    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;

    setDragging(deviceId);
    setDragOffset({
      x: (e.clientX - rect.left) / zoom - device.x,
      y: (e.clientY - rect.top) / zoom - device.y,
    });
    setSelectedDevice(deviceId);
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!dragging) return;

    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;

    const newX = (e.clientX - rect.left) / zoom - dragOffset.x;
    const newY = (e.clientY - rect.top) / zoom - dragOffset.y;

    setDevices((prev) =>
      prev.map((device) =>
        device.id === dragging ? { ...device, x: newX, y: newY } : device
      )
    );
  };

  const handleMouseUp = () => {
    setDragging(null);
  };

  const getDeviceIcon = (type: string) => {
    switch (type) {
      case "ap":
        return (
          <div className="h-10 w-10 rounded-full bg-white ring-2 ring-blue-500" />
        );
      case "laptop":
        return (
          <svg className="h-10 w-10 fill-gray-400" viewBox="0 0 24 24">
            <path d="M20 18c1.1 0 1.99-.9 1.99-2L22 6c0-1.1-.9-2-2-2H4c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2H0v2h24v-2h-4zM4 6h16v10H4V6z" />
          </svg>
        );
      case "server":
        return (
          <svg className="h-10 w-10 fill-gray-400" viewBox="0 0 24 24">
            <path d="M20 13H4c-.55 0-1 .45-1 1v6c0 .55.45 1 1 1h16c.55 0 1-.45 1-1v-6c0-.55-.45-1-1-1zM7 19c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zM20 3H4c-.55 0-1 .45-1 1v6c0 .55.45 1 1 1h16c.55 0 1-.45 1-1V4c0-.55-.45-1-1-1zM7 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2z" />
          </svg>
        );
      default:
        return <div className="h-8 w-8 rounded bg-gray-600" />;
    }
  };

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
        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={() => setZoom((z) => Math.max(0.5, z - 0.1))}
            className="rounded-lg p-2 hover:bg-gray-700"
          >
            <ZoomOut className="h-4 w-4" />
          </button>
          <span className="min-w-[60px] text-center text-sm">{Math.round(zoom * 100)}%</span>
          <button
            onClick={() => setZoom((z) => Math.min(2, z + 0.1))}
            className="rounded-lg p-2 hover:bg-gray-700"
          >
            <ZoomIn className="h-4 w-4" />
          </button>
          <button
            onClick={() => setZoom(1)}
            className="rounded-lg p-2 hover:bg-gray-700"
          >
            <Maximize2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Canvas */}
      <div
        ref={canvasRef}
        className="relative flex-1 overflow-hidden bg-[#0F172A]"
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <div style={{ transform: `scale(${zoom})`, transformOrigin: "0 0" }}>
          {/* Internet Node */}
          <div className="absolute left-1/2 top-20 -translate-x-1/2 text-center">
            <div className="mb-2 flex h-16 w-16 items-center justify-center rounded-full bg-blue-500/20">
              <svg className="h-10 w-10 text-blue-500" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
              </svg>
            </div>
            <div className="text-xs font-medium">Internet</div>
          </div>

          {/* Gateway Node */}
          <div className="absolute left-1/2 top-60 -translate-x-1/2 text-center">
            <div className="mb-2 flex h-20 w-32 items-center justify-center rounded-lg bg-[#1E293B] shadow-lg">
              <svg className="h-12 w-20 text-gray-400" fill="currentColor" viewBox="0 0 100 40">
                <rect x="5" y="8" width="90" height="24" rx="2" fill="#374151" />
                <circle cx="85" cy="20" r="2" fill="#10B981" />
                <circle cx="80" cy="20" r="2" fill="#10B981" />
              </svg>
            </div>
            <div className="text-xs font-medium">Dream Machine Pro Max</div>
          </div>

          {/* Connection Lines */}
          <svg className="absolute left-0 top-0 h-full w-full pointer-events-none">
            <line
              x1="50%"
              y1="120"
              x2="50%"
              y2="240"
              stroke="#3B82F6"
              strokeWidth="2"
              strokeDasharray="5,5"
            />
            {devices.map((device) => (
              <line
                key={device.id}
                x1="50%"
                y1="320"
                x2={device.x + 40}
                y2={device.y}
                stroke="#3B82F6"
                strokeWidth="2"
                strokeDasharray="3,3"
              />
            ))}
          </svg>

          {/* Draggable Devices */}
          {devices.map((device) => (
            <div
              key={device.id}
              className={`absolute cursor-move transition-shadow ${
                selectedDevice === device.id ? "ring-2 ring-blue-500" : ""
              } ${dragging === device.id ? "cursor-grabbing" : "cursor-grab"}`}
              style={{
                left: device.x,
                top: device.y,
                transform: "translate(-50%, -50%)",
              }}
              onMouseDown={(e) => handleMouseDown(e, device.id)}
            >
              <div
                className={`rounded-lg bg-[#1E293B] p-3 shadow-lg hover:shadow-xl ${
                  device.status === "online" ? "border-2 border-green-500" : "border-2 border-gray-600"
                }`}
              >
                <div className="mb-2 flex justify-center">{getDeviceIcon(device.type)}</div>
                <div className="max-w-[100px] truncate text-center text-xs font-medium">
                  {device.name}
                </div>
                <div className="mt-1 text-center text-[10px] text-gray-400">
                  {device.vendor}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Controls Hint */}
        <div className="absolute bottom-4 left-4 rounded-lg bg-[#1E293B] p-3 text-xs text-gray-400">
          <div className="mb-1 font-medium">Controls:</div>
          <div>• Drag devices to move them</div>
          <div>• Scroll to zoom</div>
          <div>• Click device to select</div>
        </div>
      </div>
    </div>
  );
}
