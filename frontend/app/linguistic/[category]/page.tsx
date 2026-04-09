'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { Search, Plus, Edit2, Trash2, Download, CheckCircle2, AlertCircle, Loader2, X, Save, ArrowLeft, Copy, Filter } from 'lucide-react'
import { useAuth } from '../../../components/LoginGuard'
import { useParams, useRouter } from 'next/navigation'
import * as XLSX from 'xlsx'
import api from '../../../services/api'

type Category = 'annotated' | 'disputed' | 'abbreviations'
type StatusFilter = 'all' | 'new' | 'confirmed' | 'duplicates'

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
  is_duplicate?: boolean
}

const CATEGORY_META: Record<Category, { title: string; subtitle: string; icon: string; color: string; bg: string; headerBg: string; borderColor: string }> = {
  annotated: {
    title: 'Изоҳли луғат',
    subtitle: 'Фармацевтик терминлар ва уларнинг илмий таснифи',
    icon: '📖',
    color: '#5B7FDE',
    bg: '#F0F4FF',
    headerBg: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    borderColor: '#c7d2fe'
  },
  disputed: {
    title: 'Мунозарали терминлар',
    subtitle: 'Контекстга қараб турлича ишлатиладиган сўзлар',
    icon: '💬',
    color: '#E53E3E',
    bg: '#FFF5F5',
    headerBg: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
    borderColor: '#fed7d7'
  },
  abbreviations: {
    title: 'Қисқартмалар архиви',
    subtitle: 'Қисқартмалар ва тўлиқ номлари (GMP, USP, ICH...)',
    icon: '✂️',
    color: '#38A169',
    bg: '#F0FFF4',
    headerBg: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
    borderColor: '#c6f6d5'
  },
}

function getTableColumns(cat: Category) {
  if (cat === 'abbreviations') return [
    { key: 'short_form', label: 'ҚИСҚАРТМА', width: '10%' },
    { key: 'long_ru', label: 'РУССКИЙ', width: '18%' },
    { key: 'long_uz', label: 'ЎЗБЕКСНА', width: '18%' },
    { key: 'long_en', label: 'ENGLISH FULL NAME', width: '20%' },
  ]
  if (cat === 'disputed') return [
    { key: 'en', label: 'ENGLISH', width: '14%' },
    { key: 'ru', label: 'РУССКИЙ', width: '14%' },
    { key: 'uz', label: 'ЎЗБЕКСНА', width: '14%' },
    { key: 'context', label: 'КОНТЕКСТ', width: '24%' },
  ]
  return [
    { key: 'en', label: 'ENGLISH', width: '14%' },
    { key: 'ru', label: 'РУССКИЙ', width: '14%' },
    { key: 'uz', label: 'ЎЗБЕКСНА', width: '14%' },
    { key: 'description', label: 'ТАЪРИФ', width: '24%' },
  ]
}

function getEditFields(cat: Category) {
  if (cat === 'abbreviations') return [
    { key: 'short_form', label: 'Қисқартма', placeholder: 'GMP' },
    { key: 'long_ru', label: 'Русский', placeholder: 'Надлежащая производственная практика' },
    { key: 'long_uz', label: 'Ўзбексна', placeholder: 'Yaxshi ishlab chiqarish amaliyoti' },
    { key: 'long_en', label: 'English Full Name', placeholder: 'Good Manufacturing Practice' },
  ]
  if (cat === 'disputed') return [
    { key: 'en', label: 'English', placeholder: 'container' },
    { key: 'ru', label: 'Русский', placeholder: 'контейнер/упаковка' },
    { key: 'uz', label: 'Ўзбексна', placeholder: 'idish/konteyner' },
    { key: 'context_en', label: 'Контекст (EN)', placeholder: 'Used when referring to...' },
    { key: 'context_ru', label: 'Контекст (RU)', placeholder: 'Используется когда...' },
    { key: 'context_uz', label: 'Kontekst (UZ)', placeholder: "Qo'llanilganda..." },
  ]
  return [
    { key: 'en', label: 'English', placeholder: 'bioavailability' },
    { key: 'ru', label: 'Русский', placeholder: 'биодоступность' },
    { key: 'uz', label: 'Ўзбексна', placeholder: 'biodostuplik' },
    { key: 'description_en', label: 'Таъриф (EN)', placeholder: 'The fraction of...' },
    { key: 'description_ru', label: 'Таъриф (RU)', placeholder: 'Доля вещества...' },
    { key: 'description_uz', label: 'Tavsif (UZ)', placeholder: 'Moddaning ulushi...' },
  ]
}

