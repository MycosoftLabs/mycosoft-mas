import { NextResponse } from "next/server"

export async function GET() {
  // Simple placeholder; can be wired to real DPI / flow categorization later.
  return NextResponse.json({
    total: 0,
    services: [
      { name: "SSL/TLS", value: 37.4 },
      { name: "STUN", value: 2.89 },
      { name: "XBOX", value: 2.72 },
    ],
  })
}

