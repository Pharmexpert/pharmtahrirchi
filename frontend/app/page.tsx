'use client'

import React, { useState } from 'react'
import { Upload, FileText, Loader2, Sparkles, AlertCircle, Hash } from 'lucide-react'
import TableEditor from '../components/TableEditor'

export default function Home() {
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<any[] | null>(null)
  const [filename, setFilename] = useState<string>('')
  const [textId, setTextId] = useState<string>('')
  const [readyMode, setReadyMode] = useState(false)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      setFile(e.target.files[0])
      setError(null)
    }
  }

  const handleUpload = async () => {
    if (!file) return
    if (!textId.trim()) {
      setError('Илтимос, матн рақамини (Text ID) киритинг')
      return
    }
    setLoading(true)
    setError(null)

    const formData = new FormData()
    formData.append('file', file)
    formData.append('text_id', textId.trim())

    try {
      const url = `http://localhost:8000/upload?mode=${readyMode ? 'ready' : 'auto'}`
      const res = await fetch(url, {
        method: 'POST',
        body: formData,
      })
      if (!res.ok) throw new Error('Файлни қайта ишлашда хатолик')
      const result = await res.json()

      // Inject user-provided textId into every row
      const rows = (result.data || []).map((row: any) => ({
        ...row,
        text_id: textId.trim()
      }))

      setData(rows)
      setFilename(result.filename)
    } catch (err: any) {
      setError(err.message || 'Хатолик юз берди')
    } finally {
      setLoading(false)
    }
  }

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    const dropped = e.dataTransfer.files?.[0]
    if (dropped && dropped.name.endsWith('.docx')) {
      setFile(dropped)
      setError(null)
    }
  }

  if (data) {
    return <TableEditor initialData={data} filename={filename} textId={textId} />
  }

  return (
    <main style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #f0f4ff 0%, #f8faff 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '2rem', fontFamily: "'Inter', 'Segoe UI', sans-serif" }}>
      <div style={{ width: '100%', maxWidth: '520px' }}>
        {/* Brand */}
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <div style={{ background: 'linear-gradient(135deg, #3b82f6, #6366f1)', borderRadius: '16px', width: '64px', height: '64px', margin: '0 auto 1rem', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 8px 24px rgba(99,102,241,0.35)' }}>
            <FileText size={32} color="white" />
          </div>
          <h1 style={{ fontSize: '1.6rem', fontWeight: 800, color: '#1e293b', margin: '0 0 0.4rem' }}>Scientific Pharma Editor</h1>
          <p style={{ color: '#64748b', fontSize: '0.9rem', margin: 0 }}>Учтилли (EN, RU, UZ) фармацевтик ҳужжатларни таҳлил қилиш ва таҳрир платформаси</p>
        </div>

        {/* Card */}
        <div style={{ background: 'white', borderRadius: '20px', padding: '2rem', boxShadow: '0 4px 32px rgba(0,0,0,0.08)', border: '1px solid #e2e8f0' }}>
          
          {/* Text ID input */}
          <div style={{ marginBottom: '1.25rem' }}>
            <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 700, color: '#374151', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '6px' }}>
              Матн рақами (Text ID) *
            </label>
            <div style={{ position: 'relative' }}>
              <Hash size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#9ca3af' }} />
              <input
                type="text"
                value={textId}
                onChange={e => { setTextId(e.target.value); setError(null) }}
                placeholder="масалан: 1243, USP-2.9.17, GMP-001 ..."
                style={{ width: '100%', padding: '10px 12px 10px 36px', border: '1.5px solid #e2e8f0', borderRadius: '8px', fontSize: '0.9rem', outline: 'none', boxSizing: 'border-box', transition: 'border-color 0.15s', fontFamily: 'inherit' }}
                onFocus={e => e.target.style.borderColor = '#3b82f6'}
                onBlur={e => e.target.style.borderColor = '#e2e8f0'}
                onKeyDown={e => e.key === 'Enter' && handleUpload()}
              />
            </div>
            <div style={{ fontSize: '0.72rem', color: '#9ca3af', marginTop: '4px' }}>Бу рақам маълумотлар базасида ҳар бир гапга бириктирилади</div>
          </div>

          {/* File drop zone */}
          <div
            onDrop={handleDrop}
            onDragOver={e => e.preventDefault()}
            style={{ border: `2px dashed ${file ? '#3b82f6' : '#cbd5e1'}`, borderRadius: '12px', padding: '1.5rem', marginBottom: '1.25rem', background: file ? '#eff6ff' : '#fafafa', transition: 'all 0.2s', cursor: 'default' }}
          >
            <input type="file" accept=".docx" onChange={handleFileChange} style={{ display: 'none' }} id="file-upload" />
            <label htmlFor="file-upload" style={{ cursor: 'pointer', display: 'block', textAlign: 'center' }}>
              <Upload size={28} color={file ? '#3b82f6' : '#94a3b8'} style={{ margin: '0 auto 8px' }} />
              <div style={{ color: file ? '#2563eb' : '#475569', fontWeight: 600, fontSize: '0.9rem', marginBottom: '4px' }}>
                {file ? file.name : 'DOCX файл танланг ёки тортинг'}
              </div>
              <div style={{ fontSize: '0.78rem', color: '#94a3b8' }}>Формат: .docx (3 устунли жадвал)</div>
            </label>
          </div>

          {error && (
            <div style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#dc2626', padding: '10px 14px', borderRadius: '8px', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem' }}>
              <AlertCircle size={16} /> {error}
            </div>
          )}

          {/* Ready Form Toggle */}
          <div style={{ marginBottom: '1.25rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: '#f8fafc', padding: '10px 14px', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
            <div>
              <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#334155' }}>Тайёр 3-тиллик форма</div>
              <div style={{ fontSize: '0.68rem', color: '#64748b' }}>Алайментсиз, қаторма-қатор юклаш</div>
            </div>
            <label style={{ position: 'relative', display: 'inline-block', width: '40px', height: '22px' }}>
              <input type="checkbox" checked={readyMode} onChange={e => setReadyMode(e.target.checked)} style={{ opacity: 0, width: 0, height: 0 }} />
              <span style={{ position: 'absolute', cursor: 'pointer', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: readyMode ? '#3b82f6' : '#cbd5e1', transition: '.3s', borderRadius: '34px' }}>
                <span style={{ position: 'absolute', content: '""', height: '16px', width: '16px', left: readyMode ? '21px' : '3px', bottom: '3px', backgroundColor: 'white', transition: '.3s', borderRadius: '50%' }}></span>
              </span>
            </label>
          </div>

          <button
            onClick={handleUpload}
            disabled={!file || loading}
            style={{ width: '100%', height: '48px', background: loading ? '#93c5fd' : (!file ? '#e2e8f0' : 'linear-gradient(135deg, #3b82f6, #6366f1)'), color: !file ? '#94a3b8' : 'white', border: 'none', borderRadius: '10px', fontSize: '1rem', fontWeight: 700, cursor: !file || loading ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px', transition: 'all 0.2s', fontFamily: 'inherit' }}
          >
            {loading ? (
              <><Loader2 className="animate-spin" size={20} /> Ишланмоқда...</>
            ) : (
              <><Sparkles size={20} /> Ишлов бериш ва очиш</>
            )}
          </button>
        </div>

        <div style={{ textAlign: 'center', marginTop: '1.5rem', fontSize: '0.75rem', color: '#94a3b8' }}>
          Pharmacopoeia · GMP · ISO стандартлари асосида
        </div>
      </div>
    </main>
  )
}
