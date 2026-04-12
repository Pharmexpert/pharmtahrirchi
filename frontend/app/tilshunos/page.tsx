'use client'

import React, { useState, useEffect, useRef, useCallback } from 'react'
import { Loader2, Award, BookPlus, ClipboardPaste, Wand2, ArrowRightLeft, Play, Upload, Trash2, FileText, Sparkles, Download, FileUp, CheckCircle2, FileDown } from 'lucide-react'
import { useAuth } from '../../components/LoginGuard'
import api, { TilshunosCheckResult, LinguisticIssue } from '../../services/api'
import WordDocumentViewer from '../../components/WordDocumentViewer'
import SuperDocEditor from '../../components/SuperDocEditor'
import LinguisticAnalysisBar from '../../components/LinguisticAnalysisBar'
import { useInlineSynonymPopup } from '../../components/InlineSynonymPopup'
import ErrorBoundary from '../../components/ErrorBoundary'

type Mode = 'edit' | 'translate' | 'word'
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

// Client-side Uzbek Latin↔Cyrillic transliteration
const LAT_TO_CYR_MAP: [string, string][] = [
  ["sh", "ш"], ["ch", "ч"], ["ng", "нг"], ["o'", "ў"], ["g'", "ғ"],
  ["yo", "ё"], ["ya", "я"], ["yu", "ю"],
  ["a", "а"], ["b", "б"], ["d", "д"], ["e", "е"], ["f", "ф"],
  ["g", "г"], ["h", "ҳ"], ["i", "и"], ["j", "ж"], ["k", "к"],
  ["l", "л"], ["m", "м"], ["n", "н"], ["o", "о"], ["p", "п"],
  ["q", "қ"], ["r", "р"], ["s", "с"], ["t", "т"], ["u", "у"],
  ["v", "в"], ["x", "х"], ["y", "й"], ["z", "з"],
]
const CYR_TO_LAT_MAP: [string, string][] = [
  ["ш", "sh"], ["ч", "ch"], ["нг", "ng"], ["ў", "o'"], ["ғ", "g'"],
  ["ё", "yo"], ["я", "ya"], ["ю", "yu"],
  ["а", "a"], ["б", "b"], ["д", "d"], ["е", "e"], ["ф", "f"],
  ["г", "g"], ["ҳ", "h"], ["и", "i"], ["ж", "j"], ["к", "k"],
  ["л", "l"], ["м", "m"], ["н", "n"], ["о", "o"], ["п", "p"],
  ["қ", "q"], ["р", "r"], ["с", "s"], ["т", "t"], ["у", "u"],
  ["в", "v"], ["х", "x"], ["й", "y"], ["з", "z"],
]

function clientTransliterate(input: string, direction: 'to-cyrillic' | 'to-latin'): string {
  const map = direction === 'to-cyrillic' ? LAT_TO_CYR_MAP : CYR_TO_LAT_MAP
  // Sort by key length descending so multi-char mappings match first
  const sorted = [...map].sort((a, b) => b[0].length - a[0].length)
  let result = ''
  let i = 0
  while (i < input.length) {
    let found = false
    const ch = input[i]
    const isUpper = ch === ch.toUpperCase() && ch !== ch.toLowerCase()
    for (const [from, to] of sorted) {
      const slice = input.substring(i, i + from.length).toLowerCase()
      if (slice === from) {
        result += isUpper ? to.charAt(0).toUpperCase() + to.slice(1) : to
        i += from.length
        found = true
        break
      }
    }
    if (!found) { result += input[i]; i++ }
  }
  return result
}

function detectScript(text: string): 'cyrillic' | 'latin' | 'unknown' {
  const cyr = (text.match(/[а-яА-ЯёЁўғқҳЎҒҚҲ]/g) || []).length
  const lat = (text.match(/[a-zA-Z]/g) || []).length
  if (cyr > lat) return 'cyrillic'
  if (lat > cyr) return 'latin'
  return 'unknown'
}

