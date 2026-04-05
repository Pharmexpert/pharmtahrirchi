'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { Activity, Search, Filter, Calendar, User, FileText, CheckCircle, Database, AlertCircle, Loader2, ArrowRight } from 'lucide-react'
import { useAuth } from '../../components/LoginGuard'

interface ActivityLog {
  id: number
  en_text: string
  ru_text: string
  uz_text: string
  specialist_name: string
  text_id: string
  action_type: string
  created_at: string
}

export default function ActivityPage() {
  const { token } = useAuth()
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  
  const [logs, setLogs] = useState<ActivityLog[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')

  const fetchLogs = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/admin/activity?limit=200`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setLogs(data.logs || [])
      }
    } catch (e) {
      console.error("Failed to fetch logs:", e)
    } finally {
      setLoading(false)
    }
  }, [API_BASE, token])

  useEffect(() => {
    fetchLogs()
  }, [fetchLogs])

  const filteredLogs = logs.filter(log => {
    const matchesSearch = 
      log.en_text?.toLowerCase().includes(filter.toLowerCase()) ||
      log.specialist_name?.toLowerCase().includes(filter.toLowerCase()) ||
      log.text_id?.toLowerCase().includes(filter.toLowerCase())
    
    const matchesType = typeFilter === '' || log.action_type === typeFilter
    
    return matchesSearch && matchesType
  })

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr)
    return d.toLocaleString('uz-UZ', { 
      day: '2-digit', month: '2-digit', year: 'numeric', 
      hour: '2-digit', minute: '2-digit' 
    })
  }

  const getActionColor = (type: string) => {
    switch (type) {
      case 'AI Polished': return { bg: '#F5F3FF', text: '#7C3AED', icon: <Sparkles size={14} /> }
      case 'Project Finished': return { bg: '#F0FDF4', text: '#16A34A', icon: <CheckCircle size={14} /> }
      case 'Manual Edit': return { bg: '#EFF6FF', text: '#2563EB', icon: <FileText size={14} /> }
      default: return { bg: '#F8FAFC', text: '#64748B', icon: <Activity size={14} /> }
    }
  }

  return (
    <div style={{ padding: '20px' }}>
      {/* Header Area */}
      <div style={{ 
        background: 'linear-gradient(135deg, #1E293B 0%, #0F172A 100%)', 
        borderRadius: '24px', padding: '40px', marginBottom: '30px', color: 'white',
        boxShadow: '0 20px 40px rgba(0,0,0,0.1)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <div style={{ 
            width: '60px', height: '60px', borderRadius: '18px', 
            background: 'rgba(255,255,255,0.1)', display: 'flex', 
            alignItems: 'center', justifyContent: 'center' 
          }}>
            <Activity size={32} color="#38BDF8" />
          </div>
          <div>
            <h1 style={{ fontSize: '2rem', fontWeight: 800, margin: 0, letterSpacing: '-0.02em' }}>Система Фаолияти</h1>
            <p style={{ margin: '5px 0 0 0', opacity: 0.7, fontSize: '0.95rem' }}>
              Тизимдаги барча лингвистик ўзгаришлар ва проектнинг ҳолатлари тарихи
            </p>
          </div>
        </div>
      </div>

      {/* Controls */}
      <div style={{ 
        display: 'flex', gap: '15px', marginBottom: '25px', flexWrap: 'wrap',
        background: 'white', padding: '20px', borderRadius: '16px', border: '1px solid #E2E8F0'
      }}>
        <div style={{ position: 'relative', flex: 1, minWidth: '300px' }}>
          <Search size={18} style={{ position: 'absolute', left: '15px', top: '50%', transform: 'translateY(-50%)', color: '#94A3B8' }} />
          <input 
            type="text" 
            placeholder="Мутахассис, лойиҳа ёки матн бўйича қидириш..." 
            value={filter}
            onChange={e => setFilter(e.target.value)}
            style={{ 
              width: '100%', padding: '12px 15px 12px 45px', borderRadius: '12px', 
              border: '1.5px solid #E2E8F0', outline: 'none', fontSize: '0.9rem',
              transition: 'border-color 0.2s'
            }}
          />
        </div>
        
        <select 
          value={typeFilter}
          onChange={e => setTypeFilter(e.target.value)}
          style={{ 
            padding: '12px 20px', borderRadius: '12px', border: '1.5px solid #E2E8F0',
            background: 'white', fontSize: '0.9rem', outline: 'none', minWidth: '180px'
          }}
        >
          <option value="">Барча турлар</option>
          <option value="AI Polished">AI Сайқаллаш</option>
          <option value="Manual Edit">Қўл таҳрири</option>
          <option value="Project Finished">Якунланганлар</option>
        </select>

        <button onClick={fetchLogs} style={{ 
          padding: '12px 20px', borderRadius: '12px', border: 'none',
          background: '#0F172A', color: 'white', fontWeight: 700, cursor: 'pointer',
          display: 'flex', alignItems: 'center', gap: '8px'
        }}>
          <Loader2 size={16} className={loading ? 'animate-spin' : ''} />
          Янгилаш
        </button>
      </div>

      {/* Activities List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
        {loading ? (
          <div style={{ padding: '100px', textAlign: 'center', color: '#64748B' }}>
            <Loader2 size={40} className="animate-spin" style={{ margin: '0 auto 20px' }} />
            <p style={{ fontWeight: 600 }}>Маълумотлар юкланмоқда...</p>
          </div>
        ) : filteredLogs.length === 0 ? (
          <div style={{ padding: '100px', textAlign: 'center', background: 'white', borderRadius: '24px', border: '1px dashed #E2E8F0' }}>
            <AlertCircle size={48} color="#CBD5E1" style={{ margin: '0 auto 20px' }} />
            <p style={{ color: '#64748B', fontWeight: 600 }}>Ҳеч қандай фаолият топилмади</p>
          </div>
        ) : (
          filteredLogs.map(log => {
            const theme = getActionColor(log.action_type)
            return (
              <div key={log.id} style={{ 
                background: 'white', border: '1px solid #E2E8F0', borderRadius: '20px',
                padding: '25px', transition: 'transform 0.2s, box-shadow 0.2s',
                display: 'grid', gridTemplateColumns: 'auto 1fr auto', gap: '25px', alignItems: 'start'
              }}
              onMouseEnter={e => {
                e.currentTarget.style.transform = 'translateY(-2px)'
                e.currentTarget.style.boxShadow = '0 10px 25px rgba(0,0,0,0.05)'
              }}
              onMouseLeave={e => {
                e.currentTarget.style.transform = 'none'
                e.currentTarget.style.boxShadow = 'none'
              }}>
                {/* Action Type Icon */}
                <div style={{ 
                  width: '48px', height: '48px', borderRadius: '14px', 
                  background: theme.bg, color: theme.text,
                  display: 'flex', alignItems: 'center', justifyContent: 'center'
                }}>
                  {log.action_type === 'AI Polished' ? <Sparkles size={22} /> : 
                   log.action_type === 'Project Finished' ? <CheckCircle size={22} /> : <FileText size={22} />}
                </div>

                {/* Content */}
                <div style={{ overflow: 'hidden' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                    <span style={{ 
                      padding: '4px 10px', borderRadius: '6px', background: theme.bg, 
                      color: theme.text, fontSize: '0.7rem', fontWeight: 800, textTransform: 'uppercase' 
                    }}>{log.action_type}</span>
                    <span style={{ color: '#94A3B8', fontSize: '0.8rem' }}>•</span>
                    <span style={{ color: '#1E293B', fontSize: '0.85rem', fontWeight: 700 }}>
                      <User size={12} style={{ verticalAlign: 'middle', marginRight: '4px' }} />
                      {log.specialist_name}
                    </span>
                    <span style={{ color: '#94A3B8', fontSize: '0.8rem' }}>•</span>
                    <span style={{ color: '#64748B', fontSize: '0.85rem' }}>
                      <Database size={12} style={{ verticalAlign: 'middle', marginRight: '4px' }} />
                      PROJ-{log.text_id.slice(0, 8)}
                    </span>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div style={{ fontSize: '0.9rem', color: '#1E293B', fontWeight: 500 }}>{log.en_text}</div>
                    {(log.ru_text || log.uz_text) && (
                      <div style={{ display: 'flex', gap: '15px', alignItems: 'center' }}>
                        <ArrowRight size={14} color="#94A3B8" />
                        <div style={{ fontSize: '0.85rem', color: '#16A34A', background: '#F0FDF4', padding: '4px 10px', borderRadius: '6px' }}>
                          {log.uz_text || log.ru_text}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Metadata */}
                <div style={{ textAlign: 'right', minWidth: '120px' }}>
                  <div style={{ color: '#1E293B', fontSize: '0.85rem', fontWeight: 700, marginBottom: '4px' }}>
                    <Calendar size={12} style={{ verticalAlign: 'middle', marginRight: '4px' }} />
                    {formatDate(log.created_at).split(',')[0]}
                  </div>
                  <div style={{ color: '#94A3B8', fontSize: '0.75rem' }}>
                    {formatDate(log.created_at).split(',')[1]}
                  </div>
                </div>
              </div>
            )
          })
        )}
      </div>

      <style jsx global>{`
        .animate-spin {
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}

function Sparkles({ size, color }: { size: number, color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/>
      <path d="M5 3v4"/>
      <path d="M19 17v4"/>
      <path d="M3 5h4"/>
      <path d="M17 19h4"/>
    </svg>
  )
}
