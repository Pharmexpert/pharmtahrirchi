'use client'

import React, { useState, useRef, useCallback } from 'react'
import { Play, Loader2, ArrowRightLeft, Save, Trash2, ClipboardPaste, BarChart3, Shield } from 'lucide-react'
import { useAuth } from '../../components/LoginGuard'
import api from '../../services/api'
import AnnotatedTextView, { type AnalysisResult } from '../../components/AnnotatedTextView'
import LinguisticAnalysisBar from '../../components/LinguisticAnalysisBar'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

type Lang = 'en' | 'ru' | 'uz'
const LANG_LABELS: Record<Lang, string> = { en: '🇬🇧 English', ru: '🇷🇺 Русский', uz: '🇺🇿 Ўзбек' }

export default function WorkbenchPage() {
  const { token } = useAuth()

  const [texts, setTexts] = useState<Record<Lang, string>>({ en: '', ru: '', uz: '' })
  const [activeLang, setActiveLang] = useState<Lang>('uz')
  const [translating, setTranslating] = useState(false)
  const [analysis, setAnalysis] = useState<Record<Lang, AnalysisResult | null>>({ en: null, ru: null, uz: null })
  const [showAnalysis, setShowAnalysis] = useState<Record<Lang, boolean>>({ en: false, ru: false, uz: false })
  const [tmScores, setTmScores] = useState<Record<Lang, number | null>>({ en: null, ru: null, uz: null })

  const refs = {
    en: useRef<HTMLTextAreaElement>(null),
    ru: useRef<HTMLTextAreaElement>(null),
    uz: useRef<HTMLTextAreaElement>(null),
  }

  const updateText = (lang: Lang, value: string) => {
    setTexts(prev => ({ ...prev, [lang]: value }))
  }

  // Sync scroll across editors
  const handleScroll = (sourceLang: Lang) => {
    const sourceEl = refs[sourceLang].current
    if (!sourceEl) return
    const ratio = sourceEl.scrollTop / (sourceEl.scrollHeight - sourceEl.clientHeight || 1)
    for (const lang of ['en', 'ru', 'uz'] as Lang[]) {
      if (lang !== sourceLang && refs[lang].current) {
        const el = refs[lang].current!
        el.scrollTop = ratio * (el.scrollHeight - el.clientHeight)
      }
    }
  }

  // Translate from one lang to others
  const translateAll = async () => {
    const srcText = texts[activeLang]
    if (!srcText.trim()) return
    setTranslating(true)
    try {
      const targets = (['en', 'ru', 'uz'] as Lang[]).filter(l => l !== activeLang)
      const results = await Promise.allSettled(
        targets.map(async (tgt) => {
          const res = await fetch(`${API_BASE}/api/tilshunos/translate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({ text: srcText, source_lang: activeLang, target_lang: tgt }),
          })
          if (!res.ok) throw new Error()
          const r = await res.json()
          return { lang: tgt, text: r.translated || r.text || '' }
        })
      )
      for (const r of results) {
        if (r.status === 'fulfilled' && r.value.text) {
          updateText(r.value.lang, r.value.text)
        }
      }
    } catch (_) {}
    finally { setTranslating(false) }
  }

  // Run 4-layer analysis on a language
  const analyzeText = async (lang: Lang) => {
    const text = texts[lang]
    if (!text.trim()) return
    try {
      const res = await fetch(`${API_BASE}/api/analyze/full`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ text, layers: ['morph', 'sayqallash', 'syntax', 'style'], lang }),
      })
      if (!res.ok) return
      const r = await res.json()
      setAnalysis(prev => ({ ...prev, [lang]: r }))
      setShowAnalysis(prev => ({ ...prev, [lang]: true }))
    } catch (_) {}
  }

  // Check TM score
  const checkTM = async (lang: Lang) => {
    const text = texts[lang]
    if (!text.trim()) return
    try {
      const res = await fetch(`${API_BASE}/api/tilshunos/translate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ text, source_lang: lang, target_lang: lang === 'uz' ? 'en' : 'uz', check_tm_only: true }),
      })
      if (res.ok) {
        const r = await res.json()
        setTmScores(prev => ({ ...prev, [lang]: r.tm_match?.score || null }))
      }
    } catch (_) {}
  }

  // Transliterate UZ text
  const transliterate = async (target: 'cyrillic' | 'latin') => {
    if (!texts.uz.trim()) return
    try {
      const data: any = await api.linguistic.transliterate(texts.uz, target)
      updateText('uz', data.text)
    } catch (_) {}
  }

  const clearAll = () => {
    setTexts({ en: '', ru: '', uz: '' })
    setAnalysis({ en: null, ru: null, uz: null })
    setShowAnalysis({ en: false, ru: false, uz: false })
    setTmScores({ en: null, ru: null, uz: null })
  }

  const paste = async (lang: Lang) => {
    try {
      const t = await navigator.clipboard.readText()
      if (t) updateText(lang, t)
    } catch (_) {}
  }

  return (
    <div style={{ padding: '20px 24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <div>
          <h1 style={{ fontSize: '1.3rem', fontWeight: 800, margin: 0 }}>Workbench</h1>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', margin: 0 }}>3-тилли параллел таржима станцияси</p>
        </div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <select value={activeLang} onChange={e => setActiveLang(e.target.value as Lang)}
            style={{ padding: '6px 10px', borderRadius: 6, border: '1.5px solid var(--border)', fontWeight: 600, fontSize: '0.82rem' }}>
            <option value="en">Асл тил: English</option>
            <option value="ru">Асл тил: Русский</option>
            <option value="uz">Асл тил: Ўзбек</option>
          </select>
          <button onClick={translateAll} disabled={translating || !texts[activeLang].trim()}
            style={{ display: 'flex', alignItems: 'center', gap: 4, background: 'linear-gradient(135deg,#10B981,#059669)', color: 'white', border: 'none', borderRadius: 6, padding: '8px 16px', fontSize: '0.82rem', fontWeight: 700, cursor: translating ? 'not-allowed' : 'pointer' }}>
            {translating ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
            {translating ? 'Таржима...' : 'Барчасига таржима'}
          </button>
          <button onClick={clearAll}
            style={{ display: 'flex', alignItems: 'center', gap: 4, background: '#FEF2F2', color: '#DC2626', border: '1px solid #FCA5A5', borderRadius: 6, padding: '8px 12px', fontSize: '0.82rem', fontWeight: 600, cursor: 'pointer' }}>
            <Trash2 size={14} /> Тозалаш
          </button>
        </div>
      </div>

      {/* 3-column editor */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, minHeight: 500 }}>
        {(['en', 'ru', 'uz'] as Lang[]).map(lang => (
          <div key={lang} style={{
            background: 'var(--bg-card)', border: lang === activeLang ? '2px solid #7C3AED' : '1.5px solid var(--border)',
            borderRadius: 10, padding: 12, display: 'flex', flexDirection: 'column', gap: 8,
          }}>
            {/* Lang header */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontWeight: 700, fontSize: '0.85rem' }}>{LANG_LABELS[lang]}</span>
              <div style={{ display: 'flex', gap: 3 }}>
                <button onClick={() => paste(lang)} title="Жойлаш"
                  style={{ padding: '3px 6px', borderRadius: 4, border: '1px solid var(--border)', background: 'var(--bg-secondary)', cursor: 'pointer', fontSize: '0.65rem' }}>
                  <ClipboardPaste size={11} />
                </button>
                <button onClick={() => analyzeText(lang)} title="4-қатлам таҳлил"
                  style={{ padding: '3px 6px', borderRadius: 4, border: '1px solid #C4B5FD', background: showAnalysis[lang] ? '#7C3AED' : '#F5F3FF', color: showAnalysis[lang] ? 'white' : '#7C3AED', cursor: 'pointer', fontSize: '0.65rem' }}>
                  <BarChart3 size={11} />
                </button>
                {lang === 'uz' && (
                  <>
                    <button onClick={() => transliterate('cyrillic')} title="Кирил"
                      style={{ padding: '3px 6px', borderRadius: 4, border: '1px solid #FB923C', background: '#FFF7ED', color: '#EA580C', cursor: 'pointer', fontSize: '0.6rem', fontWeight: 800 }}>К</button>
                    <button onClick={() => transliterate('latin')} title="Лотин"
                      style={{ padding: '3px 6px', borderRadius: 4, border: '1px solid #22C55E', background: '#F0FDF4', color: '#16A34A', cursor: 'pointer', fontSize: '0.6rem', fontWeight: 800 }}>L</button>
                  </>
                )}
              </div>
            </div>

            {/* TM score badge */}
            {tmScores[lang] !== null && tmScores[lang]! > 0 && (
              <div style={{ fontSize: '0.6rem', fontWeight: 700, color: tmScores[lang]! >= 0.95 ? '#16A34A' : '#F59E0B', background: tmScores[lang]! >= 0.95 ? '#F0FDF4' : '#FFFBEB', padding: '2px 8px', borderRadius: 12, alignSelf: 'flex-start' }}>
                TM: {Math.round(tmScores[lang]! * 100)}%
              </div>
            )}

            {/* Textarea */}
            <textarea
              ref={refs[lang]}
              value={texts[lang]}
              onChange={e => updateText(lang, e.target.value)}
              onScroll={() => handleScroll(lang)}
              placeholder={`${LANG_LABELS[lang]} матн...`}
              style={{
                flex: 1, minHeight: 350, padding: 10, border: '1.5px solid var(--border)',
                borderRadius: 8, fontSize: '0.88rem', fontFamily: 'Georgia, serif',
                resize: 'vertical', outline: 'none', background: 'var(--bg-secondary)',
                lineHeight: 1.7,
              }}
            />

            {/* Analysis result */}
            {showAnalysis[lang] && analysis[lang] && (
              <div style={{ padding: '8px 10px', background: '#FAFBFF', border: '1px solid #E5E7EB', borderRadius: 8, maxHeight: 200, overflowY: 'auto' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontSize: '0.6rem', fontWeight: 700, color: '#7C3AED' }}>
                    {(analysis[lang]?.sayqallash?.length || 0) + (analysis[lang]?.style?.length || 0)} та хато
                  </span>
                  <button onClick={() => setShowAnalysis(prev => ({ ...prev, [lang]: false }))}
                    style={{ fontSize: '0.55rem', cursor: 'pointer', background: 'none', border: 'none', color: '#EF4444' }}>✕</button>
                </div>
                <AnnotatedTextView text={texts[lang]} result={analysis[lang]} lang={lang} />
              </div>
            )}

            {/* Word count */}
            <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', textAlign: 'right' }}>
              {texts[lang].split(/\s+/).filter(Boolean).length} сўз · {texts[lang].length} белги
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
