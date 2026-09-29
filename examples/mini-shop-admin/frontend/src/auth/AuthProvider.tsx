import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { getCurrentAdmin, login as loginRequest, logout as logoutRequest } from '../api/auth'
import type { Admin } from '../types/api'

interface AuthValue {
  admin: Admin | null
  loading: boolean
  sessionExpired: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [admin, setAdmin] = useState<Admin | null>(null)
  const [loading, setLoading] = useState(true)
  const [sessionExpired, setSessionExpired] = useState(false)

  const expireSession = useCallback(() => {
    setAdmin(null)
    setLoading(false)
    setSessionExpired(true)
  }, [])

  useEffect(() => {
    let active = true
    getCurrentAdmin()
      .then((value) => {
        if (active) setAdmin(value)
      })
      .catch(() => {
        if (active) setAdmin(null)
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    window.addEventListener('auth:expired', expireSession)
    return () => {
      active = false
      window.removeEventListener('auth:expired', expireSession)
    }
  }, [expireSession])

  const login = useCallback(async (username: string, password: string) => {
    const result = await loginRequest(username, password)
    setAdmin(result.admin)
    setSessionExpired(false)
  }, [])

  const logout = useCallback(async () => {
    try {
      await logoutRequest()
    } finally {
      setAdmin(null)
      setSessionExpired(false)
    }
  }, [])

  const value = useMemo(
    () => ({ admin, loading, sessionExpired, login, logout }),
    [admin, loading, sessionExpired, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside AuthProvider')
  return value
}
