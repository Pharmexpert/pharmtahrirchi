'use client'

import React from 'react'
import Link from 'next/link'
import { Database, Sparkles, BookOpen } from 'lucide-react'

interface Props {
  textId: string
  filename: string
  API_BASE: string
  showSourceLangModal: string | null
  saveStatus: string | null
  isBatchPolishing: boolean
  isAiAligning: boolean
  savingAll: boolean
  isFinishing: boolean
  handleLinguisticBtnClick: (cat: string) => void
  batchTransliterate: (target: 'latin' | 'cyrillic') => void
  runBatchSayqallash: () => void
  aiAlign: () => void
  handleSaveAll: () => void
  finishWork: () => void
  handleExport: () => void
}

export default function TableToolbar({
  textId, filename, API_BASE,
  showSourceLangModal, saveStatus,
  isBatchPolishing, isAiAligning, savingAll, isFinishing,
  handleLinguisticBtnClick, batchTransliterate, runBatchSayqallash,
  aiAlign, handleSaveAll, finishWork, handleExport,
}: Props) {
  return (
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
        {textId && (
          <button onClick={() => window.open(`${API_BASE}/api/projects/${textId}/export-pdf`, '_blank')} style={{ padding: '5px 10px', background: '#dc2626', color: 'white', border: 'none', borderRadius: 6, fontWeight: 700, fontSize: '0.75rem', cursor: 'pointer', whiteSpace: 'nowrap' }}>
            Export PDF
          </button>
        )}
      </div>
    </header>
  )
}
