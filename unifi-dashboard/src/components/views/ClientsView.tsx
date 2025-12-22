"use client";

import { Search } from "lucide-react";

const clients = [
  {
    name: "84:2b:2b:46:13:e6",
    vendor: "Dell Inc.",
    connection: "Dream Machine Pro...",
    network: "Default",
    wifi: "-",
    experience: "Excellent",
    technology: "GbE",
    channel: "-",
    ip: "192.168.8.202",
    activity: "0 bps",
    download: "0 bps",
    upload: "0 bps",
    usage: "527 KB",
    uptime: "17d 22h 2m 33s",
  },
  {
    name: "Linksys EA6350 2...",
    vendor: "Linksys",
    connection: "Dream Machine Pro...",
    network: "Default",
    wifi: "-",
    experience: "Excellent",
    technology: "GbE",
    channel: "-",
    ip: "192.168.8.174",
    activity: "0 bps",
    download: "0 bps",
    upload: "0 bps",
    usage: "-",
    uptime: "18d 3h 54m 12s",
  },
  {
    name: "Meross Smart Wi-...",
    vendor: "Meross",
    connection: "Dream Machine Pro...",
    network: "Default",
    wifi: "-",
    experience: "Excellent",
    technology: "GbE",
    channel: "-",
    ip: "192.168.8.228",
    activity: "0 bps",
    download: "0 bps",
    upload: "0 bps",
    usage: "-",
    uptime: "1d 3h 37m 6s",
  },
  {
    name: "MycoComp 2a:70",
    vendor: "ASUSTeK C...",
    connection: "Dream Machine Pro...",
    network: "Default",
    wifi: "-",
    experience: "Excellent",
    technology: "GbE",
    channel: "-",
    ip: "192.168.8.172",
    activity: "85.4 Kbps",
    download: "36.1 Kbps",
    upload: "49.4 Kbps",
    usage: "5.36 GB",
    uptime: "8d 20m 11s",
  },
];

interface ClientsViewProps {
  onDeviceClick?: (device: Device) => void;
}

interface Device {
  name: string;
  type: string;
  ip: string;
  mac: string;
  vendor: string;
  uptime: string;
  experience: string;
}

export function ClientsView({ onDeviceClick }: ClientsViewProps) {
  return (
    <div className="flex h-full flex-col">
      {/* Top Bar */}
      <div className="flex items-center gap-4 border-b border-gray-800 bg-[#1E293B] px-6 py-4">
        <button className="flex items-center gap-2 rounded-lg bg-blue-500 px-4 py-2 text-sm font-medium">
          <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
            <path d="M3 13h2v-2H3v2zm0 4h2v-2H3v2zm0-8h2V7H3v2zm4 4h14v-2H7v2zm0 4h14v-2H7v2zM7 7v2h14V7H7z" />
          </svg>
          Main
        </button>
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search"
            className="w-full rounded-lg bg-[#0F172A] py-2 pl-10 pr-4 text-sm text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto">
        <table className="w-full text-left text-xs">
          <thead className="sticky top-0 bg-[#1E293B] text-gray-400">
            <tr>
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Vendor</th>
              <th className="px-4 py-3">Connection</th>
              <th className="px-4 py-3">Network</th>
              <th className="px-4 py-3">WiFi</th>
              <th className="px-4 py-3">Experience</th>
              <th className="px-4 py-3">Technology</th>
              <th className="px-4 py-3">Channel</th>
              <th className="px-4 py-3">IP Address</th>
              <th className="px-4 py-3">Activity</th>
              <th className="px-4 py-3">Download</th>
              <th className="px-4 py-3">Upload</th>
              <th className="px-4 py-3">24h Usage</th>
              <th className="px-4 py-3">Uptime</th>
            </tr>
          </thead>
          <tbody>
            {clients.map((client, i) => (
              <tr
                key={i}
                onClick={() =>
                  onDeviceClick?.({
                    name: client.name,
                    type: client.technology,
                    ip: client.ip,
                    mac: "00:11:22:33:44:55",
                    vendor: client.vendor,
                    uptime: client.uptime,
                    experience: client.experience,
                  })
                }
                className="cursor-pointer border-b border-gray-800 hover:bg-[#1E293B]"
              >
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="h-2 w-2 rounded-full bg-green-500" />
                    {client.name}
                  </div>
                </td>
                <td className="px-4 py-3 text-gray-400">{client.vendor}</td>
                <td className="px-4 py-3">{client.connection}</td>
                <td className="px-4 py-3">{client.network}</td>
                <td className="px-4 py-3 text-gray-400">{client.wifi}</td>
                <td className="px-4 py-3 text-green-500">{client.experience}</td>
                <td className="px-4 py-3 text-cyan-500">{client.technology}</td>
                <td className="px-4 py-3 text-gray-400">{client.channel}</td>
                <td className="px-4 py-3">{client.ip}</td>
                <td className="px-4 py-3">{client.activity}</td>
                <td className="px-4 py-3 text-cyan-500">
                  {client.download !== "0 bps" && "↓"} {client.download}
                </td>
                <td className="px-4 py-3 text-purple-500">
                  {client.upload !== "0 bps" && "↑"} {client.upload}
                </td>
                <td className="px-4 py-3">{client.usage}</td>
                <td className="px-4 py-3 text-gray-400">{client.uptime}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
