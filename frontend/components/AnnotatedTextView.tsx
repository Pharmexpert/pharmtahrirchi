'use client'

/**
 * AnnotatedTextView — Renders text with inline error highlights.
 *
 * Features:
 *  - Errors from 4 layers (sayqallash/syntax/style/morph) shown as colored underlines
 *  - Click on highlighted word → tooltip with error details + suggestion
 *  - Click on non-highlighted word → synonyms popup
 *  - Double-click any word → synonyms popup (force)
 *  - Replaces sentence-level errors with indicators at start of sentence
 *
 * Layer colors:
 *   sayqallash → brown/red (spelling errors)
 *   syntax → purple (sentence structure)
 *   style → pink (pharma standards)
 *   morph → blue (word form info — usually not shown as error)
 */
import React, { useState, useMemo, useCallback } from 'react'
import { X, Search, Loader2 } from 'lucide-react'
import api from '../services/api'

export interface AnalysisIssue {
  layer?: string
  from?: number
  to?: number
  from_index?: number
  to_index?: number
  old?: string
  old_value?: string
  new?: string
  new_value?: string
  suggestion?: string
  description?: string
  message?: string
  error_type?: string
  severity?: string
  rule_id?: string
  source?: string
  source_ref?: string
  source_url?: string
  sentence_index?: number
  sentence?: string
  confidence?: number
}

export interface AnalysisResult {
  morph?: any[]
  sayqallash?: AnalysisIssue[]
  syntax?: AnalysisIssue[]
  style?: AnalysisIssue[]
}

interface Props {
  text: string
  result: AnalysisResult | null
  lang?: string
}

interface Span {
  start: number
  end: number
  layer: 'sayqallash' | 'syntax' | 'style'
  issue: AnalysisIssue
}

const LAYER_COLORS: Record<string, { under: string; bg: string; label: string }> = {
  sayqallash: { under: '#DC2626', bg: '#FEE2E2', label: 'Сайқаллаш' },
  syntax:     { under: '#7C3AED', bg: '#EDE9FE', label: 'Синтаксис' },
  style:      { under: '#DB2777', bg: '#FCE7F3', label: 'Стиль' },
}

