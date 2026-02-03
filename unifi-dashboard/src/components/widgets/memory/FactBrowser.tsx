"use client";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Search, Database, User, Globe } from "lucide-react";

interface Fact {
  id: string;
  key: string;
  value: string;
  scope: "user" | "system" | "agent";
  source: string;
  confidence: number;
  updatedAt: string;
}

export function FactBrowser() {
  const [search, setSearch] = useState("");
  const [facts] = useState<Fact[]>([
    { id: "1", key: "preferred_temperature", value: "25Â°C", scope: "user", source: "User preference", confidence: 1, updatedAt: "Today" },
    { id: "2", key: "pleurotus_optimal_humidity", value: "85-95%", scope: "system", source: "MINDEX", confidence: 0.95, updatedAt: "Yesterday" },
    { id: "3", key: "current_experiment", value: "E-042: Bioelectric mapping", scope: "agent", source: "Experiment Loop", confidence: 1, updatedAt: "1 hour ago" },
    { id: "4", key: "alphafold_version", value: "2.3.2", scope: "system", source: "Configuration", confidence: 1, updatedAt: "Last week" },
  ]);

  const scopeIcons = {
    user: <User className="h-4 w-4" />,
    system: <Database className="h-4 w-4" />,
    agent: <Globe className="h-4 w-4" />,
  };

  const scopeColors = {
    user: "bg-blue-500",
    system: "bg-purple-500",
    agent: "bg-green-500",
  };

  const filteredFacts = facts.filter((f) =>
    f.key.toLowerCase().includes(search.toLowerCase()) ||
    f.value.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle>Fact Browser</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input placeholder="Search facts..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-10" />
        </div>
        <ScrollArea className="h-64">
          <div className="space-y-2">
            {filteredFacts.map((fact) => (
              <div key={fact.id} className="p-3 border rounded-lg">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    {scopeIcons[fact.scope]}
                    <span className="font-mono text-sm">{fact.key}</span>
                  </div>
                  <Badge className={scopeColors[fact.scope]}>{fact.scope}</Badge>
                </div>
                <p className="text-sm font-medium">{fact.value}</p>
                <div className="flex items-center justify-between text-xs text-muted-foreground mt-1">
                  <span>Source: {fact.source}</span>
                  <span>Confidence: {(fact.confidence * 100).toFixed(0)}%</span>
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
