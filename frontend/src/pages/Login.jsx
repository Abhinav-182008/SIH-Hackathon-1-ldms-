import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import './Login.css'
import { ThemeSwitch } from '../components/TopBar.jsx'

export default function Login() {
  const { login, error } = useAuth()
  const navigate = useNavigate()

  const [loginId, setLoginId] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setBusy(true)
    const ok = await login(loginId, password)
    setBusy(false)
    if (ok) navigate('/dashboard')
  }

  return (
    <div className="login-screen"><div className="login-theme"><ThemeSwitch /></div>
      <div className="login-brand">
        <div className="login-mark">
          <div className="login-mark-glyph">CV</div>
          <div>
            <div className="login-mark-name">CaseVault</div>
            <div className="login-mark-sub">Secure Case File System</div>
          </div>
        </div>

        <div className="login-headline">
          <div className="login-title-with-emblem">
          <img className="national-emblem" src="/emblem-of-india.svg" alt="National Emblem of India — Lion Capital of Ashoka" width="76" height="121" />
          <h1 className="login-title">
            <span className="legal-title">Secure Legal &amp; Investigation Document Management</span>
          </h1>
          </div>
          <p className="login-tagline">Secure case files. Smarter search. Controlled access. Tamper-proof justice.</p>
        </div>

        <p>Synthetic-data prototype · Server-validated access. Encryption, AI search, and tamper-proof audit integrity are planned.</p>
      </div>

      <div className="login-form-side">
        <div className="login-card">
          <h2>Sign in</h2><p>Use a synthetic demo account from the project README. Never upload real case material.</p>

          {error && <div className="error-banner">{error}</div>}

          <form onSubmit={handleSubmit}>
            <div className="field">
              <label htmlFor="loginId">Login ID</label>
              <input
                id="loginId"
                type="text"
                placeholder="e.g. rmenon"
                value={loginId}
                onChange={(e) => setLoginId(e.target.value)}
                autoComplete="off"
              />
            </div>

            <div className="field">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>

            <button type="submit" className="btn-primary" disabled={busy}>
              Sign in
            </button>
          </form>


        </div>
      </div>
    </div>
  )
}
