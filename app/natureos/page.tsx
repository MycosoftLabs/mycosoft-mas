"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  Activity,
  Network,
  Terminal,
  Database,
  HardDrive,
  Monitor,
  Plug,
  Workflow,
  Cpu,
  Thermometer,
  Droplets,
  Gauge,
  Globe,
  Grid3x3,
} from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EarthSimulatorContainer } from "@/components/earth-simulator/earth-simulator-container";
import { LiveDataFeed } from "@/components/natureos/live-data-feed";
import { MYCAInterface } from "@/components/natureos/myca-interface";
import { MycoBrainWidget } from "@/components/natureos/mycobrain-widget";

interface SystemStats {
  cpu?: { usage: number; cores: number; model: string };
  memory?: { used: number; total: number; usedPercent: number };
  os?: { hostname: string; uptime: number; platform: string };
  docker?: { running: number; stopped: number };
  network?: { totalRx: number; totalTx: number };
}

interface N8NStatus {
  local: { connected: boolean; workflows: unknown[]; activeWorkflows: number; totalWorkflows: number };
  cloud: { connected: boolean; workflows: unknown[]; activeWorkflows: number; totalWorkflows: number };
}

const navItems = [
  { href: "/apps/earth-simulator", icon: Globe, label: "Earth Simulator", description: "Interactive 3D globe with mycelium mapping" },
  { href: "/apps", icon: Grid3x3, label: "All Apps", description: "Browse all applications" },
  { href: "/natureos/workflows", icon: Workflow, label: "Workflows", description: "n8n workflow automation" },
  { href: "/natureos/shell", icon: Terminal, label: "Shell", description: "Terminal access" },
  { href: "/natureos/api", icon: Network, label: "API Explorer", description: "Browse all APIs" },
  { href: "/natureos/devices", icon: Monitor, label: "Devices", description: "Network devices" },
  { href: "/natureos/storage", icon: HardDrive, label: "Storage", description: "NAS and cloud storage" },
  { href: "/natureos/monitoring", icon: Activity, label: "Monitoring", description: "System health" },
  { href: "/natureos/integrations", icon: Plug, label: "Integrations", description: "Manage connections" },
];

function formatBytes(bytes: number): string {
  const gb = bytes / (1024 * 1024 * 1024);
  if (gb >= 1) return `${gb.toFixed(1)} GB`;
  const mb = bytes / (1024 * 1024);
  return `${mb.toFixed(1)} MB`;
}

function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  return `${days}d ${hours}h`;
}

