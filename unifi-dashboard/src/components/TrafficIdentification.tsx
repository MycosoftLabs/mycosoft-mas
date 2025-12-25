"use client";

import { useState, useEffect } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";
import { ChevronRight } from "lucide-react";
import { dataService } from "@/lib/data-service";
import type { TrafficData } from "@/types";

const initialData = [
  { name: "Blizzard Entertainment", value: 58.7, download: "57.9 GB", upload: "812 MB", color: "#0EA5E9" },
  { name: "Lets Encrypt", value: 41.9, download: "41.1 GB", upload: "822 MB", color: "#F59E0B" },
  { name: "SSL/TLS", value: 37.4, download: "36.6 GB", upload: "862 MB", color: "#10B981" },
  { name: "STUN", value: 2.89, download: "1.20 GB", upload: "1.59 GB", color: "#8B5CF6" },
  { name: "XBOX", value: 2.72, download: "2.69 GB", upload: "31.8 MB", color: "#EF4444" },
];

const COLORS = ["#0EA5E9", "#F59E0B", "#10B981", "#8B5CF6", "#EF4444"];

export function TrafficIdentification() {
  const [data, setData] = useState(initialData);
  const [isLive, setIsLive] = useState(true);

  useEffect(() => {
    if (!isLive) return;

    const unsubscribe = dataService.subscribe("traffic", (rawData) => {
      const trafficData = rawData as unknown as TrafficData;
      setData((prevData) =>
        prevData.map((item, index) => ({
          ...item,
          value: trafficData.services[index]?.value || item.value,
        }))
      );
    });

    return unsubscribe;
  }, [isLive]);

  const total = data.reduce((sum, item) => sum + item.value, 0);

  return (
    <div className="rounded-lg bg-[#1E293B] p-6">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-semibold">Traffic Identification</h3>
          <div className="flex items-center gap-2">
            <div className={`h-2 w-2 rounded-full ${isLive ? "animate-pulse bg-green-500" : "bg-gray-500"}`} />
            <button
              onClick={() => setIsLive(!isLive)}
              className="text-xs text-gray-400 hover:text-white"
            >
              {isLive ? "Live" : "Paused"}
            </button>
          </div>
        </div>
        <ChevronRight className="h-5 w-5 text-gray-400" />
      </div>

      <div className="mb-4 flex items-center justify-between text-sm">
        <span className="text-cyan-500">↓ 1.48 GB</span>
        <span className="text-purple-500">↑ 4.49 GB</span>
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
              <div className="text-2xl font-bold">{total.toFixed(0)} GB</div>
              <div className="text-xs text-gray-400">Identified Traffic</div>
            </div>
          </div>
        </div>

        {/* Legend */}
        <div className="flex flex-col justify-center space-y-3">
          <div className="mb-2 grid grid-cols-3 gap-2 text-xs text-gray-400">
            <span>Name</span>
            <span className="text-right">Download</span>
            <span className="text-right">Upload</span>
            <span className="text-right">Total</span>
          </div>
          {data.map((item, index) => (
            <div key={index} className="grid grid-cols-4 gap-2 text-xs">
              <div className="col-span-1 flex items-center gap-2">
                <div
                  className="h-2 w-2 rounded-full"
                  style={{ backgroundColor: item.color }}
                />
                <span className="truncate">{item.name}</span>
              </div>
              <span className="text-right text-cyan-500">{item.download}</span>
              <span className="text-right text-purple-500">{item.upload}</span>
              <span className="text-right">{item.value} GB</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
