import { NextResponse } from "next/server";
import si from "systeminformation";

interface SystemStats {
  cpu: {
    usage: number;
    cores: number;
    model: string;
    speed: number;
  };
  memory: {
    total: number;
    used: number;
    free: number;
    usedPercent: number;
  };
  disk: {
    total: number;
    used: number;
    free: number;
    usedPercent: number;
  };
  network: {
    interfaces: Array<{
      name: string;
      ip: string;
      mac: string;
      speed: number;
      rx: number;
      tx: number;
    }>;
    totalRx: number;
    totalTx: number;
  };
  os: {
    platform: string;
    distro: string;
    release: string;
    hostname: string;
    uptime: number;
  };
  docker: {
    running: number;
    paused: number;
    stopped: number;
    containers: Array<{
      name: string;
      state: string;
      image: string;
      ports: string[];
    }>;
  };
  processes: {
    total: number;
    running: number;
    sleeping: number;
  };
}

export async function GET(): Promise<NextResponse<SystemStats | { error: string }>> {
  try {
    // Gather system information in parallel
    const [cpu, cpuLoad, mem, disk, networkInterfaces, networkStats, osInfo, timeInfo, dockerInfo, processes] = await Promise.all([
      si.cpu(),
      si.currentLoad(),
      si.mem(),
      si.fsSize(),
      si.networkInterfaces(),
      si.networkStats(),
      si.osInfo(),
      si.time(),
      si.dockerContainers().catch(() => []),
      si.processes(),
    ]);

    // Calculate totals
    const totalDisk = disk.reduce((sum, d) => sum + d.size, 0);
    const usedDisk = disk.reduce((sum, d) => sum + d.used, 0);
    
    const totalRx = networkStats.reduce((sum, n) => sum + (n.rx_bytes || 0), 0);
    const totalTx = networkStats.reduce((sum, n) => sum + (n.tx_bytes || 0), 0);

    // Filter network interfaces to only show relevant ones
    const relevantInterfaces = (networkInterfaces as si.Systeminformation.NetworkInterfacesData[]).filter(
      (iface) => iface.ip4 && !iface.internal && iface.operstate === "up"
    );

    // Map network stats to interfaces
    const interfaceData = relevantInterfaces.map((iface) => {
      const stats = networkStats.find((s) => s.iface === iface.iface) || { rx_bytes: 0, tx_bytes: 0 };
      return {
        name: iface.iface,
        ip: iface.ip4,
        mac: iface.mac,
        speed: iface.speed || 0,
        rx: stats.rx_bytes || 0,
        tx: stats.tx_bytes || 0,
      };
    });

    // Get Docker container info
    const dockerContainers = Array.isArray(dockerInfo) ? dockerInfo : [];
    const runningContainers = dockerContainers.filter((c) => c.state === "running").length;
    const pausedContainers = dockerContainers.filter((c) => c.state === "paused").length;
    const stoppedContainers = dockerContainers.filter((c) => c.state === "exited" || c.state === "dead").length;

    const stats: SystemStats = {
      cpu: {
        usage: Math.round(cpuLoad.currentLoad * 10) / 10,
        cores: cpu.cores,
        model: cpu.brand,
        speed: cpu.speed,
      },
      memory: {
        total: mem.total,
        used: mem.used,
        free: mem.free,
        usedPercent: Math.round((mem.used / mem.total) * 1000) / 10,
      },
      disk: {
        total: totalDisk,
        used: usedDisk,
        free: totalDisk - usedDisk,
        usedPercent: Math.round((usedDisk / totalDisk) * 1000) / 10,
      },
      network: {
        interfaces: interfaceData,
        totalRx,
        totalTx,
      },
      os: {
        platform: osInfo.platform,
        distro: osInfo.distro,
        release: osInfo.release,
        hostname: osInfo.hostname,
        uptime: timeInfo.uptime || 0,
      },
      docker: {
        running: runningContainers,
        paused: pausedContainers,
        stopped: stoppedContainers,
        containers: dockerContainers.slice(0, 10).map((c) => ({
          name: c.name,
          state: c.state,
          image: c.image,
          ports: Array.isArray((c as any).ports)
            ? (c as any).ports.map((p: any) => {
                if (p && typeof p === "object" && (p.PublicPort || p.PrivatePort)) {
                  return `${p.PublicPort ?? ""}:${p.PrivatePort ?? ""}`;
                }
                return String(p);
              })
            : [],
        })),
      },
      processes: {
        total: processes.all,
        running: processes.running,
        sleeping: processes.sleeping,
      },
    };

    return NextResponse.json(stats);
  } catch (error) {
    console.error("Error getting system stats:", error);
    return NextResponse.json({ error: "Failed to get system stats" }, { status: 500 });
  }
}
