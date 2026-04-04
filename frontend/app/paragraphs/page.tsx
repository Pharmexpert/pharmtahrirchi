'use client'

import React, { useState, useEffect } from 'react'
import { Search, FileText, Filter } from 'lucide-react'
import { useAuth } from '../../components/LoginGuard'

export default function ParagraphsPage() {
  const { token } = useAuth()
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const [paragraphs, setParagraphs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [langFilter, setLangFilter] = useState<'all' | 'en' | 'ru' | 'uz'>('all')

  useEffect(() => { fetchParagraphs() }, [token])

  const fetchParagraphs = async () => {
    if (!token) return
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/linguistic/all`)
      if (res.ok) {
        const data = await res.json()
        setParagraphs(data.paragraphs || [])
      }
    } finally { setLoading(false) }
  }

  const filtered = paragraphs.filter(p => {
    const q = search.toLowerCase()
    return !q || (p.en_text || '').toLowerCase().includes(q) ||
      (p.ru_text || '').toLowerCase().includes(q) ||
      (p.uz_text || '').toLowerCase().includes(q) ||
      (p.text_id || '').toLowerCase().includes(q)
  })

  return (
    <div>
      <div style={{ marginBottom: '32px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h1 style={{ fontSize: '2rem', fontWeight: 800, marginBottom: '8px', letterSpacing: '-0.5px' }}>
            Хатбошилар 📄
          </h1>
          <p style={{ color: 'var(--text-muted)' }}>Барча лойиҳалардаги таҳрирланган сегментлар</p>
        </div>
        <div style={{
          background: 'var(--bg-card)', padding: '12px 20px', borderRadius: '12px',
          border: '1px solid var(--border)', fontWeight: 800, fontSize: '1.1rem'
        }}>
          {paragraphs.length} та хатбоши
        </div>
      </div>

      {/* Controls */}
      <div style={{ display: 'flex', gap: '16px', marginBottom: '24px', flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: '240px' }}>
          <Search size={16} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input
            placeholder="Матн ёки матн рақами бўйича..."
            value={search} onChange={e => setSearch(e.target.value)}
            style={{
              width: '100%', padding: '11px 11px 11px 42px', borderRadius: '12px',
              border: '1px solid var(--border)', background: 'var(--bg-card)',
              fontSize: '0.95rem', outline: 'none', boxSizing: 'border-box'
            }}
          />
        </div>
        <div style={{ display: 'flex', gap: '8px', background: 'var(--bg-card)', padding: '4px', borderRadius: '10px', border: '1px solid var(--border)' }}>
          {(['all', 'en', 'ru', 'uz'] as const).map(l => (
            <button key={l} onClick={() => setLangFilter(l)} style={{
              padding: '8px 16px', borderRadius: '8px', border: 'none', cursor: 'pointer',
              fontWeight: 700, fontSize: '0.85rem',
              background: langFilter === l ? 'var(--accent-primary)' : 'transparent',
              color: langFilter === l ? 'white' : 'var(--text-muted)'
            }}>
              {l === 'all' ? 'Барча' : l.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Paragraphs */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-muted)' }}>Юкланмоқда...</div>
        ) : filtered.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-muted)' }}>
            <FileText size={48} style={{ opacity: 0.2, marginBottom: 12 }} />
            <p style={{ fontWeight: 600 }}>Хатбошилар топилмади</p>
          </div>
        ) : filtered.map((p, i) => (
          <div key={i} style={{
            background: 'var(--bg-card)', borderRadius: '14px',
            border: '1px solid var(--border)', overflow: 'hidden',
            boxShadow: '0 2px 6px rgba(0,0,0,0.04)'
          }}>
            {/* Header */}
            <div style={{
              padding: '12px 20px', background: 'var(--bg-secondary)',
              borderBottom: '1px solid var(--border)',
              display: 'flex', gap: '16px', alignItems: 'center'
            }}>
              <span style={{ fontWeight: 800, color: 'var(--text-muted)', fontSize: '0.8rem' }}>№ {i + 1}</span>
              {p.text_id && (
                <span style={{
                  fontFamily: 'monospace', fontSize: '0.8rem', padding: '2px 8px',
                  background: 'var(--accent-bg)', color: 'var(--accent-primary)',
                  borderRadius: '6px', fontWeight: 700
                }}>{p.text_id}</span>
              )}
              {p.specialist_name && (
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>👤 {p.specialist_name}</span>
              )}
            </div>
            {/* Content grid */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0' }}>
              {[
                { lang: 'EN', key: 'en_text', color: '#2563EB', show: langFilter === 'all' || langFilter === 'en' },
                { lang: 'RU', key: 'ru_text', color: '#DC2626', show: langFilter === 'all' || langFilter === 'ru' },
                { lang: 'UZ', key: 'uz_text', color: '#16A34A', show: langFilter === 'all' || langFilter === 'uz' },
              ].filter(col => col.show).map((col, ci) => (
                <div key={col.lang} style={{
                  padding: '16px 20px',
                  borderRight: ci < 2 ? '1px solid var(--border)' : 'none'
                }}>
                  <div style={{ fontSize: '0.7rem', fontWeight: 800, color: col.color, marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '1px' }}>{col.lang}</div>
                  <div style={{ fontSize: '0.9rem', lineHeight: '1.6', color: 'var(--text-primary)' }}>
                    {(p as any)[col.key] || <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>—</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
