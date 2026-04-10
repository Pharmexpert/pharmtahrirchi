'use client'

import React, { useState } from 'react'
import { Shield, Play, Loader2, CheckCircle2, AlertTriangle, XCircle, ClipboardPaste } from 'lucide-react'
import { useAuth } from '../../components/LoginGuard'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

type Lang = 'en' | 'ru' | 'uz'
const LANG_LABELS: Record<Lang, string> = { en: '🇬🇧 English', ru: '🇷🇺 Русский', uz: '🇺🇿 Ўзбек' }

interface QAResult {
  checks: Record<string, any>
  score: number
  passed: number
  total: number
  grade: string
}

const GRADE_COLORS: Record<string, { bg: string; color: string }> = {
  A: { bg: '#DCFCE7', color: '#16A34A' },
  B: { bg: '#FEF9C3', color: '#CA8A04' },
  C: { bg: '#FED7AA', color: '#EA580C' },
  D: { bg: '#FEE2E2', color: '#DC2626' },
}

export default function QALabPage() {
  const { token } = useAuth()

  const [sourceText, setSourceText] = useState('')
  const [targetText, setTargetText] = useState('')
  const [sourceLang, setSourceLang] = useState<Lang>('en')
  const [targetLang, setTargetLang] = useState<Lang>('uz')
  const [backTranslate, setBackTranslate] = useState(false)
  const [checking, setChecking] = useState(false)
  const [result, setResult] = useState<QAResult | null>(null)

  const runQA = async () => {
    if (!sourceText.trim() || !targetText.trim()) return
    setChecking(true)
    try {
      const res = await fetch(`${API_BASE}/api/qa/check`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({
          source_text: sourceText, target_text: targetText,
          source_lang: sourceLang, target_lang: targetLang,
          back_translate: backTranslate,
        }),
      })
      if (!res.ok) throw new Error()
      setResult(await res.json())
    } catch (_) { setResult(null) }
    finally { setChecking(false) }
  }

  const paste = async (setter: (v: string) => void) => {
    try { const t = await navigator.clipboard.readText(); if (t) setter(t) } catch (_) {}
  }

  const CheckIcon = ({ passed }: { passed: boolean }) =>
    passed ? <CheckCircle2 size={16} color="#16A34A" /> : <XCircle size={16} color="#DC2626" />

  return (
    <div style={{ padding: '20px 24px' }}>
      <div style={{ marginBottom: 16 }}>
        <h1 style={{ fontSize: '1.3rem', fontWeight: 800, margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Shield size={24} color="#7C3AED" /> QA Lab
        </h1>
        <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', margin: 0 }}>Таржима сифатини автоматик текшириш</p>
      </div>

      {/* Language selectors */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 12, alignItems: 'center', flexWrap: 'wrap' }}>
        <select value={sourceLang} onChange={e => setSourceLang(e.target.value as Lang)}
          style={{ padding: '6px 10px', borderRadius: 6, border: '1.5px solid var(--border)', fontWeight: 600 }}>
          {Object.entries(LANG_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <span style={{ color: 'var(--text-muted)' }}>→</span>
        <select value={targetLang} onChange={e => setTargetLang(e.target.value as Lang)}
          style={{ padding: '6px 10px', borderRadius: 6, border: '1.5px solid var(--border)', fontWeight: 600 }}>
          {Object.entries(LANG_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.78rem', cursor: 'pointer' }}>
          <input type="checkbox" checked={backTranslate} onChange={e => setBackTranslate(e.target.checked)} />
          Back-translation (AI)
        </label>
        <button onClick={runQA} disabled={checking || !sourceText.trim() || !targetText.trim()}
          style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 4, background: 'linear-gradient(135deg,#7C3AED,#6D28D9)', color: 'white', border: 'none', borderRadius: 6, padding: '8px 18px', fontSize: '0.85rem', fontWeight: 700, cursor: checking ? 'not-allowed' : 'pointer' }}>
          {checking ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
          {checking ? 'Текширилмоқда...' : 'QA текшириш'}
        </button>
      </div>

      {/* Text inputs */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
            <span style={{ fontWeight: 700, fontSize: '0.82rem' }}>Асл матн ({LANG_LABELS[sourceLang]})</span>
            <button onClick={() => paste(setSourceText)} style={{ padding: '2px 6px', borderRadius: 4, border: '1px solid var(--border)', background: 'var(--bg-secondary)', cursor: 'pointer', fontSize: '0.65rem' }}>
              <ClipboardPaste size={11} />
            </button>
          </div>
          <textarea value={sourceText} onChange={e => setSourceText(e.target.value)}
            placeholder="Асл матн..."
            style={{ width: '100%', minHeight: 200, padding: 10, border: '1.5px solid var(--border)', borderRadius: 8, fontSize: '0.88rem', fontFamily: 'Georgia, serif', resize: 'vertical', outline: 'none', lineHeight: 1.6 }}
          />
        </div>
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
            <span style={{ fontWeight: 700, fontSize: '0.82rem' }}>Таржима ({LANG_LABELS[targetLang]})</span>
            <button onClick={() => paste(setTargetText)} style={{ padding: '2px 6px', borderRadius: 4, border: '1px solid var(--border)', background: 'var(--bg-secondary)', cursor: 'pointer', fontSize: '0.65rem' }}>
              <ClipboardPaste size={11} />
            </button>
          </div>
          <textarea value={targetText} onChange={e => setTargetText(e.target.value)}
            placeholder="Таржима матни..."
            style={{ width: '100%', minHeight: 200, padding: 10, border: '1.5px solid var(--border)', borderRadius: 8, fontSize: '0.88rem', fontFamily: 'Georgia, serif', resize: 'vertical', outline: 'none', lineHeight: 1.6 }}
          />
        </div>
      </div>

      {/* QA Results */}
      {result && (
        <div style={{ background: 'var(--bg-card)', border: '1.5px solid var(--border)', borderRadius: 12, padding: 20 }}>
          {/* Score header */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 16 }}>
            <div style={{
              width: 64, height: 64, borderRadius: '50%',
              background: (GRADE_COLORS[result.grade] || GRADE_COLORS.D).bg,
              color: (GRADE_COLORS[result.grade] || GRADE_COLORS.D).color,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '1.8rem', fontWeight: 900,
            }}>
              {result.grade}
            </div>
            <div>
              <div style={{ fontSize: '1.5rem', fontWeight: 800 }}>{result.score}%</div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                {result.passed}/{result.total} текширув ўтди
              </div>
            </div>
          </div>

          {/* Individual checks */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 12 }}>
            {/* Numbers */}
            {result.checks.numbers && (
              <div style={{ padding: 12, background: 'var(--bg-secondary)', borderRadius: 8, border: '1px solid var(--border)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                  <CheckIcon passed={result.checks.numbers.passed} />
                  <span style={{ fontWeight: 700, fontSize: '0.85rem' }}>Рақамлар сақланиши</span>
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Асл: {result.checks.numbers.source_numbers?.join(', ') || '—'}
                  <br />Таржима: {result.checks.numbers.target_numbers?.join(', ') || '—'}
                  {result.checks.numbers.missing_in_target?.length > 0 && (
                    <div style={{ color: '#DC2626', marginTop: 4 }}>
                      Йўқолган: {result.checks.numbers.missing_in_target.join(', ')}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Units */}
            {result.checks.units && (
              <div style={{ padding: 12, background: 'var(--bg-secondary)', borderRadius: 8, border: '1px solid var(--border)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                  <CheckIcon passed={result.checks.units.passed} />
                  <span style={{ fontWeight: 700, fontSize: '0.85rem' }}>Бирликлар сақланиши</span>
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Асл: {result.checks.units.source_units?.join(', ') || '—'}
                  <br />Таржима: {result.checks.units.target_units?.join(', ') || '—'}
                </div>
              </div>
            )}

            {/* Segments */}
            {result.checks.segments && (
              <div style={{ padding: 12, background: 'var(--bg-secondary)', borderRadius: 8, border: '1px solid var(--border)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                  <CheckIcon passed={result.checks.segments.passed} />
                  <span style={{ fontWeight: 700, fontSize: '0.85rem' }}>Сегмент сони</span>
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Асл: {result.checks.segments.source_segments} · Таржима: {result.checks.segments.target_segments} · Нисбат: {result.checks.segments.ratio}
                </div>
              </div>
            )}

            {/* Length */}
            {result.checks.length && (
              <div style={{ padding: 12, background: 'var(--bg-secondary)', borderRadius: 8, border: '1px solid var(--border)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                  <CheckIcon passed={result.checks.length.passed} />
                  <span style={{ fontWeight: 700, fontSize: '0.85rem' }}>Узунлик нисбати</span>
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Асл: {result.checks.length.source_chars} · Таржима: {result.checks.length.target_chars} · Нисбат: {result.checks.length.ratio}
                </div>
              </div>
            )}

            {/* Back-translation */}
            {result.checks.back_translation?.available && (
              <div style={{ padding: 12, background: 'var(--bg-secondary)', borderRadius: 8, border: '1px solid var(--border)', gridColumn: 'span 2' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                  <AlertTriangle size={16} color="#F59E0B" />
                  <span style={{ fontWeight: 700, fontSize: '0.85rem' }}>Back-translation</span>
                </div>
                <div style={{ fontSize: '0.82rem', lineHeight: 1.6, fontFamily: 'Georgia, serif', padding: 8, background: 'white', borderRadius: 6, border: '1px solid var(--border)' }}>
                  {result.checks.back_translation.back_translation}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
