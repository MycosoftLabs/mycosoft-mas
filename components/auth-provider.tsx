"use client"

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react"

interface AuthContextType {
  isAuthenticated: boolean
  token: string | null
  login: (username: string, password: string) => Promise<boolean>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  useEffect(() => {
    const stored = sessionStorage.getItem("myca_jwt")
    if (stored) {
      setToken(stored)
      setIsAuthenticated(true)
    }
  }, [])

  async function login(username: string, password: string) {
    try {
      const res = await fetch("/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ username, password })
      })
      if (!res.ok) return false
      const data = await res.json()
      if (data.access_token) {
        sessionStorage.setItem("myca_jwt", data.access_token)
        setToken(data.access_token)
        setIsAuthenticated(true)
        return true
      }
      return false
    } catch {
      return false
    }
  }

  function logout() {
    sessionStorage.removeItem("myca_jwt")
    setToken(null)
    setIsAuthenticated(false)
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, token, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within AuthProvider")
  return ctx
} 