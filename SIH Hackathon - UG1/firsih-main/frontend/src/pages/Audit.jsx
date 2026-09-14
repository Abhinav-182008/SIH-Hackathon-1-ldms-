import React from 'react'
import { useCaseData } from '../context/CaseDataContext.jsx'
import { dateTime } from '../components/RequestCard.jsx'
import Icon from '../components/Icon.jsx'
export default function Audit() {
  const { auditLog, refresh } = useCaseData()
  return <div className="workspace-page"><div className="page-title-row"><div><div className="eyebrow">ACTIVITY & ACCOUNTABILITY</div><h1>Audit history</h1><p>Your activity and events for cases you are assigned to review.</p></div><button className="action-button secondary" onClick={refresh}>Refresh</button></div><div className="audit-notice"><Icon name="audit" /><p>These are server-recorded events. Hash-chain verification and tamper-proof audit integrity are not implemented.</p></div><div className="table-scroll"><table className="activity-table"><thead><tr><th>Event</th><th>Actor</th><th>Case</th><th>Time</th></tr></thead><tbody>{auditLog.map(e => <tr key={e.id}><td>{e.action}</td><td>{e.actor}</td><td>{e.case_id || '—'}</td><td>{dateTime(e.at)}</td></tr>)}</tbody></table>{!auditLog.length && <div className="empty-card">No events to display yet.</div>}</div></div>
}
