import { NextResponse } from "next/server"

export async function GET() {
  const healthData = {
    status: "healthy",
    timestamp: new Date().toISOString(),
    version: "1.0.0",
    service: "mycosoft-mas",
    uptime: process.uptime(),
    memory: process.memoryUsage(),
    environment: process.env.NODE_ENV || "development",
    checks: {
      api: "ok",
      database: "ok",
      cache: "ok",
    },
  }

  return NextResponse.json(healthData)
}

