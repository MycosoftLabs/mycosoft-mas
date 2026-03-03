/**
 * WebSocket client that connects outbound to the Gateway Control Plane.
 * Handles reconnection with exponential backoff.
 */

import WebSocket from "ws";

export interface DaemonMessage {
  id: string;
  type: string;
  payload: Record<string, unknown>;
}

type MessageHandler = (msg: DaemonMessage) => Promise<void>;

export class GatewayConnection {
  private ws: WebSocket | null = null;
  private handler: MessageHandler | null = null;
  private reconnectDelay = 1000;
  private maxReconnectDelay = 30_000;
  private shouldReconnect = true;

  constructor(
    private readonly url: string,
    private readonly sandboxId: string,
    private readonly token: string,
  ) {}

  onMessage(handler: MessageHandler): void {
    this.handler = handler;
  }

  async connect(): Promise<void> {
    return new Promise<void>((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url, {
          headers: {
            "X-Sandbox-Id": this.sandboxId,
            "X-Sandbox-Token": this.token,
          },
        });

        this.ws.on("open", () => {
          console.log(`[ws] Connected to gateway: ${this.url}`);
          this.reconnectDelay = 1000;

          this.send({
            id: "handshake",
            type: "handshake",
            payload: { role: "node", sandbox_id: this.sandboxId, token: this.token },
          });

          resolve();
        });

        this.ws.on("message", (data) => {
          try {
            const msg = JSON.parse(data.toString()) as DaemonMessage;
            this.handler?.(msg);
          } catch (err) {
            console.error("[ws] Failed to parse message:", err);
          }
        });

        this.ws.on("close", () => {
          console.log("[ws] Connection closed");
          this.scheduleReconnect();
        });

        this.ws.on("error", (err) => {
          console.error("[ws] Error:", err.message);
        });
      } catch (err) {
        reject(err);
      }
    });
  }

  send(msg: DaemonMessage): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    }
  }

  close(): void {
    this.shouldReconnect = false;
    this.ws?.close();
  }

  private scheduleReconnect(): void {
    if (!this.shouldReconnect) return;
    console.log(`[ws] Reconnecting in ${this.reconnectDelay}ms...`);
    setTimeout(() => {
      this.connect().catch(() => {
        this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
        this.scheduleReconnect();
      });
    }, this.reconnectDelay);
  }
}
