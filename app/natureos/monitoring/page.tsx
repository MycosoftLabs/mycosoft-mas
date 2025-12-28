"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  Activity,
  ArrowLeft,
  RefreshCw,
  Cpu,
  HardDrive,
  Wifi,
  Server,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
} from "lucide-react";

interface SystemStats {
  cpu?: { usage: number; cores: number; model: string };
  memory?: { used: number; total: number; usedPercent: number };
  disk?: { used: number; total: number; usedPercent: number };
  docker?: {
    running: number;
    stopped: number;
    containers: Array<{ name: string; state: string; image: string }>;
  };
  network?: {
    totalRx: number;
    totalTx: number;
    interfaces: Array<{ name: string; ip: string; rx: number; tx: number }>;
  };
  os?: { hostname: string; uptime: number; platform: string };
}

interface N8NStatus {
  local: { connected: boolean; workflows: number; activeWorkflows: number };
  cloud: { connected: boolean; workflows: number; activeWorkflows: number };
}

interface ServiceHealth {
  name: string;
  url: string;
  status: "healthy" | "degraded" | "down" | "unknown";
  latency?: number;
}

function formatBytes(bytes: number): string {
  const gb = bytes / (1024 * 1024 * 1024);
  if (gb >= 1) return `${gb.toFixed(1)} GB`;
  const mb = bytes / (1024 * 1024);
  return `${mb.toFixed(1)} MB`;
}

