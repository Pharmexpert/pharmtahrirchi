'use client'

import React, { useState, useRef, useEffect } from 'react'
import { Download, Save, Database, Sparkles, Loader2, Plus, Trash2, BookOpen, MousePointer2 } from 'lucide-react'
import Link from 'next/link'
import { useAuth } from './LoginGuard'

export interface RowData {
  type: 'marker' | 'content'
  en: string
  ru_v1: string
  ru_proposed: string
  uz_v1: string
  uz_proposed: string
  status: 'aligned' | 'review'
  sentence_no: number
  display_no: string
  text_id: string
  notes: string
}

interface SynonymPopup {
  visible: boolean; x: number; y: number
  word: string; lang: 'ru' | 'uz'; rowIdx: number
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
  const [dragIdx, setDragIdx] = useState<number | null>(null)
  const [dropIdx, setDropIdx] = useState<number | null>(null)
  const [saveStatus, setSaveStatus] = useState<string | null>(null)
  const [popup, setPopup] = useState<SynonymPopup>({
    visible: false, x: 0, y: 0, word: '', lang: 'ru', rowIdx: -1, synonyms: [], loading: false
  })
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
    return () => document.removeEventListener('mousedown', h)
  }, [])

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
      } catch { /* ignore */ }
    }
    setData(prev => prev.filter((_, i) => i !== idx))
    notify('Gap #' + row.display_no + ' ochirildi')
  }

  const handleWordClick = async (e: React.MouseEvent<HTMLTextAreaElement>, rowIdx: number, lang: 'ru' | 'uz') => {
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
    setPopup({ visible: true, x: px, y: py, word: sel, lang, rowIdx, synonyms: [], loading: true })
    try {
      const res = await fetch(`${API_BASE}/suggest-edits`, {
        method: 'POST', headers: authHeaders,
        body: JSON.stringify({
          word: sel, lang,
          context_en: data[rowIdx].en,
          context_ru: data[rowIdx].ru_proposed || data[rowIdx].ru_v1,
          context_uz: data[rowIdx].uz_proposed || data[rowIdx].uz_v1,
        })
      })
      if (!res.ok) throw new Error()
      const r = await res.json()
      setPopup(p => ({ ...p, synonyms: r.variants || r.synonyms || [], loading: false }))
    } catch { setPopup(p => ({ ...p, loading: false, synonyms: [] })) }
  }

  const applyVariant = (v: string) => {
    const { rowIdx, word, lang } = popup
    const field = lang === 'ru' ? 'ru_proposed' : 'uz_proposed'
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
    } catch { notify('AI xatolik') }
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
        if (row.ru_v1 && row.ru_proposed && row.ru_v1.trim() !== row.ru_proposed.trim()) {
          const nRes = await fetch(`${API_BASE}/auto-notes`, {
            method: 'POST', headers: authHeaders,
            body: JSON.stringify({ v1: row.ru_v1, proposed: row.ru_proposed, lang: 'ru' })
          })
          if (nRes.ok) { const nr = await nRes.json(); if (nr.notes) autoNotes += nr.notes + '\n' }
        }
      } catch {}

      let finalNotes = row.notes || ''
      if (autoNotes && !finalNotes.includes(autoNotes.trim().split('\n')[0])) {
        finalNotes = (finalNotes ? finalNotes + '\n\n' : '') + autoNotes.trim()
        setData(prev => { const d = [...prev]; d[idx] = { ...d[idx], notes: finalNotes }; return d })
      }

      const res = await fetch(`${API_BASE}/save-row`, {
        method: 'POST', headers: authHeaders,
        body: JSON.stringify({ ...row, notes: finalNotes })
      })
      if (!res.ok) throw new Error()
      const r = await res.json()
      if (r.new_id && data[idx].sentence_no === 0) {
        setData(prev => { const d = [...prev]; d[idx] = { ...d[idx], sentence_no: r.new_id }; return d })
      }
      notify('Gap #' + data[idx].display_no + ' saqlandi ✓ Qoidalar yangilandi')
    } catch { notify('Saqlash xatolik') }
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
    } catch { notify('AI xatolik') }
    finally { setIsAiAligning(false) }
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
    } catch { notify('Saqlash xatolik') }
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
    } catch { notify('Export xatolik') }
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
    } catch { notify('Xatolik') }
    finally { setSavingRow(null) }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', fontFamily: "'Inter','Segoe UI',sans-serif", background: '#f1f5f9' }}>

      <header style={{ flexShrink: 0, position: 'sticky', top: 0, zIndex: 100, background: '#1e293b', color: 'white', padding: '0 14px', height: '50px', display: 'flex', alignItems: 'center', gap: '12px', boxShadow: '0 2px 8px rgba(0,0,0,.25)' }}>
        <Database size={17} color="#60a5fa" style={{ flexShrink: 0 }} />
        <span style={{ fontWeight: 800, fontSize: '0.88rem', whiteSpace: 'nowrap', flexShrink: 0 }}>Pharma Editor</span>
        {textId && <span style={{ background: '#334155', padding: '2px 9px', borderRadius: 20, fontSize: '0.72rem', color: '#93c5fd', fontWeight: 700, flexShrink: 0 }}>ID: {textId}</span>}
        <span style={{ fontSize: '0.73rem', color: '#94a3b8', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{filename}</span>
        {saveStatus && <span style={{ background: '#22c55e', color: 'white', padding: '2px 10px', borderRadius: 20, fontSize: '0.72rem', fontWeight: 700, whiteSpace: 'nowrap', flexShrink: 0 }}>{saveStatus}</span>}
        <div style={{ display: 'flex', gap: 6, flexShrink: 0, alignItems: 'center' }}>
          <Link href="/rules" style={{ display: 'flex', alignItems: 'center', gap: '4px', background: '#334155', color: '#94a3b8', padding: '5px 10px', borderRadius: 6, fontSize: '0.75rem', fontWeight: 700, textDecoration: 'none', transition: 'all 0.2s' }}
                onMouseEnter={e => (e.currentTarget.style.color = 'white', e.currentTarget.style.background = '#475569')}
                onMouseLeave={e => (e.currentTarget.style.color = '#94a3b8', e.currentTarget.style.background = '#334155')}>
            <BookOpen size={14} />
            Rules DB
          </Link>
          <button onClick={aiAlign} disabled={isAiAligning} style={{ padding: '5px 10px', background: isAiAligning ? '#4b5563' : 'linear-gradient(135deg,#6366f1,#8b5cf6)', color: 'white', border: 'none', borderRadius: 6, fontWeight: 700, fontSize: '0.75rem', cursor: isAiAligning ? 'not-allowed' : 'pointer', whiteSpace: 'nowrap' }}>
            {isAiAligning ? 'Moslashtirilmoqda...' : 'AI Moslash'}
          </button>
          <button onClick={handleSaveAll} disabled={savingAll} style={{ padding: '5px 10px', background: '#3b82f6', color: 'white', border: 'none', borderRadius: 6, fontWeight: 700, fontSize: '0.75rem', cursor: 'pointer', whiteSpace: 'nowrap' }}>
            {savingAll ? 'Saqlanmoqda...' : 'Hammasi'}
          </button>
          <button onClick={handleExport} style={{ padding: '5px 10px', background: '#10b981', color: 'white', border: 'none', borderRadius: 6, fontWeight: 700, fontSize: '0.75rem', cursor: 'pointer', whiteSpace: 'nowrap' }}>
            Export DOCX
          </button>
        </div>
      </header>

      {popup.visible && (
        <div ref={popupRef} style={{ position: 'fixed', top: popup.y, left: popup.x, zIndex: 9999, background: 'white', border: '1px solid #e2e8f0', borderRadius: 10, padding: '9px 11px', minWidth: 210, maxWidth: 290, boxShadow: '0 8px 28px rgba(0,0,0,.18)' }}>
          <div style={{ fontSize: '0.68rem', color: '#6366f1', marginBottom: 6, fontWeight: 700 }}>
            Tahrir varianti: <span style={{ color: '#1e293b' }}>{popup.word}</span>
          </div>
          {popup.loading
            ? <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Yuklanmoqda...</div>
            : popup.synonyms.length === 0
              ? <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Topilmadi</div>
              : <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 3 }}>
                  {popup.synonyms.map((s, i) => (
                    <li key={i} onClick={() => applyVariant(s)}
                      style={{ padding: '4px 8px', borderRadius: 5, fontSize: '0.82rem', cursor: 'pointer', border: '1px solid #e2e8f0', display: 'flex', alignItems: 'center', gap: 5 }}>
                      <span style={{ color: '#6366f1', fontSize: '0.65rem', fontWeight: 700 }}>{i + 1}.</span> {s}
                    </li>
                  ))}
                </ul>
          }
        </div>
      )}

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
                Uzbek
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

                  <td style={{ padding: '3px 6px', verticalAlign: 'top', borderRight: '1px solid #e9edf2', fontSize: '0.65rem', color: '#64748b', lineHeight: 1.25, fontWeight: row.type === 'marker' ? 800 : 400 }}>
                    <RichContent text={row.en} />
                  </td>

                  <LangCell v1={row.ru_v1} proposed={row.ru_proposed} rowIdx={idx} lang="ru"
                    isMarker={row.type === 'marker'} isImproving={improvingRow?.idx === idx && improvingRow?.lang === 'ru'}
                    onV1Change={v => update(idx, 'ru_v1', v)}
                    onProposedChange={v => update(idx, 'ru_proposed', v)}
                    onImprove={() => improveRow(idx, 'ru')} onWordClick={handleWordClick}
                    onBlockDrop={handleBlockDrop} token={token || undefined} />

                  <LangCell v1={row.uz_v1} proposed={row.uz_proposed} rowIdx={idx} lang="uz"
                    isMarker={row.type === 'marker'} isImproving={improvingRow?.idx === idx && improvingRow?.lang === 'uz'}
                    onV1Change={v => update(idx, 'uz_v1', v)}
                    onProposedChange={v => update(idx, 'uz_proposed', v)}
                    onImprove={() => improveRow(idx, 'uz')} onWordClick={handleWordClick}
                    onBlockDrop={handleBlockDrop} token={token || undefined} />

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

function LangCell({ v1, proposed, rowIdx, lang, isMarker, isImproving, onV1Change, onProposedChange, onImprove, onWordClick, onBlockDrop, token }: {
  v1: string; proposed: string; rowIdx: number; lang: 'ru' | 'uz'; isMarker: boolean
  isImproving: boolean
  onV1Change: (v: string) => void
  onProposedChange: (v: string) => void
  onImprove: () => void
  onWordClick: (e: React.MouseEvent<HTMLTextAreaElement>, idx: number, lang: 'ru' | 'uz') => void
  onBlockDrop?: (fromRow: number, fromField: string, toRow: number, toField: string) => void
  token?: string
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
    } catch {}
  }

  const runSayqallash = async () => {
    const text = proposed || v1 || ''
    if (!text.trim()) return
    setIsSayqallash(true)
    try {
      const res = await fetch(`${API_BASE}/sayqallash`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ text })
      })
      if (!res.ok) throw new Error()
      const r = await res.json()
      setAnnotations(r.annotations || [])
      setShowAnnotations(true)
      setRulesCount(r.rules_count || 0)
    } catch { setAnnotations([]) }
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
