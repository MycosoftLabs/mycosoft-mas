"use client";

import { useState, useEffect } from "react";
import { Sidebar } from "./Sidebar";
import { dataService } from "@/lib/data-service";
import type { Agent, NetworkStats, TopologyNode } from "@/types";
import { Navigation } from "./Navigation";
import { TrafficIdentification } from "./TrafficIdentification";
import { WiFiTechnology } from "./WiFiTechnology";
import { MostActiveClients } from "./MostActiveClients";
import { MostActiveAccessPoints } from "./MostActiveAccessPoints";
import { InternetActivity } from "./InternetActivity";
import { AgentTopologyView } from "./views/AgentTopologyView";
import { ClientsView } from "./views/ClientsView";
import { RadiosView } from "./views/RadiosView";
import { SettingsView } from "./views/SettingsView";
import { FlowsView } from "./views/FlowsView";
import { DevicesView } from "./views/DevicesView";
import { TrafficAnalysisView } from "./views/TrafficAnalysisView";
import { DeviceHealthView } from "./views/DeviceHealthView";
import { SecurityView } from "./views/SecurityView";
import { WorkflowStudioView } from "./views/WorkflowStudioView";
// 3D View disabled due to React Three Fiber version conflict - using enhanced 2D topology instead
// import dynamic from "next/dynamic";
// const Topology3DView = dynamic(() => import("./views/Topology3DView").then(mod => ({ default: mod.Topology3DView })), { ssr: false });
import { CustomizableDashboard } from "./CustomizableDashboard";
import { SearchBar } from "./SearchBar";
import { DeviceModal } from "./DeviceModal";
import { NotificationPanel } from "./NotificationPanel";
import { TalkToMYCA } from "./TalkToMYCA";
import { AgentCreator } from "./AgentCreator";
import { useTheme } from "@/lib/theme-provider";
import { ChevronRight, Sun, Moon, Mic, Activity, Menu, X, Plus } from "lucide-react";
import { Toaster } from "sonner";
import { MemoryHealthWidget } from "./widgets/memory";

