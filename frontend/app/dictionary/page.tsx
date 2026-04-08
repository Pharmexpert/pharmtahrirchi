'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { BookOpen, Search, Loader2, RefreshCw } from 'lucide-react'
import { useAuth } from '../../components/LoginGuard'
import { useLang } from '../../components/LanguageProvider'
import api from '../../services/api'

interface DictWord {
  word: string
  flags: string
  language: string
  pos: string
  frequency?: number
  source?: string
}

interface Translation { ru: string; en: string; definition: string }

const POS_LABELS: Record<string, { label: string; color: string }> = {
  noun: { label: 'От', color: '#3B82F6' },
  verb: { label: 'Феъл', color: '#10B981' },
  adj: { label: 'Сифат', color: '#F59E0B' },
  adv: { label: 'Равиш', color: '#8B5CF6' },
  other: { label: 'Бошқа', color: '#6B7280' },
}

export default function DictionaryPage() {
  const { token } = useAuth()
  const { t } = useLang()
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const [words, setWords] = useState<DictWord[]>([])
  const [language, setLanguage] = useState<'cyrl' | 'lat'>('cyrl')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(0)
  const [perPage, setPerPage] = useState(50)
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(0)
  const [loading, setLoading] = useState(false)
  const [translations, setTranslations] = useState<Record<string, Translation>>({})
  const [translatingAll, setTranslatingAll] = useState(false)
  const [sourceFilter, setSourceFilter] = useState<string>('')
  const [minFreq, setMinFreq] = useState<number>(0)

  const visibleWords = words.filter(w => {
    if (sourceFilter && (w.source || '') !== sourceFilter) return false
    if (minFreq > 0 && (w.frequency || 0) < minFreq) return false
    return true
  })
  const availableSources = Array.from(new Set(words.map(w => w.source).filter(Boolean))) as string[]
  const maxFreqInPage = Math.max(0, ...words.map(w => w.frequency || 0))

  const fetchWords = useCallback(async () => {
    setLoading(true)
    try {
      const d: any = await api.dictionary.words(language, page, perPage, search)
      setWords(d.words || [])
      setTotal(d.total || 0)
      setTotalPages(d.total_pages || 0)
    } catch {} finally { setLoading(false) }
  }, [language, page, perPage, search])

  useEffect(() => { fetchWords() }, [fetchWords])

  // Fetch cached translations whenever words change, then auto-translate missing ones
  useEffect(() => {
    if (words.length === 0) return
    const wordList = words.map(w => w.word).join(',')
    api.dictionary.translations(wordList)
      .then(async (d: any) => {
        const cached = d?.translations || {}
        setTranslations(prev => ({ ...prev, ...cached }))
        // Auto-translate words that have no cache (background, sequential to avoid quota burst)
        const missing = words.filter(w => !cached[w.word]).slice(0, 25)
        for (const w of missing) {
          try {
            const r: any = await api.dictionary.translate(w.word)
            if (r && (r.ru || r.en)) {
              setTranslations(prev => ({ ...prev, [w.word]: { ru: r.ru, en: r.en, definition: r.definition } }))
            }
          } catch {}
        }
      })
      .catch(() => {})
  }, [words])

  const translateWord = async (word: string) => {
    try {
      const d: any = await api.dictionary.translate(word)
      setTranslations(prev => ({ ...prev, [word]: { ru: d.ru, en: d.en, definition: d.definition } }))
    } catch {}
  }

  const translateAllVisible = async () => {
    setTranslatingAll(true)
    const untranslated = words.filter(w => !translations[w.word])
    for (const w of untranslated.slice(0, 25)) {
      await translateWord(w.word)
    }
    setTranslatingAll(false)
  }

  return (
    <div>
      {/* Hero */}
      <div style={{
        background: 'linear-gradient(135deg, #FFF8F0 0%, #FFEFDC 100%)', borderRadius: '20px',
        padding: '32px 36px', border: '1.5px solid #FDE3C5', marginBottom: '28px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '20px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <div style={{
            width: 52, height: 52, borderRadius: '14px',
            background: 'linear-gradient(135deg, #B48C64, #8B5E3C)',
            display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>
            <BookOpen size={24} color="white" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.7rem', fontWeight: 800, marginBottom: '4px' }}>{t('dict.title')}</h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: 0 }}>
              Ўзбек тили имло луғати • <strong>{total}</strong> сўз • {language === 'cyrl' ? 'Кирилл' : 'Лотин'}
            </p>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button onClick={() => { setLanguage('cyrl'); setPage(0) }} style={{
            padding: '8px 18px', borderRadius: '10px',
            border: language === 'cyrl' ? '1.5px solid #B48C64' : '1px solid var(--border)',
            background: language === 'cyrl' ? '#FFF8F0' : 'white',
            color: language === 'cyrl' ? '#B48C64' : 'var(--text-secondary)',
            fontWeight: 700, fontSize: '0.85rem', cursor: 'pointer'
          }}>🇺🇿 Кирилл</button>
          <button onClick={() => { setLanguage('lat'); setPage(0) }} style={{
            padding: '8px 18px', borderRadius: '10px',
            border: language === 'lat' ? '1.5px solid #16A34A' : '1px solid var(--border)',
            background: language === 'lat' ? '#F0FDF4' : 'white',
            color: language === 'lat' ? '#16A34A' : 'var(--text-secondary)',
            fontWeight: 700, fontSize: '0.85rem', cursor: 'pointer'
          }}>🇺🇿 Lotin</button>
        </div>
      </div>

      {/* Search */}
      <div style={{ marginBottom: '20px', display: 'flex', gap: '12px', alignItems: 'center' }}>
        <div style={{ position: 'relative', flex: 1 }}>
          <Search size={15} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input placeholder="Сўз бўйича қидириш..." value={search} onChange={e => { setSearch(e.target.value); setPage(0) }}
            style={{ width: '100%', padding: '12px 16px 12px 40px', borderRadius: '12px', border: '1px solid var(--border)', fontSize: '0.9rem', outline: 'none', boxSizing: 'border-box' }} />
        </div>
        <select value={sourceFilter} onChange={e => setSourceFilter(e.target.value)}
          style={{ padding: '12px 14px', borderRadius: '10px', border: '1px solid var(--border)', background: 'white', fontSize: '0.82rem', cursor: 'pointer', minWidth: 160 }}>
          <option value="">Манба: барчаси</option>
          {availableSources.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        {maxFreqInPage > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px', borderRadius: '10px', border: '1px solid var(--border)', background: 'white' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700 }}>Мин freq:</span>
            <input type="range" min={0} max={maxFreqInPage} value={minFreq} onChange={e => setMinFreq(Number(e.target.value))}
              style={{ width: 100 }} />
            <span style={{ fontSize: '0.75rem', fontWeight: 800, color: '#2563EB', minWidth: 30 }}>{minFreq}</span>
          </div>
        )}
        <button onClick={fetchWords} style={{
          padding: '12px 16px', borderRadius: '10px', border: '1px solid var(--border)',
          background: 'white', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px'
        }}><RefreshCw size={14} /> Янгилаш</button>
        <a href={`${API_BASE}/api/dictionary/export-csv?language=${language === 'cyrl' ? 'uz-cyr' : 'uz-lat'}`} target="_blank" rel="noreferrer"
          style={{ padding: '12px 16px', borderRadius: '10px', border: '1px solid var(--border)', background: 'white', fontSize: '0.82rem', fontWeight: 700, color: '#0369A1', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 6 }}>
          📥 CSV
        </a>
        <button onClick={translateAllVisible} disabled={translatingAll} style={{
          padding: '12px 16px', borderRadius: '10px', border: 'none',
          background: translatingAll ? '#9CA3AF' : 'linear-gradient(135deg, #B48C64, #8B5E3C)',
          color: 'white', cursor: translatingAll ? 'not-allowed' : 'pointer',
          fontWeight: 700, fontSize: '0.82rem'
        }}>{translatingAll ? '⏳ AI...' : '🤖 AI Таржима'}</button>
      </div>

      {/* Table */}
      <div style={{ background: 'var(--bg-card)', borderRadius: '16px', border: '1px solid var(--border)', overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: '60px', textAlign: 'center' }}>
            <Loader2 size={28} style={{ animation: 'spin 1s linear infinite' }} />
          </div>
        ) : (
          <>
            <div style={{
              display: 'grid', gridTemplateColumns: '60px 1fr 100px 1fr 1fr 120px',
              padding: '14px 20px', background: 'var(--bg-secondary)', borderBottom: '2px solid var(--border)', gap: '12px'
            }}>
              {['№', 'СЎЗ', 'ТУРКУМ', 'ТАРЖИМА (RU)', 'ТАРЖИМА (EN)', 'ИЗОҲ'].map(h => (
                <span key={h} style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>{h}</span>
              ))}
            </div>
            {visibleWords.map((w, i) => {
              const pos = POS_LABELS[w.pos] || POS_LABELS.other
              const tr = translations[w.word]
              return (
                <div key={i} style={{
                  display: 'grid', gridTemplateColumns: '60px 1fr 100px 1fr 1fr 120px',
                  padding: '12px 20px', borderBottom: '1px solid var(--border)', gap: '12px', alignItems: 'center'
                }}>
                  <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>{page * perPage + i + 1}</span>
                  <span style={{ fontWeight: 700, fontSize: '0.9rem' }}>{w.word}</span>
                  <span style={{
                    fontSize: '0.7rem', fontWeight: 700, padding: '3px 8px', borderRadius: '6px',
                    background: `${pos.color}15`, color: pos.color, display: 'inline-block', textAlign: 'center'
                  }}>{pos.label}</span>
                  <span style={{ fontSize: '0.82rem', color: tr?.ru ? '#2563EB' : 'var(--text-muted)', fontWeight: tr?.ru ? 600 : 400 }}>
                    {tr?.ru || (
                      <button onClick={() => translateWord(w.word)} style={{ background: 'none', border: 'none', color: '#94A3B8', cursor: 'pointer', fontSize: '0.7rem' }}>+ AI</button>
                    )}
                  </span>
                  <span style={{ fontSize: '0.82rem', color: tr?.en ? '#9333EA' : 'var(--text-muted)', fontWeight: tr?.en ? 600 : 400 }}>
                    {tr?.en || '—'}
                  </span>
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }} title={`${w.flags || ''}${w.source ? ' — ' + w.source : ''}`}>
                    {typeof w.frequency === 'number' && w.frequency > 0 && (
                      <span style={{ display: 'inline-block', padding: '2px 6px', marginRight: 6, background: '#DBEAFE', color: '#1D4ED8', borderRadius: 4, fontWeight: 700 }}>×{w.frequency}</span>
                    )}
                    {w.source && (
                      <span style={{ display: 'inline-block', padding: '2px 6px', marginRight: 6, background: '#F3E8FF', color: '#7C3AED', borderRadius: 4, fontWeight: 600, fontSize: '0.62rem' }}>{w.source.replace(/_/g, ' ').slice(0, 12)}</span>
                    )}
                    {tr?.definition ? tr.definition.slice(0, 30) + (tr.definition.length > 30 ? '...' : '') : (w.flags ? w.flags.slice(0, 6) + '..' : '—')}
                  </span>
                </div>
              )
            })}
          </>
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
            <option value={100}>100 / бет</option>
          </select>
        </div>
      )}
    </div>
  )
}
