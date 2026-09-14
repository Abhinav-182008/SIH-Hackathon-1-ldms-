import React from 'react'
import { Link } from 'react-router-dom'
import Icon from './Icon.jsx'
export const dateTime = value => value ? new Date(value * 1000).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : '—'
export const requestStatus = r => r.status === 'approved' && r.expires <= Date.now()/1000 ? 'expired' : r.status
export function Status({ status }) { return <span className={`status-pill status-${status}`}><span />{status === 'approved' ? 'Approved' : status.charAt(0).toUpperCase() + status.slice(1)}</span> }
export default function RequestCard({ request: r, review = false, children, compact = false }) {
  const status = requestStatus(r)
  return <article className={`request-card ${compact ? 'compact' : ''}`}>
    <div className="request-card-top"><h3>{r.caseTitle || 'Case record'}</h3><Status status={status} /></div>
    {!compact && <><div className="request-meta"><div><span>{review ? 'Requested by' : 'Reviewer'}</span><strong>{review ? r.requesterName || r.requester : r.reviewedBy || r.reviewerNames?.join(', ') || 'Assigned reviewer'}</strong></div><div><span>Submitted</span><strong>{dateTime(r.created)}</strong></div></div><div className="request-reason"><span>Reason for access</span><p>{r.reason}</p></div></>}
    <div className="request-card-bottom"><span className={`expiry-note ${status === 'expired' ? 'ended' : ''}`}><Icon name="clock" size={15} />{r.expires ? `${status === 'expired' ? 'Ended' : 'Expires'} ${dateTime(r.expires)}` : status === 'pending' ? 'Waiting for reviewer decision' : status === 'revoked' ? 'Grant withdrawn by reviewer' : 'No active grant'}</span>
      {!review && status === 'approved' && r.canOpen && <Link className="action-button primary" to={'/search-record?case=' + encodeURIComponent(r.case_id)}>Open case<Icon name="arrow" size={16} /></Link>}
      {!review && ['expired','revoked','rejected'].includes(status) && <Link className="action-button secondary" to={'/search-record?case=' + encodeURIComponent(r.case_id)}>View case entry<Icon name="arrow" size={16} /></Link>}
    </div>{children}
  </article>
}
