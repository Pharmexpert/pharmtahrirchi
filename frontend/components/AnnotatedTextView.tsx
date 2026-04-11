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
import React, { useState, useMemo, useCallback, useEffect, useRef } from 'react'
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
  onTextChange?: (newText: string) => void
}

interface Span {
  start: number
  end: number
  layer: 'sayqallash' | 'syntax' | 'style' | 'morph'
  issue: AnalysisIssue
}

const LAYER_COLORS: Record<string, { under: string; bg: string; label: string }> = {
  sayqallash: { under: '#DC2626', bg: '#FEE2E2', label: 'Сайқаллаш' },
  syntax:     { under: '#7C3AED', bg: '#EDE9FE', label: 'Синтаксис' },
  style:      { under: '#DB2777', bg: '#FCE7F3', label: 'Стиль' },
  morph:      { under: '#0EA5E9', bg: '#E0F2FE', label: 'Морфология' },
}

export default function AnnotatedTextView({ text, result, onTextChange }: Props) {
  const [tooltip, setTooltip] = useState<{ x: number; y: number; spans: Span[] } | null>(null)
  const [synonymPopup, setSynonymPopup] = useState<{ x: number; y: number; word: string; loading: boolean; synonyms: any[]; error: string | null } | null>(null)
  const [dragOffset, setDragOffset] = useState<{ dx: number; dy: number }>({ dx: 0, dy: 0 })
  const isDragging = useRef(false)
  const dragStart = useRef<{ mx: number; my: number; dx: number; dy: number }>({ mx: 0, my: 0, dx: 0, dy: 0 })

  // Reset drag offset when tooltip changes
  useEffect(() => { setDragOffset({ dx: 0, dy: 0 }) }, [tooltip])

  // Global mousemove/mouseup for dragging tooltip
  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!isDragging.current) return
      const newDx = dragStart.current.dx + (e.clientX - dragStart.current.mx)
      const newDy = dragStart.current.dy + (e.clientY - dragStart.current.my)
      setDragOffset({ dx: newDx, dy: newDy })
    }
    const onMouseUp = () => { isDragging.current = false }
    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)
    return () => {
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
    }
  }, [])

  // Collect all positional errors into spans (merge overlaps)
  const spans = useMemo<Span[]>(() => {
    if (!result) return []
    const out: Span[] = []
    // Priority order: sayqallash (red) > style (pink) > morph (blue) > syntax (purple)
    const covered = new Set<string>()
    for (const layer of ['sayqallash', 'style', 'morph', 'syntax'] as const) {
      const items = (result as any)[layer] as AnalysisIssue[] | undefined
      if (!items) continue
      for (const issue of items) {
        // Morph: only UNKNOWN words
        if (layer === 'morph' && !(issue as any).is_unknown) continue
        const start = typeof issue.from === 'number' ? issue.from
                    : typeof issue.from_index === 'number' ? issue.from_index : -1
        const end = typeof issue.to === 'number' ? issue.to
                  : typeof issue.to_index === 'number' ? issue.to_index : -1
        if (start < 0 || end <= start || end > text.length) continue
        // Skip if this range already covered by higher-priority layer
        const key = `${start}-${end}`
        if (covered.has(key)) continue
        covered.add(key)
        out.push({ start, end, layer, issue })
      }
    }
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
      {/* Sentence-level syntax banner removed — was duplicating info */}

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
            left: Math.min(tooltip.x, window.innerWidth - 360) + dragOffset.dx,
            top: Math.min(tooltip.y, window.innerHeight - 320) + dragOffset.dy,
            width: 340, background: 'white',
            border: '1.5px solid #B48C64', borderRadius: 12,
            boxShadow: '0 20px 50px rgba(0,0,0,.25)', zIndex: 9999,
            overflow: 'hidden', maxHeight: 320,
          }}>
            <div
              onMouseDown={(e) => {
                e.preventDefault()
                isDragging.current = true
                dragStart.current = { mx: e.clientX, my: e.clientY, dx: dragOffset.dx, dy: dragOffset.dy }
              }}
              style={{ padding: '10px 14px', background: 'linear-gradient(135deg, #8B5E3C, #6F4924)', color: 'white', display: 'flex', alignItems: 'center', gap: 8, cursor: 'grab', userSelect: 'none' }}>
              <span style={{ fontSize: '.78rem', fontWeight: 800, textTransform: 'uppercase' }}>
                ⚠ {tooltip.spans.length} та хато
              </span>
              <button onClick={() => setTooltip(null)} style={{ marginLeft: 'auto', background: 'transparent', border: 'none', color: 'white', cursor: 'pointer', padding: 2 }}>
                <X size={14} />
              </button>
            </div>
            <div style={{ padding: 10, maxHeight: 320, overflowY: 'auto' }}>
              {tooltip.spans.map((span, i) => {
                const color = LAYER_COLORS[span.layer] || LAYER_COLORS.sayqallash
                const iss = span.issue
                const oldVal = iss.old || iss.old_value || ''
                const newVal = iss.new || iss.new_value || iss.suggestion || ''
                // Collect all suggestions for tilmoch.ai-style list
                const allSuggestions: string[] = []
                if (newVal && !newVal.startsWith('[')) allSuggestions.push(newVal)
                if ((iss as any).suggestions) {
                  for (const s of (iss as any).suggestions) {
                    if (s && !allSuggestions.includes(s) && !s.startsWith('[')) allSuggestions.push(s)
                  }
                }
                // Apply suggestion — replace in text
                const applySuggestion = (suggestion: string) => {
                  if (!onTextChange) return
                  const from = span.start
                  const to = span.end
                  const newText = text.substring(0, from) + suggestion + text.substring(to)
                  onTextChange(newText)
                  setTooltip(null)
                }
                return (
                  <div key={i} style={{
                    padding: '8px 10px', marginBottom: 6, borderLeft: `3px solid ${color.under}`,
                    background: '#FAFBFC', borderRadius: 4,
                  }}>
                    {/* Error type label */}
                    <div style={{ fontSize: '.6rem', fontWeight: 700, color: '#94A3B8', textTransform: 'uppercase', marginBottom: 4 }}>
                      {iss.error_type || color.label}
                      {iss.confidence !== undefined && ` · ${iss.confidence}%`}
                      {(iss as any).source && <span style={{ marginLeft: 4 }}>({(iss as any).source})</span>}
                    </div>
                    {/* Suggestion list — tilmoch.ai style */}
                    {allSuggestions.length > 0 ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                        {allSuggestions.map((sug, si) => (
                          <div key={si}
                            onClick={() => applySuggestion(sug)}
                            style={{
                              display: 'flex', alignItems: 'center', gap: 6,
                              padding: '5px 8px', borderRadius: 6,
                              cursor: onTextChange ? 'pointer' : 'default',
                              background: si === 0 ? '#F0FDF4' : 'white',
                              border: `1px solid ${si === 0 ? '#86EFAC' : '#E5E7EB'}`,
                              transition: 'background .1s',
                            }}
                            onMouseEnter={e => (e.currentTarget.style.background = '#DCFCE7')}
                            onMouseLeave={e => (e.currentTarget.style.background = si === 0 ? '#F0FDF4' : 'white')}
                          >
                            <span style={{ color: '#16A34A', fontSize: '.72rem' }}>→</span>
                            <span style={{ fontWeight: si === 0 ? 700 : 500, fontSize: '.82rem', color: '#1E293B' }}>{sug}</span>
                            {si === 0 && <span style={{ fontSize: '.58rem', color: '#16A34A', marginLeft: 'auto' }}>тавсия</span>}
                          </div>
                        ))}
                      </div>
                    ) : (
                      /* No suggestion — show error info */
                      <div style={{ fontSize: '.76rem', color: '#DC2626' }}>
                        {(iss as any).message || `"${oldVal}" — тузатиш таклифи йўқ`}
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
