"use client";
import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { AlertCircle, CheckCircle, Info, AlertTriangle } from "lucide-react";

interface Event {
  id: string;
  type: string;
  severity: "info" | "warning" | "error" | "success";
  message: string;
  timestamp: string;
  source?: string;
}

export function EventFeed() {
  const [events, setEvents] = useState<Event[]>([
    { id: "1", type: "device", severity: "success", message: "Mushroom1-A connected", timestamp: "2 min ago", source: "Device Manager" },
    { id: "2", type: "signal", severity: "info", message: "Pattern detected: oscillation", timestamp: "5 min ago", source: "Signal Processor" },
    { id: "3", type: "experiment", severity: "warning", message: "Experiment E-042 approaching timeout", timestamp: "10 min ago", source: "Experiment Loop" },
    { id: "4", type: "safety", severity: "error", message: "BSL-2 containment check required", timestamp: "15 min ago", source: "Biosafety Monitor" },
    { id: "5", type: "simulation", severity: "success", message: "AlphaFold prediction completed", timestamp: "20 min ago", source: "Simulation Service" },
  ]);

  const severityIcons = {
    info: <Info className="h-4 w-4 text-blue-500" />,
    warning: <AlertTriangle className="h-4 w-4 text-yellow-500" />,
    error: <AlertCircle className="h-4 w-4 text-red-500" />,
    success: <CheckCircle className="h-4 w-4 text-green-500" />,
  };

  const severityColors = {
    info: "bg-blue-500/10 text-blue-500",
    warning: "bg-yellow-500/10 text-yellow-500",
    error: "bg-red-500/10 text-red-500",
    success: "bg-green-500/10 text-green-500",
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Event Feed</CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-80">
          <div className="space-y-2">
            {events.map((event) => (
              <div key={event.id} className="flex items-start gap-3 p-3 border rounded-lg hover:bg-accent/50 transition-colors">
                {severityIcons[event.severity]}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium">{event.message}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="outline" className={severityColors[event.severity]}>{event.type}</Badge>
                    {event.source && <span className="text-xs text-muted-foreground">{event.source}</span>}
                  </div>
                </div>
                <span className="text-xs text-muted-foreground whitespace-nowrap">{event.timestamp}</span>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
