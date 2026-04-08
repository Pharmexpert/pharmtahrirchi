'use client'

/**
 * LinguisticAnalysisBar — Shared 4-layer linguistic analysis control.
 *
 * Layers:
 *   1. Morphology (Morph) — word-level
 *   2. Sayqallash — spelling/rules
 *   3. Syntax — sentence-level
 *   4. Style Guide — document-level (USP/Ph.Eur./ICH/WHO/SI)
 *
 * Usage:
 *   <LinguisticAnalysisBar text={text} onResult={setResult} />
 *
 * Reusable across:
 *   - TableEditor toolbar (Dashboard/Files)
 *   - Tilshunos edit mode
 *   - Tilshunos translate mode
 *   - Word hujjat mode
 *   - Style Guide page
 *   - Assistant file preview
 */
import React, { useState } from 'react'
import { Loader2, Layers, Feather, BookOpen, FileCheck2, Sparkles } from 'lucide-react'
import api from '../services/api'

export interface AnalysisResult {
  morph: any[]
  sayqallash: any[]
  syntax: any[]
  style: any[]
  total: number
  summary: { morph_count: number; sayqallash_count: number; syntax_count: number; style_count: number }
}

interface Props {
  text: string
  lang?: string
  compact?: boolean
  onResult?: (result: AnalysisResult) => void
  extraButtons?: Array<{ label: string; icon?: React.ReactNode; color?: string; onClick: () => void }>
}

export default function LinguisticAnalysisBar({ text, lang = 'uz', compact = false, onResult, extraButtons = [] }: Props) {
  const [loading, setLoading] = useState<string | null>(null)
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const run = async (layers: string[], label: string) => {
    if (!text?.trim()) {
      setError('Матн бўш')
      setTimeout(() => setError(null), 2000)
      return
    }
    setLoading(label)
    setError(null)
    try {
      const r = await api.analyze.full(text, lang, layers)
      setResult(r)
      onResult?.(r)
    } catch (e: any) {
      setError(e?.message || 'Xato')
    } finally {
      setLoading(null)
    }
  }

  const buttonStyle = (color: string, isLoading: boolean): React.CSSProperties => ({
    padding: compact ? '5px 10px' : '7px 14px',
    borderRadius: 8,
    border: 'none',
    background: isLoading ? '#9CA3AF' : color,
    color: 'white',
    fontWeight: 700,
    fontSize: compact ? '.7rem' : '.78rem',
    cursor: isLoading ? 'not-allowed' : 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: 5,
    opacity: isLoading ? 0.7 : 1,
  })

  const badgeStyle = (color: string, count: number): React.CSSProperties => ({
    padding: '2px 7px',
    borderRadius: 10,
    background: count > 0 ? color : '#E2E8F0',
    color: count > 0 ? 'white' : '#64748B',
    fontSize: '.64rem',
    fontWeight: 800,
    marginLeft: 4,
  })

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap',
      padding: compact ? '6px 10px' : '8px 12px',
      background: 'linear-gradient(135deg, #F8FAFC 0%, #F1F5F9 100%)',
      borderRadius: 10, border: '1px solid #E2E8F0',
    }}>
      <span style={{ fontSize: compact ? '.62rem' : '.68rem', fontWeight: 800, color: '#475569', textTransform: 'uppercase', letterSpacing: '.04em', marginRight: 2 }}>
        <Layers size={11} style={{ display: 'inline', verticalAlign: -1, marginRight: 3 }} />
        4 қатлам:
      </span>

      <button onClick={() => run(['morph'], 'morph')} disabled={!!loading} style={buttonStyle('#0891B2', loading === 'morph')} title="Morphology — сўз таркиби">
        {loading === 'morph' ? <Loader2 size={11} className="animate-spin" /> : <Feather size={11} />}
        Morph
        {result && result.summary && <span style={badgeStyle('#0891B2', result.summary.morph_count)}>{result.summary.morph_count}</span>}
      </button>

      <button onClick={() => run(['sayqallash'], 'sayqallash')} disabled={!!loading} style={buttonStyle('#8B5E3C', loading === 'sayqallash')} title="Sayqallash — имло/қоидалар">
        {loading === 'sayqallash' ? <Loader2 size={11} className="animate-spin" /> : <Sparkles size={11} />}
        Sayqallash
        {result && result.summary && <span style={badgeStyle('#8B5E3C', result.summary.sayqallash_count)}>{result.summary.sayqallash_count}</span>}
      </button>

      <button onClick={() => run(['syntax'], 'syntax')} disabled={!!loading} style={buttonStyle('#7C3AED', loading === 'syntax')} title="Syntax — гап тузилиши">
        {loading === 'syntax' ? <Loader2 size={11} className="animate-spin" /> : <BookOpen size={11} />}
        Syntax
        {result && result.summary && <span style={badgeStyle('#7C3AED', result.summary.syntax_count)}>{result.summary.syntax_count}</span>}
      </button>

      <button onClick={() => run(['style'], 'style')} disabled={!!loading} style={buttonStyle('#DB2777', loading === 'style')} title="Style Guide — USP/Ph.Eur./ICH/SI">
        {loading === 'style' ? <Loader2 size={11} className="animate-spin" /> : <FileCheck2 size={11} />}
        Style
        {result && result.summary && <span style={badgeStyle('#DB2777', result.summary.style_count)}>{result.summary.style_count}</span>}
      </button>

      <div style={{ width: 1, height: 18, background: '#CBD5E1', margin: '0 4px' }} />

      <button onClick={() => run(['morph', 'sayqallash', 'syntax', 'style'], 'all')} disabled={!!loading} style={buttonStyle('linear-gradient(135deg, #16A34A, #15803D)', loading === 'all')} title="Барча 4 қатламни параллел ишга тушириш">
        {loading === 'all' ? <Loader2 size={11} className="animate-spin" /> : <Layers size={11} />}
        Hammasi
        {result && <span style={badgeStyle('#15803D', result.total)}>{result.total}</span>}
      </button>

      {extraButtons.map((b, i) => (
        <button key={i} onClick={b.onClick} style={buttonStyle(b.color || '#6366F1', false)}>
          {b.icon}
          {b.label}
        </button>
      ))}

      {error && (
        <span style={{ fontSize: '.7rem', color: '#DC2626', fontWeight: 700, marginLeft: 6 }}>⚠ {error}</span>
      )}
    </div>
  )
}
