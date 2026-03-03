/**
 * Exec Handler -- spawn shell commands with PTY support inside sandbox.
 */

import { spawn, ChildProcess } from "child_process";

interface ExecResult {
  stdout: string;
  stderr: string;
  exit_code: number;
  duration_ms: number;
  pid?: number;
}

export class ExecHandler {
  private processes = new Map<number, ChildProcess>();
  private static MAX_CONCURRENT = 5;

  async execute(
    command: string,
    cwd?: string,
    env?: Record<string, string>,
  ): Promise<ExecResult> {
    if (this.processes.size >= ExecHandler.MAX_CONCURRENT) {
      throw new Error(`Max concurrent processes (${ExecHandler.MAX_CONCURRENT}) reached`);
    }

    const start = Date.now();
    const effectiveCwd = cwd ?? "/workspace";
    const effectiveEnv = { ...process.env, ...env };

    return new Promise<ExecResult>((resolve) => {
      let stdout = "";
      let stderr = "";

      const child = spawn("sh", ["-c", command], {
        cwd: effectiveCwd,
        env: effectiveEnv,
        stdio: ["pipe", "pipe", "pipe"],
      });

      const pid = child.pid ?? -1;
      if (pid > 0) this.processes.set(pid, child);

      child.stdout?.on("data", (data: Buffer) => {
        stdout += data.toString();
      });

      child.stderr?.on("data", (data: Buffer) => {
        stderr += data.toString();
      });

      child.on("close", (code) => {
        if (pid > 0) this.processes.delete(pid);
        resolve({
          stdout,
          stderr,
          exit_code: code ?? -1,
          duration_ms: Date.now() - start,
          pid,
        });
      });

      child.on("error", (err) => {
        if (pid > 0) this.processes.delete(pid);
        resolve({
          stdout,
          stderr: stderr + "\n" + String(err),
          exit_code: -1,
          duration_ms: Date.now() - start,
          pid,
        });
      });
    });
  }

  sendInput(pid: number, data: string): void {
    const child = this.processes.get(pid);
    if (child?.stdin?.writable) {
      child.stdin.write(data);
    }
  }

  kill(pid: number): void {
    const child = this.processes.get(pid);
    if (child) {
      child.kill("SIGTERM");
      this.processes.delete(pid);
    }
  }

  killAll(): void {
    for (const [pid, child] of this.processes) {
      child.kill("SIGTERM");
    }
    this.processes.clear();
  }
}