function detectLang(text: string): Lang {
  if (!text || text.length < 3) return 'uz-lat'
  // Count cyrillic vs latin
  const cyr = (text.match(/[а-яА-ЯёЁўғқҳЎҒҚҲ]/g) || []).length
  const lat = (text.match(/[a-zA-Z]/g) || []).length
  // Russian-specific indicators (letters and stop words not in Uzbek Cyrillic)
  const ruIndic = /[ыэъЫЭЪ]/.test(text) ||
    /\b(что|это|как|так|для|при|или|если|есть|уже|был|была|более|менее|который|однако|таким|образом|самый|своих|свое)\b/i.test(text)
  // Uzbek Cyrillic indicators (special letters)
  const uzCyrIndic = /[ўғқҳЎҒҚҲ]/.test(text) ||
    /\b(билан|учун|керак|бўлади|ҳозирги|шунинг|шундай|каби|орқали)\b/i.test(text)
  // English stop words
  const enIndic = /\b(the|and|of|in|is|was|has|have|with|for|that|this|from|are|were|will|would|can|could|should)\b/i.test(text)
  // Uzbek Latin indicators (special letters: o', g', 'ʻ)
  const uzLatIndic = /[ʻ']/.test(text) ||
    /\b(bilan|uchun|kerak|bo'ladi|hozirgi|shuning|shunday|kabi|orqali|bo'lib|qilib)\b/i.test(text)

  // Cyrillic — decide between Russian and Uzbek Cyrillic
  if (cyr > lat * 0.5) {
    if (uzCyrIndic && !ruIndic) return 'uz-cyr'
    if (ruIndic) return 'ru'
    if (uzCyrIndic) return 'uz-cyr'
    // Default Cyrillic without indicators → Russian (more common)
    return 'ru'
  }
  // Latin
  if (enIndic && !uzLatIndic) return 'en'
  if (uzLatIndic) return 'uz-lat'
  // Default Latin → Uzbek Latin
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
  const synonymPopup = useInlineSynonymPopup()
  const [mode, setMode] = useState<Mode>('edit')
  const [lang, setLang] = useState<Lang>('uz-lat')
  const [text, setText] = useState('')
  const [result, setResult] = useState<TilshunosCheckResult | null>(null)
  const [classified, setClassified] = useState<WordSpan[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState<any>(null)
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null)
  const [popup, setPopup] = useState<{ issue: LinguisticIssue; x: number; y: number } | null>(null)
  const [popupMorph, setPopupMorph] = useState<any | null>(null)
  const [popupSynonyms, setPopupSynonyms] = useState<{ loading: boolean; items: string[] }>({ loading: false, items: [] })
  const [synPopup, setSynPopup] = useState<{ word: string; x: number; y: number; options: string[] } | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const richEditRef = useRef<HTMLDivElement>(null)
  const richSrcRef = useRef<HTMLDivElement>(null)
  const richTgtRef = useRef<HTMLDivElement>(null)
  const syncScrollRef = useRef<boolean>(true)

  // Side-by-side sync scroll handler
  const handleSourceScroll = (e: React.UIEvent<HTMLElement>) => {
    if (!syncScrollRef.current || !richTgtRef.current) return
    const src = e.currentTarget
    const tgt = richTgtRef.current
    const ratio = src.scrollTop / (src.scrollHeight - src.clientHeight || 1)
    tgt.scrollTop = ratio * (tgt.scrollHeight - tgt.clientHeight)
  }
  const handleTargetScroll = (e: React.UIEvent<HTMLElement>) => {
    if (!syncScrollRef.current || !richSrcRef.current) return
    const tgt = e.currentTarget
    const src = richSrcRef.current
    const ratio = tgt.scrollTop / (tgt.scrollHeight - tgt.clientHeight || 1)
    src.scrollTop = ratio * (src.scrollHeight - src.clientHeight)
  }
  // Rich (DOCX) HTML content — when present, render rich editor instead of plain
  const [richHtml, setRichHtml] = useState<string>('')
  const [richSrcHtml, setRichSrcHtml] = useState<string>('')
  const [richTgtHtml, setRichTgtHtml] = useState<string>('')

  // Translation mode
  const [sourceLang, setSourceLang] = useState<Lang>('en')
  const [targetLang, setTargetLang] = useState<Lang>('uz-lat')
  const [sourceText, setSourceText] = useState('')
  const [targetText, setTargetText] = useState('')
  const [translating, setTranslating] = useState(false)

  // Auto-detect source language when source text changes
  useEffect(() => {
    if (sourceText && sourceText.length > 5) {
      const d = detectLang(sourceText)
      if (d !== sourceLang) {
        setSourceLang(d)
        // Auto-pick a sensible target if same as source
        if (d === targetLang) {
          // If source is Uzbek (any script) → target English by default
          if (d.startsWith('uz')) setTargetLang('en')
          // If source is English → target Uzbek Latin
          else if (d === 'en') setTargetLang('uz-lat')
          // If source is Russian → target Uzbek Latin
          else if (d === 'ru') setTargetLang('uz-lat')
        }
      }
    }
  }, [sourceText])

  // Auto-detect target language when target text changes (for editing)
  useEffect(() => {
    if (targetText && targetText.length > 5) {
      const d = detectLang(targetText)
      if (d !== targetLang) setTargetLang(d)
    }
  }, [targetText])

  // Original snapshots for self-learning diff
  const [originalText, setOriginalText] = useState('')
  const [originalSource, setOriginalSource] = useState('')
  const [originalTarget, setOriginalTarget] = useState('')

  // Track when text is loaded to capture original snapshot
  useEffect(() => {
    if (text && !originalText) setOriginalText(text)
  }, [text])
  useEffect(() => {
    if (sourceText && !originalSource) setOriginalSource(sourceText)
  }, [sourceText])
  useEffect(() => {
    if (targetText && !originalTarget) setOriginalTarget(targetText)
  }, [targetText])

  // Send diff to self-learning when user clears or finishes editing
  const sendLearnDiff = async (orig: string, curr: string, langCode: string, source: string) => {
    if (!orig || !curr || orig === curr) return
    try {
      await api.tilshunos.learnDiff(orig, curr, langCode, source)
    } catch (_) {}
  }

  const [aiEngines, setAiEngines] = useState<Record<string, any> | null>(null)
  const [entities, setEntities] = useState<Array<{ text: string; from: number; to: number; type: string; score?: number }>>([])
  const [showEntities, setShowEntities] = useState(true)
  const [linguistic, setLinguistic] = useState<{ annotated: any[]; disputed: any[]; abbreviations: any[] }>({ annotated: [], disputed: [], abbreviations: [] })
  const [linguisticPopup, setLinguisticPopup] = useState<{ data: any; type: string; x: number; y: number } | null>(null)
  const [morphPopup, setMorphPopup] = useState<{ word: string; data: any; x: number; y: number } | null>(null)

  useEffect(() => {
    api.tilshunos.rulesStats().then(setStats).catch(() => {})
    api.tilshunos.publicAiEngines().then(r => setAiEngines(r.engines || null)).catch(() => {})
  }, [])

  // Auto-extract entities + linguistic when text is set
  useEffect(() => {
    if (!text || text.length < 10 || !showEntities) {
      setEntities([])
      setLinguistic({ annotated: [], disputed: [], abbreviations: [] })
      return
    }
    const t = setTimeout(() => {
      api.tilshunos.extractEntities(text).then(r => setEntities(r.entities || [])).catch(() => {})
      api.tilshunos.extractLinguistic(text).then(r => setLinguistic({
        annotated: r.annotated || [],
        disputed: r.disputed || [],
        abbreviations: r.abbreviations || [],
      })).catch(() => {})
    }, 800)
    return () => clearTimeout(t)
  }, [text, showEntities])

  // Enrich popup with morph data + synonyms when it opens
  useEffect(() => {
    if (!popup) {
      setPopupMorph(null)
      setPopupSynonyms({ loading: false, items: [] })
      return
    }
    const word = popup.issue.matched_text || text.substring(popup.issue.from_index, popup.issue.to_index)
    if (!word || word.length < 2) return
    // Look for morph data in result
    const morphItems = (result as any)?.morphology || []
    const morphEntry = morphItems.find((m: any) => {
      const mWord = text.substring(m.from ?? 0, m.to ?? 0)
      return mWord.toLowerCase() === word.toLowerCase()
    })
    setPopupMorph(morphEntry || null)
    // Fetch synonyms
    setPopupSynonyms({ loading: true, items: [] })
    api.synonyms.list(word).then((r: any) => {
      const syns = (r?.synonyms || []).map((s: any) => s.synonym || s.word || s).filter((s: string) => s && s !== word && s !== word.toLowerCase())
      setPopupSynonyms({ loading: false, items: syns.slice(0, 8) })
    }).catch(() => {
      setPopupSynonyms({ loading: false, items: [] })
    })
  }, [popup])

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
      const data: any = await api.linguistic.transliterate(text, target)
      setText(data.text)
      setLang(target === 'cyrillic' ? 'uz-cyr' : 'uz-lat')
      setResult(null)
      setClassified(null)
    } catch (_) {}
  }

  const transliterateField = async (fieldText: string, setter: (v: string) => void, target: 'cyrillic' | 'latin') => {
    if (!fieldText.trim()) return
    try {
      const data: any = await api.linguistic.transliterate(fieldText, target)
      setter(data.text)
    } catch (_) {}
  }

  const addWordToDictionary = async () => {
    const sel = window.getSelection()?.toString().trim()
    if (!sel) {
      alert('Аввал матндан сўзни белгиланг')
      return
    }
    try {
      const backendLang = lang.startsWith('uz') ? 'uz' : lang
      const r = await api.dictionary.add(sel, backendLang)
      if (r.ok) {
        // Generate translation in background (cache)
        api.dictionary.translate(sel).catch(() => {})
        alert(`"${sel}" луғатга қўшилди ✓`)
        // Re-run check so the word turns "known"
        if (text && result) {
          const cr = await api.tilshunos.check(text, backendLang)
          setResult(cr)
          if (backendLang === 'uz') {
            const cl = await api.tilshunos.classify(text, 'uz')
            setClassified(cl.spans || [])
          }
        }
      } else {
        alert('Хатолик: ' + (r.error || 'noma\'lum'))
      }
    } catch (e: any) {
      alert('Хатолик: ' + (e?.message || e))
    }
  }

  // Shared file extractor — for DOCX returns rich HTML (preserves tables/images/formatting)
  const extractFile = async (f: File): Promise<{ text: string; html?: string }> => {
    const name = f.name.toLowerCase()
    if (name.endsWith('.txt') || name.endsWith('.md') || name.endsWith('.csv')) {
      return { text: await f.text() }
    }
    if (name.endsWith('.docx')) {
      try {
        const mammoth = await import('mammoth')
        const buf = await f.arrayBuffer()
        const result = await mammoth.convertToHtml({ arrayBuffer: buf }, {
          // Inline images as base64 data URIs — preserves formatting
          convertImage: mammoth.images.imgElement(async (img: any) => {
            const dataUri = await img.read('base64').then((s: string) => `data:${img.contentType};base64,${s}`)
            return { src: dataUri }
          }),
          // Preserve styles: bold, italic, underline, tables, lists
          styleMap: [
            "p[style-name='Heading 1'] => h1:fresh",
            "p[style-name='Heading 2'] => h2:fresh",
            "p[style-name='Heading 3'] => h3:fresh",
            "b => strong", "i => em", "u => u",
            "table => table.docx-table",
          ],
        } as any)
        const tx = await mammoth.extractRawText({ arrayBuffer: buf })
        return { text: tx.value || '', html: result.value || '' }
      } catch (e) {
        // Fallback to backend plain extraction
      }
    }
    // Excel (.xlsx, .xls) — extract text from all sheets
    if (name.endsWith('.xlsx') || name.endsWith('.xls')) {
      try {
        const XLSX = await import('xlsx')
        const buf = await f.arrayBuffer()
        const wb = XLSX.read(buf, { type: 'array' })
        let allText = ''
        let htmlParts: string[] = []
        for (const sheetName of wb.SheetNames) {
          const ws = wb.Sheets[sheetName]
          const csvText = XLSX.utils.sheet_to_csv(ws)
          allText += `--- ${sheetName} ---\n${csvText}\n\n`
          const htmlTable = XLSX.utils.sheet_to_html(ws)
          htmlParts.push(`<h3>${sheetName}</h3>${htmlTable}`)
        }
        return { text: allText, html: htmlParts.join('\n') }
      } catch (e) {
        // Fallback
      }
    }
    const r = await api.tilshunos.extractText(f)
    return { text: r.text || '' }
  }

  // DOCX export — юклаб олиш (Миссия А/Б натижалари билан)
  const [loadedDocxFile, setLoadedDocxFile] = useState<File | null>(null)
  const exportToDocx = async () => {
    if (!token) return
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    try {
      // Агар DOCX файл юкланган бўлса — backend'да таржима/таҳрир қилинган файлни юклаб олиш
      if (loadedDocxFile && mode === 'translate') {
        const formData = new FormData()
        formData.append('file', loadedDocxFile)
        formData.append('source_lang', sourceLang)
        formData.append('target_lang', targetLang)
        const res = await fetch(`${API_BASE}/api/documents/translate-docx`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
          body: formData,
        })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const blob = await res.blob()
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `translated_${loadedDocxFile.name}`
        a.click()
        URL.revokeObjectURL(url)
        return
      }
      // Оддий матнни DOCX форматга конвертация (python-docx backend endpoint)
      const content = mode === 'translate' ? targetText || sourceText : text
      if (!content.trim()) return
      const res = await fetch(`${API_BASE}/api/documents/export-docx`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: content, title: 'Pharma Expert — Илмий таҳрир', lang: 'uz' }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'pharma_tahrir.docx'
      a.click()
      URL.revokeObjectURL(url)
    } catch (e: any) {
      alert('DOCX юклаб бўлмади: ' + (e?.message || e))
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
    // Locate the error text robustly
    const matched = issue.matched_text || (issue as any).old_value || text.substring(issue.from_index, issue.to_index)
    if (!matched) {
      setPopup(null)
      return
    }
    let from = issue.from_index
    let to = issue.to_index

    // Verify position — if text at position doesn't match, search for it
    if (!from && !to && matched) {
      const idx = text.indexOf(matched)
      if (idx >= 0) { from = idx; to = idx + matched.length }
    } else if (text.substring(from, to) !== matched) {
      const near = text.indexOf(matched, Math.max(0, from - 80))
      const idx = near >= 0 ? near : text.indexOf(matched)
      if (idx >= 0) { from = idx; to = idx + matched.length }
      else {
        // Last resort: try case-insensitive
        const lowerIdx = text.toLowerCase().indexOf(matched.toLowerCase())
        if (lowerIdx >= 0) { from = lowerIdx; to = lowerIdx + matched.length }
        else {
          setPopup(null)
          return // silently fail, don't show alert
        }
      }
    }

    const newText = text.substring(0, from) + suggestion + text.substring(to)
    setText(newText)
    setPopup(null)

    const backendLang = lang.startsWith('uz') ? 'uz' : lang

    // Self-learning (fire-and-forget)
    api.tilshunos.confirm({
      wrong: matched,
      correct: suggestion,
      context: text.substring(Math.max(0, from - 50), Math.min(text.length, to + 50)),
      category: issue.error_type,
      lang: backendLang,
    }).catch(() => {})

    // Re-run tilshunos check (keeps result in correct format for renderAnnotated)
    try {
      const [checkRes, classifyRes] = await Promise.all([
        api.tilshunos.check(newText, backendLang),
        backendLang === 'uz'
          ? api.tilshunos.classify(newText, 'uz')
          : Promise.resolve({ spans: [], counts: {} } as any),
      ])
      setResult(checkRes)
      setClassified(classifyRes.spans || [])
    } catch (_) {
      // If re-check fails, just clear the result to avoid stale state
      setResult(null)
    }
  }

  // Render annotated text as HTML — words colored by classification + errors underlined
  const renderAnnotated = () => {
    if (!text) return <span style={{ color: '#9CA3AF' }}>Матн киритинг ва «Синов олиб бориш» тугмасини босинг...</span>
    if (!result) return <div style={{ whiteSpace: 'pre-wrap' }}>{text}</div>

    // Merge errors + morph + classification + entities into non-overlapping spans
    type Span = {
      from: number
      to: number
      issue?: LinguisticIssue
      issueIdx?: number
      wordCategory?: string
      entityType?: string
      morphInfo?: any // morph layer data (pos, root, affix, prefix)
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

    // Morph layer coloring (from 4-layer analysis) — show POS-based colors
    const morphItems = (result as any).morphology || []
    for (const mi of morphItems) {
      const mFrom = mi.from ?? 0
      const mTo = mi.to ?? 0
      if (mFrom >= 0 && mTo > mFrom && mTo <= text.length) {
        const key = `${mFrom}-${mTo}`
        if (!errorSet.has(key)) {
          spans.push({ from: mFrom, to: mTo, morphInfo: mi })
        }
      }
    }

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

    // NER entities (DRUG, DOSE, PERSON, LOC, ORG)
    if (showEntities && entities.length > 0) {
      for (const ent of entities) {
        const overlap = spans.some(s => (ent.from >= s.from && ent.from < s.to) || (ent.to > s.from && ent.to <= s.to))
        if (!overlap) {
          spans.push({ from: ent.from, to: ent.to, entityType: ent.type })
        }
      }
    }

    // Linguistic words: annotated (purple), disputed (red), abbreviations (green)
    const linguisticItems: Array<{ from: number; to: number; type: 'annotated' | 'disputed' | 'abbreviations'; data: any }> = []
    for (const item of linguistic.annotated) linguisticItems.push({ from: item.from, to: item.to, type: 'annotated', data: item.data })
    for (const item of linguistic.disputed) linguisticItems.push({ from: item.from, to: item.to, type: 'disputed', data: item.data })
    for (const item of linguistic.abbreviations) linguisticItems.push({ from: item.from, to: item.to, type: 'abbreviations', data: item.data })
    for (const item of linguisticItems) {
      const overlap = spans.some(s => (item.from >= s.from && item.from < s.to) || (item.to > s.from && item.to <= s.to))
      if (!overlap) {
        spans.push({ from: item.from, to: item.to, entityType: `LING_${item.type}` })
        // Save data on a side map for popup
        ;(spans[spans.length - 1] as any).linguisticData = item.data
        ;(spans[spans.length - 1] as any).linguisticType = item.type
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
      } else if (s.morphInfo) {
        // Morph layer — color by POS, click to see morph details + synonyms
        const POS_COLORS: Record<string, string> = {
          NOUN: '#0891B2', VERB: '#7C3AED', ADJECTIVE: '#DB2777', ADJ: '#DB2777',
          ADVERB: '#D97706', ADV: '#D97706', PRONOUN: '#059669', PRON: '#059669',
          NUMERAL: '#6366F1', NUM: '#6366F1', UNKNOWN: '#DC2626',
          CONJUNCTION: '#94A3B8', CONJ: '#94A3B8', PARTICLE: '#94A3B8', PART: '#94A3B8',
        }
        const pos = (s.morphInfo.pos || 'UNKNOWN').toUpperCase()
        const mColor = POS_COLORS[pos] || '#6B7280'
        const isUnknown = pos === 'UNKNOWN' || s.morphInfo.is_unknown
        parts.push(
          <span key={`m${i}`}
            onClick={async (e) => {
              e.stopPropagation()
              const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
              // Show morph info + synonyms in popup
              const morphDesc = s.morphInfo.description || s.morphInfo.message || ''
              const synRes = await api.synonyms.list(content).catch(() => ({ synonyms: [] })) as any
              const syns = (synRes?.synonyms || []).map((ss: any) => ss.synonym || ss.word || ss).filter((ss: string) => ss && ss !== content)
              setPopup({
                issue: {
                  from_index: s.from, to_index: s.to,
                  matched_text: content,
                  old_value: content, new_value: '',
                  message: morphDesc,
                  error_type: `Morph/${pos}`,
                  category: 'morphology',
                  severity: isUnknown ? 'error' : 'info',
                  suggestions: syns.slice(0, 5),
                } as any,
                x: rect.left, y: rect.bottom + 6,
              })
            }}
            style={{
              borderBottom: isUnknown ? `2px wavy ${mColor}` : `1px dotted ${mColor}88`,
              color: isUnknown ? mColor : 'inherit',
              cursor: 'pointer',
              padding: '0 1px',
              background: isUnknown ? `${mColor}15` : 'transparent',
            }}
            title={s.morphInfo.description || `${pos}: ${s.morphInfo.root || content}`}
          >{content}</span>
        )
      } else if (s.entityType) {
        const ENTITY_COLORS: Record<string, string> = {
          DRUG: '#7C3AED',     // purple — лекарственный препарат
          DOSE: '#0891B2',     // teal — доза/единица
          PERSON: '#059669',   // green — odamlar
          LOC: '#DC2626',      // red — жойлар
          ORG: '#D97706',      // orange — компании
          MISC: '#6B7280',     // gray — бошқа
          LING_annotated: '#7C3AED',     // purple — изоҳли (siyohrang)
          LING_disputed: '#DC2626',      // red — мунозарали
          LING_abbreviations: '#16A34A', // green — қисқартмалар
        }
        const color = ENTITY_COLORS[s.entityType] || ENTITY_COLORS.MISC
        const isLinguistic = s.entityType.startsWith('LING_')
        const isDrug = s.entityType === 'DRUG'
        const linguisticData = (s as any).linguisticData
        const linguisticType = (s as any).linguisticType
        const labelMap: Record<string, string> = {
          LING_annotated: 'изоҳли',
          LING_disputed: 'мунозарали',
          LING_abbreviations: 'қисқартма',
        }
        parts.push(
          <span key={`ent${i}`}
            title={isLinguistic ? `${labelMap[s.entityType]}: ${content}` : isDrug ? `DRUG: ${content} (босинг — морфема таҳлили)` : `${s.entityType}: ${content}`}
            onClick={async (e) => {
              if (isLinguistic && linguisticData) {
                e.stopPropagation()
                const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
                setLinguisticPopup({ data: linguisticData, type: linguisticType, x: rect.left, y: rect.bottom + 6 })
              } else if (isDrug) {
                e.stopPropagation()
                const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
                try {
                  const morph = await api.tilshunos.decomposeTerm(content)
                  setMorphPopup({ word: content, data: morph, x: rect.left, y: rect.bottom + 6 })
                } catch (_) {}
              }
            }}
            style={{
              background: `${color}22`,
              color,
              fontWeight: 700,
              padding: '1px 4px',
              borderRadius: 4,
              border: `1px solid ${color}66`,
              fontSize: '0.94em',
              cursor: (isLinguistic || isDrug) ? 'pointer' : 'default',
            }}
          >{content}<sub style={{ fontSize: '0.55em', marginLeft: 2, opacity: 0.7 }}>{isLinguistic ? labelMap[s.entityType].toUpperCase() : s.entityType}</sub></span>
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
          <button onClick={() => setMode('word')}
            style={{
              padding: '8px 14px',
              background: mode === 'word' ? 'linear-gradient(135deg, #2563EB, #1D4ED8)' : 'transparent',
              color: mode === 'word' ? 'white' : 'var(--text-primary)',
              border: 'none', borderRadius: 7,
              fontWeight: 700, fontSize: '0.78rem', cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 5,
            }}>
            <FileText size={13} /> Word ҳужжат
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

      {/* AI Engines badges removed per user request */}

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

              {/* Transliteration toggle — client-side Latin↔Cyrillic */}
              <button
                onClick={() => {
                  if (!text.trim()) return
                  const script = detectScript(text)
                  if (script === 'cyrillic') {
                    const converted = clientTransliterate(text, 'to-latin')
                    setText(converted)
                    setLang('uz-lat')
                  } else {
                    const converted = clientTransliterate(text, 'to-cyrillic')
                    setText(converted)
                    setLang('uz-cyr')
                  }
                  setResult(null)
                  setClassified(null)
                }}
                disabled={!text.trim()}
                title={detectScript(text) === 'cyrillic' ? 'Лотинга ўтказиш' : 'Кириллга ўтказиш'}
                style={{
                  ...toolbarBtn,
                  background: '#FFF7ED', color: '#B45309', borderColor: '#FCD34D',
                  opacity: text.trim() ? 1 : 0.5,
                }}
              >
                🔄 {detectScript(text) === 'cyrillic' ? 'Лотин' : 'Кирилл'}
              </button>

              <button onClick={handlePaste} style={toolbarBtn}><ClipboardPaste size={13} /> Жойлаш</button>

              <label style={{ ...toolbarBtn, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                <Upload size={13} /> Файлдан юклаш
                <input
                  type="file"
                  accept=".txt,.md,.csv,.pdf,.docx,.xlsx,.xls,.pptx"
                  style={{ display: 'none' }}
                  onChange={async (e) => {
                    const f = e.target.files?.[0]
                    if (!f) return
                    try {
                      const ex = await extractFile(f)
                      setText(ex.text)
                      setRichHtml(ex.html || '')
                      if (f.name.toLowerCase().endsWith('.docx')) setLoadedDocxFile(f)
                      setResult(null)
                      setClassified(null)
                    } catch (err: any) {
                      alert('Файлни ўқиб бўлмади: ' + (err?.message || err))
                    }
                    e.target.value = ''
                  }}
                />
              </label>

              <button onClick={exportToDocx} disabled={!text.trim()}
                title="DOCX форматда юклаб олиш"
                style={{ ...toolbarBtn, background: '#EFF6FF', color: '#1D4ED8', borderColor: '#93C5FD' }}>
                <FileDown size={13} /> DOCX
              </button>

              <button
                onClick={async () => {
                  // Save edits to Sayqallash before clearing
                  await sendLearnDiff(originalText, text, lang.startsWith('uz') ? 'uz' : lang, 'tilshunos_edit')
                  setLoadedDocxFile(null)
                  setText(''); setRichHtml(''); setResult(null); setClassified(null); setPopup(null); setOriginalText('')
                }}
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

              <button
                onClick={async () => {
                  if (!text.trim()) return
                  setLoading(true)
                  try {
                    const r = await api.tilshunos.aiImprove(text, lang.startsWith('uz') ? 'uz' : lang)
                    if (r.improved && r.improved !== text) {
                      // Self-learning: diff old vs improved
                      sendLearnDiff(text, r.improved, lang.startsWith('uz') ? 'uz' : lang, 'tilshunos_ai_improve')
                      setText(r.improved)
                      setResult(null); setClassified(null)
                    }
                  } catch (e: any) { alert('AI хатоси: ' + (e?.message || e)) }
                  finally { setLoading(false) }
                }}
                disabled={loading || !text.trim()}
                title="Mistral-7B-Instruct-Uz билан илмий таҳрир"
                style={{ ...toolbarBtn, background: 'linear-gradient(135deg,#A78BFA,#7C3AED)', color: 'white', border: 'none' }}
              >
                <Wand2 size={13} /> AI Яхшилаш
              </button>

              {/* Linguistic extract buttons */}
              <button
                onClick={async () => {
                  if (!text.trim()) return
                  try {
                    const r = await api.tilshunos.extractLinguistic(text)
                    setLinguistic({ annotated: r.annotated || [], disputed: r.disputed || [], abbreviations: r.abbreviations || [] })
                    const total = (r.annotated?.length || 0) + (r.disputed?.length || 0) + (r.abbreviations?.length || 0)
                    alert(`Топилди: ${r.annotated?.length || 0} изоҳли, ${r.disputed?.length || 0} мунозарали, ${r.abbreviations?.length || 0} қисқартма`)
                  } catch (e: any) { alert('Хато: ' + (e?.message || e)) }
                }}
                disabled={!text.trim()}
                title="Изоҳли/мунозарали/қисқартмалар сўзларни матнда топиш"
                style={{ ...toolbarBtn, background: '#F5F3FF', color: '#7C3AED', borderColor: '#C4B5FD' }}
              >
                🔍 Лингвистик аниқлаш
              </button>

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

            {/* 4-layer Linguistic Analysis Bar */}
            <div style={{ padding: '10px 18px 0' }}>
              <LinguisticAnalysisBar text={text} lang="uz" compact onTextChange={(t) => setText(t)} onResult={(r: any) => {
                // Convert analyze/full format to TilshunosCheckResult format
                const issues: any[] = []
                for (const item of (r.sayqallash || [])) {
                  const from = item.from ?? item.from_index ?? 0
                  const to = item.to ?? item.to_index ?? 0
                  const oldVal = item.old ?? item.old_value ?? ''
                  const newVal = item.new ?? item.new_value ?? ''
                  issues.push({
                    from_index: from,
                    to_index: to,
                    matched_text: oldVal || text.substring(from, to),
                    old_value: oldVal,
                    new_value: newVal,
                    message: item.message || `${oldVal} → ${newVal}`,
                    error_type: item.error_type || 'S/Spelling',
                    category: (item.error_type || 'S/Spelling').split('/')[0]?.toLowerCase() === 's' ? 'orthography' : 'grammar',
                    severity: item.severity || 'error',
                    source: item.source || 'analyze',
                    confidence: item.confidence || 80,
                    suggestions: item.suggestions || (newVal ? [newVal] : []),
                    layer: 'sayqallash',
                  })
                }
                for (const item of (r.style || [])) {
                  const from = item.from ?? 0
                  const to = item.to ?? 0
                  const oldVal = item.old ?? ''
                  issues.push({
                    from_index: from,
                    to_index: to,
                    matched_text: oldVal || text.substring(from, to),
                    old_value: oldVal,
                    new_value: item.suggestion ?? '',
                    message: item.description || `${oldVal} → ${item.suggestion || ''}`,
                    error_type: item.rule_id || 'Style',
                    category: 'style',
                    severity: item.severity || 'should',
                    source: item.source || 'style_rules',
                    description: item.description,
                    suggestions: item.suggestion ? [item.suggestion] : [],
                    layer: 'style',
                  })
                }
                // Build category/severity counts
                const byCat: Record<string, number> = {}
                const bySev: Record<string, number> = {}
                for (const iss of issues) {
                  byCat[iss.category] = (byCat[iss.category] || 0) + 1
                  bySev[iss.severity] = (bySev[iss.severity] || 0) + 1
                }
                setResult({
                  text,
                  lang: 'uz',
                  issues,
                  by_category: byCat,
                  by_severity: bySev,
                  total: issues.length,
                  morphology: r.morph || [],
                  score: issues.length === 0 ? 1.0 : Math.max(0.1, 1.0 - issues.length * 0.03),
                  word_count: text.split(/\s+/).length,
                } as any)
              }} />
            </div>

            {/* Single editor area: SuperDoc if DOCX file, rich HTML, plain textarea, or annotated view */}
            <div style={{ padding: 18, flex: 1, display: 'flex', flexDirection: 'column' }} onDoubleClick={synonymPopup.handleClick}>
              {loadedDocxFile && !result ? (
                <ErrorBoundary fallback={<div style={{ padding: 20, color: '#991B1B' }}>SuperDoc юклаб бўлмади — оддий режимга ўтинг</div>}>
                  <SuperDocEditor
                    file={loadedDocxFile}
                    height="65vh"
                    onReady={(editor: any) => {
                      // Матнни text state'га синхронлаш
                      try {
                        const t = editor?.getText?.() || ''
                        if (t) setText(t)
                      } catch {}
                    }}
                    aiActions={[
                      {
                        label: '4 ҚАТЛАМ текшириш',
                        icon: <Wand2 size={13} />,
                        color: '#16A34A',
                        onClick: async (sel: string, full: string) => {
                          const t = sel || full
                          if (!t.trim()) return
                          setText(t)
                          // Run 4-layer analysis via LinguisticAnalysisBar button click
                          const btn = document.querySelector('[data-layer="hammasi"]') as HTMLButtonElement
                          if (btn) btn.click()
                        },
                      },
                      {
                        label: 'Сайқаллаш',
                        icon: <CheckCircle2 size={13} />,
                        color: '#DC2626',
                        onClick: async (sel: string, full: string) => {
                          const t = sel || full
                          if (!t.trim()) return
                          setText(t)
                          const btn = document.querySelector('[data-layer="sayqallash"]') as HTMLButtonElement
                          if (btn) btn.click()
                        },
                      },
                      {
                        label: 'DOCX юклаб олиш',
                        icon: <Download size={13} />,
                        color: '#1D4ED8',
                        onClick: () => exportToDocx(),
                      },
                    ]}
                  />
                </ErrorBoundary>
              ) : richHtml && !result ? (
                <div
                  ref={richEditRef}
                  contentEditable
                  suppressContentEditableWarning
                  onInput={e => setText((e.currentTarget as HTMLDivElement).innerText)}
                  dangerouslySetInnerHTML={{ __html: richHtml }}
                  className="docx-rich"
                  style={{
                    width: '100%', flex: 1, minHeight: 500, padding: 24,
                    border: '1.5px solid var(--border)', borderRadius: 10,
                    fontSize: '0.95rem', fontFamily: 'Times New Roman, Georgia, serif',
                    background: 'white', lineHeight: 1.6, outline: 'none',
                    overflow: 'auto', boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.04)',
                  }}
                />
              ) : !result ? (
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
                  contentEditable
                  suppressContentEditableWarning
                  onInput={(e) => {
                    const newText = (e.currentTarget as HTMLDivElement).innerText
                    // Update text silently — do NOT re-render the annotated children (would lose cursor + colors)
                    setText(newText)
                  }}
                  style={{
                    width: '100%', padding: 14, minHeight: 200,
                    border: '1.5px solid var(--border)', borderRadius: 10,
                    fontSize: '0.95rem', fontFamily: 'inherit',
                    background: 'var(--bg-secondary)', lineHeight: 1.85,
                    cursor: 'text',
                    overflow: 'auto',
                    outline: 'none',
                    whiteSpace: 'pre-wrap',
                  }}
                  // key based on result reference: re-mount only when a new check arrives, so during typing children stay stable
                  key={result ? `r-${(result as any).timestamp || ''}-${(result as any).total || 0}-${(result as any).score || 0}` : 'no-r'}
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
      ) : mode === 'translate' ? (
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
          {/* Shared toolbar for translate mode (source side) */}
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center', marginBottom: 10 }}>
            <button
              onClick={async () => {
                try {
                  const pasted = await navigator.clipboard.readText()
                  if (pasted) setSourceText(pasted)
                } catch (_) {}
              }}
              style={toolbarBtn}
            >
              <ClipboardPaste size={13} /> Жойлаш
            </button>

            <label style={{ ...toolbarBtn, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
              <Upload size={13} /> Файлдан юклаш
              <input
                type="file"
                accept=".txt,.md,.csv,.pdf,.docx,.xlsx,.xls,.pptx"
                style={{ display: 'none' }}
                onChange={async (e) => {
                  const f = e.target.files?.[0]
                  if (!f) return
                  try {
                    const ex = await extractFile(f)
                    setSourceText(ex.text)
                    setRichSrcHtml(ex.html || '')
                    if (f.name.toLowerCase().endsWith('.docx')) setLoadedDocxFile(f)
                  } catch (err: any) {
                    alert('Файлни ўқиб бўлмади: ' + (err?.message || err))
                  }
                  e.target.value = ''
                }}
              />
            </label>

            <button onClick={exportToDocx} disabled={!sourceText.trim() && !targetText.trim()}
              title="Таржима натижасини DOCX форматда юклаб олиш"
              style={{ ...toolbarBtn, background: '#EFF6FF', color: '#1D4ED8', borderColor: '#93C5FD' }}>
              <FileDown size={13} /> DOCX
            </button>

            <button
              onClick={async () => {
                // Self-learning: diff source + target before clearing
                const sLang = sourceLang.startsWith('uz') ? 'uz' : sourceLang
                const tLang = targetLang.startsWith('uz') ? 'uz' : targetLang
                await sendLearnDiff(originalSource, sourceText, sLang, 'tilshunos_translate_src')
                await sendLearnDiff(originalTarget, targetText, tLang, 'tilshunos_translate_tgt')
                setLoadedDocxFile(null)
                setSourceText(''); setTargetText(''); setRichSrcHtml(''); setRichTgtHtml(''); setOriginalSource(''); setOriginalTarget('')
              }}
              disabled={!sourceText && !targetText}
              style={{ ...toolbarBtn, background: '#FEF2F2', color: '#DC2626', borderColor: '#FCA5A5', opacity: (sourceText || targetText) ? 1 : 0.5 }}
            >
              <Trash2 size={13} /> Тозалаш
            </button>

            <button
              onClick={async () => {
                if (!sourceText.trim()) return
                setTranslating(true)
                try {
                  const sLang = sourceLang.startsWith('uz') ? 'uz' : sourceLang
                  const tLang = targetLang.startsWith('uz') ? 'uz' : targetLang
                  const r = await api.tilshunos.translate(sourceText, sLang, tLang)
                  setTargetText(r.translated || '')
                  setOriginalTarget(r.translated || '')
                } catch (e: any) {
                  alert('Таржима хатоси: ' + (e?.message || e))
                } finally {
                  setTranslating(false)
                }
              }}
              disabled={translating || !sourceText.trim()}
              style={{ ...toolbarBtn, marginLeft: 'auto', background: 'linear-gradient(135deg,#10B981,#059669)', color: 'white', border: 'none', padding: '8px 18px' }}
            >
              {translating ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />} Таржима қилиш
            </button>

            <button onClick={() => transliterateField(sourceText, setSourceText, 'cyrillic')}
              disabled={!sourceText.trim()}
              style={{ ...toolbarBtn, background: '#FFF7ED', color: '#EA580C', borderColor: '#FB923C', opacity: sourceText.trim() ? 1 : 0.5 }}>
              🔄 Кирил
            </button>
            <button onClick={() => transliterateField(sourceText, setSourceText, 'latin')}
              disabled={!sourceText.trim()}
              style={{ ...toolbarBtn, background: '#F0FDF4', color: '#16A34A', borderColor: '#22C55E', opacity: sourceText.trim() ? 1 : 0.5 }}>
              🔄 Лотин
            </button>

            <button
              onClick={async () => {
                const sel = window.getSelection()?.toString().trim()
                if (!sel) { alert('Аввал матндан сўзни белгиланг'); return }
                try {
                  const r = await api.synonyms.list(sel)
                  const opts = (r as any).synonyms?.map((s: any) => s.synonym) || []
                  setSynPopup({ word: sel, x: window.innerWidth / 2 - 120, y: 200, options: opts })
                } catch (_) { alert('Хатолик') }
              }}
              style={toolbarBtn}
            >
              Синонимлар
            </button>

            <button
              onClick={async () => {
                const sel = window.getSelection()?.toString().trim()
                if (!sel) { alert('Аввал матндан сўзни белгиланг'); return }
                try {
                  const backendLang = sourceLang.startsWith('uz') ? 'uz' : sourceLang
                  const r = await api.dictionary.add(sel, backendLang)
                  if (r.ok) {
                    api.dictionary.translate(sel).catch(() => {})
                    alert(`"${sel}" луғатга қўшилди ✓`)
                  } else alert('Хатолик: ' + (r.error || ''))
                } catch (e: any) { alert('Хатолик: ' + (e?.message || e)) }
              }}
              style={toolbarBtn}
            >
              <BookPlus size={13} /> Луғатга қўшиш
            </button>
          </div>

          {/* 4-layer Linguistic Analysis Bar for source text */}
          <div style={{ marginBottom: 10 }}>
            <LinguisticAnalysisBar text={sourceText} lang={sourceLang === 'ru' ? 'ru' : 'uz'} compact onTextChange={(t) => setSourceText(t)} />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, minHeight: 360 }}>
            <div style={{ background: 'var(--bg-card)', border: '1.5px solid var(--border)', borderRadius: 12, padding: 14 }} onDoubleClick={synonymPopup.handleClick}>
              <div style={{ fontSize: '0.72rem', fontWeight: 700, marginBottom: 8, color: 'var(--text-muted)' }}>{LANG_LABELS[sourceLang]}</div>
              {richSrcHtml ? (
                <div
                  ref={richSrcRef}
                  contentEditable
                  suppressContentEditableWarning
                  onInput={e => setSourceText((e.currentTarget as HTMLDivElement).innerText)}
                  onScroll={handleSourceScroll}
                  dangerouslySetInnerHTML={{ __html: richSrcHtml }}
                  className="docx-rich"
                  style={{ width: '100%', minHeight: 500, padding: 20, border: '1.5px solid var(--border)', borderRadius: 8, fontSize: '0.9rem', fontFamily: 'Times New Roman, Georgia, serif', background: 'white', lineHeight: 1.6, outline: 'none', overflow: 'auto' }}
                />
              ) : (
                <>
                  <textarea value={sourceText} onChange={e => setSourceText(e.target.value)} placeholder="Асл матн..." style={{ width: '100%', minHeight: 300, padding: 10, border: '1.5px solid var(--border)', borderRadius: 8, fontSize: '0.88rem', fontFamily: 'inherit', resize: 'vertical', outline: 'none', background: 'var(--bg-secondary)' }} />
                  {(linguistic.annotated.length + linguistic.disputed.length + linguistic.abbreviations.length) > 0 && sourceText && (
                    <div style={{ marginTop: 6, padding: '6px 10px', background: '#FAFBFF', border: '1px dashed #E5E7EB', borderRadius: 6, fontSize: '0.72rem', lineHeight: 1.5 }}>
                      <div style={{ fontSize: '0.58rem', color: '#9CA3AF', fontWeight: 700, textTransform: 'uppercase', marginBottom: 3 }}>🧬 Лингвистик аниқланган</div>
                      {linguistic.annotated.map((a, i) => <span key={`a${i}`} style={{ display: 'inline-block', margin: 2, padding: '1px 6px', background: '#F3E8FF', color: '#7C3AED', borderRadius: 4, fontWeight: 600 }}>{a.text}</span>)}
                      {linguistic.disputed.map((d, i) => <span key={`d${i}`} style={{ display: 'inline-block', margin: 2, padding: '1px 6px', background: '#FEE2E2', color: '#DC2626', borderRadius: 4, fontWeight: 600 }}>{d.text}</span>)}
                      {linguistic.abbreviations.map((b, i) => <span key={`b${i}`} style={{ display: 'inline-block', margin: 2, padding: '1px 6px', background: '#DCFCE7', color: '#16A34A', borderRadius: 4, fontWeight: 600 }}>{b.text}</span>)}
                    </div>
                  )}
                </>
              )}
            </div>
            <div style={{ background: 'var(--bg-card)', border: '1.5px solid var(--border)', borderRadius: 12, padding: 14 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                <div style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)' }}>{LANG_LABELS[targetLang]}</div>
                {targetText.trim() && (
                  <div style={{ display: 'flex', gap: 4 }}>
                    <button onClick={() => transliterateField(targetText, setTargetText, 'cyrillic')}
                      style={{ padding: '2px 8px', borderRadius: 4, border: '1.5px solid #FB923C', background: '#FFF7ED', color: '#EA580C', fontSize: '0.6rem', fontWeight: 800, cursor: 'pointer' }}>🔄 Кирил</button>
                    <button onClick={() => transliterateField(targetText, setTargetText, 'latin')}
                      style={{ padding: '2px 8px', borderRadius: 4, border: '1.5px solid #22C55E', background: '#F0FDF4', color: '#16A34A', fontSize: '0.6rem', fontWeight: 800, cursor: 'pointer' }}>🔄 Лотин</button>
                  </div>
                )}
              </div>
              {richTgtHtml ? (
                <div
                  ref={richTgtRef}
                  contentEditable
                  suppressContentEditableWarning
                  onInput={e => setTargetText((e.currentTarget as HTMLDivElement).innerText)}
                  onScroll={handleTargetScroll}
                  dangerouslySetInnerHTML={{ __html: richTgtHtml }}
                  className="docx-rich"
                  style={{ width: '100%', minHeight: 500, padding: 20, border: '1.5px solid var(--border)', borderRadius: 8, fontSize: '0.9rem', fontFamily: 'Times New Roman, Georgia, serif', background: 'white', lineHeight: 1.6, outline: 'none', overflow: 'auto' }}
                />
              ) : (
                <>
                  <textarea value={targetText} onChange={e => setTargetText(e.target.value)} placeholder="Таржима..." style={{ width: '100%', minHeight: 300, padding: 10, border: '1.5px solid var(--border)', borderRadius: 8, fontSize: '0.88rem', fontFamily: 'inherit', resize: 'vertical', outline: 'none', background: 'var(--bg-secondary)' }} />
                  {(linguistic.annotated.length + linguistic.disputed.length + linguistic.abbreviations.length) > 0 && targetText && (
                    <div style={{ marginTop: 6, padding: '6px 10px', background: '#FAFBFF', border: '1px dashed #E5E7EB', borderRadius: 6, fontSize: '0.72rem', lineHeight: 1.5 }}>
                      <div style={{ fontSize: '0.58rem', color: '#9CA3AF', fontWeight: 700, textTransform: 'uppercase', marginBottom: 3 }}>🧬 Лингвистик аниқланган (таржима)</div>
                      {linguistic.annotated.map((a, i) => <span key={`ta${i}`} style={{ display: 'inline-block', margin: 2, padding: '1px 6px', background: '#F3E8FF', color: '#7C3AED', borderRadius: 4, fontWeight: 600 }}>{a.text}</span>)}
                      {linguistic.disputed.map((d, i) => <span key={`td${i}`} style={{ display: 'inline-block', margin: 2, padding: '1px 6px', background: '#FEE2E2', color: '#DC2626', borderRadius: 4, fontWeight: 600 }}>{d.text}</span>)}
                      {linguistic.abbreviations.map((b, i) => <span key={`tb${i}`} style={{ display: 'inline-block', margin: 2, padding: '1px 6px', background: '#DCFCE7', color: '#16A34A', borderRadius: 4, fontWeight: 600 }}>{b.text}</span>)}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
          <style jsx global>{`
            .docx-rich table { border-collapse: collapse; width: 100%; margin: 8px 0; }
            .docx-rich table, .docx-rich th, .docx-rich td { border: 1px solid #D1D5DB; }
            .docx-rich th, .docx-rich td { padding: 6px 10px; vertical-align: top; }
            .docx-rich img { max-width: 100%; height: auto; display: block; margin: 8px 0; }
            .docx-rich h1, .docx-rich h2, .docx-rich h3 { font-weight: 700; margin: 12px 0 6px; }
            .docx-rich p { margin: 6px 0; }
            .docx-rich ul, .docx-rich ol { padding-left: 24px; }
          `}</style>

          {/* ───────── DOCUMENT TRANSLATION (format-preserving) ───────── */}
          <DocumentTranslateSection sourceLang={sourceLang} targetLang={targetLang} />
        </div>
      ) : (
        /* ───────── WORD MODE (docx-preview) ───────── */
        <WordMode
          onRunSayqallash={async (txt) => {
            if (!txt || !txt.trim()) { alert('⚠ Матн бўш. Ҳужжатдан матнни танланг ёки кутинг matn yuklansin.'); return }
            try {
              const res: any = await api.analyze.full(txt.slice(0, 5000), 'uz', ['sayqallash', 'style'])
              const say = (res?.sayqallash || []).length
              const sty = (res?.style || []).length
              alert(`✅ Сайқаллаш + Style натижа:\n\n• Имло / қоидалар: ${say} та\n• Style Guide: ${sty} та\n\nУмумий: ${say + sty}`)
            } catch (e: any) { alert('❌ Сайқаллаш xatosi: ' + (e?.message || 'тармоқ xatosi')) }
          }}
          onRunSyntax={async (txt) => {
            if (!txt || !txt.trim()) { alert('⚠ Матн бўш'); return }
            try {
              const res: any = await api.analyze.full(txt.slice(0, 5000), 'uz', ['syntax', 'morph'])
              const syn = (res?.syntax || []).length
              const mor = (res?.morph || []).length
              alert(`✅ Синтаксис натижа:\n\n• Гап тузилиши xatoлари: ${syn} та\n• Сўз таҳлили: ${mor} та\n\nБатафсил: /syntax саҳифасига ўтинг.`)
            } catch (e: any) { alert('❌ Синтаксис xatosi: ' + (e?.message || 'тармоқ xatosi')) }
          }}
          onRunTranslate={(txt) => {
            if (!txt || !txt.trim()) { alert('⚠ Матн бўш'); return }
            setSourceText(txt.slice(0, 5000))
            setMode('translate')
          }}
        />
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
            {/* SECTION 1: Сайқаллаш (suggestions) */}
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

              {/* SECTION 2: Морфология */}
              {popupMorph && (
                <div style={{ marginTop: 8, padding: 8, background: '#E0F2FE', border: '1px solid #7DD3FC', borderRadius: 6 }}>
                  <div style={{ fontSize: '0.6rem', color: '#0369A1', fontWeight: 700, marginBottom: 4, textTransform: 'uppercase' }}>Морфология</div>
                  <div style={{ fontSize: '0.75rem', color: '#1E3A5F', lineHeight: 1.6 }}>
                    {popupMorph.root && <div><strong>Ўзак:</strong> {popupMorph.root}</div>}
                    {popupMorph.pos && <div><strong>Сўз туркуми:</strong> {popupMorph.pos}</div>}
                    {popupMorph.case && <div><strong>Келишик:</strong> {popupMorph.case}</div>}
                    {popupMorph.affixes && popupMorph.affixes.length > 0 && (
                      <div><strong>Аффикслар:</strong> {popupMorph.affixes.map((a: any, i: number) => (
                        <span key={i} style={{ display: 'inline-block', margin: '1px 2px', padding: '0 4px', background: '#BAE6FD', borderRadius: 3, fontSize: '0.7rem' }}>
                          -{a.affix || a}{a.meaning ? ` (${a.meaning})` : ''}
                        </span>
                      ))}</div>
                    )}
                    {popupMorph.prefix && <div><strong>Префикс:</strong> {popupMorph.prefix}</div>}
                    {popupMorph.suffix && <div><strong>Суффикс:</strong> {popupMorph.suffix}</div>}
                    {popupMorph.description && <div style={{ marginTop: 4, fontStyle: 'italic', color: '#475569', fontSize: '0.7rem' }}>{popupMorph.description}</div>}
                  </div>
                </div>
              )}

              {/* SECTION 3: Синонимлар */}
              <div style={{ marginTop: 8, padding: 8, background: '#F5F3FF', border: '1px solid #C4B5FD', borderRadius: 6 }}>
                <div style={{ fontSize: '0.6rem', color: '#6D28D9', fontWeight: 700, marginBottom: 4, textTransform: 'uppercase' }}>Синонимлар</div>
                {popupSynonyms.loading ? (
                  <div style={{ textAlign: 'center', padding: 4, color: '#7C3AED', fontSize: '0.7rem' }}>
                    <Loader2 size={12} className="animate-spin" style={{ display: 'inline-block', verticalAlign: 'middle', marginRight: 4 }} />
                    Юкланмоқда...
                  </div>
                ) : popupSynonyms.items.length === 0 ? (
                  <div style={{ fontSize: '0.7rem', color: '#9CA3AF' }}>Синоним топилмади</div>
                ) : (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
                    {popupSynonyms.items.map((syn, i) => (
                      <span
                        key={i}
                        onClick={() => applyFix(popup.issue, syn)}
                        style={{
                          padding: '2px 7px', background: '#EDE9FE', borderRadius: 4,
                          fontSize: '0.72rem', fontWeight: 600, color: '#5B21B6',
                          cursor: 'pointer', border: '1px solid transparent',
                        }}
                        onMouseEnter={e => { e.currentTarget.style.background = '#DDD6FE'; e.currentTarget.style.borderColor = '#7C3AED' }}
                        onMouseLeave={e => { e.currentTarget.style.background = '#EDE9FE'; e.currentTarget.style.borderColor = 'transparent' }}
                      >
                        {syn}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Custom user input */}
              <div style={{ marginTop: 8, padding: 8, background: '#FFF7ED', border: '1.5px dashed #FB923C', borderRadius: 6 }}>
                <div style={{ fontSize: '0.62rem', color: '#9A3412', fontWeight: 700, marginBottom: 4, textTransform: 'uppercase' }}>✎ Ўз вариантингиз</div>
                <input
                  id="custom-fix-input"
                  type="text"
                  placeholder={popup.issue.matched_text}
                  defaultValue={popup.issue.matched_text}
                  autoFocus
                  onKeyDown={async (e) => {
                    if (e.key === 'Enter') {
                      const customValue = (e.target as HTMLInputElement).value.trim()
                      if (customValue && customValue !== popup.issue.matched_text) {
                        // Save to sayqallash DB via /confirm endpoint
                        try {
                          await api.tilshunos.confirm({
                            wrong: popup.issue.matched_text,
                            correct: customValue,
                            context: text.substring(Math.max(0, popup.issue.from_index - 50), Math.min(text.length, popup.issue.to_index + 50)),
                            category: popup.issue.error_type,
                            lang: lang.startsWith('uz') ? 'uz' : lang,
                          })
                        } catch (_) {}
                        applyFix(popup.issue, customValue)
                      }
                    }
                  }}
                  style={{
                    width: '100%', padding: '6px 10px', borderRadius: 5,
                    border: '1.5px solid #FB923C', fontSize: '0.78rem',
                    fontFamily: 'inherit', outline: 'none', background: 'white',
                  }}
                />
                <button
                  onClick={async () => {
                    const input = document.getElementById('custom-fix-input') as HTMLInputElement | null
                    const customValue = input?.value.trim() || ''
                    if (customValue && customValue !== popup.issue.matched_text) {
                      try {
                        await api.tilshunos.confirm({
                          wrong: popup.issue.matched_text,
                          correct: customValue,
                          context: text.substring(Math.max(0, popup.issue.from_index - 50), Math.min(text.length, popup.issue.to_index + 50)),
                          category: popup.issue.error_type,
                          lang: lang.startsWith('uz') ? 'uz' : lang,
                        })
                      } catch (_) {}
                      applyFix(popup.issue, customValue)
                    }
                  }}
                  style={{
                    marginTop: 4, width: '100%', padding: '5px 10px',
                    background: 'linear-gradient(135deg,#F97316,#EA580C)',
                    color: 'white', border: 'none', borderRadius: 5,
                    fontSize: '0.72rem', fontWeight: 700, cursor: 'pointer',
                  }}
                >
                  ✓ Қабул қилиш ва базага сақлаш
                </button>
                <div style={{ marginTop: 4, fontSize: '0.6rem', color: '#9A3412' }}>
                  💾 Қайта таҳлилда автоматик ишлатилади
                </div>
              </div>
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

      {/* Morphology popup for DRUG entities (Greek/Latin decomposition) */}
      {morphPopup && (
        <>
          <div onClick={() => setMorphPopup(null)} style={{ position: 'fixed', inset: 0, zIndex: 90 }} />
          <div style={{
            position: 'fixed',
            left: Math.min(morphPopup.x, window.innerWidth - 380),
            top: Math.min(morphPopup.y, window.innerHeight - 250),
            background: 'white', border: '2px solid #7C3AED', borderRadius: 12,
            boxShadow: '0 12px 48px rgba(0,0,0,0.25)', zIndex: 100, minWidth: 320, maxWidth: 400, padding: 16,
          }}>
            <div style={{ display: 'inline-block', padding: '3px 10px', borderRadius: 6, background: '#7C3AED', color: 'white', fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase', marginBottom: 10 }}>
              💊 Морфема таҳлили
            </div>
            <div style={{ fontSize: '1rem', fontWeight: 800, color: '#5B21B6', marginBottom: 10 }}>{morphPopup.word}</div>
            {morphPopup.data?.found ? (
              <div style={{ fontSize: '0.82rem', lineHeight: 1.7 }}>
                {morphPopup.data.prefix && (
                  <div style={{ marginBottom: 6 }}>
                    <strong style={{ color: '#7C3AED' }}>Префикс:</strong> <code style={{ background: '#F3E8FF', padding: '1px 6px', borderRadius: 3 }}>{morphPopup.data.prefix}</code>
                    <div style={{ fontSize: '0.75rem', color: '#6B7280', marginLeft: 4 }}>{morphPopup.data.prefix_meaning}</div>
                  </div>
                )}
                {morphPopup.data.root && (
                  <div style={{ marginBottom: 6 }}>
                    <strong style={{ color: '#16A34A' }}>Ўзак:</strong> <code style={{ background: '#DCFCE7', padding: '1px 6px', borderRadius: 3 }}>{morphPopup.data.root}</code>
                  </div>
                )}
                {morphPopup.data.suffix && (
                  <div style={{ marginBottom: 6 }}>
                    <strong style={{ color: '#0891B2' }}>Суффикс:</strong> <code style={{ background: '#CFFAFE', padding: '1px 6px', borderRadius: 3 }}>{morphPopup.data.suffix}</code>
                    <div style={{ fontSize: '0.75rem', color: '#6B7280', marginLeft: 4 }}>{morphPopup.data.suffix_meaning}</div>
                  </div>
                )}
                {morphPopup.data.meaning && (
                  <div style={{ marginTop: 10, padding: 8, background: '#F9FAFB', borderRadius: 6, fontSize: '0.75rem', color: '#475569', fontStyle: 'italic', borderLeft: '3px solid #7C3AED' }}>
                    {morphPopup.data.meaning}
                  </div>
                )}
              </div>
            ) : (
              <div style={{ fontSize: '0.85rem', color: '#9CA3AF' }}>Морфемалари аниқланмади</div>
            )}
          </div>
        </>
      )}

      {/* Linguistic info popup (annotated/disputed/abbreviation) */}
      {linguisticPopup && (
        <>
          <div onClick={() => setLinguisticPopup(null)} style={{ position: 'fixed', inset: 0, zIndex: 90 }} />
          <div style={{
            position: 'fixed',
            left: Math.min(linguisticPopup.x, window.innerWidth - 380),
            top: Math.min(linguisticPopup.y, window.innerHeight - 300),
            background: 'white', border: '1.5px solid var(--border)', borderRadius: 10,
            boxShadow: '0 8px 24px rgba(0,0,0,0.18)', zIndex: 100, minWidth: 340, maxWidth: 420, padding: 14,
          }}>
            <div style={{
              display: 'inline-block', padding: '3px 10px', borderRadius: 6,
              background: linguisticPopup.type === 'annotated' ? '#7C3AED' : linguisticPopup.type === 'disputed' ? '#DC2626' : '#16A34A',
              color: 'white', fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase',
              marginBottom: 8,
            }}>
              {linguisticPopup.type === 'annotated' ? 'Изоҳли' : linguisticPopup.type === 'disputed' ? 'Мунозарали' : 'Қисқартма'}
            </div>
            {linguisticPopup.data && (
              <div style={{ fontSize: '0.85rem', color: '#374151' }}>
                {(linguisticPopup.data.uz || linguisticPopup.data.word) && (
                  <div style={{ marginBottom: 6 }}><strong>UZ:</strong> {linguisticPopup.data.uz || linguisticPopup.data.word}</div>
                )}
                {linguisticPopup.data.ru && (
                  <div style={{ marginBottom: 6 }}><strong>RU:</strong> {linguisticPopup.data.ru}</div>
                )}
                {linguisticPopup.data.en && (
                  <div style={{ marginBottom: 6 }}><strong>EN:</strong> {linguisticPopup.data.en}</div>
                )}
                {(linguisticPopup.data.definition || linguisticPopup.data.full_form) && (
                  <div style={{ marginTop: 8, padding: 8, background: '#F9FAFB', borderRadius: 6, fontSize: '0.78rem', color: '#475569', borderLeft: '3px solid #E5E7EB' }}>
                    {linguisticPopup.data.definition || linguisticPopup.data.full_form}
                  </div>
                )}
              </div>
            )}
          </div>
        </>
      )}

      {/* Inline synonym popup — floating */}
      {synonymPopup.PopupElement}
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

// ═══════════════════════════════════════════════════
// Document Translation Section (format-preserving DOCX/XLSX/PPTX)
// ═══════════════════════════════════════════════════

const DOC_EXTENSIONS: Record<string, { label: string; accept: string; color: string }> = {
  docx: { label: 'DOCX', accept: '.docx', color: '#2563EB' },
  xlsx: { label: 'XLSX', accept: '.xlsx', color: '#16A34A' },
  pptx: { label: 'PPTX', accept: '.pptx', color: '#DC2626' },
}

function DocumentTranslateSection({ sourceLang, targetLang }: { sourceLang: string; targetLang: string }) {
  const [docFile, setDocFile] = useState<File | null>(null)
  const [docProgress, setDocProgress] = useState(0)
  const [docTranslating, setDocTranslating] = useState(false)
  const [docResult, setDocResult] = useState<Blob | null>(null)
  const [docError, setDocError] = useState('')
  const [docPreview, setDocPreview] = useState<{ paragraphs: string[]; total_paragraphs: number } | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const getFileType = (name: string): string | null => {
    const ext = name.split('.').pop()?.toLowerCase()
    if (ext === 'docx' || ext === 'xlsx' || ext === 'pptx') return ext
    return null
  }

  const handleFileSelect = async (file: File) => {
    const ftype = getFileType(file.name)
    if (!ftype) {
      setDocError('Фақат DOCX, XLSX ёки PPTX файллар қабул қилинади')
      return
    }
    setDocFile(file)
    setDocResult(null)
    setDocError('')
    setDocProgress(0)
    // Load preview
    try {
      const prev = await api.documents.preview(file)
      setDocPreview({ paragraphs: prev.paragraphs, total_paragraphs: prev.total_paragraphs })
    } catch {
      setDocPreview(null)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f) handleFileSelect(f)
  }

  const translateDocument = async () => {
    if (!docFile) return
    const ftype = getFileType(docFile.name)
    if (!ftype) return

    setDocTranslating(true)
    setDocProgress(5)
    setDocError('')
    setDocResult(null)

    const sLang = sourceLang.startsWith('uz') ? 'uz' : sourceLang
    const tLang = targetLang.startsWith('uz') ? 'uz' : targetLang

    try {
      let blob: Blob
      const onProgress = (pct: number) => setDocProgress(pct)
      if (ftype === 'docx') {
        blob = await api.documents.translateDocx(docFile, sLang, tLang, 'auto', onProgress)
      } else if (ftype === 'xlsx') {
        blob = await api.documents.translateXlsx(docFile, sLang, tLang, 'auto', onProgress)
      } else {
        blob = await api.documents.translatePptx(docFile, sLang, tLang, 'auto', onProgress)
      }
      setDocResult(blob)
      setDocProgress(100)
    } catch (err: any) {
      setDocError(err?.detail || err?.message || 'Таржима хатоси')
    } finally {
      setDocTranslating(false)
    }
  }

  const downloadResult = () => {
    if (!docResult || !docFile) return
    const ext = docFile.name.split('.').pop() || 'docx'
    const baseName = docFile.name.replace(/\.[^.]+$/, '')
    const tLang = targetLang.startsWith('uz') ? 'uz' : targetLang
    const outName = `${baseName}_${tLang}.${ext}`
    const url = URL.createObjectURL(docResult)
    const a = document.createElement('a')
    a.href = url
    a.download = outName
    a.click()
    URL.revokeObjectURL(url)
  }

  const ftype = docFile ? getFileType(docFile.name) : null
  const ftypeInfo = ftype ? DOC_EXTENSIONS[ftype] : null

  return (
    <div style={{ marginTop: 20, padding: 16, background: 'var(--bg-card)', border: '1.5px solid var(--border)', borderRadius: 12 }}>
      <div style={{ fontSize: '0.82rem', fontWeight: 700, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
        <FileText size={16} />
        Ҳужжат таржимаси (формат сақланади)
      </div>

      {/* Drop zone */}
      {!docFile && (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          style={{
            border: `2px dashed ${dragOver ? '#10B981' : '#D1D5DB'}`,
            borderRadius: 10,
            padding: '32px 20px',
            textAlign: 'center',
            cursor: 'pointer',
            background: dragOver ? '#F0FDF4' : 'var(--bg-secondary)',
            transition: 'all 0.2s',
          }}
        >
          <FileUp size={32} color={dragOver ? '#10B981' : '#9CA3AF'} style={{ margin: '0 auto 8px' }} />
          <div style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>
            Файлни ташланг ёки танланг
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
            DOCX, XLSX, PPTX — барча форматлаш сақланади
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".docx,.xlsx,.pptx"
            style={{ display: 'none' }}
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) handleFileSelect(f)
              e.target.value = ''
            }}
          />
        </div>
      )}

      {/* Selected file info */}
      {docFile && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12, padding: '10px 14px', background: 'var(--bg-secondary)', borderRadius: 8 }}>
            <div style={{
              padding: '3px 8px', borderRadius: 6, fontSize: '0.65rem', fontWeight: 800,
              background: ftypeInfo?.color || '#6B7280', color: 'white', textTransform: 'uppercase',
            }}>
              {ftypeInfo?.label || 'FILE'}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '0.8rem', fontWeight: 600 }}>{docFile.name}</div>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                {(docFile.size / 1024).toFixed(1)} КБ
                {docPreview ? ` · ${docPreview.total_paragraphs} параграф` : ''}
              </div>
            </div>
            <button
              onClick={() => { setDocFile(null); setDocResult(null); setDocPreview(null); setDocError(''); setDocProgress(0) }}
              style={{ background: '#FEF2F2', border: '1px solid #FCA5A5', borderRadius: 6, padding: '4px 10px', color: '#DC2626', fontSize: '0.7rem', fontWeight: 700, cursor: 'pointer' }}
            >
              <Trash2 size={12} /> Ўчириш
            </button>
          </div>

          {/* Preview */}
          {docPreview && docPreview.paragraphs.length > 0 && !docResult && (
            <div style={{ marginBottom: 12, padding: 10, background: '#FAFBFF', border: '1px dashed #E5E7EB', borderRadius: 8, maxHeight: 150, overflow: 'auto' }}>
              <div style={{ fontSize: '0.6rem', color: '#9CA3AF', fontWeight: 700, textTransform: 'uppercase', marginBottom: 4 }}>
                Асл матн (олдиндан кўриш)
              </div>
              {docPreview.paragraphs.slice(0, 20).map((p, i) => (
                <div key={i} style={{ fontSize: '0.72rem', color: '#374151', padding: '2px 0', borderBottom: '1px solid #F3F4F6' }}>
                  {p.length > 120 ? p.slice(0, 120) + '...' : p}
                </div>
              ))}
              {docPreview.total_paragraphs > 20 && (
                <div style={{ fontSize: '0.65rem', color: '#9CA3AF', marginTop: 4 }}>
                  ... яна {docPreview.total_paragraphs - 20} параграф
                </div>
              )}
            </div>
          )}

          {/* Progress bar */}
          {docTranslating && (
            <div style={{ marginBottom: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                <Loader2 size={14} className="animate-spin" color="#10B981" />
                <span style={{ fontSize: '0.72rem', fontWeight: 600, color: '#10B981' }}>
                  Таржима қилинмоқда... {docProgress}%
                </span>
              </div>
              <div style={{ height: 6, background: '#E5E7EB', borderRadius: 3, overflow: 'hidden' }}>
                <div style={{
                  height: '100%',
                  width: `${docProgress}%`,
                  background: 'linear-gradient(90deg, #10B981, #059669)',
                  borderRadius: 3,
                  transition: 'width 0.3s ease',
                }} />
              </div>
            </div>
          )}

          {/* Error */}
          {docError && (
            <div style={{ marginBottom: 12, padding: '8px 12px', background: '#FEF2F2', border: '1px solid #FCA5A5', borderRadius: 8, fontSize: '0.75rem', color: '#DC2626' }}>
              {docError}
            </div>
          )}

          {/* Success + Download */}
          {docResult && (
            <div style={{ marginBottom: 12, padding: '12px 16px', background: '#F0FDF4', border: '1.5px solid #86EFAC', borderRadius: 10, display: 'flex', alignItems: 'center', gap: 10 }}>
              <CheckCircle2 size={20} color="#16A34A" />
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#166534' }}>Таржима тайёр!</div>
                <div style={{ fontSize: '0.65rem', color: '#15803D' }}>Барча форматлаш сақланди</div>
              </div>
              <button
                onClick={downloadResult}
                style={{
                  display: 'flex', alignItems: 'center', gap: 6,
                  background: 'linear-gradient(135deg, #10B981, #059669)',
                  color: 'white', border: 'none', borderRadius: 8,
                  padding: '8px 18px', fontSize: '0.78rem', fontWeight: 700, cursor: 'pointer',
                }}
              >
                <Download size={14} /> Юклаб олиш
              </button>
            </div>
          )}

          {/* Action buttons */}
          {!docResult && !docTranslating && (
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={translateDocument}
                style={{
                  display: 'flex', alignItems: 'center', gap: 6,
                  background: 'linear-gradient(135deg, #10B981, #059669)',
                  color: 'white', border: 'none', borderRadius: 8,
                  padding: '10px 22px', fontSize: '0.8rem', fontWeight: 700, cursor: 'pointer',
                  flex: 1, justifyContent: 'center',
                }}
              >
                <Play size={14} /> Ҳужжатни таржима қилиш
              </button>
            </div>
          )}
        </div>
      )}
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

// ═══════════════════════════════════════════════════
// Word Mode — docx-preview integration (Stage 1 of 3)
// ═══════════════════════════════════════════════════
function WordMode({
  onRunSayqallash,
  onRunSyntax,
  onRunTranslate,
}: {
  onRunSayqallash: (text: string) => void
  onRunSyntax: (text: string) => void
  onRunTranslate: (text: string) => void
}) {
  const [file, setFile] = useState<File | null>(null)
  const [fullText, setFullText] = useState('')
  const [subMode, setSubMode] = useState<'preview' | 'edit'>('preview')

  const handleFile = (f: File) => {
    if (!f.name.toLowerCase().endsWith('.docx')) {
      alert("Faqat .docx формат qo'llab-quvvatlanadi. .doc → .docx конверт қилинг.")
      return
    }
    setFile(f)
  }

  return (
    <div>
      {/* Upload bar */}
      <div style={{ background: 'white', borderRadius: 12, padding: 16, marginBottom: 14, border: '1.5px solid var(--border)', display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
        <label style={{
          padding: '10px 18px', borderRadius: 10, background: 'linear-gradient(135deg, #2563EB, #1D4ED8)',
          color: 'white', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8, fontWeight: 700, fontSize: '.85rem',
        }}>
          <Upload size={15} /> .docx файл юклаш
          <input type="file" accept=".docx" hidden onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f) }} />
        </label>
        {file && (
          <>
            <div style={{ fontSize: '.8rem', color: '#475569' }}>
              <strong>{file.name}</strong>
              <span style={{ marginLeft: 8, color: '#94A3B8', fontSize: '.72rem' }}>
                ({(file.size / 1024).toFixed(1)} KB)
              </span>
            </div>
            {/* Preview/Edit sub-mode toggle */}
            <div style={{ display: 'flex', gap: 4, background: '#F1F5F9', borderRadius: 10, padding: 3, border: '1px solid #E2E8F0' }}>
              <button onClick={() => setSubMode('preview')} style={{
                padding: '6px 14px', borderRadius: 7, border: 'none',
                background: subMode === 'preview' ? 'linear-gradient(135deg, #3B82F6, #2563EB)' : 'transparent',
                color: subMode === 'preview' ? 'white' : '#64748B',
                fontWeight: 700, fontSize: '.74rem', cursor: 'pointer',
              }}>📖 Preview</button>
              <button onClick={() => setSubMode('edit')} style={{
                padding: '6px 14px', borderRadius: 7, border: 'none',
                background: subMode === 'edit' ? 'linear-gradient(135deg, #16A34A, #15803D)' : 'transparent',
                color: subMode === 'edit' ? 'white' : '#64748B',
                fontWeight: 700, fontSize: '.74rem', cursor: 'pointer',
              }}>✏️ Edit (SuperDoc)</button>
            </div>
            <button onClick={() => { setFile(null); setFullText('') }} style={{ marginLeft: 'auto', padding: '8px 14px', borderRadius: 8, border: '1px solid #FECACA', background: '#FEF2F2', color: '#B91C1C', fontWeight: 700, fontSize: '.78rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
              <Trash2 size={13} /> Тозалаш
            </button>
          </>
        )}
        {!file && (
          <span style={{ fontSize: '.76rem', color: '#94A3B8', fontStyle: 'italic' }}>
            Word ҳужжатингизни юкланг — жадваллар, расмлар, колонтитуллар сақланади
          </span>
        )}
      </div>

      {/* Info banner (first-time hint) */}
      {!file && (
        <div style={{
          background: 'linear-gradient(135deg, #DBEAFE 0%, #EDE9FE 100%)', borderRadius: 12, padding: '14px 18px', marginBottom: 14,
          border: '1px solid #BFDBFE', fontSize: '.82rem', color: '#1E40AF',
        }}>
          💡 <strong>Word ҳужжат режими (Босқич 1)</strong> — docx-preview орқали тўлиқ фиделити кўрсатиш: жадваллар, расмлар, колонтитуллар, ҳавolalar.
          Матнни танланг ва юқоридаги AI тугмаларини босиб сайқаллаш / синтаксис / таржима амалга оширинг.
          <br />
          <span style={{ fontSize: '.72rem', opacity: 0.8 }}>
            📌 Босқич 2 (SuperDoc) ва Босқич 3 (ONLYOFFICE — MathType) кейинги итерацияларда қўшилади.
          </span>
        </div>
      )}

      {/* 4-layer Linguistic Analysis Bar — runs against extracted text */}
      {file && fullText && (
        <div style={{ marginBottom: 10 }}>
          <LinguisticAnalysisBar text={fullText} lang="uz" compact onTextChange={(t) => setFullText(t)} />
        </div>
      )}

      {subMode === 'preview' ? (
        <ErrorBoundary name="Word Preview" compact>
          <WordDocumentViewer
            file={file}
            onTextExtracted={setFullText}
            aiActions={[
              { label: 'Сайқаллаш', icon: <Sparkles size={12} />, color: '#8B5E3C', onClick: (sel, full) => onRunSayqallash(sel || full) },
              { label: 'Синтаксис', icon: <Wand2 size={12} />, color: '#7C3AED', onClick: (sel, full) => onRunSyntax(sel || full) },
              { label: 'Таржима', icon: <ArrowRightLeft size={12} />, color: '#059669', onClick: (sel, full) => onRunTranslate(sel || full) },
            ]}
          />
        </ErrorBoundary>
      ) : (
        <ErrorBoundary name="SuperDoc Editor" compact>
          <SuperDocEditor
            file={file}
            aiActions={[
              { label: 'Сайқаллаш', icon: <Sparkles size={12} />, color: '#8B5E3C', onClick: (sel, full) => onRunSayqallash(sel || full) },
              { label: 'Синтаксис', icon: <Wand2 size={12} />, color: '#7C3AED', onClick: (sel, full) => onRunSyntax(sel || full) },
              { label: 'Таржима', icon: <ArrowRightLeft size={12} />, color: '#059669', onClick: (sel, full) => onRunTranslate(sel || full) },
            ]}
          />
        </ErrorBoundary>
      )}
    </div>
  )
}
