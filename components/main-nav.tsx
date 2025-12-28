"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { 
  Home, 
  Bot, 
  Leaf, 
  Search, 
  FileText, 
  AppWindow,
  Settings,
  Activity,
  TrendingUp
} from "lucide-react"

const navItems = [
  {
    name: "Home",
    href: "/",
    icon: Home,
  },
  {
    name: "MYCA",
    href: "/myca",
    icon: Bot,
    description: "AI Orchestrator & Agents",
  },
  {
    name: "NatureOS",
    href: "/natureos",
    icon: Leaf,
    description: "Earth System Dashboard",
  },
  {
    name: "MINDEX",
    href: "/mindex",
    icon: Search,
    description: "Species & Knowledge Search",
  },
  {
    name: "Docs",
    href: "/docs",
    icon: FileText,
    description: "Documentation",
  },
  {
    name: "Apps",
    href: "/apps",
    icon: AppWindow,
    description: "Mycosoft Applications",
  },
]

export function MainNav() {
  const pathname = usePathname()

  return (
    <nav className="sticky top-0 z-50 w-full border-b border-gray-800 bg-[#0a1929]/95 backdrop-blur supports-[backdrop-filter]:bg-[#0a1929]/80">
      <div className="flex h-16 items-center px-4 md:px-8">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-3 mr-8">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-purple-600 to-green-500">
            <span className="text-xl">🍄</span>
          </div>
          <div className="hidden sm:block">
            <div className="text-lg font-semibold text-white">Mycosoft</div>
            <div className="text-xs text-gray-400">Multi-Agent System</div>
          </div>
        </Link>

        {/* Nav Links */}
        <div className="flex items-center gap-1 overflow-x-auto">
          {navItems.map((item) => {
            const isActive = pathname === item.href || 
              (item.href !== "/" && pathname.startsWith(item.href))
            
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-all",
                  isActive
                    ? "bg-purple-600/20 text-purple-400 border border-purple-500/30"
                    : "text-gray-400 hover:text-white hover:bg-gray-800/50"
                )}
              >
                <item.icon className="h-4 w-4" />
                <span className="hidden md:inline">{item.name}</span>
              </Link>
            )
          })}
        </div>

        {/* Right side */}
        <div className="ml-auto flex items-center gap-2">
          <Link
            href="/improvements"
            className={cn(
              "flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-all",
              pathname === "/improvements"
                ? "bg-green-600/20 text-green-400 border border-green-500/30"
                : "text-gray-400 hover:text-white hover:bg-gray-800/50"
            )}
          >
            <TrendingUp className="h-4 w-4" />
            <span className="hidden lg:inline">Efficiency</span>
          </Link>
          <Link
            href="/n8n"
            className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-gray-800/50"
          >
            <Activity className="h-4 w-4" />
            <span className="hidden lg:inline">Workflows</span>
          </Link>
          <Link
            href="/settings"
            className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-gray-800/50"
          >
            <Settings className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </nav>
  )
}

