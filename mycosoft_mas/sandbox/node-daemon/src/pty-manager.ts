/**
 * PTY Manager -- manages pseudo-terminal sessions for interactive processes.
 */

import { spawn, ChildProcess } from "child_process";

interface PtySession {
  pid: number;
  child: ChildProcess;
  output: string[];
  createdAt: number;
}

type DataCallback = (pid: number, data: string) => void;

export class PtyManager {
  private sessions = new Map<number, PtySession>();
  private dataCallbacks: DataCallback[] = [];
  private static MAX_SESSIONS = 5;

  spawn(command: string, cwd?: string, env?: Record<string, string>): number {
    if (this.sessions.size >= PtyManager.MAX_SESSIONS) {
      throw new Error(`Max PTY sessions (${PtyManager.MAX_SESSIONS}) reached`);
    }

    const child = spawn("sh", ["-c", command], {
      cwd: cwd ?? "/workspace",
      env: { ...process.env, ...env, TERM: "xterm-256color" },
      stdio: ["pipe", "pipe", "pipe"],
    });

    const pid = child.pid ?? -1;
    if (pid <= 0) throw new Error("Failed to spawn PTY process");

    const session: PtySession = {
      pid,
      child,
      output: [],
      createdAt: Date.now(),
    };

    child.stdout?.on("data", (data: Buffer) => {
      const text = data.toString();
      session.output.push(text);
      if (session.output.length > 1000) session.output.shift();
      this.dataCallbacks.forEach((cb) => cb(pid, text));
    });

    child.stderr?.on("data", (data: Buffer) => {
      const text = data.toString();
      session.output.push(text);
      this.dataCallbacks.forEach((cb) => cb(pid, text));
    });

    child.on("close", () => {
      this.sessions.delete(pid);
    });

    this.sessions.set(pid, session);
    return pid;
  }

  write(pid: number, data: string): void {
    const session = this.sessions.get(pid);
    if (session?.child.stdin?.writable) {
      session.child.stdin.write(data);
    }
  }

  kill(pid: number): void {
    const session = this.sessions.get(pid);
    if (session) {
      session.child.kill("SIGTERM");
      this.sessions.delete(pid);
    }
  }

  onData(callback: DataCallback): void {
    this.dataCallbacks.push(callback);
  }

  getOutput(pid: number): string[] {
    return this.sessions.get(pid)?.output ?? [];
  }

  listSessions(): Array<{ pid: number; createdAt: number }> {
    return Array.from(this.sessions.values()).map((s) => ({
      pid: s.pid,
      createdAt: s.createdAt,
    }));
  }
}
