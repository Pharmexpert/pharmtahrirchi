'use client'

import React, { useState, useEffect } from 'react'
import { BarChart3, FileText, Database, Users, TrendingUp, BookOpen, MessageSquare, Hash, Upload } from 'lucide-react'
import { useAuth } from '../../components/LoginGuard'
import Link from 'next/link'
import { useRouter } from 'next/navigation'

export default function DashboardPage() {
  const { token, user } = useAuth()
  const router = useRouter()
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const [stats, setStats] = useState({
    projects: 0, alignments: 0, rules: 0,
    annotated: 0, disputed: 0, abbreviations: 0
  })
  const [projects, setProjects] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      if (!token) return
      setLoading(true)
      try {
        const headers = { Authorization: `Bearer ${token}` }
        const [projRes, rulesRes, lingRes] = await Promise.allSettled([
          fetch(`${API_BASE}/api/projects`, { headers }),
          fetch(`${API_BASE}/api/admin/rules?lang=uz&limit=1`, { headers }),
          fetch(`${API_BASE}/api/linguistic/all`),
        ])
        if (projRes.status === 'fulfilled' && projRes.value.ok) {
          const d = await projRes.value.json()
          const list = d.projects || d || []
          setProjects(list.slice(0, 5))
          setStats(prev => ({ ...prev, projects: list.length }))
        }
        if (rulesRes.status === 'fulfilled' && rulesRes.value.ok) {
          const d = await rulesRes.value.json()
          setStats(prev => ({ ...prev, rules: d.total || 0 }))
        }
        if (lingRes.status === 'fulfilled' && lingRes.value.ok) {
          const d = await lingRes.value.json()
          setStats(prev => ({
            ...prev,
            annotated: (d.annotated || []).length,
            disputed: (d.disputed || []).length,
            abbreviations: (d.abbreviations || []).length,
            alignments: (d.paragraphs || []).length,
          }))
        }
      } finally { setLoading(false) }
    }
    fetchData()
  }, [token])

  const cards = [
    { label: 'Лойиҳалар', value: stats.projects, icon: FileText, color: '#B48C64', bg: '#FDF6F0', path: '/projects' },
    { label: 'Sayqallash қоидалари', value: stats.rules, icon: Database, color: '#3B9B6E', bg: '#F0FDF6', path: '/rules' },
    { label: 'Изоҳли луғат', value: stats.annotated, icon: BookOpen, color: '#5B7FDE', bg: '#F0F4FF', path: '/linguistic/annotated' },
    { label: 'Мунозарали терминлар', value: stats.disputed, icon: MessageSquare, color: '#D47B3F', bg: '#FFF4EE', path: '/linguistic/disputed' },
    { label: 'Қисқартмалар', value: stats.abbreviations, icon: Hash, color: '#9B3B9B', bg: '#FDF0FF', path: '/linguistic/abbreviations' },
  ]

  return (
    <div style={{ padding: '0 0 40px' }}>
      {/* Welcome */}
      <div style={{ marginBottom: '32px' }}>
        <h1 style={{ fontSize: '1.8rem', fontWeight: 800, marginBottom: '6px' }}>
          Хуш келибсиз, {user?.name?.split(' ')[0] || 'Мутахассис'} 👋
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '1rem' }}>
          Pharma Expert тизимининг умумий ҳолати
        </p>
      </div>

      {/* Stat Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '20px', marginBottom: '40px' }}>
        {cards.map(card => (
          <Link key={card.label} href={card.path} style={{ textDecoration: 'none' }}>
            <div style={{
              background: card.bg, borderRadius: '16px', padding: '24px',
              border: `1.5px solid ${card.color}22`, cursor: 'pointer',
              transition: 'transform 0.15s, box-shadow 0.15s',
              boxShadow: '0 2px 8px rgba(0,0,0,0.05)'
            }}
              onMouseEnter={e => { (e.currentTarget as HTMLElement).style.transform = 'translateY(-4px)'; (e.currentTarget as HTMLElement).style.boxShadow = '0 8px 24px rgba(0,0,0,0.1)' }}
              onMouseLeave={e => { (e.currentTarget as HTMLElement).style.transform = 'translateY(0)'; (e.currentTarget as HTMLElement).style.boxShadow = '0 2px 8px rgba(0,0,0,0.05)' }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                <div style={{ width: 44, height: 44, borderRadius: '12px', background: `${card.color}18`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <card.icon size={22} color={card.color} />
                </div>
                <TrendingUp size={16} color={card.color} style={{ opacity: 0.5 }} />
              </div>
              <div style={{ fontSize: '2rem', fontWeight: 800, color: card.color, lineHeight: 1 }}>
                {loading ? '—' : card.value.toLocaleString()}
              </div>
              <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#555', marginTop: '6px' }}>{card.label}</div>
            </div>
          </Link>
        ))}
      </div>

      {/* Recent Projects */}
      <div style={{ background: 'var(--bg-card)', borderRadius: '16px', border: '1px solid var(--border)', padding: '28px', boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2 style={{ fontWeight: 800, fontSize: '1.1rem' }}>Охирги лойиҳалар</h2>
          <Link href="/projects" style={{ fontSize: '0.85rem', color: 'var(--accent-primary)', fontWeight: 600, textDecoration: 'none' }}>Барчасини кўриш →</Link>
        </div>
        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>Юкланмоқда...</div>
        ) : projects.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
            <Upload size={40} style={{ opacity: 0.2, marginBottom: 12 }} />
            <p style={{ fontWeight: 600 }}>Ҳали лойиҳа йўқ</p>
            <p style={{ fontSize: '0.85rem', marginTop: 8 }}>Асосий саҳифадан DOCX файл юкланг</p>
            <Link href="/" style={{ display: 'inline-block', marginTop: 12, padding: '8px 20px', background: 'var(--accent-gradient)', color: 'white', borderRadius: '8px', textDecoration: 'none', fontWeight: 700, fontSize: '0.85rem' }}>Файл юклаш</Link>
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--border)' }}>
                {['Лойиҳа номи', 'Матн рақами', 'Мутахассис', 'Сана'].map(h => (
                  <th key={h} style={{ padding: '10px 16px', textAlign: 'left', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {projects.map((p, i) => (
                <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td style={{ padding: '14px 16px', fontWeight: 600 }}>{p.specialist || '—'}</td>
                  <td style={{ padding: '14px 16px', fontFamily: 'monospace', fontSize: '0.85rem', color: 'var(--accent-primary)' }}>{p.text_id || '—'}</td>
                  <td style={{ padding: '14px 16px', color: 'var(--text-muted)' }}>{p.specialist || '—'}</td>
                  <td style={{ padding: '14px 16px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>{p.updated_at ? new Date(p.updated_at).toLocaleDateString('uz-UZ') : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
