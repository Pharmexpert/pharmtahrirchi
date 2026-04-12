'use client'

import React, { useState, useRef, useCallback } from 'react'
import { useAuth } from '../../components/LoginGuard'
import api from '../../services/api'
import {
  Languages, FileEdit, CheckCircle, Upload, Download, Loader2,
  FileText, X, ChevronRight, AlertCircle, Star, TrendingUp
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

const LANG_LABELS: Record<Lang, { uz: string; ru: string; en: string; flag: string }> = {
  uz: { uz: "O'zbek", ru: 'Узбекский', en: 'Uzbek', flag: '🇺🇿' },
  ru: { uz: 'Rus', ru: 'Русский', en: 'Russian', flag: '🇷🇺' },
  en: { uz: 'Ingliz', ru: 'Английский', en: 'English', flag: '🇬🇧' },
}

const ALL_LANGS: Lang[] = ['uz', 'ru', 'en']

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
    <button
      onClick={onClick}
      style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '10px 20px', border: 'none', borderRadius: 'var(--radius-md)',
        cursor: 'pointer', fontWeight: active ? 600 : 400, fontSize: 14,
        background: active ? 'var(--accent-primary)' : 'transparent',
        color: active ? '#fff' : 'var(--text-secondary)',
        transition: 'all 0.2s',
      }}
    >
      {icon}{children}
    </button>
  )
}

function LangButton({ lang, active, onClick, disabled }: { lang: Lang; active: boolean; onClick: () => void; disabled?: boolean }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        padding: '8px 16px', border: `1.5px solid ${active ? 'var(--accent-primary)' : 'var(--border)'}`,
        borderRadius: 'var(--radius-sm)', cursor: disabled ? 'not-allowed' : 'pointer',
        background: active ? 'var(--accent-primary)' : disabled ? 'var(--bg-secondary)' : 'var(--bg-card)',
        color: active ? '#fff' : disabled ? 'var(--text-muted)' : 'var(--text-primary)',
        fontWeight: active ? 600 : 400, fontSize: 13, opacity: disabled ? 0.5 : 1,
        transition: 'all 0.2s',
      }}
    >
      {LANG_LABELS[lang].flag} {LANG_LABELS[lang].uz}
    </button>
  )
}

function FileUploadArea({ onFile, fileName, onClear, accept = '.txt,.docx' }: {
  onFile: (f: File) => void; fileName?: string; onClear: () => void; accept?: string
}) {
  const ref = useRef<HTMLInputElement>(null)
  return (
    <div
      onClick={() => !fileName && ref.current?.click()}
      style={{
        border: `2px dashed ${fileName ? 'var(--success)' : 'var(--border)'}`,
        borderRadius: 'var(--radius-md)', padding: '16px 20px',
        cursor: fileName ? 'default' : 'pointer', textAlign: 'center',
        background: fileName ? 'var(--success-bg)' : 'var(--bg-secondary)',
        transition: 'all 0.2s',
      }}
    >
      <input
        ref={ref} type="file" accept={accept} hidden
        onChange={(e) => { if (e.target.files?.[0]) onFile(e.target.files[0]); e.target.value = '' }}
      />
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
          <Upload size={20} style={{ marginBottom: 4 }} />
          <div>Fayl yuklash (.txt, .docx)</div>
        </div>
      )}
    </div>
  )
}

function ActionButton({ onClick, loading, children, icon }: {
  onClick: () => void; loading: boolean; children: React.ReactNode; icon?: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
        width: '100%', padding: '14px 24px', border: 'none',
        borderRadius: 'var(--radius-md)', cursor: loading ? 'wait' : 'pointer',
        background: loading ? 'var(--text-muted)' : 'var(--accent-primary)',
        color: '#fff', fontWeight: 600, fontSize: 15,
        boxShadow: 'var(--shadow-md)', transition: 'all 0.2s',
      }}
    >
      {loading ? <Loader2 size={18} className="spin" /> : icon}
      {children}
    </button>
  )
}

function downloadText(text: string, filename: string) {
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}