function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${days}d ${hours}h ${minutes}m`;
}

export default function MonitoringPage() {
  const [systemStats, setSystemStats] = useState<SystemStats | null>(null);
  const [n8nStatus, setN8NStatus] = useState<N8NStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  const fetchData = async () => {
    setLoading(true);
    try {
      const [sysRes, n8nRes] = await Promise.all([
        fetch("/api/system").catch(() => null),
        fetch("/api/n8n").catch(() => null),
      ]);

      if (sysRes?.ok) {
        setSystemStats(await sysRes.json());
      }
      if (n8nRes?.ok) {
        setN8NStatus(await n8nRes.json());
      }
      setLastUpdate(new Date());
    } catch (error) {
      console.error("Error fetching data:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const services: ServiceHealth[] = [
    {
      name: "MYCA Dashboard",
      url: "http://localhost:3100",
      status: "healthy",
      latency: 12,
    },
    {
      name: "n8n Local",
      url: "http://localhost:5678",
      status: n8nStatus?.local.connected ? "healthy" : "down",
      latency: n8nStatus?.local.connected ? 45 : undefined,
    },
    {
      name: "n8n Cloud",
      url: "https://mycosoft.app.n8n.cloud",
      status: n8nStatus?.cloud.connected ? "healthy" : "degraded",
      latency: n8nStatus?.cloud.connected ? 120 : undefined,
    },
    {
      name: "MAS Backend",
      url: "http://localhost:8001",
      status: "unknown",
    },
  ];

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "healthy":
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case "degraded":
        return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
      case "down":
        return <XCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Clock className="w-5 h-5 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "healthy":
        return "text-green-400";
      case "degraded":
        return "text-yellow-400";
      case "down":
        return "text-red-400";
      default:
        return "text-gray-400";
    }
  };

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
              <div className="p-2 rounded-lg bg-green-500/20">
                <Activity className="w-6 h-6 text-green-400" />
              </div>
              <div>
                <h1 className="text-xl font-bold">Monitoring</h1>
                <p className="text-xs text-gray-400">System Health Dashboard</p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <span className="text-xs text-gray-400">
              Last updated: {lastUpdate.toLocaleTimeString()}
            </span>
            <button
              onClick={fetchData}
              className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
              title="Refresh"
            >
              <RefreshCw className={`w-5 h-5 ${loading ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
        {/* Resource Gauges */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          {/* CPU */}
          <div className="rounded-xl bg-gray-800/50 border border-gray-700/50 p-4">
            <div className="flex items-center gap-3 mb-3">
              <Cpu className="w-5 h-5 text-blue-400" />
              <span className="text-sm text-gray-400">CPU</span>
            </div>
            <div className="text-3xl font-bold mb-2">
              {systemStats?.cpu?.usage?.toFixed(0) || 0}%
            </div>
            <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all ${
                  (systemStats?.cpu?.usage || 0) > 80
                    ? "bg-red-500"
                    : (systemStats?.cpu?.usage || 0) > 60
                    ? "bg-yellow-500"
                    : "bg-blue-500"
                }`}
                style={{ width: `${systemStats?.cpu?.usage || 0}%` }}
              />
            </div>
            <div className="text-xs text-gray-500 mt-2">{systemStats?.cpu?.cores || 0} cores</div>
          </div>

          {/* Memory */}
          <div className="rounded-xl bg-gray-800/50 border border-gray-700/50 p-4">
            <div className="flex items-center gap-3 mb-3">
              <Server className="w-5 h-5 text-purple-400" />
              <span className="text-sm text-gray-400">Memory</span>
            </div>
            <div className="text-3xl font-bold mb-2">
              {systemStats?.memory?.usedPercent?.toFixed(0) || 0}%
            </div>
            <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all ${
                  (systemStats?.memory?.usedPercent || 0) > 90
                    ? "bg-red-500"
                    : (systemStats?.memory?.usedPercent || 0) > 70
                    ? "bg-yellow-500"
                    : "bg-purple-500"
                }`}
                style={{ width: `${systemStats?.memory?.usedPercent || 0}%` }}
              />
            </div>
            <div className="text-xs text-gray-500 mt-2">
              {formatBytes(systemStats?.memory?.used || 0)} / {formatBytes(systemStats?.memory?.total || 0)}
            </div>
          </div>

          {/* Disk */}
          <div className="rounded-xl bg-gray-800/50 border border-gray-700/50 p-4">
            <div className="flex items-center gap-3 mb-3">
              <HardDrive className="w-5 h-5 text-cyan-400" />
              <span className="text-sm text-gray-400">Disk</span>
            </div>
            <div className="text-3xl font-bold mb-2">
              {systemStats?.disk?.usedPercent?.toFixed(0) || 0}%
            </div>
            <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all ${
                  (systemStats?.disk?.usedPercent || 0) > 90
                    ? "bg-red-500"
                    : (systemStats?.disk?.usedPercent || 0) > 70
                    ? "bg-yellow-500"
                    : "bg-cyan-500"
                }`}
                style={{ width: `${systemStats?.disk?.usedPercent || 0}%` }}
              />
            </div>
            <div className="text-xs text-gray-500 mt-2">
              {formatBytes(systemStats?.disk?.used || 0)} / {formatBytes(systemStats?.disk?.total || 0)}
            </div>
          </div>

          {/* Uptime */}
          <div className="rounded-xl bg-gray-800/50 border border-gray-700/50 p-4">
            <div className="flex items-center gap-3 mb-3">
              <Clock className="w-5 h-5 text-green-400" />
              <span className="text-sm text-gray-400">Uptime</span>
            </div>
            <div className="text-2xl font-bold mb-2">
              {formatUptime(systemStats?.os?.uptime || 0)}
            </div>
            <div className="text-xs text-gray-500 mt-2">{systemStats?.os?.hostname || "Unknown"}</div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Service Health */}
          <div className="rounded-xl bg-gray-800/50 border border-gray-700/50 overflow-hidden">
            <div className="p-4 border-b border-gray-700/50">
              <h2 className="font-semibold">Service Health</h2>
            </div>
            <div className="divide-y divide-gray-700/50">
              {services.map((service) => (
                <div
                  key={service.name}
                  className="p-4 flex items-center justify-between hover:bg-gray-800/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    {getStatusIcon(service.status)}
                    <div>
                      <div className="font-medium">{service.name}</div>
                      <div className="text-xs text-gray-500">{service.url}</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className={`font-medium capitalize ${getStatusColor(service.status)}`}>
                      {service.status}
                    </div>
                    {service.latency && (
                      <div className="text-xs text-gray-500">{service.latency}ms</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Docker Containers */}
          <div className="rounded-xl bg-gray-800/50 border border-gray-700/50 overflow-hidden">
            <div className="p-4 border-b border-gray-700/50 flex items-center justify-between">
              <h2 className="font-semibold">Docker Containers</h2>
              <div className="flex items-center gap-2 text-sm">
                <span className="text-green-400">{systemStats?.docker?.running || 0} running</span>
                <span className="text-gray-500">•</span>
                <span className="text-gray-400">{systemStats?.docker?.stopped || 0} stopped</span>
              </div>
            </div>
            <div className="divide-y divide-gray-700/50">
              {systemStats?.docker?.containers?.length === 0 ? (
                <div className="p-4 text-center text-gray-500">No containers found</div>
              ) : (
                systemStats?.docker?.containers?.map((container) => (
                  <div
                    key={container.name}
                    className="p-4 flex items-center justify-between hover:bg-gray-800/50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-2 h-2 rounded-full ${
                          container.state === "running" ? "bg-green-500" : "bg-gray-500"
                        }`}
                      />
                      <div>
                        <div className="font-medium">{container.name}</div>
                        <div className="text-xs text-gray-500 truncate max-w-[200px]">
                          {container.image}
                        </div>
                      </div>
                    </div>
                    <span
                      className={`px-2 py-1 rounded text-xs ${
                        container.state === "running"
                          ? "bg-green-500/20 text-green-400"
                          : "bg-gray-700 text-gray-400"
                      }`}
                    >
                      {container.state}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
