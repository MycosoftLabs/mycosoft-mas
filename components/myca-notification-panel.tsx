import * as React from "react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { MycaNotification, NotificationFilter } from "./types"

interface MycaNotificationPanelProps {
  notifications: MycaNotification[]
  onSelect: (notification: MycaNotification) => void
  onReplayTTS?: (notification: MycaNotification) => void
  filter: NotificationFilter
  onFilterChange: (filter: NotificationFilter) => void
  isLoading?: boolean
}

export function MycaNotificationPanel({
  notifications,
  onSelect,
  onReplayTTS,
  filter,
  onFilterChange,
  isLoading = false,
}: MycaNotificationPanelProps) {
  // Group by batchId if present
  const batches = notifications.reduce<Record<string, MycaNotification[]>>((acc, n) => {
    const key = n.batchId || n.id
    if (!acc[key]) acc[key] = []
    acc[key].push(n)
    return acc
  }, {})

  return (
    <Card className="w-full max-w-xl mb-4">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          MYCA Notifications
          <div className="flex gap-2">
            <Button size="sm" variant={!filter.type ? "default" : "outline"} onClick={() => onFilterChange({ ...filter, type: undefined })}>All</Button>
            <Button size="sm" variant={filter.type === "critical" ? "default" : "outline"} onClick={() => onFilterChange({ ...filter, type: "critical" })}>Critical</Button>
            <Button size="sm" variant={filter.type === "warning" ? "default" : "outline"} onClick={() => onFilterChange({ ...filter, type: "warning" })}>Warning</Button>
            <Button size="sm" variant={filter.type === "info" ? "default" : "outline"} onClick={() => onFilterChange({ ...filter, type: "info" })}>Info</Button>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="text-center py-8">Loading...</div>
        ) : (
          <div className="space-y-2">
            {(Object.values(batches) as MycaNotification[][]).map((batch) => (
              <div key={batch[0].batchId || batch[0].id} className="border rounded p-2 bg-muted">
                {batch.map((n) => (
                  <div
                    key={n.id}
                    className={`flex items-center justify-between p-2 rounded cursor-pointer ${n.type === "critical" ? "bg-red-100 animate-pulse" : ""}`}
                    onClick={() => onSelect(n)}
                  >
                    <div>
                      <span className="font-medium">{n.agentName || n.channel || "MYCA"}</span>: {n.title} - {n.message}
                      <span className="ml-2 text-xs text-muted-foreground">{new Date(n.timestamp).toLocaleTimeString()}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {n.ttsUrl && onReplayTTS && (
                        <Button size="icon" variant="ghost" onClick={e => { e.stopPropagation(); onReplayTTS(n) }}>🔊</Button>
                      )}
                      <Badge variant={n.type === "critical" ? "destructive" : n.type === "warning" ? "warning" : "secondary"}>{n.type}</Badge>
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
} 