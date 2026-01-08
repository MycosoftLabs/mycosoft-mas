import { NextRequest, NextResponse } from "next/server";
import { exec } from "child_process";
import { promisify } from "util";

const execAsync = promisify(exec);

interface StorageMount {
  path: string;
  total: number;
  used: number;
  free: number;
  usedPercent: number;
  filesystem: string;
}

export async function GET(request: NextRequest) {
  try {
    // Check if running on Windows or Linux
    const isWindows = process.platform === "win32";
    
    if (isWindows) {
      // Windows: Use PowerShell to get disk info
      const { stdout } = await execAsync(
        `powershell -Command "Get-PSDrive -PSProvider FileSystem | Select-Object Name, @{Name='Used';Expression={[math]::Round($_.Used/1GB,2)}}, @{Name='Free';Expression={[math]::Round($_.Free/1GB,2)}} | ConvertTo-Json"`
      );
      
      const drives = JSON.parse(stdout);
      const storageMounts: StorageMount[] = Array.isArray(drives) ? drives.map((d: any) => ({
        path: `${d.Name}:\\`,
        total: (d.Used + d.Free) * 1024 * 1024 * 1024,
        used: d.Used * 1024 * 1024 * 1024,
        free: d.Free * 1024 * 1024 * 1024,
        usedPercent: ((d.Used / (d.Used + d.Free)) * 100) || 0,
        filesystem: "NTFS",
      })) : [];
      
      // Check for /natureos/storage mounts (if using WSL or mounted paths)
      const natureosPaths = [
        "/natureos/storage",
        "Z:\\natureos\\storage",
        "Y:\\natureos\\storage",
        "X:\\natureos\\storage",
      ];
      
      const allMounts = [...storageMounts];
      
      return NextResponse.json({
        status: "ok",
        mounts: allMounts,
        totalStorage: allMounts.reduce((sum, m) => sum + m.total, 0),
        totalUsed: allMounts.reduce((sum, m) => sum + m.used, 0),
        totalFree: allMounts.reduce((sum, m) => sum + m.free, 0),
        timestamp: new Date().toISOString(),
      });
    } else {
      // Linux: Use df command
      const { stdout } = await execAsync("df -h /natureos/storage /mnt/mycosoft-nas /data 2>/dev/null || df -h");
      
      const lines = stdout.split("\n").slice(1); // Skip header
      const mounts: StorageMount[] = [];
      
      for (const line of lines) {
        const parts = line.trim().split(/\s+/);
        if (parts.length >= 6) {
          const filesystem = parts[0];
          const totalStr = parts[1];
          const usedStr = parts[2];
          const freeStr = parts[3];
          const mountPoint = parts[5];
          
          // Parse size strings (e.g., "26T", "16G")
          const parseSize = (sizeStr: string): number => {
            const match = sizeStr.match(/^(\d+\.?\d*)([KMGT])?$/);
            if (!match) return 0;
            const value = parseFloat(match[1]);
            const unit = match[2] || "";
            const multipliers: Record<string, number> = {
              K: 1024,
              M: 1024 * 1024,
              G: 1024 * 1024 * 1024,
              T: 1024 * 1024 * 1024 * 1024,
            };
            return value * (multipliers[unit] || 1);
          };
          
          const total = parseSize(totalStr);
          const used = parseSize(usedStr);
          const free = parseSize(freeStr);
          
          if (total > 0) {
            mounts.push({
              path: mountPoint,
              total,
              used,
              free,
              usedPercent: (used / total) * 100,
              filesystem,
            });
          }
        }
      }
      
      // Expected storage: 26TB + 16TB + 16TB + 13TB + 2-5TB
      const expectedMounts = [
        { path: "/natureos/storage/26tb", size: 26 * 1024 * 1024 * 1024 * 1024 },
        { path: "/natureos/storage/16tb-1", size: 16 * 1024 * 1024 * 1024 * 1024 },
        { path: "/natureos/storage/16tb-2", size: 16 * 1024 * 1024 * 1024 * 1024 },
        { path: "/natureos/storage/13tb", size: 13 * 1024 * 1024 * 1024 * 1024 },
        { path: "/natureos/storage/2-5tb", size: 3.5 * 1024 * 1024 * 1024 * 1024 }, // Average
      ];
      
      return NextResponse.json({
        status: "ok",
        mounts,
        expectedMounts: expectedMounts.map((em) => ({
          ...em,
          found: mounts.some((m) => m.path.includes(em.path.split("/").pop() || "")),
        })),
        totalStorage: mounts.reduce((sum, m) => sum + m.total, 0),
        totalUsed: mounts.reduce((sum, m) => sum + m.used, 0),
        totalFree: mounts.reduce((sum, m) => sum + m.free, 0),
        timestamp: new Date().toISOString(),
      });
    }
  } catch (error: any) {
    console.error("Storage audit error:", error);
    return NextResponse.json(
      {
        status: "error",
        error: error.message || "Failed to audit storage",
        mounts: [],
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}

