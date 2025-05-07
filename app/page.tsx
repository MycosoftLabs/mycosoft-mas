'use client'

import { Suspense } from "react";
import { AgentManager } from "@/components/agent-manager";
import { TaskManager } from "@/components/task-manager";
import { KnowledgeGraph } from "@/components/knowledge-graph";
import { SystemMetrics } from "@/components/system-metrics";
import { Header } from "@/components/header";
import { Loading } from "@/components/loading";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-24">
      <h1 className="text-4xl font-bold">Welcome to Mycosoft MAS</h1>
    </main>
  );
} 