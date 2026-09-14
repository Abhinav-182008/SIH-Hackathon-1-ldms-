import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { useAuth } from './AuthContext.jsx'
import { api } from '../utils/api.js'
const Context = createContext(null)
const empty = { cases: [], accessRequests: [], auditLog: [], notifications: [], unreadCount: 0, canReview: false }
export function CaseDataProvider({ children }) {
  const { officer } = useAuth()
  const [state, setState] = useState(empty)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const generation = useRef(0)
  const refresh = useCallback(async () => {
    if (!officer) return
    const current = generation.current
    try { const next = await api('/state'); if (generation.current === current) { setState({ ...empty, ...next, ownerId: officer.officer_id }); setError('') } }
    catch (e) { if (generation.current === current) { setState(empty); setError(e.message) } }
    finally { if (generation.current === current) setLoading(false) }
  }, [officer])
  useEffect(() => {
    generation.current += 1
    setState(empty); setLoading(Boolean(officer)); setError('')
    refresh()
    const timer = setInterval(refresh, 5000)
    const onFocus = () => refresh()
    window.addEventListener('focus', onFocus)
    return () => { generation.current += 1; clearInterval(timer); window.removeEventListener('focus', onFocus) }
  }, [refresh, officer])
  async function markRead(id) { await api('/notifications/read', { id }); await refresh() }
  return <Context.Provider value={{ ...(state.ownerId === officer?.officer_id ? state : empty), error, loading: loading || Boolean(officer && state.ownerId !== officer.officer_id), refresh, markRead }}>{children}</Context.Provider>
}
export function useCaseData() { return useContext(Context) }
