'use client'

import React, { useState, useEffect, useRef, useMemo } from 'react'
import { Sparkles, Loader2, Award, Globe, BookPlus, ClipboardPaste, Wand2, ArrowRightLeft, Play, Library } from 'lucide-react'
import { useAuth } from '../../components/LoginGuard'
import api, { TilshunosCheckResult, LinguisticIssue } from '../../services/api'

type Mode = 'edit' | 'translate'
type Lang = 'en' | 'ru' | 'uz-cyr' | 'uz-lat'

const LANG_LABELS: Record<Lang, string> = {
  'en': 'English',
  'ru': 'Русский',
  'uz-cyr': 'Ўзбек (Кирилл)',
  'uz-lat': "O'zbek (Lotin)",
}

const CATEGORY_COLORS: Record<string, string> = {
  orthography: '#DC2626',     // red — imlo (qizil)
  punctuation: '#0EA5E9',     // cyan — punctuation
  syntax: '#9333EA',          // purple — sintaksis
  morphology: '#16A34A',      // green — morfologiya
  grammar: '#EA580C',         // orange — grammatika
  unknown: '#6B7280',
}

const CATEGORY_LABELS: Record<string, string> = {
  orthography: 'Имло',
  punctuation: 'Тиниш',
  syntax: 'Синтаксис',
  morphology: 'Морфология',
  grammar: 'Грамматика',
}

const SEVERITY_LABELS: Record<string, string> = {
  high: 'юқори',
  medium: 'ўртача',
  low: 'паст',
}

// Approximate language detection
function detectLang(text: string): Lang {
  if (!text) return 'uz-lat'
  const cyrCount = (text.match(/[а-яА-ЯёЁўғқҳЎҒҚҲ]/g) || []).length
  const latCount = (text.match(/[a-zA-Z]/g) || []).length
  const ruIndicators = /[ыэъёЁ]|(?:что|это|как|так)/i.test(text)
  if (cyrCount > latCount) return ruIndicators ? 'ru' : 'uz-cyr'
  if (/\b(the|and|of|in|is|was|has|have)\b/i.test(text)) return 'en'
  return 'uz-lat'
}

