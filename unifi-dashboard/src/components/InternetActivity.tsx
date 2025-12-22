"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const generateData = () => {
  const data = [];
  const now = new Date();
  for (let i = 0; i < 48; i++) {
    const time = new Date(now.getTime() - (47 - i) * 30 * 60 * 1000);
    data.push({
      time: time.getHours() + ":" + (time.getMinutes() < 10 ? "0" : "") + time.getMinutes(),
      download: Math.random() * 45 + 5,
      upload: Math.random() * 15 + 2,
    });
  }
  return data;
};

const data = generateData();

export function InternetActivity() {
  return (
    <div className="rounded-lg bg-[#1E293B] p-6">
      <div className="mb-6 flex items-center justify-between">
        <h3 className="text-sm font-semibold">Internet Activity</h3>
        <div className="flex items-center gap-4 text-xs">
          <button className="rounded bg-blue-500 px-3 py-1 font-medium">All</button>
          <button className="text-gray-400 hover:text-white">Download</button>
          <button className="text-gray-400 hover:text-white">Upload</button>
          <div className="flex items-center gap-6">
            <span className="text-cyan-500">↓ 1.53 GB</span>
            <span className="text-purple-500">↑ 5.87 GB</span>
          </div>
        </div>
      </div>

      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <defs>
              <linearGradient id="colorDownload" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="colorUpload" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#0EA5E9" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#0EA5E9" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis
              dataKey="time"
              stroke="#6B7280"
              tick={{ fontSize: 10 }}
              tickLine={false}
            />
            <YAxis stroke="#6B7280" tick={{ fontSize: 10 }} tickLine={false} />
            <Tooltip
              contentStyle={{
                backgroundColor: "#1E293B",
                border: "1px solid #374151",
                borderRadius: "0.5rem",
              }}
            />
            <Area
              type="monotone"
              dataKey="download"
              stroke="#10B981"
              strokeWidth={2}
              fill="url(#colorDownload)"
            />
            <Area
              type="monotone"
              dataKey="upload"
              stroke="#0EA5E9"
              strokeWidth={2}
              fill="url(#colorUpload)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
