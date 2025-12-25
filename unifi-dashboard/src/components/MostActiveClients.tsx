"use client";

import { ChevronRight, Laptop, Smartphone, Tv, Monitor, Watch } from "lucide-react";

const clients = [
  { name: "Iridium", icon: Laptop, color: "#60A5FA" },
  { name: "Journey", icon: Monitor, color: "#3B82F6" },
  { name: "Kevals-iPhone", icon: Smartphone, color: "#8B5CF6" },
  { name: "Living-Room", icon: Tv, color: "#10B981" },
  { name: "KEVALSDXBOX", icon: Monitor, color: "#6B7280" },
  { name: "Bathroom", icon: Smartphone, color: "#F59E0B" },
  { name: "BedroomApple...", icon: Watch, color: "#EC4899" },
];

export function MostActiveClients() {
  return (
    <div className="rounded-lg bg-[#1E293B] p-6">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold">Most Active Clients</h3>
        <ChevronRight className="h-5 w-5 text-gray-400" />
      </div>

      <div className="flex items-center gap-4 overflow-x-auto pb-2">
        {clients.map((client, index) => (
          <div key={index} className="flex flex-col items-center gap-2">
            <div
              className="flex h-16 w-16 items-center justify-center rounded-lg"
              style={{ backgroundColor: `${client.color}20` }}
            >
              <client.icon className="h-8 w-8" style={{ color: client.color }} />
            </div>
            <span className="max-w-[64px] truncate text-xs text-gray-300">
              {client.name}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
