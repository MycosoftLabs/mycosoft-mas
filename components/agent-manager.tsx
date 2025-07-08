"use client"

import * as React from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { PlayCircle, StopCircle, RefreshCw } from "lucide-react"
import { useAuth } from "./auth-provider"

interface Agent {
  id: string
  name: string
  status: "active" | "inactive" | "error"
  type: string
  lastActive: string
}

export function AgentManager() {
  const { token } = useAuth()
  const [agents, setAgents] = React.useState<Agent[]>([
    {
      id: "1",
      name: "Finance Admin Agent",
      status: "active",
      type: "Financial",
      lastActive: new Date().toISOString()
    },
    {
      id: "2",
      name: "Project Management Agent",
      status: "active",
      type: "Management",
      lastActive: new Date().toISOString()
    },
    // Add more default agents as needed
  ])

  const [isLoading, setIsLoading] = React.useState(false)

  const handleStartAll = async () => {
    setIsLoading(true)
    try {
      await fetch("/api/agents/start_all", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      })
      setAgents(agents.map(agent => ({ ...agent, status: "active" })))
    } catch (error) {
      console.error("Failed to start agents:", error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleStopAll = async () => {
    setIsLoading(true)
    try {
      await fetch("/api/agents/stop_all", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      })
      setAgents(agents.map(agent => ({ ...agent, status: "inactive" })))
    } catch (error) {
      console.error("Failed to stop agents:", error)
    } finally {
      setIsLoading(false)
    }
  }

  const getStatusColor = (status: Agent["status"]) => {
    switch (status) {
      case "active":
        return "bg-green-500"
      case "inactive":
        return "bg-gray-500"
      case "error":
        return "bg-red-500"
      default:
        return "bg-gray-500"
    }
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          Agent Manager
          <div className="space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleStartAll}
              disabled={isLoading}
            >
              <PlayCircle className="mr-2 h-4 w-4" />
              Start All
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleStopAll}
              disabled={isLoading}
            >
              <StopCircle className="mr-2 h-4 w-4" />
              Stop All
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsLoading(prev => !prev)}
              disabled={isLoading}
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
            </Button>
          </div>
        </CardTitle>
        <CardDescription>
          Monitor and manage all active agents in the system
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[400px] w-full rounded-md border p-4">
          <div className="space-y-4">
            {agents.map((agent) => (
              <div
                key={agent.id}
                className="flex items-center justify-between rounded-lg border p-4"
              >
                <div className="space-y-1">
                  <h4 className="text-sm font-medium">{agent.name}</h4>
                  <p className="text-sm text-muted-foreground">
                    Type: {agent.type}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Last Active: {new Date(agent.lastActive).toLocaleString()}
                  </p>
                </div>
                <div className="flex items-center space-x-4">
                  <Badge
                    variant="secondary"
                    className={`${getStatusColor(agent.status)} text-white`}
                  >
                    {agent.status}
                  </Badge>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      // TODO: Implement individual agent control
                      setAgents(agents.map(a => 
                        a.id === agent.id 
                          ? { ...a, status: a.status === "active" ? "inactive" : "active" }
                          : a
                      ))
                    }}
                  >
                    {agent.status === "active" ? (
                      <StopCircle className="h-4 w-4" />
                    ) : (
                      <PlayCircle className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
} 