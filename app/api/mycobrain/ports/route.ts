import { NextRequest, NextResponse } from "next/server";

const MYCOBRAIN_SERVICE_URL = process.env.MYCOBRAIN_SERVICE_URL || "http://localhost:8003";
const SERVICE_TIMEOUT_MS = 2500;
const FALLBACK_TIMEOUT_MS = 4000;

export async function GET(request: NextRequest) {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), SERVICE_TIMEOUT_MS);

    const response = await fetch(`${MYCOBRAIN_SERVICE_URL}/ports`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      // Prevent Next fetch cache/revalidate from ever causing a hang.
      cache: "no-store",
      signal: controller.signal,
    }).finally(() => clearTimeout(timeout));

    if (!response.ok) {
      throw new Error(`Port scan failed: ${response.statusText}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error("Error scanning ports:", error);
    // Fallback: try to use local Python script
    try {
      const { exec } = require("child_process");
      const { promisify } = require("util");
      const execAsync = promisify(exec);
      
      const { stdout } = await execAsync("python scripts/scan_usb_devices.py --json", {
        timeout: FALLBACK_TIMEOUT_MS,
        windowsHide: true,
      });
      const scanResult = JSON.parse(stdout);
      
      return NextResponse.json({
        ports: scanResult.all_ports || [],
        discovery_running: false,
        timestamp: new Date().toISOString(),
      });
    } catch (fallbackError: any) {
      return NextResponse.json(
        { 
          error: error.message || "Failed to scan ports",
          ports: [],
          discovery_running: false,
          timestamp: new Date().toISOString()
        },
        { status: 500 }
      );
    }
  }
}

