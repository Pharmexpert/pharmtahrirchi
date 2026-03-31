'use client'

import React, { useState, useRef, useEffect, useCallback } from 'react'
import { 
  Download, 
  Save, 
  Database, 
  Sparkles, 
  Loader2, 
  Plus, 
  Trash2, 
  BookOpen, 
  Settings, 
  LogOut,
  ChevronLeft,
  ChevronRight,
  Maximize2,
  Minimize2,
  Table as TableIcon,
  CheckCircle2,
  AlertCircle,
  FileText,
  MousePointer2,
  GripVertical,
  History,
  Languages,
  ShieldCheck,
  Check,
  X
} from 'lucide-react'
import { useAuth } from './LoginGuard'

interface RowData {
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

interface SayqallashAnnotation {
  from_index: number
  to_index: number
  old_value: string
  new_value: string
  error_type: string
  source: string
}

interface Props {
  initialData?: RowData[]
  filename?: string
  textId?: string
}

export default function TableEditor({ initialData = [], filename = 'Untitled.docx', textId = '' }: Props) {
  const { user, token, isAdmin } = useAuth()
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const [data, setData] = useState<RowData[]>(
    initialData.map(r => ({ ...r, display_no: r.display_no || String(r.sentence_no || '') }))
  )
  const [loading, setLoading] = useState(!initialData.length && !!textId)
  const [savingRow, setSavingRow] = useState<number | null>(null)
  const [improvingRow, setImprovingRow] = useState<{ idx: number, lang: string } | null>(null)
  const [savingAll, setSavingAll] = useState(false)
  const [isAiAligning, setIsAiAligning] = useState(false)
  const [dragIdx, setDragIdx] = useState<number | null>(null)
  const [dropIdx, setDropIdx] = useState<number | null>(null)
  const [saveStatus, setSaveStatus] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'editor' | 'preview'>('editor')
  
  const [popup, setPopup] = useState<SynonymPopup>({
    visible: false, x: 0, y: 0, word: '', lang: 'ru', rowIdx: -1, synonyms: [], loading: false
  })
  const popupRef = useRef<HTMLDivElement>(null)
  
  // Column width state (percentages)
  const [colWidths, setColWidths] = useState([28, 28, 28, 16]) 
  const resizingRef = useRef<{ idx: number; startX: number; startWidths: number[] } | null>(null)

  // Fetch initial data if not provided (for direct dashboard navigation)
  useEffect(() => {
    if (!initialData.length && textId) {
      fetchData()
    }
  }, [textId])

  const fetchData = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/history/${textId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        const d = await res.json()
        setData(d.map((r: any) => ({ ...r, display_no: r.display_no || String(r.sentence_no || '') })))
      }
    } catch (err) {
      console.error('Fetch error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleMove = useCallback((e: MouseEvent) => {
    if (!resizingRef.current) return
    e.preventDefault()
    const { idx, startX, startWidths } = resizingRef.current
    const deltaX = e.clientX - startX
    
    const tableEl = document.getElementById('editor-grid')
    const tableWidth = tableEl?.clientWidth || 1000
    const deltaPercent = (deltaX / tableWidth) * 100
    
    const newWidths = [...startWidths]
    newWidths[idx] = Math.max(10, startWidths[idx] + deltaPercent)
    newWidths[idx+1] = Math.max(10, startWidths[idx+1] - deltaPercent)
    
    setColWidths(newWidths)
  }, [])

