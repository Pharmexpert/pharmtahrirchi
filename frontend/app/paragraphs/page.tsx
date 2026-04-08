'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { Search, Download, Loader2, CheckCircle2, AlertCircle, Edit2, Save, X, ArrowLeft, Clock, Users, BookText, Filter, Trash2 } from 'lucide-react'
import { useAuth } from '../../components/LoginGuard'
import { useLang } from '../../components/LanguageProvider'
import { useRouter } from 'next/navigation'
import * as XLSX from 'xlsx'
import api from '../../services/api'

interface ParagraphEntry {
  id: number
  en_text: string
  ru_text: string
  uz_text: string
  specialist_name: string
  text_id: string
  action_type: string
  created_at: string
}

function formatDate(d?: string) {
  if (!d) return '—'
  try {
    const dt = new Date(d)
    const yy = String(dt.getFullYear()).slice(2)
    const mm = String(dt.getMonth() + 1).padStart(2, '0')
    const dd = String(dt.getDate()).padStart(2, '0')
    return `${yy}-${mm}.${dd}`
  } catch { return '—' }
}

export default function ParagraphsPage() {
  const { token, user } = useAuth()
  const { t } = useLang()
  const router = useRouter()
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const [entries, setEntries] = useState<ParagraphEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [enFilter, setEnFilter] = useState('')
  const [ruFilter, setRuFilter] = useState('')
  const [uzFilter, setUzFilter] = useState('')
  const [textIdFilter, setTextIdFilter] = useState('')
  const [specialistFilter, setSpecialistFilter] = useState('')
  const [actionFilter, setActionFilter] = useState('')
  const [dateFilter, setDateFilter] = useState('')
  const [editEntry, setEditEntry] = useState<Partial<ParagraphEntry> | null>(null)
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null)

  const showToast = (msg: string, type: 'success' | 'error' = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3000)
  }

  const fetchEntries = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.dashboard.all()
      setEntries((data as any).entries || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchEntries() }, [fetchEntries])

  const handleSaveEdit = async () => {
    if (!editEntry || !token) return
    setSaving(true)
    try {
      await api.dashboard.record({
        en: editEntry.en_text || '',
        ru: editEntry.ru_text || '',
        uz: editEntry.uz_text || '',
        specialist: editEntry.specialist_name || user?.name || 'Aniqlanmagan',
        text_id: editEntry.text_id || '',
        action_type: 'Manual Edit'
      })
      showToast('Сақланди ✓')
      setEditEntry(null)
      fetchEntries()
    } catch {
      showToast('Хатолик юз берди', 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleExportXLSX = () => {
    const rows = filtered.map((entry, i) => ({
      '№': i + 1,
      'ENGLISH': entry.en_text || '',
      'РУССКИЙ': entry.ru_text || '',
      'ЎЗБЕКСНА': entry.uz_text || '',
      'МУТАХАССИС': entry.specialist_name || '',
      'МАТН №': entry.text_id || '',
      'АМАЛ ТУРИ': entry.action_type || '',
      'САНА': formatDate(entry.created_at),
    }))
    const ws = XLSX.utils.json_to_sheet(rows)
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, 'Хатбошилар')
    XLSX.writeFile(wb, `paragraphs_${new Date().toISOString().slice(0, 10)}.xlsx`)
  }

  const filtered = entries.filter(entry => {
    const q = search.toLowerCase()
    const matchSearch = !q ||
      (entry.en_text || '').toLowerCase().includes(q) ||
      (entry.ru_text || '').toLowerCase().includes(q) ||
      (entry.uz_text || '').toLowerCase().includes(q)
    const matchEn = !enFilter || (entry.en_text || '').toLowerCase().includes(enFilter.toLowerCase())
    const matchRu = !ruFilter || (entry.ru_text || '').toLowerCase().includes(ruFilter.toLowerCase())
    const matchUz = !uzFilter || (entry.uz_text || '').toLowerCase().includes(uzFilter.toLowerCase())
    const matchTextId = !textIdFilter || (entry.text_id || '').toLowerCase().includes(textIdFilter.toLowerCase())
    const matchSpecialist = !specialistFilter || (entry.specialist_name || '').toLowerCase().includes(specialistFilter.toLowerCase())
    const matchAction = !actionFilter || (entry.action_type || '').toLowerCase().includes(actionFilter.toLowerCase())
    const matchDate = !dateFilter || (entry.created_at || '').includes(dateFilter)
    return matchSearch && matchEn && matchRu && matchUz && matchTextId && matchSpecialist && matchAction && matchDate
  })

  // Unique action types for badges
  const actionTypes = Array.from(new Set(entries.map(e => e.action_type).filter(Boolean)))

  const actionBadgeColor = (action: string) => {
    const a = action.toLowerCase()
    if (a.includes('ai') || a.includes('polished')) return { bg: '#F5F3FF', color: '#7C3AED', border: '#DDD6FE' }
    if (a.includes('manual')) return { bg: '#FFF7ED', color: '#EA580C', border: '#FED7AA' }
    if (a.includes('batch')) return { bg: '#EFF6FF', color: '#2563EB', border: '#BFDBFE' }
    if (a.includes('verified')) return { bg: '#F0FDF4', color: '#16A34A', border: '#BBF7D0' }
    return { bg: '#F8FAFC', color: '#64748B', border: '#E2E8F0' }
  }

  return (
    <div>
      {/* Toast */}
      {toast && (
        <div style={{
          position: 'fixed', bottom: 32, right: 32, zIndex: 2000,
          padding: '14px 24px', borderRadius: '12px', fontWeight: 700,
          background: toast.type === 'success' ? '#16A34A' : '#DC2626',
          color: 'white', display: 'flex', alignItems: 'center', gap: '10px',
          boxShadow: '0 8px 24px rgba(0,0,0,0.15)', animation: 'fadeIn 0.3s'
        }}>
          {toast.type === 'success' ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
          {toast.msg}
        </div>
      )}

      {/* Hero Header */}
      <div style={{
        background: '#FFFBF0', borderRadius: '20px', padding: '32px 36px',
        border: '1.5px solid #FDE68A', marginBottom: '28px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        flexWrap: 'wrap', gap: '20px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <button onClick={() => router.back()} style={{
            width: 44, height: 44, borderRadius: '50%', border: '1.5px solid #FDE68A',
            background: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: 'pointer', color: '#D97706'
          }}>
            <ArrowLeft size={20} />
          </button>
          <div style={{
            width: 52, height: 52, borderRadius: '14px',
            background: 'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '1.6rem', boxShadow: '0 4px 16px rgba(217,119,6,0.3)'
          }}>
            📝
          </div>
          <div>
            <h1 style={{ fontSize: '1.7rem', fontWeight: 800, marginBottom: '4px', letterSpacing: '-0.5px' }}>
              {t('para.title')}
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: 0 }}>
              {t('para.subtitle')}
            </p>
            <div style={{ display: 'flex', gap: '20px', marginTop: '4px' }}>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                <BookText size={12} style={{ display: 'inline', marginRight: 4, verticalAlign: 'middle' }} />
                Жами: <strong>{entries.length}</strong> та
              </span>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                <Users size={12} style={{ display: 'inline', marginRight: 4, verticalAlign: 'middle' }} />
                Мутахассис: <strong>{Array.from(new Set(entries.map(e => e.specialist_name).filter(Boolean))).length}</strong>
              </span>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                Кўрсатилган: <strong>{filtered.length}</strong>
              </span>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button onClick={fetchEntries} style={{
            padding: '8px 16px', borderRadius: '20px', border: '1.5px solid #FDE68A',
            background: 'white', color: '#D97706', fontWeight: 700, fontSize: '0.8rem', cursor: 'pointer',
            display: 'flex', alignItems: 'center', gap: '6px'
          }}>
            🔄 Янгилаш
          </button>

          {actionTypes.map(at => {
            const badge = actionBadgeColor(at)
            return (
              <button key={at} onClick={() => setActionFilter(actionFilter === at ? '' : at)}
                style={{
                  padding: '6px 14px', borderRadius: '16px',
                  border: `1.5px solid ${actionFilter === at ? '#D97706' : badge.border}`,
                  background: actionFilter === at ? '#FFFBEB' : badge.bg,
                  color: badge.color, fontWeight: 600, fontSize: '0.75rem', cursor: 'pointer'
                }}>
                {at}
              </button>
            )
          })}

          <button onClick={handleExportXLSX} style={{
            padding: '8px 16px', borderRadius: '10px', border: '1.5px solid #16A34A',
            background: '#F0FDF4', color: '#16A34A', fontWeight: 700, cursor: 'pointer',
            display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem'
          }}>
            <Download size={15} /> XLSX
          </button>
        </div>
      </div>

      {/* Table */}
      <div style={{
        background: 'var(--bg-card)', borderRadius: '16px',
        border: '1px solid var(--border)', overflow: 'hidden',
        boxShadow: '0 2px 8px rgba(0,0,0,0.04)'
      }}>
        <div className="responsive-table-wrap"><table style={{ width: '100%', minWidth: 720, borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: 'var(--bg-secondary)', borderBottom: '2px solid var(--border)' }}>
              <th style={{ padding: '14px 16px', textAlign: 'left', fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', width: '40px' }}>№</th>
              <th style={{ padding: '14px 16px', textAlign: 'left', fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', width: '20%' }}>ENGLISH</th>
              <th style={{ padding: '14px 16px', textAlign: 'left', fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', width: '20%' }}>РУССКИЙ</th>
              <th style={{ padding: '14px 16px', textAlign: 'left', fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', width: '20%' }}>ЎЗБЕКСНА</th>
              <th style={{ padding: '14px 16px', textAlign: 'left', fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', width: '12%' }}>МУТАХАССИС</th>
              <th style={{ padding: '14px 16px', textAlign: 'center', fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', width: '6%' }}>МАТН №</th>
              <th style={{ padding: '14px 16px', textAlign: 'left', fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', width: '10%' }}>АМАЛ ТУРИ</th>
              <th style={{ padding: '14px 16px', textAlign: 'left', fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', width: '7%' }}>САНА</th>
              <th style={{ padding: '14px 16px', textAlign: 'right', fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', width: '5%' }}>АМАЛ</th>
            </tr>
            {/* Filter Row — each column has its own filter */}
            <tr style={{ background: 'var(--bg-secondary)', borderBottom: '1px solid var(--border)' }}>
              <td style={{ padding: '4px 6px' }}>
                <input placeholder="№" value={search} onChange={e => setSearch(e.target.value)}
                  style={{ width: '100%', padding: '5px 6px', borderRadius: '6px', border: '1px solid var(--border)', background: 'white', fontSize: '0.75rem', outline: 'none', boxSizing: 'border-box' }} />
              </td>
              <td style={{ padding: '4px 6px' }}>
                <input placeholder="English..." value={enFilter} onChange={e => setEnFilter(e.target.value)}
                  style={{ width: '100%', padding: '5px 6px', borderRadius: '6px', border: '1px solid var(--border)', background: 'white', fontSize: '0.75rem', outline: 'none', boxSizing: 'border-box' }} />
              </td>
              <td style={{ padding: '4px 6px' }}>
                <input placeholder="Русский..." value={ruFilter} onChange={e => setRuFilter(e.target.value)}
                  style={{ width: '100%', padding: '5px 6px', borderRadius: '6px', border: '1px solid var(--border)', background: 'white', fontSize: '0.75rem', outline: 'none', boxSizing: 'border-box' }} />
              </td>
              <td style={{ padding: '4px 6px' }}>
                <input placeholder="Ўзбекча..." value={uzFilter} onChange={e => setUzFilter(e.target.value)}
                  style={{ width: '100%', padding: '5px 6px', borderRadius: '6px', border: '1px solid var(--border)', background: 'white', fontSize: '0.75rem', outline: 'none', boxSizing: 'border-box' }} />
              </td>
              <td style={{ padding: '4px 6px' }}>
                <input placeholder="Исм..." value={specialistFilter} onChange={e => setSpecialistFilter(e.target.value)}
                  style={{ width: '100%', padding: '5px 6px', borderRadius: '6px', border: '1px solid var(--border)', background: 'white', fontSize: '0.75rem', outline: 'none', boxSizing: 'border-box' }} />
              </td>
              <td style={{ padding: '4px 6px' }}>
                <input placeholder="№" value={textIdFilter} onChange={e => setTextIdFilter(e.target.value)}
                  style={{ width: '100%', padding: '5px 6px', borderRadius: '6px', border: '1px solid var(--border)', background: 'white', fontSize: '0.75rem', outline: 'none', textAlign: 'center', boxSizing: 'border-box' }} />
              </td>
              <td style={{ padding: '4px 6px' }}>
                <select value={actionFilter} onChange={e => setActionFilter(e.target.value)}
                  style={{ width: '100%', padding: '5px 4px', borderRadius: '6px', border: '1px solid var(--border)', background: 'white', fontSize: '0.7rem', outline: 'none', boxSizing: 'border-box', cursor: 'pointer' }}>
                  <option value="">Барчаси</option>
                  {actionTypes.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </td>
              <td style={{ padding: '4px 6px' }}>
                <input placeholder="Сана..." value={dateFilter} onChange={e => setDateFilter(e.target.value)}
                  style={{ width: '100%', padding: '5px 6px', borderRadius: '6px', border: '1px solid var(--border)', background: 'white', fontSize: '0.7rem', outline: 'none', boxSizing: 'border-box' }} />
              </td>
              <td></td>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={9} style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
                <Loader2 size={28} style={{ animation: 'spin 1s linear infinite', marginBottom: 12 }} />
                <p>Юкланмоқда...</p>
              </td></tr>
            ) : filtered.length === 0 ? (
              <tr><td colSpan={9} style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
                <div style={{ fontSize: '3rem', marginBottom: 12 }}>📝</div>
                <p style={{ fontWeight: 600 }}>Ёзувлар топилмади</p>
                <p style={{ fontSize: '0.85rem', marginTop: 8 }}>Файл юклаш ва таҳрир қилиш орқали маълумотлар бу ерда кўринади</p>
              </td></tr>
            ) : filtered.map((entry, i) => {
              const badge = actionBadgeColor(entry.action_type || '')
              return (
                <tr key={entry.id} style={{ borderBottom: '1px solid var(--border)', transition: 'background 0.15s' }}
                  onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = 'var(--bg-secondary)'}
                  onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = ''}>

                  <td style={{ padding: '12px 16px', color: 'var(--text-muted)', fontWeight: 600, fontSize: '0.82rem' }}>{i + 1}</td>

                  <td style={{ padding: '12px 16px', fontSize: '0.82rem', lineHeight: '1.6', verticalAlign: 'top' }}>
                    <div>
                      {entry.en_text || <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>—</span>}
                    </div>
                  </td>

                  <td style={{ padding: '12px 16px', fontSize: '0.82rem', lineHeight: '1.6', verticalAlign: 'top' }}>
                    <div>
                      {entry.ru_text || <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>—</span>}
                    </div>
                  </td>

                  <td style={{ padding: '12px 16px', fontSize: '0.82rem', lineHeight: '1.6', verticalAlign: 'top' }}>
                    <div>
                      {entry.uz_text || <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>—</span>}
                    </div>
                  </td>

                  <td style={{ padding: '12px 16px' }}>
                    <span style={{ color: '#16A34A', fontWeight: 600, fontSize: '0.85rem' }}>
                      ● {entry.specialist_name || '—'}
                    </span>
                  </td>

                  <td style={{ padding: '12px 16px', textAlign: 'center' }}>
                    {entry.text_id ? (
                      <span style={{
                        fontFamily: 'monospace', fontSize: '0.75rem', padding: '2px 8px',
                        background: '#EFF6FF', color: '#2563EB', borderRadius: '6px', fontWeight: 700
                      }}>{entry.text_id}</span>
                    ) : <span style={{ color: 'var(--text-muted)' }}>—</span>}
                  </td>

                  <td style={{ padding: '12px 16px' }}>
                    <span style={{
                      padding: '3px 10px', borderRadius: '12px', fontSize: '0.72rem',
                      fontWeight: 600, background: badge.bg, color: badge.color,
                      border: `1px solid ${badge.border}`
                    }}>
                      {entry.action_type || '—'}
                    </span>
                  </td>

                  <td style={{ padding: '12px 16px', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                    {formatDate(entry.created_at)}
                  </td>

                  <td style={{ padding: '12px 16px', textAlign: 'right', display: 'flex', gap: '4px', justifyContent: 'flex-end' }}>
                    <button onClick={async () => {
                      if (!confirm('Ушбу ёзувни ўчиришни тасдиқлайсизми?')) return
                      try {
                        const res = await fetch(`${API_BASE}/api/dashboard/${entry.id}`, {
                          method: 'DELETE', headers: { Authorization: `Bearer ${token}` }
                        })
                        if (res.ok) { showToast('Ўчирилди ✓'); fetchEntries() }
                      } catch { showToast('Хатолик', 'error') }
                    }} style={{
                      padding: '6px', borderRadius: '8px', border: '1px solid #FECACA',
                      background: '#FEF2F2', color: '#DC2626', cursor: 'pointer'
                    }}>
                      <Trash2 size={14} />
                    </button>
                    <button onClick={() => setEditEntry({ ...entry })} style={{
                      padding: '6px', borderRadius: '8px', border: 'none',
                      background: '#FFF7ED', color: '#D97706', cursor: 'pointer'
                    }}>
                      <Edit2 size={14} />
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table></div>
      </div>

      {/* Edit Modal */}
      {editEntry && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', backdropFilter: 'blur(6px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '20px'
        }}>
          <div style={{
            background: 'var(--bg-card)', borderRadius: '20px', width: '100%', maxWidth: '640px',
            boxShadow: '0 24px 64px rgba(0,0,0,0.2)', overflow: 'hidden', maxHeight: '90vh', display: 'flex', flexDirection: 'column'
          }}>
            <div style={{ padding: '24px 28px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#FFFBF0' }}>
              <h2 style={{ fontWeight: 800, fontSize: '1.1rem', color: '#D97706' }}>
                ✏️ Хатбоши таҳрирлаш
              </h2>
              <button onClick={() => setEditEntry(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
                <X size={20} />
              </button>
            </div>
            <div style={{ padding: '24px 28px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {[
                { key: 'en_text', label: 'English', ph: 'English text...' },
                { key: 'ru_text', label: 'Русский', ph: 'Русский текст...' },
                { key: 'uz_text', label: 'Ўзбексна', ph: 'O\'zbek matni...' },
              ].map(f => (
                <div key={f.key}>
                  <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    {f.label}
                  </label>
                  <textarea
                    value={(editEntry as any)[f.key] || ''}
                    onChange={e => setEditEntry(prev => ({ ...prev, [f.key]: e.target.value }))}
                    placeholder={f.ph} rows={3}
                    style={{
                      width: '100%', padding: '10px 14px', borderRadius: '10px',
                      border: '1.5px solid var(--border)', background: 'var(--bg-primary)',
                      fontSize: '0.9rem', outline: 'none', resize: 'vertical',
                      fontFamily: 'inherit', boxSizing: 'border-box'
                    }}
                    onFocus={e => e.target.style.borderColor = '#D97706'}
                    onBlur={e => e.target.style.borderColor = 'var(--border)'}
                  />
                </div>
              ))}
            </div>
            <div style={{ padding: '16px 28px', borderTop: '1px solid var(--border)', background: 'var(--bg-secondary)', display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button onClick={() => setEditEntry(null)} style={{ padding: '10px 22px', borderRadius: '10px', border: '1px solid var(--border)', background: 'white', fontWeight: 700, cursor: 'pointer' }}>
                Бекор
              </button>
              <button onClick={handleSaveEdit} disabled={saving} style={{
                padding: '10px 22px', borderRadius: '10px', border: 'none',
                background: 'linear-gradient(135deg, #F59E0B, #D97706)', color: 'white', fontWeight: 700,
                cursor: saving ? 'not-allowed' : 'pointer',
                display: 'flex', alignItems: 'center', gap: '6px', opacity: saving ? 0.7 : 1
              }}>
                {saving ? <Loader2 size={15} style={{ animation: 'spin 1s linear infinite' }} /> : <Save size={15} />}
                Сақлаш
              </button>
            </div>
          </div>
        </div>
      )}

      <style jsx global>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
      `}</style>
    </div>
  )
}
