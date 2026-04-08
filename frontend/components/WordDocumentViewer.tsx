'use client'

import React, { useEffect, useRef, useState } from 'react'
import { Loader2, FileText, Upload, X, ZoomIn, ZoomOut, Printer, Sparkles } from 'lucide-react'

// docx-preview is SSR-unsafe (uses DOM), import only in effect
type RenderAsyncFn = (file: Blob | ArrayBuffer | Uint8Array, container: HTMLElement, styleContainer?: HTMLElement | null, options?: any) => Promise<any>

interface Props {
  file: File | null
  onTextExtracted?: (text: string) => void
  aiActions?: Array<{
    label: string
    icon?: React.ReactNode
    color?: string
    onClick: (selectedText: string, fullText: string) => void
  }>
}

export default function WordDocumentViewer({ file, onTextExtracted, aiActions = [] }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [zoom, setZoom] = useState(100)
  const [fullText, setFullText] = useState('')
  const [selectedText, setSelectedText] = useState('')

  useEffect(() => {
    if (!file || !containerRef.current) return
    let cancelled = false

    const render = async () => {
      setLoading(true)
      setError(null)
      try {
        // Dynamic import (client-only)
        const { renderAsync } = await import('docx-preview') as { renderAsync: RenderAsyncFn }

        // Clear previous render
        const container = containerRef.current!
        container.innerHTML = ''

        await renderAsync(file, container, null, {
          className: 'docx-viewer',
          inWrapper: true,
          ignoreWidth: false,
          ignoreHeight: false,
          ignoreFonts: false,
          breakPages: true,
          ignoreLastRenderedPageBreak: true,
          experimental: true,
          trimXmlDeclaration: true,
          useBase64URL: false,
          renderChanges: false,
          renderHeaders: true,
          renderFooters: true,
          renderFootnotes: true,
          renderEndnotes: true,
          debug: false,
        })

        if (cancelled) return

        // Extract plain text for AI
        const text = (container.innerText || '').trim()
        setFullText(text)
        onTextExtracted?.(text)

        // Apply initial zoom
        container.style.transform = `scale(${zoom / 100})`
        container.style.transformOrigin = 'top left'
      } catch (err: any) {
        console.error('Word render error:', err)
        setError(err?.message || 'Word файлни рендеринг қилишда xato')
      } finally {
        setLoading(false)
      }
    }

    render()
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [file])

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.style.transform = `scale(${zoom / 100})`
      containerRef.current.style.transformOrigin = 'top left'
    }
  }, [zoom])

  const handleSelection = () => {
    const sel = window.getSelection()?.toString().trim() || ''
    setSelectedText(sel)
  }

  if (!file) {
    return (
      <div style={{
        padding: 60, textAlign: 'center', color: '#94A3B8',
        border: '2px dashed #E2E8F0', borderRadius: 14, background: '#F8FAFC'
      }}>
        <FileText size={56} style={{ opacity: 0.25, marginBottom: 16 }} />
        <div style={{ fontSize: '.9rem', fontWeight: 700 }}>Word файл юкланмаган</div>
        <div style={{ fontSize: '.78rem', marginTop: 6 }}>.docx файл юклаш учун юқоридаги тугмани босинг</div>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
      {/* Toolbar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
        padding: '10px 14px', background: '#1E293B', color: 'white', borderRadius: '12px 12px 0 0',
        position: 'sticky', top: 0, zIndex: 10,
      }}>
        <FileText size={16} color="#60A5FA" />
        <span style={{ fontSize: '.82rem', fontWeight: 700, maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{file.name}</span>

        <div style={{ marginLeft: 'auto', display: 'flex', gap: 6, alignItems: 'center' }}>
          <button onClick={() => setZoom(Math.max(50, zoom - 10))} style={tbBtn}><ZoomOut size={14} /></button>
          <span style={{ fontSize: '.74rem', minWidth: 40, textAlign: 'center', fontWeight: 700, color: '#CBD5E1' }}>{zoom}%</span>
          <button onClick={() => setZoom(Math.min(200, zoom + 10))} style={tbBtn}><ZoomIn size={14} /></button>
          <button onClick={() => window.print()} style={tbBtn} title="Чоп этиш"><Printer size={14} /></button>
        </div>
      </div>

      {/* AI Actions bar */}
      {aiActions.length > 0 && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap',
          padding: '10px 14px', background: '#F1F5F9', borderBottom: '1px solid #E2E8F0',
        }}>
          <span style={{ fontSize: '.68rem', fontWeight: 800, color: '#475569', textTransform: 'uppercase' }}>
            <Sparkles size={11} style={{ display: 'inline', verticalAlign: -1, marginRight: 4 }} />
            AI амаллар:
          </span>
          {aiActions.map((a, i) => (
            <button key={i} onClick={() => a.onClick(selectedText, fullText)} style={{
              padding: '6px 12px', borderRadius: 8, border: 'none',
              background: a.color || '#7C3AED', color: 'white', fontWeight: 700, fontSize: '.75rem',
              cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4,
            }}>
              {a.icon}{a.label}
            </button>
          ))}
          {selectedText && (
            <span style={{ marginLeft: 'auto', fontSize: '.72rem', color: '#64748B', fontStyle: 'italic' }}>
              📝 Танлаган: "{selectedText.slice(0, 40)}{selectedText.length > 40 ? '…' : ''}"
            </span>
          )}
        </div>
      )}

      {/* Content */}
      <div
        style={{
          background: '#E2E8F0', padding: 20, minHeight: 600,
          borderRadius: '0 0 12px 12px', overflow: 'auto', maxHeight: '75vh',
          position: 'relative',
        }}
        onMouseUp={handleSelection}
      >
        {loading && (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(226,232,240,0.9)', zIndex: 5 }}>
            <div style={{ textAlign: 'center' }}>
              <Loader2 className="animate-spin" size={36} color="#7C3AED" />
              <div style={{ fontSize: '.82rem', color: '#64748B', marginTop: 8, fontWeight: 600 }}>Word файл рендеринг қилинмоқда...</div>
            </div>
          </div>
        )}
        {error && (
          <div style={{
            padding: 30, background: '#FEE2E2', borderRadius: 12, color: '#991B1B',
            border: '1px solid #FECACA', textAlign: 'center'
          }}>
            <X size={36} style={{ marginBottom: 10 }} />
            <div style={{ fontWeight: 700, fontSize: '.9rem' }}>Xato: {error}</div>
            <div style={{ fontSize: '.75rem', marginTop: 8, opacity: 0.8 }}>
              Фақат .docx файллар қўллаб-қувватланади. Эски .doc файлларни олдин .docx форматига конверт қилинг.
            </div>
          </div>
        )}
        <div ref={containerRef} style={{ transition: 'transform 0.2s', margin: '0 auto' }} />
      </div>

      {/* Embedded stylesheet for docx-preview output */}
      <style jsx global>{`
        .docx-viewer {
          background: white !important;
          box-shadow: 0 4px 20px rgba(0,0,0,.1);
          border-radius: 4px;
        }
        .docx-viewer section.docx {
          background: white;
          padding: 20mm 25mm !important;
          margin: 0 auto 20px !important;
          box-shadow: 0 2px 12px rgba(0,0,0,.08);
        }
        .docx-viewer table {
          border-collapse: collapse;
        }
        .docx-viewer table td,
        .docx-viewer table th {
          border: 1px solid #94a3b8;
        }
        @media print {
          .docx-viewer section.docx {
            box-shadow: none;
            margin: 0 !important;
          }
        }
      `}</style>
    </div>
  )
}

const tbBtn: React.CSSProperties = {
  padding: 6, borderRadius: 6, background: 'rgba(255,255,255,0.1)', border: 'none',
  color: 'white', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
}