// ═══════════════════════════════════════════════════
// Quality Result Display
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
        <div style={{ background: 'var(--info-bg)', borderRadius: 'var(--radius-sm)', padding: 12, fontSize: 13, color: 'var(--text-primary)' }}>
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
  const [trLoading, setTrLoading] = useState(false)
  const [trResults, setTrResults] = useState<Record<string, string> | null>(null)
  const [trError, setTrError] = useState('')

  // ── Edit state ──
  const [edLang, setEdLang] = useState<Lang>('uz')
  const [edText, setEdText] = useState('')
  const [edFile, setEdFile] = useState<string>('')
  const [edLoading, setEdLoading] = useState(false)
  const [edResult, setEdResult] = useState<string | null>(null)
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

  // ── File upload helper ──
  const handleFileUpload = useCallback(async (file: File, setText: (s: string) => void, setFileName: (s: string) => void) => {
    try {
      const res = await api.assistant2.upload(file)
      setText(res.text || '')
      setFileName(res.filename || file.name)
    } catch (e: any) {
      setText('')
      setFileName('')
      alert(`Fayl xatoligi: ${e.message || e}`)
    }
  }, [])

  // ── Translation source lang change ──
  const handleSourceLangChange = (lang: Lang) => {
    setTrSourceLang(lang)
    setTrTargetLangs(ALL_LANGS.filter(l => l !== lang))
  }

  const toggleTargetLang = (lang: Lang) => {
    if (lang === trSourceLang) return
    setTrTargetLangs(prev =>
      prev.includes(lang) ? prev.filter(l => l !== lang) : [...prev, lang]
    )
  }

  // ── Actions ──
  const doTranslate = async () => {
    if (!trText.trim()) return
    if (trTargetLangs.length === 0) return
    setTrLoading(true); setTrError(''); setTrResults(null)
    try {
      const res = await api.assistant2.translate(trText, trSourceLang, trTargetLangs)
      setTrResults(res.translations)
    } catch (e: any) {
      setTrError(e.detail || e.message || 'Xatolik yuz berdi')
    } finally {
      setTrLoading(false)
    }
  }

  const doEdit = async () => {
    if (!edText.trim()) return
    setEdLoading(true); setEdError(''); setEdResult(null)
    try {
      const res = await api.assistant2.edit(edText, edLang)
      setEdResult(res.edited)
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
    } finally {
      setCtLoading(false)
    }
  }

  const doCheckEdit = async () => {
    if (!ceOriginal.trim() || !ceEdited.trim()) return
    setCeLoading(true); setCeError(''); setCeResult(null)
    try {
      const res = await api.assistant2.checkEdit(ceOriginal, ceEdited, ceLang)
      setCeResult(res.result)
    } catch (e: any) {
      setCeError(e.detail || e.message || 'Xatolik yuz berdi')
    } finally {
      setCeLoading(false)
    }
  }

  // ═══════════════════════════════════════════════════
  // Render
  // ═══════════════════════════════════════════════════

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '24px 16px' }}>
      {/* Spin animation */}
      <style>{`.spin { animation: spin 1s linear infinite; } @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>

      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
          Farmatsevtik AI Assistent
        </h1>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: '4px 0 0' }}>
          Tarjima, ilmiy tahrir va sifat nazorati
        </p>
      </div>

      {/* Main Tabs */}
      <div style={{
        display: 'flex', gap: 4, padding: 4,
        background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', marginBottom: 20,
      }}>
        <TabButton active={mainTab === 'create'} onClick={() => setMainTab('create')} icon={<FileEdit size={16} />}>
          Matn ishlab chiqish
        </TabButton>
        <TabButton active={mainTab === 'check'} onClick={() => setMainTab('check')} icon={<CheckCircle size={16} />}>
          Tekshirish
        </TabButton>
      </div>

      {/* ═══════════════ CREATE MODE ═══════════════ */}
      {mainTab === 'create' && (
        <div>
          {/* Sub-tabs */}
          <div style={{ display: 'flex', gap: 4, marginBottom: 20 }}>
            <TabButton active={createTab === 'translate'} onClick={() => setCreateTab('translate')} icon={<Languages size={15} />}>
              Tarjima
            </TabButton>
            <TabButton active={createTab === 'edit'} onClick={() => setCreateTab('edit')} icon={<FileEdit size={15} />}>
              Ilmiy tahrir
            </TabButton>
          </div>

          {/* ── TRANSLATE ── */}
          {createTab === 'translate' && (
            <div style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', padding: 24, boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border)' }}>
              {/* Source language */}
              <div style={{ marginBottom: 16 }}>
                <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 8 }}>
                  Manba til
                </label>
                <div style={{ display: 'flex', gap: 8 }}>
                  {ALL_LANGS.map(l => (
                    <LangButton key={l} lang={l} active={trSourceLang === l} onClick={() => handleSourceLangChange(l)} />
                  ))}
                </div>
              </div>

              {/* Target languages */}
              <div style={{ marginBottom: 16 }}>
                <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 8 }}>
                  Tarjima tillari
                </label>
                <div style={{ display: 'flex', gap: 8 }}>
                  {ALL_LANGS.map(l => (
                    <LangButton
                      key={l} lang={l}
                      active={trTargetLangs.includes(l)}
                      onClick={() => toggleTargetLang(l)}
                      disabled={l === trSourceLang}
                    />
                  ))}
                </div>
              </div>

              {/* File upload */}
              <div style={{ marginBottom: 16 }}>
                <FileUploadArea
                  onFile={(f) => handleFileUpload(f, setTrText, setTrFile)}
                  fileName={trFile}
                  onClear={() => { setTrFile(''); setTrText('') }}
                />
              </div>

              {/* Text input */}
              <div style={{ marginBottom: 16 }}>
                <textarea
                  value={trText}
                  onChange={(e) => setTrText(e.target.value)}
                  placeholder="Matnni shu yerga kiriting yoki yuqorida fayl yuklang..."
                  rows={8}
                  style={{
                    width: '100%', padding: 14, borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border)', background: 'var(--bg-secondary)',
                    color: 'var(--text-primary)', fontSize: 14, resize: 'vertical',
                    fontFamily: 'inherit', outline: 'none',
                  }}
                />
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4, textAlign: 'right' }}>
                  {trText.length} belgi
                </div>
              </div>

              {/* Action */}
              <ActionButton onClick={doTranslate} loading={trLoading} icon={<Languages size={18} />}>
                {trLoading ? 'Tarjima qilinmoqda...' : 'Tarjima qilish'}
              </ActionButton>

              {/* Error */}
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
                        <button
                          onClick={() => downloadText(text, `tarjima_${lang}.txt`)}
                          style={{
                            display: 'flex', alignItems: 'center', gap: 4,
                            padding: '6px 12px', border: '1px solid var(--border)',
                            borderRadius: 'var(--radius-sm)', background: 'var(--bg-card)',
                            cursor: 'pointer', fontSize: 12, color: 'var(--text-secondary)',
                          }}
                        >
                          <Download size={13} /> Yuklab olish
                        </button>
                      </div>
                      <div style={{
                        whiteSpace: 'pre-wrap', fontSize: 14, lineHeight: 1.6,
                        color: 'var(--text-primary)', maxHeight: 300, overflowY: 'auto',
                      }}>
                        {text}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ── SCIENTIFIC EDIT ── */}
          {createTab === 'edit' && (
            <div style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', padding: 24, boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border)' }}>
              {/* Language */}
              <div style={{ marginBottom: 16 }}>
                <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 8 }}>
                  Til
                </label>
                <div style={{ display: 'flex', gap: 8 }}>
                  {ALL_LANGS.map(l => (
                    <LangButton key={l} lang={l} active={edLang === l} onClick={() => setEdLang(l)} />
                  ))}
                </div>
              </div>

              {/* File upload */}
              <div style={{ marginBottom: 16 }}>
                <FileUploadArea
                  onFile={(f) => handleFileUpload(f, setEdText, setEdFile)}
                  fileName={edFile}
                  onClear={() => { setEdFile(''); setEdText('') }}
                />
              </div>

              {/* Text input */}
              <div style={{ marginBottom: 16 }}>
                <textarea
                  value={edText}
                  onChange={(e) => setEdText(e.target.value)}
                  placeholder="Tahrir qilish uchun matnni kiriting..."
                  rows={8}
                  style={{
                    width: '100%', padding: 14, borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border)', background: 'var(--bg-secondary)',
                    color: 'var(--text-primary)', fontSize: 14, resize: 'vertical',
                    fontFamily: 'inherit', outline: 'none',
                  }}
                />
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4, textAlign: 'right' }}>
                  {edText.length} belgi
                </div>
              </div>

              {/* Action */}
              <ActionButton onClick={doEdit} loading={edLoading} icon={<FileEdit size={18} />}>
                {edLoading ? 'Tahrir qilinmoqda...' : 'Tahrir qilish'}
              </ActionButton>

              {/* Error */}
              {edError && (
                <div style={{ marginTop: 12, padding: 12, borderRadius: 'var(--radius-sm)', background: 'var(--danger-bg)', color: 'var(--danger)', fontSize: 13, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <AlertCircle size={16} /> {edError}
                </div>
              )}

              {/* Result — side by side diff */}
              {edResult && (
                <div style={{ marginTop: 20 }}>
                  <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 8 }}>
                    <button
                      onClick={() => downloadText(edResult, `tahrir_${edLang}.txt`)}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 4,
                        padding: '6px 12px', border: '1px solid var(--border)',
                        borderRadius: 'var(--radius-sm)', background: 'var(--bg-card)',
                        cursor: 'pointer', fontSize: 12, color: 'var(--text-secondary)',
                      }}
                    >
                      <Download size={13} /> Yuklab olish
                    </button>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                    <div style={{ background: 'var(--danger-bg)', borderRadius: 'var(--radius-sm)', padding: 14 }}>
                      <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--danger)', marginBottom: 8 }}>Asl matn</div>
                      <div style={{ whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.6, maxHeight: 300, overflowY: 'auto' }}>
                        {edText}
                      </div>
                    </div>
                    <div style={{ background: 'var(--success-bg)', borderRadius: 'var(--radius-sm)', padding: 14 }}>
                      <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--success)', marginBottom: 8 }}>Tahrirlangan</div>
                      <div style={{ whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.6, maxHeight: 300, overflowY: 'auto' }}>
                        {edResult}
                      </div>
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
          {/* Sub-tabs */}
          <div style={{ display: 'flex', gap: 4, marginBottom: 20 }}>
            <TabButton active={checkTab === 'translation'} onClick={() => setCheckTab('translation')} icon={<TrendingUp size={15} />}>
              Tarjima sifati
            </TabButton>
            <TabButton active={checkTab === 'edit'} onClick={() => setCheckTab('edit')} icon={<CheckCircle size={15} />}>
              Tahrir sifati
            </TabButton>
          </div>

          {/* ── CHECK TRANSLATION ── */}
          {checkTab === 'translation' && (
            <div style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', padding: 24, boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border)' }}>
              {/* Language pair */}
              <div style={{ display: 'flex', gap: 20, marginBottom: 16, flexWrap: 'wrap' }}>
                <div>
                  <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 8 }}>
                    Manba til
                  </label>
                  <div style={{ display: 'flex', gap: 8 }}>
                    {ALL_LANGS.map(l => (
                      <LangButton key={l} lang={l} active={ctSourceLang === l} onClick={() => { setCtSourceLang(l); if (ctTargetLang === l) setCtTargetLang(ALL_LANGS.find(x => x !== l)!) }} />
                    ))}
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'flex-end', paddingBottom: 4 }}>
                  <ChevronRight size={20} style={{ color: 'var(--text-muted)' }} />
                </div>
                <div>
                  <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 8 }}>
                    Maqsad til
                  </label>
                  <div style={{ display: 'flex', gap: 8 }}>
                    {ALL_LANGS.filter(l => l !== ctSourceLang).map(l => (
                      <LangButton key={l} lang={l} active={ctTargetLang === l} onClick={() => setCtTargetLang(l)} />
                    ))}
                  </div>
                </div>
              </div>

              {/* Two text areas side by side */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
                <div>
                  <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 8 }}>
                    Original matn
                  </label>
                  <FileUploadArea
                    onFile={(f) => handleFileUpload(f, setCtOriginal, setCtOrigFile)}
                    fileName={ctOrigFile}
                    onClear={() => { setCtOrigFile(''); setCtOriginal('') }}
                  />
                  <textarea
                    value={ctOriginal}
                    onChange={(e) => setCtOriginal(e.target.value)}
                    placeholder="Original matnni kiriting..."
                    rows={6}
                    style={{
                      width: '100%', padding: 12, borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--border)', background: 'var(--bg-secondary)',
                      color: 'var(--text-primary)', fontSize: 13, resize: 'vertical',
                      fontFamily: 'inherit', outline: 'none', marginTop: 8,
                    }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 8 }}>
                    Tarjima matni
                  </label>
                  <FileUploadArea
                    onFile={(f) => handleFileUpload(f, setCtTranslation, setCtTrFile)}
                    fileName={ctTrFile}
                    onClear={() => { setCtTrFile(''); setCtTranslation('') }}
                  />
                  <textarea
                    value={ctTranslation}
                    onChange={(e) => setCtTranslation(e.target.value)}
                    placeholder="Tarjima matnini kiriting..."
                    rows={6}
                    style={{
                      width: '100%', padding: 12, borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--border)', background: 'var(--bg-secondary)',
                      color: 'var(--text-primary)', fontSize: 13, resize: 'vertical',
                      fontFamily: 'inherit', outline: 'none', marginTop: 8,
                    }}
                  />
                </div>
              </div>

              {/* Action */}
              <ActionButton onClick={doCheckTranslation} loading={ctLoading} icon={<CheckCircle size={18} />}>
                {ctLoading ? 'Tekshirilmoqda...' : 'Sifatni tekshirish'}
              </ActionButton>

              {/* Error */}
              {ctError && (
                <div style={{ marginTop: 12, padding: 12, borderRadius: 'var(--radius-sm)', background: 'var(--danger-bg)', color: 'var(--danger)', fontSize: 13, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <AlertCircle size={16} /> {ctError}
                </div>
              )}

              {/* Result */}
              {ctResult && (
                <div style={{ marginTop: 20 }}>
                  <TranslationQualityDisplay result={ctResult} />
                </div>
              )}
            </div>
          )}

          {/* ── CHECK EDIT ── */}
          {checkTab === 'edit' && (
            <div style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', padding: 24, boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border)' }}>
              {/* Language */}
              <div style={{ marginBottom: 16 }}>
                <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 8 }}>
                  Til
                </label>
                <div style={{ display: 'flex', gap: 8 }}>
                  {ALL_LANGS.map(l => (
                    <LangButton key={l} lang={l} active={ceLang === l} onClick={() => setCeLang(l)} />
                  ))}
                </div>
              </div>

              {/* Two text areas */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
                <div>
                  <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 8 }}>
                    Dastlabki matn
                  </label>
                  <FileUploadArea
                    onFile={(f) => handleFileUpload(f, setCeOriginal, setCeOrigFile)}
                    fileName={ceOrigFile}
                    onClear={() => { setCeOrigFile(''); setCeOriginal('') }}
                  />
                  <textarea
                    value={ceOriginal}
                    onChange={(e) => setCeOriginal(e.target.value)}
                    placeholder="Dastlabki matnni kiriting..."
                    rows={6}
                    style={{
                      width: '100%', padding: 12, borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--border)', background: 'var(--bg-secondary)',
                      color: 'var(--text-primary)', fontSize: 13, resize: 'vertical',
                      fontFamily: 'inherit', outline: 'none', marginTop: 8,
                    }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 8 }}>
                    Tahrirlangan matn
                  </label>
                  <FileUploadArea
                    onFile={(f) => handleFileUpload(f, setCeEdited, setCeEdFile)}
                    fileName={ceEdFile}
                    onClear={() => { setCeEdFile(''); setCeEdited('') }}
                  />
                  <textarea
                    value={ceEdited}
                    onChange={(e) => setCeEdited(e.target.value)}
                    placeholder="Tahrirlangan matnni kiriting..."
                    rows={6}
                    style={{
                      width: '100%', padding: 12, borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--border)', background: 'var(--bg-secondary)',
                      color: 'var(--text-primary)', fontSize: 13, resize: 'vertical',
                      fontFamily: 'inherit', outline: 'none', marginTop: 8,
                    }}
                  />
                </div>
              </div>

              {/* Action */}
              <ActionButton onClick={doCheckEdit} loading={ceLoading} icon={<CheckCircle size={18} />}>
                {ceLoading ? 'Tekshirilmoqda...' : 'Sifatni tekshirish'}
              </ActionButton>

              {/* Error */}
              {ceError && (
                <div style={{ marginTop: 12, padding: 12, borderRadius: 'var(--radius-sm)', background: 'var(--danger-bg)', color: 'var(--danger)', fontSize: 13, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <AlertCircle size={16} /> {ceError}
                </div>
              )}

              {/* Result */}
              {ceResult && (
                <div style={{ marginTop: 20 }}>
                  <EditQualityDisplay result={ceResult} />
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
