"use client";

import { ChevronRight, Wifi } from "lucide-react";

const accessPoints = [
  { name: "Office UK...", color: "#0EA5E9" },
  { name: "Living Room...", color: "#10B981" },
  { name: "Bedroom UK...", color: "#3B82F6" },
];

export function MostActiveAccessPoints() {
  return (
    <div className="rounded-lg bg-[#1E293B] p-6">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold">Most Active Access Points</h3>
        <ChevronRight className="h-5 w-5 text-gray-400" />
      </div>

      <div className="flex items-center gap-4 overflow-x-auto pb-2">
        {accessPoints.map((ap, index) => (
          <div key={index} className="flex flex-col items-center gap-2">
            <div
              className="flex h-16 w-16 items-center justify-center rounded-lg"
              style={{ backgroundColor: ap.color + "20" }}
            >
              <Wifi className="h-8 w-8" style={{ color: ap.color }} />
            </div>
            <span className="max-w-[64px] truncate text-xs text-gray-300">{ap.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
