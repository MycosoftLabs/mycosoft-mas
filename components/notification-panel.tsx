import * as React from "react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog"

interface Notification {
  id: string
  message: string
  channel: string
  priority: "normal" | "critical"
  agentId?: string
  agentName?: string
  eventType?: string
  context?: Record<string, unknown>
  timestamp: string
  batchId?: string
}

interface NotificationPanelProps {
  notifications?: Notification[]
}

export function NotificationPanel({ notifications: initialNotifications = [] }: NotificationPanelProps) {
  const [notifications, setNotifications] = React.useState<Notification[]>(initialNotifications)
  const [filter, setFilter] = React.useState<string>("")
  const [selected, setSelected] = React.useState<Notification | null>(null)
  const [soundEnabled, setSoundEnabled] = React.useState<boolean>(true)

  // Simulate real-time updates (replace with SSE/WebSocket in production)
  React.useEffect(() => {
    // TODO: Replace with real event source
    // setNotifications(...)
  }, [])

  React.useEffect(() => {
    if (soundEnabled && notifications.some((n: Notification) => n.priority === "critical")) {
      // Play sound for critical notification
      const audio = new Audio("/alert.mp3")
      audio.play()
    }
  }, [notifications, soundEnabled])

  const filtered = notifications.filter((n: Notification) =>
    !filter || n.priority === filter || n.channel === filter || n.agentName === filter
  )

  // Group by batchId if present
  const batches = filtered.reduce<Record<string, Notification[]>>((acc: Record<string, Notification[]>, n: Notification) => {
    const key = n.batchId || n.id
    if (!acc[key]) acc[key] = []
    acc[key].push(n)
    return acc
  }, {})

  return (
    <Card className="w-full max-w-xl mb-4">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          Notifications
          <div className="flex gap-2">
            <Button size="sm" variant={filter === "" ? "default" : "outline"} onClick={() => setFilter("")}>All</Button>
            <Button size="sm" variant={filter === "critical" ? "default" : "outline"} onClick={() => setFilter("critical")}>Critical</Button>
            <Button size="sm" variant={filter === "normal" ? "default" : "outline"} onClick={() => setFilter("normal")}>Normal</Button>
            <Button size="sm" variant={soundEnabled ? "default" : "outline"} onClick={() => setSoundEnabled((v: boolean) => !v)}>{soundEnabled ? "🔊" : "🔇"}</Button>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {(Object.values(batches) as Notification[][]).map((batch, i) => (
            <div key={batch[0].batchId || batch[0].id} className="border rounded p-2 bg-muted">
              {batch.map((n) => (
                <div
                  key={n.id}
                  className={`flex items-center justify-between p-2 rounded cursor-pointer ${n.priority === "critical" ? "bg-red-100 animate-pulse" : ""}`}
                  onClick={() => setSelected(n)}
                >
                  <div>
                    <span className="font-medium">{n.agentName || n.channel}</span>: {n.message}
                    <span className="ml-2 text-xs text-muted-foreground">{new Date(n.timestamp).toLocaleTimeString()}</span>
                  </div>
                  <Badge variant={n.priority === "critical" ? "destructive" : "secondary"}>{n.priority}</Badge>
                </div>
              ))}
            </div>
          ))}
        </div>
        <Dialog open={!!selected} onOpenChange={() => setSelected(null)}>
          <DialogContent>
            <DialogTitle>Notification Details</DialogTitle>
            {selected && (
              <div className="space-y-2">
                <div><b>Message:</b> {selected.message}</div>
                <div><b>Agent:</b> {selected.agentName || selected.agentId}</div>
                <div><b>Channel:</b> {selected.channel}</div>
                <div><b>Priority:</b> {selected.priority}</div>
                <div><b>Event Type:</b> {selected.eventType}</div>
                <div><b>Time:</b> {new Date(selected.timestamp).toLocaleString()}</div>
                <div><b>Context:</b> <pre className="whitespace-pre-wrap text-xs">{JSON.stringify(selected.context, null, 2)}</pre></div>
              </div>
            )}
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  )
} 