/**
 * MYCA Sandbox Node Daemon
 *
 * Runs inside each ephemeral sandbox container. Connects outbound to the
 * Gateway Control Plane via WebSocket and dispatches incoming tool requests
 * to the appropriate handler (exec, browser, fs).
 */

import { GatewayConnection } from "./websocket-client.js";
import { ExecHandler } from "./exec-handler.js";
import { BrowserHandler } from "./browser-handler.js";
import { FsHandler } from "./fs-handler.js";

const GATEWAY_URL = process.env.GATEWAY_URL ?? "ws://192.168.0.191:9000/ws/sandbox/default";
const SANDBOX_TOKEN = process.env.SANDBOX_TOKEN ?? "";
const SANDBOX_ID = process.env.SANDBOX_ID ?? "unknown";

const exec = new ExecHandler();
const browser = new BrowserHandler();
const fs = new FsHandler();

async function main(): Promise<void> {
  console.log(`[daemon] Starting sandbox daemon (id=${SANDBOX_ID})`);

  const gw = new GatewayConnection(GATEWAY_URL, SANDBOX_ID, SANDBOX_TOKEN);

  gw.onMessage(async (msg) => {
    const { id, type, payload } = msg;
    let response: Record<string, unknown>;

    try {
      switch (type) {
        case "exec":
        case "code_execute":
          response = await exec.execute(
            payload.command as string,
            payload.cwd as string | undefined,
            payload.env as Record<string, string> | undefined,
          );
          break;

        case "exec_input":
          exec.sendInput(payload.pid as number, payload.data as string);
          response = { ok: true };
          break;

        case "exec_kill":
          exec.kill(payload.pid as number);
          response = { ok: true };
          break;

        case "browser":
          response = await browser.handle(payload as Record<string, unknown>);
          break;

        case "fs":
          response = await fs.handle(payload as Record<string, unknown>);
          break;

        default:
          response = { error: `Unknown message type: ${type}` };
      }

      gw.send({ id, type: "result", payload: response });
    } catch (err) {
      gw.send({
        id,
        type: "error",
        payload: { error: String(err) },
      });
    }
  });

  await gw.connect();

  const heartbeat = setInterval(() => {
    gw.send({ id: "heartbeat", type: "heartbeat", payload: { sandbox_id: SANDBOX_ID } });
  }, 10_000);

  const shutdown = async () => {
    console.log("[daemon] Shutting down...");
    clearInterval(heartbeat);
    await browser.close();
    exec.killAll();
    gw.close();
    process.exit(0);
  };

  process.on("SIGTERM", shutdown);
  process.on("SIGINT", shutdown);
}

main().catch((err) => {
  console.error("[daemon] Fatal error:", err);
  process.exit(1);
});
