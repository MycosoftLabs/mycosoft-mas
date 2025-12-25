"use client";

import {
  LayoutDashboard,
  Network,
  Users,
  HardDrive,
  Activity,
  Settings,
  Globe,
  Satellite,
  Zap,
} from "lucide-react";

interface NavigationProps {
  currentView: string;
  onViewChange: (view: string) => void;
}

export function Navigation({ currentView, onViewChange }: NavigationProps) {
  const navItems = [
    { icon: LayoutDashboard, id: "dashboard", label: "Dashboard" },
    { icon: Network, id: "topology", label: "Topology" },
    { icon: Globe, id: "integrations", label: "Global Integrations" },
    { icon: Users, id: "agents", label: "Agents" },
    { icon: HardDrive, id: "databases", label: "Databases" },
    { icon: Activity, id: "flows", label: "Flows" },
    { icon: Settings, id: "settings", label: "Settings" },
  ];

  return (
    <div className="flex flex-col gap-2">
      {navItems.map((item) => (
        <button
          key={item.id}
          onClick={() => onViewChange(item.id)}
          className={`flex h-10 w-10 items-center justify-center rounded-lg transition-colors ${
            currentView === item.id
              ? "bg-blue-500 text-white"
              : "text-gray-400 hover:bg-gray-700 hover:text-white"
          }`}
          title={item.label}
        >
          <item.icon className="h-5 w-5" />
        </button>
      ))}
    </div>
  );
}
