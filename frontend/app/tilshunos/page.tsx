'use client'

import React, { useState, useEffect, useRef, useCallback } from 'react'
import { Loader2, Award, BookPlus, ClipboardPaste, Wand2, ArrowRightLeft, Play, Upload, Trash2 } from 'lucide-react'
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

// Error category colors (for underlines/borders)
const CAT_COLORS: Record<string, string> = {
  orthography: '#DC2626',
  punctuation: '#0EA5E9',
  syntax: '#9333EA',
  morphology: '#16A34A',
  grammar: '#EA580C',
  unknown: '#6B7280',
}

const CAT_LABELS: Record<string, string> = {
  orthography: 'Имло',
  punctuation: 'Тиниш',
  syntax: 'Синтаксис',
  morphology: 'Морфология',
  grammar: 'Грамматика',
}

// Word classification colors (background highlight for known/annotated/disputed)
const WORD_COLORS: Record<string, string> = {
  known: '#1E40AF',         // dark blue — in Hunspell dict
  annotated: '#0891B2',     // teal — in annotated_words
  disputed: '#F97316',      // orange — in disputed_words
  abbreviation: '#6366F1',  // indigo — in abbreviations
}

const SEV_LABELS: Record<string, string> = { high: 'юқори', medium: 'ўртача', low: 'паст' }

function detectLang(text: string): Lang {
  if (!text) return 'uz-lat'
  const cyr = (text.match(/[а-яА-ЯёЁўғқҳЎҒҚҲ]/g) || []).length
  const lat = (text.match(/[a-zA-Z]/g) || []).length
  const ruIndic = /[ыэъёЁ]|(?:что|это|как|так)/i.test(text)
  if (cyr > lat) return ruIndic ? 'ru' : 'uz-cyr'
  if (/\b(the|and|of|in|is|was|has|have)\b/i.test(text)) return 'en'
  return 'uz-lat'
}

interface WordSpan {
  from: number
  to: number
  word: string
  category: 'known' | 'annotated' | 'disputed' | 'abbreviation' | 'unknown'
}

