"use client"

import * as React from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"
import { useAuth } from "./auth-provider"

interface MetricData {
  timestamp: string
  cpu: number
  memory: number
  agents: number
  tasks: number
}

export function SystemMetrics() {
  const { token } = useAuth()
  const [metrics, setMetrics] = React.useState<MetricData[]>([])
  const [isLoading, setIsLoading] = React.useState(true)
  const [error, setError] = React.useState("")

  React.useEffect(() => {
    async function fetchMetrics() {
      setIsLoading(true)
      setError("")
      try {
        const res = await fetch("/api/metrics", {
          headers: { Authorization: `Bearer ${token}` }
        })
        if (!res.ok) throw new Error("Unauthorized or error fetching metrics")
        const text = await res.text()
        const parsed = parsePrometheus(text)
        setMetrics(parsed.length ? parsed : generateDemoData())
      } catch (e) {
        setError("Failed to load metrics")
        setMetrics(generateDemoData())
      } finally {
        setIsLoading(false)
      }
    }
    if (token) fetchMetrics()
  }, [token])

  function parsePrometheus(text: string): MetricData[] {
    const values: Record<string, number> = {}
    text.split("\n").forEach(line => {
      const [key, val] = line.split(" ")
      if (!key || !val) return
      if (key.startsWith("mas_cpu_usage")) values.cpu = parseFloat(val)
      if (key.startsWith("mas_memory_usage")) values.memory = parseFloat(val)
      if (key.startsWith("mas_agent_count")) values.agents = parseFloat(val)
      if (key.startsWith("mas_task_count")) values.tasks = parseFloat(val)
    })
    if (Object.keys(values).length) {
      return [{
        timestamp: new Date().toLocaleTimeString(),
        cpu: values.cpu || 0,
        memory: values.memory || 0,
        agents: values.agents || 0,
        tasks: values.tasks || 0
      }]
    }
    return []
  }

  function generateDemoData(): MetricData[] {
    const now = new Date()
    const data: MetricData[] = []
    for (let i = 0; i < 24; i++) {
      data.push({
        timestamp: new Date(now.getTime() - (23 - i) * 3600000).toLocaleTimeString(),
        cpu: Math.floor(Math.random() * 40 + 20),
        memory: Math.floor(Math.random() * 30 + 40),
        agents: Math.floor(Math.random() * 5 + 8),
        tasks: Math.floor(Math.random() * 20 + 10),
      })
    }
    return data
  }

  const formatValue = (value: number) => `${value}%`
  const formatAgents = (value: number) => `${value} agents`
  const formatTasks = (value: number) => `${value} tasks`

  if (isLoading) {
    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle>System Metrics</CardTitle>
          <CardDescription>Loading system performance data...</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>System Metrics</CardTitle>
        <CardDescription>Real-time system performance monitoring</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-8">
          <div className="h-[200px]">
            <h4 className="text-sm font-medium mb-2">Resource Usage</h4>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={metrics}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="timestamp"
                  fontSize={12}
                  tickFormatter={(value) => value.split(":")[0] + ":00"}
                />
                <YAxis fontSize={12} />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="cpu"
                  name="CPU Usage"
                  stroke="#0ea5e9"
                  strokeWidth={2}
                />
                <Line
                  type="monotone"
                  dataKey="memory"
                  name="Memory Usage"
                  stroke="#8b5cf6"
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="h-[200px]">
            <h4 className="text-sm font-medium mb-2">System Activity</h4>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={metrics}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="timestamp"
                  fontSize={12}
                  tickFormatter={(value) => value.split(":")[0] + ":00"}
                />
                <YAxis fontSize={12} />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="agents"
                  name="Active Agents"
                  stroke="#22c55e"
                  strokeWidth={2}
                />
                <Line
                  type="monotone"
                  dataKey="tasks"
                  name="Active Tasks"
                  stroke="#f59e0b"
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <Card>
              <CardHeader className="p-4">
                <CardTitle className="text-sm">CPU Usage</CardTitle>
              </CardHeader>
              <CardContent className="p-4 pt-0">
                <p className="text-2xl font-bold">{metrics[metrics.length - 1].cpu}%</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="p-4">
                <CardTitle className="text-sm">Memory Usage</CardTitle>
              </CardHeader>
              <CardContent className="p-4 pt-0">
                <p className="text-2xl font-bold">{metrics[metrics.length - 1].memory}%</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="p-4">
                <CardTitle className="text-sm">Active Agents</CardTitle>
              </CardHeader>
              <CardContent className="p-4 pt-0">
                <p className="text-2xl font-bold">{metrics[metrics.length - 1].agents}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="p-4">
                <CardTitle className="text-sm">Active Tasks</CardTitle>
              </CardHeader>
              <CardContent className="p-4 pt-0">
                <p className="text-2xl font-bold">{metrics[metrics.length - 1].tasks}</p>
              </CardContent>
            </Card>
          </div>
        </div>
      </CardContent>
    </Card>
  )
} 