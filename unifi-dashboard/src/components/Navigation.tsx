"use client";

import {
  LayoutDashboard,
  Network,
  Radio,
  Users,
  HardDrive,
  Activity,
  FileText,
  Settings,
  Workflow,
  BarChart3,
  Brain,
  Cpu,
  Box,
} from "lucide-react";

interface NavigationProps {
  currentView: string;
  onViewChange: (view: string) => void;
}

export function Navigation({ currentView, onViewChange }: NavigationProps) {
  const navItems = [
    { icon: LayoutDashboard, id: "dashboard", label: "Dashboard" },
    { icon: Network, id: "topology", label: "Agent Topology" },
    { icon: Box, id: "topology3d", label: "Mycelium View" },
    { icon: Cpu, id: "clients", label: "Agents" },
    { icon: Workflow, id: "flows", label: "Agent Flows" },
    { icon: HardDrive, id: "devices", label: "Services" },
    { icon: BarChart3, id: "insights", label: "Analytics" },
    { icon: Activity, id: "wifi", label: "Health" },
    { icon: FileText, id: "logs", label: "Logs" },
    { icon: Settings, id: "settings", label: "Settings" },
  ];

  return (
    <div className="flex flex-col gap-2">
      {navItems.map((item) => (
        <button
          key={item.id}
          onClick={() => onViewChange(item.id)}
          className={`relative flex h-10 w-10 items-center justify-center rounded-lg transition-all ${
            currentView === item.id
              ? "bg-gradient-to-br from-purple-500 to-blue-600 text-white shadow-lg shadow-purple-500/30"
              : "text-gray-400 hover:bg-gray-700 hover:text-white"
          }`}
          title={item.label}
        >
          <item.icon className="h-5 w-5" />
          {currentView === item.id && (
            <div className="absolute -left-1 top-1/2 h-6 w-1 -translate-y-1/2 rounded-r-full bg-purple-500" />
          )}
        </button>
      ))}
    </div>
  );
}
