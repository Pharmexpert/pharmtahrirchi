'use client'

import React, { useState, useEffect, createContext, useContext } from 'react'
import { ShieldCheck, AlertCircle, Loader2, Database, ShieldAlert, LogIn, UserPlus, Mail, Lock, User } from 'lucide-react'

const AuthContext = createContext<{
  user: any | null
  token: string | null
  login: (token: string, user: any) => void
  logout: () => void
  refreshUser: () => Promise<void>
  isAdmin: boolean
} | null>(null)

export const useAuth = () => useContext(AuthContext)!

export default function LoginGuard({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<any | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  useEffect(() => {
    const savedToken = localStorage.getItem('pharma_token')
    if (savedToken) {
      checkAuth(savedToken)
    } else {
      setLoading(false)
    }
  }, [])

  const checkAuth = async (t: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/auth/me`, {
        headers: { 'Authorization': `Bearer ${t}` }
      })
      if (res.ok) {
        const data = await res.json()
        setUser(data.user)
        setToken(t)
      } else {
        localStorage.removeItem('pharma_token')
      }
    } catch (err) {
      console.error('Auth error:', err)
    } finally {
      setLoading(false)
    }
  }

  const login = (t: string, u: any) => {
    localStorage.setItem('pharma_token', t)
    setToken(t)
    setUser(u)
  }

  const logout = () => {
    localStorage.removeItem('pharma_token')
    setToken(null)
    setUser(null)
    window.location.reload()
  }

  const refreshUser = async () => {
    if (token) await checkAuth(token)
  }

  const isAdmin = user?.role === 'admin'

  const [authMode, setAuthMode] = useState<'login' | 'register' | 'google' | 'forgot' | 'verify_reset' | 'new_password'>('login')
  const [formData, setFormData] = useState({ name: '', email: '', password: '', code: '', confirmPassword: '' })
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  // Initialize Google Login
  useEffect(() => {
    if (!loading && !user && window.google && authMode === 'google') {
      try {
        window.google.accounts.id.initialize({
          client_id: '1069007349621-b47vhi16hf6rdi7phgkga9mobjvfqq3g.apps.googleusercontent.com',
          callback: handleGoogleResponse
        })
        const btnElem = document.getElementById('google-btn')
        if (btnElem) {
          window.google.accounts.id.renderButton(
            btnElem,
            { theme: 'outline', size: 'large', width: 280 }
          )
        }
      } catch (err) {
        console.error('Google GSI error:', err)
      }
    }
  }, [loading, user, authMode])

  const handleGoogleResponse = async (response: any) => {
    setLoading(true)
    setError(null)
    setSuccessMsg(null)
    try {
      const res = await fetch(`${API_BASE}/api/auth/google`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ credential: response.credential })
      })
      const data = await res.json()
      if (res.ok && data.success) {
        login(data.token, data.user)
      } else {
        setError(data.detail || 'Киришда хатолик юз берди')
      }
    } catch (err) {
      setError('Серверга уланишда хатолик')
    } finally {
      setLoading(false)
    }
  }

  const handleSpecialistAuth = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setSuccessMsg(null)
    
    const endpoint = authMode === 'register' ? '/api/auth/register' : '/api/auth/login'
    
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      })
      const data = await res.json()
      
      if (res.ok) {
        if (authMode === 'register') {
          setSuccessMsg(data.message)
          setAuthMode('login')
          setFormData({ ...formData, password: '' })
        } else {
          login(data.token, data.user)
        }
      } else {
        setError(data.detail || 'Хатолик юз берди')
      }
    } catch (err) {
      setError('Серверга уланишда хатолик')
    } finally {
      setLoading(false)
    }
  }

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/api/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: formData.email })
      })
      const data = await res.json()
      if (res.ok) {
        setSuccessMsg(data.message)
        setAuthMode('verify_reset')
      } else {
        setError(data.detail || 'Хатолик юз берди')
      }
    } catch (err) {
      setError('Серверга уланишда хатолик')
    } finally {
      setLoading(false)
    }
  }

  const handleVerifyReset = async (e: React.FormEvent) => {
    e.preventDefault()
    if (formData.code.length !== 6) {
      setError('6 хонали кодни киритинг')
      return
    }
    setAuthMode('new_password')
    setError(null)
  }

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault()
    if (formData.password !== formData.confirmPassword) {
      setError('Пароллар мос келмайди')
      return
    }
    if (formData.password.length < 8) {
      setError('Парол камида 8 белги бўлиши керак')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/api/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          email: formData.email, 
          code: formData.code, 
          password: formData.password 
        })
      })
      const data = await res.json()
      if (res.ok) {
        setSuccessMsg(data.message)
        setAuthMode('login')
      } else {
        setError(data.detail || 'Хатолик юз берди')
      }
    } catch (err) {
      setError('Серверга уланишда хатолик')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div style={{ 
        minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', 
        background: 'var(--bg-primary)' 
      }}>
        <div style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '20px' }}>
          <div style={{ 
            width: '60px', height: '60px', borderRadius: '50%', border: '4px solid var(--border)',
            borderTopColor: 'var(--accent-primary)', animation: 'spin 1s linear infinite'
          }}></div>
          <p style={{ color: 'var(--text-muted)', fontWeight: 600, fontSize: '0.9rem', letterSpacing: '0.5px' }}>
            ТИЗИМГА КИРИШ ТЕКШИРИЛМОҚДА...
          </p>
          <style>{`
            @keyframes spin { to { transform: rotate(360deg); } }
          `}</style>
        </div>
      </div>
    )
  }

  if (!user) {
    return (
      <div style={{ 
        minHeight: '100vh', 
        background: 'var(--bg-primary)', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        padding: '20px'
      }}>
        <div style={{ 
          width: '100%', 
          maxWidth: '440px', 
          background: 'var(--bg-card)', 
          borderRadius: 'var(--radius-xl)', 
          boxShadow: 'var(--shadow-lg)',
          border: '1px solid var(--border)',
          backdropFilter: 'blur(20px)',
          overflow: 'hidden',
          animation: 'fadeIn 0.5s ease'
        }}>
          {/* Header Part */}
          <div style={{ 
            background: 'var(--accent-gradient)', 
            padding: '48px 40px', 
            textAlign: 'center',
            position: 'relative',
            overflow: 'hidden'
          }}>
            <div style={{ 
              position: 'absolute', top: 0, left: 0, width: '100%', height: '100%',
              background: 'radial-gradient(circle at 30% 20%, rgba(255,255,255,0.2) 0%, transparent 50%)'
            }}></div>
            <div style={{ position: 'relative', zIndex: 1 }}>
              <div style={{ 
                width: '64px', height: '64px', background: 'rgba(255,255,255,0.2)', 
                backdropFilter: 'blur(10px)', borderRadius: '18px', display: 'flex',
                alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px',
                boxShadow: '0 8px 32px rgba(0,0,0,0.1)', border: '1px solid rgba(255,255,255,0.3)'
              }}>
                <Database color="white" size={32} />
              </div>
              <h1 style={{ color: 'white', fontSize: '1.8rem', fontWeight: 800, margin: '0 0 4px', letterSpacing: '-0.5px' }}>
                Pharma Expert
              </h1>
              <p style={{ color: 'rgba(255,255,255,0.85)', fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '2px' }}>
                Scientific Translation System
              </p>
            </div>
          </div>
          
          <div style={{ padding: '30px' }}>
            {/* Tabs */}
            <div style={{ 
              display: 'flex', background: 'var(--bg-primary)', padding: '4px', 
              borderRadius: 'var(--radius-lg)', marginBottom: '24px', gap: '4px'
            }}>
              {[
                { id: 'google', icon: <LogIn size={16}/>, label: 'Google' },
                { id: 'login', icon: <LogIn size={16}/>, label: 'Кириш' },
                { id: 'register', icon: <UserPlus size={16}/>, label: 'Рўйхат' }
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => { setAuthMode(tab.id as any); setError(null); setSuccessMsg(null); }}
                  style={{
                    flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                    padding: '10px', borderRadius: 'var(--radius-md)', border: 'none',
                    fontSize: '0.85rem', fontWeight: 600, cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    background: authMode === tab.id ? 'var(--bg-card)' : 'transparent',
                    color: authMode === tab.id ? 'var(--accent-primary)' : 'var(--text-secondary)',
                    boxShadow: authMode === tab.id ? 'var(--shadow-sm)' : 'none'
                  }}
                >
                  {tab.icon}
                  {tab.label}
                </button>
              ))}
            </div>

            {error && (
              <div style={{ 
                background: 'var(--danger-bg)', border: '1px solid rgba(196, 77, 77, 0.15)', 
                color: 'var(--danger)', padding: '14px', borderRadius: 'var(--radius-md)', 
                marginBottom: '20px', fontSize: '0.85rem', display: 'flex', gap: '10px', alignItems: 'flex-start'
              }}>
                <ShieldAlert size={18} style={{ marginTop: '2px', flexShrink: 0 }} />
                <span style={{ fontWeight: 500 }}>{error}</span>
              </div>
            )}

            {successMsg && (
              <div style={{ 
                background: 'rgba(52, 199, 89, 0.1)', border: '1px solid rgba(52, 199, 89, 0.2)', 
                color: '#34c759', padding: '14px', borderRadius: 'var(--radius-md)', 
                marginBottom: '20px', fontSize: '0.85rem', display: 'flex', gap: '10px', alignItems: 'flex-start'
              }}>
                <ShieldCheck size={18} style={{ marginTop: '2px', flexShrink: 0 }} />
                <span style={{ fontWeight: 500 }}>{successMsg}</span>
              </div>
            )}
            
            {authMode === 'google' ? (
              <div style={{ padding: '10px 0 30px' }}>
                <p style={{ color: 'var(--text-secondary)', marginBottom: '24px', textAlign: 'center', fontSize: '0.9rem' }}>
                  Google ҳисобингиз орқали тизимга киринг.
                </p>
                <div style={{ display: 'flex', justifyContent: 'center' }}>
                  <div id="google-btn"></div>
                </div>
              </div>
            ) : (authMode === 'login' || authMode === 'register') ? (
              <form onSubmit={handleSpecialistAuth} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {authMode === 'register' && (
                  <div style={{ position: 'relative' }}>
                    <User size={18} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                    <input 
                      type="text" 
                      placeholder="Исм ва Фамилия"
                      required
                      value={formData.name}
                      onChange={e => setFormData({ ...formData, name: e.target.value })}
                      style={{ 
                        width: '100%', padding: '12px 12px 12px 42px', borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--border)', background: 'var(--bg-primary)',
                        color: 'var(--text-primary)', fontSize: '0.95rem', outline: 'none'
                      }}
                    />
                  </div>
                )}
                <div style={{ position: 'relative' }}>
                  <Mail size={18} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                  <input 
                    type="email" 
                    placeholder="Email почта"
                    required
                    value={formData.email}
                    onChange={e => setFormData({ ...formData, email: e.target.value })}
                    style={{ 
                      width: '100%', padding: '12px 12px 12px 42px', borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--border)', background: 'var(--bg-primary)',
                      color: 'var(--text-primary)', fontSize: '0.95rem', outline: 'none'
                    }}
                  />
                </div>
                <div style={{ position: 'relative' }}>
                  <Lock size={18} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                  <input 
                    type="password" 
                    placeholder="Парол"
                    required
                    value={formData.password}
                    onChange={e => setFormData({ ...formData, password: e.target.value })}
                    style={{ 
                      width: '100%', padding: '12px 12px 12px 42px', borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--border)', background: 'var(--bg-primary)',
                      color: 'var(--text-primary)', fontSize: '0.95rem', outline: 'none'
                    }}
                  />
                </div>
                
                {authMode === 'login' && (
                  <div style={{ textAlign: 'right', marginTop: '-8px' }}>
                    <button 
                      type="button"
                      onClick={() => { setAuthMode('forgot'); setError(null); setSuccessMsg(null); }}
                      style={{ background: 'none', border: 'none', color: 'var(--accent-primary)', fontSize: '0.8rem', cursor: 'pointer', fontWeight: 600 }}
                    >
                      Паролни унутдингизми?
                    </button>
                  </div>
                )}

                <button 
                  type="submit"
                  disabled={loading}
                  style={{ 
                    marginTop: '8px', padding: '12px', background: 'var(--accent-gradient)',
                    color: 'white', border: 'none', borderRadius: 'var(--radius-md)',
                    fontWeight: 700, fontSize: '0.95rem', cursor: 'pointer',
                    boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)',
                    transition: 'all 0.2s ease',
                    opacity: loading ? 0.7 : 1
                  }}
                >
                  {loading ? 'ЮКЛАНМОҚДА...' : (authMode === 'login' ? 'КИРИШ' : 'РЎЙХАТДАН ЎТИШ')}
                </button>
              </form>
            ) : authMode === 'forgot' ? (
              <form onSubmit={handleForgotPassword} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <p style={{ color: 'var(--text-secondary)', textAlign: 'center', fontSize: '0.9rem', marginBottom: '8px' }}>
                  Рўйхатдан ўтган Email манзилингизни киритинг. Код юборилади.
                </p>
                <div style={{ position: 'relative' }}>
                  <Mail size={18} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                  <input 
                    type="email" 
                    placeholder="Email почта"
                    required
                    value={formData.email}
                    onChange={e => setFormData({ ...formData, email: e.target.value })}
                    style={{ 
                      width: '100%', padding: '12px 12px 12px 42px', borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--border)', background: 'var(--bg-primary)',
                      color: 'var(--text-primary)', fontSize: '0.95rem', outline: 'none'
                    }}
                  />
                </div>
                <button 
                  type="submit"
                  disabled={loading}
                  style={{ 
                    marginTop: '8px', padding: '12px', background: 'var(--accent-gradient)',
                    color: 'white', border: 'none', borderRadius: 'var(--radius-md)',
                    fontWeight: 700, fontSize: '0.95rem', cursor: 'pointer',
                    boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)',
                    transition: 'all 0.2s ease'
                  }}
                >
                  {loading ? 'ЮБОРИЛМОҚДА...' : 'КОД ЮБОРИШ'}
                </button>
                <button 
                  type="button"
                  onClick={() => setAuthMode('login')}
                  style={{ background: 'none', border: 'none', color: 'var(--text-muted)', fontSize: '0.85rem', cursor: 'pointer', fontWeight: 600, marginTop: '8px' }}
                >
                  Ортга қайтиш
                </button>
              </form>
            ) : authMode === 'verify_reset' ? (
              <form onSubmit={handleVerifyReset} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <p style={{ color: 'var(--text-secondary)', textAlign: 'center', fontSize: '0.9rem', marginBottom: '8px' }}>
                  Почтангизга юборилган 6 хонали кодни киритинг.
                </p>
                <div style={{ position: 'relative' }}>
                  <ShieldCheck size={18} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                  <input 
                    type="text" 
                    placeholder="6 хонали код"
                    maxLength={6}
                    required
                    value={formData.code}
                    onChange={e => setFormData({ ...formData, code: e.target.value.replace(/\D/g, '') })}
                    style={{ 
                      width: '100%', padding: '12px 12px 12px 42px', borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--border)', background: 'var(--bg-primary)',
                      color: 'var(--text-primary)', fontSize: '1.2rem', letterSpacing: '4px', textAlign: 'center', outline: 'none', fontWeight: 700
                    }}
                  />
                </div>
                <button 
                  type="submit"
                  style={{ 
                    marginTop: '8px', padding: '12px', background: 'var(--accent-gradient)',
                    color: 'white', border: 'none', borderRadius: 'var(--radius-md)',
                    fontWeight: 700, fontSize: '0.95rem', cursor: 'pointer',
                    boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)',
                    transition: 'all 0.2s ease'
                  }}
                >
                  КОДНИ ТАСДИҚЛАШ
                </button>
                <button 
                  type="button"
                  onClick={() => setAuthMode('login')}
                  style={{ background: 'none', border: 'none', color: 'var(--text-muted)', fontSize: '0.85rem', cursor: 'pointer', fontWeight: 600, marginTop: '8px' }}
                >
                  Ортга қайтиш
                </button>
              </form>
            ) : (
              <form onSubmit={handleResetPassword} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <p style={{ color: 'var(--text-secondary)', textAlign: 'center', fontSize: '0.9rem', marginBottom: '8px' }}>
                  Янги паролни киритинг.
                </p>
                <div style={{ position: 'relative' }}>
                  <Lock size={18} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                  <input 
                    type="password" 
                    placeholder="Янги парол"
                    required
                    value={formData.password}
                    onChange={e => setFormData({ ...formData, password: e.target.value })}
                    style={{ 
                      width: '100%', padding: '12px 12px 12px 42px', borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--border)', background: 'var(--bg-primary)',
                      color: 'var(--text-primary)', fontSize: '0.95rem', outline: 'none'
                    }}
                  />
                </div>
                <div style={{ position: 'relative' }}>
                  <Lock size={18} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                  <input 
                    type="password" 
                    placeholder="Паролни тасдиқлаш"
                    required
                    value={formData.confirmPassword}
                    onChange={e => setFormData({ ...formData, confirmPassword: e.target.value })}
                    style={{ 
                      width: '100%', padding: '12px 12px 12px 42px', borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--border)', background: 'var(--bg-primary)',
                      color: 'var(--text-primary)', fontSize: '0.95rem', outline: 'none'
                    }}
                  />
                </div>
                <button 
                  type="submit"
                  disabled={loading}
                  style={{ 
                    marginTop: '10px', padding: '12px', background: 'var(--accent-gradient)',
                    color: 'white', border: 'none', borderRadius: 'var(--radius-md)',
                    fontWeight: 700, fontSize: '0.95rem', cursor: 'pointer',
                    boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)',
                    transition: 'all 0.2s ease'
                  }}
                >
                  {loading ? 'САҚЛАНМОҚДА...' : 'ПАРОЛНИ ЯНГИЛАШ'}
                </button>
              </form>
            )}
            
            <div style={{ 
              marginTop: '40px', paddingTop: '24px', borderTop: '1px solid var(--border)', 
              textAlign: 'center', fontSize: '0.7rem', color: 'var(--text-muted)',
              fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px'
            }}>
              © 2026 Pharma Translation Platform
            </div>

          </div>
        </div>
      </div>
    )
  }

  return (
    <AuthContext.Provider value={{ user, token, login, logout, refreshUser, isAdmin }}>
      {children}
    </AuthContext.Provider>
  )
}

declare global {
  interface Window {
    google: any
  }
}
