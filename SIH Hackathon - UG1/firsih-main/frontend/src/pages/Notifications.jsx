import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useCaseData } from '../context/CaseDataContext.jsx'
import Icon from '../components/Icon.jsx'
import { dateTime } from '../components/RequestCard.jsx'
export default function Notifications() {
  const { notifications, unreadCount, markRead, loading } = useCaseData()
  const [unreadOnly, setUnreadOnly] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function read(id) { setBusy(true); try { await markRead(id); setError('') } catch(e) { setError(e.message) } finally { setBusy(false) } }
  const list = notifications.filter(n => !unreadOnly || !n.read_at)
  return <div className="workspace-page"><div className="page-title-row"><div><div className="eyebrow">STAY UP TO DATE</div><h1>Notifications <span className="heading-count">{unreadCount}</span></h1><p>New requests, reviewer decisions, and access changes—all in one place.</p></div><button className="action-button secondary" disabled={!unreadCount || busy} onClick={() => read('all')}>Mark all as read</button></div>
    <div className="filter-tabs"><button className={!unreadOnly ? 'selected' : ''} aria-pressed={!unreadOnly} onClick={() => setUnreadOnly(false)}>All updates</button><button className={unreadOnly ? 'selected' : ''} aria-pressed={unreadOnly} onClick={() => setUnreadOnly(true)}>Unread<span>{unreadCount}</span></button></div>
    {error && <p className="feedback error" role="alert">{error}</p>}
    <div className="notification-list">{list.map(n => <article className={`notification-card ${n.read_at ? '' : 'is-unread'} kind-${n.kind}`} key={n.id}><div className="notification-symbol"><Icon name={n.kind === 'approved' ? 'check' : n.kind === 'expired' ? 'clock' : n.kind === 'requested' ? 'inbox' : 'bell'} size={22} /></div><div className="notification-body"><div className="notification-title"><h2>{n.title}</h2>{!n.read_at && <span className="unread-dot" aria-label="Unread" />}</div><p>{n.message}</p><small>{dateTime(n.created)} · {n.case_id}</small><div className="notification-actions"><Link className="text-link" to={n.kind === 'requested' ? '/review-inbox' : '/my-requests'}>{n.kind === 'requested' ? 'Go to Review Inbox' : 'Go to My Requests'}<Icon name="arrow" size={16} /></Link>{!n.read_at && <button disabled={busy} className="quiet-button" onClick={() => read(n.id)}>Mark as read</button>}</div></div></article>)}</div>
    {!loading && !list.length && <div className="empty-card"><Icon name="bell" size={32} /><h2>You’re all caught up</h2><p>New updates will appear here automatically while the app is open.</p></div>}
    <p className="page-footnote">In-app updates refresh every 5 seconds. Updates received while you’re away are available next time you sign in.</p>
  </div>
}
