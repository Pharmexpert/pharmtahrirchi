import React, { useState } from 'react'
import { Sparkles, Loader2 } from 'lucide-react'

export default function LangCell({ v1, proposed, rowIdx, lang, isMarker, isImproving, onV1Change, onProposedChange, onImprove, onWordClick, onBlockDrop, token, contextEn, contextRu, contextUz }: {
  v1: string; proposed: string; rowIdx: number; lang: 'ru' | 'uz'; isMarker: boolean
  isImproving: boolean
  onV1Change: (v: string) => void
  onProposedChange: (v: string) => void
  onImprove: () => void
  onWordClick: (e: React.MouseEvent<HTMLTextAreaElement>, idx: number, lang: 'ru' | 'uz') => void
  onBlockDrop?: (fromRow: number, fromField: string, toRow: number, toField: string) => void
  token?: string
  contextEn?: string; contextRu?: string; contextUz?: string
}) {
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const [dragOverField, setDragOverField] = useState<string | null>(null)
  const [annotations, setAnnotations] = useState<any[]>([])
  const [isSayqallash, setIsSayqallash] = useState(false)
  const [showAnnotations, setShowAnnotations] = useState(false)
  const [rulesCount, setRulesCount] = useState(0)

  const handleBlockDragStart = (e: React.DragEvent, field: string) => {
    e.dataTransfer.setData('text/plain', JSON.stringify({ rowIdx, lang, field }))
    e.dataTransfer.effectAllowed = 'move'
  }

  const handleBlockDragOver = (e: React.DragEvent, field: string) => {
    e.preventDefault(); e.dataTransfer.dropEffect = 'move'; setDragOverField(field)
  }
  const handleBlockDragLeave = () => setDragOverField(null)

  const handleBlockDropLocal = (e: React.DragEvent, toField: string) => {
    e.preventDefault()
    setDragOverField(null)
    try {
      const from = JSON.parse(e.dataTransfer.getData('text/plain'))
      if (onBlockDrop && (from.rowIdx !== rowIdx || from.field !== toField)) {
        onBlockDrop(from.rowIdx, `${from.lang}_${from.field}`, rowIdx, `${lang}_${toField}`)
      }
    } catch (_e) {}
  }

  const runSayqallash = async () => {
    const text = proposed || v1 || ''
    if (!text.trim()) return
    setIsSayqallash(true)
    try {
      const res = await fetch(`${API_BASE}/sayqallash`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ text, lang, context_en: contextEn || '', context_ru: contextRu || '', context_uz: contextUz || '' })
      })
      if (!res.ok) throw new Error()
      const r = await res.json()
      setAnnotations(r.annotations || [])
      setShowAnnotations(true)
      setRulesCount(r.rules_count || 0)
    } catch (_e) { setAnnotations([]) }
    finally { setIsSayqallash(false) }
  }

  const acceptAnnotation = (idx: number) => {
    const ann = annotations[idx]
    const text = proposed || v1 || ''
    const newText = text.substring(0, ann.from_index) + ann.new_value + text.substring(ann.to_index)
    onProposedChange(newText)
    const diff = ann.new_value.length - ann.old_value.length
    const remaining = annotations.filter((_, i) => i !== idx).map(a => {
      if (a.from_index > ann.from_index) {
        return { ...a, from_index: a.from_index + diff, to_index: a.to_index + diff }
      }
      return a
    })
    setAnnotations(remaining)
    if (remaining.length === 0) setShowAnnotations(false)
  }

  const rejectAnnotation = (idx: number) => {
    const remaining = annotations.filter((_, i) => i !== idx)
    setAnnotations(remaining)
    if (remaining.length === 0) setShowAnnotations(false)
  }

  const acceptAll = () => {
    let text = proposed || v1 || ''
    const sorted = [...annotations].sort((a, b) => b.from_index - a.from_index)
    for (const ann of sorted) {
      text = text.substring(0, ann.from_index) + ann.new_value + text.substring(ann.to_index)
    }
    onProposedChange(text)
    setAnnotations([])
    setShowAnnotations(false)
  }

  const dragHandleStyle: React.CSSProperties = {
    cursor: 'grab', fontSize: '0.7rem', color: '#cbd5e1', userSelect: 'none',
    padding: '0 3px', lineHeight: 1, flexShrink: 0
  }

  const renderAnnotatedText = () => {
    const text = proposed || v1 || ''
    if (!annotations.length) return null

    const parts: React.ReactNode[] = []
    let lastIdx = 0
    const sorted = [...annotations].sort((a, b) => a.from_index - b.from_index)

    sorted.forEach((ann, i) => {
      if (ann.from_index > lastIdx) {
        parts.push(<span key={`t${i}`} style={{ fontSize: '0.78rem', lineHeight: 1.5 }}>{text.slice(lastIdx, ann.from_index)}</span>)
      }
      parts.push(
        <span key={`a${i}`} style={{ display: 'inline', position: 'relative' }}>
          <span style={{
            color: '#ef4444', textDecoration: 'line-through', fontSize: '0.78rem',
            background: '#fef2f2', padding: '0 2px', borderRadius: 2
          }}>{ann.old_value}</span>
          <span style={{
            color: '#16a34a', fontWeight: 700, fontSize: '0.78rem',
            background: '#f0fdf4', padding: '0 2px', borderRadius: 2
          }}>{ann.new_value}</span>
          <span style={{ display: 'inline-flex', gap: 1, marginLeft: 2, verticalAlign: 'middle' }}>
            <button onClick={() => acceptAnnotation(i)} title="Қабул қилиш"
              style={{ background: '#dcfce7', border: '1px solid #86efac', borderRadius: 3, padding: '0 3px', cursor: 'pointer', fontSize: '0.6rem', color: '#16a34a', lineHeight: '14px' }}>✓</button>
            <button onClick={() => rejectAnnotation(i)} title="Рад этиш"
              style={{ background: '#fef2f2', border: '1px solid #fca5a5', borderRadius: 3, padding: '0 3px', cursor: 'pointer', fontSize: '0.6rem', color: '#ef4444', lineHeight: '14px' }}>✕</button>
          </span>
          <span style={{ fontSize: '0.5rem', color: '#8b5cf6', background: '#f5f3ff', padding: '0 3px', borderRadius: 8, marginLeft: 2, fontWeight: 600, verticalAlign: 'middle' }}>{ann.error_type}</span>
          {ann.source === 'rules_db' && <span style={{ fontSize: '0.5rem', color: '#0891b2', background: '#ecfeff', padding: '0 3px', borderRadius: 8, marginLeft: 1, verticalAlign: 'middle' }}>📚 DB</span>}
          {ann.source === 'ai' && <span style={{ fontSize: '0.5rem', color: '#7c3aed', background: '#f5f3ff', padding: '0 3px', borderRadius: 8, marginLeft: 1, verticalAlign: 'middle' }}>🤖 AI</span>}
        </span>
      )
      lastIdx = ann.to_index
    })
    if (lastIdx < text.length) {
      parts.push(<span key="end" style={{ fontSize: '0.78rem', lineHeight: 1.5 }}>{text.slice(lastIdx)}</span>)
    }
    return parts
  }

  return (
    <td style={{ padding: '7px 8px', verticalAlign: 'top', borderRight: '1px solid #e9edf2' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {/* V1: Original Block */}
        <div
          draggable
          onDragStart={e => handleBlockDragStart(e, 'v1')}
          onDragOver={e => handleBlockDragOver(e, 'v1')}
          onDragLeave={handleBlockDragLeave}
          onDrop={e => handleBlockDropLocal(e, 'v1')}
          style={{
            border: dragOverField === 'v1' ? '2px dashed #3b82f6' : '1px solid #e9edf2',
            borderRadius: 5, padding: 4, background: dragOverField === 'v1' ? '#eff6ff' : '#f8fafc',
            transition: 'border .15s, background .15s'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 3 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span draggable onDragStart={e => handleBlockDragStart(e, 'v1')} style={dragHandleStyle} title="Ушлаб суринг">⠿</span>
              <span style={{ fontSize: '0.55rem', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                V1: Original
              </span>
            </div>
            {lang === 'uz' && !isMarker && (
              <div style={{ display: 'flex', gap: 6 }}>
                <button disabled={!v1} onClick={async () => {
                  try {
                    const res = await fetch(`${API_BASE}/api/transliterate`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: v1, target: 'cyrillic' }) })
                    if (res.ok) { const r = await res.json(); onV1Change(r.text) }
                  } catch {}
                }} style={{ padding: '2px 8px', borderRadius: 4, border: '1.5px solid #FB923C', background: '#FFF7ED', color: '#EA580C', fontSize: '0.6rem', fontWeight: 800, cursor: v1 ? 'pointer' : 'not-allowed', opacity: v1 ? 1 : 0.5, letterSpacing: '0.02em' }}>Кирил</button>
                <button disabled={!v1} onClick={async () => {
                  try {
                    const res = await fetch(`${API_BASE}/api/transliterate`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: v1, target: 'latin' }) })
                    if (res.ok) { const r = await res.json(); onV1Change(r.text) }
                  } catch {}
                }} style={{ padding: '2px 8px', borderRadius: 4, border: '1.5px solid #22C55E', background: '#F0FDF4', color: '#16A34A', fontSize: '0.6rem', fontWeight: 800, cursor: v1 ? 'pointer' : 'not-allowed', opacity: v1 ? 1 : 0.5, letterSpacing: '0.02em' }}>Лотин</button>
              </div>
            )}
          </div>
          <textarea value={v1 || ''} onChange={e => onV1Change(e.target.value)}
            onClick={e => onWordClick(e as any, rowIdx, lang)}
            placeholder="V1 original..."
            style={{ width: '100%', minHeight: 40, fontSize: '0.78rem', color: '#475569', background: 'transparent', border: 'none', padding: '2px 4px', lineHeight: 1.45, resize: 'vertical', outline: 'none', fontFamily: 'inherit', boxSizing: 'border-box' }}
          />
        </div>

        {/* Proposed / Confirmed Block */}
        <div
          draggable
          onDragStart={e => handleBlockDragStart(e, 'proposed')}
          onDragOver={e => handleBlockDragOver(e, 'proposed')}
          onDragLeave={handleBlockDragLeave}
          onDrop={e => handleBlockDropLocal(e, 'proposed')}
          style={{
            border: dragOverField === 'proposed' ? '2px dashed #22c55e' : '1.5px solid #bfdbfe',
            borderRadius: 5, padding: 4, background: dragOverField === 'proposed' ? '#f0fdf4' : 'white',
            transition: 'border .15s, background .15s'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 3, flexWrap: 'wrap', gap: 3 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span draggable onDragStart={e => handleBlockDragStart(e, 'proposed')} style={dragHandleStyle} title="Ушлаб суринг">⠿</span>
              <span style={{ fontSize: '0.55rem', fontWeight: 700, color: '#3b82f6', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Proposed / Confirmed</span>
            </div>
            <div style={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
              {!isMarker && (
                <button onClick={onImprove} disabled={isImproving}
                  style={{ display: 'flex', alignItems: 'center', gap: 3, background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', color: 'white', border: 'none', borderRadius: 4, padding: '2px 7px', fontSize: '0.65rem', fontWeight: 700, cursor: isImproving ? 'not-allowed' : 'pointer', whiteSpace: 'nowrap' }}>
                  {isImproving
                    ? <><Loader2 size={10} style={{ animation: 'spin .8s linear infinite' }} /> AI...</>
                    : <><Sparkles size={10} /> AI Yaxshilash</>}
                </button>
              )}
              {lang === 'uz' && !isMarker && (
                <>
                  <button onClick={runSayqallash} disabled={isSayqallash}
                    style={{ display: 'flex', alignItems: 'center', gap: 3, background: 'linear-gradient(135deg,#059669,#10b981)', color: 'white', border: 'none', borderRadius: 4, padding: '2px 7px', fontSize: '0.65rem', fontWeight: 700, cursor: isSayqallash ? 'not-allowed' : 'pointer', whiteSpace: 'nowrap' }}>
                    {isSayqallash
                      ? <><Loader2 size={10} style={{ animation: 'spin .8s linear infinite' }} /> Tekshirilmoqda...</>
                      : <>✦ Sayqallash</>}
                  </button>
                  {(proposed || v1) && (
                    <div style={{ display: 'flex', gap: 6, marginLeft: 4 }}>
                      <button onClick={async () => {
                        try {
                          const text = proposed || v1 || ''
                          const res = await fetch(`${API_BASE}/api/transliterate`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text, target: 'cyrillic' }) })
                          if (res.ok) { const r = await res.json(); onProposedChange(r.text) }
                        } catch {}
                      }} style={{ padding: '2px 8px', borderRadius: 4, border: '1.5px solid #FB923C', background: '#FFF7ED', color: '#EA580C', fontSize: '0.6rem', fontWeight: 800, cursor: 'pointer', whiteSpace: 'nowrap', letterSpacing: '0.02em' }}>Кирил</button>
                      <button onClick={async () => {
                        try {
                          const text = proposed || v1 || ''
                          const res = await fetch(`${API_BASE}/api/transliterate`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text, target: 'latin' }) })
                          if (res.ok) { const r = await res.json(); onProposedChange(r.text) }
                        } catch {}
                      }} style={{ padding: '2px 8px', borderRadius: 4, border: '1.5px solid #22C55E', background: '#F0FDF4', color: '#16A34A', fontSize: '0.6rem', fontWeight: 800, cursor: 'pointer', whiteSpace: 'nowrap', letterSpacing: '0.02em' }}>Лотин</button>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>

          {/* Annotation visualization */}
          {showAnnotations && annotations.length > 0 && (
            <div style={{ marginBottom: 4 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ fontSize: '0.55rem', fontWeight: 700, color: '#8b5cf6', textTransform: 'uppercase' }}>
                  {annotations.length} та хато топилди {rulesCount > 0 && <span style={{ fontSize: '0.5rem', color: '#0891b2', fontWeight: 600 }}>| 📚 {rulesCount} қоида</span>}
                </span>
                <div style={{ display: 'flex', gap: 3 }}>
                  <button onClick={acceptAll}
                    style={{ display: 'flex', alignItems: 'center', gap: 2, background: '#dcfce7', color: '#16a34a', border: '1px solid #86efac', borderRadius: 4, padding: '1px 6px', fontSize: '0.6rem', fontWeight: 700, cursor: 'pointer' }}>
                    ✓ Ҳаммасини қабул қилиш
                  </button>
                  <button onClick={() => { setAnnotations([]); setShowAnnotations(false) }}
                    style={{ background: '#fef2f2', color: '#ef4444', border: '1px solid #fca5a5', borderRadius: 4, padding: '1px 6px', fontSize: '0.6rem', fontWeight: 700, cursor: 'pointer' }}>
                    ✕ Ёпиш
                  </button>
                </div>
              </div>
              <div style={{
                background: '#fafbff', border: '1px solid #e5e7eb', borderRadius: 5,
                padding: '6px 8px', lineHeight: 1.8, wordBreak: 'break-word'
              }}>
                {renderAnnotatedText()}
              </div>
            </div>
          )}

          <textarea value={proposed || ''} onChange={e => onProposedChange(e.target.value)}
            onClick={e => onWordClick(e as any, rowIdx, lang)} placeholder="Tasdiqlangan matn..."
            style={{ width: '100%', minHeight: 50, fontSize: '0.8rem', border: 'none', padding: '2px 4px', resize: 'vertical', outline: 'none', fontFamily: 'inherit', lineHeight: 1.45, boxSizing: 'border-box', background: 'transparent' }}
          />
        </div>
      </div>
    </td>
  )
}
