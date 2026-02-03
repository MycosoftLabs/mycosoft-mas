"use client";
import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Pause, Play, X, Eye } from "lucide-react";

interface Simulation {
  id: string;
  name: string;
  type: string;
  status: "queued" | "running" | "completed" | "failed" | "paused";
  progress: number;
  eta?: string;
  startedAt?: string;
}

export function SimulationProgress() {
  const [simulations, setSimulations] = useState<Simulation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSimulations();
    const interval = setInterval(fetchSimulations, 3000);
    return () => clearInterval(interval);
  }, []);

  async function fetchSimulations() {
    try {
      const response = await fetch("/api/scientific/simulation");
      if (response.ok) {
        const data = await response.json();
        setSimulations(data.simulations || []);
      }
    } catch (error) {
      console.error("Failed to fetch simulations:", error);
    } finally {
      setLoading(false);
    }
  }

  async function controlSimulation(id: string, action: string) {
    try {
      await fetch(`/api/scientific/simulation/${id}/${action}`, { method: "POST" });
      fetchSimulations();
    } catch (error) {
      console.error(`Failed to ${action} simulation:`, error);
    }
  }

  const statusColors = {
    queued: "bg-gray-500",
    running: "bg-blue-500 animate-pulse",
    completed: "bg-green-500",
    failed: "bg-red-500",
    paused: "bg-yellow-500",
  };

  const typeIcons: Record<string, string> = {
    protein: "ðŸ§¬",
    mycelium: "ðŸ„",
    molecular: "âš›ï¸",
    physics: "ðŸ”¬",
    metabolic: "ðŸ”„",
  };

  if (loading) {
    return <Card><CardContent className="p-8 text-center">Loading simulations...</CardContent></Card>;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Active Simulations</CardTitle>
      </CardHeader>
      <CardContent>
        {simulations.length === 0 ? (
          <p className="text-center text-muted-foreground py-4">No simulations running</p>
        ) : (
          <div className="space-y-4">
            {simulations.map((sim) => (
              <div key={sim.id} className="p-4 border rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xl">{typeIcons[sim.type] || "ðŸ“Š"}</span>
                    <div>
                      <p className="font-medium">{sim.name}</p>
                      <p className="text-sm text-muted-foreground capitalize">{sim.type}</p>
                    </div>
                  </div>
                  <Badge className={statusColors[sim.status]}>{sim.status}</Badge>
                </div>
                <div className="mb-2">
                  <div className="flex justify-between text-sm mb-1">
                    <span>{sim.progress}%</span>
                    {sim.eta && <span className="text-muted-foreground">ETA: {sim.eta}</span>}
                  </div>
                  <Progress value={sim.progress} />
                </div>
                <div className="flex gap-2">
                  {sim.status === "running" ? (
                    <Button size="sm" variant="outline" onClick={() => controlSimulation(sim.id, "pause")}><Pause className="h-4 w-4" /></Button>
                  ) : sim.status === "paused" ? (
                    <Button size="sm" variant="outline" onClick={() => controlSimulation(sim.id, "resume")}><Play className="h-4 w-4" /></Button>
                  ) : null}
                  {sim.status !== "completed" && sim.status !== "failed" && (
                    <Button size="sm" variant="outline" onClick={() => controlSimulation(sim.id, "cancel")}><X className="h-4 w-4" /></Button>
                  )}
                  {sim.status === "completed" && (
                    <Button size="sm" variant="outline"><Eye className="h-4 w-4 mr-1" /> Results</Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
