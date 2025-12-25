"use client"

import Link from "next/link"
import { useMemo } from "react"
import { Button } from "@/components/ui/button"

export default function N8nPage() {
  const n8nUrl = useMemo(() => process.env.NEXT_PUBLIC_N8N_URL ?? "http://localhost:5678", [])

  return (
    <main className="min-h-screen bg-[#0a1929] text-white p-6">
      <h1 className="text-2xl font-semibold mb-2">n8n Workflows</h1>
      <p className="text-sm text-gray-400 mb-6">
        n8n sets anti-iframe headers by default, so we link out to the full UI.
      </p>

      <div className="flex flex-wrap gap-3">
        <Button asChild>
          <a href={n8nUrl} target="_blank" rel="noreferrer">
            Open n8n
          </a>
        </Button>
        <Button asChild variant="secondary">
          <Link href="/myca">Back to MYCA</Link>
        </Button>
      </div>

      <div className="mt-6 text-xs text-gray-400">
        URL: <span className="font-mono">{n8nUrl}</span>
      </div>
    </main>
  )
}
