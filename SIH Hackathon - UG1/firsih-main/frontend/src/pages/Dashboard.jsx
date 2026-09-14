import React from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { useCaseData } from '../context/CaseDataContext.jsx'
import Icon from '../components/Icon.jsx'
import RequestCard, { requestStatus } from '../components/RequestCard.jsx'
export default function Dashboard() {
  const { officer } = useAuth()
  const { cases, accessRequests, canReview, unreadCount, loading } = useCaseData()
  const mine = accessRequests.filter(r => r.requester === officer.officer_id)
  const pending = accessRequests.filter(r => r.canReview && r.status === 'pending')
  const metrics = [
    ['Accessible cases',cases.filter(c => c.eligible).length,'file','/search-record'],
    ['My pending requests',mine.filter(r => requestStatus(r) === 'pending').length,'clock','/my-requests'],
    ['Active grants',mine.filter(r => requestStatus(r) === 'approved').length,'check','/my-requests'],
    ['Unread updates',unreadCount,'bell','/notifications'],
  ]
  const features = [['Case records','Search, request access, and open your case documents.','search','/search-record'],['Add record','Upload an original and keep its details together.','upload','/add-record'],['My Requests','Track decisions, expiry dates, and approved cases.','requests','/my-requests'],...(canReview ? [['Review Inbox','Approve requests and manage access grants.','inbox','/review-inbox']] : []),['Notifications','Catch up on decisions and access changes.','bell','/notifications'],['Audit history','View recorded actions and access events.','audit','/audit']]
  return <div className="workspace-page"><div className="page-title-row"><div><div className="eyebrow">YOUR WORKSPACE, AT A GLANCE</div><h1>Welcome back, {officer.name.split(' ')[0]}.</h1><p>Keep case files organized and access decisions moving.</p></div><Link className="action-button primary" to="/add-record"><Icon name="upload" size={18} />Add record</Link></div>
    <div className="metric-grid">{metrics.map(([label,value,icon,to]) => <Link className="metric-card" key={label} to={to}><span className="metric-icon"><Icon name={icon} /></span><strong>{loading ? '—' : value}</strong><span>{label}</span><Icon name="arrow" size={16} /></Link>)}</div>
    {canReview && <Link className={`review-callout ${pending.length ? 'attention' : ''}`} to="/review-inbox"><span className="callout-icon"><Icon name="inbox" size={27} /></span><div><div className="eyebrow">REVIEW INBOX</div><h2>{pending.length ? `${pending.length} request${pending.length === 1 ? ' needs' : 's need'} your decision` : 'Your review inbox is clear'}</h2><p>{pending.length ? 'Open your inbox to review the reasons and approve or reject access.' : 'New requests for your assigned cases will appear here.'}</p></div><span className="action-button primary">Open inbox<Icon name="arrow" size={17} /></span></Link>}
    <section><div className="section-heading"><h2>Recent requests</h2><Link className="text-link" to="/my-requests">View all requests<Icon name="arrow" size={16} /></Link></div>{mine.length ? <div className="request-grid">{mine.slice(0,2).map(r => <RequestCard compact request={r} key={r.id} />)}</div> : <div className="subtle-empty"><Icon name="requests" /><p>You haven’t requested access yet. Browse case records to get started.</p><Link className="text-link" to="/search-record">Browse cases →</Link></div>}</section>
    <section><div className="section-heading"><h2>Explore your workspace</h2><span className="muted">Everything has its place</span></div><div className="feature-grid">{features.map(([label,description,icon,to]) => <Link className="feature-card" key={to} to={to}><span className="feature-icon"><Icon name={icon} size={23} /></span><h3>{label}</h3><p>{description}</p><span className="text-link">Open<Icon name="arrow" size={16} /></span></Link>)}</div></section>
    <p className="page-footnote">Synthetic data only · Files are saved locally · OCR and application-level encryption are planned.</p>
  </div>
}
