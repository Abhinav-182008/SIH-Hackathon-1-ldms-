import React, { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useCaseData } from '../context/CaseDataContext.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { api } from '../utils/api.js'
import Icon from '../components/Icon.jsx'
import RequestCard, { requestStatus } from '../components/RequestCard.jsx'

export default function Requests({ review = false }) {
  const { officer } = useAuth()
  const { accessRequests, loading, refresh, canReview } = useCaseData()
  const [filter, setFilter] = useState(review ? 'pending' : 'all')
  const [durations, setDurations] = useState({})
  const [customDays, setCustomDays] = useState({})
  const daysFor = id => Number((durations[id] ?? '1') === 'custom' ? (customDays[id] ?? '1') : (durations[id] ?? '1'))
  const validDays = id => Number.isInteger(daysFor(id)) && daysFor(id) >= 1 && daysFor(id) <= 30
  const [busy, setBusy] = useState(false)
  const [feedback, setFeedback] = useState('')
  const [error, setError] = useState('')
  const [revoke, setRevoke] = useState(null)
  const dialog = useRef(null)
  const cancelButton = useRef(null)
  const revokeTrigger = useRef(null)
  useEffect(() => {
    if (revoke) { dialog.current.showModal(); cancelButton.current?.focus() }
    else if (dialog.current?.open) { dialog.current.close(); revokeTrigger.current?.focus() }
  }, [revoke])
  const rows = accessRequests.filter(r => review ? r.canReview : r.requester === officer.officer_id)
  const shown = rows.filter(r => filter === 'all' || requestStatus(r) === filter)
  async function decide(request, action) {
    if (action === 'approve' && !validDays(request.id)) { setError('Choose a whole number of days from 1 to 30.'); return }
    setBusy(true); setError(''); setFeedback('')
    try {
      await api('/requests/' + encodeURIComponent(request.id), { action, hours: daysFor(request.id) * 24 })
      setRevoke(null)
      setFeedback(`${request.case_id}: access ${action === 'approve' ? 'approved' : action === 'reject' ? 'rejected' : 'revoked'}. ${request.requesterName || request.requester} has been notified.`)
      await refresh()
    } catch (e) { setError(e.message) }
    finally { setBusy(false) }
  }
  if (review && !loading && !canReview) return <div className="workspace-page"><div className="empty-card"><Icon name="requests" size={34} /><h1>This inbox is for assigned reviewers</h1><p>Track your own submissions in My Requests.</p><Link className="action-button primary" to="/my-requests">Go to My Requests</Link></div></div>
  return <div className="workspace-page"><div className="page-title-row"><div><div className="eyebrow">{review ? 'REVIEW & AUTHORIZE' : 'YOUR ACCESS JOURNEY'}</div><h1>{review ? 'Review Inbox' : 'My Requests'}</h1><p>{review ? 'Review new requests, set the access window, and manage existing grants.' : 'Follow every request from submission to decision. Open approved cases directly.'}</p></div><button className="action-button secondary" onClick={refresh} disabled={loading || busy}>Refresh</button></div>
    {feedback && <div className="feedback success" role="status"><Icon name="check" />{feedback}</div>}{error && !revoke && <div className="feedback error" role="alert">{error}</div>}
    <div className="filter-tabs" aria-label="Filter requests">{['all','pending','approved','rejected','expired','revoked'].map(status => <button key={status} aria-pressed={filter === status} className={filter === status ? 'selected' : ''} onClick={() => setFilter(status)}>{status === 'all' ? 'All requests' : status === 'approved' ? 'Active grants' : status.charAt(0).toUpperCase()+status.slice(1)}<span>{rows.filter(r => status === 'all' || requestStatus(r) === status).length}</span></button>)}</div>
    {loading && <p className="muted" role="status">Loading your requests…</p>}
    <div className="request-grid">{shown.map(r => <RequestCard request={r} review={review} key={r.id}>{review && requestStatus(r) === 'pending' && <div className="decision-row"><div className="duration-fields"><label htmlFor={'grant-duration-' + r.id}>Grant access for</label><select id={'grant-duration-' + r.id} value={durations[r.id] ?? '1'} disabled={busy} onChange={e => setDurations(d => ({ ...d, [r.id]: e.target.value }))}>{[1,2,3,5,10,15,20,30].map(days => <option value={String(days)} key={days}>{days} {days === 1 ? 'day' : 'days'}</option>)}<option value="custom">Custom number of days</option></select>{durations[r.id] === 'custom' && <label className="custom-days" htmlFor={'custom-days-' + r.id}>Days (1–30)<input id={'custom-days-' + r.id} type="number" min="1" max="30" step="1" required disabled={busy} value={customDays[r.id] ?? '1'} aria-invalid={!validDays(r.id)} onChange={e => setCustomDays(d => ({ ...d, [r.id]: e.target.value }))} /></label>}</div><button className="action-button primary" disabled={busy || !validDays(r.id)} onClick={() => decide(r,'approve')}><Icon name="check" size={16} />Approve access</button><button className="action-button danger-outline" disabled={busy} onClick={() => decide(r,'reject')}>Reject</button></div>}
      {review && requestStatus(r) === 'approved' && <div className="decision-row"><p className="muted">This grant is active until its expiry time.</p><button className="action-button danger-outline" disabled={busy} onClick={e => { revokeTrigger.current=e.currentTarget; setError(''); setRevoke(r) }}>Revoke access</button></div>}
    </RequestCard>)}</div>
    {!loading && !shown.length && <div className="empty-card"><Icon name={review ? 'inbox' : 'requests'} size={32} /><h2>{review ? 'Your inbox is clear' : 'No requests in this view'}</h2><p>{review ? 'Requests assigned to you will appear here with a notification.' : 'Browse case records and request access with a reason.'}</p>{!review && <Link className="action-button primary" to="/search-record">Browse case records<Icon name="arrow" size={16} /></Link>}</div>}
    <dialog ref={dialog} className="confirm-dialog" aria-labelledby="revoke-title" aria-describedby="revoke-description" onCancel={e => { e.preventDefault(); if (!busy) setRevoke(null) }}>
      <div className="dialog-icon"><Icon name="audit" size={28} /></div><h2 id="revoke-title">Revoke this access grant?</h2><p id="revoke-description">{revoke?.requesterName || revoke?.requester} will lose this grant for <strong>{revoke?.case_id}</strong> immediately and receive a notification.</p>
      <div className="disclaimer"><strong>Before you continue</strong><ul><li>Future views and downloads using this grant will be blocked.</li><li>Other valid assignments or grants may still permit access.</li><li>Files already downloaded cannot be recalled or deleted from their device.</li><li>Restoring this grant requires a new request and approval.</li></ul></div>
      {error && <p className="feedback error" role="alert">{error}</p>}<div className="dialog-actions"><button ref={cancelButton} className="action-button secondary" disabled={busy} onClick={() => setRevoke(null)}>Keep access</button><button className="action-button danger" disabled={busy} onClick={() => decide(revoke,'revoke')}>{busy ? 'Revoking…' : 'Confirm revocation'}</button></div>
    </dialog>
  </div>
}
