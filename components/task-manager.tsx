"use client"

import * as React from "react"
import { Card } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { TaskForm } from "./task-form"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

interface Task {
  id: string
  title: string
  status: "pending" | "in-progress" | "completed"
  priority: "low" | "medium" | "high"
}

export function TaskManager() {
  const [tasks, setTasks] = React.useState<Task[]>([])

  const handleAddTask = (data: Omit<Task, "id">) => {
    const newTask: Task = {
      ...data,
      id: crypto.randomUUID(),
    }
    setTasks((prev) => [...prev, newTask])
  }

  const getPriorityColor = (priority: Task["priority"]) => {
    switch (priority) {
      case "high":
        return "bg-red-500"
      case "medium":
        return "bg-yellow-500"
      case "low":
        return "bg-green-500"
      default:
        return "bg-gray-500"
    }
  }

  const getStatusColor = (status: Task["status"]) => {
    switch (status) {
      case "completed":
        return "bg-green-500"
      case "in-progress":
        return "bg-blue-500"
      case "pending":
        return "bg-gray-500"
      default:
        return "bg-gray-500"
    }
  }

  return (
    <div className="space-y-4 p-4">
      <Card className="p-4">
        <h2 className="text-2xl font-bold mb-4">Add New Task</h2>
        <TaskForm onSubmit={handleAddTask} />
      </Card>

      <Card className="p-4">
        <h2 className="text-2xl font-bold mb-4">Tasks</h2>
        <ScrollArea className="h-[400px] w-full rounded-md border p-4">
          {tasks.length === 0 ? (
            <p className="text-center text-muted-foreground">No tasks available</p>
          ) : (
            <div className="space-y-4">
              {tasks.map((task) => (
                <Card key={task.id} className="p-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold">{task.title}</h3>
                    <div className="flex gap-2">
                      <Badge
                        className={cn(
                          "text-white",
                          getPriorityColor(task.priority)
                        )}
                      >
                        {task.priority}
                      </Badge>
                      <Badge
                        className={cn(
                          "text-white",
                          getStatusColor(task.status)
                        )}
                      >
                        {task.status}
                      </Badge>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </ScrollArea>
      </Card>
    </div>
  )
} 