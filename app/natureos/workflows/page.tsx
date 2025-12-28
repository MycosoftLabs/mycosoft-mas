"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  Workflow,
  Play,
  Pause,
  RefreshCw,
  ExternalLink,
  CheckCircle,
  XCircle,
  Clock,
  ArrowLeft,
} from "lucide-react";

interface N8NWorkflow {
  id: string;
  name: string;
  active: boolean;
  createdAt: string;
  updatedAt: string;
}

interface N8NExecution {
  id: string;
  workflowId: string;
  status: string;
  startedAt: string;
  stoppedAt?: string;
}

interface N8NStatus {
  local: {
    connected: boolean;
    url: string;
    workflows: N8NWorkflow[];
    executions: N8NExecution[];
  };
  cloud: {
    connected: boolean;
    url: string;
    workflows: N8NWorkflow[];
    executions: N8NExecution[];
  };
}

export default function WorkflowsPage() {
  const [n8nStatus, setN8NStatus] = useState<N8NStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"local" | "cloud">("local");

  const fetchData = async () => {
    try {
      const res = await fetch("/api/n8n");
      if (res.ok) {
        setN8NStatus(await res.json());
      }
    } catch (error) {
      console.error("Error fetching n8n status:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  const currentInstance = n8nStatus?.[activeTab];
  const workflows = currentInstance?.workflows || [];
  const executions = currentInstance?.executions || [];

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "success":
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case "error":
        return <XCircle className="w-4 h-4 text-red-500" />;
      default:
        return <Clock className="w-4 h-4 text-yellow-500" />;
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
              <div className="p-2 rounded-lg bg-orange-500/20">
                <Workflow className="w-6 h-6 text-orange-400" />
              </div>
              <div>
                <h1 className="text-xl font-bold">Workflows</h1>
                <p className="text-xs text-gray-400">n8n Workflow Automation</p>
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
            <a
              href={activeTab === "cloud" ? "https://mycosoft.app.n8n.cloud" : "http://localhost:5678"}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 rounded-lg text-sm font-medium"
            >
              <ExternalLink className="w-4 h-4" />
              Open n8n
            </a>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        {/* Instance Tabs */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setActiveTab("local")}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
              activeTab === "local"
                ? "bg-orange-600 text-white"
                : "bg-gray-800 text-gray-400 hover:text-white"
            }`}
          >
            <div className={`w-2 h-2 rounded-full ${n8nStatus?.local.connected ? "bg-green-500" : "bg-red-500"}`} />
            Local
          </button>
          <button
            onClick={() => setActiveTab("cloud")}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
              activeTab === "cloud"
                ? "bg-orange-600 text-white"
                : "bg-gray-800 text-gray-400 hover:text-white"
            }`}
          >
            <div className={`w-2 h-2 rounded-full ${n8nStatus?.cloud.connected ? "bg-green-500" : "bg-yellow-500"}`} />
            Cloud
          </button>
        </div>

        {/* Connection Status */}
        {!currentInstance?.connected && (
          <div className="mb-6 p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/30 text-yellow-400">
            <p className="text-sm">
              {activeTab === "cloud"
                ? "Cloud instance requires API key. Set N8N_API_KEY in your environment."
                : "Local n8n instance not connected. Make sure n8n is running on localhost:5678."}
            </p>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Workflows List */}
          <div className="lg:col-span-2">
            <div className="rounded-xl bg-gray-800/50 border border-gray-700/50 overflow-hidden">
              <div className="p-4 border-b border-gray-700/50 flex items-center justify-between">
                <h2 className="font-semibold">Workflows</h2>
                <span className="text-sm text-gray-400">{workflows.length} total</span>
              </div>
              
              <div className="divide-y divide-gray-700/50">
                {loading ? (
                  <div className="p-8 text-center text-gray-500">Loading workflows...</div>
                ) : workflows.length === 0 ? (
                  <div className="p-8 text-center text-gray-500">No workflows found</div>
                ) : (
                  workflows.map((workflow) => (
                    <div
                      key={workflow.id}
                      className="p-4 hover:bg-gray-800/50 transition-colors flex items-center justify-between"
                    >
                      <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-lg ${workflow.active ? "bg-green-500/20" : "bg-gray-700/50"}`}>
                          <Workflow className={`w-4 h-4 ${workflow.active ? "text-green-400" : "text-gray-500"}`} />
                        </div>
                        <div>
                          <div className="font-medium">{workflow.name}</div>
                          <div className="text-xs text-gray-500">
                            Updated {new Date(workflow.updatedAt).toLocaleDateString()}
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-1 rounded text-xs ${
                          workflow.active
                            ? "bg-green-500/20 text-green-400"
                            : "bg-gray-700 text-gray-400"
                        }`}>
                          {workflow.active ? "Active" : "Inactive"}
                        </span>
                        <a
                          href={`${currentInstance?.url}/workflow/${workflow.id}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
                        >
                          <ExternalLink className="w-4 h-4" />
                        </a>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Recent Executions */}
          <div>
            <div className="rounded-xl bg-gray-800/50 border border-gray-700/50 overflow-hidden">
              <div className="p-4 border-b border-gray-700/50">
                <h2 className="font-semibold">Recent Executions</h2>
              </div>
              
              <div className="divide-y divide-gray-700/50">
                {executions.length === 0 ? (
                  <div className="p-4 text-center text-gray-500 text-sm">No recent executions</div>
                ) : (
                  executions.slice(0, 10).map((execution) => (
                    <div key={execution.id} className="p-3 flex items-center gap-3">
                      {getStatusIcon(execution.status)}
                      <div className="flex-1 min-w-0">
                        <div className="text-sm truncate">
                          {workflows.find((w) => w.id === execution.workflowId)?.name || execution.workflowId}
                        </div>
                        <div className="text-xs text-gray-500">
                          {new Date(execution.startedAt).toLocaleString()}
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
