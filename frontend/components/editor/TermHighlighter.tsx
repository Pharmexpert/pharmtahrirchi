'use client'

import React, { useState } from 'react'

interface Term {
  id: number
  type: 'annotated' | 'disputed' | 'abbreviation'
  match: string
  en: string; ru: string; uz: string
  detail_en?: string; detail_ru?: string; detail_uz?: string
}

interface Props {
  text: string
  terms: Term[]
}

const COLORS = {
  annotated: { bg: '#E0E7FF', border: '#6366F1', text: '#4338CA', label: 'Изоҳли' },
  disputed: { bg: '#FEE2E2', border: '#EF4444', text: '#DC2626', label: 'Мунозарали' },
  abbreviation: { bg: '#DCFCE7', border: '#22C55E', text: '#16A34A', label: 'Қисқартма' },
}

export default function TermHighlighter({ text, terms }: Props) {
  const [tooltip, setTooltip] = useState<{ term: Term; x: number; y: number } | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 })

  if (!text || terms.length === 0) return <>{text}</>

  // Build segments: find all term matches in text
  const segments: Array<{ text: string; term?: Term }> = []
  let remaining = text
  let offset = 0

  // Sort terms by length (longest first) to prevent partial matches
  const sorted = [...terms].sort((a, b) => b.match.length - a.match.length)

  // Find all matches with positions
  const matches: Array<{ start: number; end: number; term: Term }> = []
  for (const term of sorted) {
    const regex = new RegExp(term.match.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi')
    let m
    while ((m = regex.exec(text)) !== null) {
      // Check no overlap with existing matches
      const overlaps = matches.some(e => !(m!.index >= e.end || m!.index + m![0].length <= e.start))
      if (!overlaps) {
        matches.push({ start: m.index, end: m.index + m[0].length, term })
      }
    }
  }

  matches.sort((a, b) => a.start - b.start)

  let pos = 0
  for (const m of matches) {
    if (m.start > pos) {
      segments.push({ text: text.slice(pos, m.start) })
    }
    segments.push({ text: text.slice(m.start, m.end), term: m.term })
    pos = m.end
  }
  if (pos < text.length) {
    segments.push({ text: text.slice(pos) })
  }

  return (
    <span style={{ position: 'relative' }}>
      {segments.map((seg, i) => {
        if (!seg.term) return <span key={i}>{seg.text}</span>
        const c = COLORS[seg.term.type]
        return (
          <span key={i}
            style={{
              background: c.bg, borderBottom: `2px solid ${c.border}`,
              padding: '1px 2px', borderRadius: '3px', cursor: 'pointer',
              color: c.text, fontWeight: 600
            }}
            onClick={e => {
              const rect = (e.target as HTMLElement).getBoundingClientRect()
              setTooltip(tooltip?.term.id === seg.term!.id ? null : { term: seg.term!, x: rect.left, y: rect.bottom + 4 })
            }}
            title={`${c.label}: ${seg.text}`}
          >
            {seg.text}
          </span>
        )
      })}

      {tooltip && (
        <div
          onMouseDown={e => {
            setIsDragging(true)
            const el = e.currentTarget.getBoundingClientRect()
            setDragOffset({ x: e.clientX - el.left, y: e.clientY - el.top })
          }}
          onMouseMove={e => {
            if (isDragging) setTooltip(t => t ? { ...t, x: e.clientX - dragOffset.x, y: e.clientY - dragOffset.y } : null)
          }}
          onMouseUp={() => setIsDragging(false)}
          onMouseLeave={() => setIsDragging(false)}
          style={{
            position: 'fixed', left: tooltip.x, top: tooltip.y,
            width: '380px', background: 'white', borderRadius: '14px', padding: '18px',
            boxShadow: '0 12px 48px rgba(0,0,0,0.25)', border: `2px solid ${COLORS[tooltip.term.type].border}`,
            zIndex: 9999, fontSize: '0.82rem', lineHeight: '1.6',
            cursor: isDragging ? 'grabbing' : 'grab', userSelect: 'none'
          }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <span style={{
              padding: '3px 10px', borderRadius: '8px', fontSize: '0.7rem', fontWeight: 700,
              background: COLORS[tooltip.term.type].bg, color: COLORS[tooltip.term.type].text
            }}>{COLORS[tooltip.term.type].label}</span>
            <span style={{ fontSize: '0.65rem', color: '#94A3B8' }}>суриш учун тортинг</span>
            <span onClick={() => setTooltip(null)} style={{ cursor: 'pointer', fontSize: '1.1rem', opacity: 0.5, lineHeight: 1 }}>✕</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div><span style={{ fontWeight: 700, color: '#9333EA' }}>🇬🇧 EN:</span> {tooltip.term.en}</div>
            <div><span style={{ fontWeight: 700, color: '#2563EB' }}>🇷🇺 RU:</span> {tooltip.term.ru}</div>
            <div><span style={{ fontWeight: 700, color: '#16A34A' }}>🇺🇿 UZ:</span> {tooltip.term.uz}</div>
          </div>

          {(tooltip.term.detail_en || tooltip.term.detail_ru || tooltip.term.detail_uz) && (
            <div style={{ marginTop: '10px', borderTop: '1px solid #E2E8F0', paddingTop: '10px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#64748B', textTransform: 'uppercase' }}>Таъриф / Контекст</div>
              {tooltip.term.detail_en && (
                <div style={{ padding: '6px 8px', background: '#F5F3FF', borderRadius: '6px', fontSize: '0.76rem', color: '#4338CA', lineHeight: '1.5' }}>
                  <strong>EN:</strong> {tooltip.term.detail_en}
                </div>
              )}
              {tooltip.term.detail_ru && (
                <div style={{ padding: '6px 8px', background: '#EFF6FF', borderRadius: '6px', fontSize: '0.76rem', color: '#1E40AF', lineHeight: '1.5' }}>
                  <strong>RU:</strong> {tooltip.term.detail_ru}
                </div>
              )}
              {tooltip.term.detail_uz && (
                <div style={{ padding: '6px 8px', background: '#F0FDF4', borderRadius: '6px', fontSize: '0.76rem', color: '#166534', lineHeight: '1.5' }}>
                  <strong>UZ:</strong> {tooltip.term.detail_uz}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </span>
  )
}

export type { Term }
