"use client";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Send, Terminal } from "lucide-react";

interface CommandHistory {
  id: string;
  command: string;
  target: string;
  status: "success" | "failed" | "pending";
  response?: string;
  timestamp: string;
}

export function CommandCenter() {
  const [command, setCommand] = useState("");
  const [target, setTarget] = useState("all");
  const [history, setHistory] = useState<CommandHistory[]>([]);

  const targets = [
    { value: "all", label: "All Devices" },
    { value: "mushroom1", label: "Mushroom1 Devices" },
    { value: "myconode", label: "MycoNode Probes" },
    { value: "sporebase", label: "SporeBase Collectors" },
    { value: "petraeus", label: "Petraeus Arrays" },
  ];

  const commonCommands = [
    { cmd: "status", label: "Get Status" },
    { cmd: "calibrate", label: "Calibrate" },
    { cmd: "restart", label: "Restart" },
    { cmd: "start_recording", label: "Start Recording" },
    { cmd: "stop_recording", label: "Stop Recording" },
  ];

  async function sendCommand() {
    if (!command.trim()) return;
    const newCmd: CommandHistory = {
      id: Date.now().toString(),
      command,
      target,
      status: "pending",
      timestamp: new Date().toLocaleTimeString(),
    };
    setHistory([newCmd, ...history]);
    setCommand("");
    
    setTimeout(() => {
      setHistory((prev) =>
        prev.map((c) => c.id === newCmd.id ? { ...c, status: "success", response: "Command executed successfully" } : c)
      );
    }, 1000);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><Terminal className="h-5 w-5" /> Command Center</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="flex gap-2">
            <Select value={target} onValueChange={setTarget}>
              <SelectTrigger className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {targets.map((t) => (
                  <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Input
              placeholder="Enter command..."
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendCommand()}
              className="flex-1"
            />
            <Button onClick={sendCommand}><Send className="h-4 w-4" /></Button>
          </div>

          <div className="flex flex-wrap gap-2">
            {commonCommands.map((c) => (
              <Button key={c.cmd} size="sm" variant="outline" onClick={() => setCommand(c.cmd)}>{c.label}</Button>
            ))}
          </div>

          <div className="border rounded-lg p-3 bg-muted/50 font-mono text-sm max-h-48 overflow-y-auto">
            {history.length === 0 ? (
              <p className="text-muted-foreground">No commands sent yet</p>
            ) : (
              history.map((h) => (
                <div key={h.id} className="mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">[{h.timestamp}]</span>
                    <Badge variant={h.status === "success" ? "default" : h.status === "failed" ? "destructive" : "secondary"}>{h.status}</Badge>
                    <span className="text-primary">{h.target}</span>
                    <span>&gt;</span>
                    <span>{h.command}</span>
                  </div>
                  {h.response && <p className="text-green-500 ml-4">{h.response}</p>}
                </div>
              ))
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
