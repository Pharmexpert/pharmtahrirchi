'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { Search, Plus, Edit2, Trash2, Download, CheckCircle2, AlertCircle, Loader2, X, Save } from 'lucide-react'
import { useAuth } from '../../../components/LoginGuard'
import { useParams } from 'next/navigation'
import * as XLSX from 'xlsx'

type Category = 'annotated' | 'disputed' | 'abbreviations'

interface LingItem {
  id: number
  en?: string; ru?: string; uz?: string
  short_form?: string; long_en?: string; long_ru?: string; long_uz?: string
  description_en?: string; description_ru?: string; description_uz?: string
  context_en?: string; context_ru?: string; context_uz?: string
  text_id?: string
  user_name?: string; modified_by_name?: string
  created_at?: string; modified_at?: string
  status?: string
}

const CATEGORY_META: Record<Category, { title: string; emoji: string; color: string; bg: string }> = {
  annotated:     { title: 'Изоҳли луғат',          emoji: '📖', color: '#5B7FDE', bg: '#F0F4FF' },
  disputed:      { title: 'Мунозарали терминлар',  emoji: '⚖️', color: '#D47B3F', bg: '#FFF4EE' },
  abbreviations: { title: 'Қисқартмалар архиви',    emoji: '✂️', color: '#9B3B9B', bg: '#FDF0FF' },
}

function getFields(cat: Category, item: Partial<LingItem>) {
  if (cat === 'abbreviations') return [
    { key: 'short_form', label: 'Қисқартма', placeholder: 'GMP', fullWidth: true },
    { key: 'long_en',    label: 'Тўлиқ (EN)', placeholder: 'Good Manufacturing Practice' },
    { key: 'long_ru',    label: 'Тўлиқ (RU)', placeholder: 'Надлежащая производственная практика' },
    { key: 'long_uz',    label: 'Тўлиқ (UZ)', placeholder: 'Yaxshi ishlab chiqarish amaliyoti' },
  ]
  if (cat === 'disputed') return [
    { key: 'en', label: 'EN термин', placeholder: 'container' },
    { key: 'ru', label: 'RU термин', placeholder: 'контейнер / ёмкость' },
    { key: 'uz', label: 'UZ термин', placeholder: 'idish / qadoq' },
    { key: 'context_en', label: 'Контекст (EN)', placeholder: 'Used when referring to...' },
    { key: 'context_ru', label: 'Контекст (RU)', placeholder: 'Используется когда...' },
    { key: 'context_uz', label: 'Kontekst (UZ)', placeholder: 'Qo\'llanilganda...' },
  ]
  return [
    { key: 'en', label: 'Термин (EN)', placeholder: 'bioavailability' },
    { key: 'ru', label: 'Термин (RU)', placeholder: 'биодоступность' },
    { key: 'uz', label: 'Термин (UZ)', placeholder: 'biodostuplik' },
    { key: 'description_en', label: 'Таъриф (EN)', placeholder: 'The fraction of...' },
    { key: 'description_ru', label: 'Таъриф (RU)', placeholder: 'Доля вещества...' },
    { key: 'description_uz', label: 'Tavsif (UZ)', placeholder: 'Moddaning ulushi...' },
  ]
}

function getDisplayName(item: LingItem, cat: Category) {
  if (cat === 'abbreviations') return item.short_form || '—'
  return item.en || '—'
}

function getSubName(item: LingItem, cat: Category) {
  if (cat === 'abbreviations') return item.long_en || ''
  if (cat === 'disputed') return item.context_en || item.ru || ''
  return item.description_en || item.ru || ''
}

