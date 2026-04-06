'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { Layers, Search, Loader2, RefreshCw } from 'lucide-react'
import { useAuth } from '../../components/LoginGuard'

interface AffixFlag {
  flag: string
  count: number
  description: string
  examples: { remove: string; add: string }[]
  language: string
}

export default function AffixFlagsPage() {
  const { token } = useAuth()
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const [flags, setFlags] = useState<AffixFlag[]>([])
  const [language, setLanguage] = useState<'cyrl' | 'lat'>('cyrl')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(0)
  const [perPage, setPerPage] = useState(25)
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(0)
  const [loading, setLoading] = useState(false)

  const fetchFlags = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        language, page: String(page), per_page: String(perPage), search
      })
      const res = await fetch(`${API_BASE}/api/dictionary/affix-flags?${params}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        const d = await res.json()
        setFlags(d.flags || [])
        setTotal(d.total || 0)
        setTotalPages(d.total_pages || 0)
      }
    } catch {} finally { setLoading(false) }
  }, [API_BASE, token, language, page, perPage, search])

  useEffect(() => { fetchFlags() }, [fetchFlags])

  // Color palette for flags
  const flagColor = (flag: string): string => {
    const colors = ['#3B82F6', '#10B981', '#F59E0B', '#8B5CF6', '#EF4444', '#06B6D4', '#EC4899', '#84CC16']
    const idx = flag.charCodeAt(0) % colors.length
    return colors[idx]
  }

  return (
    <div>
      {/* Hero */}
      <div style={{
        background: 'linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%)', borderRadius: '20px',
        padding: '32px 36px', border: '1.5px solid #BFDBFE', marginBottom: '28px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '20px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <div style={{
            width: 52, height: 52, borderRadius: '14px',
            background: 'linear-gradient(135deg, #2563EB, #1D4ED8)',
            display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>
            <Layers size={24} color="white" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.7rem', fontWeight: 800, marginBottom: '4px' }}>Affix Flags — Hunspell</h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: 0 }}>
              Suffix/Prefix қоидалари • <strong>{total}</strong> гуруҳ
            </p>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button onClick={() => { setLanguage('cyrl'); setPage(0) }} style={{
            padding: '8px 18px', borderRadius: '10px',
            border: language === 'cyrl' ? '1.5px solid #2563EB' : '1px solid var(--border)',
            background: language === 'cyrl' ? '#EFF6FF' : 'white',
            color: language === 'cyrl' ? '#2563EB' : 'var(--text-secondary)',
            fontWeight: 700, fontSize: '0.85rem', cursor: 'pointer'
          }}>Кирилл</button>
          <button onClick={() => { setLanguage('lat'); setPage(0) }} style={{
            padding: '8px 18px', borderRadius: '10px',
            border: language === 'lat' ? '1.5px solid #16A34A' : '1px solid var(--border)',
            background: language === 'lat' ? '#F0FDF4' : 'white',
            color: language === 'lat' ? '#16A34A' : 'var(--text-secondary)',
            fontWeight: 700, fontSize: '0.85rem', cursor: 'pointer'
          }}>Lotin</button>
        </div>
      </div>

      {/* Search */}
      <div style={{ marginBottom: '20px', display: 'flex', gap: '12px', alignItems: 'center' }}>
        <div style={{ position: 'relative', flex: 1 }}>
          <Search size={15} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input placeholder="Flag ёки тавсиф бўйича қидириш..." value={search} onChange={e => { setSearch(e.target.value); setPage(0) }}
            style={{ width: '100%', padding: '12px 16px 12px 40px', borderRadius: '12px', border: '1px solid var(--border)', fontSize: '0.9rem', outline: 'none', boxSizing: 'border-box' }} />
        </div>
        <button onClick={fetchFlags} style={{
          padding: '12px 16px', borderRadius: '10px', border: '1px solid var(--border)',
          background: 'white', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px'
        }}><RefreshCw size={14} /> Янгилаш</button>
      </div>

      {/* Flags table */}
      <div style={{ background: 'var(--bg-card)', borderRadius: '16px', border: '1px solid var(--border)', overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: '60px', textAlign: 'center' }}>
            <Loader2 size={28} style={{ animation: 'spin 1s linear infinite' }} />
          </div>
        ) : (
          flags.map((f, i) => (
            <div key={f.flag} style={{
              padding: '16px 24px', borderBottom: '1px solid var(--border)',
              display: 'grid', gridTemplateColumns: '60px 80px 100px 1fr 1.5fr', gap: '16px', alignItems: 'flex-start'
            }}>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 600 }}>{page * perPage + i + 1}</span>
              <span style={{
                display: 'inline-block', padding: '6px 14px', borderRadius: '8px',
                background: `${flagColor(f.flag)}15`, color: flagColor(f.flag),
                fontSize: '1rem', fontWeight: 800, fontFamily: 'monospace', textAlign: 'center'
              }}>{f.flag}</span>
              <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#16A34A' }}>{f.count} та</span>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-primary)' }}>{f.description}</span>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {f.examples.slice(0, 6).map((ex, j) => (
                  <span key={j} style={{
                    padding: '3px 8px', borderRadius: '6px', fontSize: '0.72rem',
                    background: '#F1F5F9', color: '#475569', fontFamily: 'monospace',
                    border: '1px solid #E2E8F0'
                  }}>
                    {ex.remove && <span style={{ color: '#DC2626' }}>−{ex.remove}</span>}
                    <span style={{ color: '#16A34A', fontWeight: 700 }}>+{ex.add}</span>
                  </span>
                ))}
                {f.examples.length > 6 && (
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>+{f.examples.length - 6}</span>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px', marginTop: '20px', flexWrap: 'wrap' }}>
          <button disabled={page === 0} onClick={() => setPage(p => p - 1)} style={{
            padding: '8px 16px', borderRadius: '8px', border: '1px solid var(--border)',
            background: page === 0 ? '#F1F5F9' : 'white', cursor: page === 0 ? 'default' : 'pointer',
            fontWeight: 700, fontSize: '0.82rem'
          }}>← Олдинги</button>
          <span style={{ padding: '8px 16px', fontSize: '0.85rem', fontWeight: 600 }}>
            {page + 1} / {totalPages} ({total} та)
          </span>
          <button disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)} style={{
            padding: '8px 16px', borderRadius: '8px', border: '1px solid var(--border)',
            background: page >= totalPages - 1 ? '#F1F5F9' : 'white', cursor: page >= totalPages - 1 ? 'default' : 'pointer',
            fontWeight: 700, fontSize: '0.82rem'
          }}>Кейинги →</button>
          <select value={perPage} onChange={e => { setPerPage(Number(e.target.value)); setPage(0) }} style={{
            padding: '6px 12px', borderRadius: '8px', border: '1px solid var(--border)', fontSize: '0.82rem', cursor: 'pointer'
          }}>
            <option value={25}>25 / бет</option>
            <option value={50}>50 / бет</option>
          </select>
        </div>
      )}
    </div>
  )
}
