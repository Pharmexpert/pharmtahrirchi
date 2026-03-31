'use client'

import React, { useState, useEffect } from 'react'
import { 
  Plus, 
  FileText, 
  Clock, 
  ChevronRight, 
  Search, 
  Filter,
  MoreVertical,
  Trash2,
  ExternalLink,
  UploadCloud,
  CheckCircle2,
  AlertCircle
} from 'lucide-react'
import { useAuth } from '../components/LoginGuard'
import TableEditor from '../components/TableEditor'
import Link from 'next/link'

export default function Dashboard() {
  const { user, token, isAdmin } = useAuth()
  const [projects, setProjects] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null)
  const [isUploading, setIsUploading] = useState(false)

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  useEffect(() => {
    if (user && !selectedProjectId) {
      fetchProjects()
    }
  }, [user, selectedProjectId])

  const fetchProjects = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/projects`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setProjects(data.projects || [])
      }
    } catch (err) {
      console.error('Fetch projects error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteProject = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!confirm('Ushbu loyihani o\'chirishni tasdiqlaysizmi?')) return
    
    try {
      const res = await fetch(`${API_BASE}/api/projects/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        setProjects(projects.filter(p => p.id !== id))
      }
    } catch (err) {
      console.error('Delete error:', err)
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.[0]) return
    setIsUploading(true)
    
    const formData = new FormData()
    formData.append('file', e.target.files[0])
    
    try {
      const res = await fetch(`${API_BASE}/upload-docx`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      })
      if (res.ok) {
        const data = await res.json()
        // If data has a text_id, we can open it
        if (data.text_id) {
          setSelectedProjectId(data.text_id)
          setShowUploadModal(false)
        } else {
          fetchProjects()
          setShowUploadModal(false)
        }
      }
    } catch (err) {
      alert('Yuklashda xato yuz berdi')
    } finally {
      setIsUploading(false)
    }
  }

  if (selectedProjectId) {
    return (
      <div className="animate-fadeIn">
        <button 
          onClick={() => setSelectedProjectId(null)}
          style={{ 
            marginBottom: '20px', 
            background: 'none', 
            border: 'none', 
            color: 'var(--accent-primary)', 
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontWeight: 600
          }}
        >
          ← Dashboardga qaytish
        </button>
        <TableEditor textId={selectedProjectId} />
      </div>
    )
  }

  return (
    <div className="animate-fadeIn" style={{ maxWidth: '1200px', margin: '0 auto' }}>
      {/* Welcome Header */}
      <div style={{ marginBottom: '40px' }}>
        <h1 style={{ fontSize: '2.2rem', fontWeight: 800, marginBottom: '8px', letterSpacing: '-1px' }}>
          Salom, {user?.name?.split(' ')[0]}! 👋
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '1.1rem' }}>
          Тизимга хуш келибсиз. Бугунги таржима ишларини бошлаймизми?
        </p>
      </div>

      {/* Grid Actions */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '24px', marginBottom: '48px' }}>
        {/* New Translation Card */}
        <div 
          onClick={() => setShowUploadModal(true)}
          style={{ 
            background: 'var(--accent-gradient)',
            padding: '32px',
            borderRadius: 'var(--radius-lg)',
            color: 'white',
            cursor: 'pointer',
            position: 'relative',
            overflow: 'hidden',
            boxShadow: 'var(--shadow-glow)',
            transition: 'transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)'
          }}
          onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-8px) scale(1.02)'}
          onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0) scale(1)'}
        >
          <div style={{ position: 'relative', zIndex: 2 }}>
            <div style={{ width: '48px', height: '48px', background: 'rgba(255,255,255,0.2)', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '20px' }}>
              <Plus size={28} />
            </div>
            <h3 style={{ fontSize: '1.4rem', fontWeight: 700, marginBottom: '8px' }}>Yangi Loyiha</h3>
            <p style={{ opacity: 0.9, fontSize: '0.9rem', lineHeight: 1.5 }}>
              Yangi DOCX faylni yuklang va AI yordamida trilinguall alignmentni boshlang.
            </p>
          </div>
          <div style={{ position: 'absolute', bottom: '-20px', right: '-20px', opacity: 0.1 }}>
            <FileText size={160} />
          </div>
        </div>

        {/* Stats Card (Example) */}
        <div style={{ 
          background: 'var(--bg-card)',
          padding: '32px',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border)',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between'
        }}>
          <div>
            <h4 style={{ color: 'var(--text-muted)', fontSize: '0.9rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '16px' }}>Status</h4>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
              <CheckCircle2 size={32} color="var(--success)" />
              <span style={{ fontSize: '2rem', fontWeight: 800 }}>{projects.length}</span>
            </div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Umumiy loyihalar soni</p>
          </div>
          <div style={{ paddingTop: '20px', borderTop: '1px solid var(--border)', marginTop: '20px' }}>
             <Link href="/history" style={{ color: 'var(--accent-primary)', fontWeight: 600, fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '4px' }}>
               Barcha tarixni ko'rish <ChevronRight size={16} />
             </Link>
          </div>
        </div>
      </div>

      {/* Projects Section */}
      <section>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700 }}>So'nggi loyihalar</h2>
          <div style={{ display: 'flex', gap: '12px' }}>
            <div style={{ position: 'relative' }}>
              <Search size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input 
                type="text" 
                placeholder="Qidiriuv..." 
                style={{ 
                  padding: '10px 12px 10px 40px', 
                  borderRadius: 'var(--radius-md)', 
                  border: '1px solid var(--border)',
                  background: 'var(--bg-card)',
                  fontSize: '0.9rem',
                  width: '240px',
                  outline: 'none'
                }} 
              />
            </div>
          </div>
        </div>

        {loading ? (
          <div style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
            <Loader2 className="animate-spin" style={{ margin: '0 auto 16px' }} />
            Loyihalar yuklanmoqda...
          </div>
        ) : projects.length === 0 ? (
          <div style={{ 
            padding: '80px', 
            textAlign: 'center', 
            background: 'var(--bg-card)', 
            borderRadius: 'var(--radius-lg)',
            border: '1px dashed var(--border)'
          }}>
            <FileText size={48} color="var(--text-muted)" style={{ marginBottom: '16px', opacity: 0.5 }} />
            <h3 style={{ fontSize: '1.2rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>Hozircha loyihalar yo'q</h3>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>Yangi loyiha yaratish uchun "Yangi Loyiha" tugmasini bosing.</p>
            <button 
              onClick={() => setShowUploadModal(true)}
              style={{ padding: '12px 24px', background: 'var(--accent-primary)', color: 'white', border: 'none', borderRadius: 'var(--radius-md)', fontWeight: 600, cursor: 'pointer' }}
            >
              Fayl yuklash
            </button>
          </div>
        ) : (
          <div style={{ 
            background: 'var(--bg-card)', 
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border)',
            overflow: 'hidden',
            boxShadow: 'var(--shadow-sm)'
          }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)', background: 'var(--bg-secondary)' }}>
                  <th style={{ padding: '16px 24px', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Loyiha nomi</th>
                  <th style={{ padding: '16px 24px', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Mutaxassis</th>
                  <th style={{ padding: '16px 24px', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Sana</th>
                  <th style={{ padding: '16px 24px', fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Status</th>
                  <th style={{ padding: '16px 24px', textAlign: 'right' }}></th>
                </tr>
              </thead>
              <tbody>
                {projects.map((p) => (
                  <tr 
                    key={p.id} 
                    onClick={() => setSelectedProjectId(p.id)}
                    style={{ 
                      borderBottom: '1px solid var(--border)', 
                      cursor: 'pointer',
                      transition: 'background 0.2s'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.background = 'var(--bg-secondary)'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                  >
                    <td style={{ padding: '20px 24px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'var(--info-bg)', color: 'var(--info)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                          <FileText size={20} />
                        </div>
                        <span style={{ fontWeight: 600 }}>{p.name || `Hujjat #${p.id.slice(0, 8)}`}</span>
                      </div>
                    </td>
                    <td style={{ padding: '20px 24px', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                      {p.specialist_name || 'Aniqlanmagan'}
                    </td>
                    <td style={{ padding: '20px 24px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Clock size={14} />
                        {new Date(p.updated_at || p.created_at).toLocaleDateString('uz-UZ')}
                      </div>
                    </td>
                    <td style={{ padding: '20px 24px' }}>
                      <span style={{ 
                        padding: '4px 12px', 
                        borderRadius: '20px', 
                        fontSize: '0.75rem', 
                        fontWeight: 700,
                        background: p.status === 'completed' ? 'var(--success-bg)' : 'var(--warning-bg)',
                        color: p.status === 'completed' ? 'var(--success)' : 'var(--warning)',
                        textTransform: 'uppercase'
                      }}>
                        {p.status === 'completed' ? 'Tayyor' : 'Jarayonda'}
                      </span>
                    </td>
                    <td style={{ padding: '20px 24px', textAlign: 'right' }}>
                      <button 
                        onClick={(e) => handleDeleteProject(p.id, e)}
                        style={{ background: 'none', border: 'none', padding: '8px', cursor: 'pointer', color: 'var(--danger)', borderRadius: '8px' }}
                        onMouseEnter={(e) => e.currentTarget.style.background = 'var(--danger-bg)'}
                        onMouseLeave={(e) => e.currentTarget.style.background = 'none'}
                      >
                        <Trash2 size={18} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Upload Modal Overlay */}
      {showUploadModal && (
        <div style={{ 
          position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', 
          background: 'rgba(61, 43, 31, 0.4)', backdropFilter: 'blur(8px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
        }}>
          <div style={{ 
            background: 'var(--bg-card)', 
            padding: '40px', 
            borderRadius: 'var(--radius-xl)', 
            width: '100%', 
            maxWidth: '500px',
            boxShadow: 'var(--shadow-lg)',
            border: '1px solid var(--border)',
            position: 'relative'
          }}>
            <button 
              onClick={() => setShowUploadModal(false)}
              style={{ position: 'absolute', top: '20px', right: '20px', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
            >
              <Plus size={24} style={{ transform: 'rotate(45deg)' }} />
            </button>
            <div style={{ textAlign: 'center', marginBottom: '32px' }}>
              <div style={{ width: '64px', height: '64px', background: 'var(--accent-bg)', color: 'var(--accent-primary)', borderRadius: '16px', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px' }}>
                <UploadCloud size={32} />
              </div>
              <h3 style={{ fontSize: '1.4rem', fontWeight: 700, marginBottom: '8px' }}>Hujjat yuklash</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>DOCX formatidagi faylni tanlang</p>
            </div>

            <label style={{ 
              display: 'flex', 
              flexDirection: 'column', 
              alignItems: 'center', 
              gap: '12px',
              padding: '40px',
              border: '2px dashed var(--border)',
              borderRadius: 'var(--radius-lg)',
              cursor: isUploading ? 'wait' : 'pointer',
              background: 'var(--bg-secondary)',
              transition: 'border-color 0.2s'
            }}
            onMouseEnter={(e) => e.currentTarget.style.borderColor = 'var(--accent-primary)'}
            onMouseLeave={(e) => e.currentTarget.style.borderColor = 'var(--border)'}
            >
              <input type="file" accept=".docx" onChange={handleFileUpload} disabled={isUploading} style={{ display: 'none' }} />
              {isUploading ? (
                <>
                  <Loader2 className="animate-spin" size={32} color="var(--accent-primary)" />
                  <span style={{ fontWeight: 600 }}>Tahlil qilinmoqda...</span>
                </>
              ) : (
                <>
                  <FileText size={32} color="var(--text-muted)" />
                  <span style={{ fontWeight: 600 }}>Faylni tanlash uchun bosing</span>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Maksimal hajm: 20MB</span>
                </>
              )}
            </label>
          </div>
        </div>
      )}
    </div>
  )
}