export default function AnnotatedTextView({ text, result }: Props) {
  const [tooltip, setTooltip] = useState<{ x: number; y: number; spans: Span[] } | null>(null)
  const [synonymPopup, setSynonymPopup] = useState<{ x: number; y: number; word: string; loading: boolean; synonyms: any[]; error: string | null } | null>(null)

  // Collect all positional errors into spans (merge overlaps)
  const spans = useMemo<Span[]>(() => {
    if (!result) return []
    const out: Span[] = []
    const layers = ['sayqallash', 'style'] as const
    for (const layer of layers) {
      const items = (result as any)[layer] as AnalysisIssue[] | undefined
      if (!items) continue
      for (const issue of items) {
        const start = typeof issue.from === 'number' ? issue.from
                    : typeof issue.from_index === 'number' ? issue.from_index : -1
        const end = typeof issue.to === 'number' ? issue.to
                  : typeof issue.to_index === 'number' ? issue.to_index : -1
        if (start >= 0 && end > start && end <= text.length) {
          out.push({ start, end, layer, issue })
        }
      }
    }
    // Syntax errors are often sentence-level (no position) — skip for highlight, show as banner
    return out.sort((a, b) => a.start - b.start)
  }, [result, text])

  // Sentence-level syntax errors (no position)
  const sentenceErrors = useMemo<AnalysisIssue[]>(() => {
    if (!result?.syntax) return []
    return result.syntax.filter(i => (i.from === undefined && i.from_index === undefined))
  }, [result])

  // Build rendered segments (text fragments with optional highlights)
  const segments = useMemo(() => {
    if (!spans.length) {
      return [{ start: 0, end: text.length, text, overlaps: [] as Span[] }]
    }
    // Merge overlapping spans
    const segs: Array<{ start: number; end: number; text: string; overlaps: Span[] }> = []
    let cursor = 0
    for (const span of spans) {
      if (span.start > cursor) {
        segs.push({ start: cursor, end: span.start, text: text.slice(cursor, span.start), overlaps: [] })
      }
      // Check if merging into previous highlighted segment
      const last = segs[segs.length - 1]
      if (last && last.overlaps.length && last.end >= span.start) {
        // Extend merge
        last.end = Math.max(last.end, span.end)
        last.text = text.slice(last.start, last.end)
        last.overlaps.push(span)
      } else {
        segs.push({
          start: span.start,
          end: span.end,
          text: text.slice(span.start, span.end),
          overlaps: [span],
        })
      }
      cursor = Math.max(cursor, span.end)
    }
    if (cursor < text.length) {
      segs.push({ start: cursor, end: text.length, text: text.slice(cursor), overlaps: [] })
    }
    return segs
  }, [text, spans])

  const handleClickHighlight = useCallback((e: React.MouseEvent, segSpans: Span[]) => {
    e.stopPropagation()
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
    setTooltip({ x: rect.left, y: rect.bottom + 4, spans: segSpans })
    setSynonymPopup(null)
  }, [])

  const handleClickNormal = useCallback(async (e: React.MouseEvent) => {
    // Find clicked word
    const selection = window.getSelection()
    let word = selection?.toString().trim() || ''
    if (!word) {
      // Extract word at click position
      try {
        const range = document.caretRangeFromPoint?.(e.clientX, e.clientY)
        if (range) {
          const node = range.startContainer
          if (node.nodeType === Node.TEXT_NODE) {
            const txt = node.textContent || ''
            const offset = range.startOffset
            const wordRegex = /[a-zA-Z0-9'ʻА-Яа-яЁёЎўҚқҒғҲҳ]+/g
            let m
            while ((m = wordRegex.exec(txt)) !== null) {
              if (m.index <= offset && offset <= m.index + m[0].length) {
                word = m[0]
                break
              }
            }
          }
        }
      } catch {}
    }
    if (!word || word.length < 2) return

    setTooltip(null)
    setSynonymPopup({ x: e.clientX, y: e.clientY, word, loading: true, synonyms: [], error: null })
    try {
      const r: any = await api.synonyms.list(word)
      const syns = (r?.synonyms || []).map((s: any) => ({
        word: s.synonym || s.word || s,
        frequency: s.frequency,
      })).filter((s: any) => s.word && s.word !== word)
      setSynonymPopup(p => p ? { ...p, synonyms: syns, loading: false } : null)
    } catch (err: any) {
      setSynonymPopup(p => p ? { ...p, error: err?.message || 'Xatolik', loading: false } : null)
    }
  }, [])

  if (!text || text.length === 0) return null

  return (
    <div style={{ position: 'relative' }}>
      {/* Sentence-level errors (banner) */}
      {sentenceErrors.length > 0 && (
        <div style={{
          marginBottom: 10, padding: '8px 12px', borderRadius: 8,
          background: '#EDE9FE', border: '1px solid #C4B5FD', fontSize: '.78rem', color: '#5B21B6',
        }}>
          ⚠ <strong>Синтаксис огоҳлантиришлари ({sentenceErrors.length})</strong>
          <div style={{ marginTop: 4, fontSize: '.74rem' }}>
            {sentenceErrors.slice(0, 3).map((e, i) => (
              <div key={i}>• {e.message || e.suggestion}</div>
            ))}
            {sentenceErrors.length > 3 && <div>+ yana {sentenceErrors.length - 3} та…</div>}
          </div>
        </div>
      )}

      {/* Annotated text */}
      <div
        onClick={handleClickNormal}
        onDoubleClick={handleClickNormal}
        style={{
          padding: '14px 18px', borderRadius: 10,
          background: '#FFFBF5', border: '1px solid #FDE3C5',
          fontSize: '.92rem', lineHeight: 1.8, whiteSpace: 'pre-wrap',
          fontFamily: 'Georgia, serif',
          cursor: 'text', userSelect: 'text',
          maxHeight: 400, overflowY: 'auto',
        }}
      >
        {segments.map((seg, i) => {
          if (seg.overlaps.length === 0) {
            return <span key={i}>{seg.text}</span>
          }
          // Use first layer's color (dominant)
          const primary = seg.overlaps[0]
          const color = LAYER_COLORS[primary.layer] || LAYER_COLORS.sayqallash
          return (
            <span
              key={i}
              onClick={(e) => handleClickHighlight(e, seg.overlaps)}
              style={{
                background: color.bg,
                borderBottom: `2px wavy ${color.under}`,
                textDecoration: `underline wavy ${color.under}`,
                textDecorationThickness: 2,
                cursor: 'pointer',
                padding: '1px 2px',
                borderRadius: 2,
              }}
              title={`${color.label}: ${primary.issue.message || primary.issue.description || primary.issue.new_value || '(изoh)'}`}
            >
              {seg.text}
            </span>
          )
        })}
      </div>

      {/* Error tooltip */}
      {tooltip && (
        <>
          <div onClick={() => setTooltip(null)} style={{ position: 'fixed', inset: 0, zIndex: 9998 }} />
          <div style={{
            position: 'fixed',
            left: Math.min(tooltip.x, window.innerWidth - 360),
            top: Math.min(tooltip.y, window.innerHeight - 320),
            width: 340, background: 'white',
            border: '1.5px solid #B48C64', borderRadius: 12,
            boxShadow: '0 20px 50px rgba(0,0,0,.25)', zIndex: 9999,
            overflow: 'hidden', maxHeight: 320,
          }}>
            <div style={{ padding: '10px 14px', background: 'linear-gradient(135deg, #8B5E3C, #6F4924)', color: 'white', display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: '.78rem', fontWeight: 800, textTransform: 'uppercase' }}>
                ⚠ {tooltip.spans.length} та хато
              </span>
              <button onClick={() => setTooltip(null)} style={{ marginLeft: 'auto', background: 'transparent', border: 'none', color: 'white', cursor: 'pointer', padding: 2 }}>
                <X size={14} />
              </button>
            </div>
            <div style={{ padding: 10, maxHeight: 260, overflowY: 'auto' }}>
              {tooltip.spans.map((span, i) => {
                const color = LAYER_COLORS[span.layer]
                const iss = span.issue
                const oldVal = iss.old || iss.old_value || ''
                const newVal = iss.new || iss.new_value || iss.suggestion || ''
                return (
                  <div key={i} style={{
                    padding: '8px 10px', marginBottom: 6, borderLeft: `3px solid ${color.under}`,
                    background: '#FAFBFC', borderRadius: 4,
                  }}>
                    <div style={{ fontSize: '.64rem', fontWeight: 800, color: color.under, textTransform: 'uppercase', letterSpacing: '.04em' }}>
                      {color.label}
                      {iss.severity && <span style={{ marginLeft: 6, padding: '1px 6px', borderRadius: 8, background: color.bg }}>{iss.severity.toUpperCase()}</span>}
                    </div>
                    {iss.description && (
                      <div style={{ fontSize: '.78rem', color: '#1E293B', marginTop: 3, fontWeight: 600 }}>
                        {iss.description}
                      </div>
                    )}
                    {oldVal && (
                      <div style={{ marginTop: 4, fontFamily: 'monospace', fontSize: '.76rem' }}>
                        <span style={{ color: '#991B1B', textDecoration: 'line-through' }}>{oldVal}</span>
                        {newVal && (
                          <>
                            <span style={{ margin: '0 6px' }}>→</span>
                            <span style={{ color: '#15803D', fontWeight: 700 }}>{newVal}</span>
                          </>
                        )}
                      </div>
                    )}
                    {iss.error_type && (
                      <div style={{ fontSize: '.64rem', color: '#94A3B8', marginTop: 3 }}>
                        Тур: {iss.error_type}
                        {iss.confidence !== undefined && ` · Ишoнч: ${iss.confidence}%`}
                      </div>
                    )}
                    {iss.source_ref && (
                      <div style={{ fontSize: '.64rem', color: '#64748B', marginTop: 2 }}>
                        Манба: {iss.source_ref}
                        {iss.source_url && (
                          <> · <a href={iss.source_url} target="_blank" rel="noreferrer" style={{ color: '#2563EB' }}>🔗</a></>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        </>
      )}

      {/* Synonym popup */}
      {synonymPopup && (
        <>
          <div onClick={() => setSynonymPopup(null)} style={{ position: 'fixed', inset: 0, zIndex: 9998 }} />
          <div style={{
            position: 'fixed',
            left: Math.min(synonymPopup.x + 8, window.innerWidth - 320),
            top: Math.min(synonymPopup.y + 8, window.innerHeight - 280),
            width: 300, background: 'white',
            border: '1.5px solid #6366F1', borderRadius: 12,
            boxShadow: '0 20px 50px rgba(0,0,0,.25)', zIndex: 9999,
            overflow: 'hidden', maxHeight: 280,
            display: 'flex', flexDirection: 'column',
          }}>
            <div style={{ padding: '10px 14px', background: 'linear-gradient(135deg, #6366F1, #4F46E5)', color: 'white', display: 'flex', alignItems: 'center', gap: 8 }}>
              <Search size={14} />
              <span style={{ fontSize: '.72rem', fontWeight: 800, textTransform: 'uppercase' }}>Синонимлар</span>
              <div style={{ marginLeft: 'auto', padding: '2px 8px', background: 'rgba(255,255,255,.2)', borderRadius: 10, fontSize: '.7rem', fontWeight: 700 }}>
                {synonymPopup.word}
              </div>
              <button onClick={() => setSynonymPopup(null)} style={{ background: 'transparent', border: 'none', color: 'white', cursor: 'pointer', padding: 0 }}>
                <X size={14} />
              </button>
            </div>
            <div style={{ flex: 1, overflowY: 'auto', padding: 10 }}>
              {synonymPopup.loading ? (
                <div style={{ textAlign: 'center', padding: 20, color: '#94A3B8' }}>
                  <Loader2 className="animate-spin" size={22} />
                </div>
              ) : synonymPopup.error ? (
                <div style={{ textAlign: 'center', padding: 16, color: '#DC2626', fontSize: '.76rem' }}>⚠ {synonymPopup.error}</div>
              ) : synonymPopup.synonyms.length === 0 ? (
                <div style={{ textAlign: 'center', padding: 20, color: '#94A3B8', fontSize: '.76rem' }}>
                  Синонимлар базасида топилмади
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  {synonymPopup.synonyms.slice(0, 15).map((s, i) => (
                    <div
                      key={i}
                      onClick={() => { navigator.clipboard?.writeText(s.word).catch(() => {}); setSynonymPopup(null) }}
                      style={{
                        padding: '7px 10px', borderRadius: 6, background: '#F5F3FF',
                        fontSize: '.82rem', fontWeight: 600, color: '#4338CA',
                        cursor: 'pointer', display: 'flex', justifyContent: 'space-between',
                        border: '1px solid transparent',
                      }}
                      onMouseEnter={e => { e.currentTarget.style.background = '#E0E7FF'; e.currentTarget.style.borderColor = '#6366F1' }}
                      onMouseLeave={e => { e.currentTarget.style.background = '#F5F3FF'; e.currentTarget.style.borderColor = 'transparent' }}
                    >
                      <span>{s.word}</span>
                      {s.frequency && <span style={{ fontSize: '.6rem', color: '#7C3AED', fontWeight: 800 }}>×{s.frequency}</span>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
