import { NextResponse } from "next/server";

// MAS Backend URL - Docker container is running on port 8001
const MAS_BACKEND_URL = process.env.MAS_BACKEND_URL || "http://localhost:8001";
const UNIFI_API_URL = process.env.UNIFI_API_URL || "https://192.168.0.1:443/proxy/network/api";

interface UniFiDevice {
  name: string;
  model: string;
  mac: string;
  ip: string;
  status: string;
  device_type: string;
}

interface UniFiClient {
  name: string;
  mac: string;
  ip: string;
  network: string;
  is_wired: boolean;
  signal: number;
}

// Fetch real network data from MAS backend (which calls UniFi integration)
async function fetchRealNetworkData(): Promise<{
  devices: UniFiDevice[];
  clients: UniFiClient[];
  health: Record<string, unknown>;
}> {
  try {
    // Try to fetch from MAS backend
    const [devicesRes, clientsRes, healthRes] = await Promise.all([
      fetch(`${MAS_BACKEND_URL}/api/network/devices`, { 
        next: { revalidate: 30 },
        signal: AbortSignal.timeout(5000),
      }).catch(() => null),
      fetch(`${MAS_BACKEND_URL}/api/network/clients`, { 
        next: { revalidate: 30 },
        signal: AbortSignal.timeout(5000),
      }).catch(() => null),
      fetch(`${MAS_BACKEND_URL}/api/network/health`, { 
        next: { revalidate: 30 },
        signal: AbortSignal.timeout(5000),
      }).catch(() => null),
    ]);

    const devices = devicesRes?.ok ? await devicesRes.json() : [];
    const clients = clientsRes?.ok ? await clientsRes.json() : [];
    const health = healthRes?.ok ? await healthRes.json() : {};

    return { devices, clients, health };
  } catch (error) {
    console.error("Error fetching network data from MAS:", error);
    return { devices: [], clients: [], health: {} };
  }
}

// Mock data for development (includes MycoBrain)
function getMockNetworkData() {
  return {
    devices: [
      {
        name: "Wyyerd Fiber Gateway",
        model: "UDM-Pro",
        mac: "fc:ec:da:12:34:56",
        ip: "192.168.0.1",
        status: "online",
        device_type: "gateway",
      },
      {
        name: "MycoBrain-01",
        model: "Raspberry Pi 5",
        mac: "dc:a6:32:ab:cd:ef",
        ip: "192.168.0.100",
        status: "online",
        device_type: "mycobrain",
      },
      {
        name: "MYCA Server",
        model: "Custom Build",
        mac: "00:1a:2b:3c:4d:5e",
        ip: "192.168.0.10",
        status: "online",
        device_type: "server",
      },
      {
        name: "UniFi Switch 24",
        model: "USW-24-POE",
        mac: "fc:ec:da:78:90:ab",
        ip: "192.168.0.2",
        status: "online",
        device_type: "switch",
      },
      {
        name: "UniFi AP Pro",
        model: "U6-Pro",
        mac: "fc:ec:da:cd:ef:12",
        ip: "192.168.0.3",
        status: "online",
        device_type: "access_point",
      },
      {
        name: "NAS Storage",
        model: "Synology DS920+",
        mac: "00:11:32:ab:cd:ef",
        ip: "192.168.0.20",
        status: "online",
        device_type: "storage",
      },
    ],
    clients: [
      {
        name: "MycoBrain-01",
        mac: "dc:a6:32:ab:cd:ef",
        ip: "192.168.0.100",
        network: "IoT",
        is_wired: true,
        signal: 0,
      },
      {
        name: "MYCA-Workstation",
        mac: "00:1a:2b:11:22:33",
        ip: "192.168.0.50",
        network: "Main",
        is_wired: true,
        signal: 0,
      },
      {
        name: "Developer-Laptop",
        mac: "ac:de:48:00:11:22",
        ip: "192.168.0.51",
        network: "Main",
        is_wired: false,
        signal: -45,
      },
      {
        name: "Azure-Bridge",
        mac: "00:0d:3a:ab:cd:ef",
        ip: "192.168.0.60",
        network: "Main",
        is_wired: true,
        signal: 0,
      },
    ],
    health: {
      status: "healthy",
      latency: 5.2,
      download: 940,
      upload: 450,
      clients_online: 12,
      devices_online: 6,
    },
  };
}

export async function GET() {
  // Try to fetch real data first, fall back to mock data
  const realData = await fetchRealNetworkData();
  
  // If we got real data, use it; otherwise use mock
  const hasRealData = realData.devices.length > 0 || realData.clients.length > 0;
  const data = hasRealData ? realData : getMockNetworkData();

  return NextResponse.json({
    ...data,
    source: hasRealData ? "live" : "mock",
    timestamp: new Date().toISOString(),
  });
}

export async function POST(request: Request) {
  const body = await request.json();
  const { action, mac } = body;

  // Forward actions to MAS backend
  try {
    const response = await fetch(`${MAS_BACKEND_URL}/api/network/action`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, mac }),
    });

    if (response.ok) {
      const result = await response.json();
      return NextResponse.json(result);
    }
  } catch (error) {
    console.error("Error forwarding network action:", error);
  }

  return NextResponse.json({ 
    success: false, 
    error: "Failed to execute network action" 
  }, { status: 500 });
}
