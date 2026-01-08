import { NextRequest, NextResponse } from "next/server";

const MYCOBRAIN_SERVICE_URL = process.env.MYCOBRAIN_SERVICE_URL || "http://localhost:8003";

export async function GET(
  request: NextRequest,
  { params }: { params: { port: string } }
) {
  try {
    const deviceId = params.port;
    
    // Send I2C scan command to discover peripherals
    const response = await fetch(
      `${MYCOBRAIN_SERVICE_URL}/devices/${deviceId}/command?command=scan`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      }
    );
    
    if (!response.ok) {
      // Return empty peripherals if device not connected
      if (response.status === 400 || response.status === 404) {
        return NextResponse.json({
          peripherals: [],
          timestamp: new Date().toISOString(),
        });
      }
      throw new Error(`Failed to scan peripherals: ${response.statusText}`);
    }
    
    const data = await response.json();
    
    // Parse the scan response to extract found I2C addresses
    const peripherals: Array<{address: string; name: string; type: string; status: string}> = [];
    const scanResponse = data.response || "";
    
    // Parse lines like "found: 0x76" and "found: 0x77"
    const matches = scanResponse.match(/found:\s*(0x[0-9A-Fa-f]+)/g);
    
    if (matches) {
      const addressMap: Record<string, { name: string; type: string }> = {
        "0x76": { name: "BME688 Environmental Sensor", type: "environmental" },
        "0x77": { name: "BME688 Ambient Sensor", type: "environmental" },
        "0x3c": { name: "SSD1306 OLED Display", type: "display" },
        "0x3d": { name: "SSD1306 OLED Display Alt", type: "display" },
        "0x68": { name: "MPU6050 IMU", type: "motion" },
        "0x69": { name: "MPU6050 IMU Alt", type: "motion" },
        "0x40": { name: "INA219 Power Monitor", type: "power" },
        "0x48": { name: "ADS1115 ADC", type: "adc" },
        "0x50": { name: "AT24C32 EEPROM", type: "storage" },
      };
      
      matches.forEach((match) => {
        const addr = match.replace("found:", "").trim().toLowerCase();
        const info = addressMap[addr] || { name: `Unknown Device`, type: "unknown" };
        peripherals.push({
          address: addr,
          name: info.name,
          type: info.type,
          status: "detected",
        });
      });
    }
    
    return NextResponse.json({
      peripherals,
      raw_scan: scanResponse,
      timestamp: new Date().toISOString(),
    });
  } catch (error: any) {
    console.error("Error scanning peripherals:", error);
    return NextResponse.json(
      { 
        error: error.message || "Failed to scan peripherals",
        peripherals: [],
      },
      { status: 500 }
    );
  }
}

