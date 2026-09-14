import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { useCaseData } from '../context/CaseDataContext.jsx'
import { api } from '../utils/api.js'
import './AddRecord.css'

export default function AddRecord() {
  const { officer } = useAuth()
  const { cases, refresh, error: loadError } = useCaseData()
  const navigate = useNavigate()
  const writable = cases.filter(c => c.canUpload)
  const canCreate = [3, 4].includes(officer.access_level)
  const [mode, setMode] = useState('existing')
  const [form, setForm] = useState({ caseId: '', crimeType: '', documentType: 'FIR', suspectName: '', section: '', location: '', notes: '' })
  const [file, setFile] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(null)
  function change(key, value) { setForm(f => ({ ...f, [key]: value })) }
  async function submit(e) {
    e.preventDefault(); setError('')
    if (!file || file.size === 0 || file.size > 50 * 1024 * 1024) { setError('Choose a non-empty file up to 50 MB.'); return }
    setBusy(true)
    try {
      const content = await new Promise((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = () => resolve(reader.result.split(',')[1])
        reader.onerror = () => reject(new Error('Unable to read the selected file'))
        reader.readAsDataURL(file)
      })
      const result = await api('/upload', { ...form, caseId: form.caseId || (mode === 'existing' ? writable[0]?.case_id : ''), createNew: mode === 'new', name: file.name, content })
      setSaved({ ...result, name: file.name }); await refresh()
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }
  return <div><div className="page-wrap">
    <button className="back-link" onClick={() => navigate('/dashboard')}>← Dashboard</button>
    <div className="page-header"><div className="eyebrow">FILES & METADATA</div><h1>Add record</h1><p>Save an original file and its metadata in the local backend. Synthetic files only. OCR and application-level encryption are not implemented.</p></div>
    {(error || loadError) && <p role="alert">{error || loadError}</p>}
    {saved ? <div className="success-panel"><h4>File and metadata saved</h4><p>{saved.name} · {saved.docId}</p><p>Stored in the backend database, with an upload audit event. Files survive browser refresh and server restart.</p><button onClick={() => navigate('/search-record')}>Search records</button><button onClick={() => { setSaved(null); setFile(null) }}>Add another</button></div> :
    <form onSubmit={submit}>
      <div className="form-section"><h4>Case</h4><div className="case-mode-toggle">
        <button type="button" className={`mode-btn ${mode === 'existing' ? 'active' : ''}`} onClick={() => { setMode('existing'); change('caseId', '') }}>Existing case</button>
        {canCreate && <button type="button" className={`mode-btn ${mode === 'new' ? 'active' : ''}`} onClick={() => { setMode('new'); change('caseId', '') }}>Create case</button>}
      </div>
      <div className="field"><label>Case ID</label>{mode === 'existing' ? <select value={form.caseId || writable[0]?.case_id || ''} onChange={e => change('caseId', e.target.value)} required>
        {!writable.length && <option value="">No assigned cases available for upload</option>}
        {writable.map(c => <option key={c.case_id} value={c.case_id}>{c.case_id} — {c.crime_type}</option>)}
      </select> : <input required maxLength={80} pattern="[A-Za-z0-9_-]+" value={form.caseId} onChange={e => change('caseId', e.target.value)} />}</div>
      {mode === 'new' && <div className="field"><label>Crime type</label><input required maxLength={200} value={form.crimeType} onChange={e => change('crimeType', e.target.value)} /></div>}</div>
      <div className="form-section"><h4>Document</h4><div className="field"><label>Document type</label><select value={form.documentType} onChange={e => change('documentType', e.target.value)}>{['FIR','Investigation Report','Witness Statement','Charge Sheet','Forensic Report','Evidence List'].map(t => <option key={t}>{t}</option>)}</select></div>
      <div className="field"><label>Original file · PDF, PNG, JPG, TXT · up to 50 MB</label><input aria-label="Original file" type="file" accept=".pdf,.png,.jpg,.jpeg,.txt" required onChange={e => setFile(e.target.files[0])} /></div></div>
      <div className="form-section"><h4>Document metadata</h4><p>These details belong to this upload; previous files are preserved.</p>
        {Object.entries({ suspectName: 'Suspect / party', section: 'Section / Act', location: 'Incident location', notes: 'Notes / summary' }).map(([key,label]) => <div className="field" key={key}><label>{label}</label><input aria-label={label} maxLength={4000} value={form[key]} onChange={e => change(key,e.target.value)} /></div>)}
      </div><button className="btn-primary btn-full" disabled={busy || (mode === 'existing' && !writable.length)}>{busy ? 'Saving…' : 'Save file and metadata'}</button>
    </form>}
  </div></div>
}
