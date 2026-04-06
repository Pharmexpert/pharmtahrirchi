'use client'

import React, { useState, useEffect } from 'react'
import { History, Search, Eye, Trash2, Download, FileText } from 'lucide-react'
import { useAuth } from '../../components/LoginGuard'
import Link from 'next/link'

export default function ProjectsPage() {
  const { token, isAdmin } = useAuth()
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const [projects, setProjects] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

  useEffect(() => { fetchProjects() }, [token])

  const fetchProjects = async () => {
    if (!token) return
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/projects`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setProjects(data.projects || data || [])
      }
    } finally { setLoading(false) }
  }

  const handleDelete = async (textId: string) => {
    if (!token) return
    try {
      const res = await fetch(`${API_BASE}/api/projects/${textId}`, {
        method: 'DELETE', headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        setProjects(prev => prev.filter(p => p.text_id !== textId))
        setDeleteConfirm(null)
      }
    } catch (e) { console.error(e) }
  }

  const filtered = projects.filter(p =>
    (p.text_id || p.id || '').toLowerCase().includes(search.toLowerCase()) ||
    (p.specialist_name || p.specialist || p.name || '').toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div>
      <div style={{ marginBottom: '32px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h1 style={{ fontSize: '2rem', fontWeight: 800, marginBottom: '8px', letterSpacing: '-0.5px' }}>
            Лойиҳалар 📁
          </h1>
          <p style={{ color: 'var(--text-muted)' }}>Барча юкланган ҳужжатлар рўйхати</p>
        </div>
        <div style={{
          background: 'var(--bg-card)', padding: '12px 20px', borderRadius: '12px',
          border: '1px solid var(--border)', fontWeight: 800, fontSize: '1.1rem'
        }}>
          {projects.length} та лойиҳа
        </div>
      </div>

      {/* Search */}
      <div style={{ position: 'relative', marginBottom: '24px', maxWidth: '420px' }}>
        <Search size={18} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
        <input
          type="text" placeholder="Лойиҳа ёки мутахассис..."
          value={search} onChange={e => setSearch(e.target.value)}
          style={{
            width: '100%', padding: '12px 12px 12px 44px', borderRadius: '12px',
            border: '1px solid var(--border)', background: 'var(--bg-card)',
            fontSize: '0.95rem', outline: 'none'
          }}
        />
      </div>

      {/* Table */}
      <div style={{ background: 'var(--bg-card)', borderRadius: '16px', border: '1px solid var(--border)', overflow: 'hidden', boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: 'var(--bg-secondary)', borderBottom: '2px solid var(--border)' }}>
              {['№', 'Матн рақами', 'Мутахассис', 'Янгиланган', 'Амаллар'].map(h => (
                <th key={h} style={{ padding: '16px 20px', textAlign: 'left', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>Юкланмоқда...</td></tr>
            ) : filtered.length === 0 ? (
              <tr><td colSpan={5} style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
                <FileText size={48} style={{ opacity: 0.2, marginBottom: 12 }} />
                <p style={{ fontWeight: 600 }}>Лойиҳалар топилмади</p>
              </td></tr>
            ) : filtered.map((p, i) => (
              <tr key={i} style={{ borderBottom: '1px solid var(--border)', transition: 'background 0.15s' }}
                onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = 'var(--bg-secondary)'}
                onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = ''}
              >
                <td style={{ padding: '16px 20px', color: 'var(--text-muted)', fontWeight: 600 }}>{i + 1}</td>
                <td style={{ padding: '16px 20px' }}>
                  <span style={{
                    fontFamily: 'monospace', fontSize: '0.9rem', padding: '4px 10px',
                    background: 'var(--accent-bg)', color: 'var(--accent-primary)',
                    borderRadius: '6px', fontWeight: 700
                  }}>{p.text_id || p.id || '—'}</span>
                </td>
                <td style={{ padding: '16px 20px', fontWeight: 600 }}>{p.specialist_name || p.user_full_name || '—'}</td>
                <td style={{ padding: '16px 20px', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                  {p.updated_at ? new Date(p.updated_at).toLocaleDateString('uz-UZ') : '—'}
                </td>
                <td style={{ padding: '16px 20px' }}>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <Link href={`/?text_id=${p.text_id || p.id}`} style={{
                      padding: '7px 14px', borderRadius: '8px',
                      background: 'var(--accent-bg)', color: 'var(--accent-primary)',
                      fontWeight: 700, fontSize: '0.8rem', textDecoration: 'none',
                      display: 'flex', alignItems: 'center', gap: '4px'
                    }}>
                      <Eye size={14} /> Ochish
                    </Link>
                    {isAdmin && (
                      <button onClick={() => setDeleteConfirm(p.text_id || p.id)} style={{
                        padding: '7px', borderRadius: '8px', border: 'none',
                        background: 'var(--danger-bg)', color: 'var(--danger)', cursor: 'pointer'
                      }}>
                        <Trash2 size={14} />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Delete Confirm Modal */}
      {deleteConfirm && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', backdropFilter: 'blur(4px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
        }}>
          <div style={{ background: 'var(--bg-card)', borderRadius: '16px', padding: '32px', maxWidth: '400px', width: '90%', textAlign: 'center' }}>
            <Trash2 size={40} color="var(--danger)" style={{ marginBottom: 16 }} />
            <h3 style={{ fontSize: '1.1rem', fontWeight: 800, marginBottom: 8 }}>Лойиҳани ўчириш</h3>
            <p style={{ color: 'var(--text-muted)', marginBottom: 24 }}>
              <strong style={{ color: 'var(--accent-primary)' }}>{deleteConfirm}</strong> лойиҳасини ўчирмоқчимисиз? Бу амал қайтарилмайди.
            </p>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
              <button onClick={() => setDeleteConfirm(null)} style={{ padding: '10px 24px', borderRadius: '10px', border: '1px solid var(--border)', background: 'white', fontWeight: 700, cursor: 'pointer' }}>Bekor</button>
              <button onClick={() => handleDelete(deleteConfirm)} style={{ padding: '10px 24px', borderRadius: '10px', border: 'none', background: 'var(--danger)', color: 'white', fontWeight: 700, cursor: 'pointer' }}>O'chirish</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
