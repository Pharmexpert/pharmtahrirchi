'use client'

import React, { useState, useEffect } from 'react'
import { Layers, Save, Upload, Trash2, Loader2, CheckCircle2, AlertTriangle, Sparkles } from 'lucide-react'
import { useAuth } from '../../components/LoginGuard'
import api from '../../services/api'

type Mode = 'work' | 'enrich'

interface Token {
  word: string
  clean: string
  pos: string
  role: string
}

interface SyntaxError {
  type: string
  severity: string
  message: string
  suggestion?: string
}

interface AnalysisResult {
  tokens: Token[]
  word_order_formula: string
  pos_sequence: string
  errors: SyntaxError[]
  suggestions: SyntaxError[]
  valid: boolean
  has_subject: boolean
  has_predicate: boolean
}

const ROLE_COLORS: Record<string, { bg: string; color: string; label: string }> = {
  ega:          { bg: '#DBEAFE', color: '#1D4ED8', label: 'ЭГА' },
  kesim:        { bg: '#FEE2E2', color: '#DC2626', label: 'КЕСИМ' },
  toldiruvchi:  { bg: '#DCFCE7', color: '#16A34A', label: 'ТЎЛДИРУВЧИ' },
  aniqlovchi:   { bg: '#FEF3C7', color: '#D97706', label: 'АНИҚЛОВЧИ' },
  hol:          { bg: '#F3E8FF', color: '#9333EA', label: 'ҲОЛ' },
  other:        { bg: '#F1F5F9', color: '#64748B', label: '?' },
}

