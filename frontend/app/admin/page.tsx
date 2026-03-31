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
  CheckCircle2,
  AlertCircle
} from 'lucide-react'
import Link from 'next/link'
import { useAuth } from '../../components/LoginGuard'

export default function AdminPage() {
  const { token, user: currentUser } = useAuth()
  const [users, setUsers] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'all' | 'pending' | 'active'>('all')

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const fetchUsers = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/admin/users`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (!res.ok) throw new Error('Admin access denied')
      const data = await res.json()
      setUsers(data.users || [])
    } catch (err) {
      setError('Users fetch error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (token) fetchUsers()
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

  const filteredUsers = users.filter(u => {
    const matchesSearch = u.email?.toLowerCase().includes(search.toLowerCase()) || u.name?.toLowerCase().includes(search.toLowerCase());
    if (activeTab === 'pending') return matchesSearch && u.status === 'pending';
    if (activeTab === 'active') return matchesSearch && u.status === 'approved';
    return matchesSearch;
  })

  if (loading) return (
    <div style={{ padding: '100px', textAlign: 'center', color: 'var(--text-muted)' }}>
      <Loader2 className="animate-spin" size={48} style={{ margin: '0 auto 24px', opacity: 0.5 }} />
      <p style={{ fontSize: '1.1rem', fontWeight: 600 }}>Foydalanuvchilar yuklanmoqda...</p>
    </div>
  )

  return (
    <div className="animate-fadeIn" style={{ maxWidth: '1200px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: '40px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h1 style={{ fontSize: '2.2rem', fontWeight: 800, marginBottom: '8px', letterSpacing: '-1px' }}>
            Admin Paneli 🛡️
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '1.1rem' }}>
            Foydalanuvchilar va ularning huquqlarini boshqarish.
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', background: 'var(--bg-card)', padding: '12px 20px', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)' }}>
          <Users size={20} color="var(--accent-primary)" />
          <span style={{ fontWeight: 800, fontSize: '1.1rem' }}>{users.length}</span>
          <span style={{ fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.9rem' }}>Foydalanuvchi</span>
        </div>
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
        </div>

        <div style={{ position: 'relative', flex: 1, maxWidth: '400px' }}>
          <Search size={18} style={{ position: 'absolute', left: '16px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input 
            type="text" 
            placeholder="Qidirish (Ism yoki Email)..." 
            value={search}
            onChange={e => setSearch(e.target.value)}
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
            onFocus={e => e.currentTarget.style.borderColor = 'var(--accent-primary)'}
            onBlur={e => e.currentTarget.style.borderColor = 'var(--border)'}
          />
        </div>
      </div>

      {/* Main Table */}
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

      <style jsx global>{`
        .hover-row:hover { background-color: var(--bg-secondary) !important; }
      `}</style>
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
