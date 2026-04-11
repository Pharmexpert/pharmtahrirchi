'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { Database, BookOpen, Languages, Layers, FileText, Shield, Search, Plus, Edit2, Trash2, Save, X, Loader2, Download } from 'lucide-react'
import { useAuth } from '../../../components/LoginGuard'
import api from '../../../services/api'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

type Tab = 'sayqallash' | 'hunspell' | 'grammar' | 'morph' | 'syntax' | 'style' | 'tahrirchi'

const TABS: Array<{ key: Tab; label: string; icon: React.ReactNode; color: string; desc: string }> = [
  { key: 'sayqallash', label: 'Сайқаллаш', icon: <Shield size={16} />, color: '#DC2626', desc: 'Имло қоидалари (хато→тўғри жуфтлар)' },
  { key: 'hunspell', label: 'Hunspell', icon: <BookOpen size={16} />, color: '#EA580C', desc: 'Имло луғати (96K сўз + аффикслар)' },
  { key: 'grammar', label: 'Грамматика', icon: <Languages size={16} />, color: '#16A34A', desc: 'Грамматик қоидалар' },
  { key: 'morph', label: 'Морфология', icon: <Layers size={16} />, color: '#0891B2', desc: 'Сўз таркиби (ўзак, қўшимча, POS)' },
  { key: 'syntax', label: 'Синтаксис', icon: <Layers size={16} />, color: '#7C3AED', desc: 'Гап тузилиши шаблонлари' },
  { key: 'style', label: 'Стиль', icon: <FileText size={16} />, color: '#DB2777', desc: 'USP/ICH/WHO стил қоидалари' },
  { key: 'tahrirchi', label: 'Таҳрирчи', icon: <Database size={16} />, color: '#6366F1', desc: '8.7M сўзлик (FAISS индекс)' },
]

