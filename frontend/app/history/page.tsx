'use client'

import React, { useState, useEffect } from 'react'
import { 
  Clock, 
  FileText, 
  Search, 
  ChevronRight, 
  Loader2,
  Calendar,
  User,
  Trash2,
  ExternalLink
} from 'lucide-react'
import { useAuth } from '../../components/LoginGuard'
import Link from 'next/link'
import api from '../../services/api'

export default function HistoryPage() {
  const { token, user } = useAuth()
  const [projects, setProjects] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  useEffect(() => {
    if (token) fetchProjects()
  }, [token])

  const fetchProjects = async () => {
    setLoading(true)
    try {
      const data: any = await api.projects.list()
      setProjects(data.projects || [])
    } catch (err) {
      console.error('Fetch error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!confirm("Ushbu loyihani o'chirishni tasdiqlaysizmi?")) return
    try {
      await api.projects.delete(id)
      setProjects(projects.filter(p => p.id !== id))
    } catch (_e) {}
  }

  const filteredProjects = projects.filter(p => {
    const q = search.toLowerCase()
    return (p.name?.toLowerCase().includes(q) || 
            p.specialist_name?.toLowerCase().includes(q) ||
            p.id?.toLowerCase().includes(q))
  })

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '—'
    try {
      return new Date(dateStr).toLocaleDateString('uz-UZ', { 
        day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit'
      })
    } catch (_e) { return dateStr }
  }

  if (loading) {
    return (
      <div style={{ padding: '100px', textAlign: 'center', color: 'var(--text-muted)' }}>
        <Loader2 className="animate-spin" size={48} style={{ margin: '0 auto 24px', opacity: 0.5 }} />
        <p style={{ fontSize: '1.1rem', fontWeight: 600 }}>Tarix yuklanmoqda...</p>
      </div>
    )
  }

  return (
    <div className="animate-fadeIn" style={{ maxWidth: '1200px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: '40px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h1 style={{ fontSize: '2.2rem', fontWeight: 800, marginBottom: '8px', letterSpacing: '-1px' }}>
            Tarix 📋
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '1.1rem' }}>
            Barcha loyihalar va tahrir tarixi.
          </p>
        </div>
        <div style={{ 
          display: 'flex', alignItems: 'center', gap: '12px', 
          background: 'var(--bg-card)', padding: '12px 20px', borderRadius: 'var(--radius-lg)', 
          border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)' 
        }}>
          <FileText size={20} color="var(--accent-primary)" />
          <span style={{ fontWeight: 800, fontSize: '1.1rem' }}>{projects.length}</span>
          <span style={{ fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.9rem' }}>Loyiha</span>
        </div>
      </div>

      {/* Search */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ position: 'relative', maxWidth: '400px' }}>
          <Search size={18} style={{ position: 'absolute', left: '16px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input 
            type="text" 
            placeholder="Loyiha nomi yoki mutaxassis bo'yicha qidirish..." 
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ 
              width: '100%', padding: '12px 12px 12px 48px',
              borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)',
              background: 'var(--bg-card)', fontSize: '0.95rem',
              boxShadow: 'var(--shadow-sm)', outline: 'none', transition: 'border-color 0.2s'
            }}
            onFocus={e => e.currentTarget.style.borderColor = 'var(--accent-primary)'}
            onBlur={e => e.currentTarget.style.borderColor = 'var(--border)'}
          />
        </div>
      </div>

      {/* Table */}
      <div style={{ 
        background: 'var(--bg-card)', borderRadius: 'var(--radius-xl)',
        border: '1px solid var(--border)', boxShadow: 'var(--shadow-md)', overflow: 'hidden'
      }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ background: 'var(--bg-secondary)', borderBottom: '2px solid var(--border)' }}>
              <th style={{ padding: '20px 24px', fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Loyiha</th>
              <th style={{ padding: '20px 24px', fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Mutaxassis</th>
              <th style={{ padding: '20px 24px', fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Yaratilgan</th>
              <th style={{ padding: '20px 24px', fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Oxirgi o'zgarish</th>
              <th style={{ padding: '20px 24px', fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', textAlign: 'right' }}>Amallar</th>
            </tr>
          </thead>
          <tbody>
            {filteredProjects.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ padding: '80px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  <Clock size={64} style={{ marginBottom: '16px', opacity: 0.2 }} />
                  <h3 style={{ fontSize: '1.2rem', fontWeight: 600 }}>Hozircha tarix yo'q</h3>
                  <p style={{ fontSize: '0.9rem', marginTop: '8px' }}>Yangi loyiha yarating va u shu yerda ko'rinadi.</p>
                </td>
              </tr>
            ) : (
              filteredProjects.map(p => (
                <tr 
                  key={p.id}
                  className="hover-row"
                  style={{ borderBottom: '1px solid var(--border)', cursor: 'pointer', transition: 'background 0.2s' }}
                  onClick={() => window.location.href = `/?project=${p.id}`}
                >
                  <td style={{ padding: '20px 24px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <div style={{ 
                        width: '40px', height: '40px', borderRadius: '10px',
                        background: 'var(--accent-bg)', color: 'var(--accent-primary)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center'
                      }}>
                        <FileText size={20} />
                      </div>
                      <div>
                        <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>{p.name || `Loyiha #${p.id?.slice(0, 8)}`}</span>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>{p.id}</div>
                      </div>
                    </div>
                  </td>
                  <td style={{ padding: '20px 24px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                      <User size={14} />
                      {p.specialist_name || 'Aniqlanmagan'}
                    </div>
                  </td>
                  <td style={{ padding: '20px 24px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                      <Calendar size={14} />
                      {formatDate(p.created_at)}
                    </div>
                  </td>
                  <td style={{ padding: '20px 24px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                      <Clock size={14} />
                      {formatDate(p.updated_at)}
                    </div>
                  </td>
                  <td style={{ padding: '20px 24px', textAlign: 'right' }}>
                    <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                      <button 
                        onClick={(e) => { e.stopPropagation(); window.location.href = `/?project=${p.id}` }}
                        style={{ 
                          padding: '8px 16px', borderRadius: '8px', 
                          background: 'var(--accent-bg)', color: 'var(--accent-primary)',
                          border: 'none', cursor: 'pointer', fontWeight: 600, fontSize: '0.8rem',
                          display: 'flex', alignItems: 'center', gap: '6px'
                        }}
                      >
                        <ExternalLink size={14} /> Ochish
                      </button>
                      <button 
                        onClick={(e) => handleDelete(p.id, e)}
                        style={{ 
                          padding: '8px', borderRadius: '8px',
                          background: 'var(--danger-bg)', color: 'var(--danger)',
                          border: 'none', cursor: 'pointer'
                        }}
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <style jsx global>{`
        .hover-row:hover { background-color: var(--bg-secondary) !important; }
      `}</style>
    </div>
  )
}