export default function TilshunosPage() {
  const { token } = useAuth()
  const [mode, setMode] = useState<Mode>('edit')
  const [lang, setLang] = useState<Lang>('uz-lat')
  const [text, setText] = useState('')
  const [result, setResult] = useState<TilshunosCheckResult | null>(null)
  const [classified, setClassified] = useState<WordSpan[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState<any>(null)
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null)
  const [popup, setPopup] = useState<{ issue: LinguisticIssue; x: number; y: number } | null>(null)
  const [synPopup, setSynPopup] = useState<{ word: string; x: number; y: number; options: string[] } | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Translation mode
  const [sourceLang, setSourceLang] = useState<Lang>('en')
  const [targetLang, setTargetLang] = useState<Lang>('uz-lat')
  const [sourceText, setSourceText] = useState('')
  const [targetText, setTargetText] = useState('')

  useEffect(() => {
    api.tilshunos.rulesStats().then(setStats).catch(() => {})
  }, [])

  useEffect(() => {
    if (text && text.length > 5) {
      const d = detectLang(text)
      if (d !== lang) setLang(d)
    }
  }, [text])

  // Run check + classify in parallel
  const runCheck = useCallback(async () => {
    if (!text.trim()) return
    setLoading(true)
    setPopup(null)
    const backendLang = lang.startsWith('uz') ? 'uz' : lang
    try {
      const [checkRes, classifyRes] = await Promise.all([
        api.tilshunos.check(text, backendLang),
        backendLang === 'uz' ? api.tilshunos.classify(text, backendLang) : Promise.resolve({ spans: [], counts: {} }),
      ])
      setResult(checkRes)
      setClassified(classifyRes.spans || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [text, lang])

  const handlePaste = async () => {
    try {
      const pasted = await navigator.clipboard.readText()
      if (pasted) {
        setText(pasted)
        setResult(null)
        setClassified(null)
      }
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
        setResult(null)
        setClassified(null)
      }
    } catch (_) {}
  }

  const addWordToDictionary = async () => {
    const sel = window.getSelection()?.toString().trim()
    if (!sel) {
      alert('Аввал матндан сўзни белгиланг')
      return
    }
    try {
      await api.dictionary.translate(sel)
      alert(`"${sel}" луғатга қўшилди`)
    } catch (_) {
      alert('Хатолик')
    }
  }

  const openSynonymsForSelection = async () => {
    const sel = window.getSelection()?.toString().trim()
    if (!sel || !textareaRef.current) {
      alert('Сўзни белгиланг')
      return
    }
    try {
      const res = await api.synonyms.list(sel)
      const options = (res as any).synonyms?.map((s: any) => s.synonym) || []
      const rect = textareaRef.current.getBoundingClientRect()
      setSynPopup({
        word: sel,
        x: rect.left + rect.width / 2 - 120,
        y: rect.top + 80,
        options,
      })
    } catch (_) {
      alert('Синонимлар олишда хатолик')
    }
  }

  const applyFix = async (issue: LinguisticIssue, suggestion: string) => {
    const newText = text.substring(0, issue.from_index) + suggestion + text.substring(issue.to_index)
    setText(newText)
    setPopup(null)
    // NOTE: do NOT clear result/classified — keep colored view stable while re-check runs

    const backendLang = lang.startsWith('uz') ? 'uz' : lang

    // Self-learning (fire-and-forget, doesn't block UI)
    api.tilshunos.confirm({
      wrong: issue.matched_text,
      correct: suggestion,
      context: text.substring(Math.max(0, issue.from_index - 50), Math.min(text.length, issue.to_index + 50)),
      category: issue.error_type,
      lang: backendLang,
    }).catch(() => {})

    // Re-run check + classify in parallel, atomically swap when both done — no flicker
    try {
      const [checkRes, classifyRes] = await Promise.all([
        api.tilshunos.check(newText, backendLang),
        backendLang === 'uz'
          ? api.tilshunos.classify(newText, 'uz')
          : Promise.resolve({ spans: [], counts: {} } as any),
      ])
      setResult(checkRes)
      setClassified(classifyRes.spans || [])
    } catch (_) {}
  }

  // Render annotated text as HTML — words colored by classification + errors underlined
  const renderAnnotated = () => {
    if (!text) return <span style={{ color: '#9CA3AF' }}>Матн киритинг ва «Синов олиб бориш» тугмасини босинг...</span>
    if (!result) return <div style={{ whiteSpace: 'pre-wrap' }}>{text}</div>

    // Merge errors + classification into non-overlapping spans
    type Span = {
      from: number
      to: number
      issue?: LinguisticIssue
      issueIdx?: number
      wordCategory?: string
    }
    const spans: Span[] = []

    // Errors first (higher priority)
    const issues = [...(result.issues || [])].sort((a, b) => a.from_index - b.from_index)
    const errorSet = new Set<string>()
    issues.forEach((iss, idx) => {
      const key = `${iss.from_index}-${iss.to_index}`
      if (!errorSet.has(key)) {
        spans.push({ from: iss.from_index, to: iss.to_index, issue: iss, issueIdx: idx })
        errorSet.add(key)
      }
    })

    // Classifications for words not already covered by errors
    if (classified) {
      for (const c of classified) {
        const overlapsError = issues.some(i =>
          (c.from >= i.from_index && c.from < i.to_index) ||
          (c.to > i.from_index && c.to <= i.to_index)
        )
        if (!overlapsError && c.category !== 'unknown') {
          spans.push({ from: c.from, to: c.to, wordCategory: c.category })
        }
      }
    }

    spans.sort((a, b) => a.from - b.from || a.to - b.to)

    const parts: React.ReactNode[] = []
    let cursor = 0
    spans.forEach((s, i) => {
      if (s.from > cursor) {
        parts.push(<span key={`t${i}`}>{text.slice(cursor, s.from)}</span>)
      }
      if (s.from < cursor) return // overlap — skip
      const content = text.slice(s.from, s.to)
      if (s.issue) {
        const color = CAT_COLORS[s.issue.category] || CAT_COLORS.unknown
        parts.push(
          <span key={`e${i}`}
            onClick={(e) => {
              e.stopPropagation()
              const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
              setPopup({ issue: s.issue!, x: rect.left, y: rect.bottom + 6 })
            }}
            onMouseEnter={() => setHoveredIdx(s.issueIdx!)}
            onMouseLeave={() => setHoveredIdx(null)}
            style={{
              borderBottom: `3px solid ${color}`,
              cursor: 'pointer',
              background: hoveredIdx === s.issueIdx ? `${color}22` : 'transparent',
              padding: '0 1px',
            }}
            title={s.issue.message}
          >{content}</span>
        )
      } else if (s.wordCategory) {
        const color = WORD_COLORS[s.wordCategory]
        parts.push(
          <span key={`w${i}`}
            style={{
              color,
              fontWeight: s.wordCategory === 'known' ? 500 : 700,
              background: s.wordCategory !== 'known' ? `${color}18` : 'transparent',
              padding: s.wordCategory !== 'known' ? '0 2px' : 0,
              borderRadius: 3,
            }}
            title={s.wordCategory}
          >{content}</span>
        )
      }
      cursor = Math.max(cursor, s.to)
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
        borderRadius: 18, padding: '18px 26px', border: '1.5px solid #FDE3C5',
        marginBottom: 14, display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap',
      }}>
        <div style={{
          width: 46, height: 46, borderRadius: 12,
          background: 'linear-gradient(135deg, #B48C64, #8B5E3C)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Award size={22} color="white" />
        </div>
        <div style={{ flex: 1, minWidth: 200 }}>
          <h1 style={{ fontSize: '1.4rem', fontWeight: 800, marginBottom: 2 }}>Тилшунос</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', margin: 0 }}>
            Имло, синтаксис, пунктуация, морфология, грамматика
          </p>
        </div>
        <div style={{ display: 'flex', gap: 6, background: 'white', borderRadius: 10, padding: 4, border: '1.5px solid var(--border)' }}>
          <button onClick={() => setMode('edit')}
            style={{
              padding: '8px 14px',
              background: mode === 'edit' ? 'linear-gradient(135deg, #B48C64, #8B5E3C)' : 'transparent',
              color: mode === 'edit' ? 'white' : 'var(--text-primary)',
              border: 'none', borderRadius: 7,
              fontWeight: 700, fontSize: '0.78rem', cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 5,
            }}>
            <Wand2 size={13} /> Илмий таҳрир
          </button>
          <button onClick={() => setMode('translate')}
            style={{
              padding: '8px 14px',
              background: mode === 'translate' ? 'linear-gradient(135deg, #B48C64, #8B5E3C)' : 'transparent',
              color: mode === 'translate' ? 'white' : 'var(--text-primary)',
              border: 'none', borderRadius: 7,
              fontWeight: 700, fontSize: '0.78rem', cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 5,
            }}>
            <ArrowRightLeft size={13} /> Илмий таржима
          </button>
        </div>
      </div>

      {/* Stats pills */}
      {stats && (
        <div style={{ display: 'flex', gap: 7, marginBottom: 12, flexWrap: 'wrap', fontSize: '0.68rem' }}>
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
        /* ───────── EDIT MODE ───────── */
        <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: 14, minHeight: '70vh' }}>
          {/* Sidebar */}
          <div style={{
            background: 'var(--bg-card)', border: '1.5px solid var(--border)', borderRadius: 12, padding: 14,
            position: 'sticky', top: 14, alignSelf: 'flex-start', maxHeight: 'calc(100vh - 40px)', overflowY: 'auto',
          }}>
            <div style={{ marginBottom: 10 }}>
              <div style={{ fontSize: '0.58rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Сифат баҳоси</div>
              <div style={{ fontSize: '2.2rem', fontWeight: 800, lineHeight: 1,
                color: result ? (result.score >= 0.9 ? '#16A34A' : result.score >= 0.6 ? '#D97706' : '#DC2626') : '#9CA3AF' }}>
                {result ? Math.round(result.score * 100) : '—'}
                <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)' }}>/100</span>
              </div>
            </div>

            {result && (
              <>
                <div style={{ marginBottom: 10 }}>
                  <div style={{ fontSize: '0.58rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 3 }}>Категориялар</div>
                  {Object.entries(categoryCounts).map(([cat, n]) => (
                    <div key={cat} style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 2, fontSize: '0.7rem' }}>
                      <span style={{ width: 8, height: 8, borderRadius: '50%', background: CAT_COLORS[cat] || '#6B7280' }} />
                      <span>{CAT_LABELS[cat] || cat}</span>
                      <span style={{ marginLeft: 'auto', fontWeight: 700 }}>{n}</span>
                    </div>
                  ))}
                </div>

                <div style={{ marginBottom: 10 }}>
                  <div style={{ fontSize: '0.58rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 3 }}>Даражалар</div>
                  {Object.entries(severityCounts).map(([sev, n]) => (n as number) > 0 && (
                    <div key={sev} style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 2, fontSize: '0.7rem' }}>
                      <span>{SEV_LABELS[sev] || sev}</span>
                      <span style={{ marginLeft: 'auto', fontWeight: 700, color: sev === 'high' ? '#DC2626' : sev === 'medium' ? '#D97706' : '#16A34A' }}>{n as number}</span>
                    </div>
                  ))}
                </div>

                <div style={{ fontSize: '0.58rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>Хатолар рўйхати</div>
                <div style={{ fontSize: '0.68rem' }}>
                  {result.issues.length === 0 && <div style={{ color: '#16A34A', padding: 5 }}>✅ Хато йўқ</div>}
                  {result.issues.slice(0, 50).map((iss, i) => (
                    <div key={i}
                      onMouseEnter={() => setHoveredIdx(i)}
                      onMouseLeave={() => setHoveredIdx(null)}
                      style={{
                        padding: 5, marginBottom: 2,
                        borderLeft: `3px solid ${CAT_COLORS[iss.category] || '#6B7280'}`,
                        background: hoveredIdx === i ? '#FFF8F0' : 'transparent',
                        borderRadius: '0 4px 4px 0',
                        cursor: 'pointer',
                      }}>
                      <div style={{ fontSize: '0.68rem', fontWeight: 700 }}>
                        <span style={{ textDecoration: 'line-through', color: '#991B1B' }}>{iss.matched_text}</span>
                        {iss.suggestion && <>  →  <span style={{ color: '#16A34A' }}>{iss.suggestion}</span></>}
                      </div>
                      <div style={{ fontSize: '0.58rem', color: 'var(--text-muted)' }}>
                        {CAT_LABELS[iss.category] || iss.category} · {iss.error_type}
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
              <select value={lang} onChange={e => { setLang(e.target.value as Lang); setResult(null); setClassified(null) }}
                style={{ padding: '6px 10px', borderRadius: 7, border: '1.5px solid var(--border)', fontSize: '0.78rem', fontWeight: 600 }}>
                <option value="en">🇬🇧 English</option>
                <option value="ru">🇷🇺 Русский</option>
                <option value="uz-cyr">🇺🇿 Ўзбек (Кирилл)</option>
                <option value="uz-lat">🇺🇿 O'zbek (Lotin)</option>
              </select>

              <button onClick={handlePaste} style={toolbarBtn}><ClipboardPaste size={13} /> Жойлаш</button>

              <label style={{ ...toolbarBtn, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                <Upload size={13} /> Файлдан юклаш
                <input
                  type="file"
                  accept=".txt,.md,.csv,text/plain"
                  style={{ display: 'none' }}
                  onChange={async (e) => {
                    const f = e.target.files?.[0]
                    if (!f) return
                    const txt = await f.text()
                    setText(txt)
                    setResult(null)
                    setClassified(null)
                    e.target.value = ''
                  }}
                />
              </label>

              <button
                onClick={() => { setText(''); setResult(null); setClassified(null); setPopup(null) }}
                disabled={!text}
                style={{ ...toolbarBtn, background: '#FEF2F2', color: '#DC2626', borderColor: '#FCA5A5', opacity: text ? 1 : 0.5 }}
              >
                <Trash2 size={13} /> Тозалаш
              </button>

              {lang.startsWith('uz') && (
                <>
                  <button onClick={() => transliterate('cyrillic')} style={{ ...toolbarBtn, background: '#FFF7ED', color: '#EA580C', borderColor: '#FB923C' }}>Кирил</button>
                  <button onClick={() => transliterate('latin')} style={{ ...toolbarBtn, background: '#F0FDF4', color: '#16A34A', borderColor: '#22C55E' }}>Лотин</button>
                </>
              )}

              <button onClick={openSynonymsForSelection} style={toolbarBtn}>Синонимлар</button>
              <button onClick={addWordToDictionary} style={toolbarBtn}><BookPlus size={13} /> Луғатга қўшиш</button>

              {result && (
                <button onClick={() => { setResult(null); setClassified(null); setPopup(null) }}
                  style={{ ...toolbarBtn, marginLeft: 'auto', background: '#FEF3C7', color: '#92400E', borderColor: '#FCD34D' }}>
                  ✎ Қайта таҳрир
                </button>
              )}
              <button onClick={runCheck} disabled={loading || !text.trim()}
                style={{ ...toolbarBtn, marginLeft: result ? 0 : 'auto', background: 'linear-gradient(135deg,#10B981,#059669)', color: 'white', border: 'none', padding: '8px 18px' }}>
                {loading ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />} Синов олиб бориш
              </button>
            </div>

            {/* Single editor area: textarea when no result, annotated view when result */}
            <div style={{ padding: 18, flex: 1, display: 'flex', flexDirection: 'column' }}>
              {!result ? (
                <textarea
                  ref={textareaRef}
                  value={text}
                  onChange={e => { setText(e.target.value); if (result) { setResult(null); setClassified(null) } }}
                  placeholder="Матнни бу ерга жойланг ёки ёзинг. Сўнг «Синов олиб бориш» тугмасини босинг."
                  style={{
                    width: '100%', flex: 1, minHeight: 400, padding: 14,
                    border: '1.5px solid var(--border)', borderRadius: 10,
                    fontSize: '0.95rem', fontFamily: 'inherit', resize: 'vertical',
                    outline: 'none', background: 'var(--bg-secondary)', lineHeight: 1.7,
                  }}
                />
              ) : (
                <div
                  style={{
                    width: '100%', padding: 14,
                    border: '1.5px solid var(--border)', borderRadius: 10,
                    fontSize: '0.95rem', fontFamily: 'inherit',
                    background: 'var(--bg-secondary)', lineHeight: 1.85,
                    cursor: 'default',
                    overflow: 'auto',
                  }}
                >
                  {renderAnnotated()}
                </div>
              )}

              {/* Tip + Color legend (compact) */}
              {(result || classified) && (
                <div style={{ marginTop: 8, padding: '8px 12px', background: 'var(--bg-secondary)', border: '1px dashed var(--border)', borderRadius: 8 }}>
                  <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginBottom: 6 }}>
                    💡 Хато устида босинг — тўғри шакл таклиф қилинади. «Қайта таҳрир» тугмаси билан матнни тахрир қилишга қайтиш мумкин.
                  </div>
                  <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                    <LegendDot color="#DC2626" label="Имло хато" />
                    <LegendDot color="#EA580C" label="Грамматика" />
                    <LegendDot color="#16A34A" label="Морфология" />
                    <LegendDot color="#1E40AF" label="Луғатда бор" />
                    <LegendDot color="#0891B2" label="Изоҳли" />
                    <LegendDot color="#F97316" label="Мунозарали" />
                    <LegendDot color="#6366F1" label="Қисқартма" />
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        /* ───────── TRANSLATE MODE ───────── */
        <div>
          <div style={{ display: 'flex', gap: 10, marginBottom: 10, alignItems: 'center', flexWrap: 'wrap' }}>
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
              <textarea value={sourceText} onChange={e => setSourceText(e.target.value)} placeholder="Асл матн..." style={{ width: '100%', minHeight: 300, padding: 10, border: '1.5px solid var(--border)', borderRadius: 8, fontSize: '0.88rem', fontFamily: 'inherit', resize: 'vertical', outline: 'none', background: 'var(--bg-secondary)' }} />
            </div>
            <div style={{ background: 'var(--bg-card)', border: '1.5px solid var(--border)', borderRadius: 12, padding: 14 }}>
              <div style={{ fontSize: '0.72rem', fontWeight: 700, marginBottom: 8, color: 'var(--text-muted)' }}>{LANG_LABELS[targetLang]}</div>
              <textarea value={targetText} onChange={e => setTargetText(e.target.value)} placeholder="Таржима..." style={{ width: '100%', minHeight: 300, padding: 10, border: '1.5px solid var(--border)', borderRadius: 8, fontSize: '0.88rem', fontFamily: 'inherit', resize: 'vertical', outline: 'none', background: 'var(--bg-secondary)' }} />
            </div>
          </div>
        </div>
      )}

      {/* Error popup */}
      {popup && (
        <>
          <div onClick={() => setPopup(null)} style={{ position: 'fixed', inset: 0, zIndex: 90 }} />
          <div style={{
            position: 'fixed',
            left: Math.min(popup.x, window.innerWidth - 300),
            top: Math.min(popup.y, window.innerHeight - 300),
            background: 'white',
            border: '1.5px solid var(--border)',
            borderRadius: 10,
            boxShadow: '0 8px 24px rgba(0,0,0,0.15)',
            zIndex: 100,
            minWidth: 260, maxWidth: 340,
            padding: 12, fontSize: '0.8rem',
          }}>
            <div style={{
              display: 'inline-block', padding: '2px 8px', borderRadius: 6,
              background: CAT_COLORS[popup.issue.category] || '#6B7280',
              color: 'white', fontSize: '0.6rem', fontWeight: 700, textTransform: 'uppercase',
              marginBottom: 6,
            }}>
              {CAT_LABELS[popup.issue.category] || popup.issue.category} · {popup.issue.error_type}
            </div>
            <div style={{ color: '#374151', marginBottom: 10, fontSize: '0.78rem' }}>
              {popup.issue.message}
            </div>
            <div style={{ borderTop: '1px solid #E5E7EB', paddingTop: 8 }}>
              <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', marginBottom: 4 }}>ТАКЛИФЛАР</div>
              {(() => {
                const suggs: string[] = ((popup.issue as any).suggestions?.length
                  ? (popup.issue as any).suggestions
                  : [popup.issue.suggestion]).filter((s: string) => s)
                if (suggs.length === 0) return <div style={{ fontSize: '0.7rem', color: '#9CA3AF' }}>Таклиф йўқ</div>
                return suggs.slice(0, 5).map((sugg, i) => (
                  <button key={i} onClick={() => applyFix(popup.issue, sugg)}
                    style={{
                      display: 'block', width: '100%', textAlign: 'left',
                      padding: '6px 10px', marginBottom: 4,
                      background: '#F0FDF4', border: '1.5px solid #86EFAC', borderRadius: 6,
                      color: '#166534', fontSize: '0.78rem', fontWeight: 600, cursor: 'pointer',
                    }}>
                    → {sugg}
                  </button>
                ))
              })()}
            </div>
          </div>
        </>
      )}

      {/* Synonyms popup */}
      {synPopup && (
        <>
          <div onClick={() => setSynPopup(null)} style={{ position: 'fixed', inset: 0, zIndex: 90 }} />
          <div style={{
            position: 'fixed', left: synPopup.x, top: synPopup.y,
            background: 'white', border: '1.5px solid var(--border)', borderRadius: 10,
            boxShadow: '0 8px 24px rgba(0,0,0,0.15)', zIndex: 100, minWidth: 240, padding: 12,
          }}>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: 6 }}>
              Сўз: <strong>{synPopup.word}</strong>
            </div>
            {synPopup.options.length === 0 ? (
              <div style={{ fontSize: '0.78rem', color: '#9CA3AF' }}>Синоним топилмади</div>
            ) : (
              synPopup.options.slice(0, 10).map((opt, i) => (
                <button key={i} onClick={() => setSynPopup(null)}
                  style={{
                    display: 'block', width: '100%', textAlign: 'left',
                    padding: '5px 8px', marginBottom: 3, background: '#F3E8FF',
                    border: '1.5px solid #D8B4FE', borderRadius: 5,
                    color: '#6B21A8', fontSize: '0.76rem', fontWeight: 600, cursor: 'pointer',
                  }}>{opt}</button>
              ))
            )}
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
      display: 'flex', alignItems: 'center', gap: 5,
      fontWeight: 600,
    }}>
      <span style={{ color: '#6B7280' }}>{label}:</span>
      <span style={{ color, fontWeight: 800 }}>{value.toLocaleString()}</span>
    </div>
  )
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
      <span style={{ width: 10, height: 3, background: color, borderRadius: 2 }} />
      <span>{label}</span>
    </span>
  )
}
