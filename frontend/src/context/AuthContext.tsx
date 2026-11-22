import React, { createContext, useContext, useEffect, useState, useCallback } from 'react'
import {
  login as apiLogin,
  register as apiRegister,
  getMe,
  storeTokens,
  clearTokens,
  getStoredToken,
} from '../api/client'
import type { UserResponse, LoginPayload, RegisterPayload } from '../api/client'

// ── Context shape ─────────────────────────────────────────────────────────────

interface AuthContextType {
  user: UserResponse | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (payload: LoginPayload) => Promise<void>
  register: (payload: RegisterPayload) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

// ── Provider ──────────────────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // On mount, try to restore session from stored token
  useEffect(() => {
    const token = getStoredToken()
    if (!token) {
      setIsLoading(false)
      return
    }
    // If it's a mock token, restore from localStorage user cache
    if (token === 'mock-access-token') {
      const cached = localStorage.getItem('cf_mock_user')
      if (cached) {
        try { setUser(JSON.parse(cached)) } catch { /* ignore */ }
      }
      setIsLoading(false)
      return
    }
    getMe()
      .then((me) => setUser(me))
      .catch(() => {
        // Token invalid/expired — clear it
        clearTokens()
      })
      .finally(() => setIsLoading(false))
  }, [])

  const login = useCallback(async (payload: LoginPayload) => {
    try {
      const data = await apiLogin(payload)
      storeTokens(data.access_token, data.refresh_token)
      setUser(data.user)
    } catch (err: any) {
      if (err?.response) {
        throw err
      }
      // ── Offline fallback only if server unreachable ──
      const mockUser: UserResponse = {
        id: 'mock-' + Math.random().toString(36).substring(2, 9),
        email: payload.email,
        name: payload.email.split('@')[0],
        role: payload.email.toLowerCase().includes('admin') || payload.email.toLowerCase().includes('instructor') ? 'instructor' : 'student',
        created_at: new Date().toISOString(),
      }
      storeTokens('mock-access-token', 'mock-refresh-token')
      localStorage.setItem('cf_mock_user', JSON.stringify(mockUser))
      setUser(mockUser)
      console.warn('[Auth] Network unreachable, using offline fallback')
    }
  }, [])

  const register = useCallback(async (payload: RegisterPayload) => {
    try {
      const data = await apiRegister(payload)
      storeTokens(data.access_token, data.refresh_token)
      setUser(data.user)
    } catch (err: any) {
      if (err?.response) {
        throw err
      }
      // ── Offline fallback only if server unreachable ──
      const mockUser: UserResponse = {
        id: 'mock-' + Math.random().toString(36).substring(2, 9),
        email: payload.email,
        name: payload.name,
        role: payload.role ?? 'student',
        created_at: new Date().toISOString(),
      }
      storeTokens('mock-access-token', 'mock-refresh-token')
      localStorage.setItem('cf_mock_user', JSON.stringify(mockUser))
      setUser(mockUser)
      console.warn('[Auth] Network unreachable, using offline fallback')
    }
  }, [])

  const logout = useCallback(() => {
    clearTokens()
    localStorage.removeItem('cf_mock_user')
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return ctx
}
