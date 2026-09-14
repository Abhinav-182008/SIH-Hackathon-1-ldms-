import React from 'react'
import { Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext.jsx'
import { CaseDataProvider } from './context/CaseDataContext.jsx'
import { ThemeProvider } from './context/ThemeContext.jsx'
import TopBar from './components/TopBar.jsx'
import NoticeBanner from './components/NoticeBanner.jsx'
import Login from './pages/Login.jsx'
import Dashboard from './pages/Dashboard.jsx'
import AddRecord from './pages/AddRecord.jsx'
import SearchRecord from './pages/SearchRecord.jsx'
import Requests from './pages/Requests.jsx'
import Notifications from './pages/Notifications.jsx'
import Audit from './pages/Audit.jsx'
import './workspace.css'
function Workspace() {
  const { officer, loading } = useAuth()
  if (loading) return <div className="session-loading">Opening your workspace…</div>
  if (!officer) return <Navigate to="/" replace />
  return <div className="app-shell"><TopBar /><main className="workspace-main"><NoticeBanner /><Outlet /></main></div>
}
export default function App() {
  return <ThemeProvider><AuthProvider><CaseDataProvider><Routes>
    <Route path="/" element={<Login />} />
    <Route element={<Workspace />}>
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/add-record" element={<AddRecord />} />
      <Route path="/search-record" element={<SearchRecord />} />
      <Route path="/my-requests" element={<Requests key="mine" />} />
      <Route path="/review-inbox" element={<Requests key="review" review />} />
      <Route path="/notifications" element={<Notifications />} />
      <Route path="/audit" element={<Audit />} />
    </Route><Route path="*" element={<Navigate to="/" replace />} />
  </Routes></CaseDataProvider></AuthProvider></ThemeProvider>
}
