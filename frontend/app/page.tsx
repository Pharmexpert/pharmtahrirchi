'use client'

import React, { useState, useEffect } from 'react'
import { Upload, FileText, Loader2, Sparkles, AlertCircle, Hash, BookOpen, User, Clock, ChevronRight, Trash2 } from 'lucide-react'
import Link from 'next/link'
import TableEditor, { RowData } from '../components/TableEditor'
import { useAuth } from '../components/LoginGuard'
import { useSearchParams, useRouter } from 'next/navigation'
import api from '../services/api'

export default function Home() {
  const { user, token } = useAuth()
  const router = useRouter()
  const searchParams = useSearchParams()
  const urlTextId = searchParams.get('text_id')

  // Redirect to dashboard as the landing page (unless opening a specific project)
  useEffect(() => {
    if (token && !urlTextId && typeof window !== 'undefined') {
      const stored = sessionStorage.getItem('editor_data')
      if (!stored) router.replace('/dashboard')
    }
  }, [token, urlTextId, router])
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<RowData[] | null>(null)
  const [filename, setFilename] = useState<string>('')
  const [textId, setTextId] = useState<string>('')
  const [readyMode, setReadyMode] = useState(false)
  const [specialistName, setSpecialistName] = useState<string>(user?.name || '')
  const [specialistList, setSpecialistList] = useState<string[]>([])
  const [projects, setProjects] = useState<any[]>([])
  const [loadingProjects, setLoadingProjects] = useState(true)
  const [showHistory, setShowHistory] = useState(false)
 
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const authHeaders = { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }

  // Fetch specialist list
  useEffect(() => {
    api.specialists.list()
      .then((d: any) => setSpecialistList(d.specialists || []))
      .catch(() => {})
  }, [token])

  // Fetch projects
  useEffect(() => {
    setLoadingProjects(true)
    api.projects.list()
      .then((d: any) => setProjects(d.projects || []))
      .catch(() => {})
      .finally(() => setLoadingProjects(false))
  }, [token])

  // AUTO-OPEN project if text_id param exists in URL
  useEffect(() => {
    if (urlTextId && token && !data) {
      openProject(urlTextId)
    }
  }, [urlTextId, token, data])

  // AUTO-OPEN from Files page (sessionStorage)
  useEffect(() => {
    try {
      const stored = sessionStorage.getItem('editor_data')
      if (stored && !data) {
        const result = JSON.parse(stored)
        sessionStorage.removeItem('editor_data')
        const rows = (result.data || []).map((row: any) => ({
          ...row,
          text_id: result.text_id || '',
          specialist_name: user?.name || ''
        }))
        setData(rows)
        setTextId(result.text_id || '')
        setFilename(result.filename || '')
        if (user?.name) setSpecialistName(user.name)
      }
    } catch {}
  }, [data, user])

  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadPhase, setUploadPhase] = useState('')

  const getPhaseLabel = (pct: number): string => {
    if (pct < 15) return 'Матн тайёрланмоқда...'
    if (pct < 35) return 'AI модел юкланмоқда...'
    if (pct < 60) return 'Терминология таҳлили...'
    if (pct < 80) return 'Таржима солиштирилмоқда...'
    if (pct < 95) return 'Натижалар тўпланмоқда...'
    return 'Тайёр!'
  }
 
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      const f = e.target.files[0]
      const ext = f.name.toLowerCase()
      if (ext.endsWith('.docx') || ext.endsWith('.pdf')) {
        setFile(f)
        setError(null)
        setUploadProgress(0)
      } else {
        setError('Фақат .docx ва .pdf файллар қабул қилинади')
      }
    }
  }
 
  const handleUpload = async () => {
    if (!file) return
    // Auto-fill specialist if empty
    if (!specialistName.trim() && user?.name) {
      setSpecialistName(user.name)
    }
    setLoading(true)
    setError(null)
    setUploadProgress(5)
    setUploadPhase(getPhaseLabel(5))

    // Simulate progressive phases while server processes
    const phaseInterval = setInterval(() => {
      setUploadProgress(prev => {
        if (prev >= 90) { clearInterval(phaseInterval); return prev }
        const next = prev + 1
        setUploadPhase(getPhaseLabel(next))
        return next
      })
    }, 400)
 
    const formData = new FormData()
    formData.append('file', file)
    formData.append('text_id', textId.trim())
 
    try {
      // Auto-generate text_id if not provided
      let finalTextId = textId.trim()
      if (!finalTextId) {
        const specialistShort = (user?.name || 'User').split(' ')[0].slice(0, 6)
        finalTextId = `${specialistShort}_${Date.now()}`
        setTextId(finalTextId)
      }
      const url = `${API_BASE}/api/upload?mode=${readyMode ? 'ready' : 'auto'}&text_id=${encodeURIComponent(finalTextId)}`
      
      const xhr = new XMLHttpRequest()
      
      const uploadPromise = new Promise((resolve, reject) => {
        xhr.upload.addEventListener('progress', (event) => {
          if (event.lengthComputable) {
            const percent = Math.round((event.loaded / event.total) * 90)
            setUploadProgress(percent)
          }
        })
 
        xhr.addEventListener('load', () => {
          clearInterval(phaseInterval)
          if (xhr.status >= 200 && xhr.status < 300) {
            setUploadProgress(100)
            setUploadPhase('Тайёр!')
            resolve(JSON.parse(xhr.responseText))
          } else {
            setUploadPhase('')
            reject(new Error('Файлни қайта ишлашда хатолик'))
          }
        })

        xhr.addEventListener('error', () => { clearInterval(phaseInterval); setUploadPhase(''); reject(new Error('Сарвер билан боғланишда хатолик')) })
        xhr.open('POST', url)
        xhr.setRequestHeader('Authorization', `Bearer ${token}`)
        xhr.send(formData)
      })
 
      const result: any = await uploadPromise
 
      const rows = (result.data || []).map((row: any) => ({
        ...row,
        text_id: textId.trim(),
        specialist_name: specialistName.trim()
      }))
 
      setTimeout(() => {
        setData(rows)
        setFilename(result.filename)
      }, 500)
 
    } catch (err: any) {
      setError(err.message || 'Хатолик юз берди')
      setUploadProgress(0)
    } finally {
      setLoading(false)
    }
  }

  const openProject = async (projectId: string) => {
    if (!projectId) return
    setLoading(true)
    try {
      const result: any = await api.editor.history(projectId)
      const rows = Array.isArray(result) ? result : (result.alignments || [])
      if (rows.length > 0) {
        setData(rows)
        setTextId(projectId)
        setFilename(projectId + '.docx')
      } else {
        setError('Лойиҳа бўш ёки топилмади')
      }
    } catch (err) {
      console.error(err)
      setError('Лойиҳани юклашда хатолик юз берди')
    } finally {
      setLoading(false)
    }
  }

  const deleteProject = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!confirm('Ushbu loyihani o\'chirishni tasdiqlaysizmi?')) return
    try {
      await api.projects.delete(id)
      setProjects(projects.filter(p => p.id !== id))
    } catch (_e) {}
  }
 
  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    const dropped = e.dataTransfer.files?.[0]
    if (dropped && (dropped.name.endsWith('.docx') || dropped.name.endsWith('.pdf'))) {
      setFile(dropped)
      setError(null)
      setUploadProgress(0)
    }
  }
 
  if (data) {
    return <TableEditor initialData={data} filename={filename} textId={textId} />
  }
 
  return (
    <main style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #f0f4ff 0%, #f8faff 100%)', display: 'flex', alignItems: 'flex-start', justifyContent: 'center', padding: '2rem', fontFamily: "'Inter', 'Segoe UI', sans-serif" }}>
      <div style={{ width: '100%', maxWidth: '900px', display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
        
        {/* LEFT: Upload Form */}
        <div style={{ flex: '1 1 400px', minWidth: '380px' }}>
          {/* Brand */}
          <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
            <div style={{ background: 'linear-gradient(135deg, #3b82f6, #6366f1)', borderRadius: '16px', width: '64px', height: '64px', margin: '0 auto 1rem', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 8px 24px rgba(99,102,241,0.35)' }}>
              <FileText size={32} color="white" />
            </div>
            <h1 style={{ fontSize: '1.6rem', fontWeight: 800, color: '#1e293b', margin: '0 0 0.4rem' }}>Scientific Pharma Editor</h1>
            <p style={{ color: '#64748b', fontSize: '0.9rem', margin: '0 0 1rem' }}>Учтилли (EN, RU, UZ) фармацевтик ҳужжатларни таҳлил қилиш ва таҳрир платформаси</p>
            
            <div style={{ display: 'flex', justifyContent: 'center', gap: '8px' }}>
              <Link href="/rules" style={{ color: '#2563eb', fontSize: '0.85rem', fontWeight: 600, textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', background: '#eff6ff', borderRadius: '8px', transition: 'all 0.2s' }}>
                <BookOpen size={16} />
                Correction Rules
              </Link>
              {user?.role === 'admin' && (
                <Link href="/admin" style={{ color: '#6366f1', fontSize: '0.85rem', fontWeight: 600, textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', background: '#eef2ff', borderRadius: '8px', transition: 'all 0.2s', border: '1px solid #c7d2fe' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>🛡️ Admin Panel</span>
                </Link>
              )}
              <button onClick={() => setShowHistory(!showHistory)} style={{ color: '#059669', fontSize: '0.85rem', fontWeight: 600, background: '#ecfdf5', border: 'none', borderRadius: '8px', padding: '6px 12px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Clock size={16} />
                Тарих ({projects.length})
              </button>
            </div>
          </div>
 
          {/* Upload Card */}
          <div style={{ background: 'white', borderRadius: '20px', padding: '2rem', boxShadow: '0 4px 32px rgba(0,0,0,0.08)', border: '1px solid #e2e8f0' }}>
            
            {/* Text ID */}
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
              onClick={() => document.getElementById('file-upload')?.click()}
              style={{ 
                position: 'relative',
                border: `2px dashed ${file ? '#3b82f6' : '#cbd5e1'}`, 
                borderRadius: '12px', 
                padding: '1.5rem', 
                marginBottom: '1.25rem', 
                background: file ? '#eff6ff' : '#fafafa', 
                transition: 'all 0.2s', 
                cursor: 'pointer',
                overflow: 'hidden'
              }}
            >
              {uploadProgress > 0 && uploadProgress < 100 && (
                <div style={{ 
                  position: 'absolute', bottom: 0, left: 0, height: '4px', 
                  width: `${uploadProgress}%`, background: '#10b981', 
                  transition: 'width 0.3s ease-out', zIndex: 5
                }} />
              )}
              
              <input type="file" accept=".docx,.pdf" onChange={handleFileChange} style={{ display: 'none' }} id="file-upload" />
              <div style={{ textAlign: 'center' }}>
                {loading ? (
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px', padding: '8px 0' }}>
                    <div style={{ width: '80%', height: '8px', background: 'rgba(0,0,0,0.08)', borderRadius: '4px', overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${uploadProgress}%`, background: 'linear-gradient(90deg, #B48C64, #C07840)', borderRadius: '4px', transition: 'width 0.3s ease-out' }} />
                    </div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--accent-primary, #B48C64)' }}>{uploadProgress}%</div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary, #6B5744)', fontWeight: 500 }}>{uploadPhase || 'Файл юкланмоқда...'}</div>
                  </div>
                ) : (
                  <>
                    <Upload size={28} color={file ? '#3b82f6' : '#94a3b8'} style={{ margin: '0 auto 8px' }} />
                    <div style={{ color: file ? '#2563eb' : '#475569', fontWeight: 600, fontSize: '0.9rem', marginBottom: '4px' }}>
                      {file ? file.name : 'DOCX файл танланг ёки тортинг'}
                    </div>
                    <div style={{ fontSize: '0.78rem', color: '#94a3b8' }}>Формат: .docx ёки .pdf (3 устунли жадвал ёки бир тилли матн)</div>
                  </>
                )}
              </div>
            </div>

            {error && (
              <div style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#dc2626', padding: '10px 14px', borderRadius: '8px', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem' }}>
                <AlertCircle size={16} /> {error}
              </div>
            )}

            {/* Specialist Name */}
            <div style={{ marginBottom: '1.25rem' }}>
              <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 700, color: '#374151', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '6px' }}>
                Мутахассис исми ва шарифи *
              </label>
              <div style={{ position: 'relative' }}>
                <User size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#9ca3af' }} />
                <input
                  type="text"
                  list="specialist-list"
                  value={specialistName}
                  onChange={e => { setSpecialistName(e.target.value); setError(null) }}
                  placeholder="масалан: Каримов Алишер"
                  style={{ width: '100%', padding: '10px 12px 10px 36px', border: '1.5px solid #e2e8f0', borderRadius: '8px', fontSize: '0.9rem', outline: 'none', boxSizing: 'border-box', transition: 'border-color 0.15s', fontFamily: 'inherit' }}
                  onFocus={e => e.target.style.borderColor = '#3b82f6'}
                  onBlur={e => e.target.style.borderColor = '#e2e8f0'}
                />
                <datalist id="specialist-list">
                  {specialistList.map((name, i) => (
                    <option key={i} value={name} />
                  ))}
                </datalist>
              </div>
            </div>

            {/* Ready Form Toggle */}
            <div style={{ marginBottom: '1.25rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: '#f8fafc', padding: '10px 14px', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
              <div>
                <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#334155' }}>Тайёр 3-тиллик форма</div>
                <div style={{ fontSize: '0.68rem', color: '#64748b' }}>шу ҳолатида юклаш</div>
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

        {/* RIGHT: Project History */}
        {showHistory && (
          <div style={{ flex: '1 1 320px', minWidth: '300px' }}>
            <div style={{ background: 'white', borderRadius: '20px', padding: '1.5rem', boxShadow: '0 4px 32px rgba(0,0,0,0.08)', border: '1px solid #e2e8f0' }}>
              <h3 style={{ margin: '0 0 1rem', fontSize: '1rem', fontWeight: 700, color: '#1e293b', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Clock size={18} /> Олдинги лойиҳалар
              </h3>
              {loadingProjects ? (
                <div style={{ textAlign: 'center', padding: '2rem', color: '#94a3b8' }}>
                  <Loader2 size={24} className="animate-spin" style={{ margin: '0 auto' }} />
                </div>
              ) : projects.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '2rem', color: '#94a3b8', fontSize: '0.85rem' }}>
                  Ҳали лойиҳалар йўқ
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '60vh', overflowY: 'auto' }}>
                  {projects.map((p: any) => (
                    <div 
                      key={p.id}
                      onClick={() => openProject(p.id)}
                      style={{ 
                        padding: '12px 14px', background: '#f8fafc', borderRadius: '10px', 
                        border: '1px solid #e2e8f0', cursor: 'pointer', 
                        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                        transition: 'all 0.2s'
                      }}
                      onMouseEnter={e => { e.currentTarget.style.background = '#eff6ff'; e.currentTarget.style.borderColor = '#93c5fd' }}
                      onMouseLeave={e => { e.currentTarget.style.background = '#f8fafc'; e.currentTarget.style.borderColor = '#e2e8f0' }}
                    >
                      <div>
                        <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#1e293b' }}>{p.id}</div>
                        <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>{p.specialist_name || p.name || ''}</div>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <button 
                          onClick={(e) => deleteProject(p.id, e)}
                          style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8', padding: '4px' }}
                        >
                          <Trash2 size={14} />
                        </button>
                        <ChevronRight size={16} color="#94a3b8" />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </main>
  )
}