export default function LanguageResourcesPage() {
  const { token, user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const [tab, setTab] = useState<Tab>('sayqallash')
  const [search, setSearch] = useState('')
  const [items, setItems] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [editItem, setEditItem] = useState<any>(null)
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null)

  const showToast = (msg: string, type: 'success' | 'error' = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3000)
  }

  const fetchData = useCallback(async () => {
    if (!token) return
    setLoading(true)
    try {
      const h = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
      let url = ''
      if (tab === 'sayqallash') {
        url = `${API_BASE}/api/admin/rules?page=${page}&per_page=50&lang=uz${search ? `&search=${encodeURIComponent(search)}` : ''}`
      } else if (tab === 'style') {
        url = `${API_BASE}/api/admin/style-guide?page=${page}&per_page=50${search ? `&search=${encodeURIComponent(search)}` : ''}`
      } else if (tab === 'hunspell') {
        url = `${API_BASE}/api/dictionary/words?page=${page}&per_page=50&language=cyrl${search ? `&search=${encodeURIComponent(search)}` : ''}`
      } else {
        url = `${API_BASE}/api/tilshunos/rules/stats`
      }
      const res = await fetch(url, { headers: h })
      const d = await res.json()
      if (tab === 'sayqallash') {
        setItems(d.rules || [])
        setTotal(d.total || 0)
      } else if (tab === 'style') {
        setItems(d.rules || d.items || [])
        setTotal(d.total || 0)
      } else if (tab === 'hunspell') {
        setItems((d.words || []).map((w: any) => ({ word: typeof w === 'string' ? w : w.word, frequency: typeof w === 'object' ? w.frequency : 0 })))
        setTotal(d.total || 0)
      } else {
        // Stats view for morph/syntax/grammar/tahrirchi
        setItems([d])
        setTotal(1)
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [token, tab, page, search])

  useEffect(() => { fetchData() }, [fetchData])
  useEffect(() => { setPage(0); setItems([]) }, [tab])

  if (!isAdmin) {
    return (
      <div style={{ padding: 40, textAlign: 'center' }}>
        <Shield size={48} color="#DC2626" />
        <h2>Фақат админ учун</h2>
        <p>Бу саҳифага фақат админ кира олади</p>
      </div>
    )
  }

  const currentTab = TABS.find(t => t.key === tab)!

  return (
    <div style={{ padding: '20px 24px' }}>
      <div style={{ marginBottom: 16 }}>
        <h1 style={{ fontSize: '1.3rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: 8, margin: 0 }}>
          <Database size={24} color="#7C3AED" /> Она тилини бойитиш
        </h1>
        <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', margin: '4px 0 0' }}>
          7 та лингвистик база бошқаруви — қоидалар қўшиш, таҳрирлаш, ўчириш
        </p>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 16, background: '#F1F5F9', padding: 4, borderRadius: 12 }}>
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            style={{
              padding: '8px 14px', borderRadius: 8, border: 'none',
              background: tab === t.key ? 'white' : 'transparent',
              color: tab === t.key ? t.color : '#64748B',
              fontWeight: tab === t.key ? 800 : 600,
              fontSize: '0.78rem', cursor: 'pointer',
              boxShadow: tab === t.key ? '0 2px 8px rgba(0,0,0,0.1)' : 'none',
              display: 'flex', alignItems: 'center', gap: 4,
              transition: 'all .15s',
            }}>
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* Header + Search */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12, flexWrap: 'wrap', gap: 8 }}>
        <div>
          <span style={{ fontSize: '1rem', fontWeight: 700, color: currentTab.color }}>{currentTab.label}</span>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginLeft: 8 }}>{currentTab.desc}</span>
          <span style={{ fontSize: '0.72rem', fontWeight: 700, color: currentTab.color, marginLeft: 8 }}>({total})</span>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <div style={{ position: 'relative' }}>
            <Search size={14} style={{ position: 'absolute', left: 8, top: 9, color: '#94A3B8' }} />
            <input value={search} onChange={e => { setSearch(e.target.value); setPage(0) }}
              placeholder="Қидириш..."
              style={{ padding: '7px 10px 7px 28px', borderRadius: 8, border: '1.5px solid var(--border)', fontSize: '0.82rem', width: 200 }}
            />
          </div>
          {(tab === 'sayqallash' || tab === 'style') && (
            <button onClick={() => setEditItem({ wrong_form: '', correct_form: '', error_type: 'S/Spelling', lang: 'uz' })}
              style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '7px 14px', borderRadius: 8, border: 'none', background: currentTab.color, color: 'white', fontWeight: 700, fontSize: '0.78rem', cursor: 'pointer' }}>
              <Plus size={14} /> Янги қўшиш
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: 40 }}><Loader2 size={24} className="animate-spin" /></div>
      ) : (
        <div style={{ background: 'var(--bg-card)', border: '1.5px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
          {tab === 'sayqallash' && (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
              <thead>
                <tr style={{ background: '#FEF2F2', borderBottom: '2px solid #FECACA' }}>
                  <th style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 700, color: '#991B1B' }}>№</th>
                  <th style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 700, color: '#991B1B' }}>Хато</th>
                  <th style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 700, color: '#15803D' }}>Тўғри</th>
                  <th style={{ padding: '10px 12px', textAlign: 'left' }}>Тур</th>
                  <th style={{ padding: '10px 12px', textAlign: 'left' }}>Частота</th>
                  <th style={{ padding: '10px 12px', textAlign: 'left' }}>Манба</th>
                  <th style={{ padding: '10px 12px', textAlign: 'right' }}>Амал</th>
                </tr>
              </thead>
              <tbody>
                {items.map((r: any, i: number) => (
                  <tr key={r.id || i} style={{ borderBottom: '1px solid var(--border)' }}
                    onMouseEnter={e => (e.currentTarget.style.background = '#FAFBFC')}
                    onMouseLeave={e => (e.currentTarget.style.background = '')}>
                    <td style={{ padding: '8px 12px', color: 'var(--text-muted)' }}>{page * 50 + i + 1}</td>
                    <td style={{ padding: '8px 12px', color: '#DC2626', fontWeight: 600 }}>{r.wrong_form}</td>
                    <td style={{ padding: '8px 12px', color: '#16A34A', fontWeight: 600 }}>{r.correct_form}</td>
                    <td style={{ padding: '8px 12px' }}>
                      <span style={{ padding: '2px 8px', borderRadius: 6, background: '#F5F3FF', color: '#7C3AED', fontSize: '0.7rem', fontWeight: 600 }}>{r.error_type}</span>
                    </td>
                    <td style={{ padding: '8px 12px', fontWeight: 600 }}>{r.frequency || 0}</td>
                    <td style={{ padding: '8px 12px', fontSize: '0.72rem', color: 'var(--text-muted)' }}>{r.source || '—'}</td>
                    <td style={{ padding: '8px 12px', textAlign: 'right' }}>
                      <button onClick={() => setEditItem(r)} style={{ padding: '3px 8px', borderRadius: 4, border: '1px solid var(--border)', background: 'white', cursor: 'pointer', marginRight: 4, fontSize: '0.7rem' }}>
                        <Edit2 size={12} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {tab === 'hunspell' && (
            <div style={{ padding: 16 }}>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {items.map((w: any, i: number) => (
                  <span key={i} style={{ padding: '4px 10px', borderRadius: 8, background: '#FFF7ED', border: '1px solid #FED7AA', fontSize: '0.82rem', fontWeight: 600, color: '#9A3412' }}>
                    {w.word} {w.frequency > 0 && <span style={{ fontSize: '0.6rem', opacity: 0.6 }}>{w.frequency}</span>}
                  </span>
                ))}
              </div>
            </div>
          )}

          {tab === 'style' && (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
              <thead>
                <tr style={{ background: '#FCE7F3', borderBottom: '2px solid #FBCFE8' }}>
                  <th style={{ padding: '10px 12px', textAlign: 'left' }}>Қоида ID</th>
                  <th style={{ padding: '10px 12px', textAlign: 'left' }}>Категория</th>
                  <th style={{ padding: '10px 12px', textAlign: 'left' }}>Тавсиф</th>
                  <th style={{ padding: '10px 12px', textAlign: 'left' }}>Pattern</th>
                  <th style={{ padding: '10px 12px', textAlign: 'left' }}>Таклиф</th>
                </tr>
              </thead>
              <tbody>
                {items.map((r: any, i: number) => (
                  <tr key={r.id || i} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td style={{ padding: '8px 12px', fontFamily: 'monospace', fontSize: '0.72rem' }}>{r.rule_id}</td>
                    <td style={{ padding: '8px 12px' }}>{r.category}</td>
                    <td style={{ padding: '8px 12px' }}>{r.description}</td>
                    <td style={{ padding: '8px 12px', fontFamily: 'monospace', fontSize: '0.72rem', color: '#7C3AED' }}>{r.pattern}</td>
                    <td style={{ padding: '8px 12px', color: '#16A34A', fontWeight: 600 }}>{r.suggestion}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {/* Stats view for morph/syntax/grammar/tahrirchi */}
          {(tab === 'morph' || tab === 'syntax' || tab === 'grammar' || tab === 'tahrirchi') && items[0] && (
            <div style={{ padding: 20 }}>
              <pre style={{ fontSize: '0.82rem', lineHeight: 1.6, whiteSpace: 'pre-wrap', background: '#F8FAFC', padding: 16, borderRadius: 8 }}>
                {JSON.stringify(items[0], null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Pagination */}
      {total > 50 && (
        <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 12 }}>
          <button disabled={page === 0} onClick={() => setPage(p => p - 1)}
            style={{ padding: '6px 14px', borderRadius: 8, border: '1px solid var(--border)', cursor: page === 0 ? 'default' : 'pointer', opacity: page === 0 ? 0.5 : 1 }}>← Олдинги</button>
          <span style={{ padding: '6px 14px', fontSize: '0.82rem', fontWeight: 700 }}>{page + 1} / {Math.ceil(total / 50)}</span>
          <button disabled={(page + 1) * 50 >= total} onClick={() => setPage(p => p + 1)}
            style={{ padding: '6px 14px', borderRadius: 8, border: '1px solid var(--border)', cursor: (page + 1) * 50 >= total ? 'default' : 'pointer' }}>Кейинги →</button>
        </div>
      )}

      {/* Edit Modal */}
      {editItem && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: 'white', borderRadius: 16, padding: 24, width: '100%', maxWidth: 480, boxShadow: '0 24px 64px rgba(0,0,0,0.25)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h3 style={{ fontWeight: 800, margin: 0 }}>{editItem.id ? 'Таҳрирлаш' : 'Янги қўшиш'}</h3>
              <button onClick={() => setEditItem(null)} style={{ background: 'none', border: 'none', cursor: 'pointer' }}><X size={20} /></button>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <input placeholder="Хато шакл..." value={editItem.wrong_form || ''} onChange={e => setEditItem({ ...editItem, wrong_form: e.target.value })}
                style={{ padding: 10, borderRadius: 8, border: '1.5px solid var(--border)', fontSize: '0.9rem' }} />
              <input placeholder="Тўғри шакл..." value={editItem.correct_form || ''} onChange={e => setEditItem({ ...editItem, correct_form: e.target.value })}
                style={{ padding: 10, borderRadius: 8, border: '1.5px solid var(--border)', fontSize: '0.9rem' }} />
              <select value={editItem.error_type || 'S/Spelling'} onChange={e => setEditItem({ ...editItem, error_type: e.target.value })}
                style={{ padding: 10, borderRadius: 8, border: '1.5px solid var(--border)', fontSize: '0.9rem' }}>
                <option value="S/Spelling">S/Spelling</option>
                <option value="S/Missing">S/Missing</option>
                <option value="S/Vowel">S/Vowel</option>
                <option value="S/Consonant">S/Consonant</option>
                <option value="S/HvsX">S/HvsX (ҳ↔х)</option>
                <option value="G/Grammar">G/Grammar</option>
                <option value="T/Terminology">T/Terminology</option>
                <option value="P/Punctuation">P/Punctuation</option>
              </select>
              <button onClick={async () => {
                try {
                  await api.sayqallash.learnBatch([{
                    old_value: editItem.wrong_form,
                    new_value: editItem.correct_form,
                    error_type: editItem.error_type,
                  }], 'uz')
                  showToast('Сақланди ✅')
                  setEditItem(null)
                  fetchData()
                } catch { showToast('Хатолик', 'error') }
              }} style={{ padding: 12, borderRadius: 10, border: 'none', background: currentTab.color, color: 'white', fontWeight: 800, fontSize: '0.9rem', cursor: 'pointer' }}>
                <Save size={16} style={{ display: 'inline', verticalAlign: -2, marginRight: 6 }} /> Сақлаш
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div style={{
          position: 'fixed', bottom: 20, right: 20, padding: '12px 20px', borderRadius: 10,
          background: toast.type === 'success' ? '#16A34A' : '#DC2626', color: 'white',
          fontWeight: 700, fontSize: '0.85rem', zIndex: 2000, boxShadow: '0 8px 24px rgba(0,0,0,0.2)',
        }}>{toast.msg}</div>
      )}
    </div>
  )
}
