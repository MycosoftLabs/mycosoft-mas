import { NextRequest, NextResponse } from "next/server";

const MYCOBRAIN_SERVICE_URL = process.env.MYCOBRAIN_SERVICE_URL || "http://localhost:8003";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { device_id, command, parameters, use_mdp = true } = body;

    if (!device_id || !command) {
      return NextResponse.json(
        { error: "device_id and command are required" },
        { status: 400 }
      );
    }

    // Build command payload
    const commandPayload = {
      command: {
        command_type: command,
        ...parameters,
      },
      use_mdp: use_mdp,
    };

    async function send(useMdp: boolean) {
      const payload = { ...commandPayload, use_mdp: useMdp };
      const response = await fetch(`${MYCOBRAIN_SERVICE_URL}/devices/${device_id}/command`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json().catch(() => ({}));
      return { response, data };
    }

    // Try requested protocol first. If MDP is requested but we get no response bytes,
    // automatically fall back to JSON so minimal firmware still works.
    const first = await send(Boolean(use_mdp));
    if (!first.response.ok) {
      const detail = first.data?.detail || first.data?.error || `Command failed: ${first.response.statusText}`;
      throw new Error(detail);
    }

    const shouldFallback =
      Boolean(use_mdp) &&
      (first.data?.response === null || first.data?.response === undefined || String(first.data?.response || "").trim().length === 0);

    if (shouldFallback) {
      const second = await send(false);
      if (second.response.ok)
        return NextResponse.json({ ...second.data, fallback_from_mdp: true });
    }

    return NextResponse.json(first.data);
  } catch (error: any) {
    console.error("Error sending MycoBrain command:", error);
    return NextResponse.json(
      { 
        error: error.message || "Command failed",
        status: "error"
      },
      { status: 500 }
    );
  }
}

