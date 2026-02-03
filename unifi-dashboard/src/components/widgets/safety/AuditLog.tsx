"use client";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Search, Filter } from "lucide-react";

interface AuditEntry {
  id: string;
  timestamp: string;
  user: string;
  action: string;
  resource: string;
  success: boolean;
  details?: string;
}

export function AuditLog() {
  const [search, setSearch] = useState("");
  const [actionFilter, setActionFilter] = useState("all");
  const [entries] = useState<AuditEntry[]>([
    { id: "1", timestamp: "2026-02-03 10:45:23", user: "admin", action: "START_EXPERIMENT", resource: "Experiment E-042", success: true },
    { id: "2", timestamp: "2026-02-03 10:42:15", user: "system", action: "SIMULATION_COMPLETE", resource: "AlphaFold Job 123", success: true },
    { id: "3", timestamp: "2026-02-03 10:38:00", user: "scientist1", action: "STIMULATE_FCI", resource: "Petraeus-001", success: true, details: "50mV, 100ms pulse" },
    { id: "4", timestamp: "2026-02-03 10:35:12", user: "admin", action: "ACCESS_DENIED", resource: "BSL-3 Lab", success: false, details: "Insufficient permissions" },
    { id: "5", timestamp: "2026-02-03 10:30:00", user: "system", action: "DEVICE_CONNECTED", resource: "Mushroom1-Alpha", success: true },
  ]);

  const filteredEntries = entries.filter((e) => {
    const matchesSearch = e.action.toLowerCase().includes(search.toLowerCase()) ||
      e.resource.toLowerCase().includes(search.toLowerCase()) ||
      e.user.toLowerCase().includes(search.toLowerCase());
    const matchesAction = actionFilter === "all" || e.action === actionFilter;
    return matchesSearch && matchesAction;
  });

  const uniqueActions = [...new Set(entries.map((e) => e.action))];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Audit Log</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex gap-2 mb-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input placeholder="Search..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-10" />
          </div>
          <Select value={actionFilter} onValueChange={setActionFilter}>
            <SelectTrigger className="w-48">
              <Filter className="h-4 w-4 mr-2" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Actions</SelectItem>
              {uniqueActions.map((action) => (
                <SelectItem key={action} value={action}>{action}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <ScrollArea className="h-64">
          <div className="space-y-2">
            {filteredEntries.map((entry) => (
              <div key={entry.id} className="p-3 border rounded-lg text-sm">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <Badge variant={entry.success ? "default" : "destructive"}>{entry.action}</Badge>
                    <span className="font-medium">{entry.resource}</span>
                  </div>
                  <span className="text-xs text-muted-foreground">{entry.timestamp}</span>
                </div>
                <div className="flex items-center justify-between text-muted-foreground">
                  <span>User: {entry.user}</span>
                  {entry.details && <span>{entry.details}</span>}
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