export default function TilshunosPage() {
  const { token } = useAuth()
  const [mode, setMode] = useState<Mode>('edit')
  const [lang, setLang] = useState<Lang>('uz-lat')
  const [text, setText] = useState('')
  const [result, setResult] = useState<TilshunosCheckResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState<any>(null)
  const [hoveredIssue, setHoveredIssue] = useState<number | null>(null)
  const [popupIssue, setPopupIssue] = useState<{ issue: LinguisticIssue; x: number; y: number; idx: number } | null>(null)

  // Translation mode state
  const [sourceLang, setSourceLang] = useState<Lang>('en')
  const [targetLang, setTargetLang] = useState<Lang>('uz-lat')
  const [sourceText, setSourceText] = useState('')
  const [targetText, setTargetText] = useState('')
  const [sourceResult, setSourceResult] = useState<TilshunosCheckResult | null>(null)
  const [targetResult, setTargetResult] = useState<TilshunosCheckResult | null>(null)
  const [translating, setTranslating] = useState(false)

  // Load stats
  useEffect(() => {
    api.tilshunos.rulesStats().then(setStats).catch(() => {})
  }, [])

  // Auto-detect language on paste
  useEffect(() => {
    if (text && text.length > 5) {
      const detected = detectLang(text)
      if (detected !== lang) setLang(detected)
    }
  }, [text])

  const runCheck = async () => {
    if (!text.trim()) return
    setLoading(true)
    try {
      const backendLang = lang.startsWith('uz') ? 'uz' : lang
      const res = await api.tilshunos.check(text, backendLang)
      setResult(res)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const handlePaste = async () => {
    try {
      const pasted = await navigator.clipboard.readText()
      if (pasted) setText(pasted)
    } catch (_) {}
  }

  const transliterate = async (target: 'cyrillic' | 'latin') => {
    if (!text.trim()) return
    try {
      const res = await fetch(`${api.API_BASE}/api/transliterate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ text, target }),
      })
      if (res.ok) {
        const data = await res.json()
        setText(data.text)
        setLang(target === 'cyrillic' ? 'uz-cyr' : 'uz-lat')
      }
    } catch (_) {}
  }

  const addWordToDictionary = async (word: string) => {
    if (!word.trim()) return
    try {
      await api.dictionary.translate(word)
      alert(`"${word}" луғатга қўшилди`)
    } catch (_) {
      alert('Хатолик юз берди')
    }
  }

  const applyFix = async (idx: number, issue: LinguisticIssue, suggestion: string) => {
    const newText = text.substring(0, issue.from_index) + suggestion + text.substring(issue.to_index)
    setText(newText)
    setPopupIssue(null)
    // Self-learning
    try {
      await api.tilshunos.confirm({
        wrong: issue.matched_text,
        correct: suggestion,
        context: text.substring(Math.max(0, issue.from_index - 50), Math.min(text.length, issue.to_index + 50)),
        category: issue.error_type,
        lang: lang.startsWith('uz') ? 'uz' : lang,
      })
    } catch (_) {}
    // Re-run check
    setTimeout(runCheck, 200)
  }

  // Render text with underlines for errors
  const renderAnnotated = () => {
    if (!result || !result.issues.length) return <div style={{ whiteSpace: 'pre-wrap' }}>{text || <span style={{ color: '#9CA3AF' }}>Матн киритинг...</span>}</div>
    const issues = [...result.issues].sort((a, b) => a.from_index - b.from_index)
    const parts: React.ReactNode[] = []
    let cursor = 0
    issues.forEach((issue, idx) => {
      if (issue.from_index > cursor) {
        parts.push(<span key={`t-${idx}`}>{text.slice(cursor, issue.from_index)}</span>)
      }
      const color = CATEGORY_COLORS[issue.category] || CATEGORY_COLORS.unknown
      parts.push(
        <span
          key={`i-${idx}`}
          onClick={(e) => {
            const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
            setPopupIssue({ issue, x: rect.left, y: rect.bottom + 5, idx })
          }}
          style={{
            borderBottom: `2px solid ${color}`,
            cursor: 'pointer',
            background: hoveredIssue === idx ? `${color}22` : 'transparent',
            padding: '0 1px',
            position: 'relative',
          }}
          onMouseEnter={() => setHoveredIssue(idx)}
          onMouseLeave={() => setHoveredIssue(null)}
          title={issue.message}
        >
          {text.slice(issue.from_index, issue.to_index)}
        </span>
      )
      cursor = issue.to_index
    })
    if (cursor < text.length) parts.push(<span key="end">{text.slice(cursor)}</span>)
    return <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.8 }}>{parts}</div>
  }

  const categoryCounts = result?.by_category || {}
  const severityCounts = result?.by_severity || {}

  return (
    <div style={{ maxWidth: 1600, margin: '0 auto', padding: '0 4px' }}>
      {/* Hero */}
      <div style={{
        background: 'linear-gradient(135deg, #FFF8F0 0%, #FFEFDC 100%)',
        borderRadius: 18, padding: '20px 28px', border: '1.5px solid #FDE3C5',
        marginBottom: 16, display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap',
      }}>
        <div style={{
          width: 48, height: 48, borderRadius: 14,
          background: 'linear-gradient(135deg, #B48C64, #8B5E3C)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Award size={24} color="white" />
        </div>
        <div style={{ flex: 1 }}>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 800, marginBottom: 2 }}>Тилшунос</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.82rem', margin: 0 }}>
            Илмий таҳрир ва илмий таржима: имло, синтаксис, пунктуация, морфология, грамматика
          </p>
        </div>

        {/* Mode tabs */}
        <div style={{ display: 'flex', gap: 6, background: 'white', borderRadius: 10, padding: 4, border: '1.5px solid var(--border)' }}>
          <button
            onClick={() => setMode('edit')}
            style={{
              padding: '8px 14px',
              background: mode === 'edit' ? 'linear-gradient(135deg, #B48C64, #8B5E3C)' : 'transparent',
              color: mode === 'edit' ? 'white' : 'var(--text-primary)',
              border: 'none',
              borderRadius: 7,
              fontWeight: 700, fontSize: '0.78rem', cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 5,
            }}>
            <Wand2 size={13} /> Илмий таҳрир
          </button>
          <button
            onClick={() => setMode('translate')}
            style={{
              padding: '8px 14px',
              background: mode === 'translate' ? 'linear-gradient(135deg, #B48C64, #8B5E3C)' : 'transparent',
              color: mode === 'translate' ? 'white' : 'var(--text-primary)',
              border: 'none',
              borderRadius: 7,
              fontWeight: 700, fontSize: '0.78rem', cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 5,
            }}>
            <ArrowRightLeft size={13} /> Илмий таржима
          </button>
        </div>
      </div>

      {/* Stats pills */}
      {stats && (
        <div style={{ display: 'flex', gap: 8, marginBottom: 14, flexWrap: 'wrap', fontSize: '0.7rem' }}>
          <StatPill label="Hunspell" value={(stats.hunspell?.lat_words || 0) + (stats.hunspell?.cyr_words || 0)} color="#D97706" />
          <StatPill label="Tahrirchi" value={stats.tahrirchi_lexicon_words || 0} color="#0EA5E9" />
          <StatPill label="Sayqallash" value={stats.sayqallash_total || 0} color="#9333EA" />
          <StatPill label="Канон" value={stats.canonical_rules?.total || 0} color="#16A34A" />
          <StatPill label="Синонимлар" value={stats.platform_databases?.synonyms || 0} color="#DB2777" />
          <StatPill label="Изоҳли" value={stats.platform_databases?.annotated_words || 0} color="#2563EB" />
          <StatPill label="Мунозарали" value={stats.platform_databases?.disputed_words || 0} color="#EA580C" />
          <StatPill label="Қисқартмалар" value={stats.platform_databases?.abbreviations || 0} color="#059669" />
        </div>
      )}

      {mode === 'edit' ? (
        /* ───────────── EDIT MODE ───────────── */
        <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: 14, minHeight: '70vh' }}>
          {/* Sidebar */}
          <div style={{
            background: 'var(--bg-card)', border: '1.5px solid var(--border)', borderRadius: 12, padding: 14,
            position: 'sticky', top: 14, alignSelf: 'flex-start', maxHeight: 'calc(100vh - 40px)', overflowY: 'auto',
          }}>
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Сифат баҳоси</div>
              <div style={{ fontSize: '2.4rem', fontWeight: 800, color: result ? (result.score >= 0.9 ? '#16A34A' : result.score >= 0.6 ? '#D97706' : '#DC2626') : '#9CA3AF' }}>
                {result ? Math.round(result.score * 100) : '—'}<span style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-muted)' }}>/100</span>
              </div>
            </div>

            {result && (
              <>
                <div style={{ marginBottom: 12 }}>
                  <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>Категориялар</div>
                  {Object.entries(categoryCounts).map(([cat, n]) => (
                    <div key={cat} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3, fontSize: '0.72rem' }}>
                      <span style={{ width: 8, height: 8, borderRadius: '50%', background: CATEGORY_COLORS[cat] || '#6B7280' }} />
                      <span>{CATEGORY_LABELS[cat] || cat}</span>
                      <span style={{ marginLeft: 'auto', fontWeight: 700 }}>{n}</span>
                    </div>
                  ))}
                </div>

                <div style={{ marginBottom: 12 }}>
                  <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>Даражалар</div>
                  {Object.entries(severityCounts).map(([sev, n]) => n > 0 && (
                    <div key={sev} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3, fontSize: '0.72rem' }}>
                      <span>{SEVERITY_LABELS[sev] || sev}</span>
                      <span style={{ marginLeft: 'auto', fontWeight: 700, color: sev === 'high' ? '#DC2626' : sev === 'medium' ? '#D97706' : '#16A34A' }}>{n}</span>
                    </div>
                  ))}
                </div>

                <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>Хатолар рўйхати</div>
                <div style={{ fontSize: '0.7rem' }}>
                  {result.issues.length === 0 && <div style={{ color: '#16A34A', padding: 6 }}>✅ Хато йўқ</div>}
                  {result.issues.slice(0, 50).map((iss, i) => (
                    <div key={i}
                      onMouseEnter={() => setHoveredIssue(i)}
                      onMouseLeave={() => setHoveredIssue(null)}
                      style={{
                        padding: 6, marginBottom: 3,
                        borderLeft: `3px solid ${CATEGORY_COLORS[iss.category] || '#6B7280'}`,
                        background: hoveredIssue === i ? '#FFF8F0' : 'transparent',
                        borderRadius: '0 4px 4px 0',
                        cursor: 'pointer',
                      }}>
                      <div style={{ fontWeight: 700, fontSize: '0.7rem' }}>
                        <span style={{ textDecoration: 'line-through', color: '#991B1B' }}>{iss.matched_text}</span>
                        {iss.suggestion && <>  →  <span style={{ color: '#16A34A' }}>{iss.suggestion}</span></>}
                      </div>
                      <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>
                        {CATEGORY_LABELS[iss.category] || iss.category} · {iss.error_type}
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>

          {/* Main editor */}
          <div style={{ background: 'var(--bg-card)', border: '1.5px solid var(--border)', borderRadius: 12, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            {/* Toolbar */}
            <div style={{ padding: 10, borderBottom: '1.5px solid var(--border)', display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
              <select value={lang} onChange={e => setLang(e.target.value as Lang)} style={{ padding: '6px 10px', borderRadius: 7, border: '1.5px solid var(--border)', fontSize: '0.78rem', fontWeight: 600 }}>
                <option value="en">🇬🇧 English</option>
                <option value="ru">🇷🇺 Русский</option>
                <option value="uz-cyr">🇺🇿 Ўзбек (Кирилл)</option>
                <option value="uz-lat">🇺🇿 O'zbek (Lotin)</option>
              </select>

              <button onClick={handlePaste} style={toolbarBtn}><ClipboardPaste size={13} /> Жойлаш</button>

              {lang.startsWith('uz') && (
                <>
                  <button onClick={() => transliterate('cyrillic')} style={{ ...toolbarBtn, background: '#FFF7ED', color: '#EA580C', borderColor: '#FB923C' }}>Кирил</button>
                  <button onClick={() => transliterate('latin')} style={{ ...toolbarBtn, background: '#F0FDF4', color: '#16A34A', borderColor: '#22C55E' }}>Лотин</button>
                </>
              )}

              <button onClick={() => {
                const sel = window.getSelection()?.toString().trim()
                if (sel) addWordToDictionary(sel)
                else alert('Сўзни белгиланг')
              }} style={toolbarBtn}><BookPlus size={13} /> Луғатга қўшиш</button>

              <button onClick={runCheck} disabled={loading || !text.trim()} style={{ ...toolbarBtn, marginLeft: 'auto', background: 'linear-gradient(135deg,#10B981,#059669)', color: 'white', border: 'none', padding: '8px 16px' }}>
                {loading ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />} Синов олиб бориш
              </button>
            </div>

            {/* Editor area */}
            <div style={{ padding: 18, flex: 1, display: 'flex', flexDirection: 'column', gap: 12 }}>
              <textarea
                value={text}
                onChange={e => setText(e.target.value)}
                placeholder="Матнни бу ерга жойланг ёки ёзинг. Сўнг «Синов олиб бориш» тугмасини босинг."
                style={{
                  width: '100%', minHeight: 250, padding: 14, border: '1.5px solid var(--border)',
                  borderRadius: 10, fontSize: '0.92rem', fontFamily: 'inherit', resize: 'vertical',
                  outline: 'none', background: 'var(--bg-secondary)', lineHeight: 1.6,
                }}
              />

              {/* Annotated preview (shows after check) */}
              {result && (
                <div style={{
                  padding: 14, background: '#FFF8F0', border: '1.5px solid #FDE3C5', borderRadius: 10,
                  fontSize: '0.92rem', lineHeight: 1.8, minHeight: 100,
                }}>
                  <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 6, fontWeight: 700 }}>
                    ТАҲЛИЛ НАТИЖАСИ ({result.total} хато)
                  </div>
                  {renderAnnotated()}
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        /* ───────────── TRANSLATE MODE ───────────── */
        <div>
          <div style={{ display: 'flex', gap: 10, marginBottom: 10, alignItems: 'center' }}>
            <select value={sourceLang} onChange={e => setSourceLang(e.target.value as Lang)} style={{ padding: '8px 12px', borderRadius: 8, border: '1.5px solid var(--border)', fontWeight: 600 }}>
              <option value="en">🇬🇧 English</option>
              <option value="ru">🇷🇺 Русский</option>
              <option value="uz-cyr">🇺🇿 Ўзбек (Кирилл)</option>
              <option value="uz-lat">🇺🇿 O'zbek (Lotin)</option>
            </select>
            <ArrowRightLeft size={18} color="#6B7280" />
            <select value={targetLang} onChange={e => setTargetLang(e.target.value as Lang)} style={{ padding: '8px 12px', borderRadius: 8, border: '1.5px solid var(--border)', fontWeight: 600 }}>
              <option value="en">🇬🇧 English</option>
              <option value="ru">🇷🇺 Русский</option>
              <option value="uz-cyr">🇺🇿 Ўзбек (Кирилл)</option>
              <option value="uz-lat">🇺🇿 O'zbek (Lotin)</option>
            </select>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, minHeight: 360 }}>
            <div style={{ background: 'var(--bg-card)', border: '1.5px solid var(--border)', borderRadius: 12, padding: 14 }}>
              <div style={{ fontSize: '0.72rem', fontWeight: 700, marginBottom: 8, color: 'var(--text-muted)' }}>{LANG_LABELS[sourceLang]}</div>
              <textarea value={sourceText} onChange={e => setSourceText(e.target.value)} placeholder="Асл матн..." style={{ width: '100%', minHeight: 240, padding: 10, border: '1.5px solid var(--border)', borderRadius: 8, fontSize: '0.88rem', fontFamily: 'inherit', resize: 'vertical', outline: 'none', background: 'var(--bg-secondary)' }} />
            </div>
            <div style={{ background: 'var(--bg-card)', border: '1.5px solid var(--border)', borderRadius: 12, padding: 14 }}>
              <div style={{ fontSize: '0.72rem', fontWeight: 700, marginBottom: 8, color: 'var(--text-muted)' }}>{LANG_LABELS[targetLang]}</div>
              <textarea value={targetText} onChange={e => setTargetText(e.target.value)} placeholder="Таржима..." style={{ width: '100%', minHeight: 240, padding: 10, border: '1.5px solid var(--border)', borderRadius: 8, fontSize: '0.88rem', fontFamily: 'inherit', resize: 'vertical', outline: 'none', background: 'var(--bg-secondary)' }} />
            </div>
          </div>
        </div>
      )}

      {/* Popup for clicked error */}
      {popupIssue && (
        <>
          <div onClick={() => setPopupIssue(null)} style={{ position: 'fixed', inset: 0, zIndex: 90 }} />
          <div style={{
            position: 'fixed',
            left: Math.min(popupIssue.x, window.innerWidth - 280),
            top: Math.min(popupIssue.y, window.innerHeight - 260),
            background: 'white',
            border: '1.5px solid var(--border)',
            borderRadius: 10,
            boxShadow: '0 8px 24px rgba(0,0,0,0.15)',
            zIndex: 100,
            minWidth: 260,
            maxWidth: 320,
            padding: 12,
            fontSize: '0.8rem',
          }}>
            <div style={{
              display: 'inline-block', padding: '2px 8px', borderRadius: 6,
              background: CATEGORY_COLORS[popupIssue.issue.category] || '#6B7280',
              color: 'white', fontSize: '0.6rem', fontWeight: 700, textTransform: 'uppercase',
              marginBottom: 6,
            }}>
              {CATEGORY_LABELS[popupIssue.issue.category] || popupIssue.issue.category} · {popupIssue.issue.error_type}
            </div>
            <div style={{ color: '#374151', marginBottom: 10, fontSize: '0.78rem' }}>
              {popupIssue.issue.message}
            </div>
            <div style={{ borderTop: '1px solid #E5E7EB', paddingTop: 8 }}>
              <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', marginBottom: 4 }}>ТАКЛИФЛАР</div>
              {((popupIssue.issue as any).suggestions?.length
                ? (popupIssue.issue as any).suggestions
                : [popupIssue.issue.suggestion]
              ).filter((s: string) => s).slice(0, 5).map((sugg: string, i: number) => (
                <button key={i}
                  onClick={() => applyFix(popupIssue.idx, popupIssue.issue, sugg)}
                  style={{
                    display: 'block', width: '100%', textAlign: 'left',
                    padding: '6px 10px', marginBottom: 4,
                    background: '#F0FDF4', border: '1.5px solid #86EFAC', borderRadius: 6,
                    color: '#166534', fontSize: '0.78rem', fontWeight: 600, cursor: 'pointer',
                  }}>
                  → {sugg}
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

const toolbarBtn: React.CSSProperties = {
  padding: '6px 12px',
  background: 'white',
  color: 'var(--text-primary)',
  border: '1.5px solid var(--border)',
  borderRadius: 7,
  fontWeight: 600,
  fontSize: '0.75rem',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  gap: 5,
}

function StatPill({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{
      padding: '4px 10px',
      background: `${color}15`,
      border: `1.5px solid ${color}40`,
      borderRadius: 999,
      display: 'flex',
      alignItems: 'center',
      gap: 6,
      fontWeight: 600,
    }}>
      <span style={{ color: '#6B7280' }}>{label}:</span>
      <span style={{ color, fontWeight: 800 }}>{value.toLocaleString()}</span>
    </div>
  )
}
