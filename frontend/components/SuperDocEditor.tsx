'use client'

import React, { useEffect, useRef, useState } from 'react'
import { Loader2, FileText, Upload, Download, Trash2, Sparkles, Wand2, ArrowRightLeft } from 'lucide-react'

/**
 * SuperDoc Editor — Stage 2 of Hybrid Word editor.
 *
 * Capabilities:
 *  - Full DOCX read + edit (OOXML-native)
 *  - Headers/footers, tables, images preserved
 *  - Pagination, section breaks, complex tables
 *  - Export .docx round-trip
 *
 * Requires client-side only (uses browser DOM + Yjs).
 */

interface Props {
  file: File | null
  onReady?: (editor: any) => void
  aiActions?: Array<{
    label: string
    icon?: React.ReactNode
    color?: string
    onClick: (selectedText: string, fullText: string, editor: any) => void
  }>
  height?: string | number
}

export default function SuperDocEditor({ file, onReady, aiActions = [], height = '75vh' }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const editorRef = useRef<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    if (!file || !containerRef.current) return
    let cancelled = false

    const init = async () => {
      setLoading(true)
      setError(null)
      setReady(false)
      try {
        // Dynamic import (client-only)
        const mod = await import('@harbour-enterprises/superdoc')
        // Load SuperDoc styles dynamically
        try { await import('@harbour-enterprises/superdoc/style.css' as any) } catch {}

        if (cancelled) return
        const SuperDoc = (mod as any).SuperDoc || (mod as any).default?.SuperDoc || (mod as any).default

        // Clear container
        const container = containerRef.current!
        container.innerHTML = '<div id="superdoc-mount" style="width:100%; height:100%; overflow:auto; background:#E2E8F0;"></div>'

        const superdoc = new SuperDoc({
          selector: '#superdoc-mount',
          documents: [
            {
              id: `doc-${Date.now()}`,
              type: 'docx',
              data: file,
            },
          ],
          onReady: () => {
            if (cancelled) return
            editorRef.current = superdoc
            setReady(true)
            setLoading(false)
            onReady?.(superdoc)
          },
          onError: (err: any) => {
            console.error('SuperDoc error:', err)
            if (!cancelled) {
              setError(err?.message || String(err))
              setLoading(false)
            }
          },
        })
      } catch (err: any) {
        console.error('SuperDoc init failed:', err)
        if (!cancelled) {
          setError(err?.message || 'SuperDoc ишга туширилмади')
          setLoading(false)
        }
      }
    }

    init()
    return () => {
      cancelled = true
      try {
        if (editorRef.current && editorRef.current.destroy) {
          editorRef.current.destroy()
        }
      } catch {}
      editorRef.current = null
    }
  }, [file])

  const handleExport = async () => {
    if (!editorRef.current) return
    try {
      // Try SuperDoc export methods
      const editor = editorRef.current
      let blob: Blob | null = null

      if (editor.exportDocx) {
        blob = await editor.exportDocx()
      } else if (editor.export) {
        blob = await editor.export({ format: 'docx' })
      } else if (editor.toDocx) {
        blob = await editor.toDocx()
      } else if (editor.save) {
        blob = await editor.save()
      }

      if (blob) {
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = file?.name?.replace(/\.docx?$/i, '-edited.docx') || 'document-edited.docx'
        a.click()
        URL.revokeObjectURL(url)
      } else {
        alert('Export method not available. SuperDoc API update kerak.')
      }
    } catch (e: any) {
      alert('Export xato: ' + (e?.message || e))
    }
  }

  const getSelectedText = (): string => {
    try {
      const sel = window.getSelection()?.toString() || ''
      return sel.trim()
    } catch {
      return ''
    }
  }

  const getFullText = (): string => {
    try {
      const editor = editorRef.current
      if (editor?.getText) return editor.getText()
      if (editor?.getHTML) {
        const div = document.createElement('div')
        div.innerHTML = editor.getHTML()
        return div.innerText || div.textContent || ''
      }
      // Fallback: read rendered DOM
      return containerRef.current?.innerText?.trim() || ''
    } catch {
      return ''
    }
  }

  if (!file) {
    return (
      <div style={{
        padding: 60, textAlign: 'center', color: '#94A3B8',
        border: '2px dashed #E2E8F0', borderRadius: 14, background: '#F8FAFC'
      }}>
        <FileText size={56} style={{ opacity: 0.25, marginBottom: 16 }} />
        <div style={{ fontSize: '.9rem', fontWeight: 700 }}>Word файл юкланмаган</div>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 0, border: '1px solid #CBD5E1', borderRadius: 12, overflow: 'hidden' }}>
      {/* Toolbar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
        padding: '10px 14px', background: '#0F172A', color: 'white',
      }}>
        <FileText size={16} color="#60A5FA" />
        <span style={{ fontSize: '.82rem', fontWeight: 700, maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{file.name}</span>
        <span style={{ fontSize: '.68rem', padding: '2px 8px', borderRadius: 10, background: '#1E40AF', color: '#BFDBFE', fontWeight: 700 }}>
          SuperDoc · edit mode
        </span>

        <div style={{ marginLeft: 'auto', display: 'flex', gap: 6, alignItems: 'center' }}>
          {ready && (
            <button onClick={handleExport} style={{
              padding: '6px 12px', borderRadius: 8, background: '#16A34A', border: 'none',
              color: 'white', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5,
              fontSize: '.75rem', fontWeight: 700,
            }}>
              <Download size={13} /> .docx Экспорт
            </button>
          )}
        </div>
      </div>

      {/* AI Actions bar */}
      {aiActions.length > 0 && ready && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap',
          padding: '10px 14px', background: '#F1F5F9', borderBottom: '1px solid #E2E8F0',
        }}>
          <span style={{ fontSize: '.68rem', fontWeight: 800, color: '#475569', textTransform: 'uppercase' }}>
            <Sparkles size={11} style={{ display: 'inline', verticalAlign: -1, marginRight: 4 }} />
            AI амаллар:
          </span>
          {aiActions.map((a, i) => (
            <button key={i} onClick={() => a.onClick(getSelectedText(), getFullText(), editorRef.current)} style={{
              padding: '6px 12px', borderRadius: 8, border: 'none',
              background: a.color || '#7C3AED', color: 'white', fontWeight: 700, fontSize: '.75rem',
              cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4,
            }}>
              {a.icon}{a.label}
            </button>
          ))}
        </div>
      )}

      {/* Editor container */}
      <div
        ref={containerRef}
        style={{
          background: '#E2E8F0',
          height: typeof height === 'number' ? `${height}px` : height,
          position: 'relative',
          overflow: 'auto',
        }}
      >
        {loading && (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(226,232,240,0.95)', zIndex: 5 }}>
            <div style={{ textAlign: 'center' }}>
              <Loader2 className="animate-spin" size={36} color="#2563EB" />
              <div style={{ fontSize: '.82rem', color: '#64748B', marginTop: 8, fontWeight: 600 }}>SuperDoc engine ишга туширилмоқда...</div>
              <div style={{ fontSize: '.68rem', color: '#94A3B8', marginTop: 4 }}>OOXML parsing + rendering (1-3 сек)</div>
            </div>
          </div>
        )}
        {error && !loading && (
          <div style={{
            margin: 20, padding: 30, background: '#FEE2E2', borderRadius: 12, color: '#991B1B',
            border: '1px solid #FECACA', textAlign: 'center'
          }}>
            <FileText size={36} style={{ marginBottom: 10 }} />
            <div style={{ fontWeight: 700, fontSize: '.9rem' }}>SuperDoc xato: {error}</div>
            <div style={{ fontSize: '.75rem', marginTop: 8, opacity: 0.8 }}>
              Босқич 1 (docx-preview) га ўтинг — read-only режимда ишлайди.
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
