"use client";

import { useState, useRef, useEffect, KeyboardEvent } from "react";
import Link from "next/link";
import { Terminal, ArrowLeft, Copy, Trash2 } from "lucide-react";

interface CommandResult {
  id: string;
  command: string;
  output: string;
  error?: boolean;
  timestamp: Date;
}

const HELP_TEXT = `
Available commands:
  help          - Show this help message
  clear         - Clear the terminal
  status        - Show system status
  agents        - List all agents
  workflows     - List n8n workflows
  docker        - Show Docker container status
  network       - Show network information
  search <q>    - Search across all entities
  myca <msg>    - Send a message to MYCA
  
Tips:
  - Use up/down arrows to navigate command history
  - Type 'clear' to clear the screen
`;

export default function ShellPage() {
  const [command, setCommand] = useState("");
  const [history, setHistory] = useState<CommandResult[]>([]);
  const [commandHistory, setCommandHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [isProcessing, setIsProcessing] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const terminalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Focus input on mount
    inputRef.current?.focus();
    
    // Add welcome message
    setHistory([{
      id: "welcome",
      command: "",
      output: `
╔══════════════════════════════════════════════════════════════╗
║                    MYCOSOFT NatureOS Shell                   ║
║                      Version 1.0.0                           ║
╚══════════════════════════════════════════════════════════════╝

Welcome to the NatureOS terminal. Type 'help' for available commands.
`,
      timestamp: new Date(),
    }]);
  }, []);

  useEffect(() => {
    // Scroll to bottom when history changes
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [history]);

  const executeCommand = async (cmd: string) => {
    const trimmedCmd = cmd.trim();
    if (!trimmedCmd) return;

    const resultId = Date.now().toString();
    setIsProcessing(true);

    // Add command to history
    setCommandHistory((prev) => [...prev.filter((c) => c !== trimmedCmd), trimmedCmd]);
    setHistoryIndex(-1);

    let output = "";
    let error = false;

    try {
      const [mainCmd, ...args] = trimmedCmd.split(" ");
      const arg = args.join(" ");

      switch (mainCmd.toLowerCase()) {
        case "help":
          output = HELP_TEXT;
          break;

        case "clear":
          setHistory([]);
          setIsProcessing(false);
          return;

        case "status": {
          const res = await fetch("/api/system");
          if (res.ok) {
            const data = await res.json();
            output = `
System Status:
  Hostname:   ${data.os?.hostname || "Unknown"}
  Platform:   ${data.os?.platform || "Unknown"}
  CPU Usage:  ${data.cpu?.usage?.toFixed(1) || 0}%
  Memory:     ${((data.memory?.used || 0) / 1024 / 1024 / 1024).toFixed(1)} GB / ${((data.memory?.total || 0) / 1024 / 1024 / 1024).toFixed(1)} GB
  Docker:     ${data.docker?.running || 0} containers running
`;
          } else {
            output = "Failed to fetch system status";
            error = true;
          }
          break;
        }

        case "agents": {
          const res = await fetch("/api/agents");
          if (res.ok) {
            const agents = await res.json();
            if (agents.length === 0) {
              output = "No agents found.";
            } else {
              output = `Agents (${agents.length} total):\n\n`;
              agents.forEach((agent: { name: string; status: string; category: string }) => {
                const statusIcon = agent.status === "online" ? "●" : "○";
                output += `  ${statusIcon} ${agent.name.padEnd(25)} [${agent.category}] ${agent.status}\n`;
              });
            }
          } else {
            output = "Failed to fetch agents";
            error = true;
          }
          break;
        }

        case "workflows": {
          const res = await fetch("/api/n8n");
          if (res.ok) {
            const data = await res.json();
            const workflows = data.local?.workflows || [];
            if (workflows.length === 0) {
              output = "No workflows found. Is n8n running?";
            } else {
              output = `n8n Workflows (${workflows.length} total):\n\n`;
              workflows.forEach((wf: { name: string; active: boolean; id: string }) => {
                const status = wf.active ? "[ACTIVE]" : "[INACTIVE]";
                output += `  ${wf.name.padEnd(30)} ${status}\n`;
              });
            }
          } else {
            output = "Failed to fetch workflows";
            error = true;
          }
          break;
        }

        case "docker": {
          const res = await fetch("/api/system");
          if (res.ok) {
            const data = await res.json();
            const containers = data.docker?.containers || [];
            if (containers.length === 0) {
              output = "No Docker containers found.";
            } else {
              output = `Docker Containers:\n\n`;
              containers.forEach((c: { name: string; state: string; image: string }) => {
                const stateIcon = c.state === "running" ? "●" : "○";
                output += `  ${stateIcon} ${c.name.padEnd(25)} ${c.state.padEnd(10)} ${c.image}\n`;
              });
            }
          } else {
            output = "Failed to fetch Docker status";
            error = true;
          }
          break;
        }

        case "network": {
          const res = await fetch("/api/network");
          if (res.ok) {
            const data = await res.json();
            output = `
Network Status:
  Source:     ${data.source || "unknown"}
  Devices:    ${data.devices?.length || 0}
  Clients:    ${data.clients?.length || 0}
  Health:     ${data.health?.status || "unknown"}
  Latency:    ${data.health?.latency || 0}ms
`;
          } else {
            output = "Failed to fetch network status";
            error = true;
          }
          break;
        }

        case "search": {
          if (!arg) {
            output = "Usage: search <query>";
            error = true;
          } else {
            const res = await fetch(`/api/search?q=${encodeURIComponent(arg)}`);
            if (res.ok) {
              const data = await res.json();
              if (data.results?.length === 0) {
                output = `No results found for "${arg}"`;
              } else {
                output = `Search results for "${arg}":\n\n`;
                data.results.forEach((r: { name: string; type: string; subtitle: string }) => {
                  output += `  [${r.type.toUpperCase()}] ${r.name}\n`;
                  output += `           ${r.subtitle}\n\n`;
                });
              }
            } else {
              output = "Search failed";
              error = true;
            }
          }
          break;
        }

        case "myca": {
          if (!arg) {
            output = "Usage: myca <message>";
            error = true;
          } else {
            output = `MYCA: I received your message: "${arg}"\n(Full MYCA chat integration coming soon)`;
          }
          break;
        }

        default:
          output = `Command not found: ${mainCmd}\nType 'help' for available commands.`;
          error = true;
      }
    } catch (e) {
      output = `Error: ${e instanceof Error ? e.message : "Unknown error"}`;
      error = true;
    }

    setHistory((prev) => [
      ...prev,
      {
        id: resultId,
        command: trimmedCmd,
        output,
        error,
        timestamp: new Date(),
      },
    ]);
    setIsProcessing(false);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      executeCommand(command);
      setCommand("");
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (commandHistory.length > 0) {
        const newIndex = historyIndex + 1;
        if (newIndex < commandHistory.length) {
          setHistoryIndex(newIndex);
          setCommand(commandHistory[commandHistory.length - 1 - newIndex]);
        }
      }
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      if (historyIndex > 0) {
        const newIndex = historyIndex - 1;
        setHistoryIndex(newIndex);
        setCommand(commandHistory[commandHistory.length - 1 - newIndex]);
      } else if (historyIndex === 0) {
        setHistoryIndex(-1);
        setCommand("");
      }
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="border-b border-gray-700/50 bg-gray-900/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/natureos" className="p-2 hover:bg-gray-800 rounded-lg transition-colors">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-green-500/20">
                <Terminal className="w-6 h-6 text-green-400" />
              </div>
              <div>
                <h1 className="text-xl font-bold">Shell</h1>
                <p className="text-xs text-gray-400">NatureOS Terminal</p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setHistory([])}
              className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
              title="Clear"
            >
              <Trash2 className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      {/* Terminal */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
        <div
          ref={terminalRef}
          className="bg-black rounded-xl border border-gray-700 font-mono text-sm h-[calc(100vh-180px)] overflow-auto"
          onClick={() => inputRef.current?.focus()}
        >
          <div className="p-4 min-h-full">
            {/* Command History */}
            {history.map((item) => (
              <div key={item.id} className="mb-4">
                {item.command && (
                  <div className="flex items-center gap-2 text-green-400">
                    <span className="text-blue-400">mycosoft@natureos</span>
                    <span className="text-gray-500">:</span>
                    <span className="text-purple-400">~</span>
                    <span className="text-gray-500">$</span>
                    <span className="text-white">{item.command}</span>
                  </div>
                )}
                <pre className={`whitespace-pre-wrap mt-1 ${item.error ? "text-red-400" : "text-gray-300"}`}>
                  {item.output}
                </pre>
              </div>
            ))}

            {/* Current Input */}
            <div className="flex items-center gap-2 text-green-400">
              <span className="text-blue-400">mycosoft@natureos</span>
              <span className="text-gray-500">:</span>
              <span className="text-purple-400">~</span>
              <span className="text-gray-500">$</span>
              <input
                ref={inputRef}
                type="text"
                value={command}
                onChange={(e) => setCommand(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isProcessing}
                className="flex-1 bg-transparent outline-none text-white caret-green-400"
                autoFocus
                spellCheck={false}
              />
              {isProcessing && <span className="text-yellow-400 animate-pulse">...</span>}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
