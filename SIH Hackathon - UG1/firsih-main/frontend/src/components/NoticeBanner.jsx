import React from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useCaseData } from '../context/CaseDataContext.jsx'
import Icon from './Icon.jsx'
export default function NoticeBanner() {
  const { notifications, unreadCount, error } = useCaseData()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const latest = notifications.find(n => !n.read_at)
  if (error) return <div className="feedback error" role="alert">{error} <button onClick={() => navigate('/')}>Sign in again</button></div>
  if (!latest || pathname === '/notifications') return null
  return <div className={`notice-banner notice-${latest.kind}`} role="status"><span className="notice-icon"><Icon name={latest.kind === 'approved' ? 'check' : latest.kind === 'requested' ? 'inbox' : 'bell'} /></span><div><strong>{latest.title}</strong><p>{latest.message}</p></div><button onClick={() => navigate(latest.kind === 'requested' ? '/review-inbox' : '/my-requests')}>{latest.kind === 'requested' ? 'Review request' : 'View my request'}<Icon name="arrow" size={16} /></button><button className="notice-all" onClick={() => navigate('/notifications')}>{unreadCount} unread</button></div>
}
