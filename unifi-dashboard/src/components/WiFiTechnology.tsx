"use client";

import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";
import { ChevronRight } from "lucide-react";

const data = [
  { name: "WiFi 6 - 5 GHz", value: 3, color: "#0EA5E9", experience: "Excellent" },
  { name: "WiFi 5 - 5 GHz", value: 4, color: "#3B82F6", experience: "Excellent" },
  { name: "WiFi 4 - 5 GHz", value: 9, color: "#60A5FA", experience: "Excellent" },
  { name: "WiFi 4 - 2.4 GHz", value: 9, color: "#93C5FD", experience: "Excellent" },
  { name: "WiFi 6 - 2.4 GHz", value: 2, color: "#BFDBFE", experience: "Excellent" },
];

const COLORS = ["#0EA5E9", "#3B82F6", "#60A5FA", "#93C5FD", "#BFDBFE"];

export function WiFiTechnology() {
  const total = data.reduce((sum, item) => sum + item.value, 0);

  return (
    <div className="rounded-lg bg-[#1E293B] p-6">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold">WiFi Technology</h3>
        <ChevronRight className="h-5 w-5 text-gray-400" />
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Pie Chart */}
        <div className="flex items-center justify-center">
          <div className="relative h-48 w-48">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={2}
                  dataKey="value"
                >
                  {data.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <div className="text-2xl font-bold">{total}</div>
              <div className="text-xs text-gray-400">Total Clients</div>
            </div>
          </div>
        </div>

        {/* Legend */}
        <div className="flex flex-col justify-center space-y-3">
          <div className="mb-2 grid grid-cols-4 gap-2 text-xs text-gray-400">
            <span className="col-span-2">Type</span>
            <span className="text-right">Activity</span>
            <span className="text-right">Experience</span>
            <span className="text-right">Clients</span>
          </div>
          {data.map((item, index) => (
            <div key={index} className="grid grid-cols-4 gap-2 text-xs">
              <div className="col-span-2 flex items-center gap-2">
                <div
                  className="h-2 w-2 rounded-full"
                  style={{ backgroundColor: item.color }}
                />
                <span className="truncate">{item.name}</span>
              </div>
              <div className="text-right">
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-700">
                  <div
                    className="h-full bg-blue-500"
                    style={{ width: `${(item.value / total) * 100}%` }}
                  />
                </div>
              </div>
              <span className="text-right text-green-500">{item.experience}</span>
              <span className="text-right">{item.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
