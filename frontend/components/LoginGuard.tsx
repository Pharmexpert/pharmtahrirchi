'use client'

import React, { useState, useEffect, createContext, useContext } from 'react'
import { ShieldCheck, AlertCircle, Loader2, Database, ShieldAlert } from 'lucide-react'

const AuthContext = createContext<{
  user: any | null
  token: string | null
  login: (token: string, user: any) => void
  logout: () => void
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

  const isAdmin = user?.role === 'admin'

  // Initialize Google Login
  useEffect(() => {
    if (!loading && !user && window.google) {
      window.google.accounts.id.initialize({
        client_id: '1069007349621-b47vhi16hf6rdi7phgkga9mobjvfqq3g.apps.googleusercontent.com',
        callback: handleGoogleResponse
      })
      window.google.accounts.id.renderButton(
        document.getElementById('google-btn'),
        { theme: 'outline', size: 'large', width: 280 }
      )
    }
  }, [loading, user])

  const handleGoogleResponse = async (response: any) => {
    setLoading(true)
    setError(null)
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
          
          <div style={{ padding: '40px' }}>
            <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '8px', textAlign: 'center' }}>
              Хуш келибсиз!
            </h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '32px', textAlign: 'center', fontSize: '0.92rem', lineHeight: '1.6' }}>
              Давом этиш учун Google ҳисобингиз орқали тизимга киринг.
            </p>
            
            {error && (
              <div style={{ 
                background: 'var(--danger-bg)', border: '1px solid rgba(196, 77, 77, 0.15)', 
                color: 'var(--danger)', padding: '14px', borderRadius: 'var(--radius-md)', 
                marginBottom: '24px', fontSize: '0.85rem', display: 'flex', gap: '10px', alignItems: 'flex-start'
              }}>
                <ShieldCheck size={18} style={{ marginTop: '2px' }} />
                <span style={{ fontWeight: 500 }}>{error}</span>
              </div>
            )}
            
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '32px' }}>
              <div id="google-btn"></div>
            </div>
            
            <div style={{ 
              paddingTop: '24px', borderTop: '1px solid var(--border)', 
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
    <AuthContext.Provider value={{ user, token, login, logout, isAdmin }}>
      {children}
    </AuthContext.Provider>
  )
}

declare global {
  interface Window {
    google: any
  }
}
