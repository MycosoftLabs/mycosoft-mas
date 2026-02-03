"use client";
import { useState, useCallback } from "react";

interface FCISession {
  id: string;
  species: string;
  status: string;
  duration: number;
}

interface SignalData {
  channel: number;
  samples: number[];
  timestamp: string;
}

export function useBio() {
  const [sessions, setSessions] = useState<FCISession[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSessions = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch("/api/bio/fci");
      if (response.ok) {
        const data = await response.json();
        setSessions(data.sessions || []);
      }
    } catch (e) {
      setError("Failed to fetch FCI sessions");
    } finally {
      setLoading(false);
    }
  }, []);

  const startSession = useCallback(async (species: string, strain?: string) => {
    try {
      const response = await fetch("/api/bio/fci", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ species, strain }),
      });
      if (response.ok) {
        await fetchSessions();
        return await response.json();
      }
    } catch (e) {
      setError("Failed to start session");
    }
    return null;
  }, [fetchSessions]);

  const controlSession = useCallback(async (id: string, action: "start" | "pause" | "stop" | "stimulate") => {
    try {
      const response = await fetch(`/api/bio/fci/${id}/${action}`, {
        method: "POST",
      });
      if (response.ok) {
        await fetchSessions();
        return true;
      }
    } catch (e) {
      setError(`Failed to ${action} session`);
    }
    return false;
  }, [fetchSessions]);

  const getSignals = useCallback(async (sessionId: string): Promise<SignalData[]> => {
    try {
      const response = await fetch(`/api/bio/fci/${sessionId}/signals`);
      if (response.ok) {
        return (await response.json()).signals || [];
      }
    } catch (e) {
      setError("Failed to fetch signals");
    }
    return [];
  }, []);

  return {
    sessions,
    loading,
    error,
    fetchSessions,
    startSession,
    controlSession,
    getSignals,
  };
}
