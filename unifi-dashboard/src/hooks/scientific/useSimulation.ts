"use client";
import { useState, useCallback } from "react";

interface Simulation {
  id: string;
  type: string;
  name: string;
  status: string;
  progress: number;
}

interface SimulationConfig {
  type: string;
  name?: string;
  config: Record<string, unknown>;
}

export function useSimulation() {
  const [simulations, setSimulations] = useState<Simulation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSimulations = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch("/api/scientific/simulation");
      if (response.ok) {
        const data = await response.json();
        setSimulations(data.simulations || []);
      }
    } catch (e) {
      setError("Failed to fetch simulations");
    } finally {
      setLoading(false);
    }
  }, []);

  const startSimulation = useCallback(async (config: SimulationConfig) => {
    try {
      const response = await fetch("/api/scientific/simulation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      if (response.ok) {
        await fetchSimulations();
        return await response.json();
      }
    } catch (e) {
      setError("Failed to start simulation");
    }
    return null;
  }, [fetchSimulations]);

  const controlSimulation = useCallback(async (id: string, action: "pause" | "resume" | "cancel") => {
    try {
      const response = await fetch(`/api/scientific/simulation/${id}/${action}`, {
        method: "POST",
      });
      if (response.ok) {
        await fetchSimulations();
        return true;
      }
    } catch (e) {
      setError(`Failed to ${action} simulation`);
    }
    return false;
  }, [fetchSimulations]);

  const getResults = useCallback(async (id: string) => {
    try {
      const response = await fetch(`/api/scientific/simulation/${id}/results`);
      if (response.ok) {
        return await response.json();
      }
    } catch (e) {
      setError("Failed to fetch results");
    }
    return null;
  }, []);

  return {
    simulations,
    loading,
    error,
    fetchSimulations,
    startSimulation,
    controlSimulation,
    getResults,
  };
}