export function Dashboard() {
  const [currentView, setCurrentView] = useState("dashboard");
  const [selectedDevice, setSelectedDevice] = useState<Agent | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [networkStats, setNetworkStats] = useState<NetworkStats>({
    download: 0,
    upload: 0,
    latency: 0,
    clients: 0,
  });
  const [isTalkToMYCAOpen, setIsTalkToMYCAOpen] = useState(false);
  const [isAgentCreatorOpen, setIsAgentCreatorOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const { theme, toggleTheme } = useTheme();

  // Subscribe to real-time data
  useEffect(() => {
    const unsubAgents = dataService.subscribe("agents", (data) => {
      setAgents(data as Agent[]);
    });

    const unsubStats = dataService.subscribe("network-stats", (data) => {
      setNetworkStats(data as NetworkStats);
    });

    return () => {
      unsubAgents();
      unsubStats();
    };
  }, []);

  const handleNodeClick = (node: TopologyNode) => {
    // Find the corresponding agent for this node
    const agent = agents.find((a) => a.id === node.id);
    if (agent) {
      setSelectedDevice(agent);
    }
  };

  const renderView = () => {
    switch (currentView) {
      case "topology":
      case "topology3d":
        return <AgentTopologyView onNodeClick={handleNodeClick} />;
      case "clients":
        return <ClientsView onDeviceClick={(device) => {
          const agent = agents.find((a) => a.name === device.name);
          if (agent) setSelectedDevice(agent);
        }} />;
      case "radios":
        return <RadiosView />;
      case "insights":
        return <TrafficAnalysisView />;
      case "settings":
        return <SettingsView />;
      case "flows":
        return <FlowsView />;
      case "devices":
        return <DevicesView />;
      case "wifi":
        return <DeviceHealthView />;
      case "logs":
        return <SecurityView />;
      case "customize":
        return <CustomizableDashboard />;
      case "workflows":
        return <WorkflowStudioView />;
      default:
        return <DashboardMainView agents={agents} networkStats={networkStats} onAgentClick={setSelectedDevice} />;
    }
  };

  const activeAgents = agents.filter((a) => a.status === "online" || a.status === "active").length;
  const totalTraffic = networkStats.download + networkStats.upload;

  return (
    <div className="flex h-screen bg-[#0F172A] text-white transition-colors duration-300">
      {/* Mobile Menu Overlay */}
      {isMobileMenuOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm lg:hidden"
          onClick={() => setIsMobileMenuOpen(false)}
        />
      )}

      {/* Left Sidebar - only show on dashboard view */}
      {currentView === "dashboard" && (
        <div className={`hidden lg:block ${isSidebarCollapsed ? "w-0 overflow-hidden" : ""} transition-all duration-300`}>
          <MYCASidebar agents={agents} networkStats={networkStats} onViewChange={setCurrentView} />
        </div>
      )}

      {/* Left Navigation Bar */}
      <div className={`
        fixed lg:relative z-50 h-full
        flex w-16 flex-col items-center border-r border-gray-800 bg-[#1E293B] py-4
        transform transition-transform duration-300
        ${isMobileMenuOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}
      `}>
        <div className="mb-8 flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-purple-500 to-blue-600 animate-pulse-glow cursor-pointer" onClick={() => setCurrentView("dashboard")}>
          <svg viewBox="0 0 24 24" className="h-6 w-6 fill-white">
            <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 4.44-2.54M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-4.44-2.54" />
          </svg>
        </div>
        <Navigation currentView={currentView} onViewChange={(view) => { setCurrentView(view); setIsMobileMenuOpen(false); }} />
      </div>

      {/* Main Content */}
      <div className="flex flex-1 flex-col overflow-hidden lg:ml-0">
        {/* Top Header */}
        <div className="border-b border-gray-800 bg-[#1E293B] px-3 sm:px-6 py-3 sm:py-4">
          <div className="flex items-center justify-between gap-2">
            {/* Left side - Mobile menu & Orchestrator selector */}
            <div className="flex items-center gap-2 sm:gap-4">
              {/* Mobile menu button */}
              <button
                onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                className="lg:hidden p-2 rounded-lg hover:bg-gray-700 transition-colors"
              >
                {isMobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
              </button>
              
              <button className="hidden sm:flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium hover:bg-gray-700 transition-colors">
                <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                <span className="hidden md:inline">MYCA Orchestrator</span>
                <span className="md:hidden">MYCA</span>
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              
              <div className="hidden sm:flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-purple-500 to-blue-600">
                  <svg viewBox="0 0 24 24" className="h-5 w-5 fill-white">
                    <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 4.44-2.54" />
                  </svg>
                </div>
                <span className="text-sm font-medium text-purple-400 hidden lg:inline">MYCA Network</span>
              </div>
            </div>
            
            {/* Right side - Actions */}
            <div className="flex items-center gap-2 sm:gap-4">
              <div className="hidden md:block">
                <SearchBar />
              </div>
              
              <div className="hidden sm:flex items-center gap-2 text-xs sm:text-sm text-gray-400">
                <Activity className="h-4 w-4 text-green-500" />
                <span>{totalTraffic.toFixed(1)} Kbps</span>
              </div>
              
              <NotificationPanel />
              
              <button
                onClick={toggleTheme}
                className="h-8 w-8 sm:h-9 sm:w-9 rounded-lg bg-gray-700 hover:bg-gray-600 flex items-center justify-center transition-colors"
                title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
              >
                {theme === "dark" ? (
                  <Sun className="h-4 w-4 sm:h-5 sm:w-5" />
                ) : (
                  <Moon className="h-4 w-4 sm:h-5 sm:w-5" />
                )}
              </button>
              
              <button
                onClick={() => setIsAgentCreatorOpen(true)}
                className="flex items-center gap-2 rounded-lg bg-green-600 hover:bg-green-700 px-3 sm:px-4 py-2 text-xs sm:text-sm font-medium transition-all hover:scale-105 hover:shadow-lg hover:shadow-green-500/30"
              >
                <Plus className="h-4 w-4" />
                <span className="hidden sm:inline">Create Agent</span>
              </button>
              <button
                onClick={() => setIsTalkToMYCAOpen(true)}
                className="flex items-center gap-2 rounded-lg bg-purple-600 hover:bg-purple-700 px-3 sm:px-4 py-2 text-xs sm:text-sm font-medium transition-all hover:scale-105 hover:shadow-lg hover:shadow-purple-500/30"
              >
                <Mic className="h-4 w-4" />
                <span className="hidden sm:inline">Talk to MYCA</span>
              </button>
              
              <div className="h-8 w-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-xs font-bold cursor-pointer hover:scale-110 transition-transform">
                MO
              </div>
            </div>
          </div>
        </div>

        {/* View Content */}
        <div className="flex-1 overflow-auto">{renderView()}</div>
      </div>

      {/* Agent Details Sidebar */}
      {selectedDevice && (
        <AgentDetailsSidebar 
          agent={selectedDevice} 
          onClose={() => setSelectedDevice(null)}
          onViewLogs={() => { setCurrentView("logs"); setSelectedDevice(null); }}
        />
      )}

      {/* Talk to MYCA Modal */}
      <TalkToMYCA isOpen={isTalkToMYCAOpen} onClose={() => setIsTalkToMYCAOpen(false)} />

      {/* Agent Creator Modal */}
      <AgentCreator 
        isOpen={isAgentCreatorOpen} 
        onClose={() => setIsAgentCreatorOpen(false)}
        onAgentCreated={() => {
          // Refresh agents list
          dataService.publish("agents", agents);
        }}
      />

      {/* Floating Action Button for Mobile */}
      <button
        onClick={() => setIsTalkToMYCAOpen(true)}
        className="fixed bottom-6 right-6 z-30 lg:hidden flex items-center justify-center w-14 h-14 rounded-full bg-gradient-to-br from-purple-500 to-blue-600 shadow-lg shadow-purple-500/30 hover:scale-110 transition-transform"
      >
        <Mic className="h-6 w-6 text-white" />
      </button>

      {/* Toast Notifications */}
      <Toaster position="top-right" richColors />
    </div>
  );
}

// MYCA-specific Sidebar
interface MYCASidebarProps {
  agents: Agent[];
  networkStats: NetworkStats;
  onViewChange?: (view: string) => void;
}

function MYCASidebar({ agents, networkStats, onViewChange }: MYCASidebarProps) {
  const activeAgents = agents.filter((a) => a.status === "online" || a.status === "active").length;
  const [showSystemInfo, setShowSystemInfo] = useState(false);
  const [systemStats, setSystemStats] = useState<{
    cpu?: { usage: number };
    memory?: { usedPercent: number; used: number; total: number };
    os?: { uptime: number; hostname: string };
  } | null>(null);

  useEffect(() => {
    if (showSystemInfo) {
      fetch("/api/system")
        .then((r) => r.ok ? r.json() : null)
        .then(setSystemStats)
        .catch(() => null);
    }
  }, [showSystemInfo]);

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${days}d ${hours}h ${minutes}m`;
  };

  const formatBytes = (bytes: number) => {
    const gb = bytes / (1024 * 1024 * 1024);
    return `${gb.toFixed(1)} GB`;
  };
  
  return (
    <div className="flex w-72 flex-col border-r border-gray-800 bg-[#1E293B]">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-gray-800 p-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-purple-500 to-blue-600">
          <svg viewBox="0 0 24 24" className="h-6 w-6 fill-white">
            <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 4.44-2.54M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-4.44-2.54" />
          </svg>
        </div>
        <div className="flex-1">
          <div className="text-sm font-semibold">MYCA Orchestrator</div>
          <div className="text-xs text-gray-400">{new Date().toLocaleTimeString()}</div>
        </div>
      </div>

      {/* Orchestrator Image */}
      <div className="border-b border-gray-800 p-6">
        <div className="mb-4 rounded-lg bg-[#0F172A] p-4 flex items-center justify-center">
          <div className="relative">
            <div className="w-24 h-24 rounded-lg bg-gradient-to-br from-purple-500/30 to-blue-600/30 border-2 border-purple-500 flex items-center justify-center">
              <svg className="h-12 w-12 text-purple-400" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 15.5m14.8-.2a2.25 2.25 0 01-1.311 2.046l-5.104 2.217a2.25 2.25 0 01-1.77 0L6.511 17.346A2.25 2.25 0 015.2 15.3" />
              </svg>
            </div>
            <div className="absolute -bottom-1 -right-1 w-4 h-4 rounded-full bg-green-500 border-2 border-[#1E293B]" />
          </div>
        </div>

        <div className="space-y-2">
          <div className="font-semibold">MYCA MAS v10.0.162</div>
          <div className="text-xs text-gray-400">Multi-Agent System</div>
          <div className="flex gap-2">
            <button 
              onClick={() => setShowSystemInfo(!showSystemInfo)}
              className="text-xs text-blue-500 hover:underline"
            >
              {showSystemInfo ? "Hide System Info" : "View System Info"}
            </button>
            <span className="text-xs text-gray-400">|</span>
            <a 
              href="https://mycosoft.io/support" 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-xs text-blue-500 hover:underline"
            >
              Support
            </a>
          </div>
        </div>

        {/* System Info Panel */}
        {showSystemInfo && systemStats && (
          <div className="mt-4 p-3 bg-[#0F172A] rounded-lg text-xs space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-400">Hostname</span>
              <span>{systemStats.os?.hostname || "Unknown"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">CPU Usage</span>
              <span className={systemStats.cpu?.usage && systemStats.cpu.usage > 80 ? "text-red-400" : "text-green-400"}>
                {systemStats.cpu?.usage?.toFixed(1) || 0}%
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Memory</span>
              <span>
                {formatBytes(systemStats.memory?.used || 0)} / {formatBytes(systemStats.memory?.total || 0)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Uptime</span>
              <span>{formatUptime(systemStats.os?.uptime || 0)}</span>
            </div>
          </div>
        )}
      </div>

      {/* System Info */}
      <div className="flex-1 overflow-auto p-6">
        <div className="space-y-4">
          <div>
            <div className="text-xs text-gray-400">Active Agents</div>
            <div className="text-sm flex items-center gap-2">
              <span className="text-green-500 font-bold">{activeAgents}</span>
              <span className="text-gray-500">/ {agents.length}</span>
            </div>
          </div>

          <div>
            <div className="text-xs text-gray-400">System Uptime</div>
            <div className="text-sm">{systemStats ? formatUptime(systemStats.os?.uptime || 0) : "Loading..."}</div>
          </div>

          <div className="border-t border-gray-800 pt-4">
            <div className="mb-2 flex items-center justify-between">
              <div className="text-xs text-gray-400">Network</div>
              <div className="flex items-center gap-1">
                <div className="h-2 w-2 rounded-full bg-green-500" />
                <div className="text-xs text-green-500">Healthy</div>
              </div>
            </div>
            <div className="mb-2">
              <div className="text-xs text-gray-400">Latency</div>
              <div className="text-sm text-green-500">{networkStats.latency.toFixed(1)}ms</div>
            </div>
            <div className="mb-2">
              <div className="text-xs text-gray-400">Activity</div>
              <div className="flex items-center gap-2 text-sm">
                <span className="text-cyan-500">â†“ {networkStats.download.toFixed(1)} Kbps</span>
                <span className="text-purple-500">â†‘ {networkStats.upload.toFixed(1)} Kbps</span>
              </div>
            </div>
          </div>

          <div className="border-t border-gray-800 pt-4">
            <div className="mb-2 text-xs font-semibold">Agent Health</div>
            <div className="mb-1 flex items-center justify-between text-xs">
              <span className="text-gray-400">-12h</span>
              <span className="text-gray-400">Now</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-gray-700">
              <div className="h-full bg-green-500" style={{ width: `${agents.length > 0 ? (activeAgents / agents.length) * 100 : 0}%` }} />
            </div>
            <div className="mt-2 flex items-center justify-between">
              <button 
                onClick={() => onViewChange?.("clients")}
                className="text-xs text-blue-500 hover:underline"
              >
                See All Agents
              </button>
            </div>
          </div>

          <div className="border-t border-gray-800 pt-4">
            <div className="mb-2 text-xs font-semibold">Recent Activity</div>
            <div className="space-y-2">
              {agents.slice(0, 3).map((agent) => (
                <div key={agent.id} className="flex items-center gap-2 text-xs">
                  <div className={`h-2 w-2 rounded-full ${
                    agent.status === "online" || agent.status === "active" ? "bg-green-500" : "bg-gray-500"
                  }`} />
                  <span className="text-gray-300 truncate flex-1">{agent.name}</span>
                  <span className="text-gray-500">{agent.tasksInProgress} tasks</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Agent Details Sidebar
function AgentDetailsSidebar({ agent, onClose, onViewLogs }: { agent: Agent; onClose: () => void; onViewLogs?: () => void }) {
  const [command, setCommand] = useState("");
  const [showCommandInput, setShowCommandInput] = useState(false);
  const [commandResult, setCommandResult] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const sendCommand = async () => {
    if (!command.trim()) return;
    
    setIsLoading(true);
    setCommandResult(null);
    
    try {
      const response = await fetch("/api/agents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          agentId: agent.id,
          message: command,
        }),
      });
      
      const result = await response.json();
      setCommandResult(result.message || "Command sent successfully");
      setCommand("");
    } catch (error) {
      setCommandResult("Failed to send command");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-80 border-l border-gray-800 bg-[#1E293B] p-4 overflow-auto">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-semibold">Agent Details</h2>
        <button onClick={onClose} className="text-gray-400 hover:text-white text-xl">Ã—</button>
      </div>

      <div className="text-center p-4 bg-[#0F172A] rounded-lg mb-4">
        <div className={`w-16 h-16 rounded-lg mx-auto mb-3 flex items-center justify-center ${
          agent.status === "online" || agent.status === "active"
            ? "bg-green-500/20 text-green-400 border border-green-500"
            : "bg-gray-500/20 text-gray-400 border border-gray-500"
        }`}>
          <svg className="h-8 w-8" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25zm.75-12h9v9h-9v-9z" />
          </svg>
        </div>
        <h3 className="font-bold text-lg">{agent.name}</h3>
        <span className={`inline-block mt-2 px-3 py-1 rounded-full text-xs font-medium ${
          agent.status === "online" || agent.status === "active"
            ? "bg-green-500/20 text-green-400"
            : agent.status === "idle"
            ? "bg-yellow-500/20 text-yellow-400"
            : "bg-gray-500/20 text-gray-400"
        }`}>
          {agent.status.toUpperCase()}
        </span>
      </div>

      <div className="space-y-3 text-sm">
        <div className="flex justify-between py-2 border-b border-gray-700">
          <span className="text-gray-400">ID</span>
          <span className="font-mono text-xs">{agent.id}</span>
        </div>
        <div className="flex justify-between py-2 border-b border-gray-700">
          <span className="text-gray-400">Category</span>
          <span className="capitalize">{agent.category}</span>
        </div>
        <div className="flex justify-between py-2 border-b border-gray-700">
          <span className="text-gray-400">Type</span>
          <span className="capitalize">{agent.type}</span>
        </div>
        <div className="flex justify-between py-2 border-b border-gray-700">
          <span className="text-gray-400">IP Address</span>
          <span>{agent.ip}</span>
        </div>
        <div className="flex justify-between py-2 border-b border-gray-700">
          <span className="text-gray-400">Experience</span>
          <span className={`${
            agent.experience === "Excellent" ? "text-green-400" :
            agent.experience === "Good" ? "text-blue-400" : "text-yellow-400"
          }`}>{agent.experience}</span>
        </div>
        <div className="flex justify-between py-2 border-b border-gray-700">
          <span className="text-gray-400">Uptime</span>
          <span>{agent.uptime}</span>
        </div>
        <div className="flex justify-between py-2 border-b border-gray-700">
          <span className="text-gray-400">Tasks Completed</span>
          <span className="text-green-400">{agent.tasksCompleted}</span>
        </div>
        <div className="flex justify-between py-2 border-b border-gray-700">
          <span className="text-gray-400">Tasks In Progress</span>
          <span className="text-yellow-400">{agent.tasksInProgress}</span>
        </div>
        <div className="flex justify-between py-2 border-b border-gray-700">
          <span className="text-gray-400">Download</span>
          <span className="text-cyan-400">â†“ {agent.downloadSpeed.toFixed(1)} Kbps</span>
        </div>
        <div className="flex justify-between py-2 border-b border-gray-700">
          <span className="text-gray-400">Upload</span>
          <span className="text-purple-400">â†‘ {agent.uploadSpeed.toFixed(1)} Kbps</span>
        </div>
      </div>

      <div className="mt-4 space-y-2">
        {/* Command Input */}
        {showCommandInput && (
          <div className="p-3 bg-[#0F172A] rounded-lg space-y-2">
            <textarea
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              placeholder="Enter command for agent..."
              className="w-full p-2 bg-gray-800 border border-gray-700 rounded text-sm resize-none"
              rows={3}
            />
            <div className="flex gap-2">
              <button
                onClick={sendCommand}
                disabled={isLoading || !command.trim()}
                className="flex-1 py-1.5 px-3 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 rounded text-sm font-medium"
              >
                {isLoading ? "Sending..." : "Send"}
              </button>
              <button
                onClick={() => { setShowCommandInput(false); setCommand(""); setCommandResult(null); }}
                className="py-1.5 px-3 bg-gray-700 hover:bg-gray-600 rounded text-sm"
              >
                Cancel
              </button>
            </div>
            {commandResult && (
              <div className="text-xs text-gray-400 mt-2 p-2 bg-gray-800 rounded">
                {commandResult}
              </div>
            )}
          </div>
        )}
        
        {!showCommandInput && (
          <button 
            onClick={() => setShowCommandInput(true)}
            className="w-full py-2 px-4 bg-purple-600 hover:bg-purple-700 rounded-lg text-sm font-medium"
          >
            Send Command
          </button>
        )}
        
        <button 
          onClick={onViewLogs}
          className="w-full py-2 px-4 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm font-medium"
        >
          View Logs
        </button>
      </div>
    </div>
  );
}

// Dashboard Main View
interface DashboardMainViewProps {
  agents: Agent[];
  networkStats: NetworkStats;
  onAgentClick?: (agent: Agent) => void;
}

function DashboardMainView({ agents, networkStats, onAgentClick }: DashboardMainViewProps) {
  const activeAgents = agents.filter((a) => a.status === "online" || a.status === "active").length;
  const totalTasks = agents.reduce((sum, a) => sum + a.tasksCompleted, 0);
  const healthPercentage = agents.length > 0 ? Math.round((activeAgents / agents.length) * 100) : 0;

  return (
    <div className="p-3 sm:p-6">
      {/* Main Stats */}
      <div className="mb-4 sm:mb-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 sm:gap-0">
        <div>
          <h1 className="text-lg sm:text-2xl font-semibold">
            System Status:{" "}
            <span className="text-green-500">Excellent</span>{" "}
            <span className="text-green-500">{healthPercentage}%</span>
          </h1>
        </div>
        <div className="flex gap-3 sm:gap-4 text-xs sm:text-sm">
          <div className="flex items-center gap-1 sm:gap-2">
            <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
            Active
          </div>
          <div className="flex items-center gap-1 sm:gap-2">
            <div className="h-2 w-2 rounded-full bg-yellow-500" />
            Idle
          </div>
          <div className="flex items-center gap-1 sm:gap-2">
            <div className="h-2 w-2 rounded-full bg-gray-500" />
            Offline
          </div>
        </div>
      </div>

      {/* Quick Stats Grid */}
      <div className="mb-4 sm:mb-6 grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-4">
        <div className="rounded-lg bg-[#1E293B] p-3 sm:p-4 transition-all hover:scale-[1.02] hover:shadow-lg hover:shadow-purple-500/10">
          <div className="text-[10px] sm:text-xs text-gray-400 uppercase tracking-wider">Active Agents</div>
          <div className="text-2xl sm:text-3xl font-bold text-green-500">{activeAgents}</div>
          <div className="text-[10px] sm:text-xs text-gray-500">of {agents.length} total</div>
        </div>
        <div className="rounded-lg bg-[#1E293B] p-3 sm:p-4 transition-all hover:scale-[1.02] hover:shadow-lg hover:shadow-blue-500/10">
          <div className="text-[10px] sm:text-xs text-gray-400 uppercase tracking-wider">Tasks/Hour</div>
          <div className="text-2xl sm:text-3xl font-bold">124</div>
          <div className="text-[10px] sm:text-xs text-green-400">â†‘ 12% from yesterday</div>
        </div>
        <div className="rounded-lg bg-[#1E293B] p-3 sm:p-4 transition-all hover:scale-[1.02] hover:shadow-lg hover:shadow-cyan-500/10">
          <div className="text-[10px] sm:text-xs text-gray-400 uppercase tracking-wider">Total Tasks</div>
          <div className="text-2xl sm:text-3xl font-bold">{totalTasks.toLocaleString()}</div>
          <div className="text-[10px] sm:text-xs text-gray-500">completed all time</div>
        </div>
        <div className="rounded-lg bg-[#1E293B] p-3 sm:p-4 transition-all hover:scale-[1.02] hover:shadow-lg hover:shadow-green-500/10">
          <div className="text-[10px] sm:text-xs text-gray-400 uppercase tracking-wider">Latency</div>
          <div className="text-2xl sm:text-3xl font-bold text-green-500">{networkStats.latency.toFixed(1)}ms</div>
          <div className="text-[10px] sm:text-xs text-green-400">Excellent</div>
        </div>
      </div>

      {/* Agent Status Overview */}
      <div className="mb-4 sm:mb-8 overflow-x-auto">
        <div className="flex gap-4 sm:gap-8 min-w-max sm:min-w-0 sm:justify-start lg:justify-start">
          {[
            { label: "Core Agents", count: agents.filter((a) => a.category === "core").length, color: "border-purple-500" },
            { label: "Financial", count: agents.filter((a) => a.category === "financial").length, color: "border-blue-500" },
            { label: "Mycology", count: agents.filter((a) => a.category === "mycology").length, color: "border-green-500" },
            { label: "Research", count: agents.filter((a) => a.category === "research").length, color: "border-cyan-500" },
            { label: "DAO", count: agents.filter((a) => a.category === "dao").length, color: "border-pink-500" },
            { label: "Communication", count: agents.filter((a) => a.category === "communication").length, color: "border-yellow-500" },
          ].map((item, i) => (
            <div key={i} className="text-center flex-shrink-0 hover:scale-105 transition-transform cursor-pointer">
              <div className="mb-1 sm:mb-2 flex h-12 sm:h-16 items-center justify-center">
                <div className="relative h-10 w-10 sm:h-12 sm:w-12">
                  <div className={`absolute inset-0 rounded-full border-4 ${item.color}`} />
                  <div className="absolute inset-0 flex items-center justify-center text-lg sm:text-xl font-bold">
                    {item.count}
                  </div>
                </div>
              </div>
              <div className="text-[10px] sm:text-xs text-gray-400">{item.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Agent Activity Chart */}
      <div className="mb-4 sm:mb-8">
        <div className="h-12 sm:h-16 rounded bg-gradient-to-r from-purple-500 via-blue-500 to-cyan-500 opacity-80 overflow-x-auto">
          <div className="flex h-full items-center justify-between px-2 sm:px-4 text-[8px] sm:text-xs min-w-[600px]">
            {Array.from({ length: 24 }, (_, i) => (
              <span key={i} className="text-white/70">
                {i}:00
              </span>
            ))}
          </div>
        </div>
        <div className="mt-2 text-center text-[10px] sm:text-xs text-gray-400">
          Agent Activity Distribution - Last 24 Hours
        </div>
      </div>

      {/* Widgets Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        <div className="rounded-lg bg-[#1E293B] p-3 sm:p-4 transition-all hover:shadow-lg hover:shadow-purple-500/10">
          <h3 className="text-xs sm:text-sm font-semibold mb-3 sm:mb-4">Top Active Agents</h3>
          <div className="space-y-2 sm:space-y-3">
            {agents
              .filter((a) => a.status === "online" || a.status === "active")
              .slice(0, 5)
              .map((agent) => (
                <div
                  key={agent.id}
                  className="flex items-center gap-2 sm:gap-3 p-2 rounded-lg hover:bg-gray-700/50 cursor-pointer transition-colors"
                  onClick={() => onAgentClick?.(agent)}
                >
                  <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-purple-500/20 flex items-center justify-center text-purple-400 flex-shrink-0">
                    <svg className="h-4 w-4 sm:h-5 sm:w-5" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25zm.75-12h9v9h-9v-9z" />
                    </svg>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-xs sm:text-sm font-medium truncate">{agent.name}</div>
                    <div className="text-[10px] sm:text-xs text-gray-400">{agent.tasksInProgress} active tasks</div>
                  </div>
                  <div className="text-[10px] sm:text-xs text-cyan-400 flex-shrink-0">
                    {agent.downloadSpeed.toFixed(1)} Kbps
                  </div>
                </div>
              ))}
          </div>
        </div>

        <div className="rounded-lg bg-[#1E293B] p-3 sm:p-4 transition-all hover:shadow-lg hover:shadow-blue-500/10">
          <h3 className="text-xs sm:text-sm font-semibold mb-3 sm:mb-4">Traffic by Category</h3>
          <div className="space-y-2 sm:space-y-3">
            {[
              { name: "Agent Communication", value: "3.10 GB", color: "bg-purple-500", width: "w-[80%]" },
              { name: "Database Queries", value: "1.88 GB", color: "bg-blue-500", width: "w-[60%]" },
              { name: "API Requests", value: "912 MB", color: "bg-cyan-500", width: "w-[40%]" },
              { name: "File Operations", value: "729 MB", color: "bg-green-500", width: "w-[35%]" },
              { name: "Caching", value: "452 MB", color: "bg-yellow-500", width: "w-[25%]" },
            ].map((item, i) => (
              <div key={i} className="space-y-1">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 sm:w-3 sm:h-3 rounded ${item.color}`} />
                    <div className="text-[10px] sm:text-sm">{item.name}</div>
                  </div>
                  <div className="text-[10px] sm:text-sm text-gray-400">{item.value}</div>
                </div>
                <div className="h-1 bg-gray-700 rounded-full overflow-hidden">
                  <div className={`h-full ${item.color} ${item.width}`} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom Section */}
      <div className="mt-4 sm:mt-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        <div className="rounded-lg bg-[#1E293B] p-4 sm:p-6 transition-all hover:shadow-lg hover:shadow-purple-500/10">
          <h3 className="mb-3 sm:mb-4 text-xs sm:text-sm font-semibold">Agent Summary</h3>
          <div className="flex items-center gap-4 sm:gap-8">
            <div className="text-center">
              <div className="mb-1 sm:mb-2 text-2xl sm:text-3xl font-bold text-purple-500">{activeAgents}</div>
              <div className="text-[10px] sm:text-xs text-gray-400">AGENTS ACTIVE</div>
            </div>
            <div className="text-center">
              <div className="mb-1 sm:mb-2 text-2xl sm:text-3xl font-bold text-gray-500">{agents.length - activeAgents}</div>
              <div className="text-[10px] sm:text-xs text-gray-400">AGENTS IDLE</div>
            </div>
          </div>
        </div>

        <div className="rounded-lg bg-[#1E293B] p-4 sm:p-6 transition-all hover:shadow-lg hover:shadow-green-500/10">
          <h3 className="mb-3 sm:mb-4 text-xs sm:text-sm font-semibold">Task Summary</h3>
          <div className="flex items-center gap-4 sm:gap-8">
            <div className="text-center">
              <div className="mb-1 sm:mb-2 text-2xl sm:text-3xl font-bold text-green-500">
                {agents.reduce((sum, a) => sum + a.tasksInProgress, 0)}
              </div>
              <div className="text-[10px] sm:text-xs text-gray-400">IN PROGRESS</div>
            </div>
            <div className="text-center">
              <div className="mb-1 sm:mb-2 text-2xl sm:text-3xl font-bold text-blue-500">{totalTasks}</div>
              <div className="text-[10px] sm:text-xs text-gray-400">COMPLETED</div>
            </div>
          </div>
        </div>

        <div className="rounded-lg bg-[#1E293B] p-4 sm:p-6 transition-all hover:shadow-lg hover:shadow-blue-500/10">
          <h3 className="mb-3 sm:mb-4 text-xs sm:text-sm font-semibold">System Resources</h3>
          <div className="space-y-2 sm:space-y-3">
            <div>
              <div className="flex justify-between text-xs sm:text-sm mb-1">
                <span className="text-gray-400">CPU Usage</span>
                <span>24%</span>
              </div>
              <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                <div className="h-full w-1/4 bg-gradient-to-r from-green-500 to-emerald-400 transition-all" />
              </div>
            </div>
            <div>
              <div className="flex justify-between text-xs sm:text-sm mb-1">
                <span className="text-gray-400">Memory</span>
                <span>4.2 GB / 16 GB</span>
              </div>
              <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                <div className="h-full w-1/4 bg-gradient-to-r from-blue-500 to-cyan-400 transition-all" />
              </div>
            </div>
          </div>
        </div>

        {/* Memory & Brain Health */}
        <MemoryHealthWidget />
      </div>
    </div>
  );
}




