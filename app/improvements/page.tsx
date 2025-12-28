"use client";

import { useState, useEffect } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Sparkles,
  Wrench,
  Activity,
  TrendingUp,
  RefreshCw,
} from "lucide-react";
import { DashboardShell } from "@/components/dashboard/shell";
import { DashboardHeader } from "@/components/dashboard/header";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface Improvement {
  id: string;
  category: "workflow" | "agent" | "system" | "performance";
  priority: "critical" | "high" | "medium" | "low";
  title: string;
  description?: string;
  workflow?: string;
  node?: string;
  errorCount?: number;
  autoFixable: boolean;
  suggestedFix: string;
  efficiency: number;
  estimatedImpact: string;
  status: "pending" | "in_progress" | "fixed" | "dismissed";
  createdAt: string;
  fixedAt?: string;
}

interface SystemEfficiency {
  overall: number;
  workflows: number;
  agents: number;
  memory: number;
  network: number;
  database: number;
}

interface ImprovementStats {
  total: number;
  pending: number;
  inProgress: number;
  fixed: number;
  autoFixable: number;
  critical: number;
  high: number;
}

export default function ImprovementsPage() {
  const [improvements, setImprovements] = useState<Improvement[]>([]);
  const [efficiency, setEfficiency] = useState<SystemEfficiency | null>(null);
  const [stats, setStats] = useState<ImprovementStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const response = await fetch("/api/system/improvements");
      const data = await response.json();
      if (data.success) {
        setImprovements(data.data.improvements);
        setEfficiency(data.data.efficiency);
        setStats(data.data.stats);
        setLastUpdated(data.data.lastUpdated);
      }
    } catch (error) {
      console.error("Error fetching improvements:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const triggerAutoFix = async (improvementId: string) => {
    try {
      const response = await fetch("/api/system/improvements", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "trigger_auto_fix", improvementId }),
      });
      const data = await response.json();
      if (data.success) {
        fetchData();
      }
    } catch (error) {
      console.error("Error triggering auto-fix:", error);
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case "critical":
        return "bg-red-500/20 text-red-400 border-red-500/50";
      case "high":
        return "bg-orange-500/20 text-orange-400 border-orange-500/50";
      case "medium":
        return "bg-yellow-500/20 text-yellow-400 border-yellow-500/50";
      default:
        return "bg-gray-500/20 text-gray-400 border-gray-500/50";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "fixed":
        return <CheckCircle2 className="h-4 w-4 text-green-400" />;
      case "in_progress":
        return <Clock className="h-4 w-4 text-yellow-400 animate-pulse" />;
      default:
        return <AlertCircle className="h-4 w-4 text-gray-400" />;
    }
  };

  const getEfficiencyColor = (value: number) => {
    if (value >= 90) return "text-green-400";
    if (value >= 70) return "text-yellow-400";
    return "text-red-400";
  };

  return (
    <DashboardShell>
      <DashboardHeader
        heading="System Improvements"
        text="Monitor system efficiency and manage automated improvements"
      >
        <Button onClick={fetchData} disabled={loading} className="gap-2">
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </DashboardHeader>

      {/* Efficiency Cards */}
      {efficiency && (
        <div className="mt-6 grid gap-4 md:grid-cols-6">
          <Card className="rounded-xl bg-[#1e293b] border border-gray-700 p-4 text-center">
            <Activity className={`h-6 w-6 mx-auto mb-2 ${getEfficiencyColor(efficiency.overall)}`} />
            <p className={`text-2xl font-bold ${getEfficiencyColor(efficiency.overall)}`}>
              {efficiency.overall}%
            </p>
            <p className="text-xs text-gray-400">Overall</p>
          </Card>
          <Card className="rounded-xl bg-[#1e293b] border border-gray-700 p-4 text-center">
            <TrendingUp className={`h-6 w-6 mx-auto mb-2 ${getEfficiencyColor(efficiency.workflows)}`} />
            <p className={`text-2xl font-bold ${getEfficiencyColor(efficiency.workflows)}`}>
              {efficiency.workflows}%
            </p>
            <p className="text-xs text-gray-400">Workflows</p>
          </Card>
          <Card className="rounded-xl bg-[#1e293b] border border-gray-700 p-4 text-center">
            <Sparkles className={`h-6 w-6 mx-auto mb-2 ${getEfficiencyColor(efficiency.agents)}`} />
            <p className={`text-2xl font-bold ${getEfficiencyColor(efficiency.agents)}`}>
              {efficiency.agents}%
            </p>
            <p className="text-xs text-gray-400">Agents</p>
          </Card>
          <Card className="rounded-xl bg-[#1e293b] border border-gray-700 p-4 text-center">
            <p className={`text-2xl font-bold ${getEfficiencyColor(efficiency.memory)}`}>
              {efficiency.memory}%
            </p>
            <p className="text-xs text-gray-400">Memory</p>
          </Card>
          <Card className="rounded-xl bg-[#1e293b] border border-gray-700 p-4 text-center">
            <p className={`text-2xl font-bold ${getEfficiencyColor(efficiency.network)}`}>
              {efficiency.network}%
            </p>
            <p className="text-xs text-gray-400">Network</p>
          </Card>
          <Card className="rounded-xl bg-[#1e293b] border border-gray-700 p-4 text-center">
            <p className={`text-2xl font-bold ${getEfficiencyColor(efficiency.database)}`}>
              {efficiency.database}%
            </p>
            <p className="text-xs text-gray-400">Database</p>
          </Card>
        </div>
      )}

      {/* Stats Summary */}
      {stats && (
        <div className="mt-6 grid gap-4 md:grid-cols-4">
          <Card className="rounded-xl bg-gradient-to-br from-purple-900/30 to-purple-700/10 border border-purple-500/30 p-4">
            <p className="text-3xl font-bold text-white">{stats.total}</p>
            <p className="text-sm text-purple-300">Total Improvements</p>
          </Card>
          <Card className="rounded-xl bg-gradient-to-br from-yellow-900/30 to-yellow-700/10 border border-yellow-500/30 p-4">
            <p className="text-3xl font-bold text-white">{stats.pending}</p>
            <p className="text-sm text-yellow-300">Pending</p>
          </Card>
          <Card className="rounded-xl bg-gradient-to-br from-green-900/30 to-green-700/10 border border-green-500/30 p-4">
            <p className="text-3xl font-bold text-white">{stats.autoFixable}</p>
            <p className="text-sm text-green-300">Auto-Fixable</p>
          </Card>
          <Card className="rounded-xl bg-gradient-to-br from-red-900/30 to-red-700/10 border border-red-500/30 p-4">
            <p className="text-3xl font-bold text-white">{stats.critical + stats.high}</p>
            <p className="text-sm text-red-300">High Priority</p>
          </Card>
        </div>
      )}

      {/* Improvements Table */}
      <div className="mt-6">
        <Card className="rounded-xl bg-[#1e293b] border border-gray-700 overflow-hidden">
          <div className="p-4 border-b border-gray-700">
            <h2 className="text-lg font-semibold text-white">Improvement Queue</h2>
            {lastUpdated && (
              <p className="text-xs text-gray-400">
                Last updated: {new Date(lastUpdated).toLocaleTimeString()}
              </p>
            )}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-[#0f172a]">
                <tr>
                  <th className="px-4 py-3 text-left text-gray-400 font-medium">Status</th>
                  <th className="px-4 py-3 text-left text-gray-400 font-medium">Priority</th>
                  <th className="px-4 py-3 text-left text-gray-400 font-medium">Title</th>
                  <th className="px-4 py-3 text-left text-gray-400 font-medium">Category</th>
                  <th className="px-4 py-3 text-left text-gray-400 font-medium">Efficiency</th>
                  <th className="px-4 py-3 text-left text-gray-400 font-medium">Impact</th>
                  <th className="px-4 py-3 text-left text-gray-400 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {improvements.map((imp) => (
                  <tr key={imp.id} className="border-t border-gray-700/50 hover:bg-gray-800/50">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {getStatusIcon(imp.status)}
                        <span className="text-gray-300 capitalize">{imp.status.replace("_", " ")}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <Badge className={getPriorityColor(imp.priority)}>{imp.priority}</Badge>
                    </td>
                    <td className="px-4 py-3">
                      <p className="text-white font-medium">{imp.title}</p>
                      {imp.workflow && (
                        <p className="text-xs text-gray-400">
                          {imp.workflow} {imp.node && `→ ${imp.node}`}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-gray-300 capitalize">{imp.category}</span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-2 bg-gray-700 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${
                              imp.efficiency >= 80
                                ? "bg-green-500"
                                : imp.efficiency >= 60
                                ? "bg-yellow-500"
                                : "bg-red-500"
                            }`}
                            style={{ width: `${imp.efficiency}%` }}
                          />
                        </div>
                        <span className="text-gray-400 text-xs">{imp.efficiency}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-gray-300 text-xs">{imp.estimatedImpact}</span>
                    </td>
                    <td className="px-4 py-3">
                      {imp.autoFixable && imp.status === "pending" && (
                        <Button
                          size="sm"
                          variant="secondary"
                          className="gap-1 text-xs"
                          onClick={() => triggerAutoFix(imp.id)}
                        >
                          <Wrench className="h-3 w-3" />
                          Auto-Fix
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
                {improvements.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
                      {loading ? "Loading improvements..." : "No improvements found"}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </DashboardShell>
  );
}