function getCellValue(item: LingItem, key: string, cat: Category): string {
  if (key === 'context') {
    return (item as any).context_en || (item as any).context_ru || (item as any).context_uz || ''
  }
  if (key === 'description') {
    // Fallback order: EN → RU → UZ (many pharmacopoeia terms only have Uzbek definitions)
    return (item as any).description_en || (item as any).description_ru || (item as any).description_uz || ''
  }
  return (item as any)[key] || ''
}

function formatDate(d?: string) {
  if (!d) return '—'
  try {
    const dt = new Date(d)
    const yy = String(dt.getFullYear()).slice(2)
    const mm = String(dt.getMonth() + 1).padStart(2, '0')
    const dd = String(dt.getDate()).padStart(2, '0')
    return `${yy}-${mm}-${dd}`
  } catch { return '—' }
}

export default function LinguisticCategoryPage() {
  const params = useParams()
  const router = useRouter()
  const category = (params?.category as Category) || 'annotated'
  const meta = CATEGORY_META[category] || CATEGORY_META.annotated

  const { token, user } = useAuth()
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const [items, setItems] = useState<LingItem[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [textIdFilter, setTextIdFilter] = useState('')
  const [userFilter, setUserFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
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
      const data: any = await api.linguistic.all()
      setItems(data[category] || [])
    } finally { setLoading(false) }
  }, [category])

  useEffect(() => { fetchItems() }, [fetchItems])

  const handleSave = async () => {
    if (!editItem || !token) return
    setSaving(true)
    try {
      if (editItem.id) {
        await api.linguistic.update(category, editItem.id, editItem as any)
      } else {
        await api.linguistic.save({ category, items: [editItem] })
      }
      showToast(editItem.id ? 'Янгиланди ✓' : 'Қўшилди ✓')
      setEditItem(null)
      fetchItems()
    } catch { showToast('Хатолик юз берди', 'error') }
    finally { setSaving(false) }
  }

  const handleDelete = async (id: number) => {
    if (!token || !confirm('Ўчиришни тасдиқлайсизми?')) return
    try {
      await api.linguistic.remove(category, id)
      setItems(prev => prev.filter(x => x.id !== id))
      showToast('Ўчирилди')
    } catch { showToast('Хатолик', 'error') }
  }

  const handleExportXLSX = () => {
    const cols = getTableColumns(category)
    const rows = filtered.map((item, i) => {
      const base: any = { '№': i + 1 }
      cols.forEach(col => {
        base[col.label] = getCellValue(item, col.key, category)
      })
      base['МУТАХАССИС'] = item.user_name || '—'
      base['МАТН №'] = item.text_id || '—'
      base['САНА'] = formatDate(item.created_at)
      return base
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
    const matchUser = !userFilter || (item.user_name || '').toLowerCase().includes(userFilter.toLowerCase())
    const matchStatus = statusFilter === 'all' ? true :
      statusFilter === 'confirmed' ? item.status === 'confirmed' :
      statusFilter === 'duplicates' ? item.is_duplicate === true :
      statusFilter === 'new' ? (!item.status || item.status === 'active') : true
    return matchSearch && matchTextId && matchUser && matchStatus
  })

  const confirmedCount = items.filter(i => i.status === 'confirmed').length
  const duplicatesCount = items.filter(i => i.is_duplicate).length

  const columns = getTableColumns(category)
  const editFields = getEditFields(category)

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
        background: meta.bg, borderRadius: '20px', padding: '32px 36px',
        border: `1.5px solid ${meta.borderColor}`, marginBottom: '28px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        flexWrap: 'wrap', gap: '20px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <button onClick={() => router.back()} style={{
            width: 44, height: 44, borderRadius: '50%', border: `1.5px solid ${meta.borderColor}`,
            background: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: 'pointer', color: meta.color
          }}>
            <ArrowLeft size={20} />
          </button>
          <div style={{
            width: 52, height: 52, borderRadius: '14px', background: meta.headerBg,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '1.6rem', boxShadow: `0 4px 16px ${meta.color}30`
          }}>
            {meta.icon}
          </div>
          <div>
            <h1 style={{ fontSize: '1.7rem', fontWeight: 800, marginBottom: '4px', letterSpacing: '-0.5px' }}>
              {meta.title}
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: 0 }}>
              {meta.subtitle} — <strong>3</strong> тилда
            </p>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', margin: '2px 0 0' }}>
              Жами: <strong>{items.length}</strong> та • Кўрсатилган: <strong>{filtered.length}</strong>
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          {/* Status Filter Buttons */}
          {[
            { id: 'new' as StatusFilter, label: '🔄 Янгилаш', count: null },
            { id: 'all' as StatusFilter, label: 'Ҳаммаси', count: null },
            { id: 'confirmed' as StatusFilter, label: '✅ Тасдиқланган', count: confirmedCount },
            { id: 'duplicates' as StatusFilter, label: '⚠️ Дубликатлар', count: duplicatesCount },
          ].map(f => (
            <button key={f.id} onClick={() => {
              if (f.id === 'new') { fetchItems(); return }
              setStatusFilter(f.id)
            }}
              style={{
                padding: '8px 16px', borderRadius: '20px', border: '1.5px solid',
                borderColor: statusFilter === f.id ? meta.color : 'var(--border)',
                background: statusFilter === f.id ? meta.color : 'white',
                color: statusFilter === f.id ? 'white' : 'var(--text-secondary)',
                fontWeight: 700, fontSize: '0.8rem', cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: '4px',
                transition: 'all 0.15s'
              }}>
              {f.label}
            </button>
          ))}

          <button onClick={handleExportXLSX} style={{
            padding: '8px 16px', borderRadius: '10px', border: '1.5px solid #16A34A',
            background: '#F0FDF4', color: '#16A34A', fontWeight: 700, cursor: 'pointer',
            display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem'
          }}>
            <Download size={15} /> XLSX
          </button>

          <button onClick={() => setEditItem({})} style={{
            padding: '10px 22px', borderRadius: '12px', border: 'none',
            background: meta.headerBg, color: 'white', fontWeight: 800, cursor: 'pointer',
            display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem',
            boxShadow: `0 4px 16px ${meta.color}40`
          }}>
            <Plus size={16} /> ЯНГИ ҚЎШИШ
          </button>
        </div>
      </div>

      {/* Table with Column Filters */}
      <div style={{
        background: 'var(--bg-card)', borderRadius: '16px',
        border: '1px solid var(--border)', overflow: 'hidden',
        boxShadow: '0 2px 8px rgba(0,0,0,0.04)'
      }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            {/* Column Headers */}
            <tr style={{ background: 'var(--bg-secondary)', borderBottom: '2px solid var(--border)' }}>
              <th style={{ padding: '14px 16px', textAlign: 'left', fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', width: '40px' }}>№</th>
              {columns.map(col => (
                <th key={col.key} style={{ padding: '14px 16px', textAlign: 'left', fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', width: col.width }}>
                  {col.label}
                </th>
              ))}
              <th style={{ padding: '14px 16px', textAlign: 'left', fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', width: '14%' }}>МУТАХАССИС</th>
              <th style={{ padding: '14px 16px', textAlign: 'center', fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', width: '6%' }}>МАТН №</th>
              <th style={{ padding: '14px 16px', textAlign: 'left', fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', width: '8%' }}>САНА</th>
              <th style={{ padding: '14px 16px', textAlign: 'right', fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', width: '8%' }}>АМАЛ</th>
            </tr>
            {/* Filter Row */}
            <tr style={{ background: 'var(--bg-secondary)', borderBottom: '1px solid var(--border)' }}>
              <td style={{ padding: '6px 8px' }}></td>
              {columns.map((col, ci) => (
                <td key={col.key} style={{ padding: '6px 8px' }}>
                  {ci < 3 && (
                    <input placeholder="Қидириш..." value={ci === 0 ? search : ''}
                      onChange={e => ci === 0 && setSearch(e.target.value)}
                      style={{
                        width: '100%', padding: '6px 10px', borderRadius: '8px',
                        border: '1px solid var(--border)', background: 'white',
                        fontSize: '0.78rem', outline: 'none', boxSizing: 'border-box'
                      }} />
                  )}
                  {ci === 3 && (
                    <input placeholder="Филтр..." style={{
                      width: '100%', padding: '6px 10px', borderRadius: '8px',
                      border: '1px solid var(--border)', background: 'white',
                      fontSize: '0.78rem', outline: 'none', boxSizing: 'border-box'
                    }} />
                  )}
                </td>
              ))}
              <td style={{ padding: '6px 8px' }}>
                <input placeholder="Исм..." value={userFilter}
                  onChange={e => setUserFilter(e.target.value)}
                  style={{
                    width: '100%', padding: '6px 10px', borderRadius: '8px',
                    border: '1px solid var(--border)', background: 'white',
                    fontSize: '0.78rem', outline: 'none', boxSizing: 'border-box'
                  }} />
              </td>
              <td style={{ padding: '6px 8px' }}>
                <input placeholder="№" value={textIdFilter}
                  onChange={e => setTextIdFilter(e.target.value)}
                  style={{
                    width: '100%', padding: '6px 10px', borderRadius: '8px',
                    border: '1px solid var(--border)', background: 'white',
                    fontSize: '0.78rem', outline: 'none', textAlign: 'center', boxSizing: 'border-box'
                  }} />
              </td>
              <td style={{ padding: '6px 8px' }}>
                <input placeholder="йй.ОО.йй" style={{
                  width: '100%', padding: '6px 10px', borderRadius: '8px',
                  border: '1px solid var(--border)', background: 'white',
                  fontSize: '0.78rem', outline: 'none', boxSizing: 'border-box'
                }} />
              </td>
              <td></td>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={columns.length + 4} style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
                <Loader2 size={28} style={{ animation: 'spin 1s linear infinite', marginBottom: 12 }} />
                <p>Юкланмоқда...</p>
              </td></tr>
            ) : filtered.length === 0 ? (
              <tr><td colSpan={columns.length + 4} style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
                <div style={{ fontSize: '3rem', marginBottom: 12 }}>{meta.icon}</div>
                <p style={{ fontWeight: 600 }}>Ёзувлар топилмади</p>
                <p style={{ fontSize: '0.85rem', marginTop: 8 }}>Янги термин қўшиш учун «ЯНГИ ҚЎШИШ» тугмасини босинг</p>
              </td></tr>
            ) : filtered.map((item, i) => (
              <tr key={item.id} style={{ borderBottom: '1px solid var(--border)', transition: 'background 0.15s' }}
                onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = 'var(--bg-secondary)'}
                onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = ''}>

                <td style={{ padding: '14px 16px', color: 'var(--text-muted)', fontWeight: 600, fontSize: '0.85rem' }}>{i + 1}</td>

                {columns.map((col, ci) => {
                  const val = getCellValue(item, col.key, category)
                  const isFirst = ci === 0
                  return (
                    <td key={col.key} style={{ padding: '14px 16px', verticalAlign: 'top' }}>
                      <div style={{
                        fontWeight: isFirst ? 700 : 400,
                        fontSize: '0.88rem',
                        color: isFirst ? meta.color : 'var(--text-primary)',
                        lineHeight: '1.5',
                        ...(col.key === 'context' || col.key === 'description' ? { fontSize: '0.82rem', color: 'var(--text-secondary)' } : {})
                      }}>
                        {val || <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>—</span>}
                      </div>
                    </td>
                  )
                })}

                {/* Specialist */}
                <td style={{ padding: '14px 16px' }}>
                  <div style={{ fontSize: '0.85rem' }}>
                    <span style={{ color: '#16A34A', fontWeight: 600 }}>● {item.user_name || '—'}</span>
                    {item.modified_by_name && item.modified_by_name !== item.user_name && (
                      <div style={{ color: '#D97706', fontSize: '0.75rem', marginTop: '2px' }}>✏ {item.modified_by_name}</div>
                    )}
                  </div>
                </td>

                {/* Text ID */}
                <td style={{ padding: '14px 16px', textAlign: 'center' }}>
                  {item.text_id ? (
                    <span style={{
                      fontFamily: 'monospace', fontSize: '0.78rem', padding: '2px 8px',
                      background: 'var(--accent-bg)', color: 'var(--accent-primary)',
                      borderRadius: '6px', fontWeight: 700
                    }}>{item.text_id}</span>
                  ) : <span style={{ color: 'var(--text-muted)' }}>—</span>}
                </td>

                {/* Date */}
                <td style={{ padding: '14px 16px', color: 'var(--text-muted)', fontSize: '0.82rem' }}>
                  {formatDate(item.created_at)}
                  {item.modified_at && (
                    <div style={{ fontSize: '0.72rem', color: '#D97706' }}>✏ {formatDate(item.modified_at)}</div>
                  )}
                </td>

                {/* Actions */}
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

      {/* Editorial Board Approved Disputed Words — second table (disputed category only) */}
      {category === 'disputed' && <DisputedBoardTable />}

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
            <div style={{ padding: '24px 28px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: meta.bg }}>
              <h2 style={{ fontWeight: 800, fontSize: '1.1rem', color: meta.color }}>
                {editItem.id ? 'Таҳрирлаш' : 'Янги ёзув'} — {meta.title}
              </h2>
              <button onClick={() => setEditItem(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
                <X size={20} />
              </button>
            </div>
            <div style={{ padding: '24px 28px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {editFields.map(f => (
                <div key={f.key}>
                  <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
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
            <div style={{ padding: '16px 28px', borderTop: '1px solid var(--border)', background: 'var(--bg-secondary)', display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button onClick={() => setEditItem(null)} style={{ padding: '10px 22px', borderRadius: '10px', border: '1px solid var(--border)', background: 'white', fontWeight: 700, cursor: 'pointer', fontSize: '0.85rem' }}>
                Бекор
              </button>
              <button onClick={handleSave} disabled={saving} style={{
                padding: '10px 22px', borderRadius: '10px', border: 'none',
                background: meta.headerBg, color: 'white', fontWeight: 700,
                cursor: saving ? 'not-allowed' : 'pointer', fontSize: '0.85rem',
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

// ═══════════════════════════════════════════════════
// Editorial Board Approved Disputed Words (second table)
// ═══════════════════════════════════════════════════
function DisputedBoardTable() {
  const [rows, setRows] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [q, setQ] = useState('')
  const [fRu, setFRu] = useState('')
  const [fEn, setFEn] = useState('')
  const [fProp, setFProp] = useState('')
  const [expanded, setExpanded] = useState<number | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const r: any = await api.admin.disputedBoard(q)
      setRows(r.rows || [])
    } catch { setRows([]) }
    finally { setLoading(false) }
  }, [q])

  useEffect(() => { load() }, [load])

  const visible = rows.filter(r => {
    if (fRu && !(r.ru_term || '').toLowerCase().includes(fRu.toLowerCase())) return false
    if (fEn && !(r.en_context || '').toLowerCase().includes(fEn.toLowerCase())) return false
    if (fProp && !(r.proposed_variant || '').toLowerCase().includes(fProp.toLowerCase())) return false
    return true
  })

  return (
    <div style={{ marginTop: 32 }}>
      <div style={{
        background: 'linear-gradient(135deg, #fce7f3 0%, #fbcfe8 100%)',
        borderRadius: 16, padding: '18px 24px', marginBottom: 14,
        border: '1.5px solid #f9a8d4', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16, flexWrap: 'wrap'
      }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 800, color: '#831843' }}>
            🏛️ Таҳририят кенгаши тасдиқлаган мунозарали сўзлар
          </h2>
          <p style={{ margin: 0, fontSize: '.78rem', color: '#9f1239' }}>
            Европа фармакопеяси асосида Давлат фармакопеяси учун тасдиқланган терминлар — {rows.length} та
          </p>
        </div>
        <div style={{ position: 'relative' }}>
          <Search size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#9f1239' }} />
          <input value={q} onChange={e => setQ(e.target.value)} placeholder="Қидирув..."
            style={{ padding: '8px 12px 8px 34px', borderRadius: 10, border: '1.5px solid #f9a8d4', background: 'white', fontSize: '.82rem', outline: 'none', minWidth: 240 }} />
        </div>
      </div>

      <div style={{ background: 'white', borderRadius: 14, border: '1px solid #E2E8F0', overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: 40, textAlign: 'center', color: '#94A3B8' }}>
            <Loader2 className="animate-spin" size={28} />
          </div>
        ) : (
          <div style={{ maxHeight: '70vh', overflowY: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '.82rem' }}>
              <thead style={{ position: 'sticky', top: 0, background: '#FDF2F8', borderBottom: '2px solid #f9a8d4', zIndex: 1 }}>
                <tr>
                  <th style={{ padding: '12px 16px', textAlign: 'left', fontWeight: 700, fontSize: '.7rem', color: '#831843', textTransform: 'uppercase', width: 50 }}>№</th>
                  <th style={{ padding: '12px 16px', textAlign: 'left', fontWeight: 700, fontSize: '.7rem', color: '#831843', textTransform: 'uppercase' }}>РУС ТЕРМИН</th>
                  <th style={{ padding: '12px 16px', textAlign: 'left', fontWeight: 700, fontSize: '.7rem', color: '#831843', textTransform: 'uppercase' }}>EUR.PH. КОНТЕКСТ (EN)</th>
                  <th style={{ padding: '12px 16px', textAlign: 'left', fontWeight: 700, fontSize: '.7rem', color: '#831843', textTransform: 'uppercase' }}>МАВЖУД ВАРИАНТЛАР</th>
                  <th style={{ padding: '12px 16px', textAlign: 'left', fontWeight: 700, fontSize: '.7rem', color: '#831843', textTransform: 'uppercase' }}>ТАКЛИФ</th>
                  <th style={{ padding: '12px 16px', width: 50 }}></th>
                </tr>
                <tr style={{ background: '#FDF2F8', borderBottom: '1px solid #f9a8d4' }}>
                  <th></th>
                  <th style={{ padding: '6px 16px' }}>
                    <input value={fRu} onChange={e => setFRu(e.target.value)} placeholder="🔍 рус..."
                      style={{ width: '100%', padding: '5px 8px', borderRadius: 6, border: '1px solid #fbcfe8', fontSize: '.72rem', background: 'white' }} />
                  </th>
                  <th style={{ padding: '6px 16px' }}>
                    <input value={fEn} onChange={e => setFEn(e.target.value)} placeholder="🔍 EN..."
                      style={{ width: '100%', padding: '5px 8px', borderRadius: 6, border: '1px solid #fbcfe8', fontSize: '.72rem', background: 'white' }} />
                  </th>
                  <th></th>
                  <th style={{ padding: '6px 16px' }}>
                    <input value={fProp} onChange={e => setFProp(e.target.value)} placeholder="🔍 таклиф..."
                      style={{ width: '100%', padding: '5px 8px', borderRadius: 6, border: '1px solid #fbcfe8', fontSize: '.72rem', background: 'white' }} />
                  </th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {visible.length === 0 ? (
                  <tr><td colSpan={6} style={{ padding: 40, textAlign: 'center', color: '#94A3B8' }}>Топилмади</td></tr>
                ) : visible.map((r, i) => (
                  <React.Fragment key={r.id}>
                    <tr style={{ borderBottom: '1px solid #FCE7F3', cursor: 'pointer' }} onClick={() => setExpanded(expanded === r.id ? null : r.id)}>
                      <td style={{ padding: '10px 16px', color: '#9CA3AF', fontWeight: 700 }}>{r.seq_no || i + 1}</td>
                      <td style={{ padding: '10px 16px', fontWeight: 700, color: '#9D174D' }}>{r.ru_term}</td>
                      <td style={{ padding: '10px 16px', color: '#475569', fontSize: '.75rem', maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {(r.en_context || '').slice(0, 100)}{(r.en_context || '').length > 100 ? '…' : ''}
                      </td>
                      <td style={{ padding: '10px 16px', color: '#64748B', fontSize: '.75rem', whiteSpace: 'pre-line' }}>
                        {(r.existing_variants || '').slice(0, 80)}
                      </td>
                      <td style={{ padding: '10px 16px' }}>
                        <span style={{ padding: '4px 10px', borderRadius: 14, background: '#DCFCE7', color: '#15803D', fontWeight: 800, fontSize: '.78rem' }}>
                          {r.proposed_variant}
                        </span>
                      </td>
                      <td style={{ padding: '10px 16px', color: '#BE185D', fontSize: '1rem' }}>
                        {expanded === r.id ? '▲' : '▼'}
                      </td>
                    </tr>
                    {expanded === r.id && (
                      <tr>
                        <td colSpan={6} style={{ padding: 16, background: '#FDF2F8', borderBottom: '1px solid #FCE7F3' }}>
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, fontSize: '.8rem' }}>
                            <div><b>EN контекст:</b><br />{r.en_context || '—'}</div>
                            <div><b>RU контекст:</b><br />{r.ru_context || '—'}</div>
                            <div style={{ gridColumn: '1 / -1' }}><b>Изоҳ (UZ):</b><br />{r.definition_uz || '—'}</div>
                            <div style={{ gridColumn: '1 / -1' }}><b>Мавжуд вариантлар:</b><br /><pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>{r.existing_variants || '—'}</pre></div>
                            <div style={{ gridColumn: '1 / -1' }}><b>Адабиётлар:</b><br /><pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontFamily: 'inherit', fontSize: '.74rem', color: '#64748B' }}>{r.references_text || '—'}</pre></div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
