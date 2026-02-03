"use client";
import { useState, useEffect } from "react";
import { DeviceCard } from "./DeviceCard";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Search } from "lucide-react";

interface Device {
  id: string;
  name: string;
  type: string;
  status: "online" | "offline" | "busy" | "error" | "maintenance";
  lastSeen?: string;
  batteryLevel?: number;
  signalStrength?: number;
}

interface DeviceGridProps {
  onDeviceSelect?: (id: string) => void;
}

export function DeviceGrid({ onDeviceSelect }: DeviceGridProps) {
  const [devices, setDevices] = useState<Device[]>([]);
  const [filter, setFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDevices();
    const interval = setInterval(fetchDevices, 10000);
    return () => clearInterval(interval);
  }, []);

  async function fetchDevices() {
    try {
      const response = await fetch("/api/natureos/devices");
      if (response.ok) {
        const data = await response.json();
        setDevices(data.devices || []);
      }
    } catch (error) {
      console.error("Failed to fetch devices:", error);
    } finally {
      setLoading(false);
    }
  }

  const filteredDevices = devices.filter((device) => {
    const matchesSearch = device.name.toLowerCase().includes(filter.toLowerCase()) || device.type.toLowerCase().includes(filter.toLowerCase());
    const matchesType = typeFilter === "all" || device.type === typeFilter;
    const matchesStatus = statusFilter === "all" || device.status === statusFilter;
    return matchesSearch && matchesType && matchesStatus;
  });

  const deviceTypes = [...new Set(devices.map((d) => d.type))];

  if (loading) {
    return <div className="flex items-center justify-center p-8">Loading devices...</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input placeholder="Search devices..." value={filter} onChange={(e) => setFilter(e.target.value)} className="pl-10" />
        </div>
        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            {deviceTypes.map((type) => (
              <SelectItem key={type} value={type}>{type}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="online">Online</SelectItem>
            <SelectItem value="offline">Offline</SelectItem>
            <SelectItem value="busy">Busy</SelectItem>
            <SelectItem value="error">Error</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {filteredDevices.length === 0 ? (
        <div className="text-center p-8 text-muted-foreground">No devices found</div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {filteredDevices.map((device) => (
            <DeviceCard key={device.id} device={device} onSelect={onDeviceSelect} />
          ))}
        </div>
      )}
    </div>
  );
}
