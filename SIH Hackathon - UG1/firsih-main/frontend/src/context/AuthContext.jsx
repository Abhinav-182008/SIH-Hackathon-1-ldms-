import React, { createContext, useContext, useEffect, useState } from 'react'
import { api } from '../utils/api.js'
const AuthContext = createContext(null)
export function AuthProvider({ children }) {
  const [officer, setOfficer] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  useEffect(() => { api('/me').then(r => setOfficer(r.officer)).catch(() => {}).finally(() => setLoading(false)) }, [])
  async function login(loginId, password) {
    try {
      const r = await api('/login', { loginId, password })
      setOfficer(r.officer); setError(''); return true
    } catch (e) { setError(e.message); return false }
  }
  async function logout() {
    try { await api('/logout', {}); setOfficer(null); setError(''); return true }
    catch (e) { setError('Logout could not be confirmed: ' + e.message); return false }
  }
  return <AuthContext.Provider value={{ officer, loading, login, logout, error, setError }}>{children}</AuthContext.Provider>
}
export function useAuth() { return useContext(AuthContext) }
