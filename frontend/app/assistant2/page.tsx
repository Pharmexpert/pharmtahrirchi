'use client'

import React, { useState, useRef, useCallback } from 'react'
import { useAuth } from '../../components/LoginGuard'
import api from '../../services/api'
import WordDocumentViewer from '../../components/WordDocumentViewer'
import {
  Languages, FileEdit, CheckCircle, Upload, Download, Loader2,
  FileText, X, ChevronRight, AlertCircle, Star, TrendingUp,
  GraduationCap, FileDown, ChevronDown
} from 'lucide-react'

// ═══════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════

type MainTab = 'create' | 'check'
type CreateTab = 'translate' | 'edit'
type CheckTab = 'translation' | 'edit'
type Lang = 'uz' | 'ru' | 'en'

interface QualityResult {
  umumiy_ball: number
  [key: string]: any
}

// ═══════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════

const LANG_LABELS: Record<Lang, { uz: string; flag: string }> = {
  uz: { uz: "O'zbek", flag: '🇺🇿' },
  ru: { uz: 'Rus', flag: '🇷🇺' },
  en: { uz: 'Ingliz', flag: '🇬🇧' },
}

const ALL_LANGS: Lang[] = ['uz', 'ru', 'en']

const ERROR_TYPES = [
  { value: 'terminology', label: 'Terminologiya' },
  { value: 'grammar', label: 'Grammatika' },
  { value: 'style', label: 'Uslub' },
  { value: 'completeness', label: "To'liqlik" },
  { value: 'other', label: 'Boshqa' },
]

// ═══════════════════════════════════════════════════
// Helper Components
// ═══════════════════════════════════════════════════

function ScoreBadge({ score }: { score: number }) {
  const color = score >= 76 ? 'var(--success)' : score >= 51 ? 'var(--warning)' : 'var(--danger)'
  const bg = score >= 76 ? 'var(--success-bg)' : score >= 51 ? 'var(--warning-bg)' : 'var(--danger-bg)'
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      padding: '4px 14px', borderRadius: 20, fontWeight: 700, fontSize: 18,
      color, background: bg, border: `1.5px solid ${color}`,
    }}>
      <Star size={16} /> {score}
    </span>
  )
}

function ProgressBar({ score }: { score: number }) {
  const color = score >= 76 ? 'var(--success)' : score >= 51 ? 'var(--warning)' : 'var(--danger)'
  return (
    <div style={{ width: '100%', height: 8, borderRadius: 4, background: 'var(--border)', overflow: 'hidden' }}>
      <div style={{ width: `${score}%`, height: '100%', borderRadius: 4, background: color, transition: 'width 0.6s ease' }} />
    </div>
  )
}

function TabButton({ active, onClick, children, icon }: { active: boolean; onClick: () => void; children: React.ReactNode; icon?: React.ReactNode }) {
  return (
    <button onClick={onClick} style={{
      display: 'flex', alignItems: 'center', gap: 8,
      padding: '10px 20px', border: 'none', borderRadius: 'var(--radius-md)',
      cursor: 'pointer', fontWeight: active ? 600 : 400, fontSize: 14,
      background: active ? 'var(--accent-primary)' : 'transparent',
      color: active ? '#fff' : 'var(--text-secondary)', transition: 'all 0.2s',
    }}>
      {icon}{children}
    </button>
  )
}

function LangButton({ lang, active, onClick, disabled }: { lang: Lang; active: boolean; onClick: () => void; disabled?: boolean }) {
  return (
    <button onClick={onClick} disabled={disabled} style={{
      padding: '8px 16px', border: `1.5px solid ${active ? 'var(--accent-primary)' : 'var(--border)'}`,
      borderRadius: 'var(--radius-sm)', cursor: disabled ? 'not-allowed' : 'pointer',
      background: active ? 'var(--accent-primary)' : disabled ? 'var(--bg-secondary)' : 'var(--bg-card)',
      color: active ? '#fff' : disabled ? 'var(--text-muted)' : 'var(--text-primary)',
      fontWeight: active ? 600 : 400, fontSize: 13, opacity: disabled ? 0.5 : 1, transition: 'all 0.2s',
    }}>
      {LANG_LABELS[lang].flag} {LANG_LABELS[lang].uz}
    </button>
  )
}

function FileUploadArea({ onFile, fileName, onClear, accept = '.txt,.docx' }: {
  onFile: (f: File) => void; fileName?: string; onClear: () => void; accept?: string
}) {
  const ref = useRef<HTMLInputElement>(null)
  return (
    <div onClick={() => !fileName && ref.current?.click()} style={{
      border: `2px dashed ${fileName ? 'var(--success)' : 'var(--border)'}`,
      borderRadius: 'var(--radius-md)', padding: '16px 20px',
      cursor: fileName ? 'default' : 'pointer', textAlign: 'center',
      background: fileName ? 'var(--success-bg)' : 'var(--bg-secondary)', transition: 'all 0.2s',
    }}>
      <input ref={ref} type="file" accept={accept} hidden
        onChange={(e) => { if (e.target.files?.[0]) onFile(e.target.files[0]); e.target.value = '' }} />
      {fileName ? (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
          <FileText size={16} style={{ color: 'var(--success)' }} />
          <span style={{ fontWeight: 500, color: 'var(--success)' }}>{fileName}</span>
          <button onClick={(e) => { e.stopPropagation(); onClear() }}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 2 }}>
            <X size={14} />
          </button>
        </div>
      ) : (
        <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>
          <Upload size={20} style={{ marginBottom: 4 }} /><div>Fayl yuklash (.txt, .docx)</div>
        </div>
      )}
    </div>
  )
}

function ActionButton({ onClick, loading, children, icon }: {
  onClick: () => void; loading: boolean; children: React.ReactNode; icon?: React.ReactNode
}) {
  return (
    <button onClick={onClick} disabled={loading} style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
      width: '100%', padding: '14px 24px', border: 'none',
      borderRadius: 'var(--radius-md)', cursor: loading ? 'wait' : 'pointer',
      background: loading ? 'var(--text-muted)' : 'var(--accent-primary)',
      color: '#fff', fontWeight: 600, fontSize: 15,
      boxShadow: 'var(--shadow-md)', transition: 'all 0.2s',
    }}>
      {loading ? <Loader2 size={18} className="spin" /> : icon}{children}
    </button>
  )
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}

function downloadText(text: string, filename: string) {
  downloadBlob(new Blob([text], { type: 'text/plain;charset=utf-8' }), filename)
}

// ═══════════════════════════════════════════════════
// Markdown renderer (lightweight, no external deps)
// ═══════════════════════════════════════════════════

