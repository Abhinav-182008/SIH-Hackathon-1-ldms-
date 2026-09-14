import React, { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { useCaseData } from '../context/CaseDataContext.jsx'
import { api } from '../utils/api.js'
import DocumentInformation from '../components/DocumentInformation.jsx'
import Icon from '../components/Icon.jsx'
import { dateTime } from '../components/RequestCard.jsx'
import './SearchRecord.css'
export default function SearchRecord() {
  const { officer } = useAuth()
  const { cases, accessRequests, refresh, loading } = useCaseData()
  const [params, setParams] = useSearchParams()
  const target = params.get('case')
  const [query, setQuery] = useState(target || '')
  const [results, setResults] = useState([])
  const [detail, setDetail] = useState(null)
  const [error, setError] = useState('')
  const [feedback, setFeedback] = useState('')
  const [busy, setBusy] = useState(false)
  const [searching, setSearching] = useState(false)
  const [reasons, setReasons] = useState({})
  useEffect(() => {
    let active = true
    if (!query.trim()) { setResults([]); setSearching(false); return }
    setSearching(true)
    const timer = setTimeout(() => api('/search?q=' + encodeURIComponent(query)).then(r => { if (active) setResults(r) }).catch(e => { if (active) { setResults([]); setError(e.message) } }).finally(() => { if (active) setSearching(false) }), 250)
    return () => { active=false; clearTimeout(timer) }
  }, [query,cases])
  useEffect(() => {
    let active = true
    setDetail(null); setError('')
    if (target) {
      setQuery(target)
      api('/cases/' + encodeURIComponent(target)).then(r => { if (active) { setDetail(r); refresh() } }).catch(e => { if (active) setError(e.message === 'Access denied' ? 'This case needs access approval. You can request access from its entry below.' : e.message) })
    }
    return () => { active = false }
  }, [target,officer])
  useEffect(() => {
    if (detail && !loading && !cases.some(c => c.case_id === detail.case_id && c.eligible)) { setDetail(null); setError('Your access has changed. An active assignment or grant is required to open this case.') }
  }, [cases,detail,loading])
  async function act(fn) {
    setBusy(true); setError('')
    try { await fn(); await refresh() } catch(e) { setError(e.message) } finally { setBusy(false) }
  }
  async function download(file) {
    const response = await fetch('/api/documents/' + encodeURIComponent(file.id), { credentials: 'same-origin' })
    if (!response.ok) { const result = await response.json(); throw new Error(result.error) }
    const url = URL.createObjectURL(await response.blob())
    const link = document.createElement('a'); link.href=url; link.download=file.name; link.click()
    setTimeout(() => URL.revokeObjectURL(url),1000)
  }
  const display = query.trim() ? results : cases
  return <div className="workspace-page"><div className="page-title-row"><div><div className="eyebrow">FIND & ACCESS</div><h1>Case records</h1><p>Search case metadata, open authorized files, or request access with a reason.</p></div><Link className="action-button secondary" to="/my-requests">My Requests<Icon name="arrow" size={16} /></Link></div>
    {error && <p className="feedback error" role="alert">{error}</p>}{feedback && <div className="feedback success" role="status">{feedback}<Link to="/my-requests">Track request →</Link></div>}
    <div className="search-box"><Icon name="search" /><input aria-label="Search records" placeholder="Search case ID, station, or authorized notes…" value={query} onChange={e => setQuery(e.target.value)} /></div>
    <div className="chip-row">{['red car','Highway','2024-CR-104','Missing person'].map(q => <button className="chip" key={q} onClick={() => setQuery(q)}>{q}</button>)}</div><p className="results-count">{searching ? 'Searching…' : `${display.length} case ${display.length === 1 ? 'entry' : 'entries'}`}</p>
    {display.map(c => {
      const pending = accessRequests.find(r => r.case_id === c.case_id && r.requester === officer.officer_id && r.status === 'pending')
      return <article className="result-card" key={c.case_id}><div className="result-top"><div><span className="case-reference"><Icon name="file" size={16} />{c.case_id}</span><h2 className="result-title">{c.crime_type}</h2><p className="muted">{c.station_name}</p></div><span className={`case-access-badge ${c.eligible ? 'access-available' : 'access-restricted'}`}><Icon name={c.eligible ? 'check' : 'lock'} size={19} />{c.eligible ? 'Access available' : 'Restricted'}</span></div>
        {c.eligible ? (detail?.case_id !== c.case_id && <button disabled={busy} className="action-button primary" onClick={() => { if (target === c.case_id) act(async () => setDetail(await api('/cases/' + encodeURIComponent(c.case_id)))); else setParams({case:c.case_id}) }}>Open case<Icon name="arrow" size={16} /></button>) : pending ? <div className="inline-pending"><Icon name="clock" size={18} /><span>Your request is awaiting review.</span><Link className="text-link" to="/my-requests">View request →</Link></div> : <form className="request-form" onSubmit={e => { e.preventDefault(); act(async () => { await api('/requests',{caseId:c.case_id,reason:reasons[c.case_id]}); setFeedback('Request submitted. The assigned reviewer has been notified.'); setReasons(r => ({...r,[c.case_id]:''})) }) }}><label htmlFor={'reason-'+c.case_id}>Why do you need access?</label><div><input id={'reason-'+c.case_id} required maxLength={1000} placeholder="Enter your investigation purpose…" value={reasons[c.case_id] || ''} onChange={e => setReasons(r => ({...r,[c.case_id]:e.target.value}))} /><button disabled={busy || !reasons[c.case_id]?.trim()} className="action-button secondary">Request access<Icon name="arrow" size={16} /></button></div></form>}
        {detail?.case_id === c.case_id && c.eligible && <div className="detail-panel"><div className="detail-heading"><h3>Case details</h3><button className="quiet-button" onClick={() => { setDetail(null); setParams({}) }}>Close details</button></div>{Object.entries({suspect_name:'Suspect / party',section_act:'Section / Act',incident_location:'Incident location',summary:'Summary',investigating_officer:'Investigating officers',assisting_officer:'Assisting officers'}).map(([key,label]) => <div className="item" key={key}><span>{label}</span><span>{Array.isArray(detail[key]) ? detail[key].join(', ') : detail[key] || '—'}</span></div>)}<div className="item full"><h3>Stored originals</h3>{!detail.files.length ? <p className="muted">No original files have been uploaded.</p> : detail.files.map(file => <div className="stored-document" key={file.id}><div className="document-row"><Icon name="file" /><div><strong>{file.name}</strong><p>{file.type} · {dateTime(file.created)}</p><p>{Object.entries(JSON.parse(file.metadata)).filter(([,v]) => v).map(([k,v]) => k+': '+v).join(' · ')}</p></div><button disabled={busy} className="action-button secondary" onClick={() => act(() => download(file))}>Download</button></div><DocumentInformation documentId={file.id} sha256={file.sha256} /></div>)}</div></div>}
      </article>
    })}
    {!loading && !searching && !display.length && <div className="empty-card"><Icon name="search" size={30} /><h2>No matches found</h2><p>Try a case ID or station. Restricted private text is excluded from your search.</p></div>}
    <p className="page-footnote">Case IDs, types, and stations are discoverable in this synthetic demo. Protected details are searched only when you have access. OCR and AI search are planned.</p>
  </div>
}
