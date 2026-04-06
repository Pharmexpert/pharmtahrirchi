'use client'

import React, { useState, useRef, useEffect } from 'react'
import { useLang, LangCode } from './LanguageProvider'

const LANGUAGES: Array<{ code: LangCode; label: string; flag: string; sub?: string }> = [
  { code: 'uz-cyr', label: 'Ўзбекча', flag: '🇺🇿', sub: 'Кирилл' },
  { code: 'uz-lat', label: 'O\'zbekcha', flag: '🇺🇿', sub: 'Lotin' },
  { code: 'ru', label: 'Русский', flag: '🇷🇺' },
  { code: 'en', label: 'English', flag: '🇬🇧' },
]

export default function LanguageSwitcher() {
  const { lang, setLang } = useLang()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const current = LANGUAGES.find(l => l.code === lang) || LANGUAGES[0]

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <div ref={ref} style={{ position: 'relative', zIndex: 100 }}>
      <button onClick={() => setOpen(!open)} style={{
        display: 'flex', alignItems: 'center', gap: '6px',
        padding: '6px 12px', borderRadius: '10px',
        border: '1.5px solid var(--border, #E2D5C5)',
        background: 'var(--bg-card, white)', cursor: 'pointer',
        fontSize: '0.82rem', fontWeight: 600,
        color: 'var(--text-primary, #3D2B1F)',
        transition: 'all 0.15s'
      }}>
        <span style={{ fontSize: '1rem' }}>{current.flag}</span>
        <span>{current.sub ? `${current.label.slice(0, 2)}` : current.label.slice(0, 2)}</span>
        {current.sub && <span style={{ fontSize: '0.65rem', color: 'var(--text-muted, #9C8B7A)', fontWeight: 700 }}>{current.sub}</span>}
        <span style={{ fontSize: '0.6rem', opacity: 0.5, transform: open ? 'rotate(180deg)' : '', transition: 'transform 0.2s' }}>▼</span>
      </button>

      {open && (
        <div style={{
          position: 'absolute', top: '100%', right: 0, marginTop: '6px',
          background: 'white', borderRadius: '12px', padding: '6px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.15)', border: '1px solid var(--border, #E2D5C5)',
          minWidth: '180px', animation: 'fadeIn 0.15s ease-out'
        }}>
          {LANGUAGES.map(l => (
            <button key={l.code} onClick={() => { setLang(l.code); setOpen(false) }} style={{
              display: 'flex', alignItems: 'center', gap: '10px', width: '100%',
              padding: '8px 12px', borderRadius: '8px', border: 'none',
              background: lang === l.code ? 'var(--bg-secondary, #FFF8F0)' : 'transparent',
              cursor: 'pointer', fontSize: '0.85rem', fontWeight: lang === l.code ? 700 : 500,
              color: lang === l.code ? 'var(--accent-primary, #B48C64)' : 'var(--text-primary, #3D2B1F)',
              transition: 'background 0.15s', textAlign: 'left'
            }}
              onMouseEnter={e => { if (lang !== l.code) (e.target as HTMLElement).style.background = '#F8F4F0' }}
              onMouseLeave={e => { if (lang !== l.code) (e.target as HTMLElement).style.background = 'transparent' }}
            >
              <span style={{ fontSize: '1.1rem' }}>{l.flag}</span>
              <div>
                <div>{l.label}</div>
                {l.sub && <div style={{ fontSize: '0.65rem', color: 'var(--text-muted, #9C8B7A)', fontWeight: 600 }}>{l.sub}</div>}
              </div>
              {lang === l.code && <span style={{ marginLeft: 'auto', color: 'var(--accent-primary, #B48C64)' }}>✓</span>}
            </button>
          ))}
        </div>
      )}

      <style jsx global>{`
        @keyframes fadeIn { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: translateY(0); } }
      `}</style>
    </div>
  )
}
