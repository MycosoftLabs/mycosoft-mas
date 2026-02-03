"use client";
import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Play, Pause, Square, Zap } from "lucide-react";

interface FCISession {
  id: string;
  species: string;
  strain?: string;
  status: "recording" | "stimulating" | "idle" | "paused";
  duration: number;
  electrodesActive: number;
  totalElectrodes: number;
}

export function FCIMonitor() {
  const [sessions, setSessions] = useState<FCISession[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSessions();
    const interval = setInterval(fetchSessions, 2000);
    return () => clearInterval(interval);
  }, []);

  async function fetchSessions() {
    try {
      const response = await fetch("/api/bio/fci");
      if (response.ok) {
        const data = await response.json();
        setSessions(data.sessions || []);
      }
    } catch (error) {
      console.error("Failed to fetch FCI sessions:", error);
    } finally {
      setLoading(false);
    }
  }

  async function controlSession(sessionId: string, action: string) {
    try {
      await fetch(`/api/bio/fci/${sessionId}/${action}`, { method: "POST" });
      fetchSessions();
    } catch (error) {
      console.error(`Failed to ${action} session:`, error);
    }
  }

  const statusColors = {
    recording: "bg-red-500 animate-pulse",
    stimulating: "bg-yellow-500 animate-pulse",
    idle: "bg-gray-500",
    paused: "bg-blue-500",
  };

  if (loading) {
    return <Card><CardContent className="p-8 text-center">Loading FCI sessions...</CardContent></Card>;
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>FCI Sessions</CardTitle>
          <Button size="sm">New Session</Button>
        </div>
      </CardHeader>
      <CardContent>
        {sessions.length === 0 ? (
          <p className="text-center text-muted-foreground py-4">No active FCI sessions</p>
        ) : (
          <div className="space-y-3">
            {sessions.map((session) => (
              <div key={session.id} className="p-3 border rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <p className="font-medium">{session.species}</p>
                    {session.strain && <p className="text-sm text-muted-foreground">{session.strain}</p>}
                  </div>
                  <Badge className={statusColors[session.status]}>{session.status}</Badge>
                </div>
                <div className="flex items-center justify-between text-sm text-muted-foreground mb-2">
                  <span>Duration: {Math.floor(session.duration / 60)}m {session.duration % 60}s</span>
                  <span>Electrodes: {session.electrodesActive}/{session.totalElectrodes}</span>
                </div>
                <div className="flex gap-2">
                  {session.status === "recording" || session.status === "stimulating" ? (
                    <>
                      <Button size="sm" variant="outline" onClick={() => controlSession(session.id, "pause")}><Pause className="h-4 w-4" /></Button>
                      <Button size="sm" variant="outline" onClick={() => controlSession(session.id, "stop")}><Square className="h-4 w-4" /></Button>
                    </>
                  ) : (
                    <Button size="sm" variant="outline" onClick={() => controlSession(session.id, "start")}><Play className="h-4 w-4" /></Button>
                  )}
                  <Button size="sm" variant="outline" onClick={() => controlSession(session.id, "stimulate")}><Zap className="h-4 w-4" /></Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