export default function SyntaxPage() {
  const { token } = useAuth()
  const [mode, setMode] = useState<Mode>('work')
  const [text, setText] = useState('')
  const [lang, setLang] = useState<'uz' | 'ru'>('uz')
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState<Record<string, number> | null>(null)
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null)

  // Drag-and-drop state for enrich mode
  const [dragIdx, setDragIdx] = useState<number | null>(null)

  useEffect(() => {
    api.syntax.stats().then(setStats).catch(() => {})
  }, [])

  const showToast = (msg: string, type: 'success' | 'error' = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3000)
  }

  const analyze = async () => {
    if (!text.trim()) return
    setLoading(true)
    try {
      const r: any = await api.syntax.analyze(text)
      setResult(r)
    } catch (e: any) {
      showToast('Хатолик: ' + (e?.message || e), 'error')
    } finally {
      setLoading(false)
    }
  }

  const reorder = async () => {
    if (!text.trim()) return
    try {
      const r: any = await api.syntax.reorder(text)
      setText(r.canonical)
      showToast('Тартиб тўғриланди ✓')
      setResult(null)
    } catch (e) {
      showToast('Қайта тартиблаш муваффақиятсиз', 'error')
    }
  }

  const saveAsRule = async () => {
    if (!result || !result.tokens.length) return
    const wrong = text
    const correct = result.tokens.map(t => t.word).join(' ')  // user-edited via DnD
    try {
      await api.syntax.saveRule(wrong, correct, 'User-saved from syntax page')
      showToast('Қоида сақланди ✓')
      api.syntax.stats().then(setStats).catch(() => {})
    } catch (e) {
      showToast('Сақлашда хатолик', 'error')
    }
  }

  const handleFile = async (file: File) => {
    const txt = await file.text()
    setText(txt.slice(0, 5000))
  }

  // Drag-and-drop reorder (enrich mode)
  const onDragStart = (idx: number) => setDragIdx(idx)
  const onDragOver = (e: React.DragEvent) => e.preventDefault()
  const onDrop = (idx: number) => {
    if (dragIdx === null || !result) return
    const newTokens = [...result.tokens]
    const [moved] = newTokens.splice(dragIdx, 1)
    newTokens.splice(idx, 0, moved)
    setResult({ ...result, tokens: newTokens })
    setDragIdx(null)
  }

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      {toast && (
        <div style={{
          position: 'fixed', bottom: 32, right: 32, zIndex: 1000,
          padding: '14px 22px', borderRadius: 12,
          background: toast.type === 'success' ? '#16A34A' : '#DC2626',
          color: 'white', fontWeight: 700, boxShadow: '0 8px 24px rgba(0,0,0,.2)'
        }}>{toast.msg}</div>
      )}

      {/* Header */}
      <div style={{
        background: 'linear-gradient(135deg, #FFF8F0 0%, #FFEFDC 100%)',
        borderRadius: 20, padding: '28px 32px', marginBottom: 24,
        border: '1.5px solid #FDE3C5',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 18 }}>
          <div style={{
            width: 52, height: 52, borderRadius: 14,
            background: 'linear-gradient(135deg, #B48C64, #8B5E3C)',
            display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>
            <Layers size={26} color="white" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.7rem', fontWeight: 800, margin: 0 }}>Синтаксис таҳлили 📐</h1>
            <p style={{ color: '#64748B', fontSize: '.9rem', margin: 0 }}>
              Гап тузилиши, сўз бирикмалари, гап бўлаклари ва сўз тартиби
            </p>
          </div>
        </div>
        {stats && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, alignItems: 'flex-end' }}>
            <div style={{ display: 'flex', gap: 10, fontSize: '.78rem', color: '#64748B', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
              <span>📊 Парсе: <b>{stats.syntax_parsed_sentences}</b></span>
              <span>🔗 Бирикма: <b>{stats.syntax_phrases}</b></span>
              <span>📋 Шаблон: <b>{stats.syntax_sentence_templates}</b></span>
              <span>⚖️ Қоида: <b>{stats.syntax_word_order_rules}</b></span>
              {typeof stats.synth_pairs === 'number' && stats.synth_pairs > 0 && (
                <span>🔬 Synth: <b>{stats.synth_pairs}</b></span>
              )}
            </div>
            {stats.sayqallash_quality && typeof stats.sayqallash_quality === 'object' && Object.keys(stats.sayqallash_quality).length > 0 && (
              <div style={{ display: 'flex', gap: 6, fontSize: '.68rem' }}>
                {Object.entries(stats.sayqallash_quality).map(([k, v]: any) => {
                  const c: any = { clean: '#16A34A', noisy: '#DC2626', suspicious: '#D97706', unverified: '#64748B' }
                  return (
                    <span key={k} style={{ padding: '2px 7px', borderRadius: 10, fontWeight: 700, background: `${c[k] || '#999'}18`, color: c[k] || '#555' }}>
                      {k}: {v}
                    </span>
                  )
                })}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Mode toggle */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <button onClick={() => setMode('work')} style={tabBtn(mode === 'work')}>
          📝 Ишчи режим
        </button>
        <button onClick={() => setMode('enrich')} style={tabBtn(mode === 'enrich')}>
          ✨ Қоидаларни бойитиш
        </button>
      </div>

      {/* Toolbar */}
      <div style={{
        background: 'white', borderRadius: 14, padding: 14, marginBottom: 14,
        border: '1px solid #E2E8F0', display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center'
      }}>
        <label style={{ padding: '8px 14px', borderRadius: 10, border: '1px solid #E2E8F0', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, fontSize: '.85rem', fontWeight: 600 }}>
          <Upload size={14} /> Файл юклаш
          <input type="file" accept=".txt,.md" hidden onChange={e => e.target.files?.[0] && handleFile(e.target.files[0])} />
        </label>
        <select value={lang} onChange={e => setLang(e.target.value as any)} style={{ padding: '8px 14px', borderRadius: 10, border: '1px solid #E2E8F0', fontSize: '.85rem' }}>
          <option value="uz">🇺🇿 Ўзбекча</option>
          <option value="ru">🇷🇺 Русский</option>
        </select>
        <button onClick={analyze} disabled={loading || !text.trim()} style={primaryBtn(loading)}>
          {loading ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
          Текшириш
        </button>
        <button onClick={reorder} disabled={!text.trim()} style={secondaryBtn()}>
          🔄 Тартибни тузатиш
        </button>
        {mode === 'enrich' && result && (
          <button onClick={saveAsRule} style={{ ...primaryBtn(false), background: '#16A34A' }}>
            <Save size={14} /> Қоида сифатида сақлаш
          </button>
        )}
        <button onClick={() => { setText(''); setResult(null) }} style={secondaryBtn()}>
          <Trash2 size={14} /> Тозалаш
        </button>
      </div>

      {/* Text input */}
      <textarea
        value={text}
        onChange={e => setText(e.target.value)}
        placeholder="Текстни шу ерга ёзинг ёки файл юкланг..."
        rows={5}
        style={{
          width: '100%', padding: 16, borderRadius: 14, border: '1px solid #E2E8F0',
          fontSize: '1rem', fontFamily: 'inherit', resize: 'vertical', boxSizing: 'border-box',
          marginBottom: 16, outline: 'none'
        }}
      />

      {/* Analysis result */}
      {result && (
        <div style={{ background: 'white', borderRadius: 14, padding: 20, border: '1px solid #E2E8F0', marginBottom: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 14 }}>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 800, margin: 0 }}>Натижа</h3>
            <div style={{ fontSize: '.78rem', color: '#64748B' }}>
              Формула: <b>{result.word_order_formula || '—'}</b>
            </div>
          </div>

          {/* Tokens */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 18 }}>
            {result.tokens.map((tok, i) => {
              const c = ROLE_COLORS[tok.role] || ROLE_COLORS.other
              return (
                <div
                  key={i}
                  draggable={mode === 'enrich'}
                  onDragStart={() => onDragStart(i)}
                  onDragOver={onDragOver}
                  onDrop={() => onDrop(i)}
                  style={{
                    padding: '10px 14px', borderRadius: 10,
                    background: c.bg, border: `1.5px solid ${c.color}`,
                    cursor: mode === 'enrich' ? 'grab' : 'default',
                    minWidth: 60, textAlign: 'center'
                  }}
                >
                  <div style={{ fontWeight: 800, color: c.color, fontSize: '.95rem' }}>{tok.word}</div>
                  <div style={{ fontSize: '.65rem', color: c.color, marginTop: 4, fontWeight: 700 }}>{c.label}</div>
                  <div style={{ fontSize: '.6rem', color: '#94A3B8', marginTop: 2 }}>{tok.pos}</div>
                </div>
              )
            })}
          </div>

          {/* Validity */}
          <div style={{ display: 'flex', gap: 12, marginBottom: 14, flexWrap: 'wrap' }}>
            <Badge ok={result.has_subject} label="Эга бор" />
            <Badge ok={result.has_predicate} label="Кесим бор" />
            <Badge ok={result.valid} label="Тартиб тўғри" />
          </div>

          {/* Errors */}
          {result.errors.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <h4 style={{ fontSize: '.85rem', fontWeight: 700, marginBottom: 8, color: '#DC2626' }}>
                ⚠️ Хатолар ({result.errors.length})
              </h4>
              {result.errors.map((err, i) => (
                <div key={i} style={{
                  padding: '10px 14px', borderRadius: 10, marginBottom: 6,
                  background: '#FEF2F2', border: '1px solid #FECACA',
                  display: 'flex', gap: 10, alignItems: 'flex-start'
                }}>
                  <AlertTriangle size={16} color="#DC2626" />
                  <div style={{ fontSize: '.82rem' }}>
                    <div style={{ fontWeight: 700, color: '#991B1B' }}>{err.message}</div>
                    {err.suggestion && <div style={{ color: '#7F1D1D', marginTop: 4 }}>💡 {err.suggestion}</div>}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Suggestions */}
          {result.suggestions.length > 0 && (
            <div>
              <h4 style={{ fontSize: '.85rem', fontWeight: 700, marginBottom: 8, color: '#D97706' }}>
                💡 Таклифлар ({result.suggestions.length})
              </h4>
              {result.suggestions.map((s, i) => (
                <div key={i} style={{
                  padding: '10px 14px', borderRadius: 10, marginBottom: 6,
                  background: '#FFFBEB', border: '1px solid #FCD34D', fontSize: '.82rem'
                }}>{s.message}</div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function Badge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div style={{
      padding: '6px 12px', borderRadius: 20,
      background: ok ? '#DCFCE7' : '#FEE2E2',
      color: ok ? '#16A34A' : '#DC2626',
      fontSize: '.75rem', fontWeight: 700,
      display: 'flex', alignItems: 'center', gap: 6
    }}>
      {ok ? <CheckCircle2 size={13} /> : <AlertTriangle size={13} />}
      {label}
    </div>
  )
}

const tabBtn = (active: boolean): React.CSSProperties => ({
  padding: '10px 18px', borderRadius: 12, border: active ? '2px solid #B48C64' : '1px solid #E2E8F0',
  background: active ? '#FFF8F0' : 'white', color: active ? '#8B5E3C' : '#64748B',
  fontWeight: 800, fontSize: '.85rem', cursor: 'pointer'
})

const primaryBtn = (loading: boolean): React.CSSProperties => ({
  padding: '8px 18px', borderRadius: 10, border: 'none',
  background: loading ? '#9CA3AF' : 'linear-gradient(135deg, #B48C64, #8B5E3C)',
  color: 'white', fontSize: '.82rem', fontWeight: 700, cursor: loading ? 'not-allowed' : 'pointer',
  display: 'flex', alignItems: 'center', gap: 6
})

const secondaryBtn = (): React.CSSProperties => ({
  padding: '8px 14px', borderRadius: 10, border: '1px solid #E2E8F0',
  background: 'white', fontSize: '.82rem', fontWeight: 600, cursor: 'pointer',
  display: 'flex', alignItems: 'center', gap: 6, color: '#64748B'
})
