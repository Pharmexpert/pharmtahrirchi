'use client'

/**
 * InlineSynonymPopup — Floating popup for word click.
 *
 * Usage in any editor/viewer:
 *   const { PopupElement, handleClick } = useInlineSynonymPopup()
 *   <div onClick={handleClick}>...</div>
 *   {PopupElement}
 *
 * Features:
 *  - Detects clicked word
 *  - Fetches synonyms from /api/synonyms
 *  - Shows floating popup with list
 *  - Auto-closes on outside click
 */
import React, { useState, useCallback, useEffect } from 'react'
import { Search, Loader2, X } from 'lucide-react'
import api from '../services/api'

interface PopupState {
  visible: boolean
  x: number
  y: number
  word: string
  synonyms: Array<{ word: string; probability?: number; frequency?: number }>
  loading: boolean
  error: string | null
}

export function useInlineSynonymPopup() {
  const [popup, setPopup] = useState<PopupState>({
    visible: false, x: 0, y: 0, word: '', synonyms: [], loading: false, error: null,
  })

  const fetchSynonyms = useCallback(async (word: string) => {
    setPopup(p => ({ ...p, loading: true, error: null }))
    try {
      const r: any = await api.synonyms.list(word)
      const syns = r?.synonyms || []
      const parsed = Array.isArray(syns)
        ? syns.map((s: any) => ({
            word: s.synonym || s.word || s,
            frequency: s.frequency,
            probability: s.probability,
          })).filter((s: any) => s.word && s.word !== word)
        : []
      setPopup(p => ({ ...p, synonyms: parsed, loading: false }))
    } catch (e: any) {
      setPopup(p => ({ ...p, error: e?.message || 'Xatolik', loading: false }))
    }
  }, [])

  const handleClick = useCallback((e: React.MouseEvent) => {
    // Get clicked word from selection or target text
    const selection = window.getSelection()
    let word = selection?.toString().trim() || ''

    if (!word) {
      // Detect word at click position
      const range = document.caretRangeFromPoint?.(e.clientX, e.clientY)
      if (range) {
        const node = range.startContainer
        if (node.nodeType === Node.TEXT_NODE) {
          const text = node.textContent || ''
          const offset = range.startOffset
          // Find word boundaries (whitespace/punctuation) — Unicode-aware via ranges
          const wordRegex = /[a-zA-Z0-9'ʻА-Яа-яЁёЎўҚқҒғҲҳ]+/g
          let match
          while ((match = wordRegex.exec(text)) !== null) {
            if (match.index <= offset && offset <= match.index + match[0].length) {
              word = match[0]
              break
            }
          }
        }
      }
    }

    if (!word || word.length < 2) {
      setPopup(p => ({ ...p, visible: false }))
      return
    }

    setPopup({
      visible: true,
      x: e.clientX,
      y: e.clientY,
      word,
      synonyms: [],
      loading: true,
      error: null,
    })
    fetchSynonyms(word)
  }, [fetchSynonyms])

  const close = useCallback(() => {
    setPopup(p => ({ ...p, visible: false }))
  }, [])

  // Close on Escape
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') close() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [close])

  const PopupElement = popup.visible ? (
    <>
      {/* Backdrop for outside-click close */}
      <div onClick={close} style={{ position: 'fixed', inset: 0, zIndex: 9998 }} />
      <div style={{
        position: 'fixed',
        left: Math.min(popup.x + 8, window.innerWidth - 320),
        top: Math.min(popup.y + 8, window.innerHeight - 280),
        width: 300,
        maxHeight: 280,
        background: 'white',
        border: '1.5px solid #6366F1',
        borderRadius: 12,
        boxShadow: '0 20px 50px rgba(0,0,0,.25)',
        zIndex: 9999,
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        animation: 'synPopIn .15s ease',
      }}>
        {/* Header */}
        <div style={{
          padding: '10px 14px', background: 'linear-gradient(135deg, #6366F1, #4F46E5)',
          color: 'white', display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <Search size={14} />
          <span style={{ fontSize: '.72rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '.04em' }}>Синонимлар</span>
          <div style={{ marginLeft: 'auto', padding: '2px 8px', background: 'rgba(255,255,255,.2)', borderRadius: 10, fontSize: '.7rem', fontWeight: 700 }}>
            {popup.word}
          </div>
          <button onClick={close} style={{ background: 'transparent', border: 'none', color: 'white', cursor: 'pointer', padding: 0, display: 'flex' }}>
            <X size={14} />
          </button>
        </div>

        {/* Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: 10 }}>
          {popup.loading ? (
            <div style={{ textAlign: 'center', padding: 24, color: '#94A3B8' }}>
              <Loader2 className="animate-spin" size={22} />
              <div style={{ fontSize: '.72rem', marginTop: 6 }}>Синонимлар излaнмоqda...</div>
            </div>
          ) : popup.error ? (
            <div style={{ textAlign: 'center', padding: 20, color: '#DC2626', fontSize: '.76rem' }}>
              ⚠ {popup.error}
            </div>
          ) : popup.synonyms.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 20, color: '#94A3B8', fontSize: '.76rem' }}>
              Синонимлар базасида топилмади
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {popup.synonyms.slice(0, 15).map((s, i) => (
                <div
                  key={i}
                  onClick={() => {
                    navigator.clipboard?.writeText(s.word).catch(() => {})
                    close()
                  }}
                  style={{
                    padding: '7px 10px', borderRadius: 6, background: '#F5F3FF',
                    fontSize: '.82rem', fontWeight: 600, color: '#4338CA',
                    cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    border: '1px solid transparent',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.background = '#E0E7FF'; e.currentTarget.style.borderColor = '#6366F1' }}
                  onMouseLeave={e => { e.currentTarget.style.background = '#F5F3FF'; e.currentTarget.style.borderColor = 'transparent' }}
                  title="Клик — clipboard'га кўчиради"
                >
                  <span>{s.word}</span>
                  {typeof s.frequency === 'number' && s.frequency > 0 && (
                    <span style={{ fontSize: '.6rem', color: '#7C3AED', fontWeight: 800 }}>×{s.frequency}</span>
                  )}
                </div>
              ))}
              {popup.synonyms.length > 15 && (
                <div style={{ fontSize: '.66rem', color: '#94A3B8', textAlign: 'center', padding: 4 }}>
                  + yana {popup.synonyms.length - 15} ta
                </div>
              )}
            </div>
          )}
        </div>
      </div>
      <style jsx>{`
        @keyframes synPopIn {
          from { opacity: 0; transform: scale(.92); }
          to { opacity: 1; transform: scale(1); }
        }
      `}</style>
    </>
  ) : null

  return { handleClick, PopupElement, close }
}
