"use client";
/**
 * Experiment Tracker Component
 * Tracks experiments through the closed-loop experimentation cycle
 * Created: February 3, 2026
 */

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

interface ExperimentStep {
  name: string;
  status: "pending" | "in_progress" | "completed" | "failed";
  startedAt?: string;
  completedAt?: string;
}

interface TrackedExperiment {
  id: string;
  name: string;
  hypothesisId?: string;
  status: string;
  currentStep: number;
  steps: ExperimentStep[];
  results?: Record<string, unknown>;
}

export function ExperimentTracker() {
  const [experiments, setExperiments] = useState<TrackedExperiment[]>([]);
  const [selectedExperiment, setSelectedExperiment] = useState<string | null>(null);

  useEffect(() => {
    fetchExperiments();
    const interval = setInterval(fetchExperiments, 10000);
    return () => clearInterval(interval);
  }, []);

  async function fetchExperiments() {
    try {
      const response = await fetch("/api/scientific/experiments");
      if (response.ok) {
        const data = await response.json();
        setExperiments(data.experiments || []);
      }
    } catch (error) {
      console.error("Failed to fetch experiments:", error);
    }
  }

  async function createExperiment() {
    try {
      const response = await fetch("/api/scientific/experiments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: "New Experiment", parameters: {} }),
      });
      if (response.ok) {
        fetchExperiments();
      }
    } catch (error) {
      console.error("Failed to create experiment:", error);
    }
  }

  const selected = experiments.find((e) => e.id === selectedExperiment);
  const progress = selected ? (selected.currentStep / selected.steps.length) * 100 : 0;

  return (
    <div className="grid gap-4 md:grid-cols-3">
      <Card className="md:col-span-1">
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            Experiments
            <Button size="sm" onClick={createExperiment}>New</Button>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {experiments.length === 0 ? (
              <p className="text-muted-foreground">No experiments</p>
            ) : (
              experiments.map((exp) => (
                <div
                  key={exp.id}
                  className={`p-2 border rounded cursor-pointer hover:bg-accent ${selectedExperiment === exp.id ? "bg-accent" : ""}`}
                  onClick={() => setSelectedExperiment(exp.id)}
                >
                  <p className="font-medium">{exp.name}</p>
                  <div className="flex items-center justify-between mt-1">
                    <Badge>{exp.status}</Badge>
                    <span className="text-xs text-muted-foreground">Step {exp.currentStep}/{exp.steps.length}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      <Card className="md:col-span-2">
        <CardHeader>
          <CardTitle>{selected ? selected.name : "Select an Experiment"}</CardTitle>
        </CardHeader>
        <CardContent>
          {selected ? (
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span>Progress</span>
                  <span>{Math.round(progress)}%</span>
                </div>
                <Progress value={progress} />
              </div>
              <div className="space-y-2">
                {selected.steps.map((step, idx) => (
                  <div key={idx} className="flex items-center gap-2 p-2 border rounded">
                    <div className={`w-3 h-3 rounded-full ${step.status === "completed" ? "bg-green-500" : step.status === "in_progress" ? "bg-blue-500" : "bg-gray-300"}`} />
                    <span className={step.status === "completed" ? "line-through text-muted-foreground" : ""}>{step.name}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-muted-foreground">Select an experiment to view details</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
