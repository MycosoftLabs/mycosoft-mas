"use client";

import { X, Wifi, Activity, HardDrive, Network } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from "recharts";
import type { Device } from "@/types";

interface DeviceModalProps {
  device: Device;
  onClose: () => void;
}

export function DeviceModal({ device, onClose }: DeviceModalProps) {
  const chartData = Array.from({ length: 24 }, (_, i) => ({
    time: `${i}:00`,
    traffic: Math.random() * 100,
  }));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="max-h-[90vh] w-full max-w-4xl overflow-auto rounded-lg bg-[#1E293B] shadow-2xl">
        {/* Header */}
        <div className="sticky top-0 flex items-center justify-between border-b border-gray-700 bg-[#1E293B] p-6">
          <div>
            <h2 className="text-2xl font-semibold text-white">{device.name}</h2>
            <p className="text-sm text-gray-400">{device.vendor}</p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-gray-400 hover:bg-gray-700 hover:text-white"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* Quick Stats */}
          <div className="mb-6 grid grid-cols-4 gap-4">
            <div className="rounded-lg bg-[#0F172A] p-4">
              <div className="mb-2 flex items-center gap-2 text-sm text-gray-400">
                <Network className="h-4 w-4" />
                IP Address
              </div>
              <div className="text-lg font-semibold">{device.ip}</div>
            </div>
            <div className="rounded-lg bg-[#0F172A] p-4">
              <div className="mb-2 flex items-center gap-2 text-sm text-gray-400">
                <HardDrive className="h-4 w-4" />
                MAC Address
              </div>
              <div className="text-lg font-semibold">{device.mac}</div>
            </div>
            <div className="rounded-lg bg-[#0F172A] p-4">
              <div className="mb-2 flex items-center gap-2 text-sm text-gray-400">
                <Activity className="h-4 w-4" />
                Uptime
              </div>
              <div className="text-lg font-semibold">{device.uptime}</div>
            </div>
            <div className="rounded-lg bg-[#0F172A] p-4">
              <div className="mb-2 flex items-center gap-2 text-sm text-gray-400">
                <Wifi className="h-4 w-4" />
                Experience
              </div>
              <div className="text-lg font-semibold text-green-500">{device.experience}</div>
            </div>
          </div>

          {/* Tabs */}
          <div className="mb-6 flex gap-2 border-b border-gray-700">
            <button className="border-b-2 border-blue-500 px-4 py-2 text-sm font-medium text-blue-500">
              Overview
            </button>
            <button className="px-4 py-2 text-sm text-gray-400 hover:text-white">
              Properties
            </button>
            <button className="px-4 py-2 text-sm text-gray-400 hover:text-white">
              Statistics
            </button>
            <button className="px-4 py-2 text-sm text-gray-400 hover:text-white">
              Settings
            </button>
          </div>

          {/* Traffic Chart */}
          <div className="mb-6">
            <h3 className="mb-4 text-lg font-semibold">Traffic Activity (24h)</h3>
            <div className="h-64 rounded-lg bg-[#0F172A] p-4">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="traffic" x1="0" y1="0" x2="0" y2="1">
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
                    fill="url(#traffic)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Device Details */}
          <div className="grid grid-cols-2 gap-6">
            <div className="rounded-lg bg-[#0F172A] p-4">
              <h3 className="mb-4 text-sm font-semibold">Network Information</h3>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Connection Type</span>
                  <span className="font-medium">{device.type}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Network</span>
                  <span className="font-medium">Default</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Speed</span>
                  <span className="font-medium text-cyan-500">1 Gbps</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Signal Strength</span>
                  <span className="font-medium text-green-500">Excellent</span>
                </div>
              </div>
            </div>

            <div className="rounded-lg bg-[#0F172A] p-4">
              <h3 className="mb-4 text-sm font-semibold">Usage Statistics</h3>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Data Downloaded</span>
                  <span className="font-medium text-cyan-500">45.2 GB</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Data Uploaded</span>
                  <span className="font-medium text-purple-500">12.8 GB</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Packets Sent</span>
                  <span className="font-medium">1.2M</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Packets Received</span>
                  <span className="font-medium">3.5M</span>
                </div>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="mt-6 flex gap-3">
            <button className="rounded-lg bg-blue-500 px-4 py-2 text-sm font-medium hover:bg-blue-600">
              Reconnect
            </button>
            <button className="rounded-lg bg-gray-700 px-4 py-2 text-sm font-medium hover:bg-gray-600">
              Block Device
            </button>
            <button className="rounded-lg bg-gray-700 px-4 py-2 text-sm font-medium hover:bg-gray-600">
              Forget Device
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
