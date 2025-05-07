"use client"

import * as React from "react"
import { MycaNotificationPanel, MycaNotificationModal, MycaChatInput } from "@/components"
import { MycaNotification, NotificationFilter, MycaChatMessage } from "@/components/types"
import { Header } from "@/components/header"
import { AgentManager } from "@/components/agent-manager"
import { SystemMetrics } from "@/components/system-metrics"
import { KnowledgeGraph } from "@/components/knowledge-graph"
import { SystemGraphPanel } from "./system-graph-panel"
import { AuthProvider, useAuth } from "@/components/auth-provider"
import { LoginDialog } from "@/components/login-dialog"

function DashboardContent() {
  const { isAuthenticated } = useAuth()
  const [notifications, setNotifications] = React.useState<MycaNotification[]>([])
  const [selected, setSelected] = React.useState<MycaNotification | null>(null)
  const [filter, setFilter] = React.useState<NotificationFilter>({})
  const [isLoading, setIsLoading] = React.useState(false)
  const [chatLoading, setChatLoading] = React.useState(false)
  const [chatHistory, setChatHistory] = React.useState<MycaChatMessage[]>([])
  const [improvements, setImprovements] = React.useState<any[]>([])
  const [logs, setLogs] = React.useState<string[]>([])

  React.useEffect(() => {
    // Connect to backend WebSocket for real-time notifications
    const ws = new WebSocket(`ws://${window.location.host}/ws`)
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        // Assume backend sends { myca_notification: { ... } }
        if (data.myca_notification) {
          setNotifications(prev => [data.myca_notification, ...prev].slice(0, 50))
        }
      } catch (e) {
        // Ignore parse errors
      }
    }
    ws.onopen = () => setIsLoading(false)
    ws.onclose = () => setIsLoading(false)
    ws.onerror = () => setIsLoading(false)
    setIsLoading(true)
    return () => ws.close()
  }, [])

  // Fetch recommended improvements (stubbed for now)
  React.useEffect(() => {
    fetch("/api/improvements")
      .then(res => res.json())
      .then(data => setImprovements(data.improvements || []))
      .catch(() => setImprovements([]))
    fetch("/api/logs")
      .then(res => res.json())
      .then(data => setLogs(data.logs || []))
      .catch(() => setLogs([]))
  }, [])

  const filtered = notifications.filter(n => {
    if (filter.type && n.type !== filter.type) return false
    if (filter.isRead !== undefined && n.isRead !== filter.isRead) return false
    if (filter.search && !n.message.toLowerCase().includes(filter.search.toLowerCase())) return false
    return true
  })

  function handleReplayTTS(notification: MycaNotification) {
    if (notification.ttsUrl) {
      const audio = new Audio(notification.ttsUrl)
      audio.play()
    }
  }

  async function handleSendChat(message: string) {
    setChatLoading(true)
    const userMsg: MycaChatMessage = {
      id: `${Date.now()}-user`,
      sender: "user",
      message,
      timestamp: new Date().toISOString(),
    }
    setChatHistory(prev => [...prev, userMsg])
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message })
      })
      const data = await res.json()
      const mycaMsg: MycaChatMessage = {
        id: `${Date.now()}-myca`,
        sender: "myca",
        message: data.response,
        timestamp: new Date().toISOString(),
      }
      setChatHistory(prev => [...prev, mycaMsg])
    } catch (e) {
      setChatHistory(prev => [...prev, {
        id: `${Date.now()}-error`,
        sender: "myca",
        message: "Sorry, I couldn't process your request right now.",
        timestamp: new Date().toISOString(),
      }])
    } finally {
      setChatLoading(false)
    }
  }

  function handleSelectNotification(n: MycaNotification) {
    setSelected(n)
    // Mark as read in state
    setNotifications(prev => prev.map(notif => notif.id === n.id ? { ...notif, isRead: true } : notif))
    // Optionally, send to backend to mark as read
    fetch(`/api/notification/${n.id}/read`, { method: "POST" }).catch(() => {})
  }

  if (!isAuthenticated) {
    return <LoginDialog open={true} />
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <main className="grid grid-cols-1 md:grid-cols-2 gap-8 w-full max-w-7xl mx-auto px-8 py-8">
        <section className="col-span-1 flex flex-col gap-4">
          <Header />
          <AgentManager />
          <SystemMetrics />
        </section>
        <section className="col-span-1 flex flex-col gap-4">
          <MycaNotificationPanel
            notifications={filtered}
            onSelect={handleSelectNotification}
            onReplayTTS={handleReplayTTS}
            filter={filter}
            onFilterChange={setFilter}
            isLoading={isLoading}
          />
          <MycaNotificationModal
            notification={selected}
            onClose={() => setSelected(null)}
            onReplayTTS={handleReplayTTS}
          />
          {/* Chat history */}
          <div className="bg-white rounded shadow p-4 mb-4">
            <h3 className="font-semibold mb-2">MYCA Chat</h3>
            <div className="flex flex-col gap-2 max-h-48 overflow-y-auto mb-2">
              {chatHistory.map(msg => (
                <div key={msg.id} className={msg.sender === "myca" ? "text-blue-700" : "text-gray-800"}>
                  <span className="font-bold">{msg.sender === "myca" ? "MYCA" : "You"}:</span> {msg.message}
                </div>
              ))}
            </div>
            <MycaChatInput onSend={handleSendChat} isLoading={chatLoading} />
          </div>
        </section>
      </main>
      {/* System Graph Panel */}
      <SystemGraphPanel />
      {/* Self-Improvement and Logs Section */}
      <section className="max-w-7xl w-full mx-auto px-8 pb-8 grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="bg-white rounded shadow p-4">
          <h3 className="font-semibold mb-2">Self-Improvement Suggestions</h3>
          <ul className="list-disc pl-5">
            {improvements.map((imp, i) => (
              <li key={i} className="mb-1">
                <span className="font-bold">{imp.name}:</span> {imp.description} {imp.source_url && <a href={imp.source_url} className="underline text-blue-600 ml-2" target="_blank" rel="noopener noreferrer">Source</a>}
              </li>
            ))}
          </ul>
        </div>
        <div className="bg-white rounded shadow p-4">
          <h3 className="font-semibold mb-2">System Logs</h3>
          <pre className="overflow-x-auto text-xs bg-gray-100 p-2 rounded border border-gray-200 max-h-64">{logs.join("\n")}</pre>
        </div>
      </section>
    </div>
  )
}

export default function DashboardPage() {
  return (
    <AuthProvider>
      <DashboardContent />
    </AuthProvider>
  )
} 