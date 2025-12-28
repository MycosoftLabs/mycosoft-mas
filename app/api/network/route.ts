import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
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
    ],
    health: {
      status: "healthy",
      latency: 5.2,
      download: 940,
      upload: 450,
      clients_online: 12,
      devices_online: 6,
    },
    source: "mock",
    timestamp: new Date().toISOString(),
  });
}