  const handleUp = useCallback(() => {
    if (resizingRef.current) {
      resizingRef.current = null
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [])

  useEffect(() => {
    window.addEventListener('mousemove', handleMove)
    window.addEventListener('mouseup', handleUp)
    return () => {
      window.removeEventListener('mousemove', handleMove)
      window.removeEventListener('mouseup', handleUp)
    }
  }, [handleMove, handleUp])

  const startResizing = (idx: number, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    resizingRef.current = { idx, startX: e.clientX, startWidths: [...colWidths] }
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
  }

  const notify = (msg: string) => {
    setSaveStatus(msg)
    setTimeout(() => setSaveStatus(null), 3000)
  }

  const update = (idx: number, field: keyof RowData, value: string) =>
    setData(prev => { const d = [...prev]; (d[idx] as any)[field] = value; return d })

  const saveSingleRow = async (idx: number) => {
    setSavingRow(idx)
    try {
      const row = data[idx]
      const res = await fetch(`${API_BASE}/save-row`, {
        method: 'POST', 
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(row)
      })
      if (!res.ok) throw new Error()
      const r = await res.json()
      if (r.new_id && data[idx].sentence_no === 0) {
        setData(prev => { const d = [...prev]; d[idx] = { ...d[idx], sentence_no: r.new_id }; return d })
      }
      notify(`Gap #${data[idx].display_no} saqlandi ✓`)
    } catch { notify('Saqlashda xatolik') }
    finally { setSavingRow(null) }
  }

  const handleExport = async () => {
    notify('DOCX tayyorlanmoqda...')
    try {
      const res = await fetch(`${API_BASE}/export`, {
        method: 'POST', 
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ filename, data })
      })
      if (!res.ok) throw new Error()
      
      const contentDisposition = res.headers.get('content-disposition')
      let downloadName = 'aligned_' + filename
      if (contentDisposition) {
        const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;\n]*)/)
        if (utf8Match?.[1]) downloadName = decodeURIComponent(utf8Match[1])
      }
      
      const blob = await res.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = downloadName
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      notify('Yuklab olindi ✓')
    } catch { notify('Eksportda xatolik') }
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
    if (!sel || sel.length < 2) return
    
    const px = Math.min(e.clientX, window.innerWidth - 300)
    const py = Math.min(e.clientY + 20, window.innerHeight - 250)
    setPopup({ visible: true, x: px, y: py, word: sel, lang, rowIdx, synonyms: [], loading: true })
    
    try {
      const res = await fetch(`${API_BASE}/suggest-edits`, {
        method: 'POST', 
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          word: sel, lang,
          context_en: data[rowIdx].en,
          context_ru: data[rowIdx].ru_proposed || data[rowIdx].ru_v1,
          context_uz: data[rowIdx].uz_proposed || data[rowIdx].uz_v1,
        })
      })
      if (res.ok) {
        const r = await res.json()
        setPopup(p => ({ ...p, synonyms: r.variants || r.synonyms || [], loading: false }))
      }
    } catch { setPopup(p => ({ ...p, loading: false })) }
  }

  if (loading) {
    return (
      <div style={{ padding: '100px', textAlign: 'center', color: 'var(--text-muted)' }}>
        <Loader2 className="animate-spin" size={48} style={{ margin: '0 auto 24px', opacity: 0.5 }} />
        <p style={{ fontSize: '1.1rem', fontWeight: 600 }}>Tarkib yuklanmoqda...</p>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Editor Header Controls */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        background: 'var(--bg-card)',
        padding: '16px 24px',
        borderRadius: 'var(--radius-lg)',
        border: '1px solid var(--border)',
        boxShadow: 'var(--shadow-sm)',
        position: 'sticky',
        top: 'var(--header-height)',
        zIndex: 40,
        backdropFilter: 'blur(10px)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
           <div style={{ display: 'flex', background: 'var(--bg-secondary)', padding: '4px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' }}>
             <button 
               onClick={() => setActiveTab('editor')}
               style={{ 
                 padding: '8px 16px', 
                 borderRadius: 'var(--radius-sm)', 
                 border: 'none', 
                 fontSize: '0.85rem', 
                 fontWeight: 600,
                 cursor: 'pointer',
                 background: activeTab === 'editor' ? 'white' : 'transparent',
                 color: activeTab === 'editor' ? 'var(--accent-primary)' : 'var(--text-muted)',
                 boxShadow: activeTab === 'editor' ? 'var(--shadow-sm)' : 'none',
                 transition: 'all 0.2s'
               }}
             >
               Editor
             </button>
             <button 
               onClick={() => setActiveTab('preview')}
               style={{ 
                 padding: '8px 16px', 
                 borderRadius: 'var(--radius-sm)', 
                 border: 'none', 
                 fontSize: '0.85rem', 
                 fontWeight: 600,
                 cursor: 'pointer',
                 background: activeTab === 'preview' ? 'white' : 'transparent',
                 color: activeTab === 'preview' ? 'var(--accent-primary)' : 'var(--text-muted)',
                 boxShadow: activeTab === 'preview' ? 'var(--shadow-sm)' : 'none',
                 transition: 'all 0.2s'
               }}
             >
               Preview
             </button>
           </div>
           
           <div style={{ height: '24px', width: '1px', background: 'var(--border)' }}></div>
           
           <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
             <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 600 }}>TIZIM:</span>
             <button 
               onClick={async () => {
                 setIsAiAligning(true)
                 notify('AI moslashtirmoqda...')
                 try {
                   const res = await fetch(`${API_BASE}/align-document`, {
                     method: 'POST', 
                     headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                     body: JSON.stringify({ data })
                   })
                   if (res.ok) {
                     const r = await res.json()
                     setData(r.data)
                     notify('AI Alignment yakunlandi ✓')
                   }
                 } finally { setIsAiAligning(false) }
               }}
               disabled={isAiAligning}
               style={{ 
                 padding: '8px 16px', 
                 background: 'var(--info-bg)', 
                 color: 'var(--info)', 
                 border: '1px solid rgba(74, 139, 194, 0.2)', 
                 borderRadius: 'var(--radius-md)', 
                 fontSize: '0.85rem', 
                 fontWeight: 700,
                 cursor: 'pointer',
                 display: 'flex',
                 alignItems: 'center',
                 gap: '8px'
               }}
             >
               {isAiAligning ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
               AI Alignment
             </button>
           </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {saveStatus && (
            <span style={{ 
              fontSize: '0.8rem', 
              color: 'var(--success)', 
              fontWeight: 700, 
              padding: '8px 16px', 
              background: 'var(--success-bg)', 
              borderRadius: '20px',
              animation: 'fadeIn 0.3s'
            }}>
              {saveStatus}
            </span>
          )}
          <button 
            onClick={handleExport}
            style={{ 
              padding: '10px 20px', 
              background: 'white', 
              color: 'var(--text-primary)', 
              border: '1px solid var(--border)', 
              borderRadius: 'var(--radius-md)', 
              fontSize: '0.85rem', 
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              boxShadow: 'var(--shadow-sm)'
            }}
          >
            <Download size={18} />
            Export DOCX
          </button>
          <button 
            onClick={async () => {
              setSavingAll(true)
              try {
                const res = await fetch(`${API_BASE}/save`, {
                  method: 'POST', 
                  headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                  body: JSON.stringify({ data })
                })
                if (res.ok) notify('Barcha o\'zgarishlar saqlandi ✓')
              } finally { setSavingAll(false) }
            }}
            disabled={savingAll}
            style={{ 
              padding: '10px 24px', 
              background: 'var(--accent-gradient)', 
              color: 'white', 
              border: 'none', 
              borderRadius: 'var(--radius-md)', 
              fontSize: '0.85rem', 
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              boxShadow: 'var(--shadow-glow)'
            }}
          >
            {savingAll ? <Loader2 size={18} className="animate-spin" /> : <Save size={18} />}
            Barchasini saqlash
          </button>
        </div>
      </div>

      {/* Editor Grid */}
      <div id="editor-grid" style={{ 
        background: 'var(--bg-card)',
        borderRadius: 'var(--radius-lg)',
        border: '1px solid var(--border)',
        overflow: 'hidden',
        boxShadow: 'var(--shadow-md)'
      }}>
        {/* Table Header */}
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: `48px ${colWidths[0]}% ${colWidths[1]}% ${colWidths[2]}% ${colWidths[3]}%`,
          background: 'var(--bg-secondary)',
          borderBottom: '2px solid var(--border)',
          position: 'sticky',
          top: 0,
          zIndex: 30
        }}>
          <div style={{ padding: '16px', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textAlign: 'center' }}>#</div>
          
          <div style={{ padding: '16px', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', position: 'relative' }}>
            ENGLISH (SOURCE)
            <div onMouseDown={e => startResizing(0, e)} style={{ position: 'absolute', right: -4, top: 0, bottom: 0, width: 8, cursor: 'col-resize', zIndex: 35 }}></div>
          </div>
          
          <div style={{ padding: '16px', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', position: 'relative' }}>
            RUSSIAN (TARGET)
            <div onMouseDown={e => startResizing(1, e)} style={{ position: 'absolute', right: -4, top: 0, bottom: 0, width: 8, cursor: 'col-resize', zIndex: 35 }}></div>
          </div>
          
          <div style={{ padding: '16px', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', position: 'relative' }}>
            UZBEK (TARGET)
            <div onMouseDown={e => startResizing(2, e)} style={{ position: 'absolute', right: -4, top: 0, bottom: 0, width: 8, cursor: 'col-resize', zIndex: 35 }}></div>
          </div>
          
          <div style={{ padding: '16px', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)' }}>IZOH VA QAYDLAR</div>
        </div>

        {/* Table Body */}
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          {data.map((row, idx) => (
            <EditorRow 
              key={`${row.text_id}-${idx}`}
              row={row}
              idx={idx}
              colWidths={colWidths}
              onUpdate={update}
              onSave={() => saveSingleRow(idx)}
              isSaving={savingRow === idx}
              isImproving={improvingRow?.idx === idx}
              onImprove={(l: string) => {
                setImprovingRow({ idx, lang: l })
                setTimeout(() => setImprovingRow(null), 2000)
              }}
              onWordClick={handleWordClick}
              apiBase={API_BASE}
              token={token}
            />
          ))}
        </div>
      </div>

      {/* Synonym Popup */}
      {popup.visible && (
        <div ref={popupRef} style={{ 
          position: 'fixed', top: popup.y, left: popup.x, zIndex: 1000, 
          background: 'white', borderRadius: 'var(--radius-md)', padding: '12px',
          minWidth: '220px', boxShadow: 'var(--shadow-lg)', border: '1px solid var(--border)',
          animation: 'fadeIn 0.2s'
        }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--accent-primary)', fontWeight: 700, marginBottom: '8px', textTransform: 'uppercase' }}>
            Tahrir varianti: <span style={{ color: 'var(--text-primary)' }}>{popup.word}</span>
          </div>
          {popup.loading ? (
            <div style={{ padding: '12px', textAlign: 'center' }}><Loader2 size={20} className="animate-spin" color="var(--text-muted)" /></div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {popup.synonyms.map((s, i) => (
                <button 
                  key={i} 
                  onClick={() => {
                    const field = popup.lang === 'ru' ? 'ru_proposed' : 'uz_proposed'
                    const current = (data[popup.rowIdx] as any)[field] || ''
                    update(popup.rowIdx, field as keyof RowData, current.replace(popup.word, s))
                    setPopup(p => ({ ...p, visible: false }))
                  }}
                  style={{ 
                    textAlign: 'left', padding: '8px 12px', background: 'var(--bg-secondary)', 
                    border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)',
                    fontSize: '0.85rem', cursor: 'pointer', transition: 'all 0.2s'
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'white'}
                  onMouseLeave={e => e.currentTarget.style.background = 'var(--bg-secondary)'}
                >
                  {s}
                </button>
              ))}
              {popup.synonyms.length === 0 && <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textAlign: 'center' }}>Varianlar topilmadi</p>}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function EditorRow({ row, idx, colWidths, onUpdate, onSave, isSaving, isImproving, onImprove, onWordClick, apiBase, token }: any) {
  const isMarker = row.type === 'marker'
  const [sayqallashData, setSayqallashData] = useState<{ annotations: SayqallashAnnotation[]; corrected_text: string; loading: boolean } | null>(null)
  
  const handleSayqallash = async (text: string) => {
    setSayqallashData({ annotations: [], corrected_text: '', loading: true })
    try {
      const res = await fetch(`${apiBase}/sayqallash`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ text, lang: 'uz' })
      })
      if (res.ok) {
        const data = await res.json()
        setSayqallashData({ annotations: data.annotations || [], corrected_text: data.corrected_text || text, loading: false })
      } else {
        setSayqallashData(null)
      }
    } catch {
      setSayqallashData(null)
    }
  }

  const acceptAnnotation = (ann: SayqallashAnnotation) => {
    const currentVal = row.uz_proposed || row.uz_v1
    const newVal = currentVal.replace(ann.old_value, ann.new_value)
    onUpdate(idx, 'uz_proposed', newVal)
    if (sayqallashData) {
      setSayqallashData({
        ...sayqallashData,
        annotations: sayqallashData.annotations.filter(a => a.from_index !== ann.from_index)
      })
    }
  }

  const acceptAllAnnotations = () => {
    if (!sayqallashData) return
    let currentVal = row.uz_proposed || row.uz_v1
    // Sort by position desc to avoid index shift
    const sorted = [...sayqallashData.annotations].sort((a, b) => b.from_index - a.from_index)
    for (const ann of sorted) {
      currentVal = currentVal.replace(ann.old_value, ann.new_value)
    }
    onUpdate(idx, 'uz_proposed', currentVal)
    setSayqallashData({ ...sayqallashData, annotations: [] })
  }

  if (isMarker) {
    return (
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: `48px 1fr`,
        background: '#FFF1E6',
        borderBottom: '1px solid #FFD8BA'
      }}>
        <div style={{ padding: '12px', textAlign: 'center', color: '#C07840', fontWeight: 800 }}>
          <TableIcon size={16} />
        </div>
        <div style={{ padding: '12px 16px', fontWeight: 800, color: '#85512B', fontSize: '0.85rem', letterSpacing: '0.5px' }}>
          {row.en}
        </div>
      </div>
    )
  }

  return (
    <div style={{ 
      display: 'grid', 
      gridTemplateColumns: `48px ${colWidths[0]}% ${colWidths[1]}% ${colWidths[2]}% ${colWidths[3]}%`,
      borderBottom: '1px solid var(--border)',
      transition: 'background 0.2s'
    }}
    onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-secondary)'}
    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
    >
      {/* Row Controls */}
      <div style={{ padding: '16px 8px', borderRight: '1px solid var(--border)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
        <span style={{ fontSize: '0.7rem', fontWeight: 800, color: 'var(--text-muted)' }}>{row.display_no}</span>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <button onClick={onSave} disabled={isSaving} style={{ background: 'white', border: '1px solid var(--border)', borderRadius: '6px', padding: '6px', cursor: 'pointer', color: 'var(--success)' }}>
            {isSaving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
          </button>
          <button style={{ background: 'white', border: '1px solid var(--border)', borderRadius: '6px', padding: '6px', cursor: 'pointer', color: 'var(--danger)' }}>
            <Trash2 size={14} />
          </button>
        </div>
        <div style={{ cursor: 'grab', color: 'var(--border)' }}><GripVertical size={16} /></div>
      </div>

      {/* English Source */}
      <div style={{ padding: '16px', borderRight: '1px solid var(--border)', fontSize: '0.9rem', lineHeight: 1.6, color: 'var(--text-primary)' }}>
        <div style={{ marginBottom: '8px', fontSize: '0.65rem', fontWeight: 800, color: '#C07840', textTransform: 'uppercase', letterSpacing: '1px' }}>Original</div>
        {row.en}
      </div>

      {/* Russian Target */}
      <TargetCell 
        val={row.ru_proposed || row.ru_v1} 
        v1={row.ru_v1}
        lang="ru" 
        onUpdate={(v: string) => onUpdate(idx, row.ru_proposed ? 'ru_proposed' : 'ru_v1', v)}
        onImprove={() => onImprove('ru')}
        isImproving={isImproving && row.lang === 'ru'}
        onWordClick={(e: any) => onWordClick(e, idx, 'ru')}
      />

      {/* Uzbek Target — with Sayqallash */}
      <TargetCell 
        val={row.uz_proposed || row.uz_v1} 
        v1={row.uz_v1}
        lang="uz" 
        onUpdate={(v: string) => onUpdate(idx, row.uz_proposed ? 'uz_proposed' : 'uz_v1', v)}
        onImprove={() => onImprove('uz')}
        isImproving={isImproving && row.lang === 'uz'}
        onWordClick={(e: any) => onWordClick(e, idx, 'uz')}
        onSayqallash={handleSayqallash}
        sayqallashData={sayqallashData}
        onAcceptAnnotation={acceptAnnotation}
        onAcceptAll={acceptAllAnnotations}
        onDismissSayqallash={() => setSayqallashData(null)}
      />

      {/* Notes */}
      <div style={{ padding: '16px' }}>
        <textarea 
          value={row.notes}
          onChange={e => onUpdate(idx, 'notes', e.target.value)}
          placeholder="Qaydlar..."
          style={{ 
            width: '100%', height: '100%', minHeight: '80px', border: 'none', background: '#FFFDF5', 
            borderRadius: 'var(--radius-sm)', padding: '12px', fontSize: '0.8rem', outline: 'none', 
            resize: 'none', color: '#6B5744', fontStyle: 'italic', borderLeft: '2px solid #E8B78E'
          }}
        />
      </div>
    </div>
  )
}

function TargetCell({ val, v1, lang, onUpdate, onImprove, isImproving, onWordClick, onSayqallash, sayqallashData, onAcceptAnnotation, onAcceptAll, onDismissSayqallash }: any) {
  const isChanged = val !== v1
  const isUz = lang === 'uz'
  
  return (
    <div style={{ 
      padding: '16px', 
      borderRight: '1px solid var(--border)', 
      display: 'flex', 
      flexDirection: 'column', 
      gap: '12px' 
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '6px' }}>
        <div style={{ fontSize: '0.65rem', fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1px' }}>
          {lang.toUpperCase()} {isChanged && <span style={{ color: 'var(--success)', marginLeft: '4px' }}>• Tahrirlangan</span>}
        </div>
        <div style={{ display: 'flex', gap: '4px' }}>
          <button 
            onClick={onImprove}
            style={{ 
              padding: '4px 8px', background: 'var(--bg-secondary)', 
              border: '1px solid var(--border)', borderRadius: '4px', 
              fontSize: '0.65rem', fontWeight: 700, cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: '4px'
            }}
          >
            {isImproving ? <Loader2 size={10} className="animate-spin" /> : <Sparkles size={10} />}
            AI Yaxshilash
          </button>
          {isUz && (
            <button 
              onClick={() => onSayqallash && onSayqallash(val)}
              disabled={sayqallashData?.loading}
              style={{ 
                padding: '4px 8px', 
                background: sayqallashData?.annotations?.length ? 'var(--warning-bg)' : 'var(--info-bg)', 
                border: `1px solid ${sayqallashData?.annotations?.length ? 'rgba(212, 163, 60, 0.3)' : 'rgba(74, 139, 194, 0.2)'}`, 
                borderRadius: '4px', 
                fontSize: '0.65rem', fontWeight: 700, cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: '4px',
                color: sayqallashData?.annotations?.length ? 'var(--warning)' : 'var(--info)'
              }}
            >
              {sayqallashData?.loading ? <Loader2 size={10} className="animate-spin" /> : <ShieldCheck size={10} />}
              Sayqallash
              {sayqallashData?.annotations?.length ? ` (${sayqallashData.annotations.length})` : ''}
            </button>
          )}
        </div>
      </div>
      
      <textarea 
        value={val}
        onChange={e => onUpdate(e.target.value)}
        onMouseUp={onWordClick}
        style={{ 
          width: '100%', minHeight: '120px', border: 'none', 
          background: isChanged ? 'rgba(59, 155, 110, 0.03)' : 'transparent', 
          fontSize: '0.9rem', lineHeight: 1.6, outline: 'none', resize: 'vertical',
          padding: '4px', fontFamily: 'inherit'
        }}
        placeholder="Таржима матни..."
      />

      {/* Sayqallash Annotations Panel */}
      {isUz && sayqallashData && !sayqallashData.loading && sayqallashData.annotations.length > 0 && (
        <div style={{ 
          background: '#FFFBF0', border: '1px solid rgba(212, 163, 60, 0.25)',
          borderRadius: 'var(--radius-md)', overflow: 'hidden'
        }}>
          <div style={{ 
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: '8px 12px', background: 'rgba(212, 163, 60, 0.08)', borderBottom: '1px solid rgba(212, 163, 60, 0.15)'
          }}>
            <span style={{ fontSize: '0.7rem', fontWeight: 800, color: '#A67C30', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              🔍 {sayqallashData.annotations.length} та хатолик топилди
            </span>
            <div style={{ display: 'flex', gap: '6px' }}>
              <button 
                onClick={onAcceptAll}
                style={{ 
                  padding: '3px 8px', background: 'var(--success)', color: 'white',
                  border: 'none', borderRadius: '4px', fontSize: '0.6rem', fontWeight: 700,
                  cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '3px'
                }}
              >
                <CheckCircle2 size={10} /> Ҳаммасини қабул қилиш
              </button>
              <button 
                onClick={onDismissSayqallash}
                style={{ 
                  padding: '3px 6px', background: 'transparent', color: 'var(--text-muted)',
                  border: '1px solid var(--border)', borderRadius: '4px', fontSize: '0.6rem',
                  cursor: 'pointer'
                }}
              >
                <X size={10} />
              </button>
            </div>
          </div>
          <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
            {sayqallashData.annotations.map((ann: SayqallashAnnotation, i: number) => (
              <div key={i} style={{ 
                display: 'flex', alignItems: 'center', gap: '8px',
                padding: '6px 12px', borderBottom: '1px solid rgba(212, 163, 60, 0.1)',
                fontSize: '0.78rem'
              }}>
                <span style={{ 
                  fontFamily: 'monospace', padding: '2px 6px', background: 'var(--danger-bg)',
                  color: 'var(--danger)', borderRadius: '3px', textDecoration: 'line-through',
                  fontSize: '0.75rem'
                }}>
                  {ann.old_value}
                </span>
                <span style={{ color: 'var(--text-muted)' }}>→</span>
                <span style={{ 
                  fontFamily: 'monospace', padding: '2px 6px', background: 'var(--success-bg)',
                  color: 'var(--success)', borderRadius: '3px', fontWeight: 700,
                  fontSize: '0.75rem'
                }}>
                  {ann.new_value}
                </span>
                <span style={{ 
                  fontSize: '0.6rem', padding: '2px 6px', background: 'var(--bg-secondary)',
                  borderRadius: '10px', color: 'var(--text-muted)', fontWeight: 600,
                  marginLeft: 'auto', flexShrink: 0
                }}>
                  {ann.error_type}
                </span>
                <button 
                  onClick={() => onAcceptAnnotation(ann)}
                  title="Қабул қилиш"
                  style={{ 
                    padding: '3px 6px', background: 'var(--success-bg)', color: 'var(--success)',
                    border: 'none', borderRadius: '4px', cursor: 'pointer', flexShrink: 0
                  }}
                >
                  <Check size={12} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sayqallash loading indicator */}
      {isUz && sayqallashData?.loading && (
        <div style={{ 
          padding: '12px', textAlign: 'center', background: 'var(--info-bg)',
          borderRadius: 'var(--radius-md)', display: 'flex', alignItems: 'center',
          justifyContent: 'center', gap: '8px', fontSize: '0.8rem', color: 'var(--info)', fontWeight: 600
        }}>
          <Loader2 size={14} className="animate-spin" />
          Матн текширилмоқда...
        </div>
      )}

      {/* No errors after check */}
      {isUz && sayqallashData && !sayqallashData.loading && sayqallashData.annotations.length === 0 && (
        <div style={{ 
          padding: '8px 12px', textAlign: 'center', background: 'var(--success-bg)',
          borderRadius: 'var(--radius-md)', display: 'flex', alignItems: 'center',
          justifyContent: 'center', gap: '6px', fontSize: '0.75rem', color: 'var(--success)', fontWeight: 700
        }}>
          <CheckCircle2 size={14} />
          Хатолик топилмади ✓
        </div>
      )}
      
      {isChanged && v1 && (
        <div style={{ 
          fontSize: '0.75rem', color: 'var(--text-muted)', background: 'var(--bg-secondary)', 
          padding: '8px', borderRadius: '4px', borderLeft: '2px solid var(--border)'
        }}>
          <span style={{ fontWeight: 700, display: 'block', marginBottom: '2px' }}>V1 Original:</span>
          {v1}
        </div>
      )}
    </div>
  )
}
