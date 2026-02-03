"use client";
/**
 * Hypothesis Board Component
 * Manages scientific hypotheses and their validation
 * Created: February 3, 2026
 */

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";

interface Hypothesis {
  id: string;
  statement: string;
  status: "untested" | "testing" | "validated" | "refuted" | "inconclusive";
  confidence: number;
  experiments: string[];
  createdAt: string;
}

export function HypothesisBoard() {
  const [hypotheses, setHypotheses] = useState<Hypothesis[]>([]);
  const [newHypothesis, setNewHypothesis] = useState("");

  async function createHypothesis() {
    if (!newHypothesis.trim()) return;
    try {
      const response = await fetch("/api/scientific/hypothesis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ statement: newHypothesis }),
      });
      if (response.ok) {
        const data = await response.json();
        setHypotheses([data.hypothesis, ...hypotheses]);
        setNewHypothesis("");
      }
    } catch (error) {
      console.error("Failed to create hypothesis:", error);
    }
  }

  async function testHypothesis(id: string) {
    try {
      const response = await fetch(`/api/scientific/hypothesis/${id}/test`, {
        method: "POST",
      });
      if (response.ok) {
        setHypotheses(hypotheses.map((h) =>
          h.id === id ? { ...h, status: "testing" } : h
        ));
      }
    } catch (error) {
      console.error("Failed to test hypothesis:", error);
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "validated": return "bg-green-500";
      case "refuted": return "bg-red-500";
      case "testing": return "bg-blue-500";
      case "inconclusive": return "bg-yellow-500";
      default: return "bg-gray-500";
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Hypothesis Board</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="flex gap-2">
            <Textarea
              placeholder="Enter a new hypothesis..."
              value={newHypothesis}
              onChange={(e) => setNewHypothesis(e.target.value)}
              className="flex-1"
            />
            <Button onClick={createHypothesis}>Add</Button>
          </div>

          <div className="space-y-3">
            {hypotheses.length === 0 ? (
              <p className="text-muted-foreground">No hypotheses yet. Add one above.</p>
            ) : (
              hypotheses.map((h) => (
                <div key={h.id} className="p-3 border rounded">
                  <div className="flex items-start justify-between mb-2">
                    <p className="flex-1">{h.statement}</p>
                    <Badge className={getStatusColor(h.status)}>{h.status}</Badge>
                  </div>
                  <div className="flex items-center justify-between text-sm text-muted-foreground">
                    <span>Confidence: {(h.confidence * 100).toFixed(0)}%</span>
                    <Button size="sm" variant="outline" onClick={() => testHypothesis(h.id)} disabled={h.status === "testing"}>
                      {h.status === "testing" ? "Testing..." : "Test"}
                    </Button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
