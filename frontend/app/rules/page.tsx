'use client'

import React, { useState, useEffect } from 'react'
import { 
  Trash2, Edit2, Plus, Search, BookOpen, RefreshCcw,
  Languages, CheckCircle2, AlertCircle, Loader2, X
} from 'lucide-react'
import { useAuth } from '../../components/LoginGuard'

interface Rule {
  id: number
  wrong_form: string
  correct_form: string
  error_type: string
  lang: string
  frequency: number
  updated_at: string
  modified_by?: string
}

export default function RulesPage() {
  const { token } = useAuth()
  const [rules, setRules] = useState<Rule[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [lang, setLang] = useState('uz')
  const [editingRule, setEditingRule] = useState<Partial<Rule> | null>(null)
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null)
  const [page, setPage] = useState(0)
  const [perPage, setPerPage] = useState(25)
  const [filterWrong, setFilterWrong] = useState('')
  const [filterCorrect, setFilterCorrect] = useState('')

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  useEffect(() => { fetchRules() }, [lang])

  const fetchRules = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/admin/rules?lang=${lang}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      const data = await res.json()
      setRules(data.rules || [])
    } catch (err) {
      console.error('Failed to fetch rules:', err)
    } finally {
      setLoading(false)
    }
  }

  const showMessage = (text: string, type: 'success' | 'error' = 'success') => {
    setMessage({ text, type })
    setTimeout(() => setMessage(null), 3000)
  }

  const handleDelete = async (id: number) => {
    if (!confirm("Bu qoidani o'chirishni tasdiqlaysizmi?")) return
    try {
      const res = await fetch(`${API_BASE}/api/admin/rules/${id}`, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } })
      if (res.ok) {
        setRules(rules.filter(r => r.id !== id))
        showMessage('Qoida muvaffaqiyatli o\'chirildi')
      }
    } catch (_e) { showMessage("O'chirishda xatolik", 'error') }
  }

  const handleSave = async () => {
    if (!editingRule?.wrong_form || !editingRule?.correct_form) return
    const isNew = !editingRule.id
    const url = isNew ? `${API_BASE}/api/admin/rules` : `${API_BASE}/api/admin/rules/${editingRule.id}`
    const method = isNew ? 'POST' : 'PUT'
    try {
      const res = await fetch(url, {
        method,
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ ...editingRule, lang })
      })
      if (res.ok) {
        fetchRules()
        setEditingRule(null)
        showMessage(isNew ? 'Yangi qoida qo\'shildi' : 'Qoida yangilandi')
      }
    } catch (_e) { showMessage('Saqlashda xatolik', 'error') }
  }

  const filteredRules = rules.filter(r => {
    const q = search.toLowerCase()
    const matchSearch = !q || r.wrong_form.toLowerCase().includes(q) || r.correct_form.toLowerCase().includes(q)
    const matchWrong = !filterWrong || r.wrong_form.toLowerCase().includes(filterWrong.toLowerCase())
    const matchCorrect = !filterCorrect || r.correct_form.toLowerCase().includes(filterCorrect.toLowerCase())
    return matchSearch && matchWrong && matchCorrect
  })
  const totalPages = Math.ceil(filteredRules.length / perPage)
  const pageRules = filteredRules.slice(page * perPage, (page + 1) * perPage)

  const errorTypeColors: Record<string, { bg: string; color: string }> = {
    'S/Spelling': { bg: 'var(--warning-bg)', color: 'var(--warning)' },
    'S/Context': { bg: 'var(--info-bg)', color: 'var(--info)' },
    'G/Grammar': { bg: 'var(--danger-bg)', color: 'var(--danger)' },
    'Terminology': { bg: 'var(--success-bg)', color: 'var(--success)' },
  }

  return (
    <div className="animate-fadeIn" style={{ maxWidth: '1200px', margin: '0 auto' }}>
      {/* Status Toast */}
      {message && (
        <div style={{ 
          position: 'fixed', bottom: '32px', right: '32px', zIndex: 1000,
          display: 'flex', alignItems: 'center', gap: '12px',
          padding: '16px 24px', borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--shadow-lg)', animation: 'fadeIn 0.3s',
          background: message.type === 'success' ? 'var(--success)' : 'var(--danger)',
          color: 'white', fontWeight: 600, fontSize: '0.9rem'
        }}>
          {message.type === 'success' ? <CheckCircle2 size={20} /> : <AlertCircle size={20} />}
          {message.text}
        </div>
      )}

      {/* Header */}
      <div style={{ marginBottom: '40px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h1 style={{ fontSize: '2.2rem', fontWeight: 800, marginBottom: '8px', letterSpacing: '-1px' }}>
            Sayqallash Qoidalari 📖
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '1.1rem' }}>
            Imlo xatoliklari va tuzatish qoidalari bazasi.
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ 
            display: 'flex', alignItems: 'center', gap: '12px',
            background: 'var(--bg-card)', padding: '12px 20px', borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)'
          }}>
            <BookOpen size={20} color="var(--accent-primary)" />
            <span style={{ fontWeight: 800, fontSize: '1.1rem' }}>{rules.length}</span>
            <span style={{ fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.9rem' }}>Qoida</span>
          </div>
        </div>
      </div>

      {/* Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', gap: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {/* Language Toggle */}
          <div style={{ 
            display: 'flex', background: 'var(--bg-card)', padding: '4px',
            borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)'
          }}>
            {[
              { id: 'uz', label: "O'zbekcha" },
              { id: 'ru', label: 'Русский' }
            ].map(l => (
              <button
                key={l.id}
                onClick={() => setLang(l.id)}
                style={{
                  padding: '10px 20px', borderRadius: 'var(--radius-sm)', border: 'none',
                  fontSize: '0.9rem', fontWeight: 700, cursor: 'pointer', transition: 'all 0.2s',
                  background: lang === l.id ? 'white' : 'transparent',
                  color: lang === l.id ? 'var(--accent-primary)' : 'var(--text-muted)',
                  boxShadow: lang === l.id ? 'var(--shadow-sm)' : 'none'
                }}
              >
                {l.label}
              </button>
            ))}
          </div>

          {/* Add Rule Button */}
          <button 
            onClick={() => setEditingRule({ wrong_form: '', correct_form: '', error_type: 'S/Spelling', lang })}
            style={{ 
              padding: '10px 20px', background: 'var(--accent-gradient)', color: 'white',
              border: 'none', borderRadius: 'var(--radius-md)', fontWeight: 700,
              fontSize: '0.85rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px',
              boxShadow: 'var(--shadow-glow)'
            }}
          >
            <Plus size={18} /> Yangi qoida
          </button>

          {/* Refresh */}
          <button 
            onClick={fetchRules}
            style={{ 
              padding: '10px', background: 'var(--bg-card)', border: '1px solid var(--border)',
              borderRadius: 'var(--radius-md)', cursor: 'pointer', color: 'var(--text-muted)'
            }}
          >
            <RefreshCcw size={18} />
          </button>
        </div>

        {/* Search */}
        <div style={{ position: 'relative', flex: 1, maxWidth: '400px' }}>
          <Search size={18} style={{ position: 'absolute', left: '16px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input 
            type="text" placeholder="Qoidalarni qidirish..."
            value={search} onChange={e => setSearch(e.target.value)}
            style={{ 
              width: '100%', padding: '12px 12px 12px 48px',
              borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)',
              background: 'var(--bg-card)', fontSize: '0.95rem',
              boxShadow: 'var(--shadow-sm)', outline: 'none', transition: 'border-color 0.2s'
            }}
            onFocus={e => e.currentTarget.style.borderColor = 'var(--accent-primary)'}
            onBlur={e => e.currentTarget.style.borderColor = 'var(--border)'}
          />
        </div>
      </div>

      {/* Rules Table */}
      <div style={{ 
        background: 'var(--bg-card)', borderRadius: 'var(--radius-xl)',
        border: '1px solid var(--border)', boxShadow: 'var(--shadow-md)', overflow: 'hidden'
      }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ background: 'var(--bg-secondary)', borderBottom: '2px solid var(--border)' }}>
              <th style={{ padding: '20px 24px', fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Хато шакл</th>
              <th style={{ padding: '20px 24px', fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Тўғри шакл</th>
              <th style={{ padding: '20px 24px', fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Тури</th>
              <th style={{ padding: '20px 24px', fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', textAlign: 'center' }}>Частота</th>
              <th style={{ padding: '20px 24px', fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Ўзгартирган</th>
              <th style={{ padding: '20px 24px', fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', textAlign: 'right' }}>Amallar</th>
            </tr>
            {/* Column Filters */}
            <tr style={{ background: '#FAFBFC', borderBottom: '1px solid var(--border)' }}>
              <th style={{ padding: '8px 24px' }}>
                <input placeholder="🔍 Хато сўз..." value={filterWrong} onChange={e => { setFilterWrong(e.target.value); setPage(0) }}
                  style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid var(--border)', fontSize: '0.78rem', background: 'white' }} />
              </th>
              <th style={{ padding: '8px 24px' }}>
                <input placeholder="🔍 Тўғри сўз..." value={filterCorrect} onChange={e => { setFilterCorrect(e.target.value); setPage(0) }}
                  style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', border: '1px solid var(--border)', fontSize: '0.78rem', background: 'white' }} />
              </th>
              <th style={{ padding: '8px 24px' }}></th>
              <th style={{ padding: '8px 24px' }}></th>
              <th style={{ padding: '8px 24px' }}></th>
              <th style={{ padding: '8px 24px' }}></th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={5} style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  <Loader2 className="animate-spin" size={32} style={{ margin: '0 auto 16px' }} />
                  <p style={{ fontWeight: 600 }}>Yuklanmoqda...</p>
                </td>
              </tr>
            ) : filteredRules.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ padding: '80px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  <BookOpen size={64} style={{ marginBottom: '16px', opacity: 0.2 }} />
                  <h3 style={{ fontSize: '1.2rem', fontWeight: 600 }}>Qoidalar topilmadi</h3>
                  <p style={{ fontSize: '0.9rem', marginTop: '8px' }}>Yangi qoida qo'shish uchun "Yangi qoida" tugmasini bosing.</p>
                </td>
              </tr>
            ) : (
              pageRules.map(rule => {
                const typeColor = errorTypeColors[rule.error_type] || { bg: 'var(--bg-secondary)', color: 'var(--text-muted)' }
                return (
                  <tr 
                    key={rule.id} 
                    className="hover-row"
                    style={{ borderBottom: '1px solid var(--border)', transition: 'background 0.2s' }}
                  >
                    <td style={{ padding: '20px 24px' }}>
                      <span style={{ 
                        fontFamily: 'monospace', fontSize: '0.9rem', padding: '4px 10px',
                        background: 'var(--danger-bg)', color: 'var(--danger)',
                        borderRadius: 'var(--radius-sm)', border: '1px solid rgba(196, 77, 77, 0.15)'
                      }}>
                        {rule.wrong_form}
                      </span>
                    </td>
                    <td style={{ padding: '20px 24px' }}>
                      <span style={{ 
                        fontFamily: 'monospace', fontSize: '0.9rem', padding: '4px 10px',
                        background: 'var(--success-bg)', color: 'var(--success)',
                        borderRadius: 'var(--radius-sm)', border: '1px solid rgba(59, 155, 110, 0.15)'
                      }}>
                        {rule.correct_form}
                      </span>
                    </td>
                    <td style={{ padding: '20px 24px' }}>
                      <span style={{ 
                        padding: '4px 12px', borderRadius: '20px', fontSize: '0.75rem',
                        fontWeight: 700, textTransform: 'uppercase',
                        background: typeColor.bg, color: typeColor.color
                      }}>
                        {rule.error_type}
                      </span>
                    </td>
                    <td style={{ padding: '20px 24px', textAlign: 'center' }}>
                      <span style={{ 
                        fontWeight: 800, fontSize: '0.9rem', color: 'var(--accent-primary)',
                        background: 'var(--accent-bg)', padding: '4px 12px', borderRadius: '8px'
                      }}>
                        {rule.frequency}
                      </span>
                    </td>
                    <td style={{ padding: '20px 24px' }}>
                      <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                        {rule.modified_by || '—'}
                      </span>
                    </td>
                    <td style={{ padding: '20px 24px', textAlign: 'right' }}>
                      <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                        <button 
                          onClick={() => setEditingRule(rule)}
                          style={{ padding: '8px', borderRadius: '8px', background: 'var(--accent-bg)', color: 'var(--accent-primary)', border: 'none', cursor: 'pointer' }}
                        >
                          <Edit2 size={16} />
                        </button>
                        <button 
                          onClick={() => handleDelete(rule.id)}
                          style={{ padding: '8px', borderRadius: '8px', background: 'var(--danger-bg)', color: 'var(--danger)', border: 'none', cursor: 'pointer' }}
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '20px', padding: '16px 20px', background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)', fontWeight: 600 }}>Саҳифада:</span>
            {[25, 50].map(n => (
              <button key={n} onClick={() => { setPerPage(n); setPage(0) }} style={{
                padding: '6px 14px', borderRadius: '8px',
                border: perPage === n ? '2px solid var(--accent-primary)' : '1px solid var(--border)',
                background: perPage === n ? 'var(--accent-bg)' : 'white',
                color: perPage === n ? 'var(--accent-primary)' : 'var(--text-muted)',
                fontWeight: 700, fontSize: '0.82rem', cursor: 'pointer'
              }}>{n}</button>
            ))}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button disabled={page === 0} onClick={() => setPage(p => p - 1)} style={{
              padding: '8px 16px', borderRadius: '8px', border: '1px solid var(--border)',
              background: page === 0 ? '#F1F5F9' : 'white', cursor: page === 0 ? 'default' : 'pointer',
              fontWeight: 700, fontSize: '0.82rem', color: page === 0 ? '#94A3B8' : 'var(--text-primary)'
            }}>← Олдинги</button>
            <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-muted)', padding: '0 12px' }}>
              {page + 1} / {totalPages} ({filteredRules.length} та қоида)
            </span>
            <button disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)} style={{
              padding: '8px 16px', borderRadius: '8px', border: '1px solid var(--border)',
              background: page >= totalPages - 1 ? '#F1F5F9' : 'white', cursor: page >= totalPages - 1 ? 'default' : 'pointer',
              fontWeight: 700, fontSize: '0.82rem', color: page >= totalPages - 1 ? '#94A3B8' : 'var(--text-primary)'
            }}>Кейинги →</button>
          </div>
        </div>
      )}

      {/* Edit/Add Modal */}
      {editingRule && (
        <div style={{ 
          position: 'fixed', top: 0, left: 0, width: '100%', height: '100%',
          background: 'rgba(61, 43, 31, 0.4)', backdropFilter: 'blur(8px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
        }}>
          <div style={{ 
            background: 'var(--bg-card)', borderRadius: 'var(--radius-xl)',
            width: '100%', maxWidth: '520px', boxShadow: 'var(--shadow-lg)',
            border: '1px solid var(--border)', overflow: 'hidden'
          }}>
            {/* Modal Header */}
            <div style={{ 
              padding: '24px 32px', borderBottom: '1px solid var(--border)',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center'
            }}>
              <h2 style={{ fontSize: '1.2rem', fontWeight: 800 }}>
                {editingRule.id ? 'Qoidani tahrirlash' : 'Yangi qoida qo\'shish'}
              </h2>
              <div style={{ 
                display: 'flex', alignItems: 'center', gap: '8px', 
                fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)',
                textTransform: 'uppercase', letterSpacing: '1px',
                background: 'var(--bg-secondary)', padding: '6px 12px', borderRadius: '20px'
              }}>
                <Languages size={12} />
                {lang === 'uz' ? "O'zbekcha" : 'Русский'}
              </div>
            </div>

            {/* Modal Body */}
            <div style={{ padding: '32px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div>
                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '8px' }}>
                  <AlertCircle size={14} color="var(--danger)" /> Хато шакли
                </label>
                <input 
                  type="text" value={editingRule.wrong_form || ''}
                  onChange={e => setEditingRule({ ...editingRule, wrong_form: e.target.value })}
                  placeholder="мас: аниқлик"
                  style={{ 
                    width: '100%', padding: '12px 16px', borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border)', background: 'var(--bg-primary)',
                    fontFamily: 'monospace', fontSize: '0.95rem', outline: 'none'
                  }}
                />
              </div>
              <div>
                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '8px' }}>
                  <CheckCircle2 size={14} color="var(--success)" /> Тўғри шакли
                </label>
                <input 
                  type="text" value={editingRule.correct_form || ''}
                  onChange={e => setEditingRule({ ...editingRule, correct_form: e.target.value })}
                  placeholder="мас: аниқлиги"
                  style={{ 
                    width: '100%', padding: '12px 16px', borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border)', background: 'var(--bg-primary)',
                    fontFamily: 'monospace', fontSize: '0.95rem', outline: 'none'
                  }}
                />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                <div>
                  <label style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '8px', display: 'block' }}>Хато тури</label>
                  <select 
                    value={editingRule.error_type || 'S/Spelling'}
                    onChange={e => setEditingRule({ ...editingRule, error_type: e.target.value })}
                    style={{ 
                      width: '100%', padding: '12px 16px', borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--border)', background: 'var(--bg-primary)',
                      fontSize: '0.9rem', outline: 'none'
                    }}
                  >
                    <option value="S/Spelling">Spelling</option>
                    <option value="S/Context">Context</option>
                    <option value="G/Grammar">Grammar</option>
                    <option value="Terminology">Terminology</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '8px', display: 'block' }}>Частота</label>
                  <input 
                    type="number" value={editingRule.frequency || 1}
                    onChange={e => setEditingRule({ ...editingRule, frequency: parseInt(e.target.value) })}
                    style={{ 
                      width: '100%', padding: '12px 16px', borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--border)', background: 'var(--bg-primary)',
                      fontSize: '0.9rem', outline: 'none'
                    }}
                  />
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div style={{ 
              padding: '20px 32px', borderTop: '1px solid var(--border)',
              background: 'var(--bg-secondary)', display: 'flex', justifyContent: 'flex-end', gap: '12px'
            }}>
              <button 
                onClick={() => setEditingRule(null)}
                style={{ 
                  padding: '10px 24px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)',
                  background: 'white', fontWeight: 700, fontSize: '0.85rem', cursor: 'pointer', color: 'var(--text-secondary)'
                }}
              >
                Bekor qilish
              </button>
              <button 
                onClick={handleSave}
                style={{ 
                  padding: '10px 24px', borderRadius: 'var(--radius-md)', border: 'none',
                  background: 'var(--accent-gradient)', color: 'white',
                  fontWeight: 700, fontSize: '0.85rem', cursor: 'pointer', boxShadow: 'var(--shadow-glow)'
                }}
              >
                Saqlash
              </button>
            </div>
          </div>
        </div>
      )}

      <style jsx global>{`
        .hover-row:hover { background-color: var(--bg-secondary) !important; }
      `}</style>
    </div>
  )
}
