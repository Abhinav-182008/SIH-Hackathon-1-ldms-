import React from 'react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { useCaseData } from '../context/CaseDataContext.jsx'
import { useTheme } from '../context/ThemeContext.jsx'
import Icon from './Icon.jsx'

export function ThemeSwitch() {
  const { theme, toggle } = useTheme()
  return <button className="icon-button theme-switch" onClick={toggle} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`} title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}><Icon name={theme === 'dark' ? 'sun' : 'moon'} /></button>
}
export default function TopBar() {
  const { officer, logout, error } = useAuth()
  const { unreadCount, accessRequests, canReview } = useCaseData()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const pending = accessRequests.filter(r => r.canReview && r.status === 'pending').length
  const links = [
    ['/dashboard', 'Overview', 'home'], ['/search-record', 'Case records', 'search'], ['/add-record', 'Add record', 'upload'],
    ['/my-requests', 'My Requests', 'requests'], ...(canReview ? [['/review-inbox', 'Review Inbox', 'inbox', pending]] : []),
    ['/notifications', 'Notifications', 'bell', unreadCount], ['/audit', 'Audit history', 'audit'],
  ]
  return <><aside className="sidebar">
    <NavLink to="/dashboard" className="brand"><span className="brand-mark"><Icon name="audit" size={24} /></span><span>CaseVault<small>RECORDS WORKSPACE</small></span></NavLink>
    <div className="nav-caption">WORKSPACE</div>
    <nav aria-label="Main navigation">{links.map(([to,label,icon,count]) => <NavLink key={to} to={to} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}><Icon name={icon} /><span>{label}</span>{count > 0 && <span className="nav-badge">{count}</span>}</NavLink>)}</nav>
    <div className="sidebar-bottom"><div className="demo-note"><span className="status-dot" />Synthetic demo environment</div><div className="profile-block"><span className="avatar">{officer.name.split(' ').map(n => n[0]).slice(0,2).join('')}</span><div><strong>{officer.name}</strong><small>{officer.rank}</small></div></div><button className="signout" onClick={async () => { if (await logout()) navigate('/') }}><Icon name="logout" size={17} />Sign out</button>{error && <p role="alert">{error}</p>}</div>
  </aside><header className="workspace-topbar"><div><span className="breadcrumb">Workspace / </span><strong>{links.find(l => l[0] === pathname)?.[1] || 'CaseVault'}</strong></div><div className="topbar-tools"><span className="station-label">{officer.station}</span><ThemeSwitch /><button className="icon-button bell-button" aria-label={`Notifications, ${unreadCount} unread`} onClick={() => navigate('/notifications')}><Icon name="bell" />{unreadCount > 0 && <span className="bell-count">{unreadCount}</span>}</button></div></header></>
}