function renderMarkdown(md: string): string {
  let html = md
    // Escape HTML
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  // Headings
  html = html.replace(/^#### (.+)$/gm, '<h4 style="font-size:15px;font-weight:700;margin:12px 0 6px">$1</h4>')
  html = html.replace(/^### (.+)$/gm, '<h3 style="font-size:16px;font-weight:700;margin:14px 0 6px">$1</h3>')
  html = html.replace(/^## (.+)$/gm, '<h2 style="font-size:17px;font-weight:700;margin:16px 0 8px">$1</h2>')
  html = html.replace(/^# (.+)$/gm, '<h1 style="font-size:19px;font-weight:700;margin:18px 0 8px">$1</h1>')
  // Bold + italic
  html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>')
  // Tables: detect | rows and wrap in table
  const lines = html.split('\n')
  const result: string[] = []
  let inTable = false
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()
    if (line.startsWith('|') && line.endsWith('|')) {
      if (!inTable) { result.push('<table style="border-collapse:collapse;width:100%;margin:8px 0;font-size:13px">'); inTable = true }
      if (line.replace(/[|\-\s]/g, '') === '') continue // skip separator row
      const cells = line.split('|').filter(c => c.trim() !== '')
      const isHeader = i + 1 < lines.length && lines[i + 1].trim().replace(/[|\-\s:]/g, '') === ''
      const tag = isHeader ? 'th' : 'td'
      const style = isHeader
        ? 'padding:6px 10px;border:1px solid #d4c5b0;background:#f5efe8;font-weight:600;text-align:left'
        : 'padding:6px 10px;border:1px solid #e5ddd3;text-align:left'
      result.push('<tr>' + cells.map(c => `<${tag} style="${style}">${c.trim()}</${tag}>`).join('') + '</tr>')
    } else {
      if (inTable) { result.push('</table>'); inTable = false }
      // List items
      if (line.startsWith('- ')) {
        result.push(`<div style="padding-left:16px;margin:2px 0">\u2022 ${line.slice(2)}</div>`)
      } else if (/^\d+\.\s/.test(line)) {
        result.push(`<div style="padding-left:16px;margin:2px 0">${line}</div>`)
      } else if (line === '') {
        result.push('<div style="height:8px"></div>')
      } else {
        result.push(`<div style="margin:3px 0;line-height:1.7">${line}</div>`)
      }
    }
  }
  if (inTable) result.push('</table>')
  return result.join('\n')
}

function MarkdownView({ text }: { text: string }) {
  return (
    <div
      style={{ fontSize: 14, color: 'var(--text-primary)' }}
      dangerouslySetInnerHTML={{ __html: renderMarkdown(text) }}
    />
  )
}

// ═══════════════════════════════════════════════════
// Quality Report Generator
// ═══════════════════════════════════════════════════

function generateQualityReport(result: QualityResult, type: 'translation' | 'edit'): string {
  const lines: string[] = []
  lines.push(`# SIFAT TEKSHIRUV HISOBOTI`)
  lines.push(``)
  lines.push(`**Turi:** ${type === 'translation' ? 'Tarjima sifati' : 'Tahrir sifati'}`)
  lines.push(`**Sana:** ${new Date().toLocaleDateString('uz-UZ')}`)
  lines.push(`**Umumiy ball:** ${result.umumiy_ball || 0} / 100`)
  lines.push(``)
  lines.push(`---`)
  lines.push(``)

  if (type === 'translation') {
    const cats = [
      { key: 'terminologiya', label: 'TERMINOLOGIYA' },
      { key: 'toliqligi', label: "TO'LIQLIGI" },
      { key: 'grammatika', label: 'GRAMMATIKA' },
      { key: 'uslub', label: 'USLUB' },
    ]
    cats.forEach((cat, i) => {
      const data = result[cat.key]
      if (!data) return
      lines.push(`## ${i + 1}. ${cat.label} — ${data.ball || 0}/100`)
      lines.push(``)
      if (data.muammolar?.length > 0) {
        lines.push(`**Muammolar:**`)
        data.muammolar.forEach((m: string, j: number) => lines.push(`${j + 1}. ${m}`))
        lines.push(``)
      }
      if (data.tavsiyalar?.length > 0) {
        lines.push(`**Tavsiyalar:**`)
        data.tavsiyalar.forEach((t: string, j: number) => lines.push(`${j + 1}. ${t}`))
        lines.push(``)
      }
      lines.push(`---`)
      lines.push(``)
    })
  } else {
    const cats = [
      { key: 'ilmiy_aniqlik', label: 'ILMIY ANIQLIK' },
      { key: 'ravonlik', label: 'RAVONLIK' },
      { key: 'izchillik', label: 'IZCHILLIK' },
      { key: 'farmatsevtik_standart', label: 'FARMATSEVTIK STANDART' },
    ]
    cats.forEach((cat, i) => {
      const data = result[cat.key]
      if (!data) return
      lines.push(`## ${i + 1}. ${cat.label} — ${data.ball || 0}/100`)
      lines.push(``)
      if (data.izohlar?.length > 0) {
        lines.push(`**Izohlar:**`)
        data.izohlar.forEach((m: string, j: number) => lines.push(`${j + 1}. ${m}`))
        lines.push(``)
      }
      lines.push(`---`)
      lines.push(``)
    })
  }

  if (result.xulosa) {
    lines.push(`## XULOSA`)
    lines.push(``)
    lines.push(result.xulosa)
    lines.push(``)
  }

  if (result.ijobiy_jihatlar?.length > 0) {
    lines.push(`## IJOBIY JIHATLAR`)
    lines.push(``)
    result.ijobiy_jihatlar.forEach((j: string, i: number) => lines.push(`${i + 1}. ${j}`))
    lines.push(``)
  }

  if (result.yaxshilanishlar?.length > 0) {
    lines.push(`## YAXSHILANISHLAR`)
    lines.push(``)
    result.yaxshilanishlar.forEach((y: string, i: number) => lines.push(`${i + 1}. ${y}`))
    lines.push(``)
  }

  lines.push(`---`)
  lines.push(`*Pharma Expert AI — pharmtech.info*`)

  return lines.join('\n')
}

function ReportDownload({ result, type }: { result: QualityResult; type: 'translation' | 'edit' }) {
  const [exporting, setExporting] = useState('')
  const report = generateQualityReport(result, type)

  const doExport = async (fmt: string) => {
    setExporting(fmt)
    try {
      if (fmt === 'txt') {
        downloadText(report, `hisobot_${type}.txt`)
      } else if (fmt === 'docx') {
        const blob = await api.assistant2.textToDocx(report, `Sifat hisoboti (${type})`)
        downloadBlob(blob, `hisobot_${type}.docx`)
      } else if (fmt === 'pdf') {
        const blob = await api.assistant2.exportPdf(report, 'uz', `Sifat hisoboti (${type})`)
        downloadBlob(blob, `hisobot_${type}.pdf`)
      }
    } catch (e: any) { alert(`Export xatoligi: ${e.message}`) }
    finally { setExporting('') }
  }

  return (
    <div style={{ display: 'flex', gap: 6, marginTop: 12, justifyContent: 'center' }}>
      {[{ f: 'docx', l: 'DOCX' }, { f: 'pdf', l: 'PDF' }, { f: 'txt', l: 'TXT' }].map(({ f, l }) => (
        <button key={f} onClick={() => doExport(f)} disabled={!!exporting}
          style={{
            display: 'flex', alignItems: 'center', gap: 4,
            padding: '8px 14px', border: '1px solid var(--border)',
            borderRadius: 'var(--radius-sm)', background: 'var(--bg-card)',
            cursor: exporting ? 'wait' : 'pointer', fontSize: 12, fontWeight: 600,
            color: 'var(--text-secondary)',
          }}>
          {exporting === f ? <Loader2 size={12} className="spin" /> : <Download size={12} />}
          Hisobot ({l})
        </button>
      ))}
    </div>
  )
}

// ═══════════════════════════════════════════════════
// Export Menu
// ═══════════════════════════════════════════════════

function ExportMenu({ text, lang, onDocxBlob }: { text: string; lang: string; onDocxBlob?: Blob | null }) {
  const [open, setOpen] = useState(false)
  const [exporting, setExporting] = useState('')

  const doExport = async (format: string) => {
    setExporting(format)
    try {
      if (format === 'txt') {
        downloadText(text, `natija_${lang}.txt`)
      } else if (format === 'docx') {
        if (onDocxBlob) {
          downloadBlob(onDocxBlob, `natija_${lang}.docx`)
        } else {
          const blob = await api.assistant2.textToDocx(text, `Farmatsevtik matn (${lang})`)
          downloadBlob(blob, `natija_${lang}.docx`)
        }
      } else if (format === 'pdf') {
        const blob = await api.assistant2.exportPdf(text, lang, `Farmatsevtik matn (${lang})`)
        downloadBlob(blob, `natija_${lang}.pdf`)
      }
    } catch (e: any) {
      alert(`Export xatoligi: ${e.message}`)
    } finally {
      setExporting('')
      setOpen(false)
    }
  }

  return (
    <div style={{ position: 'relative', display: 'inline-block' }}>
      <button onClick={() => setOpen(!open)} style={{
        display: 'flex', alignItems: 'center', gap: 4,
        padding: '6px 12px', border: '1px solid var(--border)',
        borderRadius: 'var(--radius-sm)', background: 'var(--bg-card)',
        cursor: 'pointer', fontSize: 12, color: 'var(--text-secondary)',
      }}>
        <FileDown size={13} /> Yuklab olish <ChevronDown size={12} />
      </button>
      {open && (
        <div style={{
          position: 'absolute', top: '100%', right: 0, marginTop: 4, zIndex: 10,
          background: 'var(--bg-card)', border: '1px solid var(--border)',
          borderRadius: 'var(--radius-sm)', boxShadow: 'var(--shadow-md)',
          minWidth: 140, overflow: 'hidden',
        }}>
          {[
            { fmt: 'txt', label: '.txt (matn)' },
            { fmt: 'docx', label: '.docx (Word)' },
            { fmt: 'pdf', label: '.pdf (PDF)' },
          ].map(({ fmt, label }) => (
            <button key={fmt} onClick={() => doExport(fmt)} disabled={!!exporting} style={{
              display: 'flex', alignItems: 'center', gap: 6, width: '100%',
              padding: '8px 12px', border: 'none', background: 'transparent',
              cursor: 'pointer', fontSize: 13, color: 'var(--text-primary)',
              borderBottom: '1px solid var(--border)',
            }}>
              {exporting === fmt ? <Loader2 size={12} className="spin" /> : <Download size={12} />} {label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// ═══════════════════════════════════════════════════
// Teach Modal
// ═══════════════════════════════════════════════════

function TeachModal({ aiText, context, lang, onClose }: {
  aiText: string; context: string; lang: string; onClose: () => void
}) {
  const [correct, setCorrect] = useState(aiText)
  const [errorType, setErrorType] = useState('terminology')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  const doSave = async () => {
    if (correct.trim() === aiText.trim()) {
      alert("Tuzatilgan matn AI natijasidan farq qilishi kerak")
      return
    }
    setSaving(true)
    try {
      await api.assistant2.learn(aiText, correct, errorType, context, lang)
      setSaved(true)
      setTimeout(onClose, 1500)
    } catch (e: any) {
      alert(`Xatolik: ${e.message}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.5)', zIndex: 1000,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }} onClick={onClose}>
      <div style={{
        background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)',
        padding: 24, maxWidth: 700, width: '90%', maxHeight: '80vh', overflowY: 'auto',
        boxShadow: 'var(--shadow-lg)',
      }} onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ margin: 0, fontSize: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
            <GraduationCap size={20} style={{ color: 'var(--accent-primary)' }} />
            AI ni o&apos;qitish
          </h3>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer' }}><X size={18} /></button>
        </div>

        {saved ? (
          <div style={{ textAlign: 'center', padding: 24, color: 'var(--success)' }}>
            <CheckCircle size={40} style={{ marginBottom: 8 }} />
            <div style={{ fontWeight: 600 }}>Saqlandi! AI keyingi safar yaxshiroq ishlaydi.</div>
          </div>
        ) : (
          <>
            <div style={{ marginBottom: 12 }}>
              <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
                Xato turi
              </label>
              <select value={errorType} onChange={(e) => setErrorType(e.target.value)} style={{
                padding: '8px 12px', borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border)', background: 'var(--bg-secondary)',
                fontSize: 13, color: 'var(--text-primary)', width: '100%',
              }}>
                {ERROR_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--danger)', display: 'block', marginBottom: 6 }}>
                  AI natijasi (xato)
                </label>
                <div style={{
                  padding: 12, borderRadius: 'var(--radius-sm)', background: 'var(--danger-bg)',
                  fontSize: 13, lineHeight: 1.6, maxHeight: 200, overflowY: 'auto', whiteSpace: 'pre-wrap',
                }}>{aiText}</div>
              </div>
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--success)', display: 'block', marginBottom: 6 }}>
                  To&apos;g&apos;ri variant
                </label>
                <textarea value={correct} onChange={(e) => setCorrect(e.target.value)} rows={6} style={{
                  width: '100%', padding: 12, borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--success)', background: 'var(--success-bg)',
                  fontSize: 13, resize: 'vertical', fontFamily: 'inherit', outline: 'none',
                  color: 'var(--text-primary)',
                }} />
              </div>
            </div>

            <button onClick={doSave} disabled={saving} style={{
              width: '100%', padding: '12px 20px', border: 'none',
              borderRadius: 'var(--radius-md)', cursor: saving ? 'wait' : 'pointer',
              background: 'var(--accent-primary)', color: '#fff', fontWeight: 600,
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
            }}>
              {saving ? <Loader2 size={16} className="spin" /> : <GraduationCap size={16} />}
              {saving ? 'Saqlanmoqda...' : "O'qitish"}
            </button>
          </>
        )}
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════
// Quality Result Displays
// ═══════════════════════════════════════════════════

function TranslationQualityDisplay({ result }: { result: QualityResult }) {
  const categories = [
    { key: 'terminologiya', label: 'Terminologiya', icon: '📚' },
    { key: 'toliqligi', label: "To'liqligi", icon: '📋' },
    { key: 'grammatika', label: 'Grammatika', icon: '✏️' },
    { key: 'uslub', label: 'Uslub', icon: '🎯' },
  ]
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 8 }}>Umumiy ball</div>
        <ScoreBadge score={result.umumiy_ball || 0} />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        {categories.map(cat => {
          const data = result[cat.key]
          if (!data) return null
          return (
            <div key={cat.key} style={{ background: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', padding: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6, fontSize: 13, fontWeight: 600 }}>
                <span>{cat.icon}</span> {cat.label}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <ProgressBar score={data.ball || 0} />
                <span style={{ fontWeight: 700, fontSize: 14, minWidth: 28 }}>{data.ball || 0}</span>
              </div>
              {data.muammolar?.length > 0 && (
                <ul style={{ margin: 0, paddingLeft: 16, fontSize: 12, color: 'var(--danger)' }}>
                  {data.muammolar.map((m: string, i: number) => <li key={i}>{m}</li>)}
                </ul>
              )}
              {data.tavsiyalar?.length > 0 && (
                <ul style={{ margin: '4px 0 0', paddingLeft: 16, fontSize: 12, color: 'var(--info)' }}>
                  {data.tavsiyalar.map((t: string, i: number) => <li key={i}>{t}</li>)}
                </ul>
              )}
            </div>
          )
        })}
      </div>
      {result.xulosa && (
        <div style={{ background: 'var(--info-bg)', borderRadius: 'var(--radius-sm)', padding: 12, fontSize: 13 }}>
          <strong>Xulosa:</strong> {result.xulosa}
        </div>
      )}
      {result.ijobiy_jihatlar?.length > 0 && (
        <div style={{ background: 'var(--success-bg)', borderRadius: 'var(--radius-sm)', padding: 12, fontSize: 13 }}>
          <strong style={{ color: 'var(--success)' }}>Ijobiy jihatlar:</strong>
          <ul style={{ margin: '4px 0 0', paddingLeft: 16 }}>
            {result.ijobiy_jihatlar.map((j: string, i: number) => <li key={i}>{j}</li>)}
          </ul>
        </div>
      )}
    </div>
  )
}

function EditQualityDisplay({ result }: { result: QualityResult }) {
  const categories = [
    { key: 'ilmiy_aniqlik', label: 'Ilmiy aniqlik', icon: '🔬' },
    { key: 'ravonlik', label: 'Ravonlik', icon: '📖' },
    { key: 'izchillik', label: 'Izchillik', icon: '🔗' },
    { key: 'farmatsevtik_standart', label: 'Farm. standart', icon: '💊' },
  ]
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 8 }}>Umumiy ball</div>
        <ScoreBadge score={result.umumiy_ball || 0} />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        {categories.map(cat => {
          const data = result[cat.key]
          if (!data) return null
          return (
            <div key={cat.key} style={{ background: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', padding: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6, fontSize: 13, fontWeight: 600 }}>
                <span>{cat.icon}</span> {cat.label}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <ProgressBar score={data.ball || 0} />
                <span style={{ fontWeight: 700, fontSize: 14, minWidth: 28 }}>{data.ball || 0}</span>
              </div>
              {data.izohlar?.length > 0 && (
                <ul style={{ margin: 0, paddingLeft: 16, fontSize: 12, color: 'var(--text-secondary)' }}>
                  {data.izohlar.map((m: string, i: number) => <li key={i}>{m}</li>)}
                </ul>
              )}
            </div>
          )
        })}
      </div>
      {result.xulosa && (
        <div style={{ background: 'var(--info-bg)', borderRadius: 'var(--radius-sm)', padding: 12, fontSize: 13 }}>
          <strong>Xulosa:</strong> {result.xulosa}
        </div>
      )}
      {result.yaxshilanishlar?.length > 0 && (
        <div style={{ background: 'var(--warning-bg)', borderRadius: 'var(--radius-sm)', padding: 12, fontSize: 13 }}>
          <strong style={{ color: 'var(--warning)' }}>Yaxshilanishlar:</strong>
          <ul style={{ margin: '4px 0 0', paddingLeft: 16 }}>
            {result.yaxshilanishlar.map((y: string, i: number) => <li key={i}>{y}</li>)}
          </ul>
        </div>
      )}
    </div>
  )
}

// ═══════════════════════════════════════════════════
// Main Component
// ═══════════════════════════════════════════════════

export default function Assistant2Page() {
  const { token } = useAuth()

  // Tab state
  const [mainTab, setMainTab] = useState<MainTab>('create')
  const [createTab, setCreateTab] = useState<CreateTab>('translate')
  const [checkTab, setCheckTab] = useState<CheckTab>('translation')

  // ── Translation state ──
  const [trSourceLang, setTrSourceLang] = useState<Lang>('uz')
  const [trTargetLangs, setTrTargetLangs] = useState<Lang[]>(['ru', 'en'])
  const [trText, setTrText] = useState('')
  const [trFile, setTrFile] = useState<string>('')
  const [trDocxFile, setTrDocxFile] = useState<File | null>(null)
  const [trLoading, setTrLoading] = useState(false)
  const [trResults, setTrResults] = useState<Record<string, string> | null>(null)
  const [trResultDocx, setTrResultDocx] = useState<Record<string, Blob> | null>(null)
  const [trError, setTrError] = useState('')
  const [trViewMode, setTrViewMode] = useState<'formatted' | 'text'>('formatted')

  // ── Edit state ──
  const [edLang, setEdLang] = useState<Lang>('uz')
  const [edText, setEdText] = useState('')
  const [edFile, setEdFile] = useState<string>('')
  const [edDocxFile, setEdDocxFile] = useState<File | null>(null)
  const [edLoading, setEdLoading] = useState(false)
  const [edResult, setEdResult] = useState<string | null>(null)
  const [edResultDocx, setEdResultDocx] = useState<Blob | null>(null)
  const [edError, setEdError] = useState('')

  // ── Check Translation state ──
  const [ctOriginal, setCtOriginal] = useState('')
  const [ctTranslation, setCtTranslation] = useState('')
  const [ctOrigFile, setCtOrigFile] = useState<string>('')
  const [ctTrFile, setCtTrFile] = useState<string>('')
  const [ctSourceLang, setCtSourceLang] = useState<Lang>('en')
  const [ctTargetLang, setCtTargetLang] = useState<Lang>('uz')
  const [ctLoading, setCtLoading] = useState(false)
  const [ctResult, setCtResult] = useState<QualityResult | null>(null)
  const [ctError, setCtError] = useState('')

  // ── Check Edit state ──
  const [ceOriginal, setCeOriginal] = useState('')
  const [ceEdited, setCeEdited] = useState('')
  const [ceOrigFile, setCeOrigFile] = useState<string>('')
  const [ceEdFile, setCeEdFile] = useState<string>('')
  const [ceLang, setCeLang] = useState<Lang>('uz')
  const [ceLoading, setCeLoading] = useState(false)
  const [ceResult, setCeResult] = useState<QualityResult | null>(null)
  const [ceError, setCeError] = useState('')

  // ── Teach modal ──
  const [teachData, setTeachData] = useState<{ text: string; context: string; lang: string } | null>(null)

  // ── Linguistic analysis (Izohli/Munozarali/Qisqartmalar) ──
  const [lingLoading, setLingLoading] = useState(false)
  const [lingProgress, setLingProgress] = useState(0)
  const [lingPreview, setLingPreview] = useState<{ category: string; results: any[] } | null>(null)
  const [lingError, setLingError] = useState('')

  const doLinguisticAnalysis = async (category: string) => {
    const text = trText || edText
    if (!text || text.trim().length < 10) { alert('Matn juda qisqa'); return }
    setLingLoading(true); setLingProgress(0); setLingError(''); setLingPreview(null)
    const interval = setInterval(() => setLingProgress(p => p < 90 ? p + Math.random() * 8 : p), 400)
    try {
      const res = await api.linguistic.analyze({ text, category, source_lang: trSourceLang === 'uz' ? 'Uzbek' : trSourceLang === 'ru' ? 'Russian' : 'English' })
      clearInterval(interval); setLingProgress(100)
      setTimeout(() => { setLingLoading(false); setLingPreview({ category, results: (res as any).results || [] }) }, 500)
    } catch (e: any) {
      clearInterval(interval); setLingLoading(false)
      setLingError(e.message || 'Tahlil xatoligi')
    }
  }

  const saveLinguisticResults = async (saveAll = false) => {
    if (!lingPreview) return
    const itemsToSave = saveAll
      ? lingPreview.results.map((i: any) => ({ ...i, status: 'active' }))
      : lingPreview.results.filter((i: any) => !i.is_duplicate).map((i: any) => ({ ...i, status: 'active' }))
    if (itemsToSave.length === 0) { alert('Saqlash uchun element yo\'q'); setLingPreview(null); return }
    try {
      const res = await api.linguistic.save({ category: lingPreview.category, items: itemsToSave, text_id: '' })
      alert(`${itemsToSave.length} ta element bazaga saqlandi! (${(res as any).count || itemsToSave.length})`)
      setLingPreview(null)
    } catch (e: any) {
      alert(`Saqlashda xatolik: ${e?.message || e?.detail || 'Noma\'lum xato'}`)
    }
  }

  // ── File upload helper ──
  const handleFileUpload = useCallback(async (
    file: File,
    setText: (s: string) => void,
    setFileName: (s: string) => void,
    setDocxFile?: (f: File | null) => void
  ) => {
    const isDocx = file.name.toLowerCase().endsWith('.docx')
    if (isDocx && setDocxFile) {
      setDocxFile(file)
      setFileName(file.name)
      // Also extract text for text-based operations
      try {
        const res = await api.assistant2.upload(file)
        setText(res.text || '')
      } catch {
        setText('')
      }
    } else {
      if (setDocxFile) setDocxFile(null)
      try {
        const res = await api.assistant2.upload(file)
        setText(res.text || '')
        setFileName(res.filename || file.name)
      } catch (e: any) {
        setText('')
        setFileName('')
        alert(`Fayl xatoligi: ${e.message || e}`)
      }
    }
  }, [])

  const handleSourceLangChange = (lang: Lang) => {
    setTrSourceLang(lang)
    setTrTargetLangs(ALL_LANGS.filter(l => l !== lang))
  }

  const toggleTargetLang = (lang: Lang) => {
    if (lang === trSourceLang) return
    setTrTargetLangs(prev => prev.includes(lang) ? prev.filter(l => l !== lang) : [...prev, lang])
  }

  // ── Helper: convert text to DOCX blob for WordDocumentViewer ──
  const textToDocxBlob = async (text: string, title?: string): Promise<Blob | null> => {
    try {
      return await api.assistant2.textToDocx(text, title || 'Natija')
    } catch { return null }
  }

  // ── Actions ──
  const doTranslate = async () => {
    if (!trText.trim()) return
    if (trTargetLangs.length === 0) return
    setTrLoading(true); setTrError(''); setTrResults(null); setTrResultDocx(null)
    try {
      const res = await api.assistant2.translate(trText, trSourceLang, trTargetLangs)
      setTrResults(res.translations)
      // Convert results to DOCX for WordDocumentViewer display
      const docxResults: Record<string, Blob> = {}
      for (const [lang, text] of Object.entries(res.translations)) {
        const blob = await textToDocxBlob(text, `Tarjima (${lang})`)
        if (blob) docxResults[lang] = blob
      }
      if (Object.keys(docxResults).length > 0) setTrResultDocx(docxResults)
    } catch (e: any) {
      setTrError(e.detail || e.message || 'Xatolik yuz berdi')
    } finally {
      setTrLoading(false)
    }
  }

  const doEdit = async () => {
    if (!edText.trim()) return
    setEdLoading(true); setEdError(''); setEdResult(null); setEdResultDocx(null)
    try {
      const res = await api.assistant2.edit(edText, edLang)
      setEdResult(res.edited)
      // Convert result to DOCX for display
      const blob = await textToDocxBlob(res.edited, 'Tahrirlangan matn')
      if (blob) setEdResultDocx(blob)
    } catch (e: any) {
      setEdError(e.detail || e.message || 'Xatolik yuz berdi')
    } finally {
      setEdLoading(false)
    }
  }

  const doCheckTranslation = async () => {
    if (!ctOriginal.trim() || !ctTranslation.trim()) return
    setCtLoading(true); setCtError(''); setCtResult(null)
    try {
      const res = await api.assistant2.checkTranslation(ctOriginal, ctTranslation, ctSourceLang, ctTargetLang)
      setCtResult(res.result)
    } catch (e: any) {
      setCtError(e.detail || e.message || 'Xatolik yuz berdi')
    } finally { setCtLoading(false) }
  }

  const doCheckEdit = async () => {
    if (!ceOriginal.trim() || !ceEdited.trim()) return
    setCeLoading(true); setCeError(''); setCeResult(null)
    try {
      const res = await api.assistant2.checkEdit(ceOriginal, ceEdited, ceLang)
      setCeResult(res.result)
    } catch (e: any) {
      setCeError(e.detail || e.message || 'Xatolik yuz berdi')
    } finally { setCeLoading(false) }
  }

  // ═══════════════════════════════════════════════════
  // Render
  // ═══════════════════════════════════════════════════

  const cardStyle = { background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', padding: 24, boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border)' }
  const labelStyle = { fontSize: 13, fontWeight: 600 as const, color: 'var(--text-secondary)', display: 'block' as const, marginBottom: 8 }

  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: '24px 16px' }}>
      <style>{`.spin { animation: spin 1s linear infinite; } @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>

      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
          Farmatsevtik AI Assistent
        </h1>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: '4px 0 0' }}>
          Tarjima, ilmiy tahrir va sifat nazorati — Davlat farmakopeyasi uslubida
        </p>
      </div>

      {/* Main Tabs */}
      <div style={{ display: 'flex', gap: 4, padding: 4, background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', marginBottom: 20 }}>
        <TabButton active={mainTab === 'create'} onClick={() => setMainTab('create')} icon={<FileEdit size={16} />}>
          Matn ishlab chiqish
        </TabButton>
        <TabButton active={mainTab === 'check'} onClick={() => setMainTab('check')} icon={<CheckCircle size={16} />}>
          Tekshirish
        </TabButton>
      </div>

      {/* Linguistic analysis buttons */}
      {(trText || edText) && (
        <div style={{
          display: 'flex', gap: 6, marginBottom: 16, padding: '8px 12px',
          background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)',
          alignItems: 'center',
        }}>
          <span style={{ fontSize: 12, color: 'var(--text-muted)', marginRight: 4, fontWeight: 600 }}>Tahlil:</span>
          {[
            { cat: 'annotated', label: 'Izohli', icon: '📚' },
            { cat: 'disputed', label: 'Munozarali', icon: '💬' },
            { cat: 'abbreviations', label: 'Qisqartmalar', icon: '#' },
          ].map(b => (
            <button key={b.cat} onClick={() => doLinguisticAnalysis(b.cat)} disabled={lingLoading}
              style={{
                display: 'flex', alignItems: 'center', gap: 4, padding: '6px 12px',
                border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)',
                background: 'var(--bg-card)', cursor: lingLoading ? 'wait' : 'pointer',
                fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)',
              }}>
              {b.icon} {b.label}
            </button>
          ))}
        </div>
      )}

      {/* Linguistic loading modal */}
      {lingLoading && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 200, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ background: 'white', borderRadius: 16, padding: '32px 40px', textAlign: 'center', minWidth: 320 }}>
            <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>Mantiqiy tahlil olib borilmoqda...</div>
            <div style={{ width: '100%', height: 8, background: '#E5E7EB', borderRadius: 4, overflow: 'hidden', marginBottom: 8 }}>
              <div style={{ width: `${lingProgress}%`, height: '100%', background: 'var(--green, #10B981)', borderRadius: 4, transition: 'width 0.3s' }} />
            </div>
            <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--green, #10B981)' }}>{Math.round(lingProgress)}%</div>
            <div style={{ fontSize: 12, color: '#6B7280', marginTop: 4 }}>Butun hujjat bo&apos;yicha qidirilmoqda</div>
          </div>
        </div>
      )}

      {/* Linguistic preview modal */}
      {lingPreview && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 200, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          onClick={() => setLingPreview(null)}>
          <div style={{ background: 'white', borderRadius: 16, padding: 24, maxWidth: 700, width: '90%', maxHeight: '80vh', overflowY: 'auto' }}
            onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>
                {lingPreview.category === 'annotated' ? '📚 Izohli terminlar' : lingPreview.category === 'disputed' ? '💬 Munozarali so\'zlar' : '# Qisqartmalar'}
                <span style={{ fontSize: 13, fontWeight: 400, color: 'var(--text-muted)', marginLeft: 8 }}>
                  ({lingPreview.results.length} ta topildi)
                </span>
              </h3>
              <button onClick={() => setLingPreview(null)} style={{ background: 'none', border: 'none', fontSize: 20, cursor: 'pointer' }}>✕</button>
            </div>

            {lingPreview.results.length === 0 ? (
              <div style={{ textAlign: 'center', padding: 24, color: '#94A3B8' }}>Hech narsa topilmadi</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16 }}>
                {lingPreview.results.map((item: any, i: number) => (
                  <div key={i} style={{
                    padding: '10px 12px', borderRadius: 8,
                    background: item.is_duplicate ? '#FEF2F2' : '#F0FDF4',
                    border: `1px solid ${item.is_duplicate ? '#FECACA' : '#BBF7D0'}`,
                    fontSize: 12,
                  }}>
                    {item.is_duplicate && <span style={{ fontSize: 10, color: '#DC2626', fontWeight: 700 }}>BAZADA MAVJUD </span>}
                    {lingPreview.category === 'abbreviations' ? (
                      <div><strong>{item.short_form}</strong> — EN: {item.long_en} | RU: {item.long_ru} | UZ: {item.long_uz}</div>
                    ) : (
                      <div><strong>EN:</strong> {item.en} | <strong>RU:</strong> {item.ru} | <strong>UZ:</strong> {item.uz}</div>
                    )}
                  </div>
                ))}
              </div>
            )}

            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={() => saveLinguisticResults(false)}
                style={{ flex: 1, padding: '10px 16px', background: 'var(--accent-primary)', color: 'white', border: 'none', borderRadius: 8, fontWeight: 700, fontSize: 13, cursor: 'pointer' }}>
                Yangilarini saqlash ({lingPreview.results.filter((i: any) => !i.is_duplicate).length})
              </button>
              <button onClick={() => saveLinguisticResults(true)}
                style={{ padding: '10px 16px', background: '#059669', color: 'white', border: 'none', borderRadius: 8, fontWeight: 700, fontSize: 13, cursor: 'pointer' }}>
                Barchasini saqlash ({lingPreview.results.length})
              </button>
              <button onClick={() => setLingPreview(null)}
                style={{ padding: '10px 16px', background: '#F1F5F9', color: '#64748B', border: '1px solid #E2E8F0', borderRadius: 8, fontWeight: 600, fontSize: 13, cursor: 'pointer' }}>
                Bekor
              </button>
            </div>
          </div>
        </div>
      )}

      {lingError && (
        <div style={{ marginBottom: 12, padding: 10, borderRadius: 'var(--radius-sm)', background: 'var(--danger-bg)', color: 'var(--danger)', fontSize: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
          <AlertCircle size={14} /> {lingError}
        </div>
      )}

      {/* ═══════════════ CREATE MODE ═══════════════ */}
      {mainTab === 'create' && (
        <div>
          <div style={{ display: 'flex', gap: 4, marginBottom: 20 }}>
            <TabButton active={createTab === 'translate'} onClick={() => setCreateTab('translate')} icon={<Languages size={15} />}>Tarjima</TabButton>
            <TabButton active={createTab === 'edit'} onClick={() => setCreateTab('edit')} icon={<FileEdit size={15} />}>Ilmiy tahrir</TabButton>
          </div>

          {/* ── TRANSLATE ── */}
          {createTab === 'translate' && (
            <div style={cardStyle}>
              <div style={{ marginBottom: 16 }}>
                <label style={labelStyle}>Manba til</label>
                <div style={{ display: 'flex', gap: 8 }}>
                  {ALL_LANGS.map(l => <LangButton key={l} lang={l} active={trSourceLang === l} onClick={() => handleSourceLangChange(l)} />)}
                </div>
              </div>

              <div style={{ marginBottom: 16 }}>
                <label style={labelStyle}>Tarjima tillari</label>
                <div style={{ display: 'flex', gap: 8 }}>
                  {ALL_LANGS.map(l => <LangButton key={l} lang={l} active={trTargetLangs.includes(l)} onClick={() => toggleTargetLang(l)} disabled={l === trSourceLang} />)}
                </div>
              </div>

              <div style={{ marginBottom: 16 }}>
                <FileUploadArea onFile={(f) => handleFileUpload(f, setTrText, setTrFile, setTrDocxFile)} fileName={trFile}
                  onClear={() => { setTrFile(''); setTrText(''); setTrDocxFile(null) }} />
              </div>

              {/* DOCX Preview */}
              {trDocxFile && trViewMode === 'formatted' && (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 6 }}>
                    <button onClick={() => setTrViewMode('text')} style={{
                      fontSize: 12, padding: '4px 10px', border: '1px solid var(--border)',
                      borderRadius: 'var(--radius-sm)', background: 'var(--bg-secondary)', cursor: 'pointer',
                      color: 'var(--text-secondary)',
                    }}>Oddiy matn ko&apos;rinishi</button>
                  </div>
                  <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', overflow: 'hidden', maxHeight: 400 }}>
                    <WordDocumentViewer file={trDocxFile} onTextExtracted={setTrText} />
                  </div>
                </div>
              )}

              {/* Text input (shown if no docx or text mode) */}
              {(!trDocxFile || trViewMode === 'text') && (
                <div style={{ marginBottom: 16 }}>
                  {trDocxFile && (
                    <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 6 }}>
                      <button onClick={() => setTrViewMode('formatted')} style={{
                        fontSize: 12, padding: '4px 10px', border: '1px solid var(--border)',
                        borderRadius: 'var(--radius-sm)', background: 'var(--bg-secondary)', cursor: 'pointer',
                        color: 'var(--text-secondary)',
                      }}>Formatlangan ko&apos;rinish</button>
                    </div>
                  )}
                  <textarea value={trText} onChange={(e) => setTrText(e.target.value)}
                    placeholder="Matnni shu yerga kiriting yoki yuqorida fayl yuklang..." rows={8}
                    style={{
                      width: '100%', padding: 14, borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--border)', background: 'var(--bg-secondary)',
                      color: 'var(--text-primary)', fontSize: 14, resize: 'vertical', fontFamily: 'inherit', outline: 'none',
                    }} />
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4, textAlign: 'right' }}>{trText.length} belgi</div>
                </div>
              )}

              <ActionButton onClick={doTranslate} loading={trLoading} icon={<Languages size={18} />}>
                {trLoading ? 'Tarjima qilinmoqda...' : 'Tarjima qilish'}
              </ActionButton>

              {trError && (
                <div style={{ marginTop: 12, padding: 12, borderRadius: 'var(--radius-sm)', background: 'var(--danger-bg)', color: 'var(--danger)', fontSize: 13, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <AlertCircle size={16} /> {trError}
                </div>
              )}

              {/* Results */}
              {trResults && (
                <div style={{ marginTop: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
                  {Object.entries(trResults).map(([lang, text]) => (
                    <div key={lang} style={{ background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', padding: 16, border: '1px solid var(--border)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                        <span style={{ fontWeight: 600, fontSize: 14, display: 'flex', alignItems: 'center', gap: 6 }}>
                          {LANG_LABELS[lang as Lang]?.flag} {LANG_LABELS[lang as Lang]?.uz || lang}
                        </span>
                        <div style={{ display: 'flex', gap: 6 }}>
                          <button onClick={() => setTeachData({ text, context: trText, lang })}
                            title="O'qitish" style={{
                              display: 'flex', alignItems: 'center', gap: 4,
                              padding: '6px 10px', border: '1px solid var(--accent-primary)',
                              borderRadius: 'var(--radius-sm)', background: 'transparent',
                              cursor: 'pointer', fontSize: 12, color: 'var(--accent-primary)',
                            }}>
                            <GraduationCap size={13} /> O&apos;qitish
                          </button>
                          <ExportMenu text={text} lang={lang} onDocxBlob={trResultDocx?.[lang] || null} />
                        </div>
                      </div>

                      {trResultDocx?.[lang] ? (
                        <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', overflow: 'hidden', maxHeight: 400 }}>
                          <WordDocumentViewer file={new File([trResultDocx[lang]], `tarjima_${lang}.docx`)} />
                        </div>
                      ) : (
                        <div style={{ maxHeight: 300, overflowY: 'auto' }}>
                          <MarkdownView text={text} />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ── SCIENTIFIC EDIT ── */}
          {createTab === 'edit' && (
            <div style={cardStyle}>
              <div style={{ marginBottom: 16 }}>
                <label style={labelStyle}>Til</label>
                <div style={{ display: 'flex', gap: 8 }}>
                  {ALL_LANGS.map(l => <LangButton key={l} lang={l} active={edLang === l} onClick={() => setEdLang(l)} />)}
                </div>
              </div>

              <div style={{ marginBottom: 16 }}>
                <FileUploadArea onFile={(f) => handleFileUpload(f, setEdText, setEdFile, setEdDocxFile)} fileName={edFile}
                  onClear={() => { setEdFile(''); setEdText(''); setEdDocxFile(null) }} />
              </div>

              {/* DOCX preview for edit */}
              {edDocxFile && (
                <div style={{ marginBottom: 16, border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', overflow: 'hidden', maxHeight: 350 }}>
                  <WordDocumentViewer file={edDocxFile} onTextExtracted={setEdText} />
                </div>
              )}

              {!edDocxFile && (
                <div style={{ marginBottom: 16 }}>
                  <textarea value={edText} onChange={(e) => setEdText(e.target.value)}
                    placeholder="Tahrir qilish uchun matnni kiriting..." rows={8}
                    style={{
                      width: '100%', padding: 14, borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--border)', background: 'var(--bg-secondary)',
                      color: 'var(--text-primary)', fontSize: 14, resize: 'vertical', fontFamily: 'inherit', outline: 'none',
                    }} />
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4, textAlign: 'right' }}>{edText.length} belgi</div>
                </div>
              )}

              <ActionButton onClick={doEdit} loading={edLoading} icon={<FileEdit size={18} />}>
                {edLoading ? 'Tahrir qilinmoqda...' : 'Tahrir qilish'}
              </ActionButton>

              {edError && (
                <div style={{ marginTop: 12, padding: 12, borderRadius: 'var(--radius-sm)', background: 'var(--danger-bg)', color: 'var(--danger)', fontSize: 13, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <AlertCircle size={16} /> {edError}
                </div>
              )}

              {/* Result — side by side diff */}
              {edResult && (
                <div style={{ marginTop: 20 }}>
                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginBottom: 8 }}>
                    <button onClick={() => setTeachData({ text: edResult, context: edText, lang: edLang })}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 4,
                        padding: '6px 10px', border: '1px solid var(--accent-primary)',
                        borderRadius: 'var(--radius-sm)', background: 'transparent',
                        cursor: 'pointer', fontSize: 12, color: 'var(--accent-primary)',
                      }}>
                      <GraduationCap size={13} /> O&apos;qitish
                    </button>
                    <ExportMenu text={edResult} lang={edLang} onDocxBlob={edResultDocx} />
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                    <div style={{ background: 'var(--danger-bg)', borderRadius: 'var(--radius-sm)', padding: 14 }}>
                      <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--danger)', marginBottom: 8 }}>Asl matn</div>
                      {edDocxFile ? (
                        <div style={{ maxHeight: 350, overflow: 'hidden', borderRadius: 'var(--radius-sm)' }}>
                          <WordDocumentViewer file={edDocxFile} />
                        </div>
                      ) : (
                        <div style={{ maxHeight: 300, overflowY: 'auto' }}><MarkdownView text={edText} /></div>
                      )}
                    </div>
                    <div style={{ background: 'var(--success-bg)', borderRadius: 'var(--radius-sm)', padding: 14 }}>
                      <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--success)', marginBottom: 8 }}>Tahrirlangan</div>
                      {edResultDocx ? (
                        <div style={{ maxHeight: 350, overflow: 'hidden', borderRadius: 'var(--radius-sm)' }}>
                          <WordDocumentViewer file={new File([edResultDocx], 'tahrirlangan.docx')} />
                        </div>
                      ) : (
                        <div style={{ maxHeight: 300, overflowY: 'auto' }}><MarkdownView text={edResult || ''} /></div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ═══════════════ CHECK MODE ═══════════════ */}
      {mainTab === 'check' && (
        <div>
          <div style={{ display: 'flex', gap: 4, marginBottom: 20 }}>
            <TabButton active={checkTab === 'translation'} onClick={() => setCheckTab('translation')} icon={<TrendingUp size={15} />}>Tarjima sifati</TabButton>
            <TabButton active={checkTab === 'edit'} onClick={() => setCheckTab('edit')} icon={<CheckCircle size={15} />}>Tahrir sifati</TabButton>
          </div>

          {/* ── CHECK TRANSLATION ── */}
          {checkTab === 'translation' && (
            <div style={cardStyle}>
              <div style={{ display: 'flex', gap: 20, marginBottom: 16, flexWrap: 'wrap' }}>
                <div>
                  <label style={labelStyle}>Manba til</label>
                  <div style={{ display: 'flex', gap: 8 }}>
                    {ALL_LANGS.map(l => <LangButton key={l} lang={l} active={ctSourceLang === l}
                      onClick={() => { setCtSourceLang(l); if (ctTargetLang === l) setCtTargetLang(ALL_LANGS.find(x => x !== l)!) }} />)}
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'flex-end', paddingBottom: 4 }}>
                  <ChevronRight size={20} style={{ color: 'var(--text-muted)' }} />
                </div>
                <div>
                  <label style={labelStyle}>Maqsad til</label>
                  <div style={{ display: 'flex', gap: 8 }}>
                    {ALL_LANGS.filter(l => l !== ctSourceLang).map(l => <LangButton key={l} lang={l} active={ctTargetLang === l} onClick={() => setCtTargetLang(l)} />)}
                  </div>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
                <div>
                  <label style={labelStyle}>Original matn</label>
                  <FileUploadArea onFile={(f) => handleFileUpload(f, setCtOriginal, setCtOrigFile)} fileName={ctOrigFile}
                    onClear={() => { setCtOrigFile(''); setCtOriginal('') }} />
                  <textarea value={ctOriginal} onChange={(e) => setCtOriginal(e.target.value)}
                    placeholder="Original matnni kiriting..." rows={6}
                    style={{ width: '100%', padding: 12, borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: 13, resize: 'vertical', fontFamily: 'inherit', outline: 'none', marginTop: 8 }} />
                </div>
                <div>
                  <label style={labelStyle}>Tarjima matni</label>
                  <FileUploadArea onFile={(f) => handleFileUpload(f, setCtTranslation, setCtTrFile)} fileName={ctTrFile}
                    onClear={() => { setCtTrFile(''); setCtTranslation('') }} />
                  <textarea value={ctTranslation} onChange={(e) => setCtTranslation(e.target.value)}
                    placeholder="Tarjima matnini kiriting..." rows={6}
                    style={{ width: '100%', padding: 12, borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: 13, resize: 'vertical', fontFamily: 'inherit', outline: 'none', marginTop: 8 }} />
                </div>
              </div>

              <ActionButton onClick={doCheckTranslation} loading={ctLoading} icon={<CheckCircle size={18} />}>
                {ctLoading ? 'Tekshirilmoqda...' : 'Sifatni tekshirish'}
              </ActionButton>

              {ctError && (
                <div style={{ marginTop: 12, padding: 12, borderRadius: 'var(--radius-sm)', background: 'var(--danger-bg)', color: 'var(--danger)', fontSize: 13, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <AlertCircle size={16} /> {ctError}
                </div>
              )}

              {ctResult && <div style={{ marginTop: 20 }}><TranslationQualityDisplay result={ctResult} /><ReportDownload result={ctResult} type="translation" /></div>}
            </div>
          )}

          {/* ── CHECK EDIT ── */}
          {checkTab === 'edit' && (
            <div style={cardStyle}>
              <div style={{ marginBottom: 16 }}>
                <label style={labelStyle}>Til</label>
                <div style={{ display: 'flex', gap: 8 }}>
                  {ALL_LANGS.map(l => <LangButton key={l} lang={l} active={ceLang === l} onClick={() => setCeLang(l)} />)}
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
                <div>
                  <label style={labelStyle}>Dastlabki matn</label>
                  <FileUploadArea onFile={(f) => handleFileUpload(f, setCeOriginal, setCeOrigFile)} fileName={ceOrigFile}
                    onClear={() => { setCeOrigFile(''); setCeOriginal('') }} />
                  <textarea value={ceOriginal} onChange={(e) => setCeOriginal(e.target.value)}
                    placeholder="Dastlabki matnni kiriting..." rows={6}
                    style={{ width: '100%', padding: 12, borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: 13, resize: 'vertical', fontFamily: 'inherit', outline: 'none', marginTop: 8 }} />
                </div>
                <div>
                  <label style={labelStyle}>Tahrirlangan matn</label>
                  <FileUploadArea onFile={(f) => handleFileUpload(f, setCeEdited, setCeEdFile)} fileName={ceEdFile}
                    onClear={() => { setCeEdFile(''); setCeEdited('') }} />
                  <textarea value={ceEdited} onChange={(e) => setCeEdited(e.target.value)}
                    placeholder="Tahrirlangan matnni kiriting..." rows={6}
                    style={{ width: '100%', padding: 12, borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: 13, resize: 'vertical', fontFamily: 'inherit', outline: 'none', marginTop: 8 }} />
                </div>
              </div>

              <ActionButton onClick={doCheckEdit} loading={ceLoading} icon={<CheckCircle size={18} />}>
                {ceLoading ? 'Tekshirilmoqda...' : 'Sifatni tekshirish'}
              </ActionButton>

              {ceError && (
                <div style={{ marginTop: 12, padding: 12, borderRadius: 'var(--radius-sm)', background: 'var(--danger-bg)', color: 'var(--danger)', fontSize: 13, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <AlertCircle size={16} /> {ceError}
                </div>
              )}

              {ceResult && <div style={{ marginTop: 20 }}><EditQualityDisplay result={ceResult} /><ReportDownload result={ceResult} type="edit" /></div>}
            </div>
          )}
        </div>
      )}

      {/* Teach Modal */}
      {teachData && (
        <TeachModal
          aiText={teachData.text}
          context={teachData.context}
          lang={teachData.lang}
          onClose={() => setTeachData(null)}
        />
      )}
    </div>
  )
}
