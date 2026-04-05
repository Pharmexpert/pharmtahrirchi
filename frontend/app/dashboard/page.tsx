'use client'

import React, { useState, useEffect, useRef } from 'react'
import { BarChart3, FileText, Database, Users, TrendingUp, BookOpen, MessageSquare, Hash, Upload, FolderOpen, Loader2, Sparkles, ChevronRight, Clock } from 'lucide-react'
import { useAuth } from '../../components/LoginGuard'
import Link from 'next/link'
import { useRouter } from 'next/navigation'

export default function DashboardPage() {
  const { token, user } = useAuth()
  const router = useRouter()
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const [stats, setStats] = useState({
    projects: 0, alignments: 0, rules: 0,
    annotated: 0, disputed: 0, abbreviations: 0, files: 0, synonyms: 0
  })
  const [projects, setProjects] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const fetchData = async () => {
      if (!token) return
      setLoading(true)
      try {
        const headers = { Authorization: `Bearer ${token}` }
        const [statsRes, lingRes, projRes, filesRes] = await Promise.allSettled([
          fetch(`${API_BASE}/api/admin/db-stats`, { headers }),
          fetch(`${API_BASE}/api/linguistic/all`, { headers }),
          fetch(`${API_BASE}/api/projects`, { headers }),
          fetch(`${API_BASE}/api/files`, { headers }),
        ])
        if (statsRes.status === 'fulfilled' && statsRes.value.ok) {
          const d = await statsRes.value.json()
          setStats(prev => ({ 
            ...prev, 
            projects: d.projects || d.counts?.projects || 0,
            rules: d.sayqallash_rules || d.counts?.sayqallash_rules || 0,
            alignments: d.counts?.alignments || 0,
            synonyms: d.synonyms || d.counts?.synonyms || 0
          }))
        }
        if (lingRes.status === 'fulfilled' && lingRes.value.ok) {
          const d = await lingRes.value.json()
          setStats(prev => ({
            ...prev,
            annotated: (d.annotated || []).length,
            disputed: (d.disputed || []).length,
            abbreviations: (d.abbreviations || []).length,
          }))
        }
        if (projRes.status === 'fulfilled' && projRes.value.ok) {
          const d = await projRes.value.json()
          setProjects((d.projects || []).slice(0, 5))
          setStats(prev => ({ ...prev, projects: (d.projects || []).length }))
        }
        if (filesRes.status === 'fulfilled' && filesRes.value.ok) {
          const d = await filesRes.value.json()
          setStats(prev => ({ ...prev, files: (d.files || []).length }))
        }
      } finally { setLoading(false) }
    }
    fetchData()
  }, [token, API_BASE])

  const handleUpload = async (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return
    const file = fileList[0]
    const ext = file.name.toLowerCase()
    if (!ext.endsWith('.docx') && !ext.endsWith('.pdf')) return

    setUploading(true)
    setUploadProgress(5)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const xhr = new XMLHttpRequest()
      const result: any = await new Promise((resolve, reject) => {
        xhr.upload.addEventListener('progress', (event) => {
          if (event.lengthComputable) {
            setUploadProgress(Math.round((event.loaded / event.total) * 90))
          }
        })
        xhr.addEventListener('load', () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            setUploadProgress(100)
            resolve(JSON.parse(xhr.responseText))
          } else {
            reject(new Error('Upload error'))
          }
        })
        xhr.addEventListener('error', () => reject(new Error('Network error')))
        xhr.open('POST', `${API_BASE}/api/upload?mode=auto`)
        xhr.setRequestHeader('Authorization', `Bearer ${token}`)
        xhr.send(formData)
      })

      // Store result for editor page
      if (result.data) {
        sessionStorage.setItem('editor_data', JSON.stringify(result))
        router.push('/')
      }
    } catch (e) {
      console.error(e)
    } finally {
      setUploading(false)
      setUploadProgress(0)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    handleUpload(e.dataTransfer.files)
  }

  const cards = [
    { label: 'Лойиҳалар', value: stats.projects, icon: FileText, color: '#B48C64', bg: '#FDF6F0', path: '/projects' },
    { label: 'Файллар', value: stats.files, icon: FolderOpen, color: '#2563EB', bg: '#EFF6FF', path: '/files' },
    { label: 'Sayqallash DB', value: stats.rules, icon: Database, color: '#3B9B6E', bg: '#F0FDF6', path: '/rules' },
    { label: 'Изоҳли луғат', value: stats.annotated, icon: BookOpen, color: '#5B7FDE', bg: '#F0F4FF', path: '/linguistic/annotated' },
    { label: 'Мунозарали', value: stats.disputed, icon: MessageSquare, color: '#D47B3F', bg: '#FFF4EE', path: '/linguistic/disputed' },
    { label: 'Қисқартмалар', value: stats.abbreviations, icon: Hash, color: '#9B3B9B', bg: '#FDF0FF', path: '/linguistic/abbreviations' },
    { label: 'Синонимлар', value: stats.synonyms, icon: TrendingUp, color: '#0891B2', bg: '#F0FDFF', path: '/synonyms' },
    { label: 'Хатбошилар', value: stats.alignments, icon: BarChart3, color: '#D97706', bg: '#FFFBEB', path: '/paragraphs' },
  ]

  return (
    <div style={{ padding: '0 0 40px' }}>
      {/* Welcome + Quick Upload */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
        marginBottom: '32px', flexWrap: 'wrap', gap: '20px'
      }}>
        <div>
          <h1 style={{ fontSize: '1.8rem', fontWeight: 800, marginBottom: '6px' }}>
            Хуш келибсиз, {user?.name?.split(' ')[0] || 'Мутахассис'} 👋
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '1rem' }}>
            Pharma Expert тизимининг умумий ҳолати
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <Link href="/" style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            padding: '12px 24px', borderRadius: '12px', border: 'none',
            background: 'linear-gradient(135deg, #3b82f6, #6366f1)', color: 'white',
            fontWeight: 700, fontSize: '0.9rem', textDecoration: 'none',
            boxShadow: '0 4px 16px rgba(99,102,241,0.3)',
            transition: 'transform 0.15s, box-shadow 0.15s'
          }}>
            <Sparkles size={18} /> Scientific Pharma Editor
          </Link>
        </div>
      </div>

      {/* Upload Drop Zone */}
      <div
        onDrop={handleDrop}
        onDragOver={e => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onClick={() => fileInputRef.current?.click()}
        style={{
          position: 'relative', overflow: 'hidden',
          background: dragOver ? '#EFF6FF' : 'linear-gradient(135deg, #F8FAFC 0%, #F1F5F9 100%)',
          border: `2px dashed ${dragOver ? '#3B82F6' : '#CBD5E1'}`,
          borderRadius: '16px', padding: '28px 36px', marginBottom: '28px',
          cursor: 'pointer', transition: 'all 0.2s',
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '16px'
        }}
      >
        {uploadProgress > 0 && uploadProgress < 100 && (
          <div style={{
            position: 'absolute', bottom: 0, left: 0, height: '4px',
            width: `${uploadProgress}%`, background: 'linear-gradient(90deg, #3B82F6, #10B981)',
            transition: 'width 0.3s', borderRadius: '0 4px 4px 0'
          }} />
        )}
        <input ref={fileInputRef} type="file" accept=".docx,.pdf" style={{ display: 'none' }}
          onChange={e => handleUpload(e.target.files)} />
        
        {uploading ? (
          <>
            <Loader2 size={24} style={{ animation: 'spin 1s linear infinite', color: '#3B82F6' }} />
            <div>
              <div style={{ fontWeight: 700, fontSize: '1rem', color: '#3B82F6' }}>{uploadProgress}% — юкланмоқда...</div>
              <div style={{ fontSize: '0.82rem', color: '#64748B' }}>Файл ишланмоқда, бироз кутинг</div>
            </div>
          </>
        ) : (
          <>
            <div style={{
              width: 52, height: 52, borderRadius: '14px',
              background: dragOver ? '#DBEAFE' : '#E2E8F0',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              transition: 'background 0.2s'
            }}>
              <Upload size={24} color={dragOver ? '#3B82F6' : '#94A3B8'} />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '1rem', color: dragOver ? '#2563EB' : '#334155' }}>
                DOCX ёки PDF файлни тортинг ёки танланг
              </div>
              <div style={{ fontSize: '0.82rem', color: '#94A3B8' }}>
                Файл автоматик таҳлил қилиниб, Scientific Pharma Editor-да очилади
              </div>
            </div>
          </>
        )}
      </div>

      {/* Stat Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '16px', marginBottom: '36px' }}>
        {cards.map(card => (
          <Link key={card.label} href={card.path} style={{ textDecoration: 'none' }}>
            <div style={{
              background: card.bg, borderRadius: '16px', padding: '20px',
              border: `1.5px solid ${card.color}22`, cursor: 'pointer',
              transition: 'transform 0.15s, box-shadow 0.15s',
              boxShadow: '0 2px 8px rgba(0,0,0,0.05)'
            }}
              onMouseEnter={e => { (e.currentTarget as HTMLElement).style.transform = 'translateY(-4px)'; (e.currentTarget as HTMLElement).style.boxShadow = '0 8px 24px rgba(0,0,0,0.1)' }}
              onMouseLeave={e => { (e.currentTarget as HTMLElement).style.transform = 'translateY(0)'; (e.currentTarget as HTMLElement).style.boxShadow = '0 2px 8px rgba(0,0,0,0.05)' }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                <div style={{ width: 40, height: 40, borderRadius: '12px', background: `${card.color}18`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <card.icon size={20} color={card.color} />
                </div>
                <TrendingUp size={14} color={card.color} style={{ opacity: 0.5 }} />
              </div>
              <div style={{ fontSize: '1.8rem', fontWeight: 800, color: card.color, lineHeight: 1 }}>
                {loading ? '—' : card.value.toLocaleString()}
              </div>
              <div style={{ fontSize: '0.82rem', fontWeight: 600, color: '#555', marginTop: '4px' }}>{card.label}</div>
            </div>
          </Link>
        ))}
      </div>

      {/* Recent Projects */}
      <div style={{ background: 'var(--bg-card)', borderRadius: '16px', border: '1px solid var(--border)', padding: '28px', boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2 style={{ fontWeight: 800, fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Clock size={20} /> Охирги лойиҳалар
          </h2>
          <Link href="/projects" style={{ fontSize: '0.85rem', color: 'var(--accent-primary)', fontWeight: 600, textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '4px' }}>
            Барчасини кўриш <ChevronRight size={14} />
          </Link>
        </div>
        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
            <Loader2 size={24} style={{ animation: 'spin 1s linear infinite', marginBottom: 8 }} />
            <p>Юкланмоқда...</p>
          </div>
        ) : projects.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
            <Upload size={40} style={{ opacity: 0.2, marginBottom: 12 }} />
            <p style={{ fontWeight: 600 }}>Ҳали лойиҳа йўқ</p>
            <p style={{ fontSize: '0.85rem', marginTop: 8 }}>DOCX ёки PDF файлни юқоридаги зонага тортинг</p>
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--border)' }}>
                {['Матн рақами', 'Мутахассис', 'Файл', 'Сана'].map(h => (
                  <th key={h} style={{ padding: '10px 16px', textAlign: 'left', fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {projects.map((p, i) => (
                <tr key={i} style={{ borderBottom: '1px solid var(--border)', cursor: 'pointer', transition: 'background 0.15s' }}
                  onClick={() => router.push(`/projects`)}
                  onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = 'var(--bg-secondary)'}
                  onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = ''}>
                  <td style={{ padding: '14px 16px' }}>
                    <span style={{ fontFamily: 'monospace', fontSize: '0.85rem', padding: '2px 8px', background: '#EFF6FF', color: '#2563EB', borderRadius: '6px', fontWeight: 700 }}>
                      {p.id || '—'}
                    </span>
                  </td>
                  <td style={{ padding: '14px 16px', fontSize: '0.88rem' }}>
                    <span style={{ color: '#16A34A', fontWeight: 600 }}>● {p.specialist_name || p.user_full_name || '—'}</span>
                  </td>
                  <td style={{ padding: '14px 16px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                    {p.original_filename || p.name || '—'}
                  </td>
                  <td style={{ padding: '14px 16px', color: 'var(--text-muted)', fontSize: '0.82rem' }}>
                    {p.updated_at ? new Date(p.updated_at).toLocaleDateString('uz-UZ') : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <style jsx global>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  )
}
