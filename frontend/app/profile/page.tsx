'use client'

import React, { useState } from 'react'
import { User, Mail, Lock, Save, CheckCircle2, AlertCircle, Eye, EyeOff, Shield } from 'lucide-react'
import { useAuth } from '../../components/LoginGuard'
import api from '../../services/api'

export default function ProfilePage() {
  const { token, user } = useAuth()
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const [name, setName] = useState(user?.name || '')
  const [email, setEmail] = useState(user?.email || '')
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showOld, setShowOld] = useState(false)
  const [showNew, setShowNew] = useState(false)
  const [saving, setSaving] = useState(false)
  const [savingPw, setSavingPw] = useState(false)
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null)

  const showToast = (msg: string, type: 'success' | 'error' = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3000)
  }

  const handleSaveProfile = async () => {
    if (!name.trim()) return
    setSaving(true)
    try {
      await api.profile.update({ name, email })
      showToast('Профиль янгиланди ✓')
    } catch (e: any) { showToast(e?.detail || 'Хатолик', 'error') }
    finally { setSaving(false) }
  }

  const handleChangePassword = async () => {
    if (!newPassword || newPassword.length < 6) {
      showToast('Парол камида 6 белгидан иборат бўлиши керак', 'error')
      return
    }
    if (newPassword !== confirmPassword) {
      showToast('Паролларни мос келтиринг', 'error')
      return
    }
    setSavingPw(true)
    try {
      await api.profile.changePassword(oldPassword, newPassword)
      showToast('Парол янгиланди ✓')
      setOldPassword(''); setNewPassword(''); setConfirmPassword('')
    } catch (e: any) { showToast(e?.detail || 'Хатолик', 'error') }
    finally { setSavingPw(false) }
  }

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '14px 14px 14px 44px', borderRadius: '12px',
    border: '1.5px solid var(--border)', fontSize: '0.9rem', outline: 'none',
    background: 'var(--bg-card)', boxSizing: 'border-box' as const
  }

  return (
    <div style={{ maxWidth: '640px', margin: '0 auto' }}>
      {toast && (
        <div style={{
          position: 'fixed', bottom: 32, right: 32, zIndex: 2000,
          padding: '14px 24px', borderRadius: '12px', fontWeight: 700,
          background: toast.type === 'success' ? '#16A34A' : '#DC2626',
          color: 'white', display: 'flex', alignItems: 'center', gap: '10px',
          boxShadow: '0 8px 24px rgba(0,0,0,0.15)'
        }}>
          {toast.type === 'success' ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
          {toast.msg}
        </div>
      )}

      {/* Header */}
      <div style={{
        background: 'linear-gradient(135deg, #EFF6FF 0%, #F0F7FF 100%)', borderRadius: '20px',
        padding: '32px', border: '1.5px solid #BFDBFE', marginBottom: '28px',
        display: 'flex', alignItems: 'center', gap: '20px'
      }}>
        <div style={{
          width: 64, height: 64, borderRadius: '50%',
          background: 'linear-gradient(135deg, #2563EB, #7C3AED)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: 'white', fontWeight: 800, fontSize: '1.5rem',
          boxShadow: '0 4px 16px rgba(37,99,235,0.3)'
        }}>
          {(user?.name || 'U')[0].toUpperCase()}
        </div>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 800, marginBottom: '4px' }}>Профиль созламалари</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem', margin: 0 }}>
            {user?.role === 'admin' ? '👑 Администратор' : '👤 Мутахассис'} • {user?.email}
          </p>
        </div>
      </div>

      {/* Profile Info */}
      <div style={{
        background: 'var(--bg-card)', borderRadius: '16px', border: '1px solid var(--border)',
        padding: '28px', marginBottom: '20px', boxShadow: '0 2px 8px rgba(0,0,0,0.04)'
      }}>
        <h2 style={{ fontSize: '1rem', fontWeight: 800, marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <User size={18} /> Шахсий маълумотлар
        </h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ position: 'relative' }}>
            <User size={16} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input value={name} onChange={e => setName(e.target.value)} placeholder="Исм ва фамилия"
              style={inputStyle} />
          </div>
          <div style={{ position: 'relative' }}>
            <Mail size={16} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input value={email} onChange={e => setEmail(e.target.value)} placeholder="Email"
              style={inputStyle} />
          </div>
          <button onClick={handleSaveProfile} disabled={saving} style={{
            padding: '14px', borderRadius: '12px', border: 'none',
            background: 'linear-gradient(135deg, #2563EB, #7C3AED)', color: 'white',
            fontWeight: 800, fontSize: '0.9rem', cursor: saving ? 'default' : 'pointer',
            opacity: saving ? 0.7 : 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px'
          }}>
            <Save size={16} /> {saving ? 'Сақланмоқда...' : 'Профилни сақлаш'}
          </button>
        </div>
      </div>

      {/* Password */}
      <div style={{
        background: 'var(--bg-card)', borderRadius: '16px', border: '1px solid var(--border)',
        padding: '28px', boxShadow: '0 2px 8px rgba(0,0,0,0.04)'
      }}>
        <h2 style={{ fontSize: '1rem', fontWeight: 800, marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Shield size={18} /> Парол созламалари
        </h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', marginBottom: '20px' }}>
          Google OAuth орқали кирган бўлсангиз, «Эски парол»ни бўш қолдиринг. Янги парол ўрнатилгач, электрон почта ва парол билан ҳам кира оласиз.
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ position: 'relative' }}>
            <Lock size={16} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input type={showOld ? 'text' : 'password'} value={oldPassword} onChange={e => setOldPassword(e.target.value)}
              placeholder="Эски парол (мавжуд бўлса)" style={inputStyle} />
            <button onClick={() => setShowOld(!showOld)} style={{ position: 'absolute', right: '14px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
              {showOld ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
          <div style={{ position: 'relative' }}>
            <Lock size={16} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input type={showNew ? 'text' : 'password'} value={newPassword} onChange={e => setNewPassword(e.target.value)}
              placeholder="Янги парол (камида 6 белги)" style={inputStyle} />
            <button onClick={() => setShowNew(!showNew)} style={{ position: 'absolute', right: '14px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
              {showNew ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
          <div style={{ position: 'relative' }}>
            <Lock size={16} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input type="password" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)}
              placeholder="Янги паролни тасдиқланг" style={inputStyle} />
          </div>
          {newPassword && confirmPassword && newPassword !== confirmPassword && (
            <p style={{ color: '#DC2626', fontSize: '0.82rem', fontWeight: 600 }}>⚠️ Паролларни мос келтиринг</p>
          )}
          <button onClick={handleChangePassword} disabled={savingPw} style={{
            padding: '14px', borderRadius: '12px', border: 'none',
            background: 'linear-gradient(135deg, #D97706, #EA580C)', color: 'white',
            fontWeight: 800, fontSize: '0.9rem', cursor: savingPw ? 'default' : 'pointer',
            opacity: savingPw ? 0.7 : 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px'
          }}>
            <Lock size={16} /> {savingPw ? 'Сақланмоқда...' : 'Паролни ўзгартириш'}
          </button>
        </div>
      </div>
    </div>
  )
}
