"use client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Settings, Activity, Wifi, WifiOff } from "lucide-react";

interface DeviceCardProps {
  device: {
    id: string;
    name: string;
    type: string;
    status: "online" | "offline" | "busy" | "error" | "maintenance";
    lastSeen?: string;
    batteryLevel?: number;
    signalStrength?: number;
  };
  onSelect?: (id: string) => void;
  onConfigure?: (id: string) => void;
}

export function DeviceCard({ device, onSelect, onConfigure }: DeviceCardProps) {
  const statusColors = {
    online: "bg-green-500",
    offline: "bg-gray-500",
    busy: "bg-blue-500",
    error: "bg-red-500",
    maintenance: "bg-yellow-500",
  };

  const deviceIcons: Record<string, string> = {
    mushroom1: "ðŸ„",
    myconode: "ðŸŒ±",
    sporebase: "ðŸŒ¸",
    petraeus: "ðŸ§«",
    trufflebot: "ðŸ¤–",
    alarm: "ðŸš¨",
    mycotenna: "ðŸ“¡",
  };

  return (
    <Card className="hover:shadow-lg transition-shadow cursor-pointer" onClick={() => onSelect?.(device.id)}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-2xl">{deviceIcons[device.type] || "ðŸ“Ÿ"}</span>
            <CardTitle className="text-lg">{device.name}</CardTitle>
          </div>
          <Badge className={statusColors[device.status]}>{device.status}</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Type</span>
            <span className="font-medium capitalize">{device.type}</span>
          </div>
          {device.batteryLevel !== undefined && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Battery</span>
              <span className="font-medium">{device.batteryLevel}%</span>
            </div>
          )}
          {device.signalStrength !== undefined && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Signal</span>
              <div className="flex items-center gap-1">
                {device.status === "online" ? <Wifi className="h-4 w-4" /> : <WifiOff className="h-4 w-4" />}
                <span className="font-medium">{device.signalStrength} dBm</span>
              </div>
            </div>
          )}
          {device.lastSeen && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Last seen</span>
              <span className="font-medium">{device.lastSeen}</span>
            </div>
          )}
        </div>
        <div className="flex gap-2 mt-4">
          <Button size="sm" variant="outline" className="flex-1" onClick={(e) => { e.stopPropagation(); onConfigure?.(device.id); }}>
            <Settings className="h-4 w-4 mr-1" /> Configure
          </Button>
          <Button size="sm" variant="outline">
            <Activity className="h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
