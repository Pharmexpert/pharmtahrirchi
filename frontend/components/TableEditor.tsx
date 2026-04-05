'use client'

import React, { useState, useRef, useEffect } from 'react'
import { Download, Save, Database, Sparkles, Loader2, Plus, Trash2, BookOpen, MousePointer2, Search } from 'lucide-react'
import Link from 'next/link'
import { useAuth } from './LoginGuard'
import type { RowData } from '../types/api'
import SynonymPopup from './editor/SynonymPopup'

export type { RowData }

interface SynonymPopup {
  visible: boolean; x: number; y: number
  word: string; lang: 'ru' | 'uz' | 'en'; rowIdx: number
  synonyms: string[]; loading: boolean
}

interface Props {
  initialData: RowData[]
  filename: string
  textId?: string
}

export default function TableEditor({ initialData, filename, textId = '' }: Props) {
  const { token } = useAuth()
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
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
  const [popup, setPopup] = useState<SynonymPopup>({
    visible: false, x: 0, y: 0, word: '', lang: 'ru', rowIdx: -1, synonyms: [], loading: false
  })
  const [isLinguisticLoading, setIsLinguisticLoading] = useState(false)
  const [linguisticProgress, setLinguisticProgress] = useState(0)
  const [showSourceLangModal, setShowSourceLangModal] = useState<string | null>(null)
  const [linguisticPreview, setLinguisticPreview] = useState<{ category: string, results: any[], mode?: 'ai' | 'db' } | null>(null)
  const [linguisticSearchQuery, setLinguisticSearchQuery] = useState('')
  const [isBatchPolishing, setIsBatchPolishing] = useState(false)
  const [batchSummary, setBatchSummary] = useState<{ total: number, corrected: number, annotations: number } | null>(null)
  const [isDraggingPopup, setIsDraggingPopup] = useState(false)
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 })
  const popupRef = useRef<HTMLDivElement>(null)
  
  // Column width state (percentages)
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
    
    // NEW: Fetch polishing summary on mount to show background results
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

  // Drag & Drop rows
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
      const res = await fetch(`${API_BASE}/api/linguistic/synonyms`, {
        method: 'POST', headers: authHeaders,
        body: JSON.stringify({
          word: sel, lang,
          context_en: data[rowIdx].en,
          source_lang: (data[rowIdx] as any).source_lang || 'English'
        })
      })
      if (!res.ok) throw new Error()
      const r = await res.json()
      setPopup(p => ({ ...p, synonyms: r.synonyms || [], loading: false }))
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
    // Track frequency
    try {
      fetch(`${API_BASE}/api/synonyms/select`, {
        method: 'POST', headers: authHeaders,
        body: JSON.stringify({ word, synonym: v, lang })
      })
    } catch {}
    const field = lang === 'ru' ? 'ru_proposed' : lang === 'en' ? 'en' : 'uz_proposed'
    const current = (data[rowIdx] as any)[field] || ''
    update(rowIdx, field as keyof RowData, current.replace(word, v))
    setPopup(p => ({ ...p, visible: false }))
  }

  // Block-level drag & drop (swap V1/Proposed between rows)
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
      
      // Auto-generate diff notes before saving
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

      // Self-learning: Use learn-batch to save user correction as rule
      if (row.uz_proposed && row.uz_proposed !== row.uz_v1) {
        try {
          await fetch(`${API_BASE}/api/sayqallash/learn-batch`, {
            method: 'POST', headers: authHeaders,
            body: JSON.stringify({ corrections: [{ old_value: row.uz_v1, new_value: row.uz_proposed }], lang: 'uz' })
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

    // Save source lang choice for project
    try {
      fetch(`${API_BASE}/api/linguistic/project/source-lang`, {
        method: 'POST', headers: authHeaders,
        body: JSON.stringify({ text_id: textId, lang })
      })
    } catch {}

    setIsLinguisticLoading(true)
    setLinguisticProgress(0)
    
    // Aggregate text
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
      // Filter the relevant category from the 'all' results
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
    
    // Process in sequential chunks to avoid overloading AI/DB
    const CHUNK_SIZE = 5
    const newData = [...data]
    
    for (let i = 0; i < contentRows.length; i += CHUNK_SIZE) {
      const chunk = contentRows.slice(i, i + CHUNK_SIZE)
      // Map global indices for current chunk
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

  // Magic Split
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
        // Fallback
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

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', fontFamily: "'Inter','Segoe UI',sans-serif", background: '#f1f5f9' }}>

      <header style={{ flexShrink: 0, position: 'sticky', top: 0, zIndex: 100, background: '#1e293b', color: 'white', padding: '0 14px', height: '50px', display: 'flex', alignItems: 'center', gap: '12px', boxShadow: '0 2px 8px rgba(0,0,0,.25)' }}>
        <Database size={17} color="#60a5fa" style={{ flexShrink: 0 }} />
        <span style={{ fontWeight: 800, fontSize: '0.88rem', whiteSpace: 'nowrap', flexShrink: 0 }}>Pharma Editor</span>
        {textId && <span style={{ background: '#334155', padding: '2px 9px', borderRadius: 20, fontSize: '0.72rem', color: '#93c5fd', fontWeight: 700, flexShrink: 0 }}>ID: {textId}</span>}
        <span style={{ fontSize: '0.73rem', color: '#94a3b8', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{filename}</span>
        
        <div style={{ display: 'flex', gap: 4, background: '#334155', padding: '3px 6px', borderRadius: 8, margin: '0 8px' }}>
          <button onClick={() => handleLinguisticBtnClick('annotated')} 
            style={{ background: showSourceLangModal === 'annotated' ? '#475569' : 'none', border: 'none', color: '#cbd5e1', fontSize: '0.68rem', fontWeight: 700, cursor: 'pointer', padding: '2px 8px', borderRadius: 4, transition: 'all .2s' }} 
            onMouseEnter={e => e.currentTarget.style.color='white'} onMouseLeave={e => e.currentTarget.style.color='#cbd5e1'}>
            <BookOpen size={12} style={{verticalAlign:'middle', marginRight:3}}/> Изоҳли
          </button>
          <button onClick={() => handleLinguisticBtnClick('disputed')} 
            style={{ background: showSourceLangModal === 'disputed' ? '#475569' : 'none', border: 'none', color: '#cbd5e1', fontSize: '0.68rem', fontWeight: 700, cursor: 'pointer', padding: '2px 8px', borderRadius: 4, transition: 'all .2s' }} 
            onMouseEnter={e => e.currentTarget.style.color='white'} onMouseLeave={e => e.currentTarget.style.color='#cbd5e1'}>
            <Sparkles size={12} style={{verticalAlign:'middle', marginRight:3}}/> Мунозарали
          </button>
          <button onClick={() => handleLinguisticBtnClick('abbreviations')} 
            style={{ background: showSourceLangModal === 'abbreviations' ? '#475569' : 'none', border: 'none', color: '#cbd5e1', fontSize: '0.68rem', fontWeight: 700, cursor: 'pointer', padding: '2px 8px', borderRadius: 4, transition: 'all .2s' }} 
            onMouseEnter={e => e.currentTarget.style.color='white'} onMouseLeave={e => e.currentTarget.style.color='#cbd5e1'}>
            <Database size={12} style={{verticalAlign:'middle', marginRight:3}}/> Қисқартмалар
          </button>
        </div>

        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <button onClick={() => batchTransliterate('latin')} title="Lotinga o'girish"
            style={{ background: '#334155', border: 'none', color: '#94a3b8', fontSize: '0.65rem', fontWeight: 700, padding: '3px 8px', borderRadius: 4, cursor: 'pointer' }} onMouseEnter={e => e.currentTarget.style.color='white'} onMouseLeave={e => e.currentTarget.style.color='#94a3b8'}>
            A→Z
          </button>
          <button onClick={() => batchTransliterate('cyrillic')} title="Kirillga o'girish"
            style={{ background: '#334155', border: 'none', color: '#94a3b8', fontSize: '0.65rem', fontWeight: 700, padding: '3px 8px', borderRadius: 4, cursor: 'pointer' }} onMouseEnter={e => e.currentTarget.style.color='white'} onMouseLeave={e => e.currentTarget.style.color='#94a3b8'}>
            А→Я
          </button>
        </div>

        {saveStatus && <span style={{ background: '#22c55e', color: 'white', padding: '2px 10px', borderRadius: 20, fontSize: '0.72rem', fontWeight: 700, whiteSpace: 'nowrap', flexShrink: 0 }}>{saveStatus}</span>}
        <div style={{ display: 'flex', gap: 6, flexShrink: 0, alignItems: 'center' }}>
          <Link href="/rules" style={{ display: 'flex', alignItems: 'center', gap: '4px', background: '#334155', color: '#94a3b8', padding: '5px 10px', borderRadius: 6, fontSize: '0.75rem', fontWeight: 700, textDecoration: 'none', transition: 'all 0.2s' }}
                onMouseEnter={e => (e.currentTarget.style.color = 'white', e.currentTarget.style.background = '#475569')}
                onMouseLeave={e => (e.currentTarget.style.color = '#94a3b8', e.currentTarget.style.background = '#334155')}>
            <BookOpen size={14} />
            Rules DB
          </Link>
          <button onClick={runBatchSayqallash} disabled={isBatchPolishing} style={{ padding: '5px 10px', background: isBatchPolishing ? '#4b5563' : 'linear-gradient(135deg,#059669,#10b981)', color: 'white', border: 'none', borderRadius: 6, fontWeight: 700, fontSize: '0.75rem', cursor: isBatchPolishing ? 'not-allowed' : 'pointer', whiteSpace: 'nowrap' }}>
            {isBatchPolishing ? 'Сайқалланмоқда...' : '✦ Сайқаллаш (Barchasi)'}
          </button>
          <button onClick={aiAlign} disabled={isAiAligning} style={{ padding: '5px 10px', background: isAiAligning ? '#4b5563' : 'linear-gradient(135deg,#6366f1,#8b5cf6)', color: 'white', border: 'none', borderRadius: 6, fontWeight: 700, fontSize: '0.75rem', cursor: isAiAligning ? 'not-allowed' : 'pointer', whiteSpace: 'nowrap' }}>
            {isAiAligning ? 'Moslashtirilmoqda...' : 'AI Moslash'}
          </button>
          <button onClick={handleSaveAll} disabled={savingAll} style={{ padding: '5px 10px', background: '#3b82f6', color: 'white', border: 'none', borderRadius: 6, fontWeight: 700, fontSize: '0.75rem', cursor: 'pointer', whiteSpace: 'nowrap' }}>
            {savingAll ? 'Saqlanmoqda...' : 'Saqlash'}
          </button>
          <button onClick={finishWork} disabled={isFinishing} style={{ padding: '5px 10px', background: 'linear-gradient(135deg, #f59e0b, #d97706)', color: 'white', border: 'none', borderRadius: 6, fontWeight: 800, fontSize: '0.75rem', cursor: 'pointer', whiteSpace: 'nowrap', boxShadow: '0 2px 4px rgba(217,119,6,0.3)' }}>
            {isFinishing ? 'Якунланмоқда...' : 'Ишни якунлаш ✓'}
          </button>
          <button onClick={handleExport} style={{ padding: '5px 10px', background: '#10b981', color: 'white', border: 'none', borderRadius: 6, fontWeight: 700, fontSize: '0.75rem', cursor: 'pointer', whiteSpace: 'nowrap' }}>
            Export DOCX
          </button>
        </div>
      </header>

      {/* Progress Modal (Batch Polishing / AI Analysis) */}
      {(isLinguisticLoading || isBatchPolishing) && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(15, 23, 42, 0.7)', backdropFilter: 'blur(4px)', zIndex: 10000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ background: 'white', padding: '30px', borderRadius: 20, width: '400px', textAlign: 'center', boxShadow: '0 20px 50px rgba(0,0,0,0.3)' }}>
            <h3 style={{ margin: '0 0 15px 0', fontSize: '1.1rem', color: '#1e293b' }}>
              {isBatchPolishing ? 'Ҳужжат сайқалланмоқда...' : 'AI Таҳлил қилинмоқда...'}
            </h3>
            <div style={{ height: '10px', background: '#e2e8f0', borderRadius: 10, overflow: 'hidden', marginBottom: '10px', position: 'relative' }}>
              <div style={{ height: '100%', width: `${linguisticProgress}%`, background: 'linear-gradient(90deg, #059669, #10b981)', transition: 'width 0.3s ease' }} />
            </div>
            <span style={{ fontSize: '0.9rem', fontWeight: 800, color: '#059669' }}>{Math.round(linguisticProgress)}%</span>
            <p style={{ margin: '15px 0 0 0', fontSize: '0.75rem', color: '#64748b' }}>
              {isBatchPolishing ? 'Барча қаторлар автоматик тузатилмоқда' : 'Бутун ҳужжат бўйича қидирилмоқда'}
            </p>
          </div>
        </div>
      )}

      {/* Batch Summary Modal */}
      {batchSummary && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(15, 23, 42, 0.7)', backdropFilter: 'blur(4px)', zIndex: 10000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ background: 'white', padding: '30px', borderRadius: 20, width: '450px', textAlign: 'center', boxShadow: '0 25px 60px rgba(0,0,0,0.4)' }}>
            <div style={{ background: '#dcfce7', width: '60px', height: '60px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px' }}>
              <Sparkles size={30} color="#16a34a" />
            </div>
            <h3 style={{ margin: '0 0 10px 0', fontSize: '1.3rem', color: '#1e293b' }}>Сайқаллаш якунланди!</h3>
            <p style={{ color: '#64748b', fontSize: '0.9rem', marginBottom: '25px' }}>Ҳужжат тўлиқ таҳлил қилинди ва тузатишлар киритилди.</p>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px', marginBottom: '30px' }}>
              <div style={{ background: '#f8fafc', padding: '15px', borderRadius: 12 }}>
                <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#1e293b' }}>{batchSummary.total}</div>
                <div style={{ fontSize: '0.65rem', color: '#64748b', textTransform: 'uppercase' }}>Қаторлар</div>
              </div>
              <div style={{ background: '#f0fdf4', padding: '15px', borderRadius: 12, border: '1px solid #dcfce7' }}>
                <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#16a34a' }}>{batchSummary.corrected}</div>
                <div style={{ fontSize: '0.65rem', color: '#16a34a', textTransform: 'uppercase' }}>Тузатилди</div>
              </div>
              <div style={{ background: '#f5f3ff', padding: '15px', borderRadius: 12, border: '1px solid #ddd6fe' }}>
                <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#7c3aed' }}>{batchSummary.annotations}</div>
                <div style={{ fontSize: '0.65rem', color: '#7c3aed', textTransform: 'uppercase' }}>Хатолар</div>
              </div>
            </div>
            
            <button onClick={() => setBatchSummary(null)} style={{ width: '100%', padding: '12px', background: '#1e293b', color: 'white', border: 'none', borderRadius: 10, fontWeight: 700, cursor: 'pointer' }}>
              Натижаларни кўриш
            </button>
          </div>
        </div>
      )}

      {/* Source Language Selection Modal */}
      {showSourceLangModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(15, 23, 42, 0.6)', zIndex: 10000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ background: 'white', padding: '25px', borderRadius: 15, width: '400px', boxShadow: '0 10px 40px rgba(0,0,0,0.2)' }}>
            <h3 style={{ margin: '0 0 10px 0', fontSize: '1.1rem', color: '#1e293b', textAlign: 'center' }}>Лингвистик режим</h3>
            <p style={{ fontSize: '0.8rem', color: '#64748b', textAlign: 'center', marginBottom: '20px' }}>
              Танланган категория: <span style={{ fontWeight: 800, color: '#6366f1' }}>{showSourceLangModal === 'annotated' ? 'Изоҳли луғат' : showSourceLangModal === 'disputed' ? 'Мунозарали' : 'Қисқартмалар'}</span>
            </p>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ border: '1.5px solid #6366f1', borderRadius: 12, padding: '12px', background: '#f5f3ff', marginBottom: 10 }}>
                <span style={{ fontSize: '0.7rem', fontWeight: 800, color: '#6366f1', textTransform: 'uppercase', display: 'block', marginBottom: 8 }}>Базадан қидириш (4,365+ та)</span>
                <div style={{ display: 'flex', gap: 6 }}>
                  <input 
                    type="text" 
                    placeholder="Калит сўзни ёзинг..." 
                    value={linguisticSearchQuery}
                    onChange={e => setLinguisticSearchQuery(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && searchLinguisticDatabase(showSourceLangModal, linguisticSearchQuery)}
                    style={{ flex: 1, padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd', fontSize: '0.85rem', outline: 'none' }}
                  />
                  <button onClick={() => searchLinguisticDatabase(showSourceLangModal, linguisticSearchQuery)} style={{ padding: '8px 15px', background: '#6366f1', color: 'white', border: 'none', borderRadius: 8, fontWeight: 700, cursor: 'pointer' }}>
                    <Search size={16} />
                  </button>
                </div>
              </div>

              <div style={{ border: '1px solid #e2e8f0', borderRadius: 12, padding: '12px', background: '#f8fafc' }}>
                <span style={{ fontSize: '0.7rem', fontWeight: 800, color: '#64748b', textTransform: 'uppercase', display: 'block', marginBottom: 8 }}>АИ Таҳлил (Янгиларни топиш)</span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <button onClick={() => startLinguisticAnalysis('English')} style={{ padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: 8, background: 'white', fontWeight: 700, cursor: 'pointer', textAlign: 'left', display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                    <span>English (Original) бўйича таҳлил</span>
                    <span style={{ color: '#6366f1' }}>🤖</span>
                  </button>
                  <button onClick={() => startLinguisticAnalysis('Russian')} style={{ padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: 8, background: 'white', fontWeight: 700, cursor: 'pointer', textAlign: 'left', display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                    <span>Русча бўйича таҳлил</span>
                    <span style={{ color: '#6366f1' }}>🤖</span>
                  </button>
                </div>
              </div>

              <button onClick={() => setShowSourceLangModal(null)} style={{ marginTop: '5px', padding: '10px', background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: '0.8rem' }}>Бекор қилиш</button>
            </div>
          </div>
        </div>
      )}

      {/* Preview Modal */}
      {linguisticPreview && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(15, 23, 42, 0.8)', zIndex: 10000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ background: 'white', padding: '0', borderRadius: 15, width: '90%', maxWidth: '900px', maxHeight: '85vh', overflow: 'hidden', display: 'flex', flexDirection: 'column', boxShadow: '0 25px 60px rgba(0,0,0,0.4)' }}>
            <div style={{ padding: '15px 20px', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#f8fafc' }}>
              <h3 style={{ margin: 0, fontSize: '1rem', color: '#1e293b' }}>
                {linguisticPreview.mode === 'db' ? 'Базадан топилган натижалар' : 'AI Таҳлил натижалари'}: <span style={{ textTransform: 'capitalize', color: '#6366f1' }}>{linguisticPreview.category === 'annotated' ? 'Изоҳли' : linguisticPreview.category === 'disputed' ? 'Мунозарали' : 'Қисқартмалар'}</span>
              </h3>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                {linguisticPreview.mode === 'db' && (
                  <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Жами: <b>{linguisticPreview.results.length}</b> та</span>
                )}
                <button onClick={() => setLinguisticPreview(null)} style={{ background: 'none', border: 'none', fontSize: '1.2rem', cursor: 'pointer', color: '#94a3b8' }}>✕</button>
              </div>
            </div>
            <div style={{ flex: 1, overflow: 'auto', padding: '20px' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                <thead>
                  <tr style={{ textAlign: 'left', borderBottom: '2px solid #e2e8f0' }}>
                    <th style={{ padding: '10px' }}>EN</th>
                    <th style={{ padding: '10px' }}>RU</th>
                    <th style={{ padding: '10px' }}>UZ</th>
                    <th style={{ padding: '10px' }}>Изоҳ / Контекст</th>
                    <th style={{ padding: '10px', width: '80px' }}>Ҳолат</th>
                  </tr>
                </thead>
                <tbody>
                  {linguisticPreview.results.map((item, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid #f1f5f9', background: item.is_duplicate ? '#fffbeb' : 'white' }}>
                      <td style={{ padding: '10px', fontWeight: 600 }}>{item.en || item.short_form}</td>
                      <td style={{ padding: '10px' }}>{item.ru || item.long_ru}</td>
                      <td style={{ padding: '10px' }}>{item.uz || item.long_uz}</td>
                      <td style={{ padding: '10px', fontSize: '0.75rem', color: '#64748b' }}>
                        {item.description_en || item.context_en || item.long_en}
                      </td>
                      <td style={{ padding: '10px' }}>
                        {item.is_duplicate 
                          ? <span style={{ color: '#d97706', fontSize: '0.65rem', fontWeight: 700, background: '#fef3c7', padding: '2px 5px', borderRadius: 4 }}>бор</span>
                          : <span style={{ color: '#16a34a', fontSize: '0.65rem', fontWeight: 700, background: '#dcfce7', padding: '2px 5px', borderRadius: 4 }}>янги</span>
                        }
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div style={{ padding: '15px 20px', borderTop: '1px solid #e2e8f0', textAlign: 'right', background: '#f8fafc' }}>
              <button onClick={() => setLinguisticPreview(null)} style={{ padding: '8px 15px', marginRight: '10px', borderRadius: 8, border: '1px solid #e2e8f0', background: 'white', cursor: 'pointer' }}>Ёпиш</button>
              {linguisticPreview.mode !== 'db' && (
                <button onClick={confirmSaveLinguisticItems} style={{ padding: '8px 25px', borderRadius: 8, border: 'none', background: '#6366f1', color: 'white', fontWeight: 700, cursor: 'pointer' }}>БАРЧАСИНИ САҚЛАШ</button>
              )}
            </div>
          </div>
        </div>
      )}

      <div style={{ flex: 1, overflow: 'hidden', display: 'flex' }}>
        <div style={{ flex: 1, overflow: 'auto' }}>
          <table id="main-table" style={{ minWidth: 920, width: '100%', borderCollapse: 'collapse', tableLayout: 'fixed', display: 'table' }}>
          <colgroup>
            <col style={{ width: 32 }} />
            <col style={{ width: `${colWidths[0]}%` }} />
            <col style={{ width: `${colWidths[1]}%` }} />
            <col style={{ width: `${colWidths[2]}%` }} />
            <col style={{ width: `${colWidths[3]}%` }} />
          </colgroup>
          <thead style={{ position: 'sticky', top: 0, zIndex: 5 }}>
            <tr>
              <th style={{ padding: '5px 7px', fontSize: '0.62rem', background: '#f1f5f9', borderBottom: '2px solid #e2e8f0', width: 32 }}>#</th>
              
              <th style={{ position: 'relative', textAlign: 'left', padding: '5px 7px', fontSize: '0.62rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: '#64748b', fontWeight: 700, background: '#f1f5f9', borderBottom: '2px solid #e2e8f0', overflow: 'visible' }}>
                English (Original)
                <div onMouseDown={e => startResizing(0, e)} 
                  style={{ position: 'absolute', right: -6, top: 0, bottom: 0, width: 12, cursor: 'col-resize', zIndex: 20, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <div style={{ width: 2, height: '60%', background: '#cbd5e1', borderRadius: 2, transition: 'background .15s' }} 
                    onMouseEnter={e => (e.currentTarget.style.background = '#3b82f6', e.currentTarget.style.width = '3px')}
                    onMouseLeave={e => (e.currentTarget.style.background = '#cbd5e1', e.currentTarget.style.width = '2px')} />
                </div>
              </th>
              
              <th style={{ position: 'relative', textAlign: 'left', padding: '5px 7px', fontSize: '0.62rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: '#64748b', fontWeight: 700, background: '#f1f5f9', borderBottom: '2px solid #e2e8f0', overflow: 'visible' }}>
                Russian
                <div onMouseDown={e => startResizing(1, e)} 
                  style={{ position: 'absolute', right: -6, top: 0, bottom: 0, width: 12, cursor: 'col-resize', zIndex: 20, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <div style={{ width: 2, height: '60%', background: '#cbd5e1', borderRadius: 2, transition: 'background .15s' }} 
                    onMouseEnter={e => (e.currentTarget.style.background = '#3b82f6', e.currentTarget.style.width = '3px')}
                    onMouseLeave={e => (e.currentTarget.style.background = '#cbd5e1', e.currentTarget.style.width = '2px')} />
                </div>
              </th>
              
              <th style={{ position: 'relative', textAlign: 'left', padding: '5px 7px', fontSize: '0.62rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: '#64748b', fontWeight: 700, background: '#f1f5f9', borderBottom: '2px solid #e2e8f0', overflow: 'visible' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  Uzbek
                  <button onClick={async () => {
                    const texts = data.map(r => r.uz_proposed || r.uz_v1)
                    const res = await fetch(`${API_BASE}/api/transliterate-batch`, {
                      method: 'POST', headers: authHeaders, 
                      body: JSON.stringify({ texts, target: 'latin' })
                    })
                    const r = await res.json()
                    const newData = [...data]
                    r.texts.forEach((txt: string, i: number) => {
                      if (newData[i].uz_proposed) newData[i].uz_proposed = txt
                      else newData[i].uz_v1 = txt
                    })
                    setData(newData)
                  }} style={{ background: '#334155', border: 'none', color: '#93c5fd', fontSize: '0.55rem', padding: '2px 5px', borderRadius: 4, cursor: 'pointer', fontWeight: 800 }}>К→Л</button>
                </div>
                <div onMouseDown={e => startResizing(2, e)} 
                  style={{ position: 'absolute', right: -6, top: 0, bottom: 0, width: 12, cursor: 'col-resize', zIndex: 20, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <div style={{ width: 2, height: '60%', background: '#cbd5e1', borderRadius: 2, transition: 'background .15s' }} 
                    onMouseEnter={e => (e.currentTarget.style.background = '#3b82f6', e.currentTarget.style.width = '3px')}
                    onMouseLeave={e => (e.currentTarget.style.background = '#cbd5e1', e.currentTarget.style.width = '2px')} />
                </div>
              </th>
              
              <th style={{ textAlign: 'left', padding: '5px 7px', fontSize: '0.62rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: '#64748b', fontWeight: 700, background: '#f1f5f9', borderBottom: '2px solid #e2e8f0' }}>Izoh</th>
            </tr>
          </thead>
          <tbody>
            {data.map((row, idx) => (
              <React.Fragment key={idx}>
                {dropIdx === idx && dragIdx !== null && dragIdx !== idx && (
                  <tr><td colSpan={5} style={{ padding: 0, height: 3, background: '#3b82f6' }} /></tr>
                )}
                <tr 
                  style={{ 
                    background: row.type === 'marker' ? '#dbeafe' : dragIdx === idx ? '#fef9c3' : 'white', 
                    borderBottom: '1px solid #e9edf2',
                    opacity: dragIdx === idx ? 0.5 : 1,
                    transition: 'opacity .15s'
                  }}
                  onDragOver={e => handleDragOver(e, idx)}
                  onDragLeave={handleDragLeave}
                  onDrop={e => handleDrop(e, idx)}
                >
                  <td 
                    draggable 
                    onDragStart={() => handleDragStart(idx)}
                    onDragEnd={handleDragEnd}
                    style={{ padding: '4px 2px', verticalAlign: 'top', borderRight: '1px solid #e9edf2', textAlign: 'center', width: 32, cursor: 'grab' }}
                    title="Ушлаб суринг"
                  >
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
                      <span style={{ fontSize: '0.65rem', fontWeight: 700, color: '#94a3b8', lineHeight: 1 }}>{row.display_no || row.sentence_no}</span>
                      {row.type === 'content' && (
                        <>
                          <button onClick={() => saveSingleRow(idx)} disabled={savingRow === idx} title="Saqlash"
                            style={{ background: 'none', border: '1px solid #ddd', borderRadius: 3, padding: '2px 3px', cursor: 'pointer', color: '#64748b', display: 'flex', lineHeight: 1 }}>
                            {savingRow === idx ? <Loader2 size={10} style={{ animation: 'spin .8s linear infinite' }} /> : <Save size={10} />}
                          </button>
                          <button onClick={() => onMagicSplit(idx)} title="AI Bo'lish"
                            style={{ background: 'none', border: '1px solid #ddd', borderRadius: 3, padding: '2px 3px', cursor: 'pointer', color: '#6366f1', display: 'flex', lineHeight: 1 }}>
                            <Sparkles size={10} />
                          </button>
                          <button onClick={() => deleteRow(idx)} title="O'chirish"
                            style={{ background: 'none', border: '1px solid #ddd', borderRadius: 3, padding: '2px 3px', cursor: 'pointer', color: '#94a3b8', display: 'flex', lineHeight: 1 }}>
                            <Trash2 size={10} />
                          </button>
                        </>
                      )}
                    </div>
                  </td>

                  <td style={{ padding: '3px 6px', verticalAlign: 'top', borderRight: '1px solid #e9edf2', fontSize: '0.65rem', color: '#64748b', lineHeight: 1.25, fontWeight: row.type === 'marker' ? 800 : 400, cursor: row.type === 'content' ? 'text' : 'default' }}
                    onClick={row.type === 'content' ? (e) => {
                      const sel = window.getSelection()?.toString().trim()
                      const word = sel && sel.length >= 2 ? sel.replace(/[.,;:!?()]/g, '').trim() : ''
                      if (word && word.split(' ').length <= 5) {
                        const px = Math.min(e.clientX, window.innerWidth - 310)
                        const py = Math.min(e.clientY + 22, window.innerHeight - 240)
                        setPopup({ visible: true, x: px, y: py, word, lang: 'en', rowIdx: idx, synonyms: [], loading: true })
                        fetch(`${API_BASE}/api/linguistic/synonyms`, {
                          method: 'POST', headers: authHeaders,
                          body: JSON.stringify({ word, lang: 'en', context_en: row.en, source_lang: 'English' })
                        }).then(r => r.json()).then(r => setPopup(p => ({ ...p, synonyms: r.synonyms || [], loading: false }))).catch(() => setPopup(p => ({ ...p, loading: false })))
                      }
                    } : undefined}
                  >
                    <RichContent text={row.en} />
                  </td>

                  <LangCell v1={row.ru_v1} proposed={row.ru_proposed} rowIdx={idx} lang="ru"
                    isMarker={row.type === 'marker'} isImproving={improvingRow?.idx === idx && improvingRow?.lang === 'ru'}
                    onV1Change={v => update(idx, 'ru_v1', v)}
                    onProposedChange={v => update(idx, 'ru_proposed', v)}
                    onImprove={() => improveRow(idx, 'ru')} onWordClick={handleWordClick}
                    onBlockDrop={handleBlockDrop} token={token || undefined}
                    contextEn={row.en} contextRu={row.ru_proposed || row.ru_v1} contextUz={row.uz_proposed || row.uz_v1} />

                  <LangCell v1={row.uz_v1} proposed={row.uz_proposed} rowIdx={idx} lang="uz"
                    isMarker={row.type === 'marker'} isImproving={improvingRow?.idx === idx && improvingRow?.lang === 'uz'}
                    onV1Change={v => update(idx, 'uz_v1', v)}
                    onProposedChange={v => update(idx, 'uz_proposed', v)}
                    onImprove={() => improveRow(idx, 'uz')} onWordClick={handleWordClick}
                    onBlockDrop={handleBlockDrop} token={token || undefined}
                    contextEn={row.en} contextRu={row.ru_proposed || row.ru_v1} contextUz={row.uz_proposed || row.uz_v1} />

                  <td style={{ padding: '7px 7px', verticalAlign: 'top', borderLeft: '1px solid #e9edf2' }}>
                    <textarea value={row.notes || ''} onChange={e => update(idx, 'notes', e.target.value)}
                      placeholder="Izoh..."
                      style={{ width: '100%', minHeight: 80, fontSize: '0.72rem', border: '1px solid #e8e5d5', borderRadius: 4, padding: '5px 6px', background: '#fffef5', resize: 'vertical', outline: 'none', fontFamily: 'inherit', lineHeight: 1.4, boxSizing: 'border-box' }} />
                  </td>
                </tr>

                {row.type === 'content' && (
                  <tr>
                    <td colSpan={5} style={{ padding: '0 0 0 28px', height: 14 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 4, opacity: 0, transition: 'opacity .15s' }}
                        onMouseEnter={e => { (e.currentTarget as HTMLElement).style.opacity = '1' }}
                        onMouseLeave={e => { (e.currentTarget as HTMLElement).style.opacity = '0' }}>
                        <button onClick={() => insertRowAfter(idx)}
                          style={{ display: 'flex', alignItems: 'center', gap: 3, padding: '1px 7px', background: '#eff6ff', color: '#3b82f6', border: '1px dashed #93c5fd', borderRadius: 4, fontSize: '0.65rem', fontWeight: 700, cursor: 'pointer' }}>
                          <Plus size={10} /> + band
                        </button>
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>

        {/* Synonym Sidebar */}
        <SynonymPopup popup={popup} onApplyVariant={applyVariant} />
      </div>

      <style jsx global>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        * { box-sizing: border-box; }
        body { margin: 0; }
        ::-webkit-scrollbar { width: 7px; height: 7px; }
        ::-webkit-scrollbar-track { background: #f1f5f9; }
        ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #94a3b8; }
      `}</style>
    </div>
  )
}

function LangCell({ v1, proposed, rowIdx, lang, isMarker, isImproving, onV1Change, onProposedChange, onImprove, onWordClick, onBlockDrop, token, contextEn, contextRu, contextUz }: {
  v1: string; proposed: string; rowIdx: number; lang: 'ru' | 'uz'; isMarker: boolean
  isImproving: boolean
  onV1Change: (v: string) => void
  onProposedChange: (v: string) => void
  onImprove: () => void
  onWordClick: (e: React.MouseEvent<HTMLTextAreaElement>, idx: number, lang: 'ru' | 'uz') => void
  onBlockDrop?: (fromRow: number, fromField: string, toRow: number, toField: string) => void
  token?: string
  contextEn?: string; contextRu?: string; contextUz?: string
}) {
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const [dragOverField, setDragOverField] = useState<string | null>(null)
  const [annotations, setAnnotations] = useState<any[]>([])
  const [isSayqallash, setIsSayqallash] = useState(false)
  const [showAnnotations, setShowAnnotations] = useState(false)
  const [rulesCount, setRulesCount] = useState(0)

  const handleBlockDragStart = (e: React.DragEvent, field: string) => {
    e.dataTransfer.setData('text/plain', JSON.stringify({ rowIdx, lang, field }))
    e.dataTransfer.effectAllowed = 'move'
  }

  const handleBlockDragOver = (e: React.DragEvent, field: string) => {
    e.preventDefault(); e.dataTransfer.dropEffect = 'move'; setDragOverField(field)
  }
  const handleBlockDragLeave = () => setDragOverField(null)

  const handleBlockDropLocal = (e: React.DragEvent, toField: string) => {
    e.preventDefault()
    setDragOverField(null)
    try {
      const from = JSON.parse(e.dataTransfer.getData('text/plain'))
      if (onBlockDrop && (from.rowIdx !== rowIdx || from.field !== toField)) {
        onBlockDrop(from.rowIdx, `${from.lang}_${from.field}`, rowIdx, `${lang}_${toField}`)
      }
    } catch (_e) {}
  }

  const runSayqallash = async () => {
    const text = proposed || v1 || ''
    if (!text.trim()) return
    setIsSayqallash(true)
    try {
      const res = await fetch(`${API_BASE}/sayqallash`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ text, lang, context_en: contextEn || '', context_ru: contextRu || '', context_uz: contextUz || '' })
      })
      if (!res.ok) throw new Error()
      const r = await res.json()
      setAnnotations(r.annotations || [])
      setShowAnnotations(true)
      setRulesCount(r.rules_count || 0)
    } catch (_e) { setAnnotations([]) }
    finally { setIsSayqallash(false) }
  }

  const acceptAnnotation = (idx: number) => {
    const ann = annotations[idx]
    const text = proposed || v1 || ''
    const newText = text.substring(0, ann.from_index) + ann.new_value + text.substring(ann.to_index)
    onProposedChange(newText)
    const diff = ann.new_value.length - ann.old_value.length
    const remaining = annotations.filter((_, i) => i !== idx).map(a => {
      if (a.from_index > ann.from_index) {
        return { ...a, from_index: a.from_index + diff, to_index: a.to_index + diff }
      }
      return a
    })
    setAnnotations(remaining)
    if (remaining.length === 0) setShowAnnotations(false)
  }

  const rejectAnnotation = (idx: number) => {
    const remaining = annotations.filter((_, i) => i !== idx)
    setAnnotations(remaining)
    if (remaining.length === 0) setShowAnnotations(false)
  }

  const acceptAll = () => {
    let text = proposed || v1 || ''
    const sorted = [...annotations].sort((a, b) => b.from_index - a.from_index)
    for (const ann of sorted) {
      text = text.substring(0, ann.from_index) + ann.new_value + text.substring(ann.to_index)
    }
    onProposedChange(text)
    setAnnotations([])
    setShowAnnotations(false)
  }

  const dragHandleStyle: React.CSSProperties = {
    cursor: 'grab', fontSize: '0.7rem', color: '#cbd5e1', userSelect: 'none',
    padding: '0 3px', lineHeight: 1, flexShrink: 0
  }

  // Build annotated text display
  const renderAnnotatedText = () => {
    const text = proposed || v1 || ''
    if (!annotations.length) return null
    
    const parts: React.ReactNode[] = []
    let lastIdx = 0
    const sorted = [...annotations].sort((a, b) => a.from_index - b.from_index)
    
    sorted.forEach((ann, i) => {
      if (ann.from_index > lastIdx) {
        parts.push(<span key={`t${i}`} style={{ fontSize: '0.78rem', lineHeight: 1.5 }}>{text.slice(lastIdx, ann.from_index)}</span>)
      }
      parts.push(
        <span key={`a${i}`} style={{ display: 'inline', position: 'relative' }}>
          <span style={{ 
            color: '#ef4444', textDecoration: 'line-through', fontSize: '0.78rem',
            background: '#fef2f2', padding: '0 2px', borderRadius: 2
          }}>{ann.old_value}</span>
          <span style={{ 
            color: '#16a34a', fontWeight: 700, fontSize: '0.78rem',
            background: '#f0fdf4', padding: '0 2px', borderRadius: 2
          }}>{ann.new_value}</span>
          <span style={{ display: 'inline-flex', gap: 1, marginLeft: 2, verticalAlign: 'middle' }}>
            <button onClick={() => acceptAnnotation(i)} title="Қабул қилиш"
              style={{ background: '#dcfce7', border: '1px solid #86efac', borderRadius: 3, padding: '0 3px', cursor: 'pointer', fontSize: '0.6rem', color: '#16a34a', lineHeight: '14px' }}>✓</button>
            <button onClick={() => rejectAnnotation(i)} title="Рад этиш"
              style={{ background: '#fef2f2', border: '1px solid #fca5a5', borderRadius: 3, padding: '0 3px', cursor: 'pointer', fontSize: '0.6rem', color: '#ef4444', lineHeight: '14px' }}>✕</button>
          </span>
          <span style={{ fontSize: '0.5rem', color: '#8b5cf6', background: '#f5f3ff', padding: '0 3px', borderRadius: 8, marginLeft: 2, fontWeight: 600, verticalAlign: 'middle' }}>{ann.error_type}</span>
          {ann.source === 'rules_db' && <span style={{ fontSize: '0.5rem', color: '#0891b2', background: '#ecfeff', padding: '0 3px', borderRadius: 8, marginLeft: 1, verticalAlign: 'middle' }}>📚 DB</span>}
          {ann.source === 'ai' && <span style={{ fontSize: '0.5rem', color: '#7c3aed', background: '#f5f3ff', padding: '0 3px', borderRadius: 8, marginLeft: 1, verticalAlign: 'middle' }}>🤖 AI</span>}
        </span>
      )
      lastIdx = ann.to_index
    })
    if (lastIdx < text.length) {
      parts.push(<span key="end" style={{ fontSize: '0.78rem', lineHeight: 1.5 }}>{text.slice(lastIdx)}</span>)
    }
    return parts
  }

  return (
    <td style={{ padding: '7px 8px', verticalAlign: 'top', borderRight: '1px solid #e9edf2' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {/* V1: Original Block */}
        <div 
          draggable
          onDragStart={e => handleBlockDragStart(e, 'v1')}
          onDragOver={e => handleBlockDragOver(e, 'v1')}
          onDragLeave={handleBlockDragLeave}
          onDrop={e => handleBlockDropLocal(e, 'v1')}
          style={{ 
            border: dragOverField === 'v1' ? '2px dashed #3b82f6' : '1px solid #e9edf2',
            borderRadius: 5, padding: 4, background: dragOverField === 'v1' ? '#eff6ff' : '#f8fafc',
            transition: 'border .15s, background .15s'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 3 }}>
            <span draggable onDragStart={e => handleBlockDragStart(e, 'v1')} style={dragHandleStyle} title="Ушлаб суринг">⠿</span>
            <span style={{ fontSize: '0.55rem', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              V1: Original
            </span>
          </div>
          <textarea value={v1 || ''} onChange={e => onV1Change(e.target.value)}
            onClick={e => onWordClick(e as any, rowIdx, lang)}
            placeholder="V1 original..."
            style={{ width: '100%', minHeight: 40, fontSize: '0.78rem', color: '#475569', background: 'transparent', border: 'none', padding: '2px 4px', lineHeight: 1.45, resize: 'vertical', outline: 'none', fontFamily: 'inherit', boxSizing: 'border-box' }}
          />
        </div>

        {/* Proposed / Confirmed Block */}
        <div 
          draggable
          onDragStart={e => handleBlockDragStart(e, 'proposed')}
          onDragOver={e => handleBlockDragOver(e, 'proposed')}
          onDragLeave={handleBlockDragLeave}
          onDrop={e => handleBlockDropLocal(e, 'proposed')}
          style={{ 
            border: dragOverField === 'proposed' ? '2px dashed #22c55e' : '1.5px solid #bfdbfe',
            borderRadius: 5, padding: 4, background: dragOverField === 'proposed' ? '#f0fdf4' : 'white',
            transition: 'border .15s, background .15s'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 3, flexWrap: 'wrap', gap: 3 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span draggable onDragStart={e => handleBlockDragStart(e, 'proposed')} style={dragHandleStyle} title="Ушлаб суринг">⠿</span>
              <span style={{ fontSize: '0.55rem', fontWeight: 700, color: '#3b82f6', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Proposed / Confirmed</span>
            </div>
            <div style={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
              {!isMarker && (
                <button onClick={onImprove} disabled={isImproving}
                  style={{ display: 'flex', alignItems: 'center', gap: 3, background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', color: 'white', border: 'none', borderRadius: 4, padding: '2px 7px', fontSize: '0.65rem', fontWeight: 700, cursor: isImproving ? 'not-allowed' : 'pointer', whiteSpace: 'nowrap' }}>
                  {isImproving
                    ? <><Loader2 size={10} style={{ animation: 'spin .8s linear infinite' }} /> AI...</>
                    : <><Sparkles size={10} /> AI Yaxshilash</>}
                </button>
              )}
              {lang === 'uz' && !isMarker && (
                <button onClick={runSayqallash} disabled={isSayqallash}
                  style={{ display: 'flex', alignItems: 'center', gap: 3, background: 'linear-gradient(135deg,#059669,#10b981)', color: 'white', border: 'none', borderRadius: 4, padding: '2px 7px', fontSize: '0.65rem', fontWeight: 700, cursor: isSayqallash ? 'not-allowed' : 'pointer', whiteSpace: 'nowrap' }}>
                  {isSayqallash
                    ? <><Loader2 size={10} style={{ animation: 'spin .8s linear infinite' }} /> Tekshirilmoqda...</>
                    : <>✦ Sayqallash</>}
                </button>
              )}
            </div>
          </div>

          {/* Annotation visualization */}
          {showAnnotations && annotations.length > 0 && (
            <div style={{ marginBottom: 4 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ fontSize: '0.55rem', fontWeight: 700, color: '#8b5cf6', textTransform: 'uppercase' }}>
                  {annotations.length} та хато топилди {rulesCount > 0 && <span style={{ fontSize: '0.5rem', color: '#0891b2', fontWeight: 600 }}>| 📚 {rulesCount} қоида</span>}
                </span>
                <div style={{ display: 'flex', gap: 3 }}>
                  <button onClick={acceptAll}
                    style={{ display: 'flex', alignItems: 'center', gap: 2, background: '#dcfce7', color: '#16a34a', border: '1px solid #86efac', borderRadius: 4, padding: '1px 6px', fontSize: '0.6rem', fontWeight: 700, cursor: 'pointer' }}>
                    ✓ Ҳаммасини қабул қилиш
                  </button>
                  <button onClick={() => { setAnnotations([]); setShowAnnotations(false) }}
                    style={{ background: '#fef2f2', color: '#ef4444', border: '1px solid #fca5a5', borderRadius: 4, padding: '1px 6px', fontSize: '0.6rem', fontWeight: 700, cursor: 'pointer' }}>
                    ✕ Ёпиш
                  </button>
                </div>
              </div>
              <div style={{ 
                background: '#fafbff', border: '1px solid #e5e7eb', borderRadius: 5, 
                padding: '6px 8px', lineHeight: 1.8, wordBreak: 'break-word'
              }}>
                {renderAnnotatedText()}
              </div>
            </div>
          )}

          <textarea value={proposed || ''} onChange={e => onProposedChange(e.target.value)}
            onClick={e => onWordClick(e as any, rowIdx, lang)} placeholder="Tasdiqlangan matn..."
            style={{ width: '100%', minHeight: 50, fontSize: '0.8rem', border: 'none', padding: '2px 4px', resize: 'vertical', outline: 'none', fontFamily: 'inherit', lineHeight: 1.45, boxSizing: 'border-box', background: 'transparent' }}
          />
        </div>
      </div>
    </td>
  )
}

function RichContent({ text, style }: { text: string; style?: React.CSSProperties }) {
  if (!text) return <span style={{ color: '#cbd5e1' }}>-</span>

  const imgRe = /§IMG:([^§]+)§/g
  const tblRe = /§TBL:([^§]+)§/g
  const imgPlain = /§IMG§/g

  const hasSpecial = imgRe.test(text) || tblRe.test(text) || imgPlain.test(text)
  if (!hasSpecial) return <span style={style}>{text}</span>

  const parts: React.ReactNode[] = []
  let lastIdx = 0
  const allRe = /§(IMG|TBL):([^§]+)§|§IMG§/g
  let m
  while ((m = allRe.exec(text)) !== null) {
    if (m.index > lastIdx) parts.push(<span key={'t' + lastIdx}>{text.slice(lastIdx, m.index)}</span>)
    if (m[0] === '§IMG§') {
      parts.push(<div key={'i' + m.index} style={{ color: '#94a3b8', fontSize: '0.75rem', fontStyle: 'italic' }}>[Rasm]</div>)
    } else if (m[1] === 'IMG') {
      parts.push(<img key={'i' + m.index} src={m[2]} alt="[Rasm]" style={{ maxWidth: '100%', display: 'block', margin: '4px 0', borderRadius: 3 }} />)
    } else if (m[1] === 'TBL') {
      parts.push(<div key={'t' + m.index} dangerouslySetInnerHTML={{ __html: m[2] }} style={{ margin: '4px 0', overflowX: 'auto' }} />)
    } else if (m[1] === 'MAT') {
      parts.push(<div key={'m' + m.index} style={{ display: 'inline-flex', alignItems: 'center', gap: 4, background: '#f5f3ff', color: '#7c3aed', padding: '2px 8px', borderRadius: 12, fontSize: '0.68rem', fontWeight: 700, margin: '2px 0', border: '1px solid #ddd6fe' }}>
        <Sparkles size={10} /> Formula
      </div>)
    }
    lastIdx = m.index + m[0].length
  }
  if (lastIdx < text.length) parts.push(<span key={'e'}>{text.slice(lastIdx)}</span>)
  return <div style={style}>{parts}</div>
}