export default function LinguisticCategoryPage() {
  const params = useParams()
  const category = (params?.category as Category) || 'annotated'
  const meta = CATEGORY_META[category] || CATEGORY_META.annotated

  const { token, user } = useAuth()
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const [items, setItems] = useState<LingItem[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [textIdFilter, setTextIdFilter] = useState('')
  const [userFilter, setUserFilter] = useState('')
  const [editItem, setEditItem] = useState<Partial<LingItem> | null>(null)
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null)

  const showToast = (msg: string, type: 'success' | 'error' = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3000)
  }

  const fetchItems = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/linguistic/all`)
      if (res.ok) {
        const data = await res.json()
        const key = category === 'annotated' ? 'annotated' : category === 'disputed' ? 'disputed' : 'abbreviations'
        setItems(data[key] || [])
      }
    } finally { setLoading(false) }
  }, [category, API_BASE])

  useEffect(() => { fetchItems() }, [fetchItems])

  const handleSave = async () => {
    if (!editItem || !token) return
    setSaving(true)
    try {
      let res: Response
      if (editItem.id) {
        res = await fetch(`${API_BASE}/api/linguistic/update/${category}/${editItem.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify(editItem)
        })
      } else {
        res = await fetch(`${API_BASE}/api/linguistic/save`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ category, items: [editItem] })
        })
      }
      if (res.ok) {
        showToast(editItem.id ? 'Янгиланди ✓' : 'Қўшилди ✓')
        setEditItem(null)
        fetchItems()
      } else { showToast('Хатолик юз берди', 'error') }
    } finally { setSaving(false) }
  }

  const handleDelete = async (id: number) => {
    if (!token || !confirm('Ўчиришни тасдиқлайсизми?')) return
    try {
      const res = await fetch(`${API_BASE}/api/linguistic/delete/${category}/${id}`, {
        method: 'DELETE', headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        setItems(prev => prev.filter(x => x.id !== id))
        showToast('Ўчирилди')
      }
    } catch (e) { showToast('Хатолик', 'error') }
  }

  const handleExportXLSX = () => {
    const rows = filtered.map((item, i) => {
      const base: any = { '№': i + 1, 'Матн рақами': item.text_id || '' }
      if (category === 'abbreviations') {
        return { ...base, 'Қисқартма': item.short_form, 'EN': item.long_en, 'RU': item.long_ru, 'UZ': item.long_uz }
      }
      if (category === 'disputed') {
        return { ...base, 'EN': item.en, 'RU': item.ru, 'UZ': item.uz, 'Контекст EN': item.context_en, 'Контекст RU': item.context_ru, 'Kontekst UZ': item.context_uz }
      }
      return { ...base, 'EN': item.en, 'RU': item.ru, 'UZ': item.uz, 'Таъриф EN': item.description_en, 'Таъриф RU': item.description_ru, 'Tavsif UZ': item.description_uz }
    })
    const ws = XLSX.utils.json_to_sheet(rows)
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, meta.title)
    XLSX.writeFile(wb, `${category}_${new Date().toISOString().slice(0, 10)}.xlsx`)
  }

  const filtered = items.filter(item => {
    const q = search.toLowerCase()
    const matchSearch = !q ||
      (item.en || item.short_form || '').toLowerCase().includes(q) ||
      (item.ru || item.long_ru || '').toLowerCase().includes(q) ||
      (item.uz || item.long_uz || '').toLowerCase().includes(q)
    const matchTextId = !textIdFilter || (item.text_id || '').toLowerCase().includes(textIdFilter.toLowerCase())
    const matchUser = !userFilter || (item.user_name || '').toLowerCase().includes(userFilter.toLowerCase()) ||
      (item.modified_by_name || '').toLowerCase().includes(userFilter.toLowerCase())
    return matchSearch && matchTextId && matchUser
  })

  const fields = getFields(category, editItem || {})

  return (
    <div>
      {/* Toast */}
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
      <div style={{ marginBottom: '28px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h1 style={{ fontSize: '2rem', fontWeight: 800, marginBottom: '6px' }}>
            {meta.emoji} {meta.title}
          </h1>
          <p style={{ color: 'var(--text-muted)' }}>{filtered.length} та ёзув</p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button onClick={handleExportXLSX} style={{
            padding: '10px 18px', borderRadius: '10px', border: '1.5px solid #16A34A',
            background: '#F0FDF4', color: '#16A34A', fontWeight: 700, cursor: 'pointer',
            display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem'
          }}>
            <Download size={15} /> XLSX
          </button>
          <button onClick={() => setEditItem({})} style={{
            padding: '10px 18px', borderRadius: '10px', border: 'none',
            background: meta.color, color: 'white', fontWeight: 700, cursor: 'pointer',
            display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem'
          }}>
            <Plus size={15} /> Янги
          </button>
        </div>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '24px', flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', flex: 2, minWidth: '200px' }}>
          <Search size={15} style={{ position: 'absolute', left: '13px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input placeholder="Терминни қидириш..." value={search} onChange={e => setSearch(e.target.value)}
            style={{ width: '100%', padding: '11px 11px 11px 40px', borderRadius: '10px', border: '1px solid var(--border)', background: 'var(--bg-card)', outline: 'none', fontSize: '0.9rem', boxSizing: 'border-box' }} />
        </div>
        <input placeholder="Матн рақами..." value={textIdFilter} onChange={e => setTextIdFilter(e.target.value)}
          style={{ flex: 1, minWidth: '140px', padding: '11px 14px', borderRadius: '10px', border: '1px solid var(--border)', background: 'var(--bg-card)', outline: 'none', fontSize: '0.9rem' }} />
        <input placeholder="Мутахассис..." value={userFilter} onChange={e => setUserFilter(e.target.value)}
          style={{ flex: 1, minWidth: '140px', padding: '11px 14px', borderRadius: '10px', border: '1px solid var(--border)', background: 'var(--bg-card)', outline: 'none', fontSize: '0.9rem' }} />
      </div>

      {/* Table */}
      <div style={{ background: 'var(--bg-card)', borderRadius: '16px', border: '1px solid var(--border)', overflow: 'hidden', boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: 'var(--bg-secondary)', borderBottom: '2px solid var(--border)' }}>
              <th style={{ padding: '14px 16px', textAlign: 'left', fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', width: '40px' }}>№</th>
              <th style={{ padding: '14px 16px', textAlign: 'left', fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Термин</th>
              <th style={{ padding: '14px 16px', textAlign: 'left', fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Матн №</th>
              <th style={{ padding: '14px 16px', textAlign: 'left', fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Мутахассис</th>
              <th style={{ padding: '14px 16px', textAlign: 'left', fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Сана</th>
              <th style={{ padding: '14px 16px', textAlign: 'right', fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Амал</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
                <Loader2 size={28} style={{ animation: 'spin 1s linear infinite', marginBottom: 12 }} />
                <p>Юкланмоқда...</p>
              </td></tr>
            ) : filtered.length === 0 ? (
              <tr><td colSpan={6} style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
                <div style={{ fontSize: '3rem', marginBottom: 12 }}>{meta.emoji}</div>
                <p style={{ fontWeight: 600 }}>Ёзувлар топилмади</p>
                <p style={{ fontSize: '0.85rem', marginTop: 8 }}>Янги термин қўшиш учун «Янги» тугмасини босинг</p>
              </td></tr>
            ) : filtered.map((item, i) => (
              <tr key={item.id} style={{ borderBottom: '1px solid var(--border)', transition: 'background 0.15s' }}
                onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = 'var(--bg-secondary)'}
                onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = ''}>
                <td style={{ padding: '14px 16px', color: 'var(--text-muted)', fontWeight: 600, fontSize: '0.85rem' }}>{i + 1}</td>
                <td style={{ padding: '14px 16px' }}>
                  <div style={{ fontWeight: 700 }}>{getDisplayName(item, category)}</div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '2px' }}>{getSubName(item, category)}</div>
                </td>
                <td style={{ padding: '14px 16px' }}>
                  {item.text_id ? (
                    <span style={{ fontFamily: 'monospace', fontSize: '0.82rem', padding: '2px 8px', background: 'var(--accent-bg)', color: 'var(--accent-primary)', borderRadius: '6px', fontWeight: 700 }}>
                      {item.text_id}
                    </span>
                  ) : <span style={{ color: 'var(--text-muted)' }}>—</span>}
                </td>
                <td style={{ padding: '14px 16px' }}>
                  <div style={{ fontSize: '0.85rem' }}>
                    <span style={{ color: '#16A34A', fontWeight: 600 }}>● {item.user_name || '—'}</span>
                    {item.modified_by_name && item.modified_by_name !== item.user_name && (
                      <div style={{ color: '#D97706', fontSize: '0.78rem', marginTop: '2px' }}>✎ {item.modified_by_name}</div>
                    )}
                  </div>
                </td>
                <td style={{ padding: '14px 16px', color: 'var(--text-muted)', fontSize: '0.82rem' }}>
                  {item.created_at ? new Date(item.created_at).toLocaleDateString('uz-UZ') : '—'}
                  {item.modified_at && (<div style={{ fontSize: '0.75rem', color: '#D97706' }}>✎ {new Date(item.modified_at).toLocaleDateString('uz-UZ')}</div>)}
                </td>
                <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                  <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                    <button onClick={() => setEditItem({ ...item })} style={{
                      padding: '7px', borderRadius: '8px', border: 'none',
                      background: meta.bg, color: meta.color, cursor: 'pointer'
                    }}><Edit2 size={14} /></button>
                    <button onClick={() => handleDelete(item.id)} style={{
                      padding: '7px', borderRadius: '8px', border: 'none',
                      background: 'var(--danger-bg)', color: 'var(--danger)', cursor: 'pointer'
                    }}><Trash2 size={14} /></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Edit Modal */}
      {editItem !== null && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', backdropFilter: 'blur(6px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '20px'
        }}>
          <div style={{
            background: 'var(--bg-card)', borderRadius: '20px', width: '100%', maxWidth: '640px',
            boxShadow: '0 24px 64px rgba(0,0,0,0.2)', overflow: 'hidden', maxHeight: '90vh', display: 'flex', flexDirection: 'column'
          }}>
            {/* Modal Header */}
            <div style={{ padding: '24px 28px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h2 style={{ fontWeight: 800, fontSize: '1.1rem' }}>
                {editItem.id ? 'Таҳрирлаш' : 'Янги ёзув'} — {meta.title}
              </h2>
              <button onClick={() => setEditItem(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
                <X size={20} />
              </button>
            </div>
            {/* Modal Body */}
            <div style={{ padding: '24px 28px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {fields.map(f => (
                <div key={f.key}>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    {f.label}
                  </label>
                  <textarea
                    value={(editItem as any)[f.key] || ''}
                    onChange={e => setEditItem(prev => ({ ...prev, [f.key]: e.target.value }))}
                    placeholder={f.placeholder} rows={2}
                    style={{
                      width: '100%', padding: '10px 14px', borderRadius: '10px',
                      border: '1.5px solid var(--border)', background: 'var(--bg-primary)',
                      fontSize: '0.9rem', outline: 'none', resize: 'vertical',
                      fontFamily: 'inherit', boxSizing: 'border-box'
                    }}
                    onFocus={e => e.target.style.borderColor = meta.color}
                    onBlur={e => e.target.style.borderColor = 'var(--border)'}
                  />
                </div>
              ))}
            </div>
            {/* Modal Footer */}
            <div style={{ padding: '16px 28px', borderTop: '1px solid var(--border)', background: 'var(--bg-secondary)', display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button onClick={() => setEditItem(null)} style={{ padding: '10px 22px', borderRadius: '10px', border: '1px solid var(--border)', background: 'white', fontWeight: 700, cursor: 'pointer' }}>
                Bekor
              </button>
              <button onClick={handleSave} disabled={saving} style={{
                padding: '10px 22px', borderRadius: '10px', border: 'none',
                background: meta.color, color: 'white', fontWeight: 700, cursor: saving ? 'not-allowed' : 'pointer',
                display: 'flex', alignItems: 'center', gap: '6px', opacity: saving ? 0.7 : 1
              }}>
                {saving ? <Loader2 size={15} style={{ animation: 'spin 1s linear infinite' }} /> : <Save size={15} />}
                Saqlash
              </button>
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
