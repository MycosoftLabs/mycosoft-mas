"use client";
/**
 * Lab Monitor Component
 * Real-time monitoring of laboratory instruments and experiments
 * Created: February 3, 2026
 */

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

interface Instrument {
  id: string;
  name: string;
  type: string;
  status: "online" | "offline" | "busy" | "error";
  currentJob?: string;
  progress?: number;
}

interface Experiment {
  id: string;
  name: string;
  status: "running" | "completed" | "pending" | "failed";
  progress: number;
  startedAt: string;
}

export function LabMonitor() {
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchLabStatus();
    const interval = setInterval(fetchLabStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  async function fetchLabStatus() {
    try {
      const response = await fetch("/api/scientific/lab/status");
      if (response.ok) {
        const data = await response.json();
        setInstruments(data.instruments || []);
        setExperiments(data.experiments || []);
      }
    } catch (error) {
      console.error("Failed to fetch lab status:", error);
    } finally {
      setLoading(false);
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "online": case "completed": return "bg-green-500";
      case "offline": case "pending": return "bg-gray-500";
      case "busy": case "running": return "bg-blue-500";
      case "error": case "failed": return "bg-red-500";
      default: return "bg-gray-500";
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center p-8">Loading lab status...</div>;
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Instruments</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {instruments.length === 0 ? (
              <p className="text-muted-foreground">No instruments connected</p>
            ) : (
              instruments.map((inst) => (
                <div key={inst.id} className="flex items-center justify-between p-2 border rounded">
                  <div>
                    <p className="font-medium">{inst.name}</p>
                    <p className="text-sm text-muted-foreground">{inst.type}</p>
                  </div>
                  <Badge className={getStatusColor(inst.status)}>{inst.status}</Badge>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Active Experiments</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {experiments.length === 0 ? (
              <p className="text-muted-foreground">No active experiments</p>
            ) : (
              experiments.map((exp) => (
                <div key={exp.id} className="p-2 border rounded">
                  <div className="flex items-center justify-between mb-2">
                    <p className="font-medium">{exp.name}</p>
                    <Badge className={getStatusColor(exp.status)}>{exp.status}</Badge>
                  </div>
                  <Progress value={exp.progress} className="h-2" />
                  <p className="text-xs text-muted-foreground mt-1">{exp.progress}% complete</p>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
