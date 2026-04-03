'use client'

import React, { useState, useEffect, createContext, useContext } from 'react'
import { ShieldCheck, AlertCircle, Loader2, Database, ShieldAlert, LogIn, UserPlus, Mail, Lock, User, Info, MessageSquare } from 'lucide-react'

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
  const [formData, setFormData] = useState({ name: '', email: '', password: '', code: '', confirmPassword: '', department: 'Davlat farmakopeyasi ishlab chiqish bo\'limi' })
  const [successMsg, setSuccessMsg] = useState<string | null>(null)
  
  // Translation state
  const [lang, setLang] = useState<'uz' | 'en' | 'ru'>('uz')
  
  useEffect(() => {
    const savedLang = localStorage.getItem('hb_lang') as any
    if (savedLang && ['uz', 'en', 'ru'].includes(savedLang)) {
      setLang(savedLang)
    }
  }, [])

  const t = {
    uz: {
      subtitle: "Иш бошқарув тизимига киринг",
      googleLogin: "Google орқали кириш",
      or: "ёки",
      email: "Email",
      password: "Парол",
      login: "Кириш",
      register: "Рўйхатдан ўтиш",
      forgotPw: "Паролни унутдингизми?",
      noAccount: "Ҳисобингиз йўқми?",
      hasAccount: "Ҳисобингиз борми?",
      name: "Исм-фамилия",
      confirmPw: "Паролни тасдиқланг",
      dept: "Бўлим",
      forgotTitle: "Паролни тиклаш",
      forgotDesc: "Email манзилингизни киритинг",
      sendCode: "📧 Код юбориш",
      enterCode: "Кодни киритинг",
      codeDesc: "Почтангизга юборилган 6 рақамли кодни киритинг",
      newPw: "Янги парол (камида 8 белги)",
      changePw: "🔑 Паролни ўзгартириш",
      backToLogin: "⬅ Кириш саҳифасига қайтиш",
      loading: "Юкланмоқда...",
      checking: "ТИЗИМГА КИРИШ ТЕКШИРИЛМОҚДА...",
      placeholderCode: "123456",
      placeholderName: "Исм Фамилия",
      departments: [
        "Давлат фармакопеяси ишлаб чиқиш бўлими",
        "Сифат назорати бўлими",
        "Стандартлаштириш бўлими",
        "Илмий-тадқиқот бўлими",
        "Бошқа"
      ]
    },
    en: {
      subtitle: "Sign in to the management system",
      googleLogin: "Sign in with Google",
      or: "or",
      email: "Email",
      password: "Password",
      login: "Sign In",
      register: "Register",
      forgotPw: "Forgot your password?",
      noAccount: "Don't have an account?",
      hasAccount: "Already have an account?",
      name: "Full Name",
      confirmPw: "Confirm Password",
      dept: "Department",
      forgotTitle: "Reset Password",
      forgotDesc: "Enter your email address",
      sendCode: "📧 Send Code",
      enterCode: "Enter Code",
      codeDesc: "Enter the 6-digit code sent to your email",
      newPw: "New Password (min 8 characters)",
      changePw: "🔑 Change Password",
      backToLogin: "⬅ Back to Login",
      loading: "Loading...",
      checking: "CHECKING AUTHENTICATION...",
      placeholderCode: "123456",
      placeholderName: "Full Name",
      departments: [
        "State Pharmacopoeia Development Department",
        "Quality Control Department",
        "Standardization Department",
        "Research and Development Department",
        "Other"
      ]
    },
    ru: {
      subtitle: "Войдите в систему управления",
      googleLogin: "Войти через Google",
      or: "или",
      email: "Email",
      password: "Пароль",
      login: "Войти",
      register: "Регистрация",
      forgotPw: "Забыли пароль?",
      noAccount: "Нет аккаунта?",
      hasAccount: "Уже есть аккаунт?",
      name: "Имя и фамилия",
      confirmPw: "Подтвердите пароль",
      dept: "Отдел",
      forgotTitle: "Восстановление пароля",
      forgotDesc: "Введите ваш Email адрес",
      sendCode: "📧 Отправить код",
      enterCode: "Введите код",
      codeDesc: "Введите 6-значный код, отправленный на вашу почту",
      newPw: "Новый пароль (минимум 8 символов)",
      changePw: "🔑 Изменить пароль",
      backToLogin: "⬅ Вернуться к логину",
      loading: "Загрузка...",
      checking: "ПРОВЕРКА АВТОРИЗАЦИИ...",
      placeholderCode: "123456",
      placeholderName: "Имя Фамилия",
      departments: [
        "Отдел разработки Государственной фармакопеи",
        "Отдел контроля качества",
        "Отдел стандартизации",
        "Научно-исследовательский отдел",
        "Другое"
      ]
    }
  }[lang]

  const switchLang = (l: 'uz' | 'en' | 'ru') => {
    setLang(l)
    localStorage.setItem('hb_lang', l)
  }

  // Initialize Google Login
  useEffect(() => {
    let interval: any;
    
    if (!loading && !user && (window as any).google) {
      try {
        (window as any).google.accounts.id.initialize({
          client_id: '1069007349621-b47vhi16hf6rdi7phgkga9mobjvfqq3g.apps.googleusercontent.com',
          callback: handleGoogleResponse,
          auto_select: false
        })
        
        if (authMode === 'login' || authMode === 'google') {
          const render = () => {
            const btnElem = document.getElementById('google-btn-container')
            if (btnElem) {
              (window as any).google.accounts.id.renderButton(
                btnElem,
                { theme: 'outline', size: 'large', width: 368, text: 'signin_with', shape: 'rectangular' }
              )
              return true
            }
            return false
          }
          
          if (!render()) {
            interval = setInterval(() => {
              if (render()) clearInterval(interval)
            }, 100)
          }
        }
      } catch (err) {
        console.error('Google GSI error:', err)
      }
    }
    
    return () => {
      if (interval) clearInterval(interval)
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
      if (authMode === 'register' && formData.password !== formData.confirmPassword) {
        setError(lang === 'uz' ? 'Пароллар мос келмади' : (lang === 'ru' ? 'Пароли не совпадают' : 'Passwords do not match'))
        setLoading(false)
        return
      }

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
          setFormData({ ...formData, password: '', confirmPassword: '' })
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
      setError(lang === 'uz' ? '6 хонали кодни киритинг' : (lang === 'ru' ? 'Введите 6-значный код' : 'Enter 6-digit code'))
      return
    }
    setAuthMode('new_password')
    setError(null)
  }

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault()
    if (formData.password !== formData.confirmPassword) {
      setError(lang === 'uz' ? 'Пароллар мос келмайди' : (lang === 'ru' ? 'Пароли не совпадают' : 'Passwords do not match'))
      return
    }
    if (formData.password.length < 8) {
      setError(lang === 'uz' ? 'Парол камида 8 белги бўлиши керак' : (lang === 'ru' ? 'Пароль должен быть не менее 8 символов' : 'Password must be at least 8 characters'))
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

  if (loading && !user) {
    return (
      <div style={{ 
        minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', 
        background: '#FFF8F0' 
      }}>
        <div style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '20px' }}>
          <div className="loading-spinner"></div>
          <p style={{ color: '#6B5744', fontWeight: 600, fontSize: '0.9rem', letterSpacing: '0.5px' }}>
            {t?.checking || 'ТИЗИМГА КИРИШ ТЕКШИРИЛМОҚДА...'}
          </p>
          <style>{`
            .loading-spinner {
              display: inline-block;
              width: 40px;
              height: 40px;
              border: 3px solid rgba(192, 120, 64, 0.1);
              border-top-color: #C07840;
              border-radius: 50%;
              animation: spin 0.6s linear infinite;
            }
            @keyframes spin { to { transform: rotate(360deg); } }
          `}</style>
        </div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="login-body">
        <style>{`
          .login-body {
            font-family: 'Inter', -apple-system, sans-serif;
            min-height: 100vh;
            background: #FFF8F0;
            background-image:
                radial-gradient(ellipse at 20% 50%, rgba(192, 120, 64, 0.05) 0%, transparent 60%),
                radial-gradient(ellipse at 80% 20%, rgba(212, 149, 107, 0.05) 0%, transparent 60%),
                radial-gradient(ellipse at 50% 100%, rgba(232, 183, 142, 0.05) 0%, transparent 60%);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
            color: #3D2B1F;
          }

          .login-container {
            width: 100%;
            max-width: 440px;
            animation: fadeUp 0.5s ease;
          }

          @keyframes fadeUp {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
          }

          .login-card {
            background: rgba(255, 251, 245, 0.95);
            border: 1px solid rgba(180, 140, 100, 0.12);
            border-radius: 20px;
            padding: 40px 36px;
            box-shadow: 0 8px 40px rgba(120, 80, 40, 0.08);
            backdrop-filter: blur(16px);
          }

          .login-logo {
            text-align: center;
            margin-bottom: 28px;
          }

          .login-logo-icon {
            width: 56px;
            height: 56px;
            background: linear-gradient(135deg, #C07840, #D4956B, #E8B78E);
            border-radius: 14px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 16px rgba(192, 120, 64, 0.25);
            margin-bottom: 16px;
          }

          .login-logo-icon svg {
            width: 28px;
            height: 28px;
            color: white;
          }

          .login-title {
            font-size: 1.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, #C07840, #D4956B);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
          }

          .login-subtitle {
            color: #6B5744;
            font-size: 0.9rem;
            margin-top: 6px;
          }

          .lang-switch {
            display: flex;
            justify-content: center;
            gap: 6px;
            margin-bottom: 24px;
          }

          .lang-btn-login {
            padding: 6px 14px;
            background: transparent;
            color: #9C8B7A;
            border: 1px solid rgba(180, 140, 100, 0.12);
            border-radius: 8px;
            font-size: 0.78rem;
            font-weight: 600;
            cursor: pointer;
            font-family: inherit;
            transition: all 0.25s;
          }

          .lang-btn-login:hover {
            color: #3D2B1F;
            border-color: rgba(180, 140, 100, 0.25);
          }

          .lang-btn-login.active {
            background: #C07840;
            color: white;
            border-color: #C07840;
          }

          .google-btn {
            width: 100%;
            padding: 2px;
            background: white;
            border: 1px solid rgba(180, 140, 100, 0.15);
            border-radius: 12px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.25s;
            overflow: hidden;
            min-height: 48px;
          }

          .google-btn:hover {
            box-shadow: 0 4px 16px rgba(120, 80, 40, 0.1);
          }

          .divider {
            display: flex;
            align-items: center;
            gap: 14px;
            margin: 24px 0;
            color: #9C8B7A;
            font-size: 0.82rem;
          }

          .divider::before,
          .divider::after {
            content: '';
            flex: 1;
            height: 1px;
            background: rgba(180, 140, 100, 0.12);
          }

          .form-group {
            margin-bottom: 16px;
          }

          .form-label {
            display: block;
            font-size: 0.82rem;
            font-weight: 600;
            color: #6B5744;
            margin-bottom: 6px;
          }

          .form-input {
            width: 100%;
            padding: 12px 16px;
            background: #E8F0FE;
            color: #3D2B1F;
            border: 1px solid rgba(180, 140, 100, 0.12);
            border-radius: 10px;
            font-size: 0.9rem;
            font-family: inherit;
            transition: all 0.25s;
            outline: none;
          }

          .form-input:focus {
            border-color: #C07840;
            box-shadow: 0 0 0 3px rgba(192, 120, 64, 0.15);
            background: white;
          }

          .form-select {
            width: 100%;
            padding: 12px 16px;
            background: #E8F0FE;
            color: #3D2B1F;
            border: 1px solid rgba(180, 140, 100, 0.12);
            border-radius: 10px;
            font-size: 0.9rem;
            font-family: inherit;
            cursor: pointer;
            outline: none;
          }

          .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
          }

          .login-primary-btn {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #C07840, #D4956B, #E8B78E);
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 0.95rem;
            font-weight: 700;
            cursor: pointer;
            font-family: inherit;
            transition: all 0.25s;
            box-shadow: 0 4px 16px rgba(192, 120, 64, 0.25);
            margin-top: 8px;
          }

          .login-primary-btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 24px rgba(192, 120, 64, 0.3);
          }

          .login-primary-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
          }

          .switch-mode {
            text-align: center;
            margin-top: 20px;
            font-size: 0.85rem;
            color: #6B5744;
          }

          .switch-mode a {
            color: #C07840;
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
          }

          .switch-mode a:hover {
            text-decoration: underline;
          }

          .alert-box {
            padding: 12px 16px;
            border-radius: 10px;
            font-size: 0.85rem;
            font-weight: 500;
            margin-bottom: 16px;
          }

          .alert-box.error {
            background: rgba(196, 77, 77, 0.1);
            color: #C44D4D;
            border: 1px solid rgba(196, 77, 77, 0.15);
          }

          .alert-box.success {
            background: rgba(59, 155, 110, 0.1);
            color: #3B9B6E;
            border: 1px solid rgba(59, 155, 110, 0.15);
          }

          @media (max-width: 480px) {
            .login-card { padding: 28px 22px; }
            .form-row { grid-template-columns: 1fr; }
          }
        `}</style>

        <div className="login-container">
          <div className="login-card">
            <div className="login-logo">
              <div className="login-logo-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <polyline points="12 6 12 12 16 14" />
                </svg>
              </div>
              <h1 className="login-title">Pharma Expert</h1>
              <p className="login-subtitle" style={{ textTransform: 'uppercase', letterSpacing: '2px', fontWeight: 700, fontSize: '0.75rem', opacity: 0.8 }}>
                Scientific Translation System
              </p>
            </div>

            <div className="lang-switch">
              <button className={`lang-btn-login ${lang === 'uz' ? 'active' : ''}`} onClick={() => switchLang('uz')}>🇺🇿 O'zbekcha</button>
              <button className={`lang-btn-login ${lang === 'en' ? 'active' : ''}`} onClick={() => switchLang('en')}>🇬🇧 English</button>
              <button className={`lang-btn-login ${lang === 'ru' ? 'active' : ''}`} onClick={() => switchLang('ru')}>🇷🇺 Русский</button>
            </div>

            {error && <div className="alert-box error">{error}</div>}
            {successMsg && <div className="alert-box success">{successMsg}</div>}

            {/* LOGIN FORM */}
            {(authMode === 'login' || authMode === 'google') && (
              <div id="loginSection">
                <div id="google-btn-container" className="google-btn"></div>

                <div className="divider"><span>{t.or}</span></div>

                <form onSubmit={handleSpecialistAuth}>
                  <div className="form-group">
                    <label className="form-label">{t.email}</label>
                    <input className="form-input" type="email" required value={formData.email} onChange={e => setFormData({...formData, email: e.target.value})} placeholder="email@example.com" />
                  </div>
                  <div className="form-group">
                    <label className="form-label">{t.password}</label>
                    <input className="form-input" type="password" required value={formData.password} onChange={e => setFormData({...formData, password: e.target.value})} placeholder="••••••••" />
                  </div>
                  <button className="login-primary-btn" type="submit" disabled={loading}>{loading ? t.loading : t.login}</button>
                </form>

                <div style={{ textAlign: 'center', marginTop: '10px' }}>
                  <a onClick={() => setAuthMode('forgot')} style={{ color: '#C07840', fontSize: '0.82rem', cursor: 'pointer', textDecoration: 'underline' }}>{t.forgotPw}</a>
                </div>
                <div className="switch-mode">
                  <span>{t.noAccount}</span> <a onClick={() => setAuthMode('register')}>{t.register}</a>
                </div>
              </div>
            )}

            {/* REGISTER FORM */}
            {authMode === 'register' && (
              <div id="registerSection">
                <form onSubmit={handleSpecialistAuth}>
                  <div className="form-group">
                    <label className="form-label">{t.name}</label>
                    <input className="form-input" type="text" required value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} placeholder={t.placeholderName} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">{t.email}</label>
                    <input className="form-input" type="email" required value={formData.email} onChange={e => setFormData({...formData, email: e.target.value})} placeholder="email@example.com" />
                  </div>
                  <div className="form-row">
                    <div className="form-group">
                      <label className="form-label">{t.password}</label>
                      <input className="form-input" type="password" required value={formData.password} onChange={e => setFormData({...formData, password: e.target.value})} placeholder="••••••••" minLength={8} />
                    </div>
                    <div className="form-group">
                      <label className="form-label">{t.confirmPw}</label>
                      <input className="form-input" type="password" required value={formData.confirmPassword} onChange={e => setFormData({...formData, confirmPassword: e.target.value})} placeholder="••••••••" />
                    </div>
                  </div>
                  <div className="form-group">
                    <label className="form-label">{t.dept}</label>
                    <select className="form-select" value={formData.department} onChange={e => setFormData({...formData, department: e.target.value})}>
                      {(t.departments as string[]).map(d => <option key={d} value={d}>{d}</option>)}
                    </select>
                  </div>
                  <button className="login-primary-btn" type="submit" disabled={loading}>{loading ? t.loading : t.register}</button>
                </form>
                <div className="switch-mode">
                  <span>{t.hasAccount}</span> <a onClick={() => setAuthMode('login')}>{t.login}</a>
                </div>
              </div>
            )}

            {/* FORGOT PASSWORD FORM */}
            {authMode === 'forgot' && (
              <div id="forgotSection">
                <div style={{ textAlign: 'center', marginBottom: '20px' }}>
                  <div style={{ fontSize: '2rem' }}>🔐</div>
                  <h3 style={{ margin: '8px 0' }}>{t.forgotTitle}</h3>
                  <p style={{ color: '#6B5744', fontSize: '0.82rem' }}>{t.forgotDesc}</p>
                </div>
                <form onSubmit={handleForgotPassword}>
                  <div className="form-group">
                    <label className="form-label">{t.email}</label>
                    <input className="form-input" type="email" required value={formData.email} onChange={e => setFormData({...formData, email: e.target.value})} placeholder="email@example.com" />
                  </div>
                  <button className="login-primary-btn" type="submit" disabled={loading}>{loading ? t.loading : t.sendCode}</button>
                </form>
                <div className="switch-mode">
                  <a onClick={() => setAuthMode('login')}>{t.backToLogin}</a>
                </div>
              </div>
            )}

            {/* VERIFY RESET CODE */}
            {authMode === 'verify_reset' && (
              <div id="verifySection">
                <div style={{ textAlign: 'center', marginBottom: '20px' }}>
                  <div style={{ fontSize: '2rem' }}>📬</div>
                  <h3 style={{ margin: '8px 0' }}>{t.enterCode}</h3>
                  <p style={{ color: '#6B5744', fontSize: '0.82rem' }}>{t.codeDesc}</p>
                </div>
                <form onSubmit={handleVerifyReset}>
                  <div className="form-group">
                    <label className="form-label">Код</label>
                    <input className="form-input" type="text" maxLength={6} required value={formData.code} onChange={e => setFormData({...formData, code: e.target.value.replace(/\D/g, '')})} placeholder={t.placeholderCode} style={{ textAlign: 'center', fontSize: '1.5rem', letterSpacing: '8px', fontWeight: 700 }} />
                  </div>
                  <button className="login-primary-btn" type="submit">ТАСДИҚЛАШ</button>
                </form>
                <div className="switch-mode">
                  <a onClick={() => setAuthMode('login')}>{t.backToLogin}</a>
                </div>
              </div>
            )}

            {/* NEW PASSWORD FORM */}
            {authMode === 'new_password' && (
              <div id="newPwSection">
                 <div style={{ textAlign: 'center', marginBottom: '20px' }}>
                  <div style={{ fontSize: '2rem' }}>🔑</div>
                  <h3 style={{ margin: '8px 0' }}>{t.forgotTitle}</h3>
                </div>
                <form onSubmit={handleResetPassword}>
                  <div className="form-group">
                    <label className="form-label">{t.newPw}</label>
                    <input className="form-input" type="password" required value={formData.password} onChange={e => setFormData({...formData, password: e.target.value})} placeholder="••••••••" minLength={8} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">{t.confirmPw}</label>
                    <input className="form-input" type="password" required value={formData.confirmPassword} onChange={e => setFormData({...formData, confirmPassword: e.target.value})} placeholder="••••••••" />
                  </div>
                  <button className="login-primary-btn" type="submit" disabled={loading}>{loading ? t.loading : t.changePw}</button>
                </form>
              </div>
            )}

            <div style={{ 
              marginTop: '40px', 
              paddingTop: '24px', 
              borderTop: '1px dashed rgba(180, 140, 100, 0.2)', 
              textAlign: 'center'
            }}>
              <p style={{ fontSize: '0.75rem', fontWeight: 700, color: '#8B5E3C', letterSpacing: '1px', textTransform: 'uppercase', marginBottom: '8px' }}>
                © 2026 Pharma Translation Platform
              </p>
            </div>

          </div>
        </div>

        {/* Informational Footer (Global) */}
        <div style={{ 
          padding: '40px 20px', 
          textAlign: 'center', 
          width: '100%',
          maxWidth: '600px',
          margin: '0 auto',
          position: 'relative',
          zIndex: 10
        }}>
          <p style={{ fontSize: '0.85rem', color: '#6B5744', lineHeight: '1.8' }}>
            <strong style={{ display: 'block', color: '#8B5E3C', marginBottom: '4px' }}>
              Давлат фармакопеясини ишлаб чиқиш тизими
            </strong>
            Саволлар ва таклифлар билан <strong>Акмалходжа Зайнидинов</strong> номига,<br />
            қуйидаги почта манзилига мурожаат қилишингиз мумкин:<br />
            <a href="mailto:texnopharm@gmail.com" style={{ color: '#C07840', fontWeight: 700, fontSize: '0.9rem', borderBottom: '1px solid #C07840' }}>
              texnopharm@gmail.com
            </a>
          </p>
        </div>
      </div>
    )
  }

  return (
    <AuthContext.Provider value={{ user, token, login, logout, refreshUser, isAdmin }}>
      <div style={{ 
        fontFamily: "'Inter', sans-serif",
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        background: '#FFF8F0',
        backgroundImage: 'radial-gradient(ellipse at 20% 50%, rgba(192, 120, 64, 0.04) 0%, transparent 60%), radial-gradient(ellipse at 80% 20%, rgba(212, 149, 107, 0.04) 0%, transparent 60%)'
      }}>
        <div style={{ flex: 1 }}>
          {children}
        </div>
        
        {/* GLOBAL FOOTER FOR DASHBOARD */}
        <footer style={{ 
          padding: '40px 20px', 
          textAlign: 'center', 
          borderTop: '1px solid rgba(180, 140, 100, 0.1)',
          background: 'rgba(255, 251, 245, 0.5)',
          marginTop: 'auto'
        }}>
          <p style={{ fontSize: '0.8rem', fontWeight: 700, color: '#8B5E3C', letterSpacing: '1px', textTransform: 'uppercase', marginBottom: '8px' }}>
            © 2026 Pharma Translation Platform
          </p>
          <div style={{ fontSize: '0.75rem', color: '#6B5744', lineHeight: '1.6' }}>
             <p style={{ fontWeight: 600 }}>Давлат фармакопеясини ишлаб чиқиш тизими</p>
             <p>Саволлар ва таклифлар билан Акмалходжа Зайнидинов номига, қуйидаги почта манзилига мурожаат қилишингиз мумкин: <a href="mailto:texnopharm@gmail.com" style={{ color: '#C07840', fontWeight: 700 }}>texnopharm@gmail.com</a></p>
          </div>
        </footer>
      </div>
    </AuthContext.Provider>
  )
}
