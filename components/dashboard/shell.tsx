import { ReactNode } from "react"

interface DashboardShellProps {
  children: ReactNode
}

export function DashboardShell({ children }: DashboardShellProps) {
  return (
    <div className="flex min-h-screen flex-col bg-[#0a0a0f]">
      <main className="flex-1 p-6">{children}</main>
    </div>
  )
}

