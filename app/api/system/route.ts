import { NextResponse } from "next/server";

export async function GET() {
  // Return system stats - in production would use systeminformation package
  // For now return mock data that matches expected format
  return NextResponse.json({
    cpu: {
      usage: 12.5,
      cores: 8,
      model: "Intel Core i7",
      speed: 3.6,
    },
    memory: {
      total: 17179869184, // 16GB
      used: 8589934592,   // 8GB
      free: 8589934592,
      usedPercent: 50,
    },
    disk: {
      total: 512000000000,
      used: 256000000000,
      free: 256000000000,
      usedPercent: 50,
    },
    network: {
      interfaces: [],
      totalRx: 0,
      totalTx: 0,
    },
    os: {
      platform: "win32",
      distro: "Windows",
      release: "10",
      hostname: "MycoComp",
      uptime: 86400,
    },
    docker: {
      running: 3,
      paused: 0,
      stopped: 1,
      containers: [
        { name: "mycosoft-mas-n8n-1", state: "running", image: "n8nio/n8n", ports: ["5678:5678"] },
        { name: "mycosoft-mas-redis-1", state: "running", image: "redis:alpine", ports: ["6379:6379"] },
        { name: "mycosoft-mas-postgres-1", state: "running", image: "postgres:15", ports: ["5432:5432"] },
      ],
    },
    processes: {
      total: 250,
      running: 5,
      sleeping: 245,
    },
  });
}