export default function NatureOSPage() {
  const [systemStats, setSystemStats] = useState<SystemStats | null>(null);
  const [n8nStatus, setN8NStatus] = useState<N8NStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("overview");

  useEffect(() => {
    async function fetchData() {
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
      } catch (error) {
        console.error("Error fetching data:", error);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-white">
      {/* Header */}
      <header className="border-b border-gray-700/50 bg-gray-900/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center">
              <svg viewBox="0 0 24 24" className="w-6 h-6 fill-white">
                <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 4.44-2.54M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-4.44-2.54" />
              </svg>
            </div>
            <div>
              <h1 className="text-xl font-bold">NatureOS</h1>
              <p className="text-xs text-gray-400">MYCOSOFT Operating Environment</p>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <Link href="/myca/dashboard" className="text-sm text-gray-400 hover:text-white transition-colors">
              MYCA Dashboard
            </Link>
            <div className="h-3 w-3 rounded-full bg-green-500 animate-pulse" />
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        {/* Page Header */}
        <div className="mb-6">
          <h2 className="text-2xl font-bold mb-2">NatureOS Dashboard</h2>
          <p className="text-gray-400">Monitor and manage your fungal intelligence network</p>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-3 mb-6">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="simulator">Earth Simulator</TabsTrigger>
            <TabsTrigger value="petri-dish">Petri Dish Simulator</TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6">
            {/* System Status Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* CPU */}
              <div className="p-4 rounded-xl bg-gray-800/50 border border-gray-700/50 backdrop-blur-sm">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2 rounded-lg bg-blue-500/20">
                    <Cpu className="w-5 h-5 text-blue-400" />
                  </div>
                  <span className="text-sm text-gray-400">CPU Usage</span>
                </div>
                <div className="text-2xl font-bold">
                  {loading ? "..." : `${systemStats?.cpu?.usage?.toFixed(1) || 0}%`}
                </div>
                <div className="mt-2 h-2 bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 transition-all"
                    style={{ width: `${systemStats?.cpu?.usage || 0}%` }}
                  />
                </div>
              </div>

              {/* Memory */}
              <div className="p-4 rounded-xl bg-gray-800/50 border border-gray-700/50 backdrop-blur-sm">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2 rounded-lg bg-purple-500/20">
                    <Gauge className="w-5 h-5 text-purple-400" />
                  </div>
                  <span className="text-sm text-gray-400">Memory</span>
                </div>
                <div className="text-2xl font-bold">
                  {loading ? "..." : `${systemStats?.memory?.usedPercent?.toFixed(0) || 0}%`}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {formatBytes(systemStats?.memory?.used || 0)} / {formatBytes(systemStats?.memory?.total || 0)}
                </div>
              </div>

              {/* Docker */}
              <div className="p-4 rounded-xl bg-gray-800/50 border border-gray-700/50 backdrop-blur-sm">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2 rounded-lg bg-cyan-500/20">
                    <Database className="w-5 h-5 text-cyan-400" />
                  </div>
                  <span className="text-sm text-gray-400">Docker</span>
                </div>
                <div className="text-2xl font-bold text-green-400">
                  {loading ? "..." : systemStats?.docker?.running || 0}
                </div>
                <div className="text-xs text-gray-500">containers running</div>
              </div>

              {/* n8n Workflows */}
              <div className="p-4 rounded-xl bg-gray-800/50 border border-gray-700/50 backdrop-blur-sm">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2 rounded-lg bg-orange-500/20">
                    <Workflow className="w-5 h-5 text-orange-400" />
                  </div>
                  <span className="text-sm text-gray-400">Workflows</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className={`h-2 w-2 rounded-full ${n8nStatus?.local.connected ? "bg-green-500" : "bg-red-500"}`} />
                  <span className="text-sm">
                    {n8nStatus?.local.activeWorkflows || 0} active
                  </span>
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {n8nStatus?.local.totalWorkflows || 0} total workflows
                </div>
              </div>
            </div>

            {/* Navigation Grid */}
            <div>
              <h3 className="text-lg font-semibold mb-4">System Modules</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {navItems.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className="group p-6 rounded-xl bg-gray-800/50 border border-gray-700/50 hover:border-green-500/50 hover:bg-gray-800 transition-all hover:scale-[1.02]"
                  >
                    <div className="flex items-center gap-3 mb-3">
                      <div className="p-3 rounded-lg bg-gray-700/50 group-hover:bg-green-500/20 transition-colors">
                        <item.icon className="w-6 h-6 text-gray-400 group-hover:text-green-400 transition-colors" />
                      </div>
                    </div>
                    <h3 className="font-semibold text-white group-hover:text-green-400 transition-colors">
                      {item.label}
                    </h3>
                    <p className="text-sm text-gray-500 mt-1">{item.description}</p>
                  </Link>
                ))}
              </div>
            </div>

            {/* NatureOS Components Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Live Data Feed */}
              <div className="bg-white rounded-xl p-6">
                <LiveDataFeed />
              </div>

              {/* MYCA Interface */}
              <div className="bg-white rounded-xl p-6">
                <MYCAInterface maxHeight={600} />
              </div>
            </div>

            {/* MycoBrain Widget */}
            <div>
              <div className="bg-white rounded-xl p-6">
                <MycoBrainWidget />
              </div>
            </div>
          </TabsContent>

          {/* Earth Simulator Tab */}
          <TabsContent value="simulator" className="space-y-6">
            <div className="h-[calc(100vh-300px)] min-h-[600px]">
              <EarthSimulatorContainer />
            </div>
          </TabsContent>

          {/* Petri Dish Simulator Tab */}
          <TabsContent value="petri-dish" className="space-y-6">
            <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-6">
              <h3 className="text-xl font-bold mb-4">Petri Dish Simulator</h3>
              <p className="text-gray-400 mb-4">
                The Petri Dish Simulator allows you to simulate fungal growth patterns and conditions.
              </p>
              <Link
                href="/apps/petri-dish-sim"
                className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg transition-colors"
              >
                Open Petri Dish Simulator
              </Link>
            </div>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
