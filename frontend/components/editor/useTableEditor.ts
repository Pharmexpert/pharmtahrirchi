'use client'

import React, { useState, useRef, useEffect } from 'react'
import type { RowData } from '../../types/api'
import { useAuth } from '../LoginGuard'
import api from '../../services/api'
import type { Term } from './TermHighlighter'

export interface SynonymPopupState {
  visible: boolean; x: number; y: number
  word: string; lang: 'ru' | 'uz' | 'en'; rowIdx: number
  synonyms: any[]; loading: boolean
}

export interface UseTableEditorArgs {
  initialData: RowData[]
  filename: string
  textId?: string
}

export function useTableEditor({ initialData, filename, textId = '' }: UseTableEditorArgs) {
  const { token, user } = useAuth()
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const authHeaders = { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }

  const [data, setData] = useState<RowData[]>(
    initialData.map(r => ({ ...r, display_no: r.display_no || String(r.sentence_no || '') }))
  )
  const [savingRow, setSavingRow] = useState<number | null>(null)
  const [improvingRow, setImprovingRow] = useState<{ idx: number, lang: string } | null>(null)
  const [savingAll, setSavingAll] = useState(false)
  const [isAiAligning, setIsAiAligning] = useState(false)
  const [isFinishing, setIsFinishing] = useState(false)
  const [dragIdx, setDragIdx] = useState<number | null>(null)
  const [dropIdx, setDropIdx] = useState<number | null>(null)
  const [saveStatus, setSaveStatus] = useState<string | null>(null)
  const [popup, setPopup] = useState<SynonymPopupState>({
    visible: false, x: 0, y: 0, word: '', lang: 'ru', rowIdx: -1, synonyms: [], loading: false
  })
  const [isLinguisticLoading, setIsLinguisticLoading] = useState(false)
  const [linguisticProgress, setLinguisticProgress] = useState(0)
  const [showSourceLangModal, setShowSourceLangModal] = useState<string | null>(null)
  const [linguisticPreview, setLinguisticPreview] = useState<{ category: string, results: any[], mode?: 'ai' | 'db' } | null>(null)
  const [linguisticSearchQuery, setLinguisticSearchQuery] = useState('')
  const [isBatchPolishing, setIsBatchPolishing] = useState(false)
  const [batchSummary, setBatchSummary] = useState<{ total: number, corrected: number, annotations: number } | null>(null)
  const popupRef = useRef<HTMLDivElement>(null)

  const [terms, setTerms] = useState<Term[]>([])

  useEffect(() => {
    if (!token) return
    fetch(`${API_BASE}/api/linguistic/terms-dictionary`, { headers: authHeaders })
      .then(r => r.ok ? r.json() : null)
      .then(d => {
        if (!d) return
        const allTerms: Term[] = []
        for (const a of (d.annotated || [])) {
          for (const field of ['en', 'ru', 'uz']) {
            if (a[field]) allTerms.push({ id: a.id * 100 + (field === 'en' ? 1 : field === 'ru' ? 2 : 3), type: 'annotated', match: a[field], en: a.en || '', ru: a.ru || '', uz: a.uz || '', detail_en: a.description_en, detail_ru: a.description_ru, detail_uz: a.description_uz })
          }
        }
        for (const d2 of (d.disputed || [])) {
          for (const field of ['en', 'ru', 'uz']) {
            if (d2[field]) allTerms.push({ id: d2.id * 100 + 10 + (field === 'en' ? 1 : field === 'ru' ? 2 : 3), type: 'disputed', match: d2[field], en: d2.en || '', ru: d2.ru || '', uz: d2.uz || '', detail_en: d2.context_en, detail_ru: d2.context_ru, detail_uz: d2.context_uz })
          }
        }
        for (const ab of (d.abbreviations || [])) {
          if (ab.short_form) allTerms.push({ id: ab.id * 100 + 20, type: 'abbreviation', match: ab.short_form, en: ab.long_en || '', ru: ab.long_ru || '', uz: ab.long_uz || '', detail_en: `${ab.short_form} = ${ab.long_en}` })
        }
        setTerms(allTerms)
      })
      .catch(() => {})
  }, [API_BASE, token])

  const [colWidths, setColWidths] = useState([15, 37.5, 37.5, 10])
  const resizingRef = useRef<{ idx: number; startX: number; startWidths: number[] } | null>(null)

  useEffect(() => {
    const handleMove = (e: MouseEvent) => {
      if (!resizingRef.current) return
      e.preventDefault()
      const { idx, startX, startWidths } = resizingRef.current
      const deltaX = e.clientX - startX

      const tableEl = document.getElementById('main-table')
      const tableWidth = tableEl?.clientWidth || 1000
      const deltaPercent = (deltaX / tableWidth) * 100

      const newWidths = [...startWidths]
      newWidths[idx] = Math.max(5, startWidths[idx] + deltaPercent)
      newWidths[idx+1] = Math.max(5, startWidths[idx+1] - deltaPercent)

      setColWidths(newWidths)
    }
    const handleUp = () => {
      if (resizingRef.current) {
        resizingRef.current = null
        document.body.style.cursor = ''
        document.body.style.userSelect = ''
      }
    }
    window.addEventListener('mousemove', handleMove)
    window.addEventListener('mouseup', handleUp)
    return () => {
      window.removeEventListener('mousemove', handleMove)
      window.removeEventListener('mouseup', handleUp)
    }
  }, [])

  const startResizing = (idx: number, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    resizingRef.current = { idx, startX: e.clientX, startWidths: [...colWidths] }
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
  }

  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (popupRef.current && !popupRef.current.contains(e.target as Node))
        setPopup(p => ({ ...p, visible: false }))
    }
    document.addEventListener('mousedown', h)

    if (textId) {
      fetch(`${API_BASE}/api/projects/${textId}/polishing-summary`, { headers: authHeaders })
        .then(res => res.json())
        .then(r => {
          if (r.status === 'success' && r.summary) {
            setBatchSummary(r.summary)
          }
        })
        .catch(err => console.error("Summary fetch error:", err))
    }

    return () => document.removeEventListener('mousedown', h)
  }, [textId])

  const notify = (msg: string) => {
    setSaveStatus(msg)
    setTimeout(() => setSaveStatus(null), 3500)
  }

  const update = (idx: number, field: keyof RowData, value: string) =>
    setData(prev => { const d = [...prev]; (d[idx] as any)[field] = value; return d })

  const insertRowAfter = (idx: number) => {
    const prev = data[idx]
    const base = prev.display_no || String(prev.sentence_no)
    let sub = 1
    while (data.some(r => r.display_no === base + '.' + sub)) sub++
    const newRow: RowData = {
      type: 'content', en: '', ru_v1: '', ru_proposed: '',
      uz_v1: '', uz_proposed: '', status: 'review',
      sentence_no: 0, display_no: base + '.' + sub,
      text_id: textId || prev.text_id || '', notes: ''
    }
    setData(prev => { const d = [...prev]; d.splice(idx + 1, 0, newRow); return d })
  }

  const handleDragStart = (idx: number) => { setDragIdx(idx) }
  const handleDragOver = (e: React.DragEvent, idx: number) => {
    e.preventDefault(); e.dataTransfer.dropEffect = 'move'; setDropIdx(idx)
  }
  const handleDragLeave = () => { setDropIdx(null) }
  const handleDrop = (e: React.DragEvent, toIdx: number) => {
    e.preventDefault()
    if (dragIdx === null || dragIdx === toIdx) { setDragIdx(null); setDropIdx(null); return }
    setData(prev => {
      const d = [...prev]
      const [moved] = d.splice(dragIdx, 1)
      const actualTo = toIdx > dragIdx ? toIdx - 1 : toIdx
      d.splice(actualTo, 0, moved)
      return d
    })
    setDragIdx(null); setDropIdx(null)
    notify(`Қатор #${dragIdx + 1} → #${toIdx + 1} кўчирилди`)
  }
  const handleDragEnd = () => { setDragIdx(null); setDropIdx(null) }

  const deleteRow = async (idx: number) => {
    const row = data[idx]
    if (row.sentence_no > 0) {
      try {
        await fetch(`${API_BASE}/delete-row/${encodeURIComponent(row.text_id)}/${row.sentence_no}`, {
          method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` }
        })
      } catch (_e) { /* ignore */ }
    }
    setData(prev => prev.filter((_, i) => i !== idx))
    notify('Gap #' + row.display_no + ' ochirildi')
  }

  const handleWordClick = async (e: React.MouseEvent<HTMLTextAreaElement>, rowIdx: number, lang: 'ru' | 'uz' | 'en') => {
    const t = e.currentTarget
    const s = t.selectionStart ?? 0
    const end = t.selectionEnd ?? 0
    const txt = t.value
    let sel = ''
    if (s !== end) {
      sel = txt.slice(s, end).trim()
    } else {
      let a = s, b = s
      while (a > 0 && !/\s/.test(txt[a - 1])) a--
      while (b < txt.length && !/\s/.test(txt[b])) b++
      sel = txt.slice(a, b).replace(/[.,;:!?()]/g, '').trim()
    }
    if (!sel || sel.length < 2 || sel.split(' ').length > 5) return
    const px = Math.min(e.clientX, window.innerWidth - 310)
    const py = Math.min(e.clientY + 22, window.innerHeight - 240)
    setPopup({ visible: true, x: px, y: py, word: sel, lang: lang === 'en' ? 'en' : lang, rowIdx, synonyms: [], loading: true })

    try {
      const dbRes = await fetch(`${API_BASE}/api/synonyms?word=${encodeURIComponent(sel)}&lang=${lang}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      let dbSynonyms: any[] = []
      if (dbRes.ok) {
        const dbData = await dbRes.json()
        dbSynonyms = (dbData.synonyms || [])
          .filter((s: any) => s.word.toLowerCase() === sel.toLowerCase())
          .sort((a: any, b: any) => (b.frequency || 0) - (a.frequency || 0))
          .map((s: any) => ({ word: s.synonym, frequency: s.frequency || 0, probability: Math.min(1, (s.frequency || 0) / 10) }))
      }

      if (dbSynonyms.length < 5) {
        setPopup(p => ({ ...p, synonyms: dbSynonyms, loading: dbSynonyms.length < 5 }))
        try {
          const aiRes = await fetch(`${API_BASE}/api/linguistic/synonyms`, {
            method: 'POST', headers: authHeaders,
            body: JSON.stringify({ word: sel, lang, context_en: data[rowIdx].en, source_lang: 'English' })
          })
          if (aiRes.ok) {
            const aiData = await aiRes.json()
            const aiSyns = (aiData.synonyms || []).map((s: any) => typeof s === 'string' ? { word: s, frequency: 0, probability: 0.5 } : s)
            const existing = new Set(dbSynonyms.map((s: any) => (s.word || '').toLowerCase()))
            const merged = [...dbSynonyms, ...aiSyns.filter((s: any) => !existing.has((s.word || '').toLowerCase()))]
            setPopup(p => ({ ...p, synonyms: merged, loading: false }))
          } else {
            setPopup(p => ({ ...p, loading: false }))
          }
        } catch { setPopup(p => ({ ...p, loading: false })) }
      } else {
        setPopup(p => ({ ...p, synonyms: dbSynonyms, loading: false }))
      }
    } catch (_e) { setPopup(p => ({ ...p, loading: false, synonyms: [] })) }
  }

  const batchTransliterate = async (target: 'latin' | 'cyrillic') => {
    const uzTexts = data.filter(r => r.type === 'content').map(r => r.uz_proposed || r.uz_v1)
    if (uzTexts.length === 0) return
    notify(`Матн ${target === 'latin' ? 'лотинга' : 'кириллга'} ўгирилмоқда...`)
    try {
      const res = await fetch(`${API_BASE}/api/linguistic/transliterate-batch`, {
        method: 'POST', headers: authHeaders,
        body: JSON.stringify({ texts: uzTexts, target })
      })
      if (!res.ok) throw new Error()
      const r = await res.json()
      setData(prev => {
        const d = [...prev]
        let uzIdx = 0
        return d.map(row => {
          if (row.type === 'content') {
            const val = r.results[uzIdx++]
            return { ...row, uz_proposed: val }
          }
          return row
        })
      })
      notify('Транслитерация муваффақиятли якунланди')
    } catch (_e) { notify('Хатолик юз берди') }
  }

  const applyVariant = (v: string) => {
    const { rowIdx, word, lang } = popup
    try {
      fetch(`${API_BASE}/api/synonyms/select`, {
        method: 'POST', headers: authHeaders,
        body: JSON.stringify({ word, synonym: v, lang })
      })
    } catch {}
    try {
      fetch(`${API_BASE}/api/synonyms/save`, {
        method: 'POST', headers: authHeaders,
        body: JSON.stringify({ word, synonym: v, lang })
      })
    } catch {}
    const field = lang === 'ru' ? 'ru_proposed' : lang === 'en' ? 'en' : 'uz_proposed'
    const current = (data[rowIdx] as any)[field] || ''
    update(rowIdx, field as keyof RowData, current.replace(word, v))
    setPopup(p => ({ ...p, visible: false }))
  }

  const handleBlockDrop = (fromRow: number, fromField: string, toRow: number, toField: string) => {
    setData(prev => {
      const d = [...prev]
      d[fromRow] = { ...d[fromRow] }
      d[toRow] = { ...d[toRow] }
      const fromVal = (d[fromRow] as any)[fromField] || ''
      const toVal = (d[toRow] as any)[toField] || ''
      ;(d[fromRow] as any)[fromField] = toVal
      ;(d[toRow] as any)[toField] = fromVal
      return d
    })
    notify(`Блок алмаштирилди: #${fromRow + 1} ↔ #${toRow + 1}`)
  }

  const improveRow = async (idx: number, lang: 'ru' | 'uz') => {
    setImprovingRow({ idx, lang })
    try {
      const res = await fetch(`${API_BASE}/improve-row`, {
        method: 'POST', headers: authHeaders,
        body: JSON.stringify({ ...data[idx], target_lang: lang })
      })
      if (!res.ok) throw new Error()
      const r = await res.json()
      setData(prev => {
        const d = [...prev]
        d[idx] = { ...d[idx] }
        if (lang === 'ru' && r.ru_v2) d[idx].ru_proposed = r.ru_v2.replace(/<\/?b>/g, '')
        if (lang === 'uz' && r.uz_v2) d[idx].uz_proposed = r.uz_v2.replace(/<\/?b>/g, '')
        if (r.rationale) d[idx].notes = (d[idx].notes ? d[idx].notes + '\n' : '') + r.rationale
        return d
      })
      notify(`${lang.toUpperCase()} #${data[idx].display_no} yaxshilandi`)
    } catch (_e) { notify('AI xatolik') }
    finally { setImprovingRow(null) }
  }

  const saveSingleRow = async (idx: number) => {
    setSavingRow(idx)
    try {
      const row = data[idx]

      let autoNotes = ''
      try {
        if (row.uz_v1 && row.uz_proposed && row.uz_v1.trim() !== row.uz_proposed.trim()) {
          const nRes = await fetch(`${API_BASE}/auto-notes`, {
            method: 'POST', headers: authHeaders,
            body: JSON.stringify({ v1: row.uz_v1, proposed: row.uz_proposed, lang: 'uz' })
          })
          if (nRes.ok) { const nr = await nRes.json(); if (nr.notes) autoNotes += nr.notes + '\n' }
        }
      } catch (_e) {}

      if (row.uz_proposed && row.uz_proposed !== row.uz_v1) {
        try {
          await fetch(`${API_BASE}/api/sayqallash/learn-batch`, {
            method: 'POST', headers: authHeaders,
            body: JSON.stringify({ corrections: [{ old_value: row.uz_v1, new_value: row.uz_proposed }], lang: 'uz', modified_by: user?.name || '' })
          })
        } catch (_e) {}
      }

      const res = await fetch(`${API_BASE}/api/save-row`, {
        method: 'POST', headers: authHeaders,
        body: JSON.stringify({ ...row, text_id: textId })
      })
      if (!res.ok) throw new Error()
      const r = await res.json()
      if (r.new_id && data[idx].sentence_no === 0) {
        setData(prev => { const d = [...prev]; d[idx] = { ...d[idx], sentence_no: r.new_id }; return d })
      }
      notify('Gap #' + data[idx].display_no + ' saqlandi ✓ Qoidalar yangilandi')
    } catch (_e) { notify('Saqlash xatolik') }
    finally { setSavingRow(null) }
  }

  const aiAlign = async () => {
    setIsAiAligning(true)
    notify('AI moslashtirilmoqda...')
    try {
      const res = await fetch(`${API_BASE}/align-document`, {
        method: 'POST', headers: authHeaders,
        body: JSON.stringify({ data })
      })
      if (!res.ok) throw new Error()
      const r = await res.json()
      setData(r.data)
      notify('AI moslashtirildi')
    } catch (_e) { notify('AI xatolik') }
    finally { setIsAiAligning(false) }
  }

  const handleLinguisticBtnClick = (cat: string) => setShowSourceLangModal(cat)

  const startLinguisticAnalysis = async (lang: string) => {
    const category = showSourceLangModal
    setShowSourceLangModal(null)
    if (!category) return

    try {
      fetch(`${API_BASE}/api/linguistic/project/source-lang`, {
        method: 'POST', headers: authHeaders,
        body: JSON.stringify({ text_id: textId, lang })
      })
    } catch {}

    setIsLinguisticLoading(true)
    setLinguisticProgress(0)

    const fullText = data.map(r => r.en).join('\n')

    const progressInterval = setInterval(() => {
      setLinguisticProgress(prev => (prev < 90 ? prev + Math.random() * 8 : prev))
    }, 400)

    try {
      const res = await fetch(`${API_BASE}/api/linguistic/analyze`, {
        method: 'POST', headers: authHeaders,
        body: JSON.stringify({ text: fullText, category, source_lang: lang })
      })
      if (!res.ok) throw new Error()
      const r = await res.json()
      clearInterval(progressInterval)
      setLinguisticProgress(100)
      setTimeout(() => {
        setIsLinguisticLoading(false)
        setLinguisticPreview({ category, results: r.results || [] })
      }, 500)
    } catch (_e) {
      clearInterval(progressInterval)
      setIsLinguisticLoading(false)
      notify('Таҳлил вақтида хатолик')
    }
  }

  const confirmSaveLinguisticItems = async () => {
    if (!linguisticPreview) return
    try {
      const res = await fetch(`${API_BASE}/api/linguistic/save`, {
        method: 'POST', headers: authHeaders,
        body: JSON.stringify({
          category: linguisticPreview.category,
          items: linguisticPreview.results,
          text_id: textId
        })
      })
      if (!res.ok) throw new Error()
      notify('Маълумотлар базасига сақланди')
      setLinguisticPreview(null)
    } catch (_e) { notify('Сақлашда хатолик') }
  }

  const finishWork = async () => {
    if (!confirm('Лойиҳани якунлашни тасдиқлайсизми? Бундан кейин лойиҳа архивга ўтказилади.')) return
    setIsFinishing(true)
    try {
      // Self-learning: collect all v1→proposed diffs across the document
      try {
        const corrections = data
          .filter(r => r.uz_proposed && r.uz_v1 && r.uz_proposed.trim() !== r.uz_v1.trim())
          .map(r => ({ old_value: r.uz_v1, new_value: r.uz_proposed }))
        if (corrections.length > 0) {
          await fetch(`${API_BASE}/api/sayqallash/learn-batch`, {
            method: 'POST', headers: authHeaders,
            body: JSON.stringify({ corrections, lang: 'uz', modified_by: user?.name || '' })
          })
        }
      } catch (_e) {}

      const res = await fetch(`${API_BASE}/api/projects/${encodeURIComponent(textId)}/finish`, {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({ data, specialist_name: initialData[0]?.specialist_name || '' })
      })
      if (res.ok) {
        notify('Лойиҳа муваффақиятли якунланди! ✓')
        setTimeout(() => { window.location.href = '/' }, 1500)
      } else {
        notify('Якунлашда хатолик юз берди')
      }
    } catch (_e) { notify('Сервер билан боғланишда хатолик') }
    finally { setIsFinishing(false) }
  }

  const searchLinguisticDatabase = async (category: string, query: string) => {
    setIsLinguisticLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/linguistic/all?q=${encodeURIComponent(query)}`, {
        headers: authHeaders
      })
      if (!res.ok) throw new Error()
      const r = await res.json()
      const results = r[category] || []
      setLinguisticPreview({ category, results, mode: 'db' })
    } catch (_e) {
      notify('Қидирувда хатолик')
    } finally {
      setIsLinguisticLoading(false)
    }
  }

  const runBatchSayqallash = async () => {
    const contentRows = data.filter(r => r.type === 'content')
    if (contentRows.length === 0) return

    setIsBatchPolishing(true)
    setLinguisticProgress(0)
    notify('Ҳужжат сайқалланмоқда...')

    let correctedCount = 0
    let totalAnns = 0

    const CHUNK_SIZE = 5
    const newData = [...data]

    for (let i = 0; i < contentRows.length; i += CHUNK_SIZE) {
      const chunk = contentRows.slice(i, i + CHUNK_SIZE)
      const chunkIndices = data.map((r, idx) => r.type === 'content' ? idx : -1)
                              .filter(idx => idx !== -1)
                              .slice(i, i + CHUNK_SIZE)

      try {
        const payload = chunk.map(r => ({ text: r.uz_proposed || r.uz_v1, lang: 'uz', en: r.en }))
        const res = await fetch(`${API_BASE}/api/sayqallash-batch`, {
          method: 'POST', headers: authHeaders,
          body: JSON.stringify({ rows: payload, lang: 'uz' })
        })
        if (res.ok) {
          const r = await res.json()
          r.results.forEach((res: any, j: number) => {
            const dataIdx = chunkIndices[j]
            if (res.corrected && res.corrected !== (newData[dataIdx].uz_proposed || newData[dataIdx].uz_v1)) {
              newData[dataIdx] = {
                ...newData[dataIdx],
                uz_proposed: res.corrected,
                notes: (newData[dataIdx].notes ? newData[dataIdx].notes + '\n' : '') + `AI Сайқаллаш: ${res.annotations?.length || 0} та тузатиш.`
              }
              correctedCount++
              totalAnns += res.annotations?.length || 0
            }
          })
        }
      } catch (err) {
        console.error("Batch polish chunk error:", err)
      }

      setLinguisticProgress(Math.min(100, Math.round(((i + CHUNK_SIZE) / contentRows.length) * 100)))
    }

    setData(newData)
    setIsBatchPolishing(false)
    setBatchSummary({ total: contentRows.length, corrected: correctedCount, annotations: totalAnns })
  }

  // Phase 5: Syntax check across all uz_proposed cells
  const handleSyntaxCheck = async () => {
    const newData = [...data]
    let totalErrors = 0
    let rowsWithErrors = 0
    for (let i = 0; i < newData.length; i++) {
      const r = newData[i]
      if (r.type !== 'content') continue
      const uzText = (r.uz_proposed || r.uz_v1 || '').trim()
      if (!uzText) continue
      try {
        const res: any = await api.syntax.check(uzText)
        if (res.errors && res.errors.length > 0) {
          totalErrors += res.errors.length
          rowsWithErrors++
          newData[i] = {
            ...newData[i],
            notes: (newData[i].notes ? newData[i].notes + '\n' : '') +
                   `Синтаксис: ${res.errors.length} та хато (${res.errors.map((e: any) => e.message).slice(0, 2).join('; ')})`
          }
        }
      } catch {}
    }
    setData(newData)
    return { totalErrors, rowsWithErrors }
  }

  const handleSaveAll = async () => {
    setSavingAll(true)
    try {
      const res = await fetch(`${API_BASE}/save`, {
        method: 'POST', headers: authHeaders,
        body: JSON.stringify({ data })
      })
      if (!res.ok) throw new Error()
      notify('Barchasi saqlandi')
    } catch (_e) { notify('Saqlash xatolik') }
    finally { setSavingAll(false) }
  }

  const handleExport = async () => {
    try {
      const res = await fetch(`${API_BASE}/export`, {
        method: 'POST', headers: authHeaders,
        body: JSON.stringify({ filename, data })
      })
      if (!res.ok) throw new Error()

      const contentDisposition = res.headers.get('content-disposition')
      let downloadName = 'confirmed_output.docx'
      if (contentDisposition) {
        const match = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
        if (match && match[1]) downloadName = match[1].replace(/['"]/g, '')
      } else if (filename) {
        downloadName = 'confirmed_' + filename
        if (!downloadName.endsWith('.docx')) downloadName += '.docx'
      }

      const blob = await res.blob()
      const typedBlob = new Blob([blob], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' })
      const url = window.URL.createObjectURL(typedBlob)
      const a = document.createElement('a')
      a.style.display = 'none'
      a.href = url
      a.download = downloadName
      a.setAttribute('download', downloadName)
      document.body.appendChild(a)
      a.click()
      setTimeout(() => { document.body.removeChild(a); window.URL.revokeObjectURL(url) }, 200)
      notify('DOCX yuklandi: ' + downloadName)
    } catch (_e) { notify('Export xatolik') }
  }

  const onMagicSplit = async (idx: number) => {
    setSavingRow(idx)
    notify('AI mantiqiy bo\'lish nuqtasini qidirmoqda...')
    try {
      const res = await fetch(`${API_BASE}/api/split-row`, {
        method: 'POST', headers: authHeaders,
        body: JSON.stringify({ row: data[idx] })
      })
      if (res.ok) {
        const r = await res.json()
        setData(prev => { const d = [...prev]; d.splice(idx, 1, r.row1, r.row2); return d })
        notify('AI orqali bo\'lindi ✓')
      } else {
        const row = data[idx]
        const mid = Math.floor(row.en.length / 2)
        const row1 = { ...row, en: row.en.slice(0, mid) }
        const row2 = { ...row, en: row.en.slice(mid), sentence_no: 0, display_no: row.display_no + '.1' }
        setData(prev => { const d = [...prev]; d.splice(idx, 1, row1, row2); return d })
        notify('Fallback bo\'lish')
      }
    } catch (_e) { notify('Xatolik') }
    finally { setSavingRow(null) }
  }

  return {
    // auth & config
    token, user, API_BASE, authHeaders,
    // state
    data, setData,
    savingRow, improvingRow, savingAll, isAiAligning, isFinishing,
    dragIdx, dropIdx, saveStatus, popup, setPopup,
    isLinguisticLoading, linguisticProgress,
    showSourceLangModal, setShowSourceLangModal,
    linguisticPreview, setLinguisticPreview,
    linguisticSearchQuery, setLinguisticSearchQuery,
    isBatchPolishing, batchSummary, setBatchSummary,
    terms, colWidths,
    popupRef,
    // actions
    notify, update, insertRowAfter,
    handleDragStart, handleDragOver, handleDragLeave, handleDrop, handleDragEnd,
    deleteRow, handleWordClick, batchTransliterate, applyVariant, handleBlockDrop,
    improveRow, saveSingleRow, aiAlign, handleLinguisticBtnClick, startLinguisticAnalysis,
    confirmSaveLinguisticItems, finishWork, searchLinguisticDatabase, runBatchSayqallash,
    handleSaveAll, handleExport, onMagicSplit, startResizing,
    handleSyntaxCheck,
  }
}

export type UseTableEditorReturn = ReturnType<typeof useTableEditor>
