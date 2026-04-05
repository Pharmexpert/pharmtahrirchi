'use client'

import React, { useState, useEffect } from 'react'
import { 
  Users, 
  UserCheck, 
  UserX, 
  Shield, 
  Trash2, 
  ChevronLeft, 
  Loader2, 
  Search,
  Mail,
  ShieldCheck,
  MoreVertical,
  Filter,
  AlertCircle,
  Activity,
  FileText,
  Database,
  Plus,
  Save,
  Download
} from 'lucide-react'
import Link from 'next/link'
import { useAuth } from '../../components/LoginGuard'

export default function AdminPage() {
  const { token, user: currentUser } = useAuth()
  const [users, setUsers] = useState<any[]>([])
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [rules, setRules] = useState<any[]>([])
  const [rulesSearch, setRulesSearch] = useState('')
  const [activeTab, setActiveTab] = useState<'all' | 'pending' | 'active' | 'rules'>('all')

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const fetchData = async () => {
    setLoading(true)
    try {
      const auth = { 'Authorization': `Bearer ${token}` }
      const [uRes, sRes, rRes] = await Promise.all([
        fetch(`${API_BASE}/api/admin/users`, { headers: auth }),
        fetch(`${API_BASE}/api/admin/db-stats`, { headers: auth }),
        fetch(`${API_BASE}/api/admin/rules`, { headers: auth })
      ])
      
      if (uRes.ok) {
        const uData = await uRes.json()
        setUsers(uData.users || [])
      }
      if (sRes.ok) {
        const sData = await sRes.json()
        setStats(sData)
      }
      if (rRes.ok) {
        const rData = await rRes.json()
        setRules(rData.rules || [])
      }
    } catch (err) {
      setError('Data fetch error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (token) fetchData()
  }, [token])

  const handleApprove = async (userId: string, status: 'approved' | 'rejected') => {
    try {
      const res = await fetch(`${API_BASE}/api/admin/approve`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ userId, status })
      })
      if (res.ok) {
        setUsers(prev => prev.map(u => u.id === userId ? { ...u, status } : u))
      }
    } catch (_e) {}
  }

  const handleRoleChange = async (userId: string, role: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/admin/role`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ userId, role })
      })
      if (res.ok) {
        setUsers(prev => prev.map(u => u.id === userId ? { ...u, role } : u))
      }
    } catch (_e) {}
  }

  const handleDeleteRule = async (id: number) => {
    if (!confirm('Qoidani o\'chirishni tasdiqlaysizmi?')) return
    try {
      const res = await fetch(`${API_BASE}/api/admin/rules/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        setRules(prev => prev.filter(r => r.id !== id))
      }
    } catch (_e) {}
  }

  const filteredUsers = users.filter(u => {
    const matchesSearch = u.email?.toLowerCase().includes(search.toLowerCase()) || u.name?.toLowerCase().includes(search.toLowerCase());
    if (activeTab === 'pending') return matchesSearch && u.status === 'pending';
    if (activeTab === 'active') return matchesSearch && u.status === 'approved';
    return matchesSearch;
  })

  const filteredRules = rules.filter(r => 
    r.wrong_form?.toLowerCase().includes(rulesSearch.toLowerCase()) || 
    r.correct_form?.toLowerCase().includes(rulesSearch.toLowerCase())
  )

  if (loading) return (
    <div style={{ padding: '100px', textAlign: 'center', color: 'var(--text-muted)' }}>
      <Loader2 className="animate-spin" size={48} style={{ margin: '0 auto 24px', opacity: 0.5 }} />
      <p style={{ fontSize: '1.1rem', fontWeight: 600 }}>Tizim ma'lumotlari yuklanmoqda...</p>
    </div>
  )

  return (
    <div className="animate-fadeIn" style={{ maxWidth: '1200px', margin: '0 auto', paddingBottom: '100px' }}>
      {/* Header */}
      <div style={{ marginBottom: '40px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: '2.4rem', fontWeight: 900, marginBottom: '8px', letterSpacing: '-1.5px', color: '#0F172A' }}>
            Admin Paneli 🛡️
          </h1>
          <p style={{ color: '#64748B', fontSize: '1.1rem', fontWeight: 500 }}>
            Tizim holati va foydalanuvchilarni boshqarish.
          </p>
        </div>
        <Link href="/admin/activity" style={{ 
          display: 'flex', alignItems: 'center', gap: '10px', 
          background: 'linear-gradient(135deg, #0F172A, #1E293B)', 
          color: 'white', padding: '12px 24px', borderRadius: '14px', 
          fontSize: '0.9rem', fontWeight: 700, textDecoration: 'none',
          boxShadow: '0 10px 25px rgba(0,0,0,0.1)'
        }}>
          <Activity size={18} />
          Tizim Faoliyati
        </Link>
      </div>

      {/* Stats Grid */}
      <div style={{ 
        display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', 
        gap: '20px', marginBottom: '40px' 
      }}>
        <StatCard icon={<Users size={24} />} title="Foydalanuvchilar" value={stats?.projects || users.length} color="#3B82F6" />
        <StatCard icon={<FileText size={24} />} title="Aktiv Loyihalar" value={stats?.active_projects || 0} color="#6366F1" />
        <StatCard icon={<CheckCircle2 size={24} />} title="Yakunlangan" value={stats?.finished_projects || 0} color="#10B981" />
        <StatCard icon={<Database size={24} />} title="Linguistik Qoidalar" value={stats?.sayqallash_rules || 0} color="#F59E0B" />
      </div>

      {/* Controls Area */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: '24px',
        gap: '24px'
      }}>
        <div style={{ display: 'flex', background: 'var(--bg-card)', padding: '4px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)' }}>
           <button onClick={() => setActiveTab('all')} style={tabStyle(activeTab === 'all')}>Hammasi</button>
           <button onClick={() => setActiveTab('pending')} style={tabStyle(activeTab === 'pending')}>Kutayotganlar</button>
           <button onClick={() => setActiveTab('active')} style={tabStyle(activeTab === 'active')}>Tasdiqlanganlar</button>
           <button onClick={() => setActiveTab('rules')} style={tabStyle(activeTab === 'rules')}>Linguistik Qoidalar</button>
        </div>

        <div style={{ position: 'relative', flex: 1, maxWidth: '400px' }}>
          <Search size={18} style={{ position: 'absolute', left: '16px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input 
            type="text" 
            placeholder={activeTab === 'rules' ? "Qoidalar bo'yicha qidirish..." : "Foydalanuvchi qidirish..."} 
            value={activeTab === 'rules' ? rulesSearch : search}
            onChange={e => activeTab === 'rules' ? setRulesSearch(e.target.value) : setSearch(e.target.value)}
            style={{ 
              width: '100%',
              padding: '12px 12px 12px 48px',
              borderRadius: 'var(--radius-lg)',
              border: '1px solid var(--border)',
              background: 'var(--bg-card)',
              fontSize: '0.95rem',
              boxShadow: 'var(--shadow-sm)',
              outline: 'none',
              transition: 'border-color 0.2s'
            }}
          />
        </div>
      </div>

      {activeTab === 'rules' ? (
        <div style={{ background: 'white', borderRadius: '24px', border: '1px solid #E2E8F0', overflow: 'hidden' }}>
          <div style={{ padding: '20px 24px', borderBottom: '1px solid #E2E8F0', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#F8FAFC' }}>
            <h3 style={{ fontWeight: 800, color: '#0F172A', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Database size={18} color="#F59E0B" />
              Linguistik Qoidalar ({filteredRules.length})
            </h3>
            <div style={{ display: 'flex', gap: '10px' }}>
               <a href={`${API_BASE}/api/admin/rules/export`} target="_blank" rel="noreferrer" style={{ 
                 display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px', borderRadius: '10px',
                 background: '#10B981', color: 'white', fontSize: '0.8rem', fontWeight: 700, textDecoration: 'none'
               }}>
                 <Download size={14} /> Export (XLSX)
               </a>
            </div>
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
             <thead style={{ background: '#F1F5F9' }}>
                <tr>
                   <th style={{ padding: '15px 24px', textAlign: 'left', fontSize: '0.75rem', color: '#64748B' }}>XATO SHAKL</th>
                   <th style={{ padding: '15px 24px', textAlign: 'left', fontSize: '0.75rem', color: '#64748B' }}>TO'G'RI SHAKL</th>
                   <th style={{ padding: '15px 24px', textAlign: 'left', fontSize: '0.75rem', color: '#64748B' }}>TUR</th>
                   <th style={{ padding: '15px 24px', textAlign: 'right', fontSize: '0.75rem', color: '#64748B' }}>AMALLAR</th>
                </tr>
             </thead>
             <tbody>
                {filteredRules.slice(0, 50).map(r => (
                   <tr key={r.id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                      <td style={{ padding: '15px 24px', fontWeight: 700, color: '#DC2626', fontSize: '0.9rem' }}>{r.wrong_form}</td>
                      <td style={{ padding: '15px 24px', fontWeight: 700, color: '#10B981', fontSize: '0.9rem' }}>{r.correct_form}</td>
                      <td style={{ padding: '15px 24px' }}>
                         <span style={{ fontSize: '0.7rem', fontWeight: 700, background: '#EFF6FF', color: '#3B82F6', padding: '2px 8px', borderRadius: '4px' }}>
                            {r.error_type}
                         </span>
                      </td>
                      <td style={{ padding: '15px 24px', textAlign: 'right' }}>
                         <button onClick={() => handleDeleteRule(r.id)} style={{ padding: '6px', borderRadius: '6px', background: '#FEF2F2', color: '#EF4444', border: 'none', cursor: 'pointer' }}>
                            <Trash2 size={14} />
                         </button>
                      </td>
                   </tr>
                ))}
             </tbody>
          </table>
          {filteredRules.length > 50 && (
             <div style={{ padding: '20px', textAlign: 'center', fontSize: '0.85rem', color: '#64748B', background: '#F8FAFC' }}>
                Dastlabki 50 та қоида кўрсатилмоқда. Барчасини кўриш учун қидирувдан фойдаланинг.
             </div>
          )}
        </div>
      ) : (
        /* Main Table - Users */
        <div style={{ 
          background: 'var(--bg-card)', 
          borderRadius: 'var(--radius-xl)', 
          border: '1px solid var(--border)', 
          boxShadow: 'var(--shadow-md)',
          overflow: 'hidden'
        }}>

        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ background: 'var(--bg-secondary)', borderBottom: '2px solid var(--border)' }}>
              <th style={{ padding: '20px 24px', fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Foydalanuvchi</th>
              <th style={{ padding: '20px 24px', fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Status</th>
              <th style={{ padding: '20px 24px', fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Rol</th>
              <th style={{ padding: '20px 24px', fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', textAlign: 'right' }}>Amallar</th>
            </tr>
          </thead>
          <tbody>
            {filteredUsers.map(u => (
              <tr 
                key={u.id} 
                className="hover-row"
                style={{ 
                  borderBottom: '1px solid var(--border)',
                  transition: 'background 0.2s'
                }}
              >
                <td style={{ padding: '20px 24px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    {u.avatar_url ? (
                      <img src={u.avatar_url} style={{ width: '44px', height: '44px', borderRadius: '12px', border: '2px solid var(--bg-secondary)' }} alt="" />
                    ) : (
                      <div style={{ width: '44px', height: '44px', borderRadius: '12px', background: 'var(--accent-bg)', color: 'var(--accent-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '1.2rem' }}>
                        {u.name?.[0] || 'U'}
                      </div>
                    )}
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                      <span style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--text-primary)' }}>{u.name}</span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                        <Mail size={12} /> {u.email}
                      </div>
                    </div>
                  </div>
                </td>
                <td style={{ padding: '20px 24px' }}>
                  <span style={{ 
                    padding: '6px 14px', 
                    borderRadius: '20px', 
                    fontSize: '0.75rem', 
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    background: u.status === 'approved' ? 'var(--success-bg)' : u.status === 'rejected' ? 'var(--danger-bg)' : 'var(--warning-bg)',
                    color: u.status === 'approved' ? 'var(--success)' : u.status === 'rejected' ? 'var(--danger)' : 'var(--warning)'
                  }}>
                    {u.status === 'approved' ? <CheckCircle2 size={14} /> : u.status === 'rejected' ? <AlertCircle size={14} /> : <Loader2 size={14} className="animate-spin" />}
                    {u.status}
                  </span>
                </td>
                <td style={{ padding: '20px 24px' }}>
                  <div style={{ position: 'relative' }}>
                    <Shield size={14} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--accent-primary)' }} />
                    <select 
                      value={u.role} 
                      onChange={(e) => handleRoleChange(u.id, e.target.value)}
                      disabled={u.id === currentUser?.id}
                      style={{ 
                        padding: '8px 12px 8px 36px',
                        background: 'var(--bg-secondary)',
                        border: '1px solid var(--border)',
                        borderRadius: 'var(--radius-md)',
                        fontSize: '0.85rem',
                        fontWeight: 600,
                        outline: 'none',
                        cursor: u.id === currentUser?.id ? 'not-allowed' : 'pointer',
                        appearance: 'none',
                        width: '160px'
                      }}
                    >
                      <option value="user">Foydalanuvchi</option>
                      <option value="ishchi">Translate Specialist</option>
                      <option value="ekspert">Senior Expert</option>
                      <option value="rahbar">Department Head</option>
                      <option value="admin">System Admin</option>
                    </select>
                  </div>
                </td>
                <td style={{ padding: '20px 24px', textAlign: 'right' }}>
                  <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                    {u.status !== 'approved' && (
                      <button 
                         onClick={() => handleApprove(u.id, 'approved')}
                         style={{ 
                           padding: '10px', 
                           borderRadius: '10px', 
                           background: 'var(--success-bg)', 
                           color: 'var(--success)', 
                           border: 'none', 
                           cursor: 'pointer' 
                         }}
                         title="Tasdiqlash"
                      >
                        <UserCheck size={20} />
                      </button>
                    )}
                    {u.status !== 'rejected' && u.id !== currentUser?.id && (
                      <button 
                         onClick={() => handleApprove(u.id, 'rejected')}
                         style={{ 
                           padding: '10px', 
                           borderRadius: '10px', 
                           background: 'var(--danger-bg)', 
                           color: 'var(--danger)', 
                           border: 'none', 
                           cursor: 'pointer' 
                         }}
                         title="Rad etish"
                      >
                        <UserX size={20} />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filteredUsers.length === 0 && (
           <div style={{ padding: '80px', textAlign: 'center', color: 'var(--text-muted)' }}>
             <Users size={64} style={{ marginBottom: '16px', opacity: 0.2 }} />
             <h3 style={{ fontSize: '1.2rem', fontWeight: 600 }}>Hech qanday foydalanuvchi topilmadi</h3>
           </div>
        )}
      </div>

      )}
    </div>
  )
}

function StatCard({ icon, title, value, color }: { icon: any, title: string, value: any, color: string }) {
  return (
    <div style={{ 
      background: 'white', padding: '24px', borderRadius: '24px', 
      border: '1px solid #E2E8F0', boxShadow: '0 4px 6px rgba(0,0,0,0.02)',
      display: 'flex', alignItems: 'center', gap: '20px'
    }}>
      <div style={{ 
        width: '56px', height: '56px', borderRadius: '16px', 
        background: `${color}15`, color: color,
        display: 'flex', alignItems: 'center', justifyContent: 'center'
      }}>
        {icon}
      </div>
      <div>
        <div style={{ color: '#64748B', fontSize: '0.9rem', fontWeight: 600, marginBottom: '4px' }}>{title}</div>
        <div style={{ color: '#0F172A', fontSize: '1.5rem', fontWeight: 800 }}>{value}</div>
      </div>
    </div>
  )
}

function tabStyle(active: boolean): React.CSSProperties {
  return {
    padding: '10px 20px', 
    borderRadius: 'var(--radius-sm)', 
    border: 'none', 
    fontSize: '0.9rem', 
    fontWeight: 700,
    cursor: 'pointer',
    background: active ? 'white' : 'transparent',
    color: active ? 'var(--accent-primary)' : 'var(--text-muted)',
    boxShadow: active ? 'var(--shadow-sm)' : 'none',
    transition: 'all 0.2s'
  }
}
