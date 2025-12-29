import { NextResponse } from "next/server";

export async function GET() {
  try {
    // Aggregate data from multiple sources
    const [mycobrainDevices, earthScience, spaceWeather] = await Promise.allSettled([
      fetch(`${process.env.MAS_API_URL || "http://localhost:8001"}/api/mycobrain/devices`).catch(() => null),
      fetch(`${process.env.NEXT_PUBLIC_BASE_URL || "http://localhost:3000"}/api/mas/earth-science?action=earthquakes&limit=10`).catch(() => null),
      fetch(`${process.env.NEXT_PUBLIC_BASE_URL || "http://localhost:3000"}/api/mas/space-weather?action=solar_wind`).catch(() => null),
    ]);

    const devices = mycobrainDevices.status === "fulfilled" && mycobrainDevices.value?.ok
      ? await mycobrainDevices.value.json()
      : [];

    const activeDevices = Array.isArray(devices) ? devices.length : 0;

    // Mock data structure matching LiveDataResponse
    const dashboardData = {
      stats: {
        totalEvents: 12547,
        activeDevices: activeDevices,
        speciesDetected: 342,
        onlineUsers: 12,
      },
      liveData: {
        readings: devices.slice(0, 10).map((device: any) => ({
          sourceDevice: device.device_id || device.id || "unknown",
          kingdomDomain: device.purpose || "Environmental Monitoring",
          timestamp: device.last_seen || new Date().toISOString(),
        })),
        lastUpdate: new Date().toISOString(),
      },
      insights: {
        trendingCompounds: [
          "Psilocybin",
          "Beta-glucan",
          "Ergosterol",
          "Lovastatin",
        ],
        recentDiscoveries: [
          {
            kingdomDomain: "Fungi - Basidiomycota",
            timestamp: new Date(Date.now() - 3600000).toISOString(),
          },
          {
            kingdomDomain: "Fungi - Ascomycota",
            timestamp: new Date(Date.now() - 7200000).toISOString(),
          },
        ],
      },
    };

    return NextResponse.json(dashboardData);
  } catch (error) {
    console.error("Failed to fetch NatureOS dashboard data:", error);
    
    // Return fallback data
    return NextResponse.json({
      stats: {
        totalEvents: 0,
        activeDevices: 0,
        speciesDetected: 0,
        onlineUsers: 0,
      },
      liveData: {
        readings: [],
        lastUpdate: new Date().toISOString(),
      },
      insights: {
        trendingCompounds: [],
        recentDiscoveries: [],
      },
    });
  }
}

