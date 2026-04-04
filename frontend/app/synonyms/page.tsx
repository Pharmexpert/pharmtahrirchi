'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { Repeat2, Search, Plus, Trash2, Loader2, CheckCircle2, AlertCircle, X, RefreshCw, Languages } from 'lucide-react'
import { useAuth } from '../../components/LoginGuard'

interface Synonym {
  id: number
  word: string
  synonym: string
  lang: string
  frequency: number
  source: string
  created_by: string
  created_at: string
}

export default function SynonymsPage() {
  const { token, user } = useAuth()
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const [synonyms, setSynonyms] = useState<Synonym[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [lang, setLang] = useState<string>('')
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null)
  const [showAdd, setShowAdd] = useState(false)
  const [newWord, setNewWord] = useState('')
  const [newSynonym, setNewSynonym] = useState('')
  const [newLang, setNewLang] = useState('uz')
  const [page, setPage] = useState(0)
  const PER_PAGE = 25

  const showToast = (msg: string, type: 'success' | 'error' = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3000)
  }

  const fetchSynonyms = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (search) params.set('word', search)
      if (lang) params.set('lang', lang)
      const res = await fetch(`${API_BASE}/api/synonyms?${params}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        const d = await res.json()
        setSynonyms(d.synonyms || [])
      }
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }, [API_BASE, token, search, lang])

  useEffect(() => { fetchSynonyms() }, [fetchSynonyms])

  const handleAdd = async () => {
    if (!newWord.trim() || !newSynonym.trim()) return
    try {
      const res = await fetch(`${API_BASE}/api/synonyms/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ word: newWord, synonym: newSynonym, lang: newLang })
      })
      if (res.ok) {
        showToast('Синоним қўшилди ✓')
        setNewWord(''); setNewSynonym(''); setShowAdd(false)
        fetchSynonyms()
      }
    } catch { showToast('Хатолик', 'error') }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Синонимни ўчиришни тасдиқлайсизми?')) return
    try {
      const res = await fetch(`${API_BASE}/api/synonyms/${id}`, {
        method: 'DELETE', headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        showToast('Ўчирилди ✓')
        setSynonyms(synonyms.filter(s => s.id !== id))
      }
    } catch { showToast('Хатолик', 'error') }
  }

  const filtered = synonyms
  const totalPages = Math.ceil(filtered.length / PER_PAGE)
  const pageData = filtered.slice(page * PER_PAGE, (page + 1) * PER_PAGE)

  const langLabel = (l: string) => l === 'uz' ? '🇺🇿 UZ' : l === 'ru' ? '🇷🇺 RU' : l === 'en' ? '🇬🇧 EN' : l
  const langColor = (l: string) => l === 'uz' ? '#16A34A' : l === 'ru' ? '#2563EB' : l === 'en' ? '#9333EA' : '#666'

  return (
    <div>
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

      {/* Hero */}
      <div style={{
        background: 'linear-gradient(135deg, #F0FDF4 0%, #ECFDF5 100%)', borderRadius: '20px',
        padding: '32px 36px', border: '1.5px solid #BBF7D0', marginBottom: '28px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '20px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <div style={{
            width: 52, height: 52, borderRadius: '14px',
            background: 'linear-gradient(135deg, #16A34A 0%, #059669 100%)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 4px 16px rgba(22,163,74,0.3)'
          }}>
            <Repeat2 size={24} color="white" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.7rem', fontWeight: 800, marginBottom: '4px' }}>Синонимлар базаси</h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: 0 }}>
              3 тилда (EN/RU/UZ) синонимлар • Жами: <strong>{filtered.length}</strong> та
            </p>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button onClick={fetchSynonyms} style={{
            padding: '8px 16px', borderRadius: '10px', border: '1.5px solid #BBF7D0',
            background: 'white', color: '#16A34A', fontWeight: 700, fontSize: '0.8rem', cursor: 'pointer',
            display: 'flex', alignItems: 'center', gap: '6px'
          }}><RefreshCw size={14} /> Янгилаш</button>
          <button onClick={() => setShowAdd(true)} style={{
            padding: '10px 22px', borderRadius: '12px', border: 'none',
            background: 'linear-gradient(135deg, #16A34A, #059669)', color: 'white',
            fontWeight: 800, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px',
            fontSize: '0.85rem', boxShadow: '0 4px 16px rgba(22,163,74,0.4)'
          }}><Plus size={16} /> СИНОНИМ ҚЎШИШ</button>
        </div>
      </div>

      {/* Filters */}
      <div style={{ marginBottom: '20px', display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: '200px' }}>
          <Search size={15} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input placeholder="Сўз бўйича қидириш..." value={search} onChange={e => { setSearch(e.target.value); setPage(0) }}
            style={{
              width: '100%', padding: '12px 14px 12px 40px', borderRadius: '12px',
              border: '1.5px solid var(--border)', background: 'var(--bg-card)',
              fontSize: '0.9rem', outline: 'none', boxSizing: 'border-box'
            }} />
        </div>
        {['', 'uz', 'ru', 'en'].map(l => (
          <button key={l} onClick={() => { setLang(l); setPage(0) }} style={{
            padding: '10px 18px', borderRadius: '10px',
            border: lang === l ? '2px solid #16A34A' : '1.5px solid var(--border)',
            background: lang === l ? '#F0FDF4' : 'var(--bg-card)',
            color: lang === l ? '#16A34A' : 'var(--text-primary)',
            fontWeight: 700, fontSize: '0.82rem', cursor: 'pointer'
          }}>{l === '' ? 'Барчаси' : langLabel(l)}</button>
        ))}
      </div>

      {/* Table */}
      <div style={{ background: 'var(--bg-card)', borderRadius: '16px', border: '1px solid var(--border)', overflow: 'hidden', boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}>
        {loading ? (
          <div style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
            <Loader2 size={28} style={{ animation: 'spin 1s linear infinite', marginBottom: 12 }} />
            <p>Юкланмоқда...</p>
          </div>
        ) : pageData.length === 0 ? (
          <div style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
            <Repeat2 size={40} style={{ opacity: 0.2, marginBottom: 12 }} />
            <p style={{ fontWeight: 700 }}>Синонимлар топилмади</p>
          </div>
        ) : (
          <>
            <div style={{
              display: 'grid', gridTemplateColumns: '50px 1fr 1fr 80px 100px 120px 120px 60px',
              padding: '14px 20px', background: 'var(--bg-secondary)', borderBottom: '2px solid var(--border)', gap: '12px'
            }}>
              {['№', 'СЎЗ', 'СИНОНИМ', 'ТИЛ', 'ЧАСТОТА', 'МАНБА', 'МУАЛЛИФ', ''].map(h => (
                <span key={h} style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>{h}</span>
              ))}
            </div>
            {pageData.map((s, i) => (
              <div key={s.id} style={{
                display: 'grid', gridTemplateColumns: '50px 1fr 1fr 80px 100px 120px 120px 60px',
                padding: '12px 20px', borderBottom: '1px solid var(--border)', gap: '12px', alignItems: 'center',
                transition: 'background 0.15s'
              }}
                onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = 'var(--bg-secondary)'}
                onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = ''}
              >
                <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>{page * PER_PAGE + i + 1}</span>
                <span style={{ fontWeight: 700, fontSize: '0.9rem' }}>{s.word}</span>
                <span style={{ fontSize: '0.88rem', color: '#16A34A', fontWeight: 600 }}>{s.synonym}</span>
                <span style={{
                  fontSize: '0.72rem', fontWeight: 700, padding: '2px 8px', borderRadius: '6px',
                  background: `${langColor(s.lang)}15`, color: langColor(s.lang), display: 'inline-block'
                }}>{langLabel(s.lang)}</span>
                <span style={{
                  fontSize: '0.85rem', fontWeight: 800,
                  color: s.frequency > 5 ? '#16A34A' : s.frequency > 0 ? '#D97706' : '#94A3B8'
                }}>{s.frequency}×</span>
                <span style={{
                  fontSize: '0.72rem', fontWeight: 600, padding: '2px 8px', borderRadius: '6px',
                  background: s.source === 'ai' ? '#EFF6FF' : '#F0FDF4',
                  color: s.source === 'ai' ? '#2563EB' : '#16A34A'
                }}>{s.source === 'ai' ? '🤖 AI' : '✏️ Қўлда'}</span>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{s.created_by || '—'}</span>
                <button onClick={() => handleDelete(s.id)} style={{
                  padding: '6px', borderRadius: '8px', border: '1px solid #FECACA',
                  background: '#FEF2F2', color: '#DC2626', cursor: 'pointer'
                }}><Trash2 size={14} /></button>
              </div>
            ))}
          </>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', gap: '8px', marginTop: '20px', flexWrap: 'wrap' }}>
          <button disabled={page === 0} onClick={() => setPage(p => p - 1)} style={{
            padding: '8px 16px', borderRadius: '8px', border: '1px solid var(--border)',
            background: page === 0 ? '#F1F5F9' : 'white', cursor: page === 0 ? 'default' : 'pointer',
            fontWeight: 700, fontSize: '0.82rem', color: page === 0 ? '#94A3B8' : '#334155'
          }}>← Олдинги</button>
          <span style={{ padding: '8px 16px', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)' }}>
            {page + 1} / {totalPages} ({filtered.length} та)
          </span>
          <button disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)} style={{
            padding: '8px 16px', borderRadius: '8px', border: '1px solid var(--border)',
            background: page >= totalPages - 1 ? '#F1F5F9' : 'white', cursor: page >= totalPages - 1 ? 'default' : 'pointer',
            fontWeight: 700, fontSize: '0.82rem', color: page >= totalPages - 1 ? '#94A3B8' : '#334155'
          }}>Кейинги →</button>
        </div>
      )}

      {/* Add Modal */}
      {showAdd && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(4px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
        }}>
          <div style={{
            background: 'var(--bg-card)', borderRadius: '20px', padding: '32px', width: '100%', maxWidth: '480px',
            boxShadow: '0 24px 64px rgba(0,0,0,0.25)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
              <h3 style={{ fontWeight: 800, fontSize: '1.1rem' }}>Синоним қўшиш</h3>
              <button onClick={() => setShowAdd(false)} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
                <X size={20} />
              </button>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <input placeholder="Сўз..." value={newWord} onChange={e => setNewWord(e.target.value)}
                style={{ padding: '12px', borderRadius: '10px', border: '1.5px solid var(--border)', fontSize: '0.9rem' }} />
              <input placeholder="Синоним..." value={newSynonym} onChange={e => setNewSynonym(e.target.value)}
                style={{ padding: '12px', borderRadius: '10px', border: '1.5px solid var(--border)', fontSize: '0.9rem' }} />
              <select value={newLang} onChange={e => setNewLang(e.target.value)}
                style={{ padding: '12px', borderRadius: '10px', border: '1.5px solid var(--border)', fontSize: '0.9rem' }}>
                <option value="uz">🇺🇿 Ўзбекча</option>
                <option value="ru">🇷🇺 Русча</option>
                <option value="en">🇬🇧 Инглизча</option>
              </select>
              <button onClick={handleAdd} style={{
                padding: '14px', borderRadius: '12px', border: 'none',
                background: 'linear-gradient(135deg, #16A34A, #059669)', color: 'white',
                fontWeight: 800, fontSize: '0.9rem', cursor: 'pointer'
              }}>Сақлаш</button>
            </div>
          </div>
        </div>
      )}

      <style jsx global>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  )
}
