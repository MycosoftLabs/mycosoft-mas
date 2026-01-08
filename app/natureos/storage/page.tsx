"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  HardDrive,
  ArrowLeft,
  RefreshCw,
  FolderOpen,
  File,
  Cloud,
  Database,
  Upload,
} from "lucide-react";

interface DiskInfo {
  total: number;
  used: number;
  free: number;
  usedPercent: number;
}

interface SystemStats {
  disk?: DiskInfo;
}

function formatBytes(bytes: number): string {
  const gb = bytes / (1024 * 1024 * 1024);
  if (gb >= 1) return `${gb.toFixed(1)} GB`;
  const mb = bytes / (1024 * 1024);
  if (mb >= 1) return `${mb.toFixed(1)} MB`;
  return `${(bytes / 1024).toFixed(1)} KB`;
}

export default function StoragePage() {
  const [systemStats, setSystemStats] = useState<SystemStats | null>(null);
  const [loading, setLoading] = useState(true);

  const [storageData, setStorageData] = useState<any>(null);

  const fetchData = async () => {
    try {
      const [sysRes, storageRes] = await Promise.all([
        fetch("/api/system").catch(() => null),
        fetch("/api/natureos/storage").catch(() => null),
      ]);
      
      if (sysRes?.ok) {
        setSystemStats(await sysRes.json());
      }
      
      if (storageRes?.ok) {
        const data = await storageRes.json();
        setStorageData(data);
      }
    } catch (error) {
      console.error("Error fetching storage data:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  // Use real storage data if available, otherwise fallback to defaults
  const storageLocations = storageData?.mounts?.length > 0
    ? storageData.mounts.map((mount: any) => ({
        name: mount.path.split("/").pop() || mount.path,
        path: mount.path,
        icon: HardDrive,
        used: mount.used,
        total: mount.total,
        usedPercent: mount.usedPercent,
        description: `${mount.filesystem} filesystem`,
      }))
    : [
        {
          name: "MINDEX Database",
          path: "/data/mindex",
          icon: Database,
          used: 2.4 * 1024 * 1024 * 1024,
          total: 50 * 1024 * 1024 * 1024,
          description: "Fungal knowledge and research data",
        },
        {
          name: "Agent Data",
          path: "/data/agents",
          icon: FolderOpen,
          used: 512 * 1024 * 1024,
          total: 10 * 1024 * 1024 * 1024,
          description: "Agent states and configurations",
        },
      ];

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
              <div className="p-2 rounded-lg bg-cyan-500/20">
                <HardDrive className="w-6 h-6 text-cyan-400" />
              </div>
              <div>
                <h1 className="text-xl font-bold">Storage</h1>
                <p className="text-xs text-gray-400">NAS and Cloud Storage</p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
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
        {/* System Disk Overview */}
        <div className="mb-8">
          <h2 className="text-lg font-semibold mb-4">System Storage</h2>
          <div className="rounded-xl bg-gray-800/50 border border-gray-700/50 p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <HardDrive className="w-8 h-8 text-cyan-400" />
                <div>
                  <div className="font-medium">Primary Disk</div>
                  <div className="text-sm text-gray-400">System Drive</div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold">
                  {systemStats?.disk ? `${systemStats.disk.usedPercent.toFixed(0)}%` : "..."}
                </div>
                <div className="text-sm text-gray-400">used</div>
              </div>
            </div>
            
            <div className="h-4 bg-gray-700 rounded-full overflow-hidden mb-3">
              <div
                className={`h-full transition-all ${
                  (systemStats?.disk?.usedPercent || 0) > 90
                    ? "bg-red-500"
                    : (systemStats?.disk?.usedPercent || 0) > 70
                    ? "bg-yellow-500"
                    : "bg-gradient-to-r from-cyan-500 to-blue-500"
                }`}
                style={{ width: `${systemStats?.disk?.usedPercent || 0}%` }}
              />
            </div>
            
            <div className="flex justify-between text-sm text-gray-400">
              <span>{formatBytes(systemStats?.disk?.used || 0)} used</span>
              <span>{formatBytes(systemStats?.disk?.free || 0)} free</span>
              <span>{formatBytes(systemStats?.disk?.total || 0)} total</span>
            </div>
          </div>
        </div>

        {/* Storage Locations */}
        <h2 className="text-lg font-semibold mb-4">Storage Locations</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {storageLocations.map((location) => (
            <div
              key={location.path}
              className="rounded-xl bg-gray-800/50 border border-gray-700/50 p-4 hover:border-cyan-500/50 transition-colors"
            >
              <div className="flex items-start gap-4">
                <div className="p-3 rounded-lg bg-gray-700/50">
                  <location.icon className="w-6 h-6 text-cyan-400" />
                </div>
                <div className="flex-1">
                  <div className="font-medium">{location.name}</div>
                  <div className="text-xs text-gray-500 font-mono mb-2">{location.path}</div>
                  <div className="text-sm text-gray-400 mb-3">{location.description}</div>
                  
                  <div className="h-2 bg-gray-700 rounded-full overflow-hidden mb-2">
                    <div
                      className={`h-full transition-all ${
                        (location.usedPercent || (location.used / location.total) * 100) > 90
                          ? "bg-red-500"
                          : (location.usedPercent || (location.used / location.total) * 100) > 70
                          ? "bg-yellow-500"
                          : "bg-gradient-to-r from-cyan-500 to-blue-500"
                      }`}
                      style={{ width: `${location.usedPercent || (location.used / location.total) * 100}%` }}
                    />
                  </div>
                  
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>{formatBytes(location.used)}</span>
                    <span>{formatBytes(location.total)}</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Quick Actions */}
        <div className="mt-8">
          <h2 className="text-lg font-semibold mb-4">Quick Actions</h2>
          <div className="flex flex-wrap gap-3">
            <button className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm font-medium transition-colors">
              <Upload className="w-4 h-4" />
              Upload Files
            </button>
            <button className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm font-medium transition-colors">
              <Cloud className="w-4 h-4" />
              Sync to Cloud
            </button>
            <button className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm font-medium transition-colors">
              <Database className="w-4 h-4" />
              Backup Database
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
