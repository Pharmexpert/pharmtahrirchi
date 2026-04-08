'use client'

import React, { useState, useEffect } from 'react'
import { Layers, Search, Loader2, RefreshCw } from 'lucide-react'
import { useAuth } from '../../../components/LoginGuard'
import api from '../../../services/api'

interface Template {
  id: number
  template: string
  sentence_type?: string
  semantic_type?: string
  example_uz?: string
  formula?: string
  frequency?: number
}

export default function SyntaxTemplatesPage() {
  const { token } = useAuth()
  const [templates, setTemplates] = useState<Template[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState<string>('')
  const [sortBy, setSortBy] = useState<'frequency' | 'template' | 'id'>('frequency')

  const fetchData = async () => {
    setLoading(true)
    try {
      const r: any = await api.syntax.templates(500)
      setTemplates(r.templates || [])
    } finally { setLoading(false) }
  }

  useEffect(() => { fetchData() }, [])

  const filtered = templates
    .filter(t => {
      if (search && !t.template.toLowerCase().includes(search.toLowerCase()) &&
                    !(t.example_uz || '').toLowerCase().includes(search.toLowerCase())) return false
      if (typeFilter && t.sentence_type !== typeFilter) return false
      return true
    })
    .sort((a: any, b: any) => {
      if (sortBy === 'frequency') return (b.frequency || 0) - (a.frequency || 0)
      if (sortBy === 'template') return (a.template || '').localeCompare(b.template || '')
      return (a.id || 0) - (b.id || 0)
    })

  const types = Array.from(new Set(templates.map(t => t.sentence_type).filter(Boolean))) as string[]

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      <div style={{
        background: 'linear-gradient(135deg, #FFF8F0 0%, #FFEFDC 100%)',
        borderRadius: 20, padding: '24px 28px', marginBottom: 20,
        border: '1.5px solid #FDE3C5', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 18 }}>
          <div style={{
            width: 48, height: 48, borderRadius: 12,
            background: 'linear-gradient(135deg, #B48C64, #8B5E3C)',
            display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}><Layers size={24} color="white" /></div>
          <div>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 800, margin: 0 }}>Синтаксис шаблонлари 📋</h1>
            <p style={{ color: '#64748B', fontSize: '.85rem', margin: 0 }}>
              UD_Uzbek + ручной қўшилган гап шаблонлари ({templates.length})
            </p>
          </div>
        </div>
        <button onClick={fetchData} style={{ padding: '10px 16px', borderRadius: 10, border: '1px solid #E2E8F0', background: 'white', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
          <RefreshCw size={14} /> Янгилаш
        </button>
      </div>

      <div style={{ display: 'flex', gap: 12, marginBottom: 16, alignItems: 'center' }}>
        <div style={{ position: 'relative', flex: 1 }}>
          <Search size={15} style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: '#94A3B8' }} />
          <input placeholder="Шаблон ёки намуна бўйича қидириш..." value={search} onChange={e => setSearch(e.target.value)}
            style={{ width: '100%', padding: '11px 16px 11px 40px', borderRadius: 10, border: '1px solid #E2E8F0', fontSize: '.9rem', outline: 'none', boxSizing: 'border-box' }} />
        </div>
        <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)}
          style={{ padding: '11px 14px', borderRadius: 10, border: '1px solid #E2E8F0', background: 'white', fontSize: '.82rem', cursor: 'pointer' }}>
          <option value="">Тип: барчаси</option>
          {types.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <select value={sortBy} onChange={e => setSortBy(e.target.value as any)}
          style={{ padding: '11px 14px', borderRadius: 10, border: '1px solid #E2E8F0', background: 'white', fontSize: '.82rem', cursor: 'pointer' }}>
          <option value="frequency">Sort: частота</option>
          <option value="template">Sort: шаблон</option>
          <option value="id">Sort: id</option>
        </select>
      </div>

      <div style={{ background: 'white', borderRadius: 14, border: '1px solid #E2E8F0', overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: 60, textAlign: 'center', color: '#94A3B8' }}>
            <Loader2 className="animate-spin" size={32} style={{ margin: '0 auto 10px' }} />
            Yuklanmoqda...
          </div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: 60, textAlign: 'center', color: '#94A3B8' }}>
            Шаблонлар топилмади
          </div>
        ) : (
          <div style={{ maxHeight: '70vh', overflowY: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '.85rem' }}>
              <thead style={{ position: 'sticky', top: 0, background: '#F8FAFC', borderBottom: '2px solid #E2E8F0' }}>
                <tr>
                  <th style={{ padding: '14px 18px', textAlign: 'left', fontWeight: 700, color: '#64748B', fontSize: '.72rem', textTransform: 'uppercase' }}>Шаблон</th>
                  <th style={{ padding: '14px 18px', textAlign: 'left', fontWeight: 700, color: '#64748B', fontSize: '.72rem', textTransform: 'uppercase' }}>Тип</th>
                  <th style={{ padding: '14px 18px', textAlign: 'left', fontWeight: 700, color: '#64748B', fontSize: '.72rem', textTransform: 'uppercase' }}>Намуна</th>
                  <th style={{ padding: '14px 18px', textAlign: 'right', fontWeight: 700, color: '#64748B', fontSize: '.72rem', textTransform: 'uppercase' }}>Частота</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(t => (
                  <tr key={t.id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                    <td style={{ padding: '12px 18px', fontFamily: 'monospace', color: '#2563EB', fontWeight: 700 }}>{t.template}</td>
                    <td style={{ padding: '12px 18px' }}>
                      <span style={{ padding: '3px 10px', borderRadius: 12, fontSize: '.68rem', fontWeight: 700, background: '#F3E8FF', color: '#7C3AED', textTransform: 'uppercase' }}>
                        {t.sentence_type || '—'}
                      </span>
                    </td>
                    <td style={{ padding: '12px 18px', color: '#475569' }}>{t.example_uz || '—'}</td>
                    <td style={{ padding: '12px 18px', textAlign: 'right', fontWeight: 800, color: '#16A34A' }}>{t.frequency || 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
