import React, { useEffect, useState } from 'react'
import { api } from '../utils/api.js'
import { dateTime } from './RequestCard.jsx'
import './DocumentInformation.css'

const labels = { case_id: 'Case ID stated in document', fir_number: 'FIR / crime number', police_station: 'Police station', district: 'District', document_type: 'Document type', crime_type: 'Crime type', sections_statutes: 'Sections / statutes', incident_date: 'Incident date', report_date: 'Report date', complainant: 'Complainant', investigating_officer: 'Investigating officer', persons_entities: 'Named persons / entities', location: 'Location', summary: 'Factual summary', other_metadata: 'Other factual metadata', uncertainties: 'Uncertainties' }
export default function DocumentInformation({ documentId, sha256 }) {
  const [records, setRecords] = useState([])
  const [canConfirm, setCanConfirm] = useState(false)
  const [editing, setEditing] = useState(null)
  const [values, setValues] = useState({})
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [integrity, setIntegrity] = useState(null)
  const [hash, setHash] = useState(sha256)
  const base = '/documents/' + encodeURIComponent(documentId)
  async function load() {
    const result = await api(base + '/extractions')
    setRecords(result.records); setCanConfirm(result.canConfirm)
  }
  useEffect(() => {
    let active = true
    api(base + '/extractions').then(r => { if (active) { setRecords(r.records); setCanConfirm(r.canConfirm) } }).catch(e => { if (active) setError(e.message) })
    return () => { active = false }
  }, [base])
  async function run(label, fn) {
    setBusy(label); setError(''); setNotice('')
    try { await fn() } catch(e) { setError(e.message) } finally { setBusy('') }
  }
  async function update(record, action, fields = record.fields) {
    await api(base + '/extractions/' + record.id + '/' + action, { fields })
    setEditing(null); await load()
  }
  return <section className="document-information" aria-label="Document integrity and case information">
    <div className="document-tools">
      <button className="action-button secondary" disabled={!!busy} onClick={() => run('Verifying…', async () => { setIntegrity(null); const r = await api(base + '/integrity', {}); setIntegrity(r.verified); setHash(r.sha256) })}>Verify Integrity</button>
      <button className="action-button primary" disabled={!!busy || !!editing} onClick={() => run('Extracting case information…', async () => { const r = await api(base + '/extractions', {}); await load(); if (r.cleanupWarning) setNotice(r.cleanupWarning) })}>Extract Case Information with AI</button>
    </div>
    <p className="muted">Optional AI extraction sends this document to xAI for processing. Use synthetic documents only. AI supports PDF, TXT, PNG and JPG up to 20 MB; original uploads still support 50 MB.</p>
    <p role="status" className={integrity === false ? 'feedback error' : integrity === true ? 'feedback success' : 'muted'}>{integrity === null ? 'Not verified in this session' : integrity ? 'Integrity Verified — document matches its original fingerprint.' : 'Integrity Verification Failed — stored document does not match its original fingerprint.'}</p>
    {hash && <details><summary>SHA-256 fingerprint · {hash.slice(0,12)}…</summary><code className="source-hash">{hash}</code></details>}
    {busy && <p role="status">{busy} Please wait.</p>}{error && <p className="feedback error" role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
    {records.map(record => <article className="extraction-record" key={record.id}>
      <h4>{record.status === 'verified' ? 'Human Verified' : 'AI-Extracted Draft — Human verification required'}</h4>
      <p className="muted">Linked case: {record.case_id} · Model: {record.model}</p>
      {record.status === 'verified' && <p>Confirmed by {record.confirmed_by} · {dateTime(record.confirmed_at)}</p>}
      <details><summary>Source document and original SHA-256</summary><p>{record.document_id}</p><code className="source-hash">{record.source_sha256}</code></details>
      <table className="extraction-table"><thead><tr><th scope="col">Field</th><th scope="col">Extracted Value</th></tr></thead><tbody>{Object.entries(record.fields).map(([field,value]) => <tr key={field}><th scope="row">{labels[field] || field}</th><td>{editing === record.id ? <textarea aria-label={labels[field] || field} maxLength={4000} value={values[field] ?? ''} placeholder="Not stated / uncertain" onChange={e => setValues(v => ({...v, [field]: e.target.value || null}))} /> : value ?? <span className="muted">Not stated / uncertain</span>}</td></tr>)}</tbody></table>
      {record.status === 'draft' && <><p className="muted">Review against the original. Confirmation records your verification; it does not establish the truth of allegations or replace the original.</p><div className="document-tools">
        {editing === record.id ? <><button className="action-button secondary" disabled={!!busy} onClick={() => run('Saving draft…', () => update(record, 'edit', values))}>Save draft edits</button><button className="action-button secondary" disabled={!!busy} onClick={() => setEditing(null)}>Cancel edits</button></> : <button className="action-button secondary" disabled={!!busy} onClick={() => { setValues({...record.fields}); setEditing(record.id) }}>Edit</button>}
        {canConfirm && <button className="action-button primary" disabled={!!busy} onClick={() => run('Confirming…', () => update(record, 'confirm', editing === record.id ? values : record.fields))}>✓ Confirm Information</button>}
        <button className="action-button secondary" disabled={!!busy} onClick={() => run('Discarding…', () => update(record, 'discard'))}>Cancel / Discard</button>
      </div>{!canConfirm && <p>Read-only access: an assigned officer or reviewer must extract and confirm information.</p>}</>}
    </article>)}
  </section>
}
