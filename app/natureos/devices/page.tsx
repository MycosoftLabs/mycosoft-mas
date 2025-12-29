"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  Monitor,
  ArrowLeft,
  RefreshCw,
  Wifi,
  Server,
  HardDrive,
  Router,
  Cpu,
  ExternalLink,
} from "lucide-react";
import { MycoBrainDeviceManager } from "@/components/mycobrain-device-manager";

interface NetworkDevice {
  name: string;
  model: string;
  mac: string;
  ip: string;
  status: string;
  device_type: string;
}

interface NetworkClient {
  name: string;
  mac: string;
  ip: string;
  network: string;
  is_wired: boolean;
  signal: number;
}

interface NetworkData {
  devices: NetworkDevice[];
  clients: NetworkClient[];
  health: {
    status: string;
    latency: number;
    download: number;
    upload: number;
    clients_online: number;
    devices_online: number;
  };
  source: string;
}

const getDeviceIcon = (type: string) => {
  switch (type) {
    case "gateway":
      return Router;
    case "switch":
      return Server;
    case "access_point":
      return Wifi;
    case "storage":
      return HardDrive;
    case "server":
      return Server;
    case "mycobrain":
      return Cpu;
    default:
      return Monitor;
  }
};

export default function DevicesPage() {
  const [networkData, setNetworkData] = useState<NetworkData | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"devices" | "clients" | "mycobrain">("devices");

  const fetchData = async () => {
    try {
      const res = await fetch("/api/network");
      if (res.ok) {
        setNetworkData(await res.json());
      }
    } catch (error) {
      console.error("Error fetching network data:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-white">
      {/* Header */}
      <header className="border-b border-gray-700/50 bg-gray-900/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/natureos" className="p-2 hover:bg-gray-800 rounded-lg transition-colors">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-purple-500/20">
                <Monitor className="w-6 h-6 text-purple-400" />
              </div>
              <div>
                <h1 className="text-xl font-bold">Devices</h1>
                <p className="text-xs text-gray-400">Network Device Management</p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className={`px-3 py-1 rounded-full text-xs ${
              networkData?.source === "live" ? "bg-green-500/20 text-green-400" : "bg-yellow-500/20 text-yellow-400"
            }`}>
              {networkData?.source === "live" ? "Live Data" : "Mock Data"}
            </span>
            <button
              onClick={fetchData}
              className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
              title="Refresh"
            >
              <RefreshCw className={`w-5 h-5 ${loading ? "animate-spin" : ""}`} />
            </button>
            <a
              href="https://unifi.ui.com"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg text-sm font-medium"
            >
              <ExternalLink className="w-4 h-4" />
              UniFi Console
            </a>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="p-4 rounded-xl bg-gray-800/50 border border-gray-700/50">
            <div className="text-sm text-gray-400">Devices Online</div>
            <div className="text-2xl font-bold text-green-400">
              {networkData?.health?.devices_online || networkData?.devices?.length || 0}
            </div>
          </div>
          <div className="p-4 rounded-xl bg-gray-800/50 border border-gray-700/50">
            <div className="text-sm text-gray-400">Clients Connected</div>
            <div className="text-2xl font-bold text-blue-400">
              {networkData?.health?.clients_online || networkData?.clients?.length || 0}
            </div>
          </div>
          <div className="p-4 rounded-xl bg-gray-800/50 border border-gray-700/50">
            <div className="text-sm text-gray-400">Latency</div>
            <div className="text-2xl font-bold text-cyan-400">
              {networkData?.health?.latency || 0}ms
            </div>
          </div>
          <div className="p-4 rounded-xl bg-gray-800/50 border border-gray-700/50">
            <div className="text-sm text-gray-400">Status</div>
            <div className={`text-2xl font-bold capitalize ${
              networkData?.health?.status === "healthy" ? "text-green-400" : "text-yellow-400"
            }`}>
              {networkData?.health?.status || "Unknown"}
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setActiveTab("devices")}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === "devices"
                ? "bg-purple-600 text-white"
                : "bg-gray-800 text-gray-400 hover:text-white"
            }`}
          >
            Network Devices ({networkData?.devices?.length || 0})
          </button>
          <button
            onClick={() => setActiveTab("clients")}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === "clients"
                ? "bg-purple-600 text-white"
                : "bg-gray-800 text-gray-400 hover:text-white"
            }`}
          >
            Clients ({networkData?.clients?.length || 0})
          </button>
          <button
            onClick={() => setActiveTab("mycobrain")}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === "mycobrain"
                ? "bg-purple-600 text-white"
                : "bg-gray-800 text-gray-400 hover:text-white"
            }`}
          >
            MycoBrain Devices
          </button>
        </div>

        {/* Device/Client List */}
        {activeTab === "mycobrain" ? (
          <MycoBrainDeviceManager />
        ) : (
        <div className="rounded-xl bg-gray-800/50 border border-gray-700/50 overflow-hidden">
          {activeTab === "devices" ? (
            <div className="divide-y divide-gray-700/50">
              {loading ? (
                <div className="p-8 text-center text-gray-500">Loading devices...</div>
              ) : networkData?.devices?.length === 0 ? (
                <div className="p-8 text-center text-gray-500">No devices found</div>
              ) : (
                networkData?.devices?.map((device) => {
                  const Icon = getDeviceIcon(device.device_type);
                  return (
                    <div
                      key={device.mac}
                      className="p-4 hover:bg-gray-800/50 transition-colors flex items-center justify-between"
                    >
                      <div className="flex items-center gap-4">
                        <div className={`p-3 rounded-lg ${
                          device.status === "online" ? "bg-green-500/20" : "bg-gray-700/50"
                        }`}>
                          <Icon className={`w-6 h-6 ${
                            device.status === "online" ? "text-green-400" : "text-gray-500"
                          }`} />
                        </div>
                        <div>
                          <div className="font-medium">{device.name}</div>
                          <div className="text-sm text-gray-500">{device.model}</div>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-6">
                        <div className="text-right">
                          <div className="text-sm">{device.ip}</div>
                          <div className="text-xs text-gray-500 font-mono">{device.mac}</div>
                        </div>
                        <div className={`px-3 py-1 rounded-full text-xs ${
                          device.status === "online"
                            ? "bg-green-500/20 text-green-400"
                            : "bg-gray-700 text-gray-400"
                        }`}>
                          {device.status}
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          ) : (
            <div className="divide-y divide-gray-700/50">
              {loading ? (
                <div className="p-8 text-center text-gray-500">Loading clients...</div>
              ) : networkData?.clients?.length === 0 ? (
                <div className="p-8 text-center text-gray-500">No clients found</div>
              ) : (
                networkData?.clients?.map((client) => (
                  <div
                    key={client.mac}
                    className="p-4 hover:bg-gray-800/50 transition-colors flex items-center justify-between"
                  >
                    <div className="flex items-center gap-4">
                      <div className="p-3 rounded-lg bg-blue-500/20">
                        {client.is_wired ? (
                          <Server className="w-6 h-6 text-blue-400" />
                        ) : (
                          <Wifi className="w-6 h-6 text-blue-400" />
                        )}
                      </div>
                      <div>
                        <div className="font-medium">{client.name}</div>
                        <div className="text-sm text-gray-500">
                          {client.is_wired ? "Wired" : `Wireless (${client.signal}dBm)`} • {client.network}
                        </div>
                      </div>
                    </div>
                    
                    <div className="text-right">
                      <div className="text-sm">{client.ip}</div>
                      <div className="text-xs text-gray-500 font-mono">{client.mac}</div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
        )}
      </main>
    </div>
  );
}
