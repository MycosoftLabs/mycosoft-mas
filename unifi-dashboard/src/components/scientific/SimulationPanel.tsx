"use client";
/**
 * Simulation Panel Component
 * Manages and displays scientific simulations
 * Created: February 3, 2026
 */

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface Simulation {
  id: string;
  type: string;
  name: string;
  status: "queued" | "running" | "completed" | "failed";
  progress: number;
  startedAt?: string;
  completedAt?: string;
  results?: Record<string, unknown>;
}

export function SimulationPanel() {
  const [simulations, setSimulations] = useState<Simulation[]>([]);
  const [activeTab, setActiveTab] = useState("protein");

  async function startSimulation(type: string) {
    try {
      const response = await fetch("/api/scientific/simulation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type, config: {} }),
      });
      if (response.ok) {
        const data = await response.json();
        setSimulations([...simulations, data.simulation]);
      }
    } catch (error) {
      console.error("Failed to start simulation:", error);
    }
  }

  const simulationTypes = [
    { id: "protein", label: "Protein Folding", description: "AlphaFold/BoltzGen structure prediction" },
    { id: "mycelium", label: "Mycelium Growth", description: "Fungal network simulation" },
    { id: "metabolic", label: "Metabolic Flux", description: "COBRA pathway analysis" },
    { id: "molecular", label: "Molecular Dynamics", description: "OpenMM simulation" },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Simulation Center</CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-4">
            {simulationTypes.map((sim) => (
              <TabsTrigger key={sim.id} value={sim.id}>{sim.label}</TabsTrigger>
            ))}
          </TabsList>
          
          {simulationTypes.map((sim) => (
            <TabsContent key={sim.id} value={sim.id} className="mt-4">
              <div className="space-y-4">
                <p className="text-muted-foreground">{sim.description}</p>
                <Button onClick={() => startSimulation(sim.id)}>
                  Start {sim.label} Simulation
                </Button>
                
                <div className="mt-4 space-y-2">
                  <h4 className="font-medium">Recent Simulations</h4>
                  {simulations.filter(s => s.type === sim.id).length === 0 ? (
                    <p className="text-sm text-muted-foreground">No simulations of this type</p>
                  ) : (
                    simulations.filter(s => s.type === sim.id).map((s) => (
                      <div key={s.id} className="flex items-center justify-between p-2 border rounded">
                        <span>{s.name || s.id.slice(0, 8)}</span>
                        <Badge>{s.status}</Badge>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </TabsContent>
          ))}
        </Tabs>
      </CardContent>
    </Card>
  );
}
