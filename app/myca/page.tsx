"use client"

import Link from "next/link"
import { useMemo, useState } from "react"
import { Button } from "@/components/ui/button"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import MycaDashboard from "@/components/myca-dashboard"
import MycaDashboardUnifi from "@/components/myca-dashboard-unifi"

export default function MycaPage() {
  const [tab, setTab] = useState<"integrated" | "unifi" | "external">("unifi")

  const unifiUrl = useMemo(() => process.env.NEXT_PUBLIC_UNIFI_DASHBOARD_URL ?? "http://localhost:3100", [])
  const n8nUrl = useMemo(() => process.env.NEXT_PUBLIC_N8N_URL ?? "http://localhost:5678", [])

  return (
    <main className="min-h-screen bg-[#0a1929] text-white p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold">MYCA</h1>
          <p className="text-sm text-gray-400">Staff dashboard + UniFi-style topology + voice control</p>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="secondary">
            <Link href="/n8n">Open n8n</Link>
          </Button>
          <Button asChild variant="outline">
            <a href={n8nUrl} target="_blank" rel="noreferrer">
              n8n (direct)
            </a>
          </Button>
        </div>
      </div>

      <Tabs value={tab} onValueChange={(v) => setTab(v as typeof tab)}>
        <TabsList className="bg-[#0d2137] border border-[#1e3a5f]">
          <TabsTrigger value="unifi" className="data-[state=active]:bg-[#1e3a5f]">
            UniFi Dashboard (embedded)
          </TabsTrigger>
          <TabsTrigger value="integrated" className="data-[state=active]:bg-[#1e3a5f]">
            Integrated (MAS app)
          </TabsTrigger>
          <TabsTrigger value="external" className="data-[state=active]:bg-[#1e3a5f]">
            Links
          </TabsTrigger>
        </TabsList>

        <TabsContent value="unifi" className="mt-4">
          <div className="rounded-lg overflow-hidden border border-[#1e3a5f] bg-black">
            <iframe title="MYCA UniFi Dashboard" src={unifiUrl} className="w-full h-[80vh]" />
          </div>
          <p className="text-xs text-gray-400 mt-2">
            If this is blank, make sure the `unifi-dashboard` service is running (host port 3100).
          </p>
        </TabsContent>

        <TabsContent value="integrated" className="mt-4">
          <MycaDashboardUnifi />
          <div className="mt-8 border-t border-[#1e3a5f] pt-6">
            <MycaDashboard />
          </div>
        </TabsContent>

        <TabsContent value="external" className="mt-4 space-y-2">
          <div className="flex gap-2">
            <Button asChild>
              <a href={unifiUrl} target="_blank" rel="noreferrer">
                Open UniFi dashboard (direct)
              </a>
            </Button>
            <Button asChild variant="secondary">
              <Link href="/n8n">Open n8n (embedded)</Link>
            </Button>
          </div>
        </TabsContent>
      </Tabs>
    </main>
  )
}
