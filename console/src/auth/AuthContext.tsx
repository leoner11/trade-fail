import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { clearToken, getToken, setToken } from '../api/client'

interface AuthState {
  token: string
  signIn: (token: string) => void
  signOut: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTok] = useState(getToken())

  const signIn = useCallback((t: string) => {
    setToken(t)
    setTok(t)
  }, [])

  const signOut = useCallback(() => {
    clearToken()
    setTok('')
  }, [])

  const value = useMemo(() => ({ token, signIn, signOut }), [token, signIn, signOut])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth outside AuthProvider')
  return ctx
}
